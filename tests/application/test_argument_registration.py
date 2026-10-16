"""Imported personal baseline has source history, not fabricated local commands."""
import unittest
import hashlib
import tempfile
from pathlib import Path
import subprocess
import sys
import io
import os
import select
import time
import struct
import fcntl
import termios
from unittest.mock import patch
from claimbranch.core.canonical import ContractError
from claimbranch.application.cli import main
from application.test_argument_import import fixture
from claimbranch.core.paper_capacity import encode, decode
from claimbranch.core import argument_import
from claimbranch.application.project_work import ProjectWork, preview_association
from claimbranch.application.paper_work_store import PaperWork
from claimbranch.application.personal_project import PersonalProjectStore, IMPORT_PERSONAL_MAGIC
from claimbranch.application.personal_archive import personal_backup, split_personal_backup, IMPORT_BACKUP_MAGIC
from claimbranch.application.tui_project import project_workspace
from claimbranch.application.tui_work_recovery import snapshot_value


class ImportedHistoryTests(unittest.TestCase):
    def test_cached_history_and_its_public_views_remain_immutable(self):
        raw = encode(fixture(), purpose='project')
        h = argument_import.history_from_import(raw, anchor_id='anchor')
        original = h.manifest()
        view = h.view('main'); view['imported_records'][0]['body']['statement'] = 'Tampered projection'
        h2 = h.append(dict(schema_version=5, id='new-local', project_id='synthetic-paper', episode_id='new-local-episode',
            created_at='2026-10-13T00:00:00Z', operation_type='open-episode', expected_heads=dict(h.heads),
            evidence_watermark=h.watermark, payload=dict(title='New question', question='What should change next?')))
        self.assertEqual((), h.commands); self.assertEqual(1, len(h2.commands))
        self.assertEqual(original, argument_import.history_from_import(raw, anchor_id='anchor').manifest())

    def test_current_argument_is_seeded_without_past_local_operations(self):
        raw = encode(fixture(), purpose='project')
        history = argument_import.history_from_import(raw, anchor_id='anchor')
        self.assertEqual(5, history.schema_version)
        self.assertEqual((), history.commands)
        self.assertEqual([], history.episodes())
        view = history.view('main')
        self.assertEqual({'C', 'T'}, {item['id'] for item in view['claims']})
        self.assertEqual('supported', next(item for item in view['claims'] if item['id'] == 'C')['status'])
        self.assertEqual('import', view['evidence'][0]['history'][0]['action'])
        self.assertEqual('unknown', view['imported_records'][3]['origin']['contributor'])
        self.assertEqual(1, len(view['historical_decisions']))
        self.assertFalse(history.authorization_verified)
        self.assertEqual(history.manifest(), type(history)(history.seed).manifest())
        claim = next(item for item in view['claims'] if item['id'] == 'C')
        self.assertEqual('imported-source-claim', claim['imported_source']['authority'])
        self.assertIn('/entries/1/banned_terms/0', sum(claim['imported_source']['unresolved_pointer_pages'], []))

    def test_new_local_episode_and_correction_preserve_initial_source(self):
        history = argument_import.history_from_import(encode(fixture(), purpose='project'), anchor_id='anchor')
        seed = history.seed
        def append(kind, payload, key):
            nonlocal history
            history = history.append(dict(schema_version=5, id=key, project_id='synthetic-paper', episode_id='next',
                created_at='2026-10-13T00:00:00Z', operation_type=kind, expected_heads=dict(history.heads),
                evidence_watermark=history.watermark, payload=payload))
        append('open-episode', dict(title='New follow-up', question='Does the claim generalize?'), 'open-next')
        event_id = history.view('main')['evidence'][0]['history'][0]['event_id']
        append('record-evidence-event', dict(event_id='correction', target_id='O', run_id='X', action='correct',
            statement='Corrected blind preference.', value='0.4', rationale='New local correction from checked source.', supersedes_id=event_id), 'correct-next')
        self.assertEqual(seed, history.seed)
        self.assertEqual(['import', 'correct'], [event['action'] for event in history.view('main')['evidence'][0]['history']])
        self.assertEqual('ai', next(record for record in history.view('main')['imported_records'] if record['id'] == 'C')['origin']['contributor'])

    def test_unqualified_imported_source_reasoning_refuses_without_losing_current_graph(self):
        history = argument_import.history_from_import(encode(fixture(), purpose='project'), anchor_id='anchor')
        before = history.manifest()
        for kind in ('create-reasoning-branch', 'record-interpretation', 'apply-selected-merge'):
            from claimbranch.core.research_history import _apply, _reduce
            from copy import deepcopy
            with self.assertRaisesRegex(ContractError, 'origin propagation is not yet qualified'):
                _apply(deepcopy(_reduce(history.seed, history.commands)), {'operation_type':kind})
        self.assertEqual(before, history.manifest())


class ImportedProjectTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir='/private/tmp' if sys.platform == 'darwin' else None)
        self.addCleanup(self.tmp.cleanup); self.root = Path(self.tmp.name)
        self.paper = self.root / 'paper'; self.paper.mkdir()
        self.work = self.root / 'work'; self.work.mkdir(mode=0o700)
        subprocess.run(['/usr/bin/git', 'init', '-q', str(self.paper)], check=True)
        self.manuscript = b'% claimbranch:start id=anchor\nSynthetic paper only.\n% claimbranch:end id=anchor\n'
        (self.paper / 'paper.tex').write_bytes(self.manuscript)
        self.raw = encode(fixture(), purpose='project')
        h = argument_import.history_from_import(self.raw, anchor_id='anchor', registered_at='2026-10-13T00:00:00Z')
        h = h.append(dict(schema_version=5, id='open-local', project_id='synthetic-paper', episode_id='local',
            created_at='2026-10-13T00:00:00Z', operation_type='open-episode', expected_heads=dict(h.heads),
            evidence_watermark=h.watermark, payload=dict(title='New work', question='What should we test next?')))
        self.preview = preview_association(self.paper, 'paper.tex', 'anchor', self.work)
        self.project = ProjectWork.create(PaperWork.create(h), self.preview, import_input=self.raw)

    def personal_app(self):
        from claimbranch.application.personal_project import PersonalProjectRecovery
        store = self.enterContext(PersonalProjectStore.create(self.work, project_id=self.project.project_id))
        store.save(self.project, preview=self.preview)
        app = project_workspace(self.project)
        app.recovery = PersonalProjectRecovery(store, app, self.project)
        return app

    def test_registration_reopen_writing_and_backup_restore_preserve_full_source_and_origins(self):
        with PersonalProjectStore.create(self.work, project_id=self.project.project_id) as store:
            store.save(self.project, preview=self.preview)
        self.assertTrue((self.work / 'personal.cbp').read_bytes().startswith(IMPORT_PERSONAL_MAGIC))
        with PersonalProjectStore(self.work) as store:
            original = store.load(); app = project_workspace(original)
            app.selected_id = 'C'
            self.assertIn('IMPORTED SOURCE / AI', str(app.detail()))
            self.assertIn('banned_terms', str(app.detail()))
            app.notes[app.context_key()] = 'Keep the wording limitation visible.'
            later = original.with_work(PaperWork.create(app.paper.history, workspace=snapshot_value(app)))
            store.save(later); archived = store.backup()
        self.assertTrue(archived.startswith(IMPORT_BACKUP_MAGIC))
        restored = split_personal_backup(archived)
        self.assertEqual(later.payload, restored.payload)
        destination = self.root / 'restored'; destination.mkdir(mode=0o700)
        PersonalProjectStore.restore_backup(archived, destination)
        with PersonalProjectStore(destination) as store:
            returned = store.load(); app = project_workspace(returned)
            self.assertEqual(later.payload, returned.payload)
            self.assertIn('Keep the wording limitation visible.', list(app.notes.values()))
            self.assertEqual(hashlib.sha256(self.raw).hexdigest(), decode(returned.payload, purpose='project')['import_input_sha256'])
        self.assertEqual(self.manuscript, (self.paper / 'paper.tex').read_bytes())

    def run_import(self, answer='import', mutate=None, interrupt=None):
        path = self.root / 'input.json'; path.write_bytes(self.raw); path.chmod(0o600)
        class TTY(io.StringIO):
            def isatty(self): return True
        final_seen = False
        def respond(prompt):
            nonlocal final_seen
            if interrupt and (('final' if prompt.startswith('Type import') else 'page') == interrupt[0]):
                raise interrupt[1]
            if prompt.startswith('Type import'):
                final_seen = True
                if mutate: mutate(path)
                return answer
            return 'cancel' if final_seen else 'continue'
        output, errors = TTY(), io.StringIO()
        with patch('sys.stdin.isatty', return_value=True), patch('sys.stdout', output), patch('sys.stderr', errors), patch('claimbranch.application.import_review.ReviewInput') as reader:
            from contextlib import nullcontext
            reader.return_value = nullcontext(respond)
            code = main(['project','import-argument','--input',str(path),'--directory',str(self.work),
                '--paper-root',str(self.paper),'--manuscript','paper.tex','--question','What should we test next?'])
        return code, output.getvalue(), errors.getvalue()

    def test_public_exact_confirmation_registers_once_and_refuses_reimport(self):
        code, output, error = self.run_import()
        self.assertEqual(0, code, error); self.assertIn('argument saved', output)
        before = (self.work / 'personal.cbp').read_bytes()
        self.assertEqual(1, self.run_import()[0])
        self.assertEqual(before, (self.work / 'personal.cbp').read_bytes())
        with PersonalProjectStore(self.work) as store:
            h = store.load().work.history
            self.assertEqual(1, len(h.commands)); self.assertEqual('open-episode', decode(h.commands[0], purpose='history')['operation_type'])

    def test_cancel_and_changed_input_do_not_publish_any_selected_record(self):
        self.assertEqual(0, self.run_import(answer='')[0])
        self.assertFalse((self.work / 'personal.cbp').exists())
        def change(path): path.write_bytes(path.read_bytes() + b'\n')
        code, _, error = self.run_import(mutate=change)
        self.assertEqual(1, code); self.assertIn('changed after review', error)
        self.assertFalse((self.work / 'personal.cbp').exists())
        self.assertEqual(self.manuscript, (self.paper / 'paper.tex').read_bytes())

    def test_interrupt_and_eof_during_registration_preserve_exit_status_and_destination(self):
        for stage in ('page', 'final'):
            for raised, code in ((EOFError, 1), (KeyboardInterrupt, 130)):
                result, output, error = self.run_import(interrupt=(stage, raised))
                self.assertEqual(code, result, output + error)
                self.assertFalse((self.work / 'personal.cbp').exists())

    def test_imported_relations_show_their_original_source_and_unresolved_fields(self):
        app = project_workspace(self.project); app.selected_id = 'C'
        index = next(i for i, link in enumerate(app.display_links()) if link.kind == 'supports')
        app.link_index = index
        self.assertIn('IMPORTED RELATION / UNKNOWN', str(app.relationship_detail()))

    def test_retained_input_and_seed_origin_cannot_be_rewritten_on_later_save(self):
        value = decode(self.project.payload, purpose='project')
        value['sources'] = []
        with self.assertRaises(ContractError): ProjectWork(encode(value, purpose='project'))
        value = decode(self.project.payload, purpose='project')
        value['work']['seed']['initial_argument']['records'][0]['origin']['contributor'] = 'human'
        with self.assertRaises(ContractError): ProjectWork(encode(value, purpose='project'))
        value['work']['commands'] = []
        with self.assertRaisesRegex(ContractError, 'does not match'): ProjectWork(encode(value, purpose='project'))

    def test_provider_context_refuses_before_disclosing_raw_source(self):
        from claimbranch.application.paper_service import PaperService
        service = PaperService(self.project.work.history)
        with self.assertRaisesRegex(ContractError, 'Imported-origin provider context'): service.compile_context({})

    def test_new_reasoning_records_imported_basis_without_fake_owned_ai_and_survives_return(self):
        from claimbranch.application.personal_project import PersonalProjectRecovery
        from claimbranch.application.personal_research import PersonalResearch
        with PersonalProjectStore.create(self.work, project_id=self.project.project_id) as store:
            store.save(self.project, preview=self.preview)
            app = project_workspace(self.project); app.recovery = PersonalProjectRecovery(store, app, self.project)
            app.select('C')
            app.keep_draft('Blind preference must be tested independently of the rubric.', 'Retain the earlier limitation rather than assert rubric fidelity.')
            work = app.review.candidates()
            claim = work.create('claim', dict(role='subclaim', statement='A blind comparison is necessary for this argument.', scope='Synthetic writing task only', parent_ids=['C']))
            service = PersonalResearch(app, clock=lambda:2000000000)
            preview = service.prepare('reasoning', explanation_state='leave-for-later')
            self.assertTrue(preview.display['recording_available'])
            refs = preview.display['imported_sources']
            self.assertEqual('ai', next(ref for ref in refs if ref['record_id']=='C')['contributor'])
            self.assertTrue(any(ref['contributor']=='unknown' for ref in refs))
            self.assertTrue(all(c['contributor']=='human' for c in preview.display['judgment']['history']))
            service.commit(preview)
            saved = store.load(); backup = store.backup()
        app = project_workspace(split_personal_backup(backup))
        self.assertIn(claim, app.nodes)
        self.assertTrue(app.nodes[claim]['content']['imported_dependencies'])
        self.assertEqual(saved.payload, split_personal_backup(backup).payload)

    def test_imported_reasoning_rejects_omitted_or_relabelled_source_before_append(self):
        from copy import deepcopy
        from claimbranch.application.personal_research import PersonalResearch
        app = self.personal_app(); app.select('C')
        app.keep_draft('Retain the uncertainty.', 'The source does not establish rubric fidelity.')
        preview = PersonalResearch(app, clock=lambda:2000000000).prepare('reasoning', explanation_state='leave-for-later')
        history = preview.history
        commands = [decode(raw, purpose='history') for raw in history.commands]
        for index in (len(commands)-2, len(commands)-1):
            prefix = type(history)(history.seed, history.commands[:index])
            before = prefix.manifest()
            for change in ('omit', 'contributor', 'digest', 'unresolved'):
                command = deepcopy(commands[index]); refs = command['payload']['source_refs']
                if change == 'omit': refs.pop()
                elif change == 'contributor': refs[0]['contributor'] = 'human'
                elif change == 'digest': refs[0]['source_sha256'] = '0'*64
                else: refs[0]['unresolved_count'] += 1
                with self.assertRaisesRegex(ContractError, 'source references|source provenance'):
                    prefix.append(command)
                self.assertEqual(before, prefix.manifest())

    def test_omitted_ai_candidate_is_not_a_selected_source_and_unknown_stays_unknown(self):
        from claimbranch.application.personal_research import PersonalResearch
        app = self.personal_app(); app.select('T')
        app.keep_draft('Keep a limited claim.', 'This is an independent human reading of the thesis.')
        work = app.review.candidates()
        chosen = work.create('claim', dict(role='main', statement='Blind comparison remains an open question.', scope='Synthetic study', parent_ids=['T']))
        omitted = work.create('claim', dict(role='subclaim', statement='An AI-derived alternative.', scope='Synthetic study', parent_ids=['C']))
        work.toggle(omitted)
        preview = PersonalResearch(app, clock=lambda:2000000000).prepare('reasoning', explanation_state='leave-for-later')
        self.assertIn(chosen, [r['id'] for r in preview.display['changes'] if r['disposition']=='selected'])
        self.assertEqual(['T'], [r['record_id'] for r in preview.display['imported_sources']])
        self.assertTrue(preview.display['origin_uncertain'])
        self.assertFalse(preview.display['ai_origin_retained'])
        self.assertEqual('unknown', preview.display['ai_origin_status'])
        self.assertTrue(preview.display['origin_review_required'])
        self.assertTrue(all(r['contributor']=='human' for r in preview.display['judgment']['history']))

    def test_original_uninterpreted_values_are_readable_without_entering_science(self):
        app = project_workspace(self.project)
        app.select('C'); self.assertIn('guarantees', str(app.detail()))
        app.select('O'); self.assertIn('seed1', str(app.detail()))
        self.assertNotIn('values', app.nodes['O']['content'].get('value', ''))

    def test_cached_imported_reasoning_returns_detached_science_and_preserves_source_binding(self):
        from claimbranch.application.personal_research import PersonalResearch
        from claimbranch.application.paper_proposal_work import cause_science
        from copy import deepcopy
        app = self.personal_app(); app.select('C')
        app.keep_draft('Keep the source limitation.', 'A rubric is not an independent verifier.')
        preview = PersonalResearch(app, clock=lambda:2000000000).prepare('reasoning', explanation_state='leave-for-later')
        cause = preview.origin_record['cause']
        science = cause_science(app.paper.history, cause)
        expected = deepcopy(science)
        science['provenance']['imported_sources'].clear()
        self.assertEqual(expected, cause_science(app.paper.history, cause))
        changed = deepcopy(cause); changed['source']['digest'] = '0'*64
        with self.assertRaisesRegex(ContractError, 'source'): cause_science(app.paper.history, changed)

    def test_ordinary_candidate_review_uses_original_owner_and_unknown_review_requirement(self):
        app = self.personal_app(); app.select('C')
        app.keep_draft('Keep a limited reading.', 'The imported claim is not an independent verifier.')
        work = app.review.candidates()
        work.create('claim', dict(role='main',statement='Blind evaluation remains necessary.',scope='Synthetic task',parent_ids=['T']))
        session = app.review.session()
        preview = session.prepare_changes(app.review.changes_request())
        self.assertEqual('C', preview['preview']['provenance']['source_node_id'])
        self.assertTrue(preview['preview']['provenance']['ai_influenced'])
        app.select('T'); app.keep_draft('A human-only new reading.', 'The prior thesis author is unknown.')
        work = app.review.candidates()
        work.create('claim', dict(role='main',statement='A source limitation should be disclosed.',scope='Synthetic task',parent_ids=['T']))
        session = app.review.session(); preview = session.prepare_changes(app.review.changes_request())
        self.assertTrue(preview['preview']['provenance']['origin_uncertain'])
        self.assertFalse(preview['preview']['provenance']['ai_influenced'])
        with self.assertRaises(ContractError): session.finish_changes_review(preview['digest'], disposition='not-required', answers=[])

    def test_nine_reasoning_rounds_survive_return_without_legacy_eight_consequence_cap(self):
        from claimbranch.application.personal_project import PersonalProjectRecovery
        from claimbranch.application.personal_research import PersonalResearch
        with PersonalProjectStore.create(self.work, project_id=self.project.project_id) as store:
            store.save(self.project, preview=self.preview)
            app = project_workspace(self.project); app.recovery = PersonalProjectRecovery(store, app, self.project)
            service = PersonalResearch(app, clock=lambda:2000000000)
            for index in range(9):
                app.select('C')
                app.keep_draft(f'Round {index}: retain the rubric limitation.', f'Round {index}: a blind test is still needed.')
                service.commit(service.prepare('reasoning', explanation_state='leave-for-later'))
                if index < 8: service.commit(service.prepare('next', question=f'Next question {index}'))
            saved = store.load(); backup = store.backup()
        returned = project_workspace(split_personal_backup(backup))
        self.assertEqual(9, len(returned.paper._recorded_origins))
        self.assertEqual(saved.payload, split_personal_backup(backup).payload)
        self.assertTrue(all(record['explanation']['state']=='leave-for-later' for record in returned.paper._recorded_origins))

    def test_large_imported_dependency_set_survives_review_record_and_backup(self):
        from copy import deepcopy
        import json
        from claimbranch.core.paper_capacity import source_bytes, source_record
        from claimbranch.core.argument_import import _leaves
        from claimbranch.application.personal_research import PersonalResearch
        value = fixture(); records = value['records']
        original = json.loads(source_bytes(value['source']))
        for index in range(1, 70):
            for template in (2, 3, 4):
                item = deepcopy(records[template]); item['id'] += '-' + str(index)
                if template == 3: item['body']['experiment_id'] = 'X-' + str(index)
                if template == 4: item['body']['source_id'] = 'O-' + str(index)
                item['source_pointer'] = '/entries/' + str(len(original['entries']))
                original['entries'].append(deepcopy(item['body']))
                records.append(item)
        records[1]['body']['basis_ids'] = ['E'] + ['E-'+str(i) for i in range(1,70)]
        original['entries'][1]['basis_ids'] = records[1]['body']['basis_ids']
        for item in records:
            item['mappings'] = [dict(target=p, source=item['source_pointer']+p, transformation=None) for p,_ in _leaves(item['body'])]
        value['source'] = source_record(json.dumps(original).encode())
        raw = encode(value, purpose='project')
        h = argument_import.history_from_import(raw, anchor_id='anchor')
        h = h.append(dict(schema_version=5, id='large-open', project_id='synthetic-paper', episode_id='local',
            created_at='2026-10-13T00:00:00Z', operation_type='open-episode', expected_heads=dict(h.heads),
            evidence_watermark=h.watermark, payload=dict(title='Large source',question='What should change?')))
        self.project = ProjectWork.create(PaperWork.create(h), self.preview, import_input=raw)
        app = self.personal_app(); app.select('C')
        app.keep_draft('Retain a narrow interpretation.', 'The registered sources must remain inspectable.')
        service = PersonalResearch(app, clock=lambda:2000000000)
        preview = service.prepare('reasoning', explanation_state='leave-for-later')
        self.assertGreater(len(preview.display['imported_sources']), 128)
        service.commit(preview)
        returned = project_workspace(split_personal_backup(app.recovery.store.backup()))
        self.assertEqual(1, len(returned.paper._recorded_origins))
        self.assertEqual(raw, source_bytes(next(s for s in decode(app.recovery.project.payload,purpose='project')['sources'] if s['sha256']==hashlib.sha256(raw).hexdigest())))

    def test_actual_terminal_registration_open_quit_and_fresh_status(self):
        path = self.root / 'input.json'; path.write_bytes(self.raw); path.chmod(0o600)
        def terminal(arguments, publish=False):
            master, slave = os.openpty()
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 40, 140, 0, 0))
            env = dict(os.environ, TERM='xterm-256color')
            process = subprocess.Popen([sys.executable, '-m', 'claimbranch', *arguments], stdin=slave, stdout=slave, stderr=slave, env=env)
            os.close(slave); output = b''; pending = b''; deadline = time.monotonic() + 20; sent_quit = False
            try:
                while process.poll() is None and time.monotonic() < deadline:
                    if select.select([master], [], [], 0.1)[0]:
                        try: chunk = os.read(master, 65536)
                        except OSError: break
                        output += chunk; pending += chunk
                        if publish:
                            if b'Review: details / continue to confirmation / cancel:' in pending:
                                os.write(master, b'continue\n'); pending = b''
                            elif b'Type import to register' in pending:
                                os.write(master, b'import\n'); pending = b''
                        elif not sent_quit and (b'ClaimBranch' in output or b'New work' in output or b'Imported current argument' in output):
                            os.write(master, b'q'); sent_quit = True
                self.assertEqual(0, process.wait(timeout=5), output[-4000:].decode(errors='replace'))
                if publish: self.assertIn(b'Imported personal argument saved', output)
                else: self.assertTrue(sent_quit, output[-4000:])
            finally:
                if process.poll() is None: process.kill(); process.wait()
                os.close(master)
        terminal(['project','import-argument','--input',str(path),'--directory',str(self.work),
                  '--paper-root',str(self.paper),'--manuscript','paper.tex','--question','What should we test next?'], publish=True)
        terminal(['project','open','--directory',str(self.work)])
        checked = subprocess.run([sys.executable,'-m','claimbranch','project','status','--directory',str(self.work),'--json'], capture_output=True, text=True, timeout=10)
        self.assertEqual(0, checked.returncode, checked.stderr)
        import json
        self.assertEqual(5, json.loads(checked.stdout)['capacity']['schema_version'])


