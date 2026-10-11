"""Explicit personal recording over the existing bounded candidate reducers.

This is ordinary local history, never protected acceptance or signed consent.
Preview values stay in their live owner; a saved comparison cannot authorize.
"""
from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import secrets
import time

from claimbranch.core.canonical import ContractError, bounded_text, canonical_bytes, decode, digest
from claimbranch.core.research_history import ResearchHistory
from .paper_branch import judgment_value
from .paper_work_store import PaperWork
from .tui_model import TerminalWorkspace
from .tui_retention import personal, recovery_copy
from .tui_work_recovery import restore, snapshot_value, WorkReopenRequired, save_failure_message


@dataclass(frozen=True)
class PersonalPreview:
    kind: str
    binding: bytes
    history: ResearchHistory
    episode_id: str
    ref: str
    node_id: str
    fields: dict | None
    display: dict
    graphs: dict | None
    expires_at: int
    consumed_result: str | None = None
    origin_record: dict | None = None


def _binding(app):
    return canonical_bytes({'history': hashlib.sha256(app.paper.history.manifest()).hexdigest(),
                            'writing': snapshot_value(app)})


def _seal(preview):
    return canonical_bytes({'kind':preview.kind,'history':hashlib.sha256(preview.history.manifest()).hexdigest(),
        'episode':preview.episode_id,'ref':preview.ref,'node':preview.node_id,'fields':preview.fields,
        'display':preview.display,'graphs':preview.graphs,'expires':preview.expires_at,
        'consumed_result':preview.consumed_result, 'origin_record': preview.origin_record})


def _install(app, history, episode, ref, node, fields=None):
    app.paper.update_history(history)
    app.service = app.paper.service
    app.review.history = history
    app.history_digest = hashlib.sha256(history.manifest()).hexdigest()
    app.switch_context(episode, ref, refresh=True)
    app.select(node, remember=False)
    if fields and (fields['judgment'] or fields['rationale']):
        # A new observation owns its tentative writing. Existing judgments
        # remain at their original owners; no source contribution is relabeled.
        app.keep_draft(fields['judgment'], fields['rationale'])


