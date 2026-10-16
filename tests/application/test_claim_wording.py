from claimbranch.application.personal_project import METADATA_PERSONAL_MAGIC
from claimbranch.application.personal_archive import METADATA_BACKUP_MAGIC
"""Owned wording review, explicit reporting declarations and durable return."""
import unittest
import json
import io
from unittest.mock import patch
from application import test_manuscript_anchors as anchor_tests
from claimbranch.application.claim_wording import prepare_revision, recheck_revision, lint, literal_present
from claimbranch.application.paper_service import PaperService
from claimbranch.application.tui_project import project_workspace
from claimbranch.application.personal_project import PersonalProjectStore, WORDING_PERSONAL_MAGIC
from claimbranch.application.personal_archive import split_personal_backup, WORDING_BACKUP_MAGIC
from claimbranch.core.paper_capacity import decode
from claimbranch.core.canonical import ContractError

class ClaimWordingTests(unittest.TestCase):
    setUp=anchor_tests.ManuscriptAnchorTests.setUp
    register=anchor_tests.ManuscriptAnchorTests.register

    def policy(self,project=None,**changes):
        payload=dict(claim_id='C',grade='Direction only',limitation='Synthetic writing; no causal or universal conclusion.',
            allowed_wording=['The rubric score improved under these conditions.'],required_caveats=['Only these conditions.'],
            banned_phrases=['negligible','share'],placement=['appendix'],rationale='The support does not justify stronger wording.')
        payload.update(changes)
        return prepare_revision(project or self.project,'set-claim-wording',payload)

    def companion(self,project,**changes):
        payload=dict(id='co-report',target_id='C',companion_id='O',scope='anchor',status='active',rationale='Report the contrary sensitivity observation together.')
        payload.update(changes)
        return prepare_revision(project,'set-claim-companion',payload)

    def context(self,project,anchor,**changes):
        payload=dict(anchor_id=anchor,placement='abstract',paragraphs=[],rationale='Explicit marked-block use.')
        payload.update(changes)
        return prepare_revision(project,'set-anchor-context',payload)

    def test_reporting_policy_is_separate_from_status_and_keeps_prefix_and_origin(self):
        project,preview=self.policy()
        before=self.project.work.history.view('main');after=project.work.history.view('main')
        self.assertEqual(before['claims'],after['claims'])
        self.assertEqual(self.project.work.history.seed,project.work.history.seed)
        self.assertEqual(self.project.work.history.commands,project.work.history.commands[:-1])
        policy=after['wording_policies']['C']
        self.assertEqual('Direction only',policy['grade']);self.assertEqual(['appendix'],policy['placement'])
        self.assertTrue(any(ref['contributor']=='ai' for ref in policy['source_refs']))
        node=next(n for n in preview['after']['nodes'] if n['id']=='C')
        self.assertEqual(policy,node['content']['wording_policy'])
        app=project_workspace(project);app.select('C');self.assertIn('Direction only',str(app.detail()))
        self.assertEqual('claimbranch.project-work/v18',decode(project.payload,purpose='project')['schema'])

    def test_banned_phrase_placement_and_missing_companion_with_readonly_lint(self):
        project,_=self.register('abstract')
        path=self.paper/'abstract.tex';path.write_text('% claimbranch:start id=abstract\nThe difference is negligible; shares are not share.\n% claimbranch:end id=abstract\n')
        project,_=self.register('other',project=project)
        from claimbranch.application.manuscript_anchors import prepare_registration
        project,_=prepare_registration(project,manuscript='abstract.tex',anchor_id='abstract',kind='text',expresses=['C'],rationale='Read this wording.')
        project,_=self.policy(project);project,_=self.companion(project);project,_=self.context(project,'abstract')
        raw=path.read_bytes();original=project.payload
        result=lint(project.work.history);codes={w['code'] for w in result['warnings'] if w['anchor_id']=='abstract'}
        self.assertTrue({'banned-phrase','placement-mismatch','missing-companion-association','caveat-text-not-found'}<=codes)
        self.assertEqual(raw,path.read_bytes());self.assertEqual(original,project.payload)
        self.assertFalse(result['scientific_validity_verified']);self.assertFalse(result['write_available'])
        self.assertFalse(literal_present('shares shareholder','share'));self.assertTrue(literal_present('a SHARE.','share'))

    def test_paragraph_scope_requires_explicit_current_association_and_retirement_retains_original(self):
        path=self.paper/'caption.tex';path.write_text('% claimbranch:start id=caption\nFirst claim.\n\nSecond evidence.\n% claimbranch:end id=caption\n')
        from claimbranch.application.manuscript_anchors import prepare_registration
        project,_=prepare_registration(self.project,manuscript='caption.tex',anchor_id='caption',kind='caption',expresses=['C'],plots=['O'],rationale='Scope-specific reading.')
        project,_=self.companion(project,scope='paragraph')
        self.assertIn('paragraph-coverage-unknown',{w['code'] for w in lint(project.work.history)['warnings']})
        project,_=self.context(project,'caption',placement='appendix',paragraphs=[dict(index=1,expresses=['C'],plots=[]),dict(index=2,expresses=[],plots=['O'])])
        self.assertIn('missing-paragraph-companion',{w['code'] for w in lint(project.work.history)['warnings']})
        project,_=self.context(project,'caption',placement='appendix',paragraphs=[dict(index=1,expresses=['C'],plots=['O'])])
        self.assertFalse(lint(project.work.history)['warnings'])
        old=project.work.history.commands[-1]
        retired,_=self.companion(project,scope='paragraph',status='retired')
        self.assertEqual('retired',retired.work.history.view('main')['companion_dependencies']['co-report']['status'])
        self.assertIn(old,retired.work.history.commands)

    def test_changed_missing_macros_and_comments_report_limits_not_certification(self):
        project,_=self.register('abstract');project,_=self.policy(project)
        path=self.paper/'abstract.tex';path.write_text('% claimbranch:start id=abstract\n\\emph{Shares} % negligible\n% claimbranch:end id=abstract\n')
        self.assertIn('source-unavailable-or-changed',{w['code'] for w in lint(project.work.history)['warnings']})
        from claimbranch.application.manuscript_anchors import prepare_registration
        project,_=prepare_registration(project,manuscript='abstract.tex',anchor_id='abstract',kind='text',expresses=['C'],rationale='Read changed text.')
        warnings=lint(project.work.history)['warnings']
        self.assertIn('unsupported-tex-semantics',{w['code'] for w in warnings})
        self.assertNotIn('banned-phrase',{w['code'] for w in warnings})
        path.unlink();self.assertIn('source-unavailable-or-changed',{w['code'] for w in lint(project.work.history)['warnings']})

    def test_stale_policy_preview_and_source_changes_refuse_without_mutation(self):
        anchored,_=self.register('abstract');candidate,preview=self.policy(anchored)
        recheck_revision(anchored,preview)
        changed,_=self.policy(anchored,grade='Exploratory only')
        with self.assertRaisesRegex(ContractError,'changed'):recheck_revision(changed,preview)
        path=self.paper/'abstract.tex';path.write_bytes(path.read_bytes()+b'% another edit\n')
        with self.assertRaisesRegex(ContractError,'changed'):recheck_revision(anchored,preview)
        self.assertNotEqual(anchored.payload,candidate.payload)

    def test_frame_backup_notes_and_fresh_return_keep_restrictions_and_sources(self):
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.tui_work_recovery import snapshot_value
        app=project_workspace(self.project);app.select('C');app.notes[app.context_key()]='Keep my unfinished wording.'
        original=self.project.with_work(PaperWork.create(app.paper.history,workspace=snapshot_value(app)))
        project,_=self.policy(original);project,_=self.companion(project)
        with PersonalProjectStore.create(self.work,project_id=project.project_id) as store:
            store.save(project,preview=self.preview)
            self.assertTrue((self.work/'personal.cbp').read_bytes().startswith(METADATA_PERSONAL_MAGIC))
            backup=store.backup();self.assertTrue(backup.startswith(METADATA_BACKUP_MAGIC))
            returned=split_personal_backup(backup);self.assertEqual(project.payload,returned.payload)
            app=project_workspace(returned);app.select('C');self.assertIn('Keep my unfinished wording.',app.notes.values())
            self.assertIn('Direction only',str(app.detail()));self.assertIn('co-report',str(app.detail()))

    def test_invalid_endpoints_identity_or_paragraph_declarations_refuse_whole_revision(self):
        for change in (dict(claim_id='missing'),dict(placement=[]),dict(banned_phrases=['share','share'])):
            with self.assertRaises(ContractError):self.policy(**change)
        project,_=self.register('abstract')
        for change in (dict(companion_id='missing'),dict(companion_id='C'),dict(id='O'),dict(status='retired')):
            with self.assertRaises(ContractError):self.companion(project,**change)
        project,_=self.companion(project)
        with self.assertRaisesRegex(ContractError,'immutable'):self.companion(project,companion_id='T')
        for rows in ([dict(index=2,expresses=['C'],plots=[])],[dict(index=1,expresses=['C'],plots=['O'])]):
            with self.assertRaises(ContractError):self.context(project,'abstract',paragraphs=rows)

    def test_cli_dryrun_cancel_confirm_and_lint(self):
        from claimbranch.application.cli import main
        with PersonalProjectStore.create(self.work,project_id=self.project.project_id) as store:store.save(self.project,preview=self.preview)
        args=['project','claim-policy','--directory',str(self.work),'--claim','C','--grade','Direction only','--limitation','Synthetic only','--placement','appendix','--reason','Preserve scientific limits.']
        before=(self.work/'personal.cbp').read_bytes()
        with patch('sys.stdout',new_callable=io.StringIO) as output:self.assertEqual(0,main(args+['--dry-run']))
        self.assertIn('Direction only',output.getvalue());self.assertEqual(before,(self.work/'personal.cbp').read_bytes())
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',return_value=''),patch('builtins.print'):
            self.assertEqual(0,main(args))
        self.assertEqual(before,(self.work/'personal.cbp').read_bytes())
        def answer(prompt):return 'record' if prompt.startswith('Type record') else 'continue'
        with patch('sys.stdin.isatty',return_value=True),patch('sys.stdout.isatty',return_value=True),patch('builtins.input',side_effect=answer),patch('builtins.print'):
            self.assertEqual(0,main(args))
        with patch('sys.stdout',new_callable=io.StringIO) as output:self.assertEqual(0,main(['project','wording-lint','--directory',str(self.work)]))
        self.assertFalse(json.loads(output.getvalue())['write_available'])

    def test_policy_change_revokes_owned_reasoning_review_and_keeps_unfinished_reason(self):
        from claimbranch.application.personal_project import PersonalProjectRecovery
        from claimbranch.application.personal_research import PersonalResearch, _install
        with PersonalProjectStore.create(self.work,project_id=self.project.project_id) as store:
            store.save(self.project,preview=self.preview)
            app=project_workspace(self.project);app.recovery=PersonalProjectRecovery(store,app,self.project)
            app.select('C');app.keep_draft('Keep the qualified claim.','Only the limited reading is justified.')
            service=PersonalResearch(app);review=service.prepare('reasoning',explanation_state='leave-for-later')
            changed,_=self.policy()
            _install(app,changed.work.history,app.episode_id,app.ref,app.selected_id)
            with self.assertRaisesRegex(ContractError,'changed or expired'):service.commit(review)
            self.assertIn('Only the limited reading is justified.',str(__import__('claimbranch.application.tui_work_recovery',fromlist=['snapshot_value']).snapshot_value(app)))
            self.assertEqual(self.project.payload,store.load().payload)

    def test_companion_capacity_refuses_257_before_append_and_old_versions_remain_identical(self):
        from claimbranch.core.research_history import ResearchHistory
        history=self.project.work.history
        for index in range(256):
            history=history.append(dict(schema_version=7,id=f'operation-{index}',project_id=self.project.project_id,
                episode_id='local',created_at='2026-10-14T00:00:00Z',operation_type='set-claim-companion',
                expected_heads=dict(history.heads),evidence_watermark=history.watermark,
                payload=dict(id=f'companion-{index}',target_id='C',companion_id='O',scope='anchor',status='active',rationale='Synthetic repeated declaration.')))
        before=history.manifest()
        with self.assertRaisesRegex(ContractError,'companion_dependencies: 257 / 256'):
            history.append(dict(schema_version=7,id='operation-overflow',project_id=self.project.project_id,
                episode_id='local',created_at='2026-10-14T00:00:00Z',operation_type='set-claim-companion',
                expected_heads=dict(history.heads),evidence_watermark=history.watermark,
                payload=dict(id='overflow',target_id='C',companion_id='O',scope='anchor',status='active',rationale='Synthetic overflow.')))
        self.assertEqual(before,history.manifest());self.assertEqual(before,ResearchHistory(history.seed,history.commands).manifest())
        self.assertEqual(256,history.capacity()['resources']['companion_dependencies']['used'])

    def test_reporting_dependency_impact_and_saved_identity_are_not_support(self):
        project,_=self.register('abstract');project,_=self.companion(project,companion_id='T')
        service=PaperService(project.work.history);impact=service.anchor_impact(['T'])
        self.assertIn('abstract',impact['potentially_affected_anchor_ids'])
        relation=next(e for e in service.query('main')['relations'] if e['type']=='must-co-report')
        self.assertFalse(relation['scientific'])
        app=project_workspace(project);app.select('T')
        app.link_index=next(i for i,link in enumerate(app.display_links()) if link.kind=='must-co-report')
        self.assertIn('Reporting obligation',str(app.relationship_detail()))
        self.assertEqual(['T','C','abstract'],next(w['node_ids'] for w in impact['anchor_witness_paths'] if w['anchor_id']=='abstract'))

    def test_manual_profile_without_import_retains_policy_on_fresh_return(self):
        from claimbranch.application.paper_profile_project import new_paper_project
        original=new_paper_project(self.preview,'manual-paper','Synthetic paper','A manually limited thesis.','What next?')
        project,_=self.policy(original,claim_id='thesis')
        self.assertIsNone(decode(project.payload,purpose='project')['import_input_sha256'])
        returned=project_workspace(split_personal_backup(__import__('claimbranch.application.personal_archive',fromlist=['personal_backup']).personal_backup(project)))
        returned.select('thesis');self.assertIn('Direction only',str(returned.detail()))

    def test_actual_pty_policy_record_then_fresh_open_and_older_reader_refusal(self):
        import os,select,subprocess,sys,time,struct,fcntl,termios
        from types import ModuleType
        with PersonalProjectStore.create(self.work,project_id=self.project.project_id) as store:store.save(self.project,preview=self.preview)
        args=['project','claim-policy','--directory',str(self.work),'--claim','C','--grade','Direction only','--limitation','Synthetic only','--placement','appendix','--reason','Keep the limitation.']
        def terminal(arguments,record=False):
            master,slave=os.openpty();fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',40,140,0,0))
            process=subprocess.Popen([sys.executable,'-m','claimbranch',*arguments],stdin=slave,stdout=slave,stderr=slave,env=dict(os.environ,TERM='xterm-256color'))
            os.close(slave);output=b'';pending=b'';quit_sent=False;deadline=time.monotonic()+25
            try:
                while process.poll() is None and time.monotonic()<deadline:
                    if select.select([master],[],[],.1)[0]:
                        try:chunk=os.read(master,65536)
                        except OSError:break
                        output+=chunk;pending+=chunk
                        if record:
                            if b'Review: details / continue' in pending:os.write(master,b'continue\n');pending=b''
                            elif b'Enter: next page' in pending:os.write(master,b'\n');pending=b''
                            elif b'Type record to save' in pending:os.write(master,b'record\n');pending=b''
                        elif b'ClaimBranch' in output and not quit_sent:os.write(master,b'q');quit_sent=True
                self.assertEqual(0,process.wait(timeout=5),output[-3000:].decode(errors='replace'))
                if record:self.assertIn(b'Reporting restriction saved',output)
            finally:
                if process.poll() is None:process.kill();process.wait()
                os.close(master)
        terminal(args,True);terminal(['project','open','--directory',str(self.work)])
        raw=(self.work/'personal.cbp').read_bytes()
        old=__import__('pathlib').Path(__file__).with_name('legacy_personal_project.py').read_text()
        module=ModuleType('claimbranch.application.wording_old_reader');module.__package__='claimbranch.application'
        exec(compile(old,'legacy-personal-project','exec'),module.__dict__)
        with self.assertRaises(ContractError):module._PersonalCodec().open(raw)
        self.assertEqual(raw,(self.work/'personal.cbp').read_bytes())

    def test_reregistered_or_relocated_block_requires_fresh_placement_classification(self):
        project,_=self.register('abstract');project,_=self.policy(project);project,_=self.context(project,'abstract',placement='appendix')
        from claimbranch.application.manuscript_anchors import prepare_registration
        path=self.paper/'abstract.tex';raw=path.read_bytes();path.write_bytes(raw.replace(b'Synthetic',b'Changed'))
        project,_=prepare_registration(project,manuscript='abstract.tex',anchor_id='abstract',kind='text',expresses=['C'],rationale='New wording needs new placement declaration.')
        codes={w['code'] for w in lint(project.work.history)['warnings']}
        self.assertTrue({'anchor-context-stale','placement-unknown'}<=codes)
        project,_=self.context(project,'abstract',placement='appendix')
        (self.paper/'relocated.tex').write_bytes(path.read_bytes())
        project,_=prepare_registration(project,manuscript='relocated.tex',anchor_id='abstract',kind='text',expresses=['C'],rationale='Same text in another marked file.')
        self.assertIn('anchor-context-stale',{w['code'] for w in lint(project.work.history)['warnings']})

    def test_missing_historical_endpoint_has_coverage_marker_and_no_dangling_relation(self):
        from claimbranch.application.paper_service import _graph, _anchor_reach
        project,_=self.companion(self.project,companion_id='T')
        view=project.work.history.view('main');view['claims']=[c for c in view['claims'] if c['id']!='C'];view['changes']=[c for c in view['changes'] if c['id']!='C' and c['kind']!='scientific-edge']
        graph=_graph(decode(project.work.history.seed,purpose='history'),view)
        self.assertEqual(['co-report'],graph['reporting_dependencies_outside_view'])
        self.assertFalse([e for e in graph['relations'] if e['type']=='must-co-report'])
        _anchor_reach(graph,['T'],'after')
        # Defensive reach also tolerates an unrelated unavailable historical endpoint.
        graph['relations'].append(dict(source_id='T',target_id='missing',scientific=True,type='supports',key='old'))
        _anchor_reach(graph,['T'],'after')

    def test_comment_escape_parity_and_paragraphs_use_same_literal_view(self):
        from claimbranch.core.wording_policy import visible_text, paragraph_count
        self.assertEqual('line\\\\',visible_text('line\\\\% negligible'))
        self.assertEqual('line\\% literal',visible_text('line\\% literal'))
        self.assertEqual(1,paragraph_count('Visible.\n\n% Comment-only paragraph.'))
        project,_=self.register('abstract')
        with self.assertRaises(ContractError):self.context(project,'abstract',paragraphs=[dict(index=2,expresses=['C'],plots=[])])
        with self.assertRaises(ContractError):self.policy(grade='   ')

    def test_recorded_reasoning_and_correction_keep_policy_ai_sources_and_original_reason(self):
        from claimbranch.application.personal_project import PersonalProjectRecovery
        from claimbranch.application.personal_research import PersonalResearch
        from claimbranch.application.paper_work_store import PaperWork
        from claimbranch.application.tui_work_recovery import snapshot_value
        project,_=self.policy();project,_=self.companion(project)
        with PersonalProjectStore.create(self.work,project_id=project.project_id) as store:
            store.save(project,preview=self.preview)
            app=project_workspace(project);app.recovery=PersonalProjectRecovery(store,app,project)
            app.select('C');app.keep_draft('Keep a direction-only reading.','A score is not a verifier.')
            app.review.candidates().put(dict(id='C',kind='claim',body=dict(role='main',statement='Rubric scores reflect these measured conditions only.',scope='Synthetic writing task only',parent_ids=['T'])))
            service=PersonalResearch(app);preview=service.prepare('reasoning',explanation_state='leave-for-later')
            self.assertTrue(preview.display['ai_origin_retained']);service.commit(preview)
            service.commit(service.prepare('next',question='Does the sensitivity result hold?'))
            app.select('O');correction=app.intake.create((app.episode_id,'main','O'))
            for field,value in dict(observation='Corrected preference under the same condition.',value='0.4',rationale='A synthetic re-reading.').items():app.intake.keep(correction,field,value)
            service.commit(service.prepare('correct',item_id=correction))
            returned=project_workspace(split_personal_backup(store.backup()));returned.select('C')
            self.assertIn('Direction only',str(returned.detail()))
            self.assertTrue(returned.paper._recorded_origins)
            self.assertIn('A score is not a verifier.',str(returned.paper._recorded_origins))
            self.assertIn('ai',str(returned.paper.history.view('main')['wording_policies']['C']['source_refs']))


    def test_soft_wrapping_comment_join_and_required_companion_review_context(self):
        from claimbranch.core.wording_policy import visible_text, paragraph_count
        self.assertEqual(1,paragraph_count('Claim A holds.\n% note\nWe also show B.'))
        self.assertEqual(2,paragraph_count('A %c\n\nB'))
        self.assertEqual(2,paragraph_count('A %c\n   \nB'))
        self.assertEqual(1,paragraph_count('A %c\nB'))
        self.assertTrue(literal_present(visible_text('definitely\nproven'),'definitely proven'))
        self.assertTrue(literal_present(visible_text('definitely % comment\nproven'),'definitely proven'))
        self.assertFalse(literal_present(visible_text('definitely% comment\nproven'),'definitely proven'))
        project,_=self.register('table','table',expresses=(),plots=('O',))
        project,_=self.companion(project)
        _,preview=self.policy(project)
        self.assertEqual(['O'],preview['impact']['review_companion_ids'])
        self.assertIn('table',preview['impact']['potentially_affected_anchor_ids'])


    def test_unicode_separators_inside_comments_do_not_create_visible_text_or_paragraphs(self):
        from claimbranch.core.wording_policy import visible_text, paragraph_count
        for separator in ('\v','\f','\x1c','\x1d','\x1e','\x85','\u2028','\u2029'):
            with self.subTest(separator=repr(separator)):
                self.assertEqual('Results ',visible_text('Results % definitely'+separator+'proven'))
                self.assertEqual(1,paragraph_count('A %c'+separator+'\nB'))
                self.assertFalse(literal_present(visible_text('definitely %x'+separator+'proven'),'definitely proven'))
        self.assertEqual(1,paragraph_count('A %c\n\u00a0\nB'))


