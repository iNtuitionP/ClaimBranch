"""One volatile synthetic Episode Review, backed by the portable contracts.

There is no accepted store, private import, live provider or manuscript writer.
The committed fixture is validated before any of its bytes enter the session.
"""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timedelta
import hashlib
import secrets
import time

from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.core.context import (ContextRecord, ContextSelection, Destination,
                                     OfflineBroker, compile_context, review_outbound)
from claimbranch.core.lifecycle import EpisodeLedger, ProposalAttempt
from claimbranch.core.research_history import ResearchHistory
from claimbranch.core.review import Judgment
from claimbranch.core.marked_text import preview_marked_text, tex_text
from claimbranch.validation.truth_packet import DEFAULT_PACKET, TruthPacketValidator
from claimbranch.fixtures import replay_example as replay_fixture
from .graph import project_graph


class Unavailable(ContractError):
    """A real product boundary has not passed its readiness gates."""


class DemoWorkspace:
    def __init__(self, *, clock=None, example=False):
        self.clock = clock or (lambda: int(time.time()))
        validator = TruthPacketValidator(DEFAULT_PACKET)
        validator.validate()
        if validator.errors:
            raise ContractError("committed synthetic fixture failed validation")
        self.packet = decode(validator.verified_bytes["truth-packet.json"])
        self.frozen = decode(validator.verified_bytes["frozen-proposal.json"])
        self.source_before = validator.verified_bytes["manuscript-before.tex"]
        self.source_digest = hashlib.sha256(self.source_before).hexdigest()
        frozen_history = replay_fixture("manual")
        self.base = ResearchHistory(frozen_history.seed, frozen_history.commands[:4])
        self.template = decode(frozen_history.commands[4])["payload"]["changes"]
        self.example_judgment = decode(frozen_history.commands[4])["payload"]["judgment"]
        seed = decode(self.base.seed)
        self.project, self.episode = seed["project_id"], seed["episode_id"]
        self.ledger = EpisodeLedger(self.project, "synthetic-only-v1").start(
            self.episode, dict(self.base.heads)["main"], self.base.watermark)
        self.judgment = Judgment.start(self.project, self.episode)
        self.text = self.rationale = ""
        self.before_proposal = None
        self.revision = 0
        self.broker = OfflineBroker()
        self.destination = Destination("offline://frozen", "frozen-v1")
        self.outbound = self.attempt = self.proposal = None
        self.prepared = self.result = None
        self.adopted = set()
        self.example_loaded = False
        if example:
            self.load_example()

    def load_example(self):
        if self.text or self.rationale or self.judgment.history or self.outbound or self.proposal:
            raise ContractError("예시는 빈 세션에서만 불러올 수 있습니다. 현재 초안을 보존했습니다.")
        self.edit(self.example_judgment["text"], self.example_judgment["rationale"])
        for item in self.template:
            if item["kind"] == "experiment-plan":
                item["body"]["objective"] = (
                    "합성 예시 계획: 비슷한 민감도를 가진 모델 조건을 맞추고, 가지치기율·양자화 비트수·압축률을 단계별로 바꿔 손상 순서를 비교한다. "
                    "변형의 크기와 구조를 함께 기록해 연산별 차이가 남는지 확인한다. 아직 실행하거나 결과를 측정하지 않았다.")
        self.prepare(["claim-status", "optional-experiment"], "not-required", [])
        self.example_loaded = True
        return self.state()

    def state(self):
        review = self.prepared[3] if self.prepared else None
        proposal = None
        if self.proposal:
            proposal = {"text": self.proposal.text, "id": self.proposal.id,
                        "state": self.attempt.state, "adopted": self.proposal.id in self.adopted,
                        "expires_at": self.attempt.expires_at}
        return deepcopy({"mode": "synthetic-volatile", "revision": self.revision, "example_loaded": self.example_loaded,
            "claim": self.base.view("main")["claim"], "observations": self.packet["observations"],
            "draft": {"text": self.text, "rationale": self.rationale,
                      "ai_influenced": self.judgment.ai_influenced},
            "before_proposal": self.before_proposal,
            "outbound": decode(self.outbound.payload) if self.outbound else None,
            "proposal": proposal, "review": review, "result": self.result,
            "pending_debts": [], "accepted_writes": 0, "authorization_verified": False,
            "episode": {"id": self.episode, "state": self.ledger.entries[-1].state},
            "traces": [{"request_id": item.request_id, "digest": item.digest,
                        "payload_availability": item.payload_availability} for item in self.broker.sent]})

    def edit(self, text, rationale):
        # Empty drafts are legitimate. Only a complete judgment enters history.
        raw = decode(canonical_bytes({"text": text, "rationale": rationale}))
        if any(type(raw[key]) is not str for key in raw):
            raise ContractError("draft fields must be text")
        if (raw["text"], raw["rationale"]) != (self.text, self.rationale):
            self.text, self.rationale = raw["text"], raw["rationale"]
            self.revision += 1
            self.outbound = self.prepared = self.result = None
            if self.attempt and self.proposal and self.proposal.id not in self.adopted:
                self.attempt = self.attempt.cancel()
        return self.state()

    def _judgment(self):
        if (self.text, self.rationale) == (self.judgment.text, self.judgment.rationale):
            return self.judgment
        return self.judgment.edit(self.text, self.rationale)

    def _context(self):
        records = [ContextRecord.create(self.project, "C-01", "claim", "redacted",
                   {"statement": self.packet["claim"]["statement"], "status": "supported"})]
        records.extend(ContextRecord.create(self.project, item["id"], "observation", "redacted",
                       {"statement": item["rationale"], "status": "confirmed"}) for item in self.packet["observations"])
        if self.text.strip():
            fields = {"statement": self.text}
            if self.rationale.strip():
                fields["rationale"] = self.rationale
            records.append(ContextRecord.create(self.project, "draft", "interpretation", "private", fields))
        selection = ContextSelection(self.project, self.episode, "critique-interpretation",
                                     tuple((r.id, tuple(sorted(decode(r.fields)))) for r in records))
        return compile_context(tuple(records), selection)

    def preview_request(self):
        if len(self.broker.sent) >= 3:
            raise ContractError("the example allows one proposal and two requested revisions")
        context = self._context()
        review = review_outbound(context, self.destination, request_id="request-" + secrets.token_hex(16),
                                 nonce=secrets.token_hex(24), now=self.clock())
        self.outbound = review
        self.attempt = ProposalAttempt(review.request_id, context.digest, review.created_at, review.expires_at)
        self.proposal = None
        return self.state()

    def cancel_request(self):
        if self.attempt:
            self.attempt = self.attempt.cancel()
        self.outbound = None
        return self.state()

    def request_proposal(self, request_id):
        if not self.outbound or request_id != self.outbound.request_id:
            raise ContractError("review the current exact request before dispatch")
        context = self._context()
        if not self.attempt or self.attempt.state != "pending" or self.attempt.context_digest != context.digest:
            raise ContractError("provider request was cancelled or its context changed")
        proposal = self.broker.dispatch(context, self.destination, self.outbound, now=self.clock(),
                                        response=self.frozen["normalized_text"])
        self.attempt = self.attempt.complete(proposal.text, current_digest=context.digest, now=self.clock())
        self.outbound = None
        if self.attempt.state != "proposed":
            raise ContractError("proposal arrived after the review expired")
        self.proposal = proposal
        return self.state()

    def use_proposal(self):
        if not self.proposal or self.proposal.id in self.adopted:
            raise ContractError("a current unused proposal is required")
        self.attempt = self.attempt.complete(self.proposal.text, current_digest=self._context().digest, now=self.clock())
        if self.attempt.state != "proposed":
            raise ContractError("proposal is cancelled, stale or expired")
        # Preserve a complete unaided judgment before recording AI influence.
        judgment = self._judgment() if self.text.strip() and self.rationale.strip() else self.judgment
        judgment = judgment.use_proposal(self.proposal)
        # Preserve even an incomplete edit buffer; it cannot enter Judgment
        # history until the researcher supplies a complete rationale.
        self.before_proposal = {"text": self.text, "rationale": self.rationale}
        self.judgment = judgment
        self.text = judgment.text
        self.adopted.add(self.proposal.id)
        self.revision += 1
        self.prepared = self.result = self.outbound = None
        return self.state()

    def erase_trace(self, request_id):
        self.broker.erase_payload(request_id)
        return self.state()

    def _command(self, history, operation, payload, suffix):
        # Fixture event time and the interactive consent clock are separate.
        event_time = datetime.fromisoformat(decode(history.commands[-1])["created_at"].replace("Z", "+00:00")) + timedelta(seconds=1)
        return {"schema_version": 1, "id": "demo-" + suffix, "project_id": self.project,
                "episode_id": self.episode, "created_at": event_time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "operation_type": operation, "expected_heads": dict(history.heads),
                "evidence_watermark": history.watermark, "payload": payload}

    def _manuscript(self, text):
        marker = self.packet["manuscript"]["marker_id"]
        return preview_marked_text(self.source_before, marker, text, self.source_digest).decode("utf-8")

    def prepare(self, selected, disposition, answers):
        judgment = self._judgment()
        changes = deepcopy(self.template)
        changes[0]["body"]["statement"] = judgment.text
        history = self.base.append(self._command(self.base, "record-interpretation",
                              {"judgment": asdict(judgment), "changes": changes}, "interpretation"))
        command = self._command(history, "apply-selected-merge",
                                {"judgment": asdict(judgment), "selected_ids": selected,
                                 "disposition": disposition, "answers": answers}, "merge")
        now = self.clock()
        sealed = history.prepare_merge_review(command, manuscript_digest=self.source_digest,
                    session_nonce=secrets.token_hex(24), sealed_at=now, expires_at=now + 120)
        preview = history.merge_preview(selected)
        content = decode(preview.payload)
        anchor = self.packet["manuscript"]["anchor_id"]
        # An operation's rationale does not make every branch interpretation
        # selected. Wording needs a selected interpretation with an actual path
        # to this anchor; a plan-only merge retains the original source bytes.
        wording = next((item["body"]["statement"] for item in content["changes"]
                        if item["kind"] == "interpretation" and any(
                            path[0] == item["id"] and path[-1] == anchor
                            for path in content["impact_paths"])), None)
        after = self._manuscript(wording) if wording is not None else self.source_before.decode("utf-8")
        display = {"text": judgment.text, "rationale": judgment.rationale,
                   "contributions": [asdict(item) for item in judgment.history],
                   "selected": list(preview.selection.selected), "required": list(preview.selection.required),
                   "omitted": list(preview.selection.omitted), "changes": content["changes"],
                   "impact_paths": content["impact_paths"], "has_manuscript_candidate": wording is not None,
                   "manuscript_before": self.source_before.decode("utf-8"), "manuscript_after": after,
                   "postimage_digest": hashlib.sha256(after.encode("utf-8")).hexdigest(),
                   "digest": sealed.digest, "expires_at": sealed.context.expires_at,
                   "disposition": disposition, "answers": list(sealed.answers),
                   "graph": project_graph(history, self.packet, selection=preview.selection)}
        self.judgment = judgment
        self.prepared = (history, command, sealed, display)
        self.result = None
        return self.state()

    def preview_result(self):
        if not self.prepared:
            raise ContractError("prepare a current review first")
        history, command, sealed, display = self.prepared
        candidate_history, candidate = history.append_reviewed_merge(command, sealed,
                            manuscript_digest=self.source_digest, now=self.clock())
        self.result = {"claim_status": candidate_history.view("main")["claim"]["status"],
                       "candidate_debts": [debt.kind for debt in candidate.debts],
                       "has_manuscript_candidate": display["has_manuscript_candidate"],
                       "requires_authorization": True, "authorization_verified": False}
        return self.state()

    def not_now(self):
        self.prepared = self.result = None
        return self.state()

    def accept(self):
        raise Unavailable("protected acceptance requires verified native custody, private IPC and writer isolation")
