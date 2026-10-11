"""Human personal recording, explicit previews and append-only return."""
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch

from claimbranch.application.personal_project import PersonalProjectStore, PersonalProjectRecovery
from claimbranch.application.project_work import preview_association
from claimbranch.application.tui_project import prepare_project, project_workspace
from claimbranch.core.canonical import ContractError, decode


class PersonalResearchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.paper, self.directory = root / 'paper', root / 'work'
        self.paper.mkdir(); self.directory.mkdir(mode=0o700)
        subprocess.run(['git', 'init', '-q', str(self.paper)], check=True)
        self.source = b'% claimbranch:start id=anchor\nUndecided.\n% claimbranch:end id=anchor\n'
        (self.paper / 'paper.tex').write_bytes(self.source)
        association = preview_association(self.paper, 'paper.tex', 'anchor', self.directory)
        project = prepare_project(association, project_id='new-study', title='Noise study',
            thesis='입력 조건에 따라 지연시간이 달라진다.', question='잡음이 지연시간에 영향을 주는가?')
        self.store = PersonalProjectStore.create(self.directory, project_id='new-study').__enter__()
        self.addCleanup(self.store.close)
        self.store.save(project, preview=association)
        self.app = project_workspace(project)
        self.app.recovery = PersonalProjectRecovery(self.store, self.app, project)
        from claimbranch.application.personal_research import PersonalResearch
        self.research = PersonalResearch(self.app, clock=lambda: 2000000000)

    def result(self):
        key = self.app.intake.create((self.app.episode_id, self.app.ref, self.app.selected_id))
        for field, value in {'observation':'잡음 조건에서 지연시간은 24 ms였다.',
            'run_ref':'run-47; ten repetitions with injected noise', 'source_ref':'ssh://lab/run-47.csv',
            'conditions':'32 samples, fixed hardware', 'metric_name':'latency',
            'metric_definition':'elapsed time from input to output', 'value':'24', 'unit':'ms',
            'comparison':'clean input: 20 ms', 'uncertainty':'Other hardware unmeasured',
            'judgment':'이 환경에서는 잡음이 지연을 늘렸다.', 'rationale':'입력 외의 조건을 고정했다.'}.items():
            self.app.intake.keep(key, field, value)
        return key

    def confirm_result(self):
        preview = self.research.prepare('confirm', item_id=self.result())
        self.research.commit(preview)
        return self.app.selected_id

    def author(self, observation):
        self.app.select('thesis')
        self.app.keep_draft('이 환경에서는 잡음이 지연을 늘렸다.', '입력 외의 조건을 고정했다.')
        work = self.app.review.candidates()
        claim = work.create('claim', {'role':'main','statement':'잡음 입력에서 지연이 늘어난다.',
            'scope':'Tested hardware and sample count only', 'parent_ids':['thesis']})
        work.create('scientific-edge', {'edge_type':'supports', 'source_id':observation,
            'target_id':claim, 'rationale':'24 ms exceeds the clean 20 ms baseline.'})
        work.create('scientific-edge', {'edge_type':'qualifies', 'source_id':observation,
            'target_id':'thesis', 'rationale':'Only the tested conditions are measured.'})
        work.create('experiment-plan', {'claim_id':claim,'objective':'Repeat on other hardware.',
            'status':'planned','conditions':'A second device, same inputs',
            'metric':{'name':'latency','definition':'time from input to output','unit':'ms','comparison':'same device clean inputs'}})
        return claim

    def test_preview_cancel_stale_and_partial_results_do_not_confirm(self):
        key = self.app.intake.create((self.app.episode_id,'main','thesis'))
        self.app.intake.keep(key,'observation','Not enough source information.')
        before = self.app.paper.history.manifest()
        with self.assertRaises(ContractError): self.research.prepare('confirm',item_id=key)
        preview = self.research.prepare('confirm',item_id=self.result())
        self.assertEqual(before,self.app.paper.history.manifest())
        self.research.cancel()
        with self.assertRaises(ContractError): self.research.commit(preview)
        preview = self.research.prepare('confirm',item_id=self.result())
        self.app.keep_note('Newer writing invalidates this comparison.')
        with self.assertRaises(ContractError): self.research.commit(preview)
        self.assertEqual(before,self.app.paper.history.manifest())
        self.assertEqual(0,self.store.load().work.history.watermark)

    def test_full_new_content_argument_selected_record_correction_later_episode_restart(self):
        observation = self.confirm_result()
        self.assertEqual(1,self.app.paper.history.watermark)
        self.assertEqual('이 환경에서는 잡음이 지연을 늘렸다.',self.app.draft()['text'])
        claim = self.author(observation)
        preview = self.research.prepare('reasoning')
        self.assertEqual([], self.app.paper.history.view('main')['changes'])
        self.research.commit(preview)
        view = self.app.paper.history.view('main')
        self.assertIn(claim,{c['id'] for c in view['changes']})
        self.assertEqual('입력 외의 조건을 고정했다.',view['judgment']['rationale'])
        self.assertEqual(2,len(self.app.claim_uses(observation)))
        self.assertEqual(1,len([n for n in self.app.view['nodes'] if n['id']==observation]))
        plan = next(c for c in view['changes'] if c['kind']=='experiment-plan')
        self.assertEqual('planned',plan['body']['status'])
        self.app.select(observation)
        correction = self.app.intake.create((self.app.episode_id,'main',observation))
        for f,v in {'observation':'보정 후 지연시간은 23 ms였다.','value':'23','rationale':'Timer offset was 1 ms.'}.items():
            self.app.intake.keep(correction,f,v)
        self.research.commit(self.research.prepare('correct',item_id=correction))
        earlier = self.app.episode_id
        self.app.unfinished[(*self.app.context_key(),'note')] = ['남겨 둔 입력']
        self.research.commit(self.research.prepare('next',question='다른 하드웨어에서도 재현되는가?'))
        self.assertNotEqual(earlier,self.app.episode_id)
        self.assertEqual(2,len(self.app.paper.history.episodes()))
        evidence = self.app.paper.history.view('main',episode_id=earlier)['evidence'][0]
        self.assertEqual('23',evidence['value'])
        self.assertEqual(['24','23'],[e['value'] for e in evidence['history']])
        confirmation = next(decode(c)['id'] for c in self.app.paper.history.commands
            if decode(c)['operation_type']=='record-evidence-event' and decode(c)['payload']['action']=='confirm')
        self.assertEqual('24',self.app.paper.history.view('main',at_operation=confirmation)['evidence'][0]['value'])
        self.app.recovery.save(self.app)
        self.store.close()
        with PersonalProjectStore(self.directory) as store:
            project = store.load(); restored = project_workspace(project)
            self.assertEqual(self.app.paper.history.manifest(),restored.paper.history.manifest())
            self.assertIn(['남겨 둔 입력'],restored.unfinished.values())
            restored.switch_context(earlier,'main'); restored.select('thesis')
            self.assertEqual('입력 외의 조건을 고정했다.',restored.draft()['rationale'])
            self.assertFalse(project.work.history.authorization_verified)
        self.assertEqual(self.source,(self.paper/'paper.tex').read_bytes())

    def test_failed_record_keeps_live_writing_and_prior_science(self):
        key = self.result(); before = self.app.paper.history.manifest()
        saved = (self.directory/'personal.cbp').read_bytes()
        preview = self.research.prepare('confirm',item_id=key)
        with patch('claimbranch.application.paper_work_store.os.replace',side_effect=OSError('injected replace failure')):
            with self.assertRaises(ContractError): self.research.commit(preview)
        self.assertEqual(saved,(self.directory/'personal.cbp').read_bytes())
        self.assertEqual(before,self.app.paper.history.manifest())
        self.assertEqual('24',self.app.intake.get(key)['kept']['value'])

    def test_refusal_outside_personal_mode_and_expired_preview(self):
        self.app.recovery.personal_project = False
        with self.assertRaises(ContractError): self.research.prepare('next',question='Another question')
        self.app.recovery.personal_project = True
        preview = self.research.prepare('confirm',item_id=self.result())
        self.research.clock = lambda: 2000000301
        with self.assertRaises(ContractError): self.research.commit(preview)

    def test_mutated_preview_cannot_record_other_fields_or_science(self):
        preview=self.research.prepare('confirm',item_id=self.result())
        preview.display['result']['value']='Changed after comparison'
        with self.assertRaises(ContractError): self.research.commit(preview)
        self.assertEqual(0,self.store.load().work.history.watermark)

    def test_retained_ai_origin_is_not_relabelled_manual_when_recording(self):
        from claimbranch.core.review import Judgment, Proposal
        self.app.keep_draft('Initial reading','The measured conditions are bounded.')
        session=self.app.review.session()
        inherited=Judgment.start('new-study',self.app.episode_id).edit('Initial reading','The measured conditions are bounded.')
        inherited=inherited.use_proposal(Proposal('retained-proposal','new-study',self.app.episode_id,'Retained AI wording','a'*64))
        session._judgment=inherited
        session._prior_dispatches=1  # A legitimate retained adoption includes its spent request.
        session.edit(inherited.text,inherited.rationale)
        preview=self.research.prepare('reasoning', explanation_state='leave-for-later')
        self.assertTrue(preview.display['ai_origin_retained'])
        self.research.commit(preview)
        self.assertIn('ai',[c['contributor'] for c in self.store.load().work.history.view('main')['judgment']['history']])
        self.assertFalse(self.app.paper.ai_available)

    def test_correction_cannot_silently_ignore_new_units_or_conditions(self):
        observation=self.confirm_result()
        key=self.app.intake.create((self.app.episode_id,'main',observation))
        for f,v in {'observation':'23 µs','value':'23','unit':'µs','rationale':'Correct units'}.items():
            self.app.intake.keep(key,f,v)
        before=self.app.paper.history.manifest()
        with self.assertRaisesRegex(ContractError,'unit'): self.research.prepare('correct',item_id=key)
        self.assertEqual(before,self.store.load().work.history.manifest())
        self.assertEqual('µs',self.app.intake.get(key)['kept']['unit'])

    def test_confirmation_retains_limitations_and_names_existing_copy(self):
        key=self.result(); preview=self.research.prepare('confirm',item_id=key)
        self.assertNotIn('rationale',preview.display['result'])
        self.assertIn('Other hardware unmeasured',preview.display['confirmation_note'])
        self.research.commit(preview)
        observation=self.app.intake.recorded_copy(key)
        self.assertIn('Other hardware unmeasured',observation['history'][0]['rationale'])
        self.app.select('thesis')
        with self.assertRaisesRegex(ContractError,'already'): self.research.prepare('confirm',item_id=key)

    def test_correction_draft_is_consumed_only_after_successful_save(self):
        observation=self.confirm_result()
        key=self.app.intake.create((self.app.episode_id,'main',observation))
        for f,v in {'observation':'Corrected latency','value':'23','rationale':'Timer offset'}.items():
            self.app.intake.keep(key,f,v)
        self.research.commit(self.research.prepare('correct',item_id=key))
        self.assertNotIn(key,{i['id'] for i in self.app.intake.items()})
        reopened=project_workspace(self.store.load())
        self.assertNotIn(key,{i['id'] for i in reopened.intake.items()})
        with self.assertRaises(ContractError): self.research.prepare('correct',item_id=key)
        self.assertEqual(['24','23'],[e['value'] for e in self.store.load().work.history.view('main')['evidence'][0]['history']])

    def test_next_episode_can_record_its_own_reasoning_but_old_selection_cannot_repeat(self):
        observation=self.confirm_result(); self.author(observation)
        self.research.commit(self.research.prepare('reasoning'))
        self.app.keep_draft('Another reading','Different question')
        with self.assertRaisesRegex(ContractError,'already'): self.research.prepare('reasoning')
        self.research.commit(self.research.prepare('next',question='Does it reproduce?'))
        self.app.keep_draft('Tentative new reading','Earlier observation remains available')
        self.research.commit(self.research.prepare('reasoning'))
        self.assertEqual(2,len([raw for raw in self.app.paper.history.commands if decode(raw)['operation_type']=='apply-selected-merge']))

    def test_uncertain_record_freezes_live_save_and_reopens_recorded_copy(self):
        from claimbranch.application.tui_work_recovery import WorkReopenRequired
        key=self.result(); before=self.app.paper.history.manifest()
        preview=self.research.prepare('confirm',item_id=key)
        original=self.store._sync
        def sync(descriptor):
            if descriptor==self.store._dir: raise OSError('Injected directory sync failure')
            return original(descriptor)
        with patch.object(self.store,'_sync',side_effect=sync):
            with self.assertRaises(WorkReopenRequired): self.research.commit(preview)
        self.assertEqual(before,self.app.paper.history.manifest())
        self.assertEqual('24',self.app.intake.get(key)['kept']['value'])
        with self.assertRaises(WorkReopenRequired): self.app.recovery.save(self.app)
        self.store.close()
        with PersonalProjectStore(self.directory) as store:
            self.assertEqual(1,store.load().work.history.watermark)

    def test_post_save_view_failure_freezes_before_another_save(self):
        from claimbranch.application import personal_research as module
        from claimbranch.application.tui_work_recovery import WorkReopenRequired
        preview=self.research.prepare('confirm',item_id=self.result())
        original=module._install
        def install(app,*args):
            if app is self.app: raise KeyError('Injected live install failure')
            return original(app,*args)
        with patch.object(module,'_install',side_effect=install):
            with self.assertRaises(WorkReopenRequired): self.research.commit(preview)
        with self.assertRaises(WorkReopenRequired): self.app.recovery.save(self.app)
        self.assertEqual(1,self.store.load().work.history.watermark)