class WordingAcknowledgementTests(unittest.TestCase):
    setUp=ClaimWordingTests.setUp
    register=ClaimWordingTests.register
    policy=ClaimWordingTests.policy

    def prepared(self):
        base,_=self.register('passage');base,_=self.policy(base,banned_phrases=['Synthetic'])
        report=lint(base.work.history);binding=next(b for b in report['review_bindings'] if b['anchor_id']=='passage')
        payload=dict(id='ack',claim_id='C',anchor_id='passage',expected_policy_digest=binding['policy_digest'],expected_anchor_digest=binding['anchor_digest'],rule='banned-phrase',phrase='Synthetic',rationale='This literal occurs in the example label, not the scientific assertion.')
        return base,payload

    def test_exact_acknowledgement_keeps_warning_and_does_not_authorize_science(self):
        from claimbranch.application.metadata_batch import prepare_batch
        from claimbranch.application.personal_archive import personal_backup,split_personal_backup
        from claimbranch.application.personal_project import _PersonalCodec,ITERATION_PERSONAL_MAGIC
        from claimbranch.core.paper_capacity import encode
        base,payload=self.prepared();request=dict(schema='claimbranch.metadata-batch/v4',entries=[dict(id='acknowledge',kind='acknowledge-wording-warning',origin='human',request=payload)],selected_ids=['acknowledge'])
        project,review=prepare_batch(base,encode(request,purpose='project'));self.assertTrue(review['valid'],review)
        report=lint(project.work.history);warning=next(w for w in report['warnings'] if w['code']=='banned-phrase')
        self.assertEqual(['ack'],warning['acknowledgement_ids']);self.assertTrue(report['acknowledgements'][0]['current'])
        self.assertEqual(base.work.history.view('main')['claims'],project.work.history.view('main')['claims']);self.assertEqual(base.work.history.view('main')['evidence'],project.work.history.view('main')['evidence'])
        self.assertTrue(_PersonalCodec().seal(project.payload).startswith(ITERATION_PERSONAL_MAGIC));self.assertEqual(project.payload,split_personal_backup(personal_backup(project)).payload)
        changed,_=self.policy(project,banned_phrases=['Synthetic']);self.assertFalse(lint(changed.work.history)['acknowledgements'][0]['current'])
        self.assertNotIn('acknowledgement_ids',next(w for w in lint(changed.work.history)['warnings'] if w['code']=='banned-phrase'))

    def test_acknowledgement_rejects_stale_binding_and_unmatched_rule(self):
        base,payload=self.prepared()
        with self.assertRaises(ContractError):prepare_revision(base,'acknowledge-wording-warning',{**payload,'expected_policy_digest':'0'*64},contribution_origin='human')
        with self.assertRaises(ContractError):prepare_revision(base,'acknowledge-wording-warning',{**payload,'phrase':'does not appear'},contribution_origin='human')
