"""Offline paper-scale migration qualification; source claims are not truth."""
import base64
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import zipfile

from claimbranch.core.paper_capacity import encode,source_bytes
from .test_original_ledger import paper_fixture


def prepared_workload(root, *, shared=False):
    """Synthetic setup only: 430 source records, 30 literal figure associations."""
    from claimbranch.core.argument_import import history_from_import
    from claimbranch.application.project_work import ProjectWork,preview_association
    from claimbranch.application.manuscript_anchors import read_binding
    from claimbranch.application.paper_work_store import PaperWork
    paper=root/'paper';paper.mkdir();work=root/'work';work.mkdir(mode=0o700)
    subprocess.run(['/usr/bin/git','init','-q',str(paper)],check=True)
    figures=[f'\\begin{{figure}}\n\\caption{{Synthetic result {i}.}}\\label{{fig:{i}}}\n\\end{{figure}}\n' for i in range(30)]
    manuscript=('\\begin{document}\n\\section{Argument}\\label{sec:argument}\n'+''.join(figures)+'\\end{document}\n').encode()
    (paper/'paper.tex').write_bytes(manuscript)
    selector=lambda key:dict(schema='claimbranch.tex-selector/v1',kind='label',value=key)
    preview=preview_association(paper,'paper.tex','anchor',work,selector=selector('sec:argument'))
    value=paper_fixture();raw=encode(value,purpose='project')
    history=history_from_import(raw,anchor_id='anchor',registered_at='2026-10-16T00:00:00Z')
    def append(version,key,kind,payload):
        nonlocal history
        command=dict(schema_version=version,id=key,project_id='paper-workload',episode_id='local',created_at='2026-10-16T00:00:00Z',operation_type=kind,expected_heads=dict(history.heads),evidence_watermark=history.watermark,payload=payload)
        if version==15:command['contribution_origin']='human'
        history=history.append(command)
    append(14,'open-local','open-episode',dict(title='New research',question='Which claim needs independent testing?'))
    source=preview.recheck()['source']
    for i in range(30):
        binding,block=read_binding({**source,'anchor_id':f'A{i}','selector':selector(f'fig:{i}')})
        append(15,f'register-A{i}','register-manuscript-anchor',dict(id=f'A{i}',kind='figure',source=binding,block_digest=hashlib.sha256(block).hexdigest(),block=[base64.b64encode(block).decode()],expresses=[f'C{i}'],plots=[f'O{i}'],parents=[],rationale='Explicit synthetic manuscript use.'))
    if shared:append(16,'shared-audit','set-audit-encoding',dict(encoding='shared-values/v1'))
    project=ProjectWork.create(PaperWork.create(history),preview,import_input=raw)
    return value,raw,project,preview,manuscript


COLD_OPERATION=r'''
import hashlib,json,resource,sys,time
from pathlib import Path
started=time.monotonic()
from claimbranch.application.personal_project import PersonalProjectStore
from claimbranch.application.project_work import ProjectWork
from claimbranch.application.tui_project import project_workspace
root=Path(sys.argv[1]);mode=sys.argv[2]
if mode=='register':
 project=ProjectWork((root/'candidate.json').read_bytes())
 with PersonalProjectStore.create(root/'work',project_id=project.project_id) as store:store._save_restored(project)
elif mode=='restore':
 project=PersonalProjectStore.restore_backup((root/'backup.cbp').read_bytes(),root/'restored')
else:
 with PersonalProjectStore(root/'work') as store:
  project=store.load()
  if mode=='backup':(root/'backup.cbp').write_bytes(store.backup())
app=project_workspace(project)
assert len(app.paper._personal_explanations)==40
assert len(app.paper._recorded_origins)==1
assert len(app.paper.history.view('main')['manuscript_anchors'])==30
assert not app.paper.history.authorization_verified
print(json.dumps(dict(mode=mode,seconds=time.monotonic()-started,peak_rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,project_bytes=len(project.payload),project_sha256=hashlib.sha256(project.payload).hexdigest(),manifest_sha256=hashlib.sha256(project.work.history.manifest()).hexdigest())))
'''

