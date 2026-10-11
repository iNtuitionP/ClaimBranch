"""Bounded context and one-shot offline dispatch. No network or file access.

Record classification must come from the trusted reader, never a provider.
Content screening is supplementary; it is not a proof that arbitrary prose is
public. Live deployments and transport are intentionally unavailable here.
"""
from dataclasses import asdict, dataclass, replace
import hashlib
import ipaddress
import re
from threading import Lock
from urllib.parse import urlsplit

from .canonical import ContractError, bounded_text, canonical_bytes, decode, digest, identifier, integer
from .review import Proposal
from . import paper_context
from .research_schema import normalize


FIELDS = {"observation": {"statement", "status"}, "claim": {"statement", "status"},
          "interpretation": {"statement", "rationale"}, "manuscript": {"excerpt"}}
PURPOSES = ("compare-evidence", "critique-interpretation", "plan-experiment", "draft-manuscript")
SENSITIVE = re.compile(r"-----BEGIN .*PRIVATE KEY-----|\bBearer\s+\S+|\bsk-[A-Za-z0-9_-]{16,}|file://|/(?:Users|home|etc|var)/|[A-Za-z]:[\\/]", re.I)


@dataclass(frozen=True)
class ContextRecord:
    project_id: str
    id: str
    kind: str
    sensitivity: str
    fields: bytes
    schema_version: int = 1

    def __post_init__(self):
        identifier(self.project_id)
        identifier(self.id)
        if type(self.schema_version) is not int or self.schema_version not in (1, 2):
            raise ContractError("unknown context version")
        allowed = FIELDS if self.schema_version == 1 else paper_context.FIELDS
        if self.kind not in allowed or self.sensitivity not in ("public", "redacted", "private", "secret"):
            raise ContractError("unknown context record classification")
        values = decode(self.fields)
        if type(values) is not dict or not values or not set(values).issubset(allowed[self.kind]):
            raise ContractError("context record contains a forbidden field")
        if self.schema_version == 1:
            for value in values.values():
                bounded_text(value)
        else:
            paper_context.validate_fields(self.kind, values)
        if canonical_bytes(values) != self.fields:
            raise ContractError("context record must be canonical")

    @classmethod
    def create(cls, project_id, record_id, kind, sensitivity, fields, *, schema_version=1):
        return cls(project_id, record_id, kind, sensitivity, canonical_bytes(fields), schema_version)


@dataclass(frozen=True)
class ContextSelection:
    project_id: str
    episode_id: str
    purpose: str
    fields: tuple
    schema_version: int = 1
    binding: bytes | None = None

    def __post_init__(self):
        identifier(self.project_id)
        identifier(self.episode_id)
        if type(self.schema_version) is not int or self.schema_version not in (1, 2):
            raise ContractError("unknown context version")
        if self.schema_version == 1 and self.binding is not None:
            raise ContractError("version-one context cannot carry a paper binding")
        if self.schema_version == 2:
            value = normalize(decode(self.binding), paper_context.BINDING)
            if canonical_bytes(value) != self.binding:
                raise ContractError("canonical paper view binding required")
        record_limit = 16 if self.schema_version == 1 else paper_context.NODE_LIMIT + paper_context.EDGE_LIMIT
        field_limit = 4 if self.schema_version == 1 else paper_context.FIELD_LIMIT
        if self.purpose not in PURPOSES or type(self.fields) is not tuple or not 1 <= len(self.fields) <= record_limit:
            raise ContractError("bounded explicit context selection required")
        seen = set()
        for pair in self.fields:
            if type(pair) is not tuple or len(pair) != 2:
                raise ContractError("record/field selection required")
            record_id, names = pair
            identifier(record_id)
            if record_id in seen or type(names) is not tuple or not 1 <= len(names) <= field_limit:
                raise ContractError("duplicate or empty context selection")
            seen.add(record_id)
            for name in names:
                identifier(name)
            if len(set(names)) != len(names):
                raise ContractError("duplicate selected field")


@dataclass(frozen=True)
class ContextBundle:
    records: tuple
    selection: ContextSelection
    payload: bytes
    digest: str


def _sensitive(value):
    if isinstance(value, str):
        return bool(SENSITIVE.search(value))
    if isinstance(value, dict):
        return any(_sensitive(item) for item in value.values())
    if isinstance(value, list):
        return any(_sensitive(item) for item in value)
    return False


