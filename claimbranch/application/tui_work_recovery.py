"""Encrypted judgment/authoring adapter over the existing device work store.

Review authority and manuscript review answers remain explicitly excluded.
This is synthetic unaccepted work, never a project backup or accepted writer.
"""
from contextlib import ExitStack
import sys

from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from .paper_work_store import PaperWork, WorkReopenRequired
from .paper_workspace_snapshot import paper_snapshot, restore_paper, validate_workspace


def enabled(app):
    return isinstance(app.recovery, JudgmentRecovery)


def excluded_work(app):
    result = ['unfinished research editor text'] if getattr(app, 'uncheckpointed_editor', False) else []
    if getattr(app, 'unsent_discussion_question', False): result.append('unsent AI discussion question (session only)')
    if app.branches.volatile_work(): result.append('branch/merge work')
    if any(mode == 'answer' for _, mode in app.manuscript.buffers):
        result.append('manuscript review answers')
    if any(s.get_preview() or s.get_review() for s in app.manuscript.sessions.values()):
        result.append('manuscript reviews')
    if any(state['attempts'] or state['attempt'] or state['changes_preview'] or state['changes_review']
           for session in app.review.sessions.values() for state in (session.state(),)):
        result.append('live requests, consent and reviews')
    return result


from .paper_storage_codec import encode as canonical_bytes, decode

def snapshot_value(app, active=None, *, proposals=True):
    unfinished = dict(app.unfinished)
    if active and active[0] not in ('note', 'edit', 'candidate', 'intake', 'understanding', 'review', 'manuscript'):
        raise ContractError('This editor is outside the writing checkpoint.')
    if active and active[0] in ('note', 'edit'):
        mode, texts = active
        unfinished[(*app.writing_key(mode), mode)] = list(texts)
    value = {'schema': 'claimbranch.review-pool-workspace/v6', 'paper': paper_snapshot(app.paper),
        'notes': [{'owner': list(key), 'text': text} for key, text in sorted(app.notes.items())],
        'drafts': [{'owner': list(key), **draft} for key, draft in sorted(app.drafts.items())],
        'buffers': [{'owner': list(key), **draft} for key, draft in sorted(app.review.buffers.items())],
        'unfinished': [{'owner': list(key[:-1]), 'mode': key[-1], 'texts': list(texts)}
                       for key, texts in sorted(unfinished.items())],
        'selection': list(app.context_key())}
    from .paper_authoring_snapshot import authoring_snapshot
    value['authoring'] = authoring_snapshot(app, active)
    from .paper_explanation_snapshot import explanation_snapshot
    value['understanding'] = explanation_snapshot(app, active)
    from .paper_review_writing_snapshot import writing_snapshot
    value['review_writing'] = writing_snapshot(app, active, pooled=True)
    from .paper_wording_snapshot import wording_snapshot
    value['manuscript'] = wording_snapshot(app, active)
    if proposals:
        from .paper_proposal_work import proposal_snapshot, proposal_workspace_schema
        retained = proposal_snapshot(app.paper)
        if any(retained.values()):
            value['schema'] = proposal_workspace_schema(retained)
            value['proposals'] = retained
            from .paper_proposal_work import fit_new_payloads
            value = fit_new_payloads(app, value)
    if app.paper.history.schema_version in (4, 5):
        value['schema'] = 'claimbranch.paper-workspace/v15' if app.paper.history.has_manuscript_anchors else 'claimbranch.paper-workspace/v14' if app.paper.history.schema_version == 5 else 'claimbranch.paper-workspace/v13'
    return value


def snapshot(app, active=None):
    return PaperWork.create(app.paper.history, workspace=snapshot_value(app, active))


class WritingInputError(ContractError):
    """Writing validation failed before calling the checkpoint store."""


def checkpoint_input(app, active=None):
    try:
        value = snapshot_value(app, active)
        current = (app.paper.history.seed, app.paper.history.commands, canonical_bytes(value))
        return value, current
    except ContractError as error:
        raise WritingInputError(str(error)) from error


def save_failure_message(error):
    if isinstance(error, WritingInputError):
        return ('Writing checkpoint not saved: ' + str(error) + '. Keep this session open; text remains in memory. '
                'Inspect the reported input; correct or shorten it before retrying. '
                'Ctrl+C exits without saving newer input.')
    if isinstance(error, WorkReopenRequired):
        return ('Writing save not confirmed. Keep this session open to copy newer writing before exiting; '
                'then reopen to inspect the checkpoint. Saving is blocked for this session. '
                'Ctrl+C exits without saving newer input. ' + str(error))
    return ('Writing save not confirmed: ' + str(error) + '. Keep this session open; text remains in memory. '
            'Check storage/encryption availability before retrying. '
            'Ctrl+C exits without saving newer input.')


