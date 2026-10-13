"""A bounded action list for the selected subject; existing handlers own effects."""
from .tui_retention import recovery_copy, personal
from dataclasses import dataclass

from claimbranch.core.canonical import ContractError
from .tui_model import clip, wrap


@dataclass(frozen=True)
class Action:
    title: str
    key: str | None
    detail: str
    group: str = 'WRITE AND INSPECT'
    work: bool = False
    unavailable: str = ''


class ActionsUI:
    def __init__(self, terminal):
        self.terminal = terminal
        self.index = 0
        self.notice = ''
        self.has_failure = False

    def items(self):
        app = self.terminal.app
        from .tui_proposals import available
        typed = available(app)
        connection = getattr(app, 'provider_connection', None)
        session = app.review.sessions.get(app.review.key)
        prepared = session.get_changes_preview() if session else None
        draft = app.draft()
        review_reason = ('Write a judgment and reason first.' if not all(draft.values()) else
                         'Edit and select scientific changes first.' if not app.review.selected.get(app.review.key) else '')
        review_reason = review_reason or app.review.interpretation_review_reason()
        branch_reason = (('Choose the active research episode first.' if personal(app) else 'Requires an active episode; try demo tui --merge-example.')
                         if not app.series or app.view['episode']['status'] != 'active' else '')
        candidate_reason = branch_reason or ('Switch to the alternative branch before preparing its candidate.'
                                             if app.ref != 'alternative' and 'alternative' in dict(app.paper.history.heads)
                                             else review_reason)
        unfinished = app.review.unfinished or any(any(texts) for texts in app.unfinished.values())
        from .paper_candidates import interpretation_unavailable
        work = app.review.candidate_works.get(app.review.key)
        interpretation_reason = interpretation_unavailable(app.paper, app.full_context(app.review.key),
            [*(work.records.values() if work else ()), *app.review.candidate_inputs.get(app.review.key, {}).values()])
        failures = ([Action('Inspect writing save status', 'save-status',
                            'Read the complete failure and safe next steps. Esc returns without changing writing.',
                            'WRITING RECOVERY')] if self.has_failure else [])
        personal_reason = ''
        if personal(app):
            from .personal_research import reasoning_unavailable
            personal_reason = reasoning_unavailable(app)
        return failures + [
            Action('Write a judgment', 'e', 'Edit judgment ' + app.node_label(app.work_key()[-1]) + ' beside this node\'s recorded context. Keep with Ctrl+S; choose another judgment from actions.', work=True),
            Action('Edit personal note', 'n', 'A free-form note on this node. It does not replace evidence or your scientific judgment.'),
            Action('Add a claim or subclaim', 'candidate:claim', 'Choose its level and parent; write the claim and scope. Drafts are unaccepted; --work-dir retains them.', 'CREATE'),
            Action('Connect research records', 'candidate:scientific-edge', 'Choose source, target claim, supports/challenges/qualifies and your reason. Reuses existing evidence.', 'CREATE'),
            Action('Plan a follow-up experiment', 'candidate:experiment-plan', 'Choose a claim; write the question, conditions and measurement. An unrun draft; --work-dir retains it.', 'CREATE'),
            Action('Draft a result and source', 'intake:new', 'Capture an unconfirmed result beside this recorded subject. References, conditions and a tentative judgment may remain incomplete. --work-dir retains drafts.', 'CREATE'),
            Action('Resume result drafts', 'intake:list', 'Return to kept and unfinished result writing with its original context. Evidence confirmation and scientific review are not connected.', 'CREATE'),
            Action('Write an interpretation', 'candidate:interpretation', 'Write your explanation and explicitly choose the observations it interprets. One interpretation per episode here; --work-dir retains drafts.', 'CREATE', unavailable=interpretation_reason),
            Action('Follow connections', 'r', 'Read each connection, its direction and reason; follow it and return to this subject.'),
            Action('Resume unfinished writing', 'U', 'Choose unfinished text by node, branch and kind. Resuming does not restore review authority.',
                   unavailable='' if unfinished else 'No unfinished writing in this session.'),
            Action('Open argument drafts', 'candidate:list', 'Create and revise claims, connections and unrun plans owned by the selected judgment, even before it is complete.'),
            Action('Resume manuscript drafts', 'manuscript:saved', 'Return to wording with its original source and scientific basis. Restoring text does not restore review authority.'),
            Action('Return to authored work', 'candidate:owners', 'Return to the original node and work owning your argument drafts or unfinished candidate fields.'),
            Action('Link this judgment to nodes', 'work-links:edit', 'Use this judgment at explicitly chosen nodes in this episode and branch. Other judgments remain separate.'),
            Action('Choose a judgment for this node', 'work-links:choose', 'Use an existing judgment here, or return to this node\'s separate judgment. Preview before changing links.'),
            Action('Edit scientific changes', 'c', 'Edit existing claims, interpretations, plans or relations. Select which authored changes to review.', 'REVIEW', True),
            Action('Review selected changes', 'R', 'Preview the exact selected changes and their consequences. Nothing is accepted.', 'REVIEW', True, review_reason),
            Action('Compare before and after', 'G', 'Inspect the selected changes in both graphs. Tab switches before/after.', 'REVIEW', True,
                   '' if prepared else 'Prepare a current selected-change review first.'),
            Action('Finish change review', 'enter', 'Complete this unaccepted review; source AI may require explanation or deferral.', 'REVIEW', True,
                   '' if prepared else 'Prepare and inspect the selected-change review first.'),
            Action('Prepare branch candidate', 'C', 'Preview authored reasoning on the active alternative. A candidate does not install or merge it.', 'REVIEW', True, candidate_reason),
            Action('Review merge selection', 'M', 'Choose reasoning from the active alternative; exact review needs a supplied manuscript source.', 'REVIEW', False, branch_reason),
            Action('Paper connection', 'project-source', 'Inspect the saved paper; preview relocation or source refresh while retaining earlier writing.',
                   unavailable='' if hasattr(app, 'project_source_status') else 'Open a selected project with demo project open first.'),
        ] + ([
            Action('Record selected reasoning personally', 'personal:reasoning', 'Review chosen claims/relations and reuse this judgment/reason. Record main and retain the alternative; manuscript stays read-only.', 'PERSONAL HISTORY',
                   unavailable=personal_reason or ('' if all(draft.values()) else 'Write your judgment and reason first.')),
            Action('Start the next research question', 'personal:next', 'Preview a new question. Keep earlier evidence, writing, alternatives and unresolved manuscript work.', 'PERSONAL HISTORY', unavailable=branch_reason),
        ] if personal(app) else []) + [
            Action('Ask AI about this context', 'proposal:ask' if typed else 'A',
                   'Choose recorded science and task, then inspect the exact unsent API request. Actual provider not qualified; no complete judgment required.' if connection else
                   'Choose exact context, then review a fixed offline request. No live model; no complete judgment required.',
                   'OPTIONAL AI', True, '' if typed or app.paper.ai_available else 'AI OFF. Manual writing remains available. No request will be prepared.'),
        ] + ([Action('Discuss this argument with AI', 'proposal:discuss',
                     'Ask a question and read natural-language advice. Choose graph context and earlier replies explicitly; no graph change.',
                     'OPTIONAL AI', True, '' if connection.enabled else 'Enable the personal connection first.'),
              Action('Prepare a small edit with AI', 'proposal:edit',
                     'Describe one intended claim, plan or typed connection. Review exact input, then compare the returned candidates.',
                     'OPTIONAL AI', True, '' if connection.enabled else 'Enable the personal connection first.'),
              Action('Disable personal AI connection' if connection.enabled else 'Enable personal AI connection',
                     'proposal:disable' if connection.enabled else 'proposal:enable',
                     'Session-only choice. Keep manual work and saved origins; enabling creates no request or provider qualification.', 'OPTIONAL AI')]
             if connection else []) + ([Action('Compare current AI items', 'proposal:current', 'Select independent items; compare required/omitted scope and both draft graphs before staging.', 'OPTIONAL AI')]
             if typed else []) + ([
            Action('Read AI response history', 'proposal:history', 'Read saved input, original items, disposition and payload availability. No request or incorporation capability restores.', 'ORIGIN AND RETURN'),
            Action('Inspect AI item origins', 'proposal:origins', 'Original items, human edits and recorded judgments/reasons remain visible with AI disabled.', 'ORIGIN AND RETURN'),
        ] if app.paper.proposal_history() or app.paper.recorded_origins() else []) + ([
            Action('Return to personal explanations', 'personal:explanations', 'Read original/current science, partial writing and explicit review choice. No debt closure.', 'ORIGIN AND RETURN'),
        ] if personal(app) and (app.paper._personal_explanations or app.paper._recorded_origins) else [])

    def open(self):
        self.index = 0
        self.notice = ''
        self.has_failure = bool(getattr(self.terminal.app, 'recovery_error', None))
        self.terminal.modal = 'actions'

    def key(self, event):
        terminal = self.terminal
        if event in ('escape', ';'):
            terminal.modal = None
            return
        height, width = terminal.screen.getmaxyx()
        if width < 48 or height < 18:
            return
        items = self.items()
        if event in ('up', 'k', 'down', 'j', 'home', 'end', 'page-up', 'page-down'):
            self.notice = ''
            self.index = (0 if event == 'home' else len(items) - 1 if event == 'end' else
                          max(0, min(len(items) - 1, self.index +
                                     {'up': -1, 'k': -1, 'down': 1, 'j': 1, 'page-up': -5, 'page-down': 5}[event])))
        elif event == 'enter':
            action = items[self.index]
            if action.unavailable:
                self.notice = 'UNAVAILABLE / no action taken'
                return
            if (action.key or '').startswith('proposal:'):
                from .tui_proposals import proposals_ui
                try:
                    proposals_ui(terminal).enter(action.key.split(':',1)[1])
                except (ContractError, OSError, ValueError) as error:
                    self.notice = str(error)
                return
            if (action.key or '').startswith('personal:'):
                from .tui_personal import personal_ui
                try:
                    personal_ui(terminal).enter(action.key.split(':',1)[1])
                except (ContractError, OSError, ValueError) as error:
                    self.notice = str(error)
                return
            if action.key == 'save-status':
                terminal.save_scroll = 0
                terminal.modal = 'save-status'
                return
            if action.key == 'manuscript:saved':
                from .tui_manuscript_ui import manuscript_ui
                manuscript_ui(terminal).open_saved()
                return
            if action.key == 'project-source':
                from .tui_project_source import project_source_ui
                try:
                    project_source_ui(terminal).open()
                except (ContractError, OSError) as error:
                    self.notice = str(error)
                return
            if action.key and action.key.startswith('intake:'):
                from .tui_intake_ui import intake_ui
                try:
                    intake_ui(terminal).enter(action.key.split(':', 1)[1])
                except ContractError as error:
                    self.notice = str(error)
                return
            if action.key and action.key.startswith('work-links:'):
                from .tui_work_links_ui import work_links_ui
                try:
                    work_links_ui(terminal).enter(action.key.split(':', 1)[1])
                except ContractError as error:
                    self.notice = str(error)
                return
            if action.key and action.key.startswith('candidate:'):
                from .tui_candidates_ui import candidates_ui
                try:
                    candidates_ui(terminal).enter(action.key.split(':', 1)[1])
                except ContractError as error:
                    self.notice = str(error)
                return
            terminal.modal = None
            if action.work:
                terminal.key('w')
            terminal.key(action.key)

    def draw(self, frame):
        from .tui import Frame
        frame = Frame(frame.width, frame.height)
        width, height = frame.width, frame.height
        app = self.terminal.app
        if width < 48 or height < 18:
            frame.put(1, 1, 'Actions paused', 'top_warning', width - 2)
            frame.put(3, 1, 'Enlarge to 48 x 18. Esc returns.', 'top_muted', width - 2)
            return frame
        measure = min(94, width - 6)
        x = (width - measure) // 2
        frame.put(0, x, 'ACTIONS / ' + app.node_label(app.selected_id) + ' ' + app.kind(app.selected_id), 'brand', measure)
        frame.put(1, x, app.episode_id + ' / ' + app.ref + recovery_copy(app, ' / synthetic session'), 'top_muted', measure)
        from .tui_proposals import available
        frame.put(2, x, 'Fixed example AI · no live model' if app.paper.ai_available or available(app) else 'AI OFF · Manual writing remains available', 'top_accent', measure)
        source = wrap(app.title(app.selected_id), measure)
        if len(source) > 2:
            source[1] = clip(source[1], measure - 1, ellipsis=False).rstrip() + '…'
        for row, text in enumerate(source[:2]):
            frame.put(3 + row, x, text, 'top_muted', measure)
        items = self.items()
        visible = max(1, height - 14)
        offset = max(0, self.index - visible + 1)
        for row, action in enumerate(items[offset:offset + visible]):
            active = row + offset == self.index
            frame.fill(6 + row, x, measure, 'selected' if active else 'body')
            label = ('› ' if active else '  ') + ('× ' if action.unavailable else '  ') + action.title
            frame.put(6 + row, x, label, 'selected' if active else 'muted' if action.unavailable else 'body', measure - 8)
            shortcut = ('' if (action.key or '').startswith(('proposal:', 'candidate:', 'work-links:', 'intake:', 'personal:', 'manuscript:', 'project-source', 'save-status')) else
                        ('w ' if action.work and action.key != 'e' else '') + (action.key or ''))
            frame.put(6 + row, x + measure - 7, '--' if action.unavailable else shortcut,
                      'selected_meta' if active else 'muted', 7)
        action = items[self.index]
        y = height - 7
        frame.put(y, x, self.notice or action.group + (' / UNAVAILABLE' if action.unavailable else ''),
                  'top_warning' if action.unavailable else 'top_accent', measure)
        detail = action.unavailable or action.detail
        if personal(app):
            detail = detail.replace('--work-dir retains', 'Local saves retain')
            detail = detail.replace('Evidence confirmation and scientific review are not connected.', 'Open a result to preview personal confirmation or a correction.')
        for row, text in enumerate(wrap(detail, measure)[:3]):
            frame.put(y + 1 + row, x, text, 'top_muted', measure)
        frame.put(height - 2, x, '↑↓ choose · Enter open · Esc return', 'top_accent', measure)
        failure = getattr(app, 'recovery_error', None)
        footer = ('Esc, then ; to inspect save failure' if failure and not self.has_failure else failure)
        frame.put(height - 1, x, footer or
                  f'{self.index + 1}/{len(items)} · × unavailable · PgUp/PgDn', 'top_warning' if getattr(app, 'recovery_error', None) else 'top_muted', measure)
        return frame


def actions_ui(terminal):
    if not hasattr(terminal, '_actions_ui'):
        terminal._actions_ui = ActionsUI(terminal)
    return terminal._actions_ui
