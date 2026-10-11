"""Volatile terminal adapter over paper drafting and selected-change review."""
from .tui_retention import recovery_copy
from copy import deepcopy
import time

from claimbranch.core.canonical import ContractError, bounded_text
from claimbranch.core.paper_context import FIELDS


FROZEN_CRITIQUE = (
    'Before generalizing this claim, distinguish the measured conditions from '
    'untested conditions. Check which observations support each comparison and '
    'whether the planned replication could change that interpretation.'
)
from .paper_review_writing_snapshot import EDIT_FIELDS
FIELD_LABELS = {'role': 'Claim level', 'parent_ids': 'Parent in the argument',
                'observation_ids': 'Observations interpreted',
                'statement': 'Claim statement', 'scope': 'Scope / conditions',
                'source_id': 'From / source', 'target_id': 'To / claim',
                'edge_type': 'Scientific relationship', 'rationale': 'Why this connection?',
                'objective': 'Experiment question / objective', 'claim_id': 'Claim to test',
                'conditions': 'Experimental conditions', 'metric.name': 'Metric name',
                'metric.definition': 'Measurement definition', 'metric.unit': 'Measurement unit',
                'metric.comparison': 'Comparison / baseline'}
REVIEW_LIMIT = 'Draft kept locally. Shorten each field to 16,384 UTF-8 bytes before AI or scientific review.'