COLD_REPLAY=r'''
import hashlib,json,resource,sys,time
from pathlib import Path
started=time.monotonic()
from claimbranch.core.research_history import ResearchHistory
from claimbranch.core.paper_capacity import encode
value=json.loads((Path(sys.argv[1])/'candidate.json').read_bytes())['work']
history=ResearchHistory.replay(encode(value['seed'],purpose='history'),tuple(encode(c,purpose='history') for c in value['commands']))
manifest=history.manifest()
print(json.dumps(dict(seconds=time.monotonic()-started,peak_rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,manifest_sha256=hashlib.sha256(manifest).hexdigest())))
'''


class MigrationJourneyTests(unittest.TestCase):
    def test_clean_runtime_full_paper_sources_reviews_labels_return_and_selected_share(self):
        from types import SimpleNamespace
        from claimbranch.application.tui_project import project_workspace
        from claimbranch.application.personal_research import PersonalResearch
        from claimbranch.application.paper_proposal_work import _cause_validation,_validate_explanation_topics
        from claimbranch.application.tui_work_recovery import snapshot_value
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.canonical_share import prepare_share,verify_share,SELECTION_SCHEMA
        from claimbranch.application.tui import compose
        from scripts.build_source import build_source
        with tempfile.TemporaryDirectory(dir='/private/tmp' if sys.platform=='darwin' else None) as folder:
            root=Path(folder);value,raw,project,preview,manuscript=prepared_workload(root,shared=True)
            app=project_workspace(project);app.recovery=SimpleNamespace(personal_project=True,project=project);app.select('C20')
            service=PersonalResearch(app,clock=lambda:2000000000);partials=[]
            # One real owned comparison supplies the exact source/request shape.
            # Generate the other synthetic past drafts constructively, then
            # validate every distinct cause through the same strict cold reader.
            # Repeating 40 live branch constructions only inflated setup cost;
            # no acceptance/consent from this fixture assembly is claimed.
            app.keep_draft('Unresolved comparison 0.','Synthetic original reason 0: independent blind tests remain necessary.')
            pending=service.prepare('reasoning');template=deepcopy(pending.origin_record['cause']);service.cancel()
            self.assertEqual([],template['origin_digests'])
            self.assertEqual(['interpretation'],[a['kind'] for a in template['request']['amendments']])
            from dataclasses import asdict
            from claimbranch.core.review import Judgment
            for i in range(40):
                cause=deepcopy(template)
                text=f'Unresolved comparison {i}.';reason=f'Synthetic original reason {i}: independent blind tests remain necessary.'
                cause['judgment']=asdict(Judgment.start(project.project_id,'local').edit(text,reason))
                cause['request']['draft_id']=f'fixture-comparison-{i}';cause['request']['draft_revision']=0
                cause['request']['amendments'][0].update(id=f'fixture-reading-{i}',body=dict(statement=text,observation_ids=[]))
                cause['request']['selected_ids']=[f'fixture-reading-{i}']
                science=_cause_validation(app.paper.history,cause);topic=science['topics'][0]['id']
                explanation=_validate_explanation_topics(science['topics'],dict(state='partial',entries=[dict(topic_id=topic,text=f'Unfinished explanation {i}.',reuse_rationale=False)]))
                partials.append(dict(cause=cause,explanation=explanation))
            # Fixture assembly is not 40 accepted judgments. Complete snapshot
            # validation checks every original cause when materializing work.
            app.paper._personal_explanations=partials
            project=project.with_work(PaperWork.create(app.paper.history,workspace=snapshot_value(app)))
            app=project_workspace(project)
            from claimbranch.application.personal_project import PersonalProjectStore,PersonalProjectRecovery
            with PersonalProjectStore.create(root/'work',project_id=project.project_id) as store:
                store.save(project,preview=preview);app.recovery=PersonalProjectRecovery(store,app,project)
                app.keep_draft('The quality proxy still needs an independent test.','Earlier source judgments do not establish validity.')
                service=PersonalResearch(app,clock=lambda:2000000000)
                service.commit(service.prepare('reasoning',explanation_state='leave-for-later'))
                project=store.load()
            from claimbranch.application.project_work import _scientific_ids
            h=project.work.history;seed=json.loads(h.seed);reference_ids={seed['claim_id'],seed['anchor_id']}
            for ref,_ in h.heads:
                view=h.view(ref)
                reference_ids.update(row['id'] for row in [*view['evidence'],*view['experiments'],*view['changes']])
                for name in ('manuscript_anchors','companion_dependencies','co_reports','critiques','critique_links','protocols','experiment_associations','gate_amendments','gate_results','outcome_assessments'):reference_ids.update(view.get(name,{}))
                reference_ids.update(gate['id'] for protocol in view.get('protocols',{}).values() for gate in protocol['gates'])
                reference_ids.update(e['measurement']['id'] for o in view['evidence'] for e in o['history'] if 'measurement' in e)
            self.assertEqual(reference_ids,_scientific_ids(h))
            # Start every cold operation from a clean store in the extracted
            # runtime. No source checkout imports or test modules are available.
            for item in (root/'work').iterdir():item.unlink()
            (root/'candidate.json').write_bytes(project.payload);(root/'candidate.json').chmod(0o600)
            archive=root/'source.zip';build_source(archive);runtime=root/'runtime'
            with zipfile.ZipFile(archive) as package:package.extractall(runtime)
            env=dict(os.environ);env.pop('PYTHONPATH',None);metrics=[]
            (root/'restored').mkdir(mode=0o700)
            for mode in ('register','open','backup','restore'):
                result=subprocess.run([sys.executable,'-B','-c',COLD_OPERATION,str(root),mode],cwd=runtime,env=env,capture_output=True,text=True,timeout=180)
                self.assertEqual(0,result.returncode,result.stderr);item=json.loads(result.stdout);metrics.append(item)
                self.assertLessEqual(item['seconds'],60,item)
                self.assertLessEqual(item['peak_rss']*(1 if sys.platform=='darwin' else 1024),2*1024**3,item)
            self.assertEqual(1,len({m['project_sha256'] for m in metrics}));self.assertEqual(1,len({m['manifest_sha256'] for m in metrics}))
            result=subprocess.run([sys.executable,'-B','-c',COLD_REPLAY,str(root)],cwd=runtime,env=env,capture_output=True,text=True,timeout=90)
            self.assertEqual(0,result.returncode,result.stderr);replay=json.loads(result.stdout)
            self.assertLessEqual(replay['seconds'],30,replay)
            self.assertLessEqual(replay['peak_rss']*(1 if sys.platform=='darwin' else 1024),2*1024**3,replay)
            self.assertEqual(metrics[0]['manifest_sha256'],replay['manifest_sha256'])
            for lens,subject in [('argument','C20'),('evidence','O20')]:
                started=time.monotonic();app.switch_lens(lens,evidence_id=subject if lens=='evidence' else None);app.select(subject);compose(app,132,38)
                self.assertLessEqual(time.monotonic()-started,20)
                self.assertEqual(100,len(app.paper.history.view('main')['evidence']))
            shared=prepare_share(project,dict(schema=SELECTION_SCHEMA,record_ids=['C20','O20'],reason_ids=[]))
            self.assertTrue(verify_share(project,shared))
            for file in value['files']:
                self.assertNotIn(file['name'].encode(),shared);self.assertNotIn(source_bytes(file['source'])[:256],shared)
            self.assertNotIn(b'Unfinished explanation',shared);self.assertEqual(manuscript,(root/'paper/paper.tex').read_bytes())
            print('MIGRATION-COLD-METRICS '+json.dumps(dict(operations=metrics,replay=replay)),flush=True)


