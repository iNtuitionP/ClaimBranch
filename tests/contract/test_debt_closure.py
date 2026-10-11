"""Closing an explanation never completes a manuscript; compile alone never authorizes closure."""
from dataclasses import asdict, replace
import json
import unittest

from claimbranch.core.canonical import ContractError, canonical_bytes, decode, digest
from claimbranch.core.debt import (ClosureReview, CompileResult, closure_candidate,
    UnderstandingClosureContext, prepare_understanding_closure,
    restore_understanding_closure, understanding_closure_candidate, understanding_closure_schema)
from claimbranch.core.review import (Change, Debt, Judgment, Proposal, ReviewContext,
    acceptance_candidate, seal_review, select_changes)


class DebtClosureTests(unittest.TestCase):
    def setUp(self):
        self.debt = Debt("understanding", "project", "episode", "accepted-operation", "a" * 64, None)
        self.review = ClosureReview("close-operation", self.debt.id, "project", "episode", "current-head",
                                    "관찰과 해석의 범위를 다시 검토했다.", "new-session", 100, 160)

    def close(self, debt=None, review=None, **kwargs):
        return closure_candidate(debt or self.debt, review or self.review,
                                 current_head="current-head", now=101, **kwargs)

    def test_closure_is_separate_and_still_requires_real_authorization(self):
        candidate = self.close()
        self.assertEqual("open", self.debt.status)
        self.assertEqual("closed-by-human", candidate.resulting_debt.status)
        self.assertTrue(candidate.requires_authorization)
        self.assertFalse(candidate.authorization_verified)
        self.assertEqual(self.debt.id, candidate.resulting_debt.id)

    def test_other_debt_project_episode_old_head_and_reused_operation_fail(self):
        for field, value in {"debt_id": "another-debt", "project_id": "other", "episode_id": "other",
                             "expected_head": "old-head", "operation_id": "accepted-operation"}.items():
            with self.subTest(field=field), self.assertRaises(ContractError):
                self.close(review=replace(self.review, **{field: value}))
        with self.assertRaises(ContractError):
            closure_candidate(self.debt, self.review, current_head="current-head", now=160)

    def test_ai_cannot_supply_a_closure_review_or_close_a_closed_debt(self):
        with self.assertRaises(ContractError):
            self.close(review=Proposal("p", "project", "episode", "review complete", "a" * 64))
        with self.assertRaises(ContractError):
            self.close(debt=replace(self.debt, status="closed-by-human"))

    def test_manuscript_closure_binds_every_observed_compile_field(self):
        debt = Debt("manuscript", "project", "episode", "merge", "a" * 64, "anchor")
        proof = CompileResult(debt.id, "anchor", "patch", "attempt", "a" * 64, "b" * 64,
                              "c" * 64, "d" * 64, "e" * 64, "current-head", 1, "verified")
        review = replace(self.review, debt_id=debt.id, compile_result=proof)
        self.assertTrue(self.close(debt, review, current_compile=proof).requires_authorization)
        for field, value in {"attempt_id": "new-attempt", "source_digest": "f" * 64,
                             "postimage_digest": "f" * 64, "output_digest": "f" * 64,
                             "compiler_digest": "f" * 64, "configuration_digest": "f" * 64,
                             "fencing_token": 2}.items():
            with self.subTest(field=field), self.assertRaises(ContractError):
                self.close(debt, review, current_compile=replace(proof, **{field: value}))
        for status in ("applied-unverified", "restored", "recovery-required"):
            current = replace(proof, status=status)
            with self.subTest(status=status), self.assertRaises(ContractError):
                self.close(debt, replace(review, compile_result=current), current_compile=current)