def compile_context(records, selection):
    if type(records) is not tuple or not isinstance(selection, ContextSelection):
        raise ContractError("typed bounded context inputs required")
    limit = 16 if selection.schema_version == 1 else paper_context.NODE_LIMIT + paper_context.EDGE_LIMIT
    if len(records) > limit:
        raise ContractError("context source count exceeds its profile")
    known = {}
    for record in records:
        if (not isinstance(record, ContextRecord) or record.project_id != selection.project_id or record.id in known
                or record.schema_version != selection.schema_version):
            raise ContractError("ambiguous or cross-project context source")
        known[record.id] = record
    included, redactions = [], []
    for key, names in selection.fields:
        if key not in known:
            raise ContractError("unknown context source")
        record = known[key]
        fields = decode(record.fields)
        if record.sensitivity == "secret" or not set(names).issubset(fields):
            raise ContractError("forbidden context field or sensitivity")
        if record.kind == "manuscript" and selection.purpose != "draft-manuscript":
            raise ContractError("manuscript excerpt was not selected for this purpose")
        if selection.schema_version == 2 and not paper_context.REQUIRED.get(record.kind, set()).issubset(names):
            raise ContractError("selection hides a required scientific status or relation field")
        selected = {name: fields[name] for name in sorted(names)}
        if _sensitive(selected):
            raise ContractError("selected text contains a secret or absolute local path")
        included.append({"id": key, "kind": record.kind, "sensitivity": record.sensitivity, "fields": selected})
        omitted = sorted(set(fields) - set(names))
        if selection.schema_version == 1:
            redactions.extend({"record_id": key, "field": name} for name in omitted)
        elif omitted:
            redactions.append({"record_id": key, "fields": omitted})
    value = {"schema_version": selection.schema_version, "project_id": selection.project_id, "episode_id": selection.episode_id,
             "purpose": selection.purpose, "records": included, "redactions": redactions}
    if selection.schema_version == 2:
        nodes = {item["id"]: item for item in included if item["kind"] != "scientific-relation"}
        edges = [item for item in included if item["kind"] == "scientific-relation"]
        if not 1 <= len(nodes) <= paper_context.NODE_LIMIT or len(edges) > paper_context.EDGE_LIMIT:
            raise ContractError("paper context exceeds node or relation bounds")
        for edge in edges:
            source, target = (nodes.get(edge["fields"][name]) for name in ("source_id", "target_id"))
            if not source or not target or source["kind"] not in ("claim", "observation", "interpretation") or target["kind"] != "claim":
                raise ContractError("scientific relation requires both explicitly selected endpoints")
        value.update(binding=decode(selection.binding), authority="unverified-candidate", authorization_verified=False)
    payload = canonical_bytes(value)
    if selection.schema_version == 2 and len(payload) > paper_context.BYTE_LIMIT:
        raise ContractError("paper context exceeds its UTF-8 byte budget; narrow the selection")
    return ContextBundle(records, selection, payload, hashlib.sha256(payload).hexdigest())


@dataclass(frozen=True)
class Destination:
    url: str
    model: str

    def __post_init__(self):
        bounded_text(self.model, limit=128)
        bounded_text(self.url, limit=1024)
        if self.url == "offline://frozen":
            return
        try:
            url = urlsplit(self.url)
            port = url.port
        except ValueError as error:
            raise ContractError("invalid provider destination") from error
        if (url.username or url.password or url.query or url.fragment or not url.hostname
                or not self.url.isascii() or "\\" in self.url or any(c.isspace() for c in self.url)):
            raise ContractError("destination cannot contain credentials, query or fragment")
        if port is not None and not 1 <= port <= 65535:
            raise ContractError("invalid provider port")
        if url.scheme == "http":
            try:
                loopback = ipaddress.ip_address(url.hostname).is_loopback
            except ValueError:
                loopback = False
            if not loopback or port is None:
                raise ContractError("HTTP requires a literal loopback address and explicit port")
        elif url.scheme != "https":
            raise ContractError("unsupported provider scheme")

    @property
    def remote_capable(self):
        return self.url != "offline://frozen"


@dataclass(frozen=True)
class OutboundReview:
    request_id: str
    nonce: str
    created_at: int
    expires_at: int
    payload: bytes
    digest: str


