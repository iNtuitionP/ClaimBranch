"""Owned graph revisions: originals, atomic refusal, explicit kinds and return."""
import unittest
from copy import deepcopy
from application import test_manuscript_anchors as prior
from claimbranch.application.graph_edits import editable_record,prepare_edits,recheck_edits
from claimbranch.application.personal_archive import personal_backup,split_personal_backup
from claimbranch.application.personal_project import PersonalProjectStore,EDIT_PERSONAL_MAGIC
from claimbranch.application.tui_project import project_workspace
from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_capacity import decode


class GraphEditTests(unittest.TestCase):
    setUp=prior.ManuscriptAnchorTests.setUp
    register=prior.ManuscriptAnchorTests.register

    def edit(self,key='C',project=None,**body):
        p=project or self.project;r=editable_record(p,key);r['title']='Rubric improvement does not establish writing quality';r['body'].update(body)
        return prepare_edits(p,[r],'Retain the scientific limitation.')

    def test_title_and_content_keep_originals_and_backup_and_query(self):
        p,review=self.edit(statement='Rubric improvement alone is insufficient.')
        self.assertEqual(self.project.work.history.commands,p.work.history.commands[:-1]);self.assertEqual(self.project.work.history.seed,p.work.history.seed)
        restored=split_personal_backup(personal_backup(p));self.assertEqual(p.payload,restored.payload)
        app=project_workspace(restored);app.select('C');self.assertEqual('Rubric improvement does not establish writing quality',app.title('C'))
        self.assertIn('Rubric improvement alone is insufficient.',str(app.detail()));self.assertTrue(review['review_required'])
        with PersonalProjectStore.create(self.work,project_id=p.project_id) as store:store.save(p,preview=self.preview)
        self.assertTrue((self.work/'personal.cbp').read_bytes().startswith(EDIT_PERSONAL_MAGIC))
        with PersonalProjectStore(self.work) as store:self.assertEqual(p.payload,store.load().payload)

    def test_observation_append_only_and_context_reinterpretation_refused(self):
        old=self.project.work.history.view('main')['evidence'][0]
        p,_=self.edit('O',statement='Corrected result.',value='2')
        new=p.work.history.view('main')['evidence'][0]
        self.assertEqual(old['history'],new['history'][:-1]);self.assertEqual('correct',new['history'][-1]['action'])
        run=old['run_id']
        with self.assertRaisesRegex(ContractError,'metric and conditions'):self.edit(run,conditions='Changed measurement setting')
        changed,_=self.edit(run,method='Revised description with original conditions.')
        self.assertEqual(self.project.work.history.commands,changed.work.history.commands[:-1])

    def test_invalid_edge_or_kind_refuses_entire_revision(self):
        edge=next(r for r in self.project.work.history.view('main')['changes'] if r['kind']=='scientific-edge')['id']
        for body in (dict(target_id='missing'),dict(source_id='C',target_id='C'),dict(edge_type='proves')):
            with self.assertRaises(ContractError):self.edit(edge,**body)
        r=editable_record(self.project,'O');r.update(kind='claim',body=editable_record(self.project,'C')['body'])
        with self.assertRaisesRegex(ContractError,'Keep identity'):prepare_edits(self.project,[r],'Cannot retag evidence.')

    def test_replacement_keeps_original_edges_and_explicit_relinks_validate(self):
        r=editable_record(self.project,'C');r.update(id='replacement',replaces='O',title='A separately identified reading')
        p,_=prepare_edits(self.project,[r],'Keep original; no silent re-links.')
        self.assertEqual(self.project.work.history.view('main')['evidence'],p.work.history.view('main')['evidence'])
        oldedges=[e for e in self.project.work.history.view('main')['changes'] if e['kind']=='scientific-edge']
        self.assertEqual(oldedges,[e for e in p.work.history.view('main')['changes'] if e['kind']=='scientific-edge'])
        edge=editable_record(self.project,oldedges[0]['id']);edge['body']['source_id']='replacement'
        linked,_=prepare_edits(self.project,[r,edge],'Explicitly move this edge; retain other relationships.')
        self.assertEqual('replacement',next(e for e in linked.work.history.view('main')['changes'] if e['id']==edge['id'])['body']['source_id'])
        self.assertIn('C',{c['id'] for c in linked.work.history.view('main')['claims']})

    def test_stale_project_or_manuscript_refuses(self):
        p,preview=self.edit();recheck_edits(self.project,preview)
        with self.assertRaisesRegex(ContractError,'changed'):recheck_edits(p,preview)
        original=self.project.payload
        with self.assertRaises(ContractError):self.edit(parent_ids=['C'])
        self.assertEqual(original,self.project.payload)

    def test_anchor_metadata_retains_exact_file_and_source(self):
        p,_=self.register('abstract');path=self.paper/'abstract.tex';original=path.read_bytes()
        p,review=self.edit('abstract',p,expresses=['T'])
        self.assertEqual(original,path.read_bytes());self.assertEqual(['T'],p.work.history.view('main')['manuscript_anchors']['abstract']['expresses'])

    def test_ai_origin_survives_later_human_title_edit(self):
        r=editable_record(self.project,'C');r['title']='AI suggested title'
        p,_=prepare_edits(self.project,[r],'Explicitly selected proposal.','ai')
        p,_=self.edit(project=p)
        origins={r['origin'] for r in p.work.history.view('main')['graph_revisions']}
        self.assertEqual({'human','ai'},origins)

    def test_tui_closed_choice_retains_cancelled_input_and_preview_requires_reading(self):
        from types import SimpleNamespace
        from claimbranch.application.tui_graph_edit import GraphEditUI
        from claimbranch.application.tui_project_source import exact_path_buffer
        term=SimpleNamespace(modal='graph-edit-fields',app=SimpleNamespace(),screen=SimpleNamespace(getmaxyx=lambda:(24,80)))
        ui=GraphEditUI(term);ui.key=('ep','C');ui.record=editable_record(self.project,'C');ui.origin='human';ui.relinks=[];ui.base_history='synthetic';ui.proposed=None;ui.proposal_source=None;ui._fields()
        ui.fields[0]=('title',exact_path_buffer('Unfinished title'))
        ui.key_event('escape');self.assertEqual('Unfinished title',ui.sessions[ui.key][1][0][1].text)
        term.modal='graph-edit-preview';ui.seen_end=False;ui.key_event('r');self.assertEqual('graph-edit-preview',term.modal)

    def test_every_chooser_draws_without_mutating_history(self):
        from types import SimpleNamespace
        from claimbranch.application.tui_graph_edit import GraphEditUI
        from claimbranch.application.tui import Frame
        app=project_workspace(self.project)
        term=SimpleNamespace(app=app,modal='graph-edit-kind')
        ui=GraphEditUI(term);ui.record=editable_record(self.project,'C');ui.options=['claim','experiment-plan'];ui.option=0
        for mode in ('graph-edit-kind','graph-edit-choice','graph-edit-relinks'):
            term.modal=mode;ui.relinks=[]
            for w,h in ((144,42),(120,32),(80,24)):
                self.assertIsNotNone(ui.draw(Frame(w,h)))

    def test_observation_title_alone_does_not_append_a_correction(self):
        old=self.project.work.history.view('main')['evidence']
        p,_=self.edit('O')
        self.assertEqual(old,p.work.history.view('main')['evidence'])
        self.assertEqual(self.project.work.history.watermark,p.work.history.watermark)

    def test_imported_run_origin_remains_available_after_revision(self):
        key=self.project.work.history.view('main')['experiments'][0]['id']
        p,_=self.edit(key,method='A clearer description of the original procedure.')
        before=self.project.work.history.view('main')['experiments'][0]['imported_source']
        self.assertEqual(before,p.work.history.view('main')['experiments'][0]['imported_source'])

    def test_operation_identity_cannot_be_used_as_replacement_source(self):
        record=editable_record(self.project,'C');record.update(id='new-claim',replaces=decode(self.project.work.history.commands[0],purpose='history')['id'])
        with self.assertRaisesRegex(ContractError,'existing original'):prepare_edits(self.project,[record],'An operation is not a scientific node.')

    def test_removed_anchor_association_keeps_before_impact_in_comparison(self):
        p,_=self.register('abstract');record=editable_record(p,'abstract');record['body']['expresses']=[]
        candidate,preview=prepare_edits(p,[record],'The manuscript use was removed.')
        # The exact graphs retain the old association; impact starts at the changed anchor.
        self.assertTrue(any(e['source_id']=='abstract' and e['target_id']=='C' for e in preview['before']['relations']))
        self.assertFalse(any(e['source_id']=='abstract' and e['target_id']=='C' for e in preview['after']['relations']))

    def test_scoped_pending_work_matches_full_projection_without_replaying_other_episodes(self):
        from claimbranch.application.paper_service import PaperService
        from claimbranch.fixtures import replay_example
        history=replay_example('manual',series=True);service=PaperService(history)
        episode=history.episodes()[-1]['id'];scoped=service.pending_work(episode_id=episode)
        whole=PaperService(history).pending_work()
        self.assertEqual([i for i in whole['items'] if i['episode_id']==episode],scoped['items'])
        self.assertIsNone(service._pending_work)

    def test_selected_share_preserves_title_and_declared_origin_without_raw_revision(self):
        from claimbranch.application.canonical_share import prepare_share,verify_share
        record=editable_record(self.project,'C');record['title']='A bounded selected title'
        project,_=prepare_edits(self.project,[record],'Retain origin.','ai')
        raw=prepare_share(project,dict(schema='claimbranch.share-selection/v1',record_ids=['C'],reason_ids=[]))
        self.assertTrue(verify_share(project,raw));output=decode(raw,purpose='project')
        self.assertEqual('claimbranch.canonical-share/v2',output['schema'])
        claim=next(r for r in output['records'] if r['kind']=='claim' and r['content'].get('title'))
        self.assertEqual('A bounded selected title',claim['content']['title']);self.assertIn('ai',claim['content']['origins'])
        self.assertNotIn('graph_revisions',str(output));self.assertNotIn('proposal_source',str(output))

    def test_closed_experiment_schema_refuses_status_and_claim_fields(self):
        for extra in ({'status':'planned'},{'claim_id':'C'}):
            key=self.project.work.history.view('main')['experiments'][0]['id'];record=editable_record(self.project,key);record['body'].update(extra)
            with self.assertRaises(ContractError):prepare_edits(self.project,[record],'An experiment is not a plan or scientific edge.')

    def test_editor_records_from_experiment_lens_and_stale_preview_preserves_input(self):
        from types import SimpleNamespace
        from claimbranch.application.personal_project import PersonalProjectRecovery
        from claimbranch.application.tui_graph_edit import GraphEditUI
        from claimbranch.application.tui import Buffer,Frame
        with PersonalProjectStore.create(self.work,project_id=self.project.project_id) as store:
            store.save(self.project,preview=self.preview);app=project_workspace(self.project)
            app.recovery=PersonalProjectRecovery(store,app,self.project)
            app.switch_lens('evidence',evidence_id='O');app.select('C');app.notes[app.context_key()]='Retain my research writing'
            term=SimpleNamespace(app=app,modal=None,screen=SimpleNamespace(getmaxyx=lambda:(32,120)))
            ui=GraphEditUI(term);ui.open();ui.fields[0]=('title',Buffer('Edited beside the experiment'));ui.fields[-1]=('reason',Buffer('Keep this limited reading.'))
            ui.key_event('keep');self.assertEqual('graph-edit-preview',term.modal)
            ui.scroll=100000;ui.draw(Frame(120,32));ui.key_event('r');ui.confirmation.insert('record');ui.key_event('enter')
            self.assertIsNone(term.modal);self.assertEqual(('evidence','O','C'),(app.lens,app.evidence_root,app.selected_id))
            self.assertEqual('Edited beside the experiment',app.title('C'));self.assertIn('Retain my research writing',app.notes.values())
            app.recovery.save(app);before=app.paper.history.manifest()
            ui.open();ui.fields[0]=('title',Buffer('Unrecorded changed title'));ui.fields[-1]=('reason',Buffer('Fresh reason.'))
            ui.key_event('keep');ui.scroll=100000;ui.draw(Frame(120,32));ui.key_event('r')
            app.notes[app.context_key()]='Newer writing changes the review binding'
            ui.confirmation.insert('record');ui.dispatch('enter')
            self.assertEqual('graph-edit-fields',term.modal);self.assertEqual(before,app.paper.history.manifest())
            self.assertEqual('Unrecorded changed title',ui.fields[0][1].text)

    def test_kind_choice_acceptance_uses_thesis_identity_and_relinks_remain_opt_in(self):
        from types import SimpleNamespace
        from claimbranch.application.tui_graph_edit import GraphEditUI
        from claimbranch.application.tui import Buffer
        app=project_workspace(self.project)
        term=SimpleNamespace(app=app,modal='graph-edit-fields',screen=SimpleNamespace(getmaxyx=lambda:(32,120)))
        ui=GraphEditUI(term);ui.key=('local-episode','O');ui.record=editable_record(self.project,'O');ui.origin='human';ui.relinks=[];ui.base_history=app.history_digest;ui.proposed=None;ui.proposal_source=None;ui._fields()
        ui.key_event('\x0b');self.assertEqual('graph-edit-kind',term.modal)
        ui.option=ui.options.index('claim');ui.key_event('enter')
        self.assertEqual('graph-edit-fields',term.modal);self.assertEqual('O',ui.record['replaces']);self.assertNotEqual('O',ui.record['id'])
        self.assertEqual([app.view['thesis_id']],ui.record['body']['parent_ids']);self.assertEqual([],ui.relinks)
        self.assertEqual('claim',ui.record['kind']);self.assertTrue(ui.choices()==[])

    def test_replacement_has_public_mapping_and_exact_share_round_trip(self):
        from claimbranch.application.canonical_share import prepare_share,verify_share
        record=editable_record(self.project,'C');record.update(id='replacement',replaces='O',title='An explicit new reading')
        project,_=prepare_edits(self.project,[record],'Retain observation; introduce reasoning.')
        raw=prepare_share(project,dict(schema='claimbranch.share-selection/v1',record_ids=['replacement'],reason_ids=[]))
        self.assertTrue(verify_share(project,raw));self.assertIn(b'An explicit new reading',raw)
        self.assertNotIn(b'original_item',raw)

    def test_edge_revision_marks_dependent_claims_for_review_without_rewriting_status(self):
        edge=next(r for r in self.project.work.history.view('main')['changes'] if r['kind']=='scientific-edge')
        record=editable_record(self.project,edge['id']);record['body']['rationale']='A newly scoped rationale; recheck dependent wording.'
        project,review=prepare_edits(self.project,[record],'Changed rationale still needs dependent review.')
        nodes={n['id']:n for n in review['after']['nodes']}
        self.assertTrue(nodes['C']['content']['review_required']);self.assertTrue(nodes['T']['content']['review_required'])
        before=next(c for c in self.project.work.history.view('main')['claims'] if c['id']=='C')['status']
        self.assertEqual(before,nodes['C']['content']['status'])

    def test_default_edge_and_anchor_captions_do_not_publish_private_ids_or_reasons(self):
        edge=next(r for r in self.project.work.history.view('main')['changes'] if r['kind']=='scientific-edge')
        record=editable_record(self.project,edge['id'])
        self.assertEqual('supports connection',record['title']);self.assertNotEqual(edge['body']['rationale'],record['title'])
        project,_=self.register('private-anchor-identity');record=editable_record(project,'private-anchor-identity')
        self.assertEqual('Registered text block',record['title'])
