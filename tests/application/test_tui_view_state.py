"""Presentation return is disposable and never contains writing or authority."""
import json
import unittest
from copy import deepcopy
from pathlib import Path
from application import test_graph_edits as prior
from claimbranch.application.tui_view_state import snapshot,apply,load,save,NAME
from claimbranch.application.tui_project import project_workspace
from claimbranch.application.personal_project import PersonalProjectStore,PersonalProjectRecovery
from claimbranch.application.personal_archive import personal_backup,split_personal_backup


class ViewStateTests(unittest.TestCase):
    setUp=prior.GraphEditTests.setUp

    def test_two_entry_roots_restore_independently_without_writing_or_consent(self):
        app=project_workspace(self.project);run=app.view['nodes'][0]['id']
        run=next(n['id'] for n in app.view['nodes'] if n['kind']=='experiment-record')
        app.notes[app.context_key()]='PRIVATE-WRITING-NOT-A-VIEW'
        app.switch_lens('evidence',evidence_id=run);app.select('C');app.graph_pan=(13,7);old=app._navigation()
        app.switch_lens('argument');app.select('T');app.switch_lens('evidence',evidence_id='O');app.select('C')
        value=snapshot(app);raw=json.dumps(value)
        self.assertNotIn('PRIVATE-WRITING',raw);self.assertNotIn('consent',raw);self.assertNotIn('judgment',raw)
        reopened=project_workspace(self.project);apply(reopened,value)
        self.assertEqual(('evidence','O','C'),(reopened.lens,reopened.evidence_root,reopened.selected_id))
        reopened.switch_lens('evidence',evidence_id=run)
        self.assertEqual(old['selected_id'],reopened.selected_id);self.assertEqual(old['collapsed'],reopened.collapsed)
        self.assertEqual(self.project.work.history.manifest(),reopened.paper.history.manifest())

    def test_private_atomic_file_corruption_and_backup_exclusion(self):
        with PersonalProjectStore.create(self.work,project_id=self.project.project_id) as store:
            store.save(self.project,preview=self.preview)
            app=project_workspace(self.project);app.switch_lens('evidence',evidence_id='O');raw=save(store,app)
            self.assertEqual(0,(self.work/NAME).stat().st_mode&0o077)
            other=project_workspace(self.project);self.assertEqual(raw,load(store,other));self.assertEqual('O',other.evidence_root)
            self.assertEqual(self.project.payload,split_personal_backup(store.backup()).payload)
            (self.work/NAME).write_text('{bad')
            fresh=project_workspace(self.project);self.assertIsNone(load(store,fresh));self.assertEqual('argument',fresh.lens)
            self.assertEqual(self.project.payload,store.load().payload)

    def test_missing_stale_root_and_owner_changes_revalidate(self):
        app=project_workspace(self.project);app.switch_lens('evidence',evidence_id='O');value=snapshot(app)
        entry=value['entries'][value['active']];entry['root']='removed';entry['selected_id']='removed';entry['revision']='0'*64
        entry['selected_path']=['removed'];entry['folds']=[dict(id='C',path=['removed','C'])]
        fresh=project_workspace(self.project);apply(fresh,value)
        self.assertNotEqual('removed',fresh.evidence_root);self.assertIn(fresh.selected_id,fresh.nodes);self.assertNotIn('C',fresh.collapsed)

    def test_symlink_and_foreign_project_never_touch_target_or_science(self):
        with PersonalProjectStore.create(self.work,project_id=self.project.project_id) as store:
            store.save(self.project,preview=self.preview);target=self.root/'other';target.write_text('retain target');(self.work/NAME).symlink_to(target)
            app=project_workspace(self.project);self.assertIsNone(load(store,app))
            from claimbranch.core.canonical import ContractError
            with self.assertRaises(ContractError):save(store,app)
            self.assertEqual('retain target',target.read_text())
        value=snapshot(app);value['project_id']='another'
        with self.assertRaises(ContractError):apply(app,value)

    def test_recovery_saves_navigation_even_when_writing_is_unchanged(self):
        with PersonalProjectStore.create(self.work,project_id=self.project.project_id) as store:
            store.save(self.project,preview=self.preview);app=project_workspace(self.project)
            recovery=PersonalProjectRecovery(store,app,self.project);app.recovery=recovery
            recovery.save(app);saved=recovery.project.payload
            app.switch_lens('evidence',evidence_id='O');recovery.save(app)
            self.assertEqual(self.project.work.history.manifest(),recovery.project.work.history.manifest())
        with PersonalProjectStore(self.work) as store:
            app=project_workspace(store.load());app.recovery=PersonalProjectRecovery(store,app,store.load())
            self.assertEqual('O',app.evidence_root)

    def test_folded_impact_reaches_every_declared_anchor_after_correction(self):
        from claimbranch.application.graph_edits import editable_record,prepare_edits
        project=self.project
        for name,kind,expresses,plots in [('abstract','text',('C',),()),('figure','figure',('C',),('O',))]:
            project,_=prior.GraphEditTests.register(self,name,kind,expresses,plots,project=project)
        record=editable_record(project,'O');record['title']='Corrected result';record['body'].update(statement='Corrected synthetic observation.',value='2')
        project,review=prepare_edits(project,[record],'Retain the original measurement.')
        app=project_workspace(project);app.switch_lens('evidence',evidence_id='O');app.collapsed=set(app.nodes)
        impact=app.service.anchor_impact(['O'])
        self.assertTrue({'abstract','figure'}<=set(impact['potentially_affected_anchor_ids']))
        self.assertIn('review-required',app.fold_inventory('O')['statuses'])

    def test_extreme_pan_is_bounded_and_argument_roots_are_canonical(self):
        app=project_workspace(self.project);app.graph_pan=(10**12,-10**12);app.evidence_root='O'
        value=snapshot(app);entry=value['entries'][value['active']]
        self.assertIsNone(entry['root']);self.assertEqual(dict(x=1000000,y=-1000000),entry['viewport'])

    def test_deeply_corrupt_json_resets_only_presentation(self):
        with PersonalProjectStore.create(self.work,project_id=self.project.project_id) as store:
            store.save(self.project,preview=self.preview)
            path=self.work/NAME;path.write_text('['*2000+']'*2000);path.chmod(0o600)
            app=project_workspace(self.project);self.assertIsNone(load(store,app))
            self.assertEqual(self.project.payload,store.load().payload);self.assertEqual('argument',app.lens)

    def test_view_cache_budget_discards_only_old_presentation(self):
        from unittest.mock import patch
        from claimbranch.application import tui_view_state
        app=project_workspace(self.project);app.switch_lens('evidence',evidence_id='O');app.select('C')
        original=app.paper.history.manifest()
        with patch.object(tui_view_state,'MAX_BYTES',1500):value=snapshot(app)
        self.assertLessEqual(len(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()),1500)
        self.assertEqual('C',value['entries'][value['active']]['selected_id'])
        self.assertEqual(original,app.paper.history.manifest())
