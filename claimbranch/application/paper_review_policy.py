"""Owned, in-memory proportional review for the cumulative paper candidate.

This adapter is independent of the TUI and old sealed reviews. Registered
origins are unverified candidate source references, not proof of typed provider
adoption. Nothing here can authorize an operation, open debt or persist work.
"""
from dataclasses import asdict
from datetime import datetime, timezone
import hashlib
from threading import RLock

from claimbranch.core.canonical import ContractError, canonical_bytes, decode, digest, identifier
from claimbranch.core.paper_changes import AmendmentLineage, amendment_schema
from claimbranch.core.paper_commit import COMMIT, PaperCommitCandidate
from claimbranch.core.paper_operation import (OPERATION, REVIEW, PaperOperationCandidate,
                                              PaperOperationReview, check_lifetime)
from claimbranch.core.paper_record_transition import TRANSITION, PaperRecordTransition
from claimbranch.core.research_history import ResearchHistory
from claimbranch.core.research_schema import HASH, ID, PAPER_LIMITS, array, normalize, obj
from claimbranch.core.review import Contribution, Judgment
from claimbranch.core.review_policy import (ASSESSMENT, DECISION, ENTRY, RULES,
                                          ReviewAssessment, requirements)
from .paper_service import PaperService
from .paper_branch import continue_judgment
from .paper_understanding import contextual_topics


def _judgment(value):
    return Judgment(value['project_id'], value['episode_id'], value['text'], value['rationale'],
                    tuple(Contribution(**item) for item in value['history']))


