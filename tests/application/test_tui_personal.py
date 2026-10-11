from types import SimpleNamespace
import unittest
from unittest.mock import patch

from claimbranch.application.tui import Frame, Terminal
from claimbranch.application.tui_actions import actions_ui
from claimbranch.application.tui_intake_ui import intake_ui
from claimbranch.application.tui_personal import personal_ui
from tests.application import test_personal_research as fixture


class PersonalUITests(unittest.TestCase):
    setUp = fixture.PersonalResearchTests.setUp
    result = fixture.PersonalResearchTests.result
    author = fixture.PersonalResearchTests.author
    confirm_result = fixture.PersonalResearchTests.confirm_result

    def terminal(self):
        with patch.object(Terminal,'setup_styles'):
            terminal = Terminal(SimpleNamespace(getmaxyx=lambda:(24,80)),self.app,SimpleNamespace(flushinp=lambda:None))
        personal_ui(terminal).service.clock=lambda:2000000000
        return terminal

    def test_result_preview_requires_reading_cancel_keeps_text_and_enter_records(self):
        terminal=self.terminal(); intake=intake_ui(terminal)
        intake.entry_id=self.result(); intake.open('form')
        terminal.key('c'); self.assertEqual('personal-preview',terminal.modal)
        preview=personal_ui(terminal)
        terminal.key('enter'); self.assertEqual(0,self.app.paper.history.watermark)
        self.assertIn('PERSONAL RECORD PREVIEW',terminal.draw_modal(Frame(80,24)).plain())
        terminal.key('escape'); self.assertEqual('intake-form',terminal.modal)
        self.assertEqual('24',self.app.intake.get(intake.entry_id)['kept']['value'])
        terminal.key('c'); terminal.draw_modal(Frame(80,24))
        terminal.key('end'); terminal.draw_modal(Frame(80,24)); terminal.key('enter')
        self.assertIsNone(terminal.modal); self.assertEqual(1,self.app.paper.history.watermark)
        self.assertIn('saved',self.app.message)

    def test_named_reasoning_graph_narrow_pause_then_next_question(self):
        observation=self.confirm_result(); self.author(observation)
        terminal=self.terminal(); menu=actions_ui(terminal); menu.open()
        menu.index=next(i for i,a in enumerate(menu.items()) if a.key=='personal:reasoning')
        terminal.key('enter')
        self.assertIn('Personal controls paused',terminal.draw_modal(Frame(40,12)).plain())
        terminal.draw_modal(Frame(80,24)); terminal.key('G')
        self.assertIn('PERSONAL COMPARISON',terminal.draw_modal(Frame(132,38)).plain())
        terminal.key('tab'); terminal.key('right'); terminal.key('f')
        terminal.key('escape'); terminal.key('end'); terminal.draw_modal(Frame(80,24)); terminal.key('enter')
        self.assertEqual(2,len(self.app.claim_uses(observation)))
        earlier=self.app.episode_id
        menu.open(); menu.index=next(i for i,a in enumerate(menu.items()) if a.key=='personal:next')
        terminal.key('enter'); terminal.key(('paste','다른 기기에서는 어떤가?'))
        self.assertIn('NEXT RESEARCH QUESTION',terminal.draw_modal(Frame(80,24)).plain())
        terminal.key('keep'); terminal.draw_modal(Frame(80,24)); terminal.key('end')
        terminal.draw_modal(Frame(80,24)); terminal.key('enter')
        self.assertNotEqual(earlier,self.app.episode_id)

    def test_next_question_text_returns_after_failed_record(self):
        terminal=self.terminal(); ui=personal_ui(terminal)
        ui.enter('next'); terminal.key(('paste','질문을 잃지 않아야 한다.')); terminal.key('keep')
        terminal.draw_modal(Frame(80,24)); terminal.key('end'); terminal.draw_modal(Frame(80,24))
        with patch.object(self.store,'save',side_effect=OSError('Failed save')):
            terminal.key('enter')
        terminal.key('escape')
        self.assertEqual('personal-next',terminal.modal)
        self.assertEqual('질문을 잃지 않아야 한다.',terminal.buffers[0].text)
        terminal.key('escape')
        self.assertIsNone(terminal.modal)
        ui.enter('next'); self.assertEqual('질문을 잃지 않아야 한다.',terminal.buffers[0].text)
        terminal.key('escape')
        self.assertIsNone(terminal.modal)
        ui.enter('next')
        self.assertEqual('질문을 잃지 않아야 한다.',terminal.buffers[0].text)

    def test_next_editor_cancel_and_preview_cancel_retain_the_question(self):
        terminal=self.terminal(); ui=personal_ui(terminal)
        ui.enter('next'); terminal.key(('paste','Later question')); terminal.key('escape')
        ui.enter('next'); self.assertEqual('Later question',terminal.buffers[0].text)
        terminal.key('keep'); terminal.key('escape')
        self.assertEqual('personal-next',terminal.modal)
        self.assertEqual('Later question',terminal.buffers[0].text)
        self.assertEqual(1,len(self.app.paper.history.episodes()))
        terminal.key('escape'); self.assertIsNone(terminal.modal)

    def test_empty_next_question_validation_failure_can_cancel(self):
        terminal=self.terminal(); ui=personal_ui(terminal)
        ui.enter('next'); terminal.key('keep'); terminal.key('escape')
        self.assertIsNone(terminal.modal)
        terminal.key('escape')
        self.assertIsNone(terminal.modal)

    def test_next_question_refusal_can_exit_and_contexts_keep_separate_text(self):
        terminal=self.terminal(); ui=personal_ui(terminal)
        ui.enter('next'); terminal.key('keep'); terminal.key('escape')
        self.assertIsNone(terminal.modal)
        earlier=self.app.episode_id
        ui.enter('next'); terminal.key(('paste','Question for the original episode')); terminal.key('escape')
        self.research.commit(self.research.prepare('next',question='A separately recorded question'))
        ui.enter('next'); terminal.key(('paste','Question for the later episode')); terminal.key('escape')
        later=self.app.episode_id
        self.app.switch_context(earlier,'main')
        ui.enter('next'); self.assertEqual('Question for the original episode',terminal.buffers[0].text)
        terminal.key('escape'); self.app.switch_context(later,'main')
        ui.enter('next'); self.assertEqual('Question for the later episode',terminal.buffers[0].text)

    def test_recorded_copy_navigation_returns_to_original_context_and_keeps_save_warning(self):
        key=self.result(); self.research.commit(self.research.prepare('confirm',item_id=key))
        observation=self.app.selected_id; earlier=self.app.episode_id
        self.research.commit(self.research.prepare('next',question='Later question'))
        terminal=self.terminal(); intake=intake_ui(terminal)
        intake.entry_id=key; intake.open('form')
        self.app.recovery_error='Save failed; live writing retained.'
        frame=terminal.draw_modal(Frame(80,24)).plain()
        self.assertIn('Save failed',frame)
        terminal.key('v')
        self.assertIsNone(terminal.modal)
        self.assertEqual((earlier,'main',observation),self.app.context_key())

    def test_correction_preview_names_exact_statement_and_unchanged_measurement(self):
        observation=self.confirm_result()
        key=self.app.intake.create((self.app.episode_id,'main',observation))
        for f,v in {'observation':'Corrected statement','value':'23','rationale':'Timer offset'}.items():
            self.app.intake.keep(key,f,v)
        terminal=self.terminal(); ui=personal_ui(terminal); ui.enter('correct',item_id=key)
        rows='\n'.join(ui.rows(74))
        self.assertIn('CORRECTED STATEMENT',rows)
        self.assertIn('UNCHANGED MEASUREMENT',rows)
        self.assertIn('UNIT: ms',rows)
        self.assertNotIn('STILL UNCONFIRMED',rows)

    def test_next_question_follows_episode_when_graph_selection_changes(self):
        observation=self.confirm_result()
        self.app.select('thesis')
        terminal=self.terminal(); ui=personal_ui(terminal)
        ui.enter('next'); terminal.key(('paste','Does another device reproduce this?')); terminal.key('escape')
        self.app.select(observation)
        ui.enter('next')
        self.assertEqual('Does another device reproduce this?',terminal.buffers[0].text)

    def test_reasoning_preview_names_impacted_claim_and_ai_disposition(self):
        observation=self.confirm_result(); self.author(observation)
        terminal=self.terminal(); ui=personal_ui(terminal); ui.enter('reasoning')
        rows='\n'.join(ui.rows(74))
        self.assertIn('MAY NEED CLAIM REVIEW',rows)
        self.assertIn('OUTSIDE THIS PATH',rows)
        self.assertIn('No AI influence recorded',rows)
        self.assertIn('잡음 입력에서 지연이 늘어난다.',rows)
