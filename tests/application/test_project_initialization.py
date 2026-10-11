import json
from pathlib import Path
import unittest

from claimbranch.application.project_initialization import ProjectInitialization, INITIALIZATION_REVIEW
from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from claimbranch.core.research_schema import normalize
from tests.application.test_project_work import AssociationFixture


class ProjectInitializationTests(AssociationFixture, unittest.TestCase):
    def owner(self, **changes):
        return ProjectInitialization(self.preview(), **{
            'project_id': 'project', 'title': 'New paper', 'thesis_id': 'thesis',
            'thesis': 'An unresolved argument.', **changes})

    def seal(self, owner):
        return owner.prepare_review(session_nonce='session', sealed_at=100, expires_at=400)

    def test_exact_initial_thesis_and_locations_start_without_imported_science(self):
        owner = self.owner(thesis='사람이 작성한 아직 검증되지 않은 주장.')
        review = self.seal(owner)
        shown = owner.display(review, session_nonce='session', now=100)
        self.assertEqual('사람이 작성한 아직 검증되지 않은 주장.', shown['thesis'])
        self.assertEqual(str(self.paper), shown['paper_root'])
        self.assertEqual(str(self.workspace), shown['workspace'])
        self.assertEqual([], shown['writes'])
        self.assertFalse(shown['source_fidelity_verified'])
        candidate = owner.candidate(review, session_nonce='session', now=399)
        project = candidate.project
        self.assertEqual(self.preview().payload, candidate.association.payload)
        self.assertIs(review, candidate.review)
        self.assertEqual((), project.work.history.commands)
        self.assertEqual(0, project.work.history.watermark)
        self.assertIsNone(decode(project.work.history.manifest())['active_episode_id'])
        self.assertEqual({'main': shown['initial_head']}, dict(project.work.history.heads))
        self.assertFalse(project.work.history.authorization_verified)
        self.assertEqual(self.source, self.manuscript.read_bytes())
        self.assertEqual([], list(self.workspace.iterdir()))

    def test_same_fields_on_a_new_owner_do_not_restore_a_seal(self):
        owner = self.owner()
        review = self.seal(owner)
        other = self.owner()
        with self.assertRaises(ContractError):
            other.candidate(review, session_nonce='session', now=100)
        with self.assertRaises(ContractError):
            other.restore_review(review.payload, session_nonce='session', now=100)
        self.assertEqual(review, owner.restore_review(review.payload, session_nonce='session', now=100))

    def test_forged_thesis_and_recomputed_digest_are_not_owned_review(self):
        from dataclasses import replace
        from claimbranch.core.canonical import digest
        owner = self.owner()
        review = self.seal(owner)
        value = decode(review.payload)
        value['seed']['claim_statement'] = 'A different scientific assertion.'
        value['initial_head'] = 'root-' + digest(value['seed'])
        self.assertEqual(value, normalize(value, INITIALIZATION_REVIEW))
        forged = replace(review, payload=canonical_bytes(value), digest=digest(value))
        with self.assertRaises(ContractError):
            owner.candidate(forged, session_nonce='session', now=100)

    def test_imported_commands_evidence_or_receipts_have_no_initialization_field(self):
        owner = self.owner()
        review = self.seal(owner)
        for field, content in [('commands', [{}]), ('evidence', [{}]), ('receipt', 'human'),
                               ('authorization_verified', True)]:
            value = decode(review.payload)
            value[field] = content
            with self.subTest(field=field), self.assertRaises(ContractError):
                owner.restore_review(canonical_bytes(value), session_nonce='session', now=100)

    def test_expired_changed_session_or_replaced_review_refuses(self):
        owner = self.owner()
        review = self.seal(owner)
        for nonce, now in [('other', 100), ('session', 99), ('session', 400)]:
            with self.subTest(nonce=nonce, now=now), self.assertRaises(ContractError):
                owner.candidate(review, session_nonce=nonce, now=now)
        owner.prepare_review(session_nonce='session', sealed_at=101, expires_at=401)
        with self.assertRaises(ContractError):
            owner.candidate(review, session_nonce='session', now=101)

    def test_source_or_workspace_change_invalidates_review_without_writes(self):
        owner = self.owner()
        review = self.seal(owner)
        self.manuscript.write_bytes(self.source + b'% external change\n')
        with self.assertRaises(ContractError):
            owner.candidate(review, session_nonce='session', now=100)
        self.assertEqual([], list(self.workspace.iterdir()))
        self.manuscript.write_bytes(self.source)
        owner = self.owner()
        review = self.seal(owner)
        self.workspace.rename(self.root / 'old-work')
        self.workspace.mkdir(mode=0o700)
        with self.assertRaises(ContractError):
            owner.candidate(review, session_nonce='session', now=100)

    def test_bad_lifetimes_and_aliases_cannot_prepare_initialization(self):
        for changes in [{'thesis_id': 'anchor'}, {'thesis': ''}, {'project_id': True}]:
            with self.subTest(changes=changes), self.assertRaises(ContractError):
                self.owner(**changes)
        owner = self.owner()
        for times in [(100, 100), (100, 401), (True, 300), (-1, 100)]:
            with self.subTest(times=times), self.assertRaises(ContractError):
                owner.prepare_review(session_nonce='session', sealed_at=times[0], expires_at=times[1])

    def test_failed_reprepare_revokes_previous_review(self):
        owner = self.owner()
        review = self.seal(owner)
        with self.assertRaises(ContractError):
            owner.prepare_review(session_nonce='session', sealed_at=100, expires_at=100)
        with self.assertRaises(ContractError):
            owner.candidate(review, session_nonce='session', now=100)
        with self.assertRaises(ContractError):
            owner.restore_review(review.payload, session_nonce='session', now=100)

    def test_result_keeps_reviewed_workspace_even_for_identical_science(self):
        from claimbranch.application.project_work import preview_association
        other_workspace = self.root / 'other-work'
        other_workspace.mkdir(mode=0o700)
        first = self.owner()
        second = ProjectInitialization(preview_association(self.paper, 'paper.tex', 'anchor', other_workspace),
                                       project_id='project', title='New paper', thesis_id='thesis',
                                       thesis='An unresolved argument.')
        a = first.candidate(self.seal(first), session_nonce='session', now=100)
        b = second.candidate(self.seal(second), session_nonce='session', now=100)
        self.assertEqual(a.project.payload, b.project.payload)
        self.assertNotEqual(a.association.payload, b.association.payload)
        self.assertNotEqual(a.review.digest, b.review.digest)

    def test_candidates_are_repeatable_preparations_not_one_use_receipts(self):
        owner = self.owner()
        review = self.seal(owner)
        a = owner.candidate(review, session_nonce='session', now=100)
        b = owner.candidate(review, session_nonce='session', now=101)
        self.assertEqual(a, b)
        self.assertFalse(a.project.work.history.authorization_verified)
        self.assertIs(review, owner.restore_review(review.payload, session_nonce='session', now=102))

    def test_unbounded_and_nonbyte_imports_are_rejected_before_parsing(self):
        owner = self.owner()
        review = self.seal(owner)
        for raw in [bytearray(review.payload), review.payload.decode(), b'[' * 262145]:
            with self.subTest(kind=type(raw)), self.assertRaises(ContractError):
                owner.restore_review(raw, session_nonce='session', now=100)

    def test_generated_closed_schema_matches(self):
        from claimbranch.application.project_initialization import initialization_schema
        path = Path(__file__).resolve().parents[2] / 'schemas/project-initialization-review-v1.json'
        self.assertEqual(initialization_schema(), json.loads(path.read_text()))