class UnderstandingClosureTests(unittest.TestCase):
    def setUp(self):
        # Explicitly synthetic sealed cause, not an accepted v3 work-item conversion.
        judgment = Judgment.start('project', 'episode').use_proposal(
            Proposal('proposal', 'project', 'episode', 'A possible ranking explanation.', 'a' * 64)
        ).edit('Magnitude alone does not explain pruning.', 'Keep the observed mismatch and untested cause distinct.')
        selection = select_changes((Change('interpretation', 'interpretation', ('observation',)),),
                                   ('interpretation',), ('observation',))
        cause_context = ReviewContext('project', 'episode', 'cause', 'apply-selected-merge',
                                     'b' * 64, (('main', 'before'), ('alternative', 'branch')),
                                     3, 'anchor', 'c' * 64, 'cause-session', 10, 30)
        self.cause = seal_review(judgment, cause_context, selection, disposition='deferred')
        self.debt = next(d for d in acceptance_candidate(self.cause, decision='accept').debts
                         if d.kind == 'understanding')
        self.context = UnderstandingClosureContext(
            'project', 'episode', self.debt.id, 'cause', self.cause.digest, 'current-head', 4,
            'claimbranch.understanding-topics/v1', digest({'topic': 'claim scope', 'source': 'observation'}),
            digest({'display': 'synthetic current evidence and original judgment'}))
        self.rationale = '관찰의 범위와 아직 검증하지 않은 원인을 구분한다.'
        self.review = self.prepare()

    def prepare(self, *, debt=None, cause=None, context=None, current=None, **changes):
        options = dict(operation_id='close', rationale=self.rationale, session_nonce='closure-session',
                       sealed_at=100, expires_at=160, now=101)
        options.update(changes)
        return prepare_understanding_closure(debt or self.debt, cause or self.cause,
            context or self.context, current_context=current or self.context, **options)

    def candidate(self, *, debt=None, cause=None, review=None, current=None, now=101):
        return understanding_closure_candidate(debt or self.debt, cause or self.cause,
            review or self.review, current_context=current or self.context, now=now)

    def restore(self, raw, *, current=None, now=101):
        return restore_understanding_closure(raw, self.debt, self.cause,
                                            current_context=current or self.context, now=now)

    def test_exact_candidate_reuses_rationale_and_never_changes_original_or_authority(self):
        before = (asdict(self.debt), self.cause.payload, self.review.payload)
        candidate = self.candidate()
        self.assertEqual(self.rationale, self.review.rationale)
        self.assertEqual(self.review.digest, candidate.review_digest)
        self.assertEqual('close', candidate.operation_id)
        self.assertEqual(replace(self.debt, status='closed-by-human'), candidate.resulting_debt)
        self.assertTrue(candidate.requires_authorization)
        self.assertFalse(candidate.authorization_verified)
        self.assertEqual(before, (asdict(self.debt), self.cause.payload, self.review.payload))
        self.assertFalse(decode(self.review.payload)['authorization_verified'])
        # Repetition is pure calculation, not single-use receipt consumption.
        self.assertEqual(candidate, self.candidate())

    def test_every_context_binding_is_rechecked_at_preparation_and_candidate(self):
        variants = {'project_id': 'foreign', 'episode_id': 'later', 'debt_id': 'debt-other',
                    'cause_operation_id': 'other-cause', 'cause_review_digest': 'd' * 64,
                    'expected_head': 'later-head', 'evidence_watermark': 5,
                    'topics_digest': 'e' * 64, 'displayed_context_digest': 'f' * 64}
        for field, value in variants.items():
            changed = replace(self.context, **{field: value})
            with self.subTest(field=field):
                for operation in (lambda: self.prepare(current=changed),
                                  lambda: self.candidate(current=changed),
                                  lambda: self.restore(self.review.payload, current=changed)):
                    with self.assertRaises(ContractError):
                        operation()
        changed = replace(self.context, evidence_watermark=5)
        self.assertEqual(changed.expected_head, self.context.expected_head)
        fresh = self.prepare(context=changed, current=changed)
        self.assertNotEqual(self.review.digest, fresh.digest)
        self.assertEqual(self.rationale, fresh.rationale)
        self.assertFalse(self.candidate(review=fresh, current=changed).authorization_verified)

    def test_same_debt_id_with_changed_cause_review_cannot_reuse_closure(self):
        revised = seal_review(self.cause.judgment.edit('A narrower interpretation.', 'Another explicit reason.'),
                              self.cause.context, self.cause.selection, disposition='deferred')
        debt = replace(self.debt, review_digest=revised.digest)
        self.assertEqual(self.debt.id, debt.id)
        for candidate_debt, candidate_cause in ((debt, revised), (debt, self.cause), (self.debt, revised)):
            with self.subTest(digest=candidate_debt.review_digest), self.assertRaises(ContractError):
                self.candidate(debt=candidate_debt, cause=candidate_cause)
        context = replace(self.context, cause_review_digest=revised.digest)
        fresh = self.prepare(debt=debt, cause=revised, context=context, current=context)
        self.assertNotEqual(self.review.digest, fresh.digest)

    def test_matching_context_does_not_override_foreign_cause_or_rollback(self):
        for field, value in {'project_id': 'other', 'episode_id': 'other', 'debt_id': 'other',
                             'cause_operation_id': 'other', 'cause_review_digest': 'f' * 64,
                             'evidence_watermark': 2}.items():
            current = replace(self.context, **{field: value})
            with self.subTest(field=field), self.assertRaises(ContractError):
                self.prepare(context=current, current=current)

    def test_forged_manual_answered_or_unsealed_cause_is_refused(self):
        manual = Judgment.start('project', 'episode').edit('Manual meaning.', 'Manual rationale.')
        causes = [replace(self.cause, payload=b'{}'), replace(self.cause, digest='f' * 64),
                  seal_review(manual, self.cause.context, self.cause.selection, disposition='not-required'),
                  seal_review(self.cause.judgment, self.cause.context, self.cause.selection,
                              disposition='answered', answers=('Already explained.',)),
                  Proposal('p', 'project', 'episode', 'I approve closure.', 'a' * 64),
                  {'actor_class': 'human'}]
        for cause in causes:
            with self.subTest(cause=type(cause).__name__), self.assertRaises(ContractError):
                self.prepare(cause=cause)

    def test_only_exact_open_understanding_debt_is_admitted(self):
        for debt in (replace(self.debt, status='closed-by-human'), replace(self.debt, status='superseded'),
                     replace(self.debt, kind='manuscript', anchor_id='anchor'),
                     replace(self.debt, project_id='other'), replace(self.debt, episode_id='other'),
                     replace(self.debt, cause_operation_id='other'), {'id': self.debt.id, 'status': 'open'}):
            with self.subTest(debt=debt), self.assertRaises(ContractError):
                self.prepare(debt=debt)

    def test_closure_lifetime_is_fresh_even_when_historical_cause_has_expired(self):
        self.assertLess(self.cause.context.expires_at, self.review.sealed_at)
        for now in (100, 159):
            self.assertTrue(self.candidate(now=now).requires_authorization)
        for now in (99, 160, True, -1):
            with self.subTest(now=now):
                for action in (lambda: self.prepare(now=now), lambda: self.candidate(now=now),
                               lambda: self.restore(self.review.payload, now=now)):
                    with self.assertRaises(ContractError):
                        action()
        for changes in ({'operation_id': 'cause'}, {'expires_at': 100}, {'expires_at': 401},
                        {'sealed_at': True}, {'session_nonce': ''}, {'rationale': ' '}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                self.prepare(**changes)
        full_lifetime = self.prepare(expires_at=400)
        self.assertEqual(400, full_lifetime.expires_at)
        self.assertEqual(full_lifetime, self.restore(full_lifetime.payload))
        # Whole-second clocks cannot establish accepted-operation ordering.
        # Equality is allowed here; only a future accepted loader can prove it.
        same_second = self.prepare(sealed_at=10, expires_at=20, now=10)
        self.assertEqual(self.cause.context.sealed_at, same_second.sealed_at)
        self.assertFalse(self.candidate(review=same_second, now=10).authorization_verified)

    def test_changed_review_payload_digest_or_fields_are_refused(self):
        for changes in ({'payload': b'{}'}, {'digest': 'f' * 64}, {'rationale': 'Unreviewed writing.'},
                        {'operation_id': 'unreviewed'}, {'session_nonce': 'unreviewed'},
                        {'expires_at': 159}, {'context': replace(self.context, evidence_watermark=5)}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                self.candidate(review=replace(self.review, **changes))

    def test_canonical_round_trip_and_closed_versioned_shape(self):
        value = decode(self.review.payload)
        self.assertEqual('claimbranch.understanding-closure-review/v1', value['schema'])
        self.assertEqual(self.review, self.restore(self.review.payload))
        self.assertEqual(self.review.payload, canonical_bytes(value))
        for changes in ({'schema': 'claimbranch.understanding-closure-review/v2'},
                        {'rule_version': 'unknown'}, {'authorization_verified': True},
                        {'actor_class': 'human'}, {'receipt': 'forged'}, {'answers': ['complete']}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                self.restore(canonical_bytes(dict(value, **changes)))
        non_nfc = json.dumps(dict(value, rationale='e\u0301'), ensure_ascii=False,
                             sort_keys=True, separators=(',', ':')).encode()
        self.assertNotEqual(non_nfc, canonical_bytes(decode(non_nfc)))
        for raw in (non_nfc, json.dumps(value, ensure_ascii=False, indent=2).encode(), b'{"schema":1,"schema":1}',
                    b'{}', self.review.payload.decode(), b' ' * 262145):
            with self.subTest(raw_type=type(raw).__name__), self.assertRaises(ContractError):
                self.restore(raw)
        for changes in ({'evidence_watermark': True}, {'topics_rule_version': 'unknown'},
                        {'topics_digest': 'invalid'}, {'extra': 'field'}):
            changed = dict(value, context=dict(value['context'], **changes))
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                self.restore(canonical_bytes(changed))

    def test_unicode_and_resource_limits_do_not_mutate_review_or_debt(self):
        review = self.prepare(rationale='e\u0301')
        self.assertEqual('é', review.rationale)
        self.assertEqual(review, self.restore(review.payload))
        self.assertEqual(self.prepare(rationale='é').payload, review.payload)
        full = self.prepare(rationale='x' * 16384)
        self.assertEqual(full, self.restore(full.payload))
        for text in ('x' * 16385, '\ud800'):
            with self.subTest(length=len(text)), self.assertRaises(ContractError):
                self.prepare(rationale=text)
        self.assertEqual(self.rationale, self.review.rationale)
        self.assertEqual('open', self.debt.status)

    def test_legacy_review_is_not_upgraded_and_schema_is_detached(self):
        legacy = ClosureReview('close', self.debt.id, 'project', 'episode', 'current-head',
                               self.rationale, 'session', 100, 160)
        with self.assertRaises(ContractError):
            self.candidate(review=legacy)
        with self.assertRaises(ContractError):
            self.restore(canonical_bytes(asdict(legacy)))
        with self.assertRaises(ContractError):
            closure_candidate(self.debt, self.review, current_head='current-head', now=101)
        schema = understanding_closure_schema()
        schema['properties']['authorization_verified']['const'] = True
        self.assertFalse(understanding_closure_schema()['properties']['authorization_verified']['const'])

    def test_context_bounds_and_invalid_typed_inputs_fail_without_coercion(self):
        for changes in ({'topics_rule_version': 'claimbranch.understanding-topics/v2'},
                        {'evidence_watermark': True}, {'evidence_watermark': 33},
                        {'expected_head': 'invalid head'}, {'displayed_context_digest': 'not-a-digest'}):
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                replace(self.context, **changes)
        for action in (lambda: self.prepare(current={'actor_class': 'human'}),
                       lambda: self.prepare(context={'actor_class': 'human'}),
                       lambda: self.prepare(sealed_at=9, expires_at=20, now=11)):
            with self.assertRaises(ContractError):
                action()

    def test_cumulative_cause_and_partial_draft_survive_same_head_evidence_change(self):
        from claimbranch.application.paper_service import PaperService
        from claimbranch.application.paper_understanding import PaperUnderstandingSession
        from tests.contract.test_paper_episodes import command, first_episode

        source = first_episode(ai=True, merge=False, close=False)
        merge = command(source, 'apply-selected-merge', {
            'selected_ids': [item['id'] for item in source.view('alternative')['changes']],
            'judgment': source.view('alternative')['judgment'], 'disposition': 'deferred', 'answers': []})
        cause = source.prepare_merge_review(merge, manuscript_digest='c' * 64,
                                            session_nonce='cause-session', sealed_at=10, expires_at=30)
        history, acceptance = source.append_reviewed_merge(merge, cause, manuscript_digest='c' * 64, now=11)
        self.assertFalse(acceptance.authorization_verified)
        debt = next(d for d in acceptance.debts if d.kind == 'understanding')
        item = next(i for i in PaperService(history).pending_work()['items'] if i['kind'] == 'understanding')
        session = PaperUnderstandingSession(history, project_id='project', work_id=item['id'])
        state = session.state()
        session.edit(state['topics'][0]['id'], '조건을 더 확인하는 중…', reuse_rationale=True)
        unfinished = session.snapshot()
        context = UnderstandingClosureContext('project', 'episode', debt.id, merge['id'], cause.digest,
            dict(history.heads)['main'], history.watermark, state['draft']['rules_version'],
            state['draft']['topics_digest'], state['context']['digest'])
        review = self.prepare(debt=debt, cause=cause, context=context, current=context,
                              rationale=cause.rationale)
        self.assertFalse(self.candidate(debt=debt, cause=cause, review=review,
                                        current=context).authorization_verified)
        corrected = history.append(command(history, 'record-evidence-event', {
            'event_id': 'closure-correction', 'target_id': 'obs-1', 'run_id': 'run-accuracy',
            'action': 'correct', 'statement': 'Synthetic recount: pruning loses 1.2 percentage points.',
            'value': '1.2', 'rationale': 'Recount the original measurement.', 'supersedes_id': 'event-1'}))
        state = session.update_source(corrected)
        changed = replace(context, evidence_watermark=corrected.watermark,
                          displayed_context_digest=state['context']['digest'])
        self.assertEqual(history.heads, corrected.heads)
        self.assertNotEqual(context.evidence_watermark, changed.evidence_watermark)
        with self.assertRaises(ContractError):
            self.candidate(debt=debt, cause=cause, review=review, current=changed)
        self.assertEqual(unfinished, session.snapshot())
        session.rebind_context(state['context']['digest'])
        with self.assertRaises(ContractError):
            self.candidate(debt=debt, cause=cause, review=review, current=changed)
        restored = PaperUnderstandingSession(corrected, project_id='project', work_id=item['id'],
                                              draft=session.snapshot()).state()
        self.assertEqual(decode(unfinished)['entries'], restored['draft']['entries'])
        self.assertFalse(restored['closure_available'])
        self.assertEqual('open', debt.status)
        # The supplied sealed cause was created explicitly for this fixture.
        # Nothing maps the conditional work to an accepted debt in the application.
        self.assertTrue(restored['source_ai_influenced'])


if __name__ == "__main__":
    unittest.main()