class ColdReturnReaderTests(unittest.TestCase):
    def setUp(self):
        from .test_original_registration import OriginalProjectTests
        OriginalProjectTests.setUp(self)

    def test_distinct_causes_match_full_previews_and_cannot_poison_shared_source(self):
        from types import SimpleNamespace
        from claimbranch.application.personal_research import PersonalResearch
        from claimbranch.application.tui_project import project_workspace
        from claimbranch.application.paper_service import PaperService
        from claimbranch.application.paper_branch import judgment_value
        from claimbranch.application.paper_proposal_work import cause_science,explanation_topics,_imported_source_service,_cause_validation
        from claimbranch.core.canonical import ContractError
        app=project_workspace(self.project);app.recovery=SimpleNamespace(personal_project=True,project=self.project);app.select('C')
        service=PersonalResearch(app,clock=lambda:2000000000)
        for i,text in enumerate(('Independent interpretation 0.','Independent interpretation 1.','Cafe\u0301 비교: 판단은 미완성입니다.')):
            app.keep_draft(text,f'Keep uncertainty {i} explicit.')
            pending=service.prepare('reasoning');cause=deepcopy(pending.origin_record['cause']);service.cancel()
            expected=PaperService(app.paper.history).preview_changes(cause['request'],judgment_value(cause['judgment']),source_node_id='C')
            baseline=deepcopy(expected)
            actual=cause_science(app.paper.history,cause)
            self.assertEqual(expected,actual)
            self.assertEqual(explanation_topics(cause,expected),explanation_topics(cause,actual))
            compact=_cause_validation(app.paper.history,cause)
            self.assertEqual({k:expected[k] for k in ('selection','amendments','provenance')},
                {k:compact[k] for k in ('selection','amendments','provenance')})
            self.assertEqual(explanation_topics(cause,expected),compact['topics'])
            compact['amendments'][0]['after']['body']['statement']='A poisoned caller copy.'
            compact['provenance']['judgment']['history'][0]['text']='Forged caller contribution.'
            compact['topics'][0]['node_ids'].append('missing-node')
            again=_cause_validation(app.paper.history,cause)
            for key in ('selection','amendments','provenance'):self.assertEqual(expected[key],again[key])
            self.assertEqual(explanation_topics(cause,expected),again['topics'])
            compact['topics'].clear()
            self.assertEqual(explanation_topics(cause,expected),_cause_validation(app.paper.history,cause)['topics'])
            actual['graphs']['after']['nodes'].clear()
            source=_imported_source_service(app.paper.history);source.query('main')['nodes'].clear()
            self.assertEqual(expected,cause_science(app.paper.history,cause))
            expected['provenance']['source_judgments'].append({'forged':'caller-only'})
            expected['provenance']['imported_sources'][0]['contributor']='human'
            expected['amendments'][0]['before']={'forged':'caller-only'}
            expected['amendments'][0]['after']['body']['statement']='Caller mutation'
            self.assertEqual(baseline,PaperService(app.paper.history).preview_changes(cause['request'],judgment_value(cause['judgment']),source_node_id='C'))
            self.assertEqual(baseline,cause_science(app.paper.history,cause))
            self.assertEqual({k:baseline[k] for k in ('selection','amendments','provenance')},
                {k:_cause_validation(app.paper.history,cause)[k] for k in ('selection','amendments','provenance')})
            for path in ('source','request','owner','judgment','amendments','selected_ids'):
                bad=deepcopy(cause)
                if path=='source':bad[path]['digest']='0'*64
                elif path=='request':bad[path]['view_digest']='0'*64
                elif path=='owner':bad[path][2]='missing-node'
                elif path=='amendments':bad['request']['amendments'][0]['body']['statement']='A different interpretation.'
                elif path=='selected_ids':bad['request']['selected_ids']=['missing-amendment']
                else:bad[path]['text']='A forged judgment without its contribution chain.'
                for check in (cause_science,_cause_validation):
                    with self.subTest(field=path,check=check.__name__),self.assertRaises(ContractError):check(app.paper.history,bad)

    def test_warm_seed_version_cannot_validate_a_changed_or_noncanonical_seed(self):
        from claimbranch.core.research_history import ResearchHistory
        from claimbranch.core.canonical import ContractError
        h=self.project.work.history;self.assertEqual(14,h.schema_version)
        value=json.loads(h.seed);value['initial_argument']['records'][0]['body']['statement']='Unsourced replacement'
        with self.assertRaises(ContractError):ResearchHistory(encode(value,purpose='history'),h.commands)
        with self.assertRaises(ContractError):ResearchHistory(h.seed+b' ',h.commands)
        self.assertEqual(h.manifest(),ResearchHistory(h.seed,h.commands).manifest())

    def test_query_byte_cache_is_detached_and_binds_non_head_scientific_changes(self):
        from claimbranch.application.paper_service import PaperService
        h=self.project.work.history;original=PaperService(h).query('main');returned=PaperService(type(h).replay(h.seed,h.commands)).query('main')
        self.assertEqual(original,PaperService(h)._query('main'))
        returned['nodes'].clear();returned['judgment']={'forged':'caller'}
        self.assertEqual(original,PaperService(h).query('main'))
        run=h.view('main')['experiments'][0]
        experiment={key:deepcopy(run[key]) for key in ('id','question','method','conditions','metric','source_ref')};experiment['id']='new-run'
        later=h.append(dict(schema_version=14,id='record-new-run',project_id=self.project.project_id,episode_id='local',created_at='2033-05-18T03:33:20Z',operation_type='record-experiment',expected_heads=dict(h.heads),evidence_watermark=h.watermark,payload=experiment))
        self.assertEqual(h.heads,later.heads);self.assertEqual(h.watermark,later.watermark)
        current=PaperService(later).query('main')
        self.assertNotEqual(original['digest'],current['digest']);self.assertNotEqual(original['history_digest'],current['history_digest'])

    def test_identity_inventory_uses_same_episode_and_head_refs_as_views(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from claimbranch.application.project_work import _scientific_ids
        # A historical episode can own a distinct branch map. Inventory must
        # use the same default episode resolution as history.view(ref), and
        # must not include branches that history.heads does not enumerate.
        state=dict(seed=dict(schema_version=14,claim_id='thesis',anchor_id='anchor'),
                   experiments={},events=[],active_episode=None,
                   branches=dict(main=dict(changes={'wrong-current':{}})),
                   episodes={'past':dict(branches=dict(main=dict(changes={'past-main':{}}),
                       alternative=dict(changes={'past-alternative':{}}),
                       unlisted=dict(changes={'not-a-head':{}})))})
        history=SimpleNamespace(schema_version=14,seed=b'seed',commands=(),
                                heads=(('main','main-head'),('alternative','alternative-head')))
        with patch('claimbranch.core.research_history._reduce',return_value=state):
            self.assertEqual({'thesis','anchor','past-main','past-alternative'},_scientific_ids(history))
            from claimbranch.core.canonical import ContractError
            history.heads=(('missing-ref','head'),)
            with self.assertRaisesRegex(ContractError,'unknown reasoning ref'):_scientific_ids(history)

    def test_initial_read_translates_io_errors_and_rolls_back_unverified_identity(self):
        from unittest.mock import patch
        from claimbranch.application.personal_project import PersonalProjectStore
        from claimbranch.application.paper_storage_codec import decode as load,encode as dump
        from claimbranch.core.canonical import ContractError
        store=PersonalProjectStore(self.work);before=store._project
        with patch.object(store,'_check_directory'),patch.object(store,'_read',side_effect=OSError('synthetic unreadable file')):
            with self.assertRaisesRegex(ContractError,'work could not be read'):store.load()
        self.assertFalse(store._known_project);self.assertEqual(before,store._project)
        value=load(self.project.payload);value['public_ids']=[]
        bad=store._codec.seal(dump(value))
        with patch.object(store,'_check_directory'),patch.object(store,'_read',return_value=bad):
            with self.assertRaises(ContractError):store.load()
        self.assertFalse(store._known_project);self.assertEqual(before,store._project)
        good=store._codec.seal(self.project.payload)
        with patch.object(store,'_check_directory'),patch.object(store,'_read',return_value=good):
            self.assertEqual(self.project.payload,store.load().payload)
        self.assertTrue(store._known_project);self.assertEqual(self.project.project_id,store._project)

    def test_workspace_validation_cache_keys_all_bytes_and_never_caches_a_session(self):
        from unittest.mock import patch
        from claimbranch.application import paper_work_store as module
        from claimbranch.application.project_commands import prepare_shared_audit
        from claimbranch.application.tui_project import project_workspace
        from claimbranch.application.tui_work_recovery import snapshot_value
        from claimbranch.application.paper_storage_codec import decode as load,encode as dump
        from claimbranch.core.canonical import ContractError
        app=project_workspace(self.project);app.notes[app.context_key()]='Original partial note.'
        work=module.PaperWork.create(app.paper.history,workspace=snapshot_value(app))
        converted,_=prepare_shared_audit(self.project.with_work(work));raw=converted.work.payload
        module._validate_imported_workspace.cache_clear();original=module.validate_workspace
        with patch.object(module,'validate_workspace',wraps=original) as validation:
            first=module.PaperWork(raw);second=module.PaperWork(raw)
            self.assertEqual(1,validation.call_count)
            self.assertEqual(first.payload,second.payload)
            value=load(raw);value['workspace']['notes'][0]['text']='Newer writing still needs validation.'
            module.PaperWork(dump(value));self.assertEqual(2,validation.call_count)
            value['workspace']['selection'][2]='missing-node'
            with self.assertRaises(ContractError):module.PaperWork(dump(value))
            self.assertEqual(3,validation.call_count)
        before=module._validate_imported_workspace.cache_info()
        self.assertIsNone(module._validate_imported_workspace(converted.work.history,module.canonical_bytes(load(raw)['workspace'])))
        self.assertEqual(before.hits+1,module._validate_imported_workspace.cache_info().hits)

    def test_causal_topics_match_full_review_for_edges_plans_and_source_metadata(self):
        self.maxDiff=None
        from claimbranch.application.paper_service import PaperService
        from claimbranch.application.paper_proposal_work import explanation_topics,_cause_validation
        from claimbranch.core.review import Judgment
        h=self.project.work.history
        # Add explicit figure/table/caption paths. The core source bindings and
        # normal full comparison are the independent oracle for the lean reader.
        from .test_manuscript_anchors import ManuscriptAnchorTests
        for name,kind,expresses,plots,parents in [('fig','figure',('C',),('O',),()),('cap','caption',(),(),('fig',))]:
            self.project,_=ManuscriptAnchorTests.register(self,name,kind,expresses,plots,parents,self.project)
        h=self.project.work.history;service=PaperService(h);view=service.query('main')
        judgment=Judgment.start(view['project_id'],'local').edit('An explicitly bounded interpretation.','Independent validation is still needed.')
        metric=h.view('main')['experiments'][0]['metric']
        reading=dict(id='I-new',kind='interpretation',body=dict(statement=judgment.text,observation_ids=['O']))
        plan=dict(id='P-new',kind='experiment-plan',body=dict(claim_id='C',objective='Test the competing explanation.',status='planned',conditions='Blind evaluation.',metric=metric))
        for edge_type in ('supports','challenges','qualifies'):
            edge=dict(id='edge-new',kind='scientific-edge',body=dict(source_id='I-new',target_id='C',edge_type=edge_type,rationale='Explicitly selected relation.'))
            for amendments in ([reading,edge],[plan],[reading,edge,plan]):
                request=dict(schema_version=1,project_id=view['project_id'],episode_id='local',ref='main',view_digest=view['digest'],draft_id='draft-independent',draft_revision=0,amendments=amendments,selected_ids=[a['id'] for a in amendments])
                from dataclasses import asdict
                cause=dict(owner=['local','main','C'],source=dict(commands=len(h.commands),digest=view['digest']),request=request,judgment=asdict(judgment),origin_digests=[])
                from claimbranch.core import research_history as core
                core._paper_preview_basis.cache_clear()
                before_state=deepcopy(core._reduce(h.seed,h.commands))
                before_basis=deepcopy(core._paper_preview_basis(h.seed,h.commands,'main','local'))
                full=service.preview_changes(request,judgment,source_node_id='C')
                self.assertEqual(before_state,core._reduce(h.seed,h.commands))
                self.assertEqual(before_basis,core._paper_preview_basis(h.seed,h.commands,'main','local'))
                compact=_cause_validation(h,cause)
                self.assertEqual(before_state,core._reduce(h.seed,h.commands))
                self.assertEqual(before_basis,core._paper_preview_basis(h.seed,h.commands,'main','local'))
                # Reference the previous eager isolation strategy independently;
                # hypothetical branch sharing must preserve exact public bytes.
                from unittest.mock import patch
                original_reduce=core._reduce;before_state=deepcopy(original_reduce(h.seed,h.commands))
                original_view=core._view
                def isolated_view(state,ref,episode_id=None,**_):return original_view(state,ref,episode_id)
                with patch.object(core,'_reduce',side_effect=lambda seed,commands:deepcopy(original_reduce(seed,commands))),patch.object(core,'_fork_preview_state',side_effect=lambda state,episode:deepcopy(state)),patch.object(core,'_view',side_effect=isolated_view),patch.object(core,'_paper_preview_basis',side_effect=lambda seed,commands,ref,episode:isolated_view(original_reduce(seed,commands),ref,episode)):
                    reference=PaperService(h).preview_changes(request,judgment,source_node_id='C')
                self.assertEqual(reference,full)
                self.assertEqual(before_state,original_reduce(h.seed,h.commands))
                self.assertEqual(full,service.preview_changes(request,judgment,source_node_id='C'))
                self.assertEqual(before_basis,core._paper_preview_basis(h.seed,h.commands,'main','local'))
                self.assertEqual(explanation_topics(cause,full),compact['topics'])
                for key in ('selection','amendments','provenance'):self.assertEqual(full[key],compact[key])

    def test_co_report_and_companion_reach_matches_full_graph(self):
        from .test_co_report import CoReportTests
        from claimbranch.application.co_report import prepare_co_report
        from claimbranch.application.paper_service import _graph,_anchor_reach
        from claimbranch.core.paper_capacity import decode
        fixture=CoReportTests();fixture.setUp();self.addCleanup(fixture.doCleanups)
        project,_=fixture.register('sensitivity-use',expresses=('T',),project=fixture.base())
        project,_=prepare_co_report(project,fixture.request());h=project.work.history
        seed=decode(h.seed,purpose='history');view=h.view('main')
        original=deepcopy(view)
        full=_graph(seed,view);compact=_graph(seed,view,_borrow_payloads=True)
        self.assertEqual(full,compact);self.assertEqual(original,view)
        for roots in (['O'],['primary'],['sensitivity'],['C'],['T']):
            self.assertEqual(_anchor_reach(full,roots,'after'),_anchor_reach(compact,roots,'after'))

    def test_full_preview_byte_refusal_is_also_enforced_during_cause_validation(self):
        from unittest.mock import patch
        from dataclasses import asdict
        from claimbranch.application import paper_service as module
        from claimbranch.core.review import Judgment
        from claimbranch.core.canonical import ContractError
        project=self.project;service=module.PaperService(project.work.history);original=module._graph
        def large_projection(*args,**kwargs):
            # Each single view fits; both phases together exceed the old limit.
            return {**original(*args,**kwargs),'render-size-probe':['x'*16384]*257}
        with patch.object(module,'_graph',side_effect=large_projection):
            view=service.query('main');judgment=Judgment.start(view['project_id'],'local').edit('A bounded interpretation.','Retain its evidence context.')
            amendment=dict(id='I-size',kind='interpretation',body=dict(statement=judgment.text,observation_ids=['O']))
            request=dict(schema_version=1,project_id=view['project_id'],episode_id='local',ref='main',view_digest=view['digest'],draft_id='draft-size',draft_revision=0,amendments=[amendment],selected_ids=['I-size'])
            cause=dict(owner=['local','main','C'],source=dict(commands=len(project.work.history.commands),digest=view['digest']),request=request,judgment=asdict(judgment),origin_digests=[])
            errors=[]
            for operation in (lambda:service.preview_changes(request,judgment,source_node_id='C'),lambda:service._causal_validation(cause)):
                with self.assertRaisesRegex(ContractError,'capacity manifest-bytes') as caught:operation()
                errors.append(str(caught.exception))
            self.assertEqual(errors[0],errors[1])

    def test_digest_bearing_preview_exact_limit_and_one_byte_band_refuse(self):
        from unittest.mock import patch
        from types import SimpleNamespace
        from claimbranch.application.personal_research import PersonalResearch
        from claimbranch.application.tui_project import project_workspace
        from claimbranch.application.paper_service import PaperService
        from claimbranch.application.paper_branch import judgment_value
        from claimbranch.core.paper_capacity import MANIFEST_BYTES
        from claimbranch.core.canonical import ContractError
        app=project_workspace(self.project);app.recovery=SimpleNamespace(personal_project=True,project=self.project);app.select('C')
        app.keep_draft('A bounded reading.','Keep the source limitation.')
        owned=PersonalResearch(app);pending=owned.prepare('reasoning');cause=pending.origin_record['cause'];owned.cancel()
        service=PaperService(app.paper.history);service.query('main');normal=service._bytes
        for extra in (40,76):
            def sized(value):
                return b'x'*(MANIFEST_BYTES-extra) if value.get('schema')=='claimbranch.paper-changes/v1' else normal(value)
            with patch.object(service,'_bytes',side_effect=sized),patch('claimbranch.core.paper_capacity.encoded_size',return_value=MANIFEST_BYTES-extra):
                for operation in (lambda:service.preview_changes(cause['request'],judgment_value(cause['judgment']),source_node_id='C'),lambda:service._causal_validation(cause)):
                    if extra==40:
                        with self.assertRaisesRegex(ContractError,f'capacity manifest-bytes: {MANIFEST_BYTES+36} / {MANIFEST_BYTES}'):operation()
                    else:self.assertIn('selection',operation())


class CanonicalSizeTests(unittest.TestCase):
    def test_exact_bytes_with_escaping_unicode_aliases_and_all_json_types(self):
        from claimbranch.core.paper_capacity import encoded_size,encoding_value,decode
        shared={'é':['line\n"\\\t',None,True,False,-(2**53-1),2**53-1]}
        values=[{},[],(),shared,{'a':shared,'b':shared},{'a':[shared],'b':shared},['e\u0301','한글','😀','\x00'],{'e\u0301':('value',1)},{'z':{'z':2,'a':1},'a':0}]
        for value in values:
            with self.subTest(value=value):
                raw=encode(value,purpose='manifest')
                from claimbranch.core.canonical import _normalize
                reference=json.dumps(_normalize(value,collection_limit=2048),ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')
                self.assertEqual(reference,raw)
                self.assertEqual(len(raw),encoded_size(value,purpose='manifest'))
                self.assertEqual(decode(raw,purpose='manifest'),encoding_value(value,purpose='manifest'))
                self.assertEqual(json.dumps(decode(raw,purpose='manifest'),ensure_ascii=False),
                    json.dumps(encoding_value(value,purpose='manifest'),ensure_ascii=False))

    def test_hypothetical_branch_fork_matches_eager_copy_for_archived_and_active_episodes(self):
        from claimbranch.core.research_history import _fork_preview_state,_episode_branches
        for version in (2,5,14):
            for archived in (False,True):
                for own in (False,True):
                    source=dict(seed=dict(schema_version=version,episode_id='current'),branches={'main':{'head':'base'}},active_episode='current',
                        episodes={'current':{},'past':{}},interpretation_owners={})
                    episode='past' if archived else 'current'
                    if own:source['episodes'][episode]['branches']={'main':{'head':'prior'}}
                    before=deepcopy(source);expected=deepcopy(source);actual=_fork_preview_state(source,episode)
                    for state in (expected,actual):
                        _episode_branches(state,episode if version>=3 else None)[0]['main']={'head':'candidate'}
                        if version>=3:state['interpretation_owners']['reading']=episode
                    self.assertEqual(expected,actual);self.assertEqual(before,source)

    def test_same_type_unicode_depth_collection_and_byte_overflow_refusals(self):
        from claimbranch.core.paper_capacity import encoded_size
        from claimbranch.core.canonical import ContractError
        deep=None
        for i in range(18):deep=[deep]
        for value in (1.5,2**53,'x'*16385,'\ud800',{'e\u0301':1,'é':2},{1:'bad key'},[0]*2049,deep,['x'*16384]*513):
            for operation in (encode,encoded_size):
                with self.subTest(operation=operation.__name__),self.assertRaises(ContractError):operation(value,purpose='manifest')