def review_outbound(context, destination, *, request_id, nonce, now, result_format="text",
                    retention="volatile-session-only"):
    if not isinstance(context, ContextBundle) or not isinstance(destination, Destination):
        raise ContractError("typed context and destination required")
    if compile_context(context.records, context.selection) != context:
        raise ContractError("compiled context changed")
    if result_format not in ("text", "typed"):
        raise ContractError("unknown provider response format")
    if (retention not in ('volatile-session-only', 'workspace-history')
            or result_format == 'text' and retention != 'volatile-session-only'):
        raise ContractError('unsupported provider retention; legacy text review remains volatile')
    if result_format == "typed":
        from .paper_proposals import PURPOSE_KINDS
        if context.selection.schema_version != 2 or context.selection.purpose not in PURPOSE_KINDS:
            raise ContractError("typed dispatch requires scientific paper context v2")
    identifier(request_id)
    identifier(nonce)
    integer(now)
    value = {"request_id": request_id, "nonce": nonce, "created_at": now, "expires_at": now + 120,
             "destination": asdict(destination), "context": decode(context.payload), "context_digest": context.digest,
             "remote_capable": destination.remote_capable, "retention": retention}
    # Text reviews retain their existing exact bytes/digests. Typed requests
    # bind their response contract in the displayed one-shot review as well.
    if result_format == "typed":
        value['result_schema'] = 'claimbranch.provider-result/v2'
    return OutboundReview(request_id, nonce, now, now + 120, canonical_bytes(value), digest(value))


@dataclass(frozen=True)
class Trace:
    request_id: str
    request_digest: str
    response_digest: str | None
    model: str
    disposition: str
    payload_availability: str
    payload: bytes | None

    @property
    def digest(self):
        return digest({key: value for key, value in asdict(self).items()
                       if key not in ("payload", "payload_availability")})


RESULT_BYTE_LIMIT = 65_536


def provider_result(raw):
    """Normalize a bounded, provider-neutral result; no tools or side effects.

    Raw response bytes have a separate hash. Only the normalized text may become
    a Proposal. Refusals and failures deliberately cannot carry substitute text.
    """
    if type(raw) is not bytes or len(raw) > RESULT_BYTE_LIMIT:
        raise ContractError("bounded provider result bytes required")
    value = decode(raw)
    if (type(value) is not dict or set(value) != {"schema", "status", "text"}
            or value["schema"] != "claimbranch.provider-result/v1"
            or value["status"] not in ("ok", "refused", "failed")):
        raise ContractError("unknown provider result; only proposal text is permitted")
    if value["status"] == "ok":
        bounded_text(value["text"])
    elif value["text"] is not None:
        raise ContractError("non-proposal results cannot supply text")
    if len(canonical_bytes(value)) > RESULT_BYTE_LIMIT:
        raise ContractError("normalized provider result exceeds its byte limit")
    return value


@dataclass(frozen=True)
class Dispatch:
    request_id: str
    request_digest: str
    context_digest: str
    destination: Destination
    dispatched_at: int
    expires_at: int
    result_format: str = "text"


