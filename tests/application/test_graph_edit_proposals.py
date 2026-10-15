"""Owned typed replies enter the same exact human-editable revision path."""
from copy import deepcopy
import unittest
from application import test_graph_edits as prior
from claimbranch.application.graph_edits import proposal_edit,prepare_edits
from claimbranch.application.personal_archive import personal_backup,split_personal_backup
from claimbranch.core.canonical import ContractError


class GraphEditProposalTests(unittest.TestCase):
    setUp=prior.GraphEditTests.setUp
    def entry(self):
        return dict(request_id='owned-request',result=dict(schema='claimbranch.provider-result/v2',status='ok',critique=None,items=[dict(id='edit-C',action='edit',kind='claim',target_id='C',body=dict(role='main',parent_ids=[dict(domain='context',id='T')],statement='Rubric improvement alone is insufficient.',scope='Only these measured conditions.'))]))

    def test_selected_item_human_edit_and_ai_source_survive_return(self):
        entry=self.entry();record,source=proposal_edit(self.project,entry,'edit-C')
        record['title']='Human revised the AI title'
        candidate,preview=prepare_edits(self.project,[record],'Retain limitation.','mixed',source)
        returned=split_personal_backup(personal_backup(candidate))
        revision=returned.work.history.view('main')['graph_revisions'][-1]
        self.assertEqual('mixed',revision['origin']);self.assertEqual(entry['result']['items'][0],revision['proposal_source']['original_item'])
        self.assertEqual('owned-request',revision['proposal_source']['request_id'])
        self.assertEqual(self.project.work.history.commands,candidate.work.history.commands[:-1])

    def test_bad_type_missing_target_item_reference_and_self_edge_refuse(self):
        for field,value in (('kind','verdict'),('target_id','missing'),('action','create')):
            entry=self.entry();entry['result']['items'][0][field]=value
            with self.assertRaises(ContractError):proposal_edit(self.project,entry,'edit-C')
        entry=self.entry();entry['result']['items'][0]['body']['parent_ids'][0]['domain']='item'
        with self.assertRaisesRegex(ContractError,'Item-local'):proposal_edit(self.project,entry,'edit-C')
        entry=self.entry();entry['result']['items'][0]['body']['parent_ids'][0]['id']='C'
        record,source=proposal_edit(self.project,entry,'edit-C')
        with self.assertRaisesRegex(ContractError,'parents'):prepare_edits(self.project,[record],'Refuse cyclic AI proposal.','ai',source)

    def test_unselected_items_not_in_history_and_plain_advice_cannot_be_graph(self):
        entry=self.entry();omitted=deepcopy(entry['result']['items'][0]);omitted['id']='omitted';omitted['body']['statement']='OMITTED-LITERAL';entry['result']['items'].append(omitted)
        record,source=proposal_edit(self.project,entry,'edit-C');candidate,_=prepare_edits(self.project,[record],'Select only one.','ai',source)
        self.assertNotIn(b'OMITTED-LITERAL',candidate.work.history.commands[-1])
        with self.assertRaises(ContractError):proposal_edit(self.project,dict(request_id='advice',result={'answer':'Natural language only'}),'edit-C')

    def test_recorded_direct_ai_revision_is_visible_in_origin_reader_with_ai_off(self):
        from types import SimpleNamespace
        from claimbranch.application.tui_project import project_workspace
        from claimbranch.application.tui_proposals import ProposalsUI
        record,source=proposal_edit(self.project,self.entry(),'edit-C')
        candidate,_=prepare_edits(self.project,[record],'Keep the limitation.','ai',source)
        app=project_workspace(candidate);ui=ProposalsUI(SimpleNamespace(app=app));ui.owner=app.work_key()
        shown='\n'.join(ui.content('origins'))
        self.assertIn('DIRECT GRAPH REVISION',shown);self.assertIn('owned-request',shown)
        self.assertIn('Rubric improvement alone is insufficient.',shown)
        self.assertFalse(app.paper.ai_available)