class PaperReviewPolicy:
    def __init__(self, history, *, episode_id):
        if type(history) is not ResearchHistory or history.schema_version != 3:
            raise ContractError('review policy requires cumulative candidate history')
        identifier(episode_id)
        self._history, self._episode = history, episode_id
        self._project = decode(history.seed)['project_id']
        self._service = PaperService(history)
        self._origins = {}
        self._prepared = None
        self._sealed_operation = None
        self._sealed_record_transition = None
        self._lock = RLock()
        self._require_active()

    def _require_active(self):
        if self._service.episodes()['active_episode_id'] != self._episode:
            raise ContractError('review policy requires the active paper episode')

    def work_sources(self):
        """Export immutable candidate sources, separately from any review seal."""
        with self._lock:
            return self._history, self._episode, tuple(self._origins[key] for key in sorted(self._origins))

    @classmethod
    def from_work_sources(cls, history, *, episode_id, origins=()):
        """Reopen unaccepted work with no prepared assessment or current seal."""
        result = cls(history, episode_id=episode_id)
        if type(origins) not in (tuple, list) or len(origins) > 64:
            raise ContractError('bounded candidate origin registry required')
        for origin in origins:
            if type(origin) is not AmendmentLineage:
                raise ContractError('typed candidate origin required')
            checked = AmendmentLineage.restore(origin.payload)
            value = decode(checked.payload)
            if (value['project_id'], value['episode_id']) != (result._project, episode_id):
                raise ContractError('candidate origin belongs to another work context')
            key = checked.amendment['id']
            if key in result._origins:
                raise ContractError('duplicate candidate origin')
            result._origins[key] = checked
        return result

    def revise_amendment(self, amendment, *, sources=()):
        """Keep origin through later manual edits; invalid input leaves it intact."""
        with self._lock:
            self._require_active()
            record = normalize(amendment, amendment_schema()['items'])
            previous = self._origins.get(record['id'])
            if previous is None and len(self._origins) >= 64:
                raise ContractError('amendment lineage capacity reached')
            lineage = (previous.revise(record, sources=sources) if previous else
                       AmendmentLineage.start(self._project, self._episode, record, sources=sources))
            self._origins[record['id']] = lineage
            return lineage

    def _records(self, ids):
        ids = normalize(ids, array(ID, 64, unique=True))
        if any(key not in self._origins for key in ids):
            raise ContractError('unknown registered amendment')
        return [self._origins[key].amendment for key in ids]

    def _check_judgment(self, judgment):
        if judgment is not None:
            if type(judgment) is not Judgment or (judgment.project_id, judgment.episode_id) != (self._project, self._episode):
                raise ContractError('judgment belongs to another paper context')
            # Reconstruct, rather than treating an arbitrary dataclass as proof.
            return _judgment(decode(canonical_bytes(asdict(judgment))))
        return None

    def _prepare(self, action, ref, ids, selected, judgment):
        with self._lock:
            descriptor = (action, ref, tuple(normalize(ids, array(ID, 64, unique=True))),
                          tuple(normalize(selected, array(ID, 64, unique=True))), self._check_judgment(judgment))
            assessment = self._build(*descriptor)
            if self._prepared != (descriptor, assessment):
                self._sealed_operation = None
            self._prepared = (descriptor, assessment)
            return assessment

    def capture(self, ref, amendment_ids, *, judgment=None):
        return self._prepare('capture-draft', ref, amendment_ids, [], judgment)

    def record(self, ref, amendment_ids, selected_ids, judgment):
        return self._prepare('record-interpretation', ref, amendment_ids, selected_ids, judgment)

    def merge(self, selected_ids):
        return self._prepare('apply-selected-merge', 'alternative', [], selected_ids, None)

    def _build(self, action, ref, ids, selected, judgment):
        self._require_active()
        if action == 'record-interpretation':
            source_ref = 'alternative' if 'alternative' in dict(self._history.heads) else 'main'
            if ref != source_ref:
                raise ContractError('record review must use the existing alternative source')
        view = self._service.query(ref, episode_id=self._episode)
        source_view = self._history.view(ref, episode_id=self._episode)
        sources = source_view['judgments']
        inherited_ai = any(_judgment(source).ai_influenced for source in sources)
        records = self._records(list(ids))
        topics, selection = [], {key: [] for key in ('selected', 'required', 'omitted',
                                                    'existing_references', 'evidence_references')}
        if action == 'capture-draft':
            science = self._service.project_draft(ref, records, episode_id=self._episode)
            included = set(ids)
        else:
            if action == 'record-interpretation':
                if judgment is None:
                    raise ContractError('record review requires a complete judgment')
                judgment = continue_judgment(source_view['judgment'] if ref == 'alternative' else None, judgment)
                science = self._service.preview_changes({
                    'schema_version': 1, 'project_id': self._project, 'episode_id': self._episode,
                    'ref': ref, 'view_digest': view['digest'], 'draft_id': 'review-policy',
                    'draft_revision': 0, 'amendments': records, 'selected_ids': list(selected)}, judgment)
            else:
                science = self._service.preview_merge(list(selected), episode_id=self._episode)
                judgment = _judgment(science['provenance']['judgment'])
            selection = science['selection']
            included = set(selection['selected']) | set(selection['required'])
            records = [item['after'] for item in science['amendments'] if item['id'] in included]

        records_by_id = {record['id']: record for record in records}
        origins = []
        for key in sorted(included):
            lineage = self._origins.get(key)
            if lineage:
                if records_by_id.get(key) != lineage.amendment:
                    raise ContractError('amendment lineage does not match the reviewed record')
                origins.append(lineage)
        lineages = [{'record_id': item.amendment['id'], 'digest': item.digest} for item in origins]
        ai = inherited_ai or bool(judgment and judgment.ai_influenced) or any(item.ai_influenced for item in origins)
        impact, target, requirement = requirements(action, ai_influenced=ai)
        if requirement == 'contextual-explanation':
            original = {**science['graphs']['after'],
                        'digest': digest({'science_digest': science['digest'], 'lineages': lineages, 'rules_version': RULES})}
            topics = contextual_topics({'original': original, 'work': {'selection': selection, **science['impact']}})
        value = normalize({'schema': 'claimbranch.paper-review-assessment/v1', 'rules_version': RULES,
            'project_id': self._project, 'episode_id': self._episode, 'action': action,
            'impact': impact, 'target_ref': target, 'source_ref': ref, 'requirement': requirement,
            'history_digest': view['history_digest'], 'view_digest': view['digest'], 'science_digest': science['digest'],
            'selection': selection, 'judgment_digest': digest(asdict(judgment)) if judgment else None,
            'source_judgment_digests': sorted(digest(source) for source in sources),
            'rationale': judgment.rationale if judgment else None,
            'inherited_ai': inherited_ai, 'ai_influenced': ai, 'lineages': lineages,
            'topics': topics, 'topics_digest': digest(topics),
            'authority': 'unaccepted-assessment', 'authorization_verified': False, 'acceptance_available': False}, ASSESSMENT)
        return ReviewAssessment(canonical_bytes(value), digest(value))

    def _current(self, assessment):
        if type(assessment) is not ReviewAssessment or self._prepared is None:
            raise ContractError('owned prepared review assessment required')
        descriptor, prepared = self._prepared
        if assessment != prepared or self._build(*descriptor) != prepared:
            raise ContractError('review assessment is stale or changed')
        return descriptor

    @staticmethod
    def _decision(assessment, disposition, entries):
        value = decode(assessment.payload)
        if type(entries) not in (tuple, list):
            raise ContractError('bounded explanation entries required')
        entries = normalize(list(entries), array(ENTRY, 3))
        requirement = value['requirement']
        if disposition == 'answered' and requirement == 'contextual-explanation':
            if [entry['topic_id'] for entry in entries] != [topic['id'] for topic in value['topics']]:
                raise ContractError('answers must reference every exact owned topic in order')
            if any(not entry['text'].strip() and not entry['reuse_rationale'] for entry in entries):
                raise ContractError('an answer or explicit rationale reference is required')
            if any(entry['reuse_rationale'] for entry in entries) and not value['rationale']:
                raise ContractError('there is no human rationale to reuse')
        elif (entries or disposition not in ('not-required', 'deferred', 'not-now')
              or disposition == 'deferred' and requirement != 'contextual-explanation'
              or disposition == 'not-required' and requirement == 'contextual-explanation'):
            raise ContractError('explanation disposition does not match the operation requirement')
        return normalize({'schema': 'claimbranch.paper-review-decision/v1', 'assessment_digest': assessment.digest,
            'disposition': disposition, 'entries': entries,
            'understanding_debt': 'opens-if-accepted' if disposition == 'deferred' else 'none',
            'authority': 'unaccepted-review', 'authorization_verified': False, 'acceptance_available': False}, DECISION)

    def finish(self, assessment, *, disposition, entries=()):
        """Record an unaccepted disposition against the current owned assessment.

        Partial explanation belongs to its separate draft; this only records
        an explicit completed answer, deferral or Not now. No comprehension test.
        """
        with self._lock:
            self._current(assessment)
            result = self._decision(assessment, disposition, entries)
            if self._sealed_operation and decode(self._sealed_operation.payload)['decision'] != result:
                self._sealed_operation = None
            return {**result, 'digest': digest(result)}

    def prepare_operation(self, assessment, *, disposition, operation_id, manuscript_digest,
                          session_nonce, sealed_at, expires_at, now, entries=(), parent_review_digest=None,
                          bind_origins=False):
        """Seal exactly the current owned review, without signing or accepting it."""
        with self._lock:
            descriptor = self._current(assessment)
            if type(bind_origins) is not bool or bind_origins and descriptor[0] != 'record-interpretation':
                raise ContractError('origin-bound sealing requires an interpretation record')
            origins = tuple(self._origins[key] for key in sorted(self._origins))
            review = self._operation_review(descriptor, assessment, disposition=disposition, entries=entries,
                operation_id=operation_id, manuscript_digest=manuscript_digest, session_nonce=session_nonce,
                sealed_at=sealed_at, expires_at=expires_at, now=now, parent_review_digest=parent_review_digest,
                origin_registry_digest=digest([decode(o.payload) for o in origins]) if bind_origins else None)
            transition = self._replay_record(review, origins) if bind_origins else None
            self._sealed_operation = review
            self._sealed_record_transition = transition
            return review

    def _operation_review(self, descriptor, assessment, *, disposition, entries, operation_id,
                          manuscript_digest, session_nonce, sealed_at, expires_at, now, parent_review_digest,
                          origin_registry_digest=None):
        action, ref, ids, selected, judgment = descriptor
        if action == 'capture-draft' or disposition == 'not-now':
            raise ContractError('capture and Not now cannot create an operation request')
        check_lifetime(sealed_at, expires_at, now)
        self._history.check_operation_identity(operation_id)
        operation_ids = [operation_id]
        if action == 'record-interpretation' and 'alternative' not in dict(self._history.heads):
            operation_ids.append(operation_id + '-branch')
            self._history.check_operation_identity(operation_ids[-1])
        if any(key in self._origins for key in operation_ids):
            raise ContractError('operation identity conflicts with an owned amendment draft')
        if len(self._history.commands) + len(operation_ids) > PAPER_LIMITS['commands']:
            raise ContractError('paper operation capacity reached')
        created_at = datetime.fromtimestamp(sealed_at, timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')
        if self._history.commands and created_at < decode(self._history.commands[-1])['created_at']:
            raise ContractError('operation clock moved backwards')
        value = decode(assessment.payload)
        decision = self._decision(assessment, disposition, entries)
        source_judgments = self._history.view(ref, episode_id=self._episode)['judgments']
        lineages = [decode(self._origins[item['record_id']].payload) for item in value['lineages']]
        if action == 'record-interpretation':
            _, branch = self._service.branch_candidate({
                'schema_version': 1, 'project_id': self._project, 'episode_id': self._episode,
                'ref': ref, 'view_digest': value['view_digest'], 'draft_id': 'review-policy',
                'draft_revision': 0, 'amendments': self._records(list(ids)), 'selected_ids': list(selected)},
                judgment, operation_id=operation_id, created_at=created_at)
            commands = branch['commands']
            effect = {**commands[-1]['payload'],
                      'branch_operation_id': commands[0]['id'] if len(commands) == 2 else None}
        else:
            if action != 'apply-selected-merge' or ref != 'alternative' or ids or judgment is not None:
                raise ContractError('merge preparation must name only the owned selection')
            science = self._service.preview_merge(list(selected), episode_id=self._episode)
            effect = {'selected_ids': science['selection']['selected'],
                      'changes': [item['after'] for item in science['amendments'] if item['disposition'] != 'omitted'],
                      'judgment': science['provenance']['judgment']}
        operation = normalize({'schema': 'claimbranch.paper-operation/v1', 'id': operation_id,
            'project_id': self._project, 'episode_id': self._episode, 'action': action,
            'created_at': created_at, 'expected_heads': dict(self._history.heads),
            'evidence_watermark': self._history.watermark, 'source_history_digest': value['history_digest'],
            'assessment_digest': assessment.digest, 'decision_digest': digest(decision),
            'provenance_digest': digest({'source_judgments': source_judgments, 'lineages': lineages,
                                         'judgment': effect['judgment']}), 'effect': effect}, OPERATION)
        review = normalize({'schema': ('claimbranch.paper-operation-review/v2' if origin_registry_digest is not None
                                      else 'claimbranch.paper-operation-review/v1'),
            **({'origin_registry_digest': origin_registry_digest} if origin_registry_digest is not None else {}),
            'operation': operation, 'operation_digest': digest(operation), 'assessment': value, 'decision': decision,
            'lineages': lineages, 'source_judgments': source_judgments,
            'preparation': {'action': action, 'ref': ref, 'amendment_ids': list(ids),
                            'selected_ids': list(selected), 'judgment': asdict(judgment) if judgment else None},
            'manuscript_digest': manuscript_digest, 'session_nonce': session_nonce,
            'sealed_at': sealed_at, 'expires_at': expires_at, 'parent_review_digest': parent_review_digest,
            'authority': 'unaccepted-review', 'authorization_verified': False, 'acceptance_available': False}, REVIEW)
        return PaperOperationReview(canonical_bytes(review), digest(review))

    def restore_operation(self, raw, *, manuscript_digest, session_nonce, now):
        """Rederive from owned sources; never enroll embedded origins or draft state."""
        with self._lock:
            value = normalize(decode(raw), REVIEW)
            if canonical_bytes(value) != raw:
                raise ContractError('operation review requires canonical bytes')
            bindings = normalize({'manuscript_digest': manuscript_digest, 'session_nonce': session_nonce},
                                 obj(manuscript_digest=HASH, session_nonce=ID))
            if any(value[key] != item for key, item in bindings.items()):
                raise ContractError('operation review manuscript or session changed')
            check_lifetime(value['sealed_at'], value['expires_at'], now)
            preparation = value['preparation']
            descriptor = (preparation['action'], preparation['ref'], tuple(preparation['amendment_ids']),
                          tuple(preparation['selected_ids']),
                          self._check_judgment(_judgment(preparation['judgment'])) if preparation['judgment'] else None)
            assessment = self._build(*descriptor)
            registry_digest = None
            if value['schema'] == 'claimbranch.paper-operation-review/v2':
                snapshot = (self._sealed_record_transition.origins
                            if self._sealed_record_transition is not None and self._sealed_operation is not None
                            and self._sealed_operation.payload == raw else
                            tuple(self._origins[key] for key in sorted(self._origins)))
                registry_digest = digest([decode(o.payload) for o in snapshot])
                if registry_digest != value['origin_registry_digest']:
                    raise ContractError('review origin registry snapshot changed')
            expected = self._operation_review(descriptor, assessment,
                disposition=value['decision']['disposition'], entries=value['decision']['entries'],
                operation_id=value['operation']['id'], manuscript_digest=manuscript_digest, session_nonce=session_nonce,
                sealed_at=value['sealed_at'], expires_at=value['expires_at'], now=now,
                parent_review_digest=value['parent_review_digest'], origin_registry_digest=registry_digest)
            if expected.payload != raw:
                raise ContractError('operation review source, policy or effects changed')
            return expected

    def operation_candidate(self, review, *, manuscript_digest, session_nonce, now):
        """Return a request requiring a future trusted gateway and foreground receipt."""
        with self._lock:
            if type(review) is not PaperOperationReview:
                raise ContractError('typed paper operation review required')
            if review != self._sealed_operation:
                raise ContractError('operation review is no longer the current owned seal')
            current = self.restore_operation(review.payload, manuscript_digest=manuscript_digest,
                                             session_nonce=session_nonce, now=now)
            if current != review:
                raise ContractError('operation review digest changed')
            value = decode(current.payload)
            assessment = ReviewAssessment(canonical_bytes(value['assessment']), digest(value['assessment']))
            action, ref, ids, selected, judgment = self._current(assessment)
            preparation = {'action': action, 'ref': ref, 'amendment_ids': list(ids),
                           'selected_ids': list(selected), 'judgment': asdict(judgment) if judgment else None}
            if canonical_bytes(preparation) != canonical_bytes(value['preparation']):
                raise ContractError('operation review preparation is no longer current')
            operation = value['operation']
            return PaperOperationCandidate(canonical_bytes(operation), digest(operation), current.digest)

    def commit_candidate(self, review, *, manuscript_digest, session_nonce, now):
        """Rederive one conditional transaction without appending a legacy command.

        Retain full amendment origins and contextual explanation disposition.
        Forecast heads and debts together, but grant no accepted-store handle
        or authorization. The native gateway must independently load accepted
        sources and consume fresh private consent before these effects exist.
        """
        with self._lock:
            self.operation_candidate(review, manuscript_digest=manuscript_digest,
                                     session_nonce=session_nonce, now=now)
            value = decode(review.payload)
            operation = value['operation']
            heads = dict(self._history.heads)
            target = 'main' if operation['action'] == 'apply-selected-merge' else 'alternative'
            heads[target] = operation['id']
            debts = []
            if target == 'main':
                kinds = ['manuscript']
                if value['decision']['understanding_debt'] == 'opens-if-accepted':
                    kinds.append('understanding')
                for kind in kinds:
                    identity = {'kind': kind, 'project_id': operation['project_id'],
                                'episode_id': operation['episode_id'],
                                'cause_operation_id': operation['id'], 'cause_review_digest': review.digest}
                    debts.append({**identity, 'id': 'debt-' + digest(identity),
                        'cause_main_head': operation['id'], 'evidence_watermark': self._history.watermark,
                        'anchor_id': decode(self._history.seed)['anchor_id'] if kind == 'manuscript' else None,
                        'manuscript_digest': manuscript_digest if kind == 'manuscript' else None,
                        'topics_digest': value['assessment']['topics_digest'] if kind == 'understanding' else None,
                        'status': 'opens-if-accepted'})
            result = normalize({'schema': 'claimbranch.paper-commit-candidate/v1',
                'review': value, 'review_digest': review.digest, 'resulting_heads': heads, 'debt_openings': debts,
                'authority': 'unaccepted-commit-candidate', 'authorization_verified': False,
                'acceptance_available': False, 'accepted_writes': 0, 'accepted_debts_created': 0}, COMMIT)
            return PaperCommitCandidate(canonical_bytes(result), digest(result))

    def restore_commit_candidate(self, raw, review, *, manuscript_digest, session_nonce, now):
        """Inspect only against this owner's current seal; never install consent."""
        with self._lock:
            value = normalize(decode(raw), COMMIT)
            if canonical_bytes(value) != raw:
                raise ContractError('commit candidate requires canonical bytes')
            current = self.commit_candidate(review, manuscript_digest=manuscript_digest,
                                            session_nonce=session_nonce, now=now)
            if current.payload != raw:
                raise ContractError('commit candidate effects, debt or source bindings changed')
            return current

    def record_transition(self, review, *, manuscript_digest, session_nonce, now):
        """Replay a reviewed alternative record while retaining complete origins.

        Return new candidate history; do not install it or change this owner's
        seal/source. In particular, merge/debt/explanation semantics are not
        translated into the legacy history format. No receipt is consumed.
        """
        with self._lock:
            self.operation_candidate(review, manuscript_digest=manuscript_digest,
                                     session_nonce=session_nonce, now=now)
            value = decode(review.payload)
            operation = value['operation']
            if operation['action'] != 'record-interpretation':
                raise ContractError('only alternative recording has a replay transition; merge requires its full policy log')
            if self._sealed_record_transition is None or decode(self._sealed_record_transition.payload)['review'] != value:
                raise ContractError('owned sealed record transition required')
            return self._sealed_record_transition

    def _replay_record(self, review, origins):
        """Validate record science and its complete snapshot budget before sealing."""
        value = decode(review.payload)
        operation = value['operation']
        if operation['action'] != 'record-interpretation':
            raise ContractError('record effect required')
        if (value['schema'] != 'claimbranch.paper-operation-review/v2'
                or value['origin_registry_digest'] != digest([decode(o.payload) for o in origins])):
            raise ContractError('full origin-bound v2 record review required')
        effect = operation['effect']
        history, commands = self._history, []

        def append(kind, key, payload):
            nonlocal history
            command = {'schema_version': 3, 'id': key, 'project_id': self._project,
                'episode_id': self._episode, 'created_at': operation['created_at'],
                'operation_type': kind, 'expected_heads': dict(history.heads),
                'evidence_watermark': history.watermark, 'payload': payload}
            history = history.append(command)
            commands.append(command)

        if effect['branch_operation_id'] is not None:
            append('create-reasoning-branch', effect['branch_operation_id'], {})
        append('record-interpretation', operation['id'], {key: effect[key] for key in ('changes', 'judgment')})
        result = normalize({'schema': 'claimbranch.paper-record-transition/v1',
            'review': value, 'review_digest': review.digest,
            'source_history_digest': hashlib.sha256(self._history.manifest()).hexdigest(),
            'result_history_digest': hashlib.sha256(history.manifest()).hexdigest(),
            'commands': commands, 'origins': [decode(origin.payload) for origin in origins],
            'authority': 'unaccepted-record-transition', 'authorization_verified': False,
            'acceptance_available': False, 'accepted_writes': 0, 'accepted_debts_created': 0}, TRANSITION)
        return PaperRecordTransition(canonical_bytes(result), digest(result), self._history, history, origins)

    @classmethod
    def from_record_transition(cls, transition, *, expected_review_digest):
        """Continue a full candidate bundle, refusing missing/substituted origins.

        Historical replay uses the original sealed time only to verify science.
        The expected digest must come from an independently retained review,
        not from the untrusted bundle. This verifies integrity, not authority.
        Returned work has no current assessment, seal or human authorization.
        Bare legacy history cannot substitute for this provenance envelope.
        """
        if type(transition) is not PaperRecordTransition:
            raise ContractError('typed full record transition required')
        value = normalize(decode(transition.payload), TRANSITION)
        normalize({'digest': expected_review_digest}, obj(digest=HASH))
        if (value['review_digest'] != expected_review_digest
                or digest(value['review']) != expected_review_digest):
            raise ContractError('record transition does not match the independently retained review')
        if (canonical_bytes(value) != transition.payload or digest(value) != transition.digest
                or type(transition.source_history) is not ResearchHistory
                or type(transition.history) is not ResearchHistory
                or type(transition.origins) is not tuple
                or any(type(origin) is not AmendmentLineage for origin in transition.origins)
                or value['origins'] != [decode(origin.payload) for origin in transition.origins]):
            raise ContractError('record transition history or origin binding changed')
        episode = value['review']['operation']['episode_id']
        owner = cls.from_work_sources(transition.source_history, episode_id=episode, origins=transition.origins)
        reviewed = value['review']
        review = owner.restore_operation(canonical_bytes(reviewed),
            manuscript_digest=reviewed['manuscript_digest'], session_nonce=reviewed['session_nonce'],
            now=reviewed['sealed_at'])
        if owner._replay_record(review, transition.origins) != transition:
            raise ContractError('record transition commands, source or result changed')
        return cls.from_work_sources(transition.history, episode_id=episode, origins=transition.origins)

    def restore_record_transition(self, raw, review, *, manuscript_digest, session_nonce, now):
        """Recheck current science/seal and compare its fixed registry snapshot."""
        with self._lock:
            value = normalize(decode(raw), TRANSITION)
            if canonical_bytes(value) != raw:
                raise ContractError('record transition requires canonical bytes')
            current = self.record_transition(review, manuscript_digest=manuscript_digest,
                                             session_nonce=session_nonce, now=now)
            if current.payload != raw:
                raise ContractError('record transition effects, source or origins changed')
            return current

    def update_source(self, history):
        """Keep known origins but revoke review freshness when owned history grows."""
        with self._lock:
            if (type(history) is not ResearchHistory or history.seed != self._history.seed
                    or history.commands[:len(self._history.commands)] != self._history.commands):
                raise ContractError('review source must extend its owned history')
            self._history, self._service = history, PaperService(history)