class OfflineBroker:
    """One-shot offline ingress, including split arrival; no injected live sender."""

    def __init__(self):
        self._sent = ()
        self._dispatched = ()
        self._pending = {}
        self._used = set()
        self._lock = Lock()

    @property
    def sent(self):
        return self._sent

    @property
    def dispatched(self):
        return self._dispatched

    def begin(self, context, destination, review, *, now, result_format="text"):
        if not isinstance(review, OutboundReview):
            raise ContractError("exact outbound review required")
        current = review_outbound(context, destination, request_id=review.request_id, nonce=review.nonce,
                                  now=review.created_at, result_format=result_format)
        integer(now)
        if review != current or not review.created_at <= now < review.expires_at:
            raise ContractError("outbound content, destination or lifetime changed")
        if destination.remote_capable:
            raise ContractError("live transport requires a verified deployment and is unavailable")
        with self._lock:
            if review.request_id in self._used or review.nonce in self._used or len(self._dispatched) >= 6:
                raise ContractError("one-shot request already used or attempt budget exhausted")
            self._used.update((review.request_id, review.nonce))
            started = Dispatch(review.request_id, review.digest, context.digest, destination, now, review.expires_at, result_format)
            self._dispatched += (started,)
            self._pending[review.request_id] = (started, context.selection.project_id, context.selection.episode_id, context)
            return started

    def _finish(self, request_id, *, raw, text, disposition):
        # Caller holds the broker lock; one arrival wins and any retry is denied.
        if request_id not in self._pending:
            raise ContractError("response requires an outstanding exact dispatch")
        entry = self._pending.pop(request_id)
        return self._record(request_id, entry, raw=raw, text=text, disposition=disposition)

    def _record(self, request_id, entry, *, raw, text, disposition, typed=None):
        # Caller owns the claimed arrival and holds the lock during append.
        started, project, episode, _ = entry
        bounded = type(raw) is bytes and len(raw) <= RESULT_BYTE_LIMIT
        trace = Trace(request_id, started.request_digest, hashlib.sha256(raw).hexdigest() if bounded else None,
                      started.destination.model, disposition,
                      "retained" if bounded and disposition != "malformed" else "unavailable",
                      raw if bounded and disposition != "malformed" else None)
        self._sent += (trace,)
        if disposition == "proposed":
            if typed is not None:
                from .paper_proposals import TypedProposal
                return TypedProposal("proposal-" + digest(request_id), project, episode,
                                     started.request_digest, started.context_digest, trace.digest, canonical_bytes(typed))
            return Proposal("proposal-" + digest(request_id), project, episode, text, trace.digest)
        return None

    def complete_typed(self, request_id, raw):
        """Separate v2 ingress bound to the exact dispatched scientific context.

        Arrival consumes one dispatch and creates no candidate, adoption or
        scientific write. Existing text-only completion continues to reject v2.
        """
        from .paper_proposals import provider_typed_result
        identifier(request_id)
        with self._lock:
            if request_id not in self._pending:
                raise ContractError("response requires an outstanding exact dispatch")
            if self._pending[request_id][0].result_format != 'typed':
                raise ContractError('typed completion requires a reviewed typed dispatch; request preserved')
            entry = self._pending.pop(request_id)
        try:
            typed = provider_typed_result(raw, entry[3])
            status = "proposed" if typed['status'] == 'ok' else typed['status']
        except ContractError:
            typed, status = None, 'malformed'
        except BaseException:
            with self._lock:
                self._record(request_id, entry, raw=raw, text=None, disposition='failed')
            raise
        with self._lock:
            return self._record(request_id, entry, raw=raw, text=None, disposition=status, typed=typed)

    def complete(self, request_id, raw):
        """Record one untrusted result even when its owner has cancelled it.

        The draft owner separately decides freshness/adoptability; transport
        completion never grants scientific authority or changes a draft.
        """
        return self.complete_checked(request_id, raw, check=lambda: None)

    def complete_checked(self, request_id, raw, *, check):
        """Claim one arrival before a bounded local check, without holding a lock.

        Failure/cancellation records the original response as failed, consumes
        the dispatch, and reraises. A new arrival needs new explicit consent;
        no competing response can replace this one while the check is pending.
        This callback is an application-owned check, never provider-supplied code.
        """
        identifier(request_id)
        if not callable(check):
            raise ContractError("application-owned result check required")
        with self._lock:
            if request_id not in self._pending:
                raise ContractError("response requires an outstanding exact dispatch")
            if self._pending[request_id][0].result_format != 'text':
                raise ContractError('text completion requires a reviewed text dispatch; request preserved')
            entry = self._pending.pop(request_id)
        try:
            try:
                result = provider_result(raw)
                status = "proposed" if result["status"] == "ok" else result["status"]
                text = result["text"]
            except ContractError:
                status, text = "malformed", None
            else:
                if check() is not None:
                    raise ContractError("result check cannot replace provider content")
        except BaseException:
            with self._lock:
                self._record(request_id, entry, raw=raw, text=None, disposition="failed")
            raise
        with self._lock:
            return self._record(request_id, entry, raw=raw, text=text, disposition=status)

    def dispatch(self, context, destination, review, *, now, response):
        """Compatibility route for existing frozen text callers."""
        self.begin(context, destination, review, now=now)
        with self._lock:
            try:
                bounded_text(response)
            except ContractError:
                self._finish(review.request_id, raw=None, text=None, disposition="malformed")
                raise
            return self._finish(review.request_id, raw=response.encode("utf-8"), text=response, disposition="proposed")

    def erase_payload(self, request_id):
        identifier(request_id)
        with self._lock:
            if request_id not in {item.request_id for item in self._sent}:
                raise ContractError("unknown trace")
            self._sent = tuple(replace(item, payload=None, payload_availability="erased")
                               if item.request_id == request_id and item.payload_availability == "retained"
                               else item for item in self._sent)