def restore(app, work):
    from .tui_review import FROZEN_CRITIQUE, REVIEW_LIMIT
    if app.review.sessions or app.notes or app.drafts or app.unfinished or app.review.volatile_work():
        raise ContractError('Restore into a fresh terminal workspace; current writing is retained.')
    value = decode(work.payload)
    if ('workspace' not in value or not app.series or app.paper.history.seed != work.history.seed
            or app.paper.history.commands != work.history.commands):
        raise ContractError('Judgment checkpoint requires its exact cumulative example and variant; no data was replaced.')
    value = validate_workspace(work.history, value['workspace'])
    paper = restore_paper(work.history, value['paper'],
                          frozen_response=FROZEN_CRITIQUE if app.paper.ai_available else None)
    # Validate a complete detached result before installing anything in the UI.
    notes = {tuple(item['owner']): item['text'] for item in value['notes']}
    drafts = {tuple(item['owner']): {key: item[key] for key in ('text', 'rationale')} for item in value['drafts']}
    buffers = {tuple(item['owner']): {key: item[key] for key in ('text', 'rationale')} for item in value['buffers']}
    unfinished = {(*item['owner'], item['mode']): item['texts'] for item in value['unfinished']}
    from .paper_authoring_snapshot import restore_authoring
    from .paper_intake import PaperResultIntake
    candidate_inputs, intake = restore_authoring(paper, value['authoring']) if 'authoring' in value else ({}, PaperResultIntake(paper))
    if 'proposals' in value:
        from .paper_proposal_work import restore_proposals
        restore_proposals(paper, value['proposals'], unfinished=candidate_inputs)
    from .paper_explanation_snapshot import restore_explanations
    from .tui_understanding import TerminalUnderstanding
    understanding = TerminalUnderstanding(app)
    if 'understanding' in value:
        for name, content in restore_explanations(work.history, value['understanding']).items():
            setattr(understanding, name, content)
    from .paper_review_writing_snapshot import restore_writing
    review_inputs, review_basis = restore_writing(work.history, value.get('review_writing', []))
    from .paper_wording_snapshot import restore_wording
    from .tui_manuscript import TerminalManuscript
    manuscript = TerminalManuscript(app, clock=app.manuscript.clock)
    if 'manuscript' in value:
        for name, content in restore_wording(work.history, value['manuscript'], clock=manuscript.clock).items():
            setattr(manuscript, name, content)
    app.manuscript = manuscript
    app.review.unfinished, app.review.unfinished_basis = review_inputs, review_basis
    app.understanding = understanding
    app.paper, app.service = paper, paper.service
    paper._checkpoint_app = app
    app.intake = intake
    app.review.candidate_works = dict(paper._candidates)
    app.review.candidate_inputs = candidate_inputs
    app.review.sessions = dict(paper._drafts)
    app.review.buffers = buffers
    app.review.buffer_notices = {key: REVIEW_LIMIT if key in paper._drafts else
                                'Manual text restored. Review session limit reached; writing is retained.'
                                for key in buffers}
    app.notes, app.drafts, app.unfinished = notes, drafts, unfinished
    app.open_context_key(value['selection'])
    app.message = 'Writing restored. U resumes review input; W explains; actions resume manuscript drafts. Prepare reviews again.'


class JudgmentRecovery:
    """One device-backed store session, with no plaintext recovery key on disk."""
    encrypted_judgments = True

    def __init__(self, store, app, *, resources=None):
        self.store, self.resources, self.previous = store, resources, None
        self.previous_input = None
        work = store.load()
        if work is not None:
            restore(app, work)
            self.previous = work.payload
            self.previous_input = (app.paper.history.seed, app.paper.history.commands,
                                   canonical_bytes(snapshot_value(app)))

    @classmethod
    def open(cls, directory, app, *, create=False):
        from .device_work_store import DevicePaperWorkStore
        from .work_cipher import MacWorkCipher
        if not app.series:
            raise ContractError('Encrypted judgments require --series or --merge-example; the ordinary example is unchanged.')
        if sys.platform != 'darwin':
            raise ContractError('Device judgment recovery currently requires macOS; terminal-only use remains available.')
        resources = ExitStack()
        try:
            cipher = resources.enter_context(MacWorkCipher())
            project = app.view['project_id']
            if create:
                from .work_commands import recovery_key
                print('Create a synthetic writing checkpoint: judgments, AI origin, notes, links, argument/result drafts, partial explanations and unfinished review input.\n'
                      'Original sources are retained alongside written wording. Manuscript review answers and completed reviews remain session-only.')
                key = recovery_key(from_stdin=False, create=True)
                store = DevicePaperWorkStore.create(directory, cipher=cipher, project_id=project, recovery_key=key)
                del key
            else:
                store = DevicePaperWorkStore(directory, cipher=cipher, project_id=project)
            resources.enter_context(store)
            result = cls(store, app, resources=resources)
            if create: result.save(app)
            return result
        except BaseException:
            resources.close()
            raise

    def save(self, app, active=None):
        self._check_writable()
        value, current_input = checkpoint_input(app, active)
        if current_input == self.previous_input:
            self._store_call(self.store.verify_unchanged)
            return
        try:
            work = PaperWork.create(app.paper.history, workspace=value)
        except ContractError as error:
            raise WritingInputError(str(error)) from error
        if work.payload != self.previous:
            self._store_call(lambda: self.store.save(work))
            self.previous = work.payload
        else:
            self._store_call(self.store.verify_unchanged)
        self.previous_input = current_input
        from .paper_proposal_work import mark_saved
        mark_saved(app.paper, value)

    def _check_writable(self):
        if getattr(self, '_reopen_error', None) is not None:
            raise self._reopen_error

    def _store_call(self, action):
        self._check_writable()
        try:
            return action()
        except WorkReopenRequired as error:
            self._reopen_error = error
            raise

    def close(self):
        if self.resources is not None:
            self.resources.close()
            self.resources = None