class PersonalResearch:
    def __init__(self, app, *, clock=None):
        self.app, self.clock, self.pending = app, clock or time.time, None

    def cancel(self):
        self.pending = None

    def prepare(self, kind, *, item_id=None, question=None, explanation_state=None, explanation_entries=()):
        app = self.app
        self.pending = None
        if not personal(app):
            raise ContractError('Personal recording requires a personal project; protected operations stay unavailable.')
        history = app.paper.history
        if not any(e['id'] == app.episode_id and e['status'] == 'active' for e in history.episodes()):
            raise ContractError('Choose the active research episode before recording new work.')
        now = int(self.clock())
        stamp = datetime.fromtimestamp(now, timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        episode, ref, node = app.episode_id, app.ref, app.selected_id
        fields = graphs = origin_record = None
        display = {'kind':kind, 'scope': f'{episode} / {ref}',
            'storage':'Personal local history, not protected approval; manuscript read-only.'}

        def append(kind, payload, *, episode_id=episode):
            nonlocal history
            key = 'personal-' + secrets.token_hex(12)
            history = history.append({'schema_version':3, 'id':key,
                'project_id':app.view['project_id'], 'episode_id':episode_id,
                'created_at':stamp, 'operation_type':kind,
                'expected_heads':dict(history.heads), 'evidence_watermark':history.watermark,
                'payload':payload})

        if kind in ('confirm', 'correct'):
            item = app.intake.get(item_id)
            if tuple(item['owner'][:2]) != (episode, ref) or item['unfinished']:
                raise ContractError('Keep unfinished fields and return to this result\'s original episode/branch first.')
            context = app.intake.context(item_id)
            if context['current'] is None:
                raise ContractError('Result subject is unavailable; original text remains retained.')
            values = item['kept']
            required = (('observation','value','rationale') if kind == 'correct' else
                ('observation','run_ref','source_ref','conditions','metric_name','metric_definition','value','unit','comparison'))
            for field in required:
                bounded_text(values[field], 'Result ' + field.replace('_',' '))
            display.update(result={f:values[f] for f in required}, original_context=item['source']['digest'],
                           current_context=context['status'], references='Not opened by ClaimBranch; you check the source yourself.')
            if kind == 'confirm':
                if app.intake.recorded_copy(item_id) is not None:
                    raise ContractError('This draft already has a recorded observation. Open its recorded copy; create a separate correction draft there.')
                suffix = item_id.removeprefix('result-draft-')
                run, node = 'run-' + suffix, 'observation-' + suffix
                append('record-experiment', {'id':run, 'question':app.view['episode']['question'],
                    'method':values['run_ref'], 'conditions':values['conditions'],
                    'metric':{k:values['metric_'+k] if k in ('name','definition') else values[k]
                              for k in ('name','definition','unit','comparison')}, 'source_ref':values['source_ref']})
                previous = None
                fields = deepcopy(values)
                rationale = 'Personally confirmed entered result fields; source reference was not opened by the application.'
                if values['uncertainty']:
                    rationale += '\nHuman-entered limitations: '+values['uncertainty']
                display.update(effect='Record one run and one personally confirmed observation; keep tentative judgment at that observation.',
                               question=app.view['episode']['question'],confirmation_note=rationale,
                               tentative_writing={f:values[f] for f in ('judgment','rationale')})
            else:
                unsupported=[f for f,v in values.items() if v and f not in required]
                if unsupported:
                    raise ContractError('Correction records only statement, value and reason. Other entered fields cannot change this run: '+
                        ', '.join(unsupported)+'. Keep this draft; record a separate run/result for changed units or conditions.')
                node = item['owner'][2]
                observation = next((o for o in history.view(ref,episode_id=episode)['evidence'] if o['id']==node),None)
                if observation is None:
                    raise ContractError('Correction needs an existing observation as this result draft\'s subject.')
                run, previous = observation['run_id'], observation['history'][-1]['event_id']
                rationale = values['rationale']
                unchanged_run=next((r for r in history.view(ref,episode_id=episode)['experiments'] if r['id']==run),None)
                if unchanged_run is None:
                    raise ContractError('Original run is unavailable; correction writing is retained.')
                display.update(effect='Append a corrected value/statement to this observation; retain the original and earlier reasoning.',
                    previous=deepcopy(observation), target=node,
                    unchanged_run=unchanged_run)
            append('record-evidence-event', {'event_id':'event-'+secrets.token_hex(12), 'target_id':node,
                'run_id':run, 'action':kind, 'statement':values['observation'],
                'rationale':rationale, 'supersedes_id':previous, 'value':values['value']})
        elif kind == 'reasoning':
            reason = reasoning_unavailable(app)
            if reason:
                raise ContractError(reason)
            app.review.require_current_draft()
            work = app.review.candidates()
            work.require_current()
            reason = app.review.interpretation_review_reason()
            if reason:
                raise ContractError(reason)
            session = app.review.session()
            request = app.review.changes_request()
            current = history.view(ref,episode_id=episode)
            interpretations = [r for r in [*current['changes'], *request['amendments']]
                if r['kind']=='interpretation' and current.get('interpretation_episode_ids',{}).get(r['id'],episode)==episode]
            if not interpretations:
                # Deterministic reuse of the person's own judgment, displayed
                # before recording; no observation basis is inferred.
                # Reopening an unchanged comparison must retain the same cause
                # and topic IDs so explicit reason reuse can be checked. New
                # scientific/writing inputs produce a different identity.
                reading = 'reading-'+digest(request)
                request['amendments'].append({'id':reading,'kind':'interpretation',
                    'body':{'statement':app.draft()['text'],'observation_ids':[]}})
                request['selected_ids'].append(reading)
                display['judgment_reuse'] = 'Your judgment becomes an interpretation with no inferred observation links.'
            judgment = session._current_judgment()
            history, science = app.service.branch_candidate(request,judgment,
                operation_id='record-'+secrets.token_hex(12), created_at=stamp)
            recorded = history.view('alternative',episode_id=episode)
            selected = [a['id'] for a in science['preview']['amendments'] if a['disposition']!='omitted']
            from .paper_proposal_work import record_provenance, explanation_topics, validate_explanation
            from .paper_branch import judgment_value
            cause, lineages, inherited_ai = record_provenance(app.paper, work, science['preview'], request,
                                                            judgment_value(recorded['judgment']))
            explanation = {'state': explanation_state or 'not-reviewed', 'entries': list(explanation_entries)}
            explanation = validate_explanation(cause, science['preview'], explanation)
            recording_available = not inherited_ai or explanation['state'] in ('reviewed', 'leave-for-later')
            judgment_ai = any(c['contributor']=='ai' for j in recorded['judgments'] for c in j['history'])
            if recording_available:
                append('apply-selected-merge', {'selected_ids':selected, 'judgment':recorded['judgment'],
                    # Item-level AI remains in the personal origin registry. The
                    # legacy reducer checks judgment AI only; do not invent a
                    # human deferral from either Boolean.
                    'disposition': ('deferred' if explanation['state']=='leave-for-later' else 'answered')
                        if judgment_ai else 'not-required',
                    'answers': [e['text'] if e['text'].strip() else recorded['judgment']['rationale']
                                for e in explanation['entries']] if judgment_ai and explanation['state']=='reviewed' else []})
            if inherited_ai or explanation_state is not None:
                if len(app.paper._recorded_origins) >= 8:
                    raise ContractError('This personal workspace retains eight AI/explanation consequences; earlier work and writing remain available. A new recorded consequence exceeds its bounded history.')
                origin_record = {'operation_id': decode(history.commands[-1])['id'] if recording_available else 'unrecorded-comparison', 'cause': cause, 'lineages': lineages,
                    'source_judgments': deepcopy(science['preview']['provenance'].get('source_judgments', [])),
                    'explanation': explanation}
            graphs = science['preview']['graphs']
            display.update(effect='Record the displayed selected reasoning in main; retain the alternative and omitted drafts.',
                changes=science['preview']['amendments'], judgment=recorded['judgment'],
                impact=science['preview']['impact'], ai_origin_retained=inherited_ai,
                source_judgments=deepcopy(recorded['judgments']),
                item_origins=lineages, explanation=explanation,
                explanation_topics=explanation_topics(cause, science['preview']) if inherited_ai else [],
                recording_available=not inherited_ai or explanation['state'] in ('reviewed', 'leave-for-later'),
                follow_up='Manuscript follow-up remains open. No file is applied; any AI explanation remains unfinished.')
            ref = 'main'
            from .paper_service import PaperService
            if node not in {n['id'] for n in PaperService(history).query(ref,episode_id=episode)['nodes']}:
                node = app.view['thesis_id']
        elif kind == 'next':
            bounded_text(question,'Next research question')
            append('close-episode', {})
            episode = 'episode-'+secrets.token_hex(12)
            append('open-episode', {'title':question,'question':question},episode_id=episode)
            ref, node = 'main', app.view['thesis_id']
            display.update(effect='Close this episode and begin the displayed question; retain earlier writing, evidence and open follow-up.',
                           question=question, unfinished_results='Earlier result drafts stay readable, but confirmation requires their episode to be active. Finish those results before starting this question.')
        else:
            raise ContractError('Choose personal result confirmation, correction, reasoning or a next question.')
        self.pending = PersonalPreview(kind,_binding(app),history,episode,ref,node,fields,display,graphs,now+300,
                                       item_id if kind=='correct' else None, origin_record)
        self._pending_seal = _seal(self.pending)
        return self.pending

    def keep_explanation(self, preview, *, state='partial', entries=()):
        """Retain contextual personal writing; no science, debt or grading."""
        if (preview is not self.pending or preview.kind != 'reasoning' or preview.origin_record is None
                or _seal(preview) != self._pending_seal
                or state != 'partial' and (int(self.clock()) >= preview.expires_at
                                          or preview.binding != _binding(self.app))):
            raise ContractError('Open an owned personal consequence before writing its explanation')
        # An owned original cause permits partial writing after review expiry or
        # changed current science. It grants no recording/explanation approval:
        # cancel below, and commit still requires a fresh exact comparison.
        from .paper_proposal_work import cause_science, validate_explanation, check_capacity, proposal_snapshot
        cause = preview.origin_record['cause']
        explanation = validate_explanation(cause, cause_science(self.app.paper.history, cause), {'state': state, 'entries': list(entries)})
        paper = self.app.paper
        before = paper._personal_explanations
        updated = [e for e in before if e['cause'] != cause]
        updated.append({'cause': deepcopy(cause), 'explanation': explanation})
        paper._personal_explanations = updated
        try: check_capacity(paper, proposal_snapshot(paper))
        except Exception:
            paper._personal_explanations = before
            raise
        self.cancel()

    def explanation_contexts(self):
        from .paper_proposal_work import cause_science, explanation_topics
        result = []
        entries = deepcopy(self.app.paper._personal_explanations)
        for recorded in self.app.paper._recorded_origins:
            entry = next((e for e in entries if e['cause'] == recorded['cause']), None)
            if entry is None:
                entry = {'cause':deepcopy(recorded['cause']), 'explanation':deepcopy(recorded['explanation'])}
                entries.append(entry)
            entry['recorded_explanation'] = deepcopy(recorded['explanation'])
        for entry in entries:
            cause = entry['cause']; original = cause_science(self.app.paper.history, cause)
            current = self.app.paper.service.query(cause['owner'][1], episode_id=cause['owner'][0])
            result.append({**deepcopy(entry), 'original': original, 'current': current,
                'changed_context': current['digest'] != cause['source']['digest'],
                'topics': explanation_topics(cause, original), 'closure_available': False})
        return result

    def keep_retained_explanation(self, cause, *, entries=()):
        """Continue partial writing on its saved original cause, never science/closure."""
        from .paper_proposal_work import cause_science, validate_explanation, check_capacity, proposal_snapshot
        paper = self.app.paper
        known = [*paper._personal_explanations, *paper._recorded_origins]
        if not any(e['cause'] == cause for e in known):
            raise ContractError('Choose an existing retained personal explanation; no new cause was inferred.')
        explanation = validate_explanation(cause, cause_science(paper.history, cause),
            {'state':'partial', 'entries':list(entries)})
        before = paper._personal_explanations
        paper._personal_explanations = [e for e in before if e['cause'] != cause] + [
            {'cause':deepcopy(cause), 'explanation':explanation}]
        try: check_capacity(paper, proposal_snapshot(paper))
        except Exception:
            paper._personal_explanations = before
            raise
        self.cancel()

    def commit(self, preview):
        app = self.app
        if (not personal(app) or preview is not self.pending or int(self.clock()) >= preview.expires_at
                or preview.binding != _binding(app) or _seal(preview) != self._pending_seal):
            self.cancel()
            raise ContractError('Personal comparison changed or expired; preview again. Writing is retained.')
        self.cancel()
        if preview.kind == 'reasoning' and not preview.display['recording_available']:
            raise ContractError('Choose reviewed or leave-for-later explicitly; partial explanation and reasoning are retained.')
        # Validate the complete prospective workspace before changing either
        # science or the live UI. Failed saves leave all live writing untouched.
        before = PaperWork.create(app.paper.history,workspace=snapshot_value(app))
        candidate = TerminalWorkspace(app.paper.history,ai_off=True)
        restore(candidate,before)
        candidate.paper._saved_proposal_payloads = set(app.paper._saved_proposal_payloads)
        _install(candidate,preview.history,preview.episode_id,preview.ref,preview.node_id,preview.fields)
        if preview.origin_record is not None:
            candidate.paper._recorded_origins.append(deepcopy(preview.origin_record))
        if preview.consumed_result:
            candidate.intake.remove(preview.consumed_result)
        from .paper_proposal_work import fit_new_payloads
        value = snapshot_value(candidate, proposals=False)
        if any(candidate.paper._proposal_entries) or candidate.paper._recorded_origins or candidate.paper._personal_explanations:
            from .paper_proposal_work import proposal_snapshot, proposal_workspace_schema
            value['proposals'] = proposal_snapshot(candidate.paper)
            value['schema'] = proposal_workspace_schema(value['proposals'])
            fit_new_payloads(candidate, value, project=app.recovery.project)
        project = app.recovery.project.with_work(PaperWork.create(preview.history,workspace=value))
        app.recovery._check_writable()
        try:
            app.recovery._store_call(lambda: app.recovery.store.save(project))
        except (ContractError,OSError) as error:
            app.recovery_error = recovery_copy(app,save_failure_message(error))
            raise
        app.recovery.project = project
        from .paper_proposal_work import mark_saved
        mark_saved(app.paper, decode(project.work.payload)['workspace'])
        app.recovery.previous_input = None
        try:
            _install(app,preview.history,preview.episode_id,preview.ref,preview.node_id,preview.fields)
            if preview.origin_record is not None:
                app.paper._recorded_origins.append(deepcopy(preview.origin_record))
            if preview.consumed_result:
                app.intake.remove(preview.consumed_result)
        except Exception as error:
            failure = WorkReopenRequired('Recorded checkpoint could not be installed in this view; reopen to inspect saved research.')
            app.recovery._reopen_error = failure
            app.recovery_error = recovery_copy(app,save_failure_message(failure))
            raise failure from error
        app.recovery_error = None
        app.message = 'Personal research recorded and saved. Earlier work retained; manuscript unchanged.'
        return preview.history


def reasoning_unavailable(app):
    if app.view['episode']['status'] != 'active':
        return 'Choose the active research episode first.'
    if any(decode(raw)['operation_type']=='apply-selected-merge' and decode(raw)['episode_id']==app.episode_id
           for raw in app.paper.history.commands):
        return 'This episode already has its chosen reasoning. Start the next research question for another update; writing is retained.'
    if app.ref != 'alternative' and 'alternative' in dict(app.paper.history.heads):
        return 'Switch to this episode’s alternative branch before recording its reasoning.'
    return ''
