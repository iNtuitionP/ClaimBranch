"""Offline proposal ingress experiment; no provider, egress, tools or authority."""

from scripts.contracts.first_pass import ContractError, Draft, receive_model_proposal


class PendingProposal:
    """A single response scoped to the exact synthetic draft and request."""

    def __init__(self, request_id, draft):
        if not isinstance(request_id, str) or not request_id.strip() or not isinstance(draft, Draft):
            raise ContractError("a request identity and Draft are required")
        self._request_id = request_id
        self._draft = draft
        self._pending = True

    def cancel(self):
        self._pending = False

    def deliver(self, request_id, payload, *, current):
        if not self._pending or request_id != self._request_id:
            raise ContractError("response has no matching pending request")
        self._pending = False
        if current != self._draft:
            raise ContractError("response belongs to an outdated draft")
        if type(payload) is not dict or set(payload) != {"operation", "text"}:
            raise ContractError("only bounded proposal text is permitted")
        try:
            if type(payload["text"]) is not str or len(payload["text"].encode("utf-8")) > 8192:
                raise ContractError("proposal exceeds the text boundary")
        except UnicodeError as exc:
            raise ContractError("proposal must be valid UTF-8 text") from exc
        return receive_model_proposal(self._draft, payload)