class ImportReviewTests(unittest.TestCase):
    """Usable review and write-free preflight, independent of source fidelity."""
    setUp = ImportedProjectTests.setUp

    def test_summary_scales_with_kinds_not_original_lines_or_mapping_count(self):
        from copy import deepcopy
        from claimbranch.core.argument_import import _leaves
        from claimbranch.core.paper_capacity import source_record
        from claimbranch.application.import_review import summary_lines, unresolved_items
        value = fixture(); templates = {r['kind']:r for r in value['records']}
        records = [deepcopy(value['records'][0])]
        for kind, count, prefix in [('claim',20,'C'),('experiment',52,'X'),('observation',52,'O'),('scientific-edge',67,'E'),('historical-decision',18,'D')]:
            for i in range(count):
                record = deepcopy(templates[kind]);record['id'] = f'{prefix}-{i}'
                body = record['body']
                if kind == 'claim': body.update(status='proposed',basis_ids=[])
                if kind == 'observation': body['experiment_id'] = f'X-{i}'
                if kind == 'scientific-edge': body.update(source_id=f'O-{i%52}',target_id=f'C-{i%20}')
                if kind == 'historical-decision': body['record_ids'] = ['C-0','O-0']
                records.append(record)
        original = dict(entries=[r['body'] for r in records], archive='NOT-IN-SUMMARY\n'*16072)
        for i, record in enumerate(records):
            record['source_pointer'] = f'/entries/{i}'
            record['mappings'] = [dict(target=p,source=f'/entries/{i}'+p,transformation=None) for p,_ in _leaves(record['body'])]
        value.update(records=records, selected_ids=[r['id'] for r in records],source=source_record(__import__('json').dumps(original).encode()))
        result = argument_import.preview_import(encode(value,purpose='project'))
        self.assertTrue(result['valid'],result['errors']);self.assertGreater(len(records),200)
        summary = '\n'.join(summary_lines(result))
        self.assertLessEqual(len(summary.splitlines()),120)
        self.assertNotIn('NOT-IN-SUMMARY',summary);self.assertNotIn('mappings',summary)
        self.assertEqual(1,len(list(unresolved_items(result))))
        with patch('sys.stdout',new=io.StringIO()) as out:
            from claimbranch.application.import_review import review
            answers = iter(['unresolved','item 1','q'])
            self.assertFalse(review(result,read=lambda _:next(answers)))
        self.assertIn('/archive',out.getvalue())

    def test_detail_back_blank_confirmation_and_distinct_cancel(self):
        from claimbranch.application.import_review import review
        result=argument_import.preview_import(self.raw)
        answers=iter(['source original','q','continue','','cancel'])
        with patch('sys.stdout',new=io.StringIO()):
            self.assertFalse(review(result,read=lambda _:next(answers),registration=True))
        answers=iter(['continue','import'])
        with patch('sys.stdout',new=io.StringIO()):
            self.assertTrue(review(result,read=lambda _:next(answers),registration=True))
        self.assertEqual([],list(self.work.iterdir()))

    def preflight(self,extra=()):
        path=self.root/'input.json';path.write_bytes(self.raw);path.chmod(0o600)
        with patch('sys.stdout',new=io.StringIO()) as out,patch('sys.stderr',new=io.StringIO()) as err:
            code=main(['project','import-argument','--input',str(path),'--dry-run','--preflight','--json',
                '--directory',str(self.work),'--paper-root',str(self.paper),'--manuscript','paper.tex',
                '--question','What should we test next?',*extra])
        return code,out.getvalue(),err.getvalue()

    def test_full_preflight_is_write_free_and_rejects_used_destination_without_cleanup(self):
        def snapshot():
            paths=[self.root,*self.root.rglob('*')]
            return {str(p.relative_to(self.root)):(p.lstat().st_ino,p.lstat().st_mode,p.lstat().st_size,p.lstat().st_mtime_ns,p.lstat().st_ctime_ns) for p in paths}
        path=self.root/'input.json';path.write_bytes(self.raw);path.chmod(0o600)
        # Launch the public path with -B so interpreter caches are not confused with preflight writes.
        before=snapshot()
        argv=[sys.executable,'-B','-m','claimbranch','project','import-argument','--input',str(path),'--dry-run','--preflight','--json',
            '--directory',str(self.work),'--paper-root',str(self.paper),'--manuscript','paper.tex','--question','Next question?']
        r=subprocess.run(argv,capture_output=True,timeout=30)
        self.assertEqual(0,r.returncode,r.stderr);self.assertEqual(before,snapshot())
        report=__import__('json').loads(r.stdout)['full_preflight']
        self.assertFalse(report['writes']);self.assertGreater(report['archive_bytes'],report['saved_bytes'])
        self.assertEqual(64, len(report['result_sha256']))
        self.assertIn('prepared_at',report);self.assertNotIn('registered_at',report)
        from application.test_original_registration import fixture as table_fixture
        path.write_bytes(encode(table_fixture(),purpose='project'));before=snapshot()
        r=subprocess.run([*argv,'--shared-audit'],capture_output=True,timeout=30)
        self.assertEqual(0,r.returncode,r.stderr);self.assertEqual(before,snapshot())
        shared=__import__('json').loads(r.stdout)['full_preflight']
        self.assertEqual('shared-values/v1',shared['representation'])
        self.assertTrue(shared['audit_encoding_review']['source_seed_unchanged'])
        (self.work/'backup.cbp').write_bytes(b'existing backup');before=snapshot()
        r=subprocess.run(argv,capture_output=True,timeout=30)
        self.assertEqual(1,r.returncode);self.assertIn(b'fresh',r.stderr);self.assertEqual(before,snapshot())

    def test_cheap_json_preview_unchanged_and_preflight_requires_options(self):
        path=self.root/'input.json';path.write_bytes(self.raw);path.chmod(0o600)
        with patch('sys.stdout',new=io.StringIO()) as out:
            self.assertEqual(0,main(['project','import-argument','--input',str(path),'--dry-run','--json']))
        self.assertEqual(argument_import.preview_import(self.raw),__import__('json').loads(out.getvalue()))
        with patch('sys.stdout',new=io.StringIO()),patch('sys.stderr',new=io.StringIO()) as err:
            self.assertEqual(1,main(['project','import-argument','--input',str(path),'--dry-run','--preflight']))
        self.assertIn('--directory',err.getvalue());self.assertEqual([],list(self.work.iterdir()))

    def test_nested_table_errors_name_missing_field_and_bad_cell(self):
        from application.test_original_registration import fixture as table_fixture
        value=table_fixture();table=value['records'][3]['body']['measurement']
        del table['conditions'];table['rows'][0]['cells'][0]['value']['value']='NaN'
        result=argument_import.preview_import(encode(value,purpose='project'))
        self.assertFalse(result['valid'])
        errors={e['pointer']:e['error'] for e in result['errors']}
        self.assertEqual('missing field',errors['/records/3/body/measurement/conditions'])
        self.assertIn('format',errors['/records/3/body/measurement/rows/0/cells/0/value/value'])

    def test_empty_artifact_pointer_normalizes_and_verifies_root_value(self):
        from application.test_typed_observations import TypedObservationTests
        from claimbranch.core.typed_observations import TABLE,validate_table
        from claimbranch.core.research_schema import normalize
        from claimbranch.application.typed_observations import check_artifact
        raw=b'0.123456789012345678901234567890';path=self.root/'root.json';path.write_bytes(raw)
        table=TypedObservationTests().table()
        table['artifact_refs']=[dict(id='root',path='root.json',sha256=hashlib.sha256(raw).hexdigest(),json_pointer='',tool_sha256=None,commit=None)]
        table=normalize(table,TABLE,profile='paper');validate_table(table,{k:{'values':v} for k,v in [('model',['M1']),('leg',['primary','sensitivity']),('dose',['low','mid','high']),('seed',['s1','s2','s3'])]})
        h=type('History',(),{'view':lambda _,ref:dict(evidence=[dict(id='O',measurement=table,measurement_revision='import-event')])})()
        result=check_artifact(h,'O','root',path,table['rows'][0]['cells'][0]['id'])
        self.assertEqual('hash-and-cell-match',result['status']);self.assertFalse(result['scientific_validity_verified'])


    @unittest.skipUnless(os.name == 'posix', 'real Unix PTY input boundary')
    def test_actual_tty_queued_pasted_input_back_and_fresh_confirmation(self):
        import pty
        for width in (100, 34):
            work=self.root/f'pty-{width}';work.mkdir(mode=0o700)
            path=self.root/'pty-input.json';path.write_bytes(self.raw);path.chmod(0o600)
            master,slave=pty.openpty()
            fcntl.ioctl(slave,termios.TIOCSWINSZ,struct.pack('HHHH',24,width,0,0))
            original=termios.tcgetattr(slave)
            process=subprocess.Popen([sys.executable,'-B','-m','claimbranch','project','import-argument',
                '--input',str(path),'--directory',str(work),'--paper-root',str(self.paper),
                '--manuscript','paper.tex','--question','What should change next?'],stdin=slave,stdout=slave,stderr=slave)
            pending=b''
            def wait_for(marker):
                nonlocal pending
                deadline=time.monotonic()+20
                while marker not in pending and time.monotonic()<deadline:
                    if select.select([master],[],[],0.1)[0]:
                        try:pending+=os.read(master,65536)
                        except OSError:break
                    if process.poll() is not None and marker not in pending:break
                self.assertIn(marker,pending,pending[-3000:])
                before,pending=pending.split(marker,1)
                return before
            prompt=b'Review: details / continue to confirmation / cancel: '
            final=b'Type import to register this exact selection; Enter: back to summary / cancel: '
            try:
                wait_for(prompt)
                for data in (b'\n'*40+b'import\n',b'continue\nimport\n'):
                    os.write(master,data);wait_for(prompt)
                    self.assertFalse((work/'personal.cbp').exists())
                os.write(master,b'continue\n');wait_for(final)
                os.write(master,b'\x1b[200~import\n\x1b[201~');wait_for(prompt)
                self.assertFalse((work/'personal.cbp').exists())
                os.write(master,b'continue\n');wait_for(final)
                os.write(master,b'\n'*40+b'import\n');wait_for(prompt)
                self.assertFalse((work/'personal.cbp').exists())
                os.write(master,b'source original\n');wait_for(b'Enter: next detail page / q: back to summary: ')
                os.write(master,b'q\n');wait_for(prompt)
                os.write(master,b'continue\n');wait_for(final)
                os.write(master,b'import\n');wait_for(b'Imported personal argument saved.')
                self.assertEqual(0,process.wait(timeout=10))
                self.assertEqual(original,termios.tcgetattr(slave))
                with PersonalProjectStore(work) as store:
                    self.assertEqual(1,len(store.load().work.history.commands))
            finally:
                if process.poll() is None:process.kill();process.wait()
                os.close(master);os.close(slave)


    def test_review_back_is_not_cancel_and_long_single_line_source_is_paged(self):
        from claimbranch.application.import_review import review
        from claimbranch.core.paper_capacity import source_record
        result=argument_import.preview_import(self.raw)
        result['source']=source_record(b'{"long":"'+b'x'*20000+b'"}')
        answers=iter(['source original','q','q','continue','import'])
        with patch('sys.stdout',new=io.StringIO()) as output:
            self.assertTrue(review(result,read=lambda _:next(answers),registration=True))
        self.assertNotIn('x'*1000,output.getvalue())
        self.assertIn('Unknown command',output.getvalue())

    def test_empty_root_exception_does_not_relax_other_nonblank_text(self):
        from claimbranch.core.research_schema import normalize,TEXT
        for schema in (TEXT,{'type':'string','maxLength':160}):
            with self.assertRaisesRegex(ContractError,'nonblank'):
                normalize('',schema)
        from claimbranch.core.argument_import import _errors
        from claimbranch.core.typed_observations import VALUE
        errors=[];_errors(dict(type='mystery',value='0'),VALUE,'/cell',errors)
        self.assertEqual('/cell/type',errors[0]['pointer'])
        self.assertIn('integer',errors[0]['error'])


    def test_post_review_manuscript_or_destination_change_prevents_publication(self):
        def manuscript_changed(_):
            (self.paper/'paper.tex').write_bytes(self.manuscript.replace(b'Synthetic paper only.',b'Changed source.'))
        code,_,_=ImportedProjectTests.run_import(self,mutate=manuscript_changed)
        self.assertEqual(1,code);self.assertEqual([],list(self.work.iterdir()))
        (self.paper/'paper.tex').write_bytes(self.manuscript)
        def destination_changed(_):
            (self.work/'backup.cbp').write_bytes(b'preserve this concurrent file')
        code,_,_=ImportedProjectTests.run_import(self,mutate=destination_changed)
        self.assertEqual(1,code)
        self.assertEqual(['backup.cbp'],[p.name for p in self.work.iterdir()])
        self.assertEqual(b'preserve this concurrent file',(self.work/'backup.cbp').read_bytes())

    def test_published_candidate_matches_the_exact_reviewed_preflight_commitment(self):
        reviewed=[]
        def confirm(result,details,**kwargs):
            reviewed.append(details)
            return True
        with patch('claimbranch.application.import_review.review',side_effect=confirm):
            code,_,error=ImportedProjectTests.run_import(self)
        self.assertEqual(0,code,error)
        self.assertEqual(1,len(reviewed));self.assertTrue(reviewed[0]['passed'])
        with PersonalProjectStore(self.work) as store:
            loaded=store.load()
        self.assertEqual(reviewed[0]['result_sha256'],hashlib.sha256(loaded.payload).hexdigest())

    def test_import_os_failure_does_not_echo_internal_os_filename(self):
        with patch('claimbranch.application.project_commands._read_argument_input',side_effect=OSError(13,'private OS detail','hidden-private-path')):
            with patch('sys.stdout',new=io.StringIO()),patch('sys.stderr',new=io.StringIO()) as errors:
                self.assertEqual(1,main(['project','import-argument','--input','missing','--dry-run']))
        self.assertIn('private regular input',errors.getvalue())
        self.assertNotIn('hidden-private-path',errors.getvalue());self.assertNotIn('private OS detail',errors.getvalue())