class TerminalReview:
    def __init__(self, app, history):
        self.app, self.history = app, history
        self.sessions, self.candidate_works = {}, {}
        self.candidate_inputs = {}
        self.buffers = {}
        # Unfinished inputs have independent original-context bindings; no live seal.
        self.unfinished, self.unfinished_basis = {}, {}
        self.buffer_notices = {}
        self.pending = []

    def change_text(self, change, graphs):
        """Keep exact field differences readable, including nested measurement fields."""
        before = change['before']['body'] if change['before'] else {}
        after = change['after']['body'] if change['after'] else {}
        nodes = {phase: {node['id']: node for node in graph['nodes']} for phase, graph in graphs.items()}

        def describe(field, value, phase):
            if field in ('source_id', 'target_id', 'claim_id'):
                content = nodes[phase].get(value, {}).get('content', {})
                return self.label(value) + ' / ' + (content.get('statement') or content.get('objective') or value)
            if field in ('parent_ids', 'observation_ids', 'basis_ids'):
                return '\n'.join(describe('claim_id', key, phase) for key in value)
            if field == 'status' and value == 'planned':
                return 'Planned / not run'
            return str(value)

        result = []
        for field, value in after.items():
            values = [(field + '.' + key, before.get(field, {}).get(key), item)
                      for key, item in value.items()] if field == 'metric' else [(field, before.get(field), value)]
            for name, old, new in values:
                if old == new:
                    continue
                title = ('Interpretation statement' if name == 'statement' and change['after']['kind'] == 'interpretation'
                         else FIELD_LABELS.get(name, name.replace('_', ' ')))
                result.append(title.upper() + ('\nBefore: ' + describe(name, old, 'before') if before else '')
                              + '\nProposed: ' + describe(name, new, 'after'))
        return '\n\n'.join(result) or 'No content difference.'

    @property
    def key(self):
        return self.app.work_key()

    def candidates(self):
        self.session()
        if self.key not in self.candidate_works:
            self.candidate_works[self.key] = self.app.paper.candidates(
                *self.app.full_context(self.key))
        return self.candidate_works[self.key]

    @property
    def amendments(self):
        return {key: work.records for key, work in self.candidate_works.items()}

    @property
    def selected(self):
        return {key: work.selected for key, work in self.candidate_works.items()}

    def label(self, record_id):
        if record_id in self.app.nodes:
            return self.app.node_label(record_id)
        work = self.candidate_works.get(self.key)
        return work.alias(record_id) if work and record_id in work.records else record_id

    def session(self):
        if self.key not in self.sessions:
            session = self.app.paper.draft(*self.app.full_context(self.key))
            draft = self.app.drafts.get(self.key, {'text': '', 'rationale': ''})
            self.sessions[self.key] = session
            self.edit_draft(draft)
        return self.sessions[self.key]

    def edit_draft(self, draft):
        try:
            session = self.session()
        except ContractError as error:
            self.buffers[self.key] = dict(draft)
            self.buffer_notices[self.key] = 'Manual draft kept. Review unavailable: ' + str(error)
            return False
        try:
            fits = all(len(text.encode('utf-8')) <= 16_384 for text in draft.values())
        except UnicodeError:
            fits = False
        if not fits:
            session.not_now()
            self.buffers[self.key] = dict(draft)
            self.buffer_notices[self.key] = REVIEW_LIMIT
            return False
        session.edit(**draft)
        self.buffers.pop(self.key, None)
        self.buffer_notices.pop(self.key, None)
        return True

    def require_current_draft(self):
        self.session()
        if self.key in self.buffers:
            raise ContractError(REVIEW_LIMIT)

    def influenced(self, key=None):
        session = self.sessions.get(key or self.key)
        return bool(session and session.state()['draft']['ai_influenced'])

    def volatile_work(self):
        if self.app.intake.has_writing():
            return True
        return self.app.paper.volatile_links or any(self.candidate_inputs.values()) or bool(self.unfinished) or self.app.branches.volatile_work() or self.app.manuscript.volatile_work() or self.app.understanding.volatile_work() or any(self.amendments.values()) or any(
            state['attempt'] or state['draft']['ai_influenced'] or state['changes_preview']
            for session in self.sessions.values() for state in (session.state(),))

    def records(self):
        return {item['id']: deepcopy(item) for item in self.app.paper.history.view(self.app.ref, episode_id=self.app.episode_id)['changes']
                if item['kind'] in EDIT_FIELDS}

    def stage(self, record_id, values):
        source = self.records().get(record_id)
        if source is None or set(values) != set(EDIT_FIELDS[source['kind']]):
            raise ContractError('Choose an existing claim, interpretation, plan or scientific relation and its editable fields.')
        for field, value in values.items():
            if field == 'scope' and value is None:
                continue
            bounded_text(value)
        if source['kind'] == 'scientific-edge' and values['edge_type'] not in ('supports', 'challenges', 'qualifies'):
            raise ContractError('Choose supports, challenges or qualifies; relation strength is not inferred.')
        record = deepcopy(self.amendments.get(self.key, {}).get(record_id) or source)
        record['body'].update(values)
        self.candidates().put(record)

    def stage_judgment(self, record_id):
        self.require_current_draft()
        record = self.records().get(record_id)
        if not record or record['kind'] != 'interpretation':
            raise ContractError("Choose this episode's interpretation to use your judgment wording.")
        owners = self.history.view(self.app.ref, episode_id=self.app.episode_id).get('interpretation_episode_ids', {})
        if owners and owners.get(record_id) != self.app.episode_id:
            raise ContractError('Choose the interpretation owned by this episode.')
        self.stage(record_id, {'statement': self.app.draft()['text']})

    def toggle(self, record_id):
        if record_id not in self.amendments.get(self.key, {}):
            raise ContractError('Edit the change before including it in review.')
        self.candidates().toggle(record_id)

    def changes_request(self):
        self.require_current_draft()
        self.candidates().require_current()
        session = self.session()
        state = session.state()
        return {'schema_version': 1, **state['paper'],
            'draft_id': state['draft_id'], 'draft_revision': state['revision'],
            'amendments': list(self.amendments.get(self.key, {}).values()),
            'selected_ids': sorted(self.selected.get(self.key, set()))}

    def prepare_changes(self):
        from .tui_retention import personal
        work = self.candidate_works.get(self.key)
        if personal(self.app) and work and any(origin.ai_influenced for origin in work.origins.values()):
            raise ContractError('AI item origins require the personal consequence comparison; use Record selected reasoning personally from actions.')
        reason = self.interpretation_review_reason()
        if reason:
            raise ContractError(reason)
        return self.session().prepare_changes(self.changes_request())

    def interpretation_review_reason(self):
        work = self.candidate_works.get(self.key)
        if work and any(item['kind'] == 'interpretation' and item['body']['statement'] != self.app.draft()['text']
                        for item in work.records.values()):
            return ('Kept interpretation and judgment wording must match, even when omitted. '
                    'Open argument drafts: J reuses a new interpretation; u unkeeps it for later, '
                    'or edit its wording. Your text is retained.')
        return ''

    def finish_changes(self, digest, disposition, answers):
        self.candidates().require_current()
        return self.session().finish_changes_review(digest, disposition=disposition, answers=answers)

    def prepare_ai(self, record_ids, *, include_draft=False):
        self.require_current_draft()
        view = self.app.view
        ids = set(record_ids)
        if len(ids) != len(record_ids):
            raise ContractError('Select each context record once.')
        selections = []
        for key in record_ids:
            node = self.app.nodes.get(key)
            if node is None or node['kind'] not in FIELDS:
                raise ContractError('This record cannot enter the scoped paper context.')
            selections.append({'record_id': key, 'fields': list(FIELDS[node['kind']])})
        return self.session().prepare_request({'schema_version': 1,
            'project_id': view['project_id'], 'episode_id': view['episode_id'],
            'ref': self.app.ref, 'view_digest': view['digest'], 'purpose': 'compare-evidence',
            'selections': selections,
            'scientific_edge_ids': [edge['record_id'] for edge in view['relations']
                if edge['scientific'] and edge['source_id'] in ids and edge['target_id'] in ids]},
            include_draft=include_draft)['outbound']

    def begin_ai(self, outbound):
        request_id = outbound['request']['request_id']
        state = self.session().begin_proposal(request_id, outbound['digest'])
        self.pending.append((self.key, request_id, time.monotonic() + .7))
        return state

    def complete_ai(self, key, request_id):
        state = self.sessions[key].complete_proposal(request_id)
        self.pending = [item for item in self.pending if item[:2] != (key, request_id)]
        return state

    def poll(self):
        changed = False
        for key, request_id, deadline in list(self.pending):
            if time.monotonic() >= deadline:
                state = self.complete_ai(key, request_id)
                if key == self.key:
                    self.app.message = ('Offline example ready: w to inspect; nothing adopted.' if state['proposal']
                                        else 'Late offline response retained as a trace; current draft unchanged.')
                changed = True
        return changed

    def adopt_ai(self, proposal_id=None):
        self.require_current_draft()
        session = self.session()
        proposal = session.state()['proposal']
        if not proposal:
            raise ContractError('No current proposal to adopt.')
        return session.use_proposal(proposal['id'] if proposal_id is None else proposal_id)

    def restore_before_ai(self):
        before = self.session().state()['before_proposal']
        if before is None:
            raise ContractError('There is no replaced draft in this session.')
        state = self.session().edit(**before)
        self.buffers.pop(self.key, None)
        return state

    def not_now(self):
        return self.session().not_now()

    def lines(self, width=72):
        from .tui_subject import subject_summary
        from .tui_work_recovery import enabled
        saved_origin = enabled(self.app)
        try:
            state = self.session().state()
        except ContractError as error:
            return subject_summary(self.app, width) + [('', 'body'), ('WORK / REVIEW LIMIT', 'heading'), (str(error), 'warning'),
                    ('Manual notes and judgments remain editable; existing reviews are retained.', 'body'),
                    (self.app.draft()['text'], 'body'), (self.app.draft()['rationale'], 'body')]
        draft, proposal = {**state['draft'], **self.app.draft()}, state['proposal']
        lines = []

        def section(title, text, style='body'):
            lines.extend([(title, 'heading'), (text, style), ('', 'body')])

        prepared = self.session().get_changes_preview()
        reviewed = self.session().get_changes_review()
        if reviewed:
            lines.append(('REVIEW COMPLETE / nothing accepted', 'warning'))
        elif prepared:
            lines.append(('SCIENTIFIC CHANGE REVIEW / G graphs · Enter review', 'accent'))
        if self.key in self.buffers:
            lines.append(('REVIEW LENGTH LIMIT / shorten before AI or review; e edits', 'warning'))
        if any(key[:-1] == self.key for key in self.unfinished):
            lines.append(('UNFINISHED WRITING / U resumes · ' + (recovery_copy(self.app, 'encrypted recovery') if saved_origin else 'session only'), 'warning'))
        if draft['ai_influenced']:
            lines.append((recovery_copy(self.app, 'AI ORIGIN / encrypted judgment checkpoint') if saved_origin else 'SESSION-ONLY AI HISTORY / not checkpointed', 'warning'))
        if state['attempt']:
            lines.append(('OFFLINE AI / ' + state['attempt']['state'].upper() + ' · fixed example', 'muted'))
        if self.amendments.get(self.key) or self.candidate_inputs.get(self.key):
            lines.append(('ARGUMENT DRAFTS / ' + (recovery_copy(self.app, 'encrypted recovery') if saved_origin else 'session only') + ' · ; → Open argument drafts', 'accent'))
        if self.candidate_inputs.get(self.key):
            lines.append(('UNKEPT CANDIDATE FIELDS / excluded from graph and review', 'warning'))
        if len(self.app.paper.work_nodes(self.app.full_context(self.key))) > 1:
            section('LINKED JUDGMENT / ' + self.app.node_label(self.key[-1]),
                    'Linked nodes: ' + self.app.work_labels() + (recovery_copy(self.app, '. Links are included in encrypted checkpoints; other judgments remain separate.') if saved_origin else '. Links last for this session; other judgments remain separate.'), 'accent')
        lines.extend(subject_summary(self.app, width))
        lines.append(('', 'body'))
        section('YOUR JUDGMENT', draft['text'] or 'e writes a judgment; AI is optional.')
        section('WHY / EVIDENCE', draft['rationale'] or 'Add your reason in the judgment editor.')
        work = self.candidate_works.get(self.key)
        if work and any(origin.ai_influenced for origin in work.origins.values()):
            section('AI ITEM ORIGIN / separate from your judgment',
                'Chosen draft items retain AI source after human edits. ; → Inspect AI item origins reads full history. '
                'Personal recording reuses this judgment/reason and asks an explicit explanation choice.', 'warning')
        section('WORK / ' + self.app.node_label(self.key[-1]),
                '; opens named actions · e write · c changes · R review', 'accent')
        section('OPTIONAL ASSISTANCE',
                'A chooses context for a fixed offline example; no live model.' if state['ai_available'] or getattr(self.app,'offline_assistance',lambda:False)()
                else 'AI OFF. Manual writing and review remain available.', 'muted')
        if any(key[:-1] == self.key for key in self.unfinished):
            section('UNFINISHED WRITING / U resumes',
                    (recovery_copy(self.app, 'Encrypted recovery. ') if saved_origin else 'Session only. ') + 'Unkept edits are excluded from staged changes and completed reviews.', 'warning')
        if self.key in self.buffers:
            section('REVIEW LENGTH LIMIT', REVIEW_LIMIT, 'warning')
        if reviewed:
            section('REVIEW COMPLETE / SESSION ONLY',
                    'No scientific change accepted. No manuscript written.', 'warning')
            if reviewed['consequences_if_accepted']['understanding_debt']:
                section('DEFERRED UNDERSTANDING', 'If accepted later, this would leave understanding work open.', 'warning')
        if prepared:
            preview = prepared['preview']
            selection = preview['selection']
            section('SCIENTIFIC CHANGE REVIEW',
                    f"{len(selection['selected'])} selected · {len(selection['required'])} required · {len(selection['omitted'])} omitted. "
                    'G compares graphs; Enter completes review.', 'accent')
            for change in preview['amendments']:
                section(change['disposition'].upper() + ' / ' + self.label(change['id']),
                        self.change_text(change, preview['graphs']))
            impact = preview['impact']
            projected_nodes = {node['id']: node for node in preview['graphs']['after']['nodes']}
            for title, field in (('MAY NEED REVIEW', 'potentially_affected_claim_ids'),
                                 ('OUTSIDE THIS PATH', 'outside_impact_claim_ids'),
                                 ('UNCHANGED EVIDENCE', 'unchanged_evidence_ids')):
                section(title, '\n'.join(projected_nodes[key]['content'].get('statement') or
                        projected_nodes[key]['content'].get('objective') or key for key in impact[field]) or 'None')
            section('MANUSCRIPT', 'Affected anchors: ' + ', '.join(impact['potentially_affected_anchor_ids'])
                    + '. Actual source and file application remain unavailable.', 'muted')
            if preview['provenance']['ai_influenced']:
                section('AI ORIGIN', 'The selected source or your draft contains AI contributions. Completing review requires your explanation or explicit deferral.', 'warning')
        if state['attempt']:
            attempt = state['attempt']
            section('OFFLINE AI / ' + attempt['state'].upper(),
                    'Fixed example output; no model server or network request. '
                    + ('Response pending; drafting remains available.' if attempt['state'] == 'pending' and attempt['dispatched'] else
                       'A reviews another request; x cancels without discarding your draft.'), 'muted')
        if proposal:
            section('PROPOSAL / ' + ('ADOPTED' if proposal['adopted'] else 'NOT ADOPTED'), proposal['text'])
            if not proposal['adopted']:
                section('COMPARE BEFORE REPLACING', 'y compares your judgment/reason with the proposal. Enter explicitly replaces the whole judgment; Esc keeps yours and leaves the proposal available. AI origin and the prior buffer remain after replacement. ' + (recovery_copy(self.app, 'Judgment and origin are included in encrypted checkpoints; raw proposal traces remain session-only.') if saved_origin else 'AI-influenced work is not checkpointed.'), 'accent')
        if draft['ai_influenced']:
            section('AI CONTRIBUTION RETENTION' if saved_origin else 'SESSION-ONLY AI HISTORY',
                    recovery_copy(self.app, 'Encrypted checkpoints include this judgment and its adopted AI contributions; no review authority is restored.') if saved_origin else
                    'This draft and its AI origin are not saved by --draft-file. The earlier manual checkpoint stays intact.', 'warning')
        if state['before_proposal'] is not None:
            section('BEFORE ADOPTION / B compares before restoring', state['before_proposal']['text'] or '(empty judgment)')
            section('PREVIOUS REASON', state['before_proposal']['rationale'] or '(empty reason)', 'muted')
        for index, entry in enumerate(draft['contributions'], 1):
            section(f"CONTRIBUTION {index} / {entry['contributor'].upper()}", entry['text'])
            if entry.get('rationale'):
                section('REASON', entry['rationale'], 'muted')
        if not prepared and self.amendments.get(self.key):
            section('AUTHORED CHANGES / SESSION ONLY', '\n'.join(
                ('[x] ' if key in self.selected.get(self.key, set()) else '[ ] ') + self.label(key)
                for key in self.amendments[self.key]))
            section('NEXT', 'R prepares the exact change review after your judgment and reason are complete.', 'accent')
        return lines
