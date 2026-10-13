"""BYO preparation preserves private science and grants no send capability."""
from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
from dataclasses import replace
import io
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from claimbranch.application.cli import main
from claimbranch.application.provider_profile import (
    ProviderProfile, ProviderProfileStore, prepare_provider_request, decode_provider_response)
from claimbranch.application.personal_project import PersonalProjectStore
from claimbranch.application.project_work import preview_association
from claimbranch.application.tui_project import prepare_project, project_workspace
from claimbranch.core.canonical import ContractError, canonical_bytes, decode
from tests.application.test_paper_proposal_work import fixture, request
from tests.application.test_paper_proposals import response


def profile(api='openai-chat', **overrides):
    values = {'api': api, 'endpoint': 'https://llm.example/v1/'+(
        'messages' if api == 'anthropic-messages' else 'chat/completions'),
        'model': 'my-personal-model', 'credential_env': 'MY_LLM_KEY'}
    return ProviderProfile.create(**(values | overrides))


def prepared(api='openai-chat', *, include_draft=False):
    app = fixture()
    context = app.paper.draft(*app.context_key()).compile_proposal_context(request(app), include_draft=include_draft)
    return prepare_provider_request(profile(api), context, request_id='request-1', nonce='nonce-1', now=100)


def wrapper(api, text):
    if api == 'openai-chat':
        return {'choices': [{'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': text}}],
                'usage': {'diagnostic_seconds': 0.5}}
    return {'type': 'message', 'role': 'assistant', 'stop_reason': 'end_turn',
            'content': [{'type': 'text', 'text': text}]}


class CodexPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root/'llm'
        self.config.mkdir(mode=0o700)

    def invoke(self, *args):
        with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()) as err:
            code = main(['provider', *args])
        return code, out.getvalue(), err.getvalue()

    def test_codex_configuration_is_separate_from_api_keys_and_never_launches(self):
        from claimbranch.application.provider_profile import CodexProfile, load_provider_profile
        arguments = ('configure-codex', '--directory', str(self.config), '--model', 'gpt-6.1-sol')
        with patch('subprocess.Popen', side_effect=AssertionError('no client launch')), patch(
                'socket.socket', side_effect=AssertionError('no network')):
            code, out, err = self.invoke(*arguments, '--dry-run')
            self.assertEqual((0, ''), (code, err))
            self.assertFalse(json.loads(out)['configuration_saved'])
            self.assertEqual([], list(self.config.iterdir()))
            code, out, err = self.invoke(*arguments)
            self.assertEqual((0, ''), (code, err))
            result = json.loads(out)
            self.assertEqual('chatgpt-login', result['configuration']['authentication'])
            self.assertFalse(result['dispatch_available'])
            self.assertEqual('not checked', result['login_status'])
            self.assertEqual('supported candidate; installed/runtime version not observed', result['client_version_status'])
            code, out, err = self.invoke('inspect', '--directory', str(self.config))
            self.assertEqual((0, ''), (code, err))
            self.assertEqual(result['profile_digest'], json.loads(out)['profile_digest'])
        raw = (self.config/'provider.json').read_bytes()
        self.assertIs(type(load_provider_profile(raw)), CodexProfile)
        self.assertNotIn('credential_env', json.loads(raw))
        self.assertNotIn('api_key', json.loads(raw))
        self.assertEqual(0o600, (self.config/'provider.json').stat().st_mode & 0o777)
        self.assertEqual(1, self.invoke(*arguments)[0])
        self.assertEqual(raw, (self.config/'provider.json').read_bytes())

    def test_codex_profile_does_not_widen_the_frozen_api_profile(self):
        from claimbranch.application.provider_profile import CodexProfile, load_provider_profile
        item = CodexProfile.create(model='gpt-6.1-sol')
        for update in ({'credential_env':'KEY'}, {'authentication':'api-key'},
                       {'client_version':'0.159.0'}, {'model':'bad\nmodel'},
                       {'schema':'claimbranch.codex-profile/v2'}, {'reasoning_effort':'automatic'}):
            with self.subTest(update=update), self.assertRaises(ContractError):
                load_provider_profile(canonical_bytes(item.value | update))
        with self.assertRaises(ContractError): ProviderProfile(item.payload)
        with self.assertRaises(ContractError): CodexProfile(profile().payload)
        self.assertEqual(profile(), load_provider_profile(profile().payload))

    def test_codex_preview_binds_selected_input_and_keeps_wrapper_uncertainty_visible(self):
        from claimbranch.application.provider_profile import CodexProfile, prepare_personal_provider_request
        app = fixture(); session = app.paper.draft(*app.context_key())
        item = CodexProfile.create(model='gpt-6.1-sol')
        results = []
        for include in (False, True):
            context = session.compile_proposal_context(request(app), include_draft=include)
            outbound = prepare_personal_provider_request(item, context, request_id='request-1', nonce='nonce-1', now=100)
            results.append(outbound)
            value = outbound.preview()
            self.assertFalse(value['sent']); self.assertFalse(value['dispatch_available'])
            self.assertEqual('service-origin', value['destination']['scope'])
            self.assertEqual('https://chatgpt.com', value['destination']['url'])
            self.assertEqual('unverified', value['runtime_wrapper'])
            self.assertEqual('supported candidate; installed/runtime version not observed', value['client_version_status'])
            self.assertNotIn('wire_body', value)
            self.assertNotIn('method', value)
            selected = value['application_input']['input']['context']['records']
            self.assertEqual(['thesis','obs-a'], [r['id'] for r in selected if r['kind']!='draft'])
            self.assertEqual(include, any(r['kind']=='draft' for r in selected))
            self.assertEqual(json.loads(outbound.body), value['application_input'])
            self.assertIn('Do not confirm evidence', value['application_input']['instructions'])
            outbound.recheck(item, context, now=219)
            with self.assertRaises(ContractError): outbound.recheck(item, context, now=220)
            with self.assertRaises(ContractError): outbound.recheck(item, context, now=99)
            with self.assertRaises(ContractError):
                outbound.recheck(CodexProfile.create(model='different-model'), context, now=101)
            with self.assertRaises(ContractError):
                replace(outbound, body=outbound.body+b' ').recheck(item, context, now=101)
        self.assertNotEqual(results[0].digest, results[1].digest)
        self.assertEqual([], app.paper.proposal_history())

    def test_codex_complete_preview_refuses_excess_bytes(self):
        from claimbranch.application.provider_profile import CodexProfile, prepare_personal_provider_request
        app = fixture(); context = app.paper.draft(*app.context_key()).compile_proposal_context(request(app))
        with patch('claimbranch.application.provider_profile._codex_output_schema',return_value={'large':'a'*65536}):
            with self.assertRaises(ContractError):
                prepare_personal_provider_request(CodexProfile.create(model='gpt-6.1-sol'), context,
                    request_id='request-1', nonce='nonce-1', now=100)

    def test_codex_generation_schema_uses_supported_subset_without_changing_ingress(self):
        from claimbranch.application.provider_profile import CodexProfile, prepare_codex_request
        from claimbranch.core.paper_proposals import result_schema
        from tests.application.test_paper_proposals import context
        scientific=result_schema()
        prepared=prepare_codex_request(CodexProfile.create(model='gpt-6-sol'),context(),
            request_id='request-1',nonce='nonce-1',now=100)
        schema=json.loads(prepared.body)['output_schema']
        allowed={'type','properties','required','additionalProperties','items','enum','anyOf'}
        def check(node):
            self.assertFalse(set(node)-allowed)
            if node.get('type')=='object':
                self.assertIs(False,node['additionalProperties'])
                self.assertEqual(set(node['properties']),set(node['required']))
                for child in node['properties'].values(): check(child)
            if 'items' in node: check(node['items'])
            for child in node.get('anyOf',[]): check(child)
        check(schema)
        self.assertEqual('object',schema['type'])
        self.assertEqual({'type':'string','enum':['claimbranch.provider-result/v2']},
            schema['properties']['schema'])
        variants=schema['properties']['items']['items']['anyOf']
        self.assertEqual(['claim','interpretation','scientific-edge','experiment-plan'],
            [v['properties']['kind']['enum'][0] for v in variants])
        self.assertEqual([{'type':'string'},{'type':'null'}],schema['properties']['critique']['anyOf'])
        self.assertEqual(scientific,result_schema())
        self.assertIn('oneOf',scientific['properties']['items']['items'])
        self.assertEqual(64,scientific['properties']['items']['maxItems'])

    def test_codex_generation_projection_refuses_unknown_contract_keywords(self):
        from claimbranch.application.provider_profile import _codex_output_schema
        with patch('claimbranch.application.provider_profile.result_schema',return_value={'unreviewed':True}):
            with self.assertRaises(ContractError): _codex_output_schema()

    def test_codex_saved_project_preview_preserves_research_and_manuscript(self):
        from claimbranch.application.provider_profile import CodexProfile
        with ProviderProfileStore(self.config) as store:
            store.write(CodexProfile.create(model='gpt-6.1-sol').payload)
        paper, work, _ = ProviderPreparationTests.personal_project(self)
        before = (work/'personal.cbp').read_bytes(); source = (paper/'paper.tex').read_bytes()
        original_popen = subprocess.Popen
        def only_git(argv, *args, **kwargs):
            if argv[0] != '/usr/bin/git': raise AssertionError('no provider client')
            return original_popen(argv, *args, **kwargs)
        with patch('subprocess.Popen', side_effect=only_git), patch(
                'socket.socket', side_effect=AssertionError('no network')):
            code, out, err = self.invoke('preview', '--directory', str(self.config),
                '--project-directory', str(work), '--node', 'thesis', '--record', 'thesis')
        self.assertEqual((0, ''), (code, err))
        self.assertEqual('unsent-codex-input', json.loads(out)['kind'])
        self.assertIn('Temperature may affect latency.', out)
        self.assertEqual(before, (work/'personal.cbp').read_bytes())
        self.assertEqual(source, (paper/'paper.tex').read_bytes())


class ProviderPreparationTests(unittest.TestCase):
    def test_wire_v1_preparation_refuses_unversioned_policy_or_header_changes(self):
        from claimbranch.application.provider_profile import POLICY, retained_provider_request
        item=prepared();original=item.preview()
        with patch.dict(POLICY, {'read_seconds':20}):
            with self.assertRaises(ContractError):prepared()
            self.assertEqual(original,item.preview())
            self.assertEqual(item.digest,hashlib.sha256(canonical_bytes(retained_provider_request(item))).hexdigest())
        with patch('claimbranch.application.provider_profile.provider_request_headers',return_value={'Changed':'header'}):
            with self.assertRaises(ContractError):prepared()
            self.assertEqual(original,item.preview())

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root/'llm'
        self.config.mkdir(mode=0o700)

    def invoke(self, *args):
        with redirect_stdout(io.StringIO()) as out, redirect_stderr(io.StringIO()) as err:
            code = main(['provider', *args])
        return code, out.getvalue(), err.getvalue()

    def configure(self, *extra):
        return self.invoke('configure', '--directory', str(self.config), '--api', 'openai-chat',
            '--endpoint', 'https://llm.example/v1/chat/completions', '--model', 'my-model',
            '--credential-env', 'MY_LLM_KEY', *extra)

    def test_public_configure_inspect_and_dry_run_never_read_keys_or_network(self):
        with patch.dict(os.environ, {'MY_LLM_KEY': 'private-test-value'}), patch('socket.socket', side_effect=AssertionError('network forbidden')):
            code, out, err = self.configure('--dry-run')
            self.assertEqual((0, ''), (code, err))
            self.assertFalse(json.loads(out)['configuration_saved'])
            self.assertEqual([], list(self.config.iterdir()))
            code, out, err = self.configure()
            self.assertEqual((0, ''), (code, err))
            self.assertNotIn('private-test-value', out)
            code, out, err = self.invoke('inspect', '--directory', str(self.config))
            self.assertEqual((0, ''), (code, err))
            value = json.loads(out)
            self.assertFalse(value['dispatch_available'])
            self.assertEqual('not read', value['credential_value'])
            self.assertEqual('not qualified', value['topology'])
        raw = (self.config/'provider.json').read_bytes()
        self.assertNotIn(b'private-test-value', raw)
        self.assertEqual(0o600, (self.config/'provider.json').stat().st_mode & 0o777)
        code, _, _ = self.configure()
        self.assertEqual(1, code)
        self.assertEqual(raw, (self.config/'provider.json').read_bytes())

    def test_inline_secrets_unknown_fields_and_invalid_destinations_refuse(self):
        for update in ({'api_key': 'secret'}, {'credential_env': 'sk-secret-value'},
                       {'endpoint': 'https://user:secret@host/chat/completions'},
                       {'endpoint': 'https://host/chat/completions?key=secret'},
                       {'endpoint': 'https://host/chat/completions#fragment'},
                       {'endpoint': 'http://localhost:1234/v1'}, {'endpoint': 'offline://frozen'},
                       {'output_tokens': True}, {'output_tokens': 8193}, {'model': 'model\nheader'}):
            with self.subTest(update=update):
                with self.assertRaises(ContractError):
                    ProviderProfile(canonical_bytes(profile().value | update))
        with self.assertRaises(ContractError):
            profile('anthropic-messages', json_mode='json-object')
        for value in ({'model': 'model\n'}, {'credential_env': 'MY_LLM_KEY\n'}):
            with self.assertRaises(ContractError): ProviderProfile(canonical_bytes(profile().value | value))

    def test_private_external_profile_read_checks_symlink_hardlink_corruption_and_permissions(self):
        with ProviderProfileStore(self.config) as store:
            store.write(profile().payload)
        path = self.config/'provider.json'; raw = path.read_bytes()
        path.chmod(0o644)
        with self.assertRaises(ContractError):
            with ProviderProfileStore(self.config) as store: store.read()
        path.chmod(0o600)
        linked = self.root/'linked'; os.link(path, linked)
        with self.assertRaises(ContractError):
            with ProviderProfileStore(self.config) as store: store.read()
        linked.unlink(); path.unlink(); path.symlink_to(linked)
        with self.assertRaises(ContractError):
            with ProviderProfileStore(self.config) as store: store.read()
        path.unlink(); path.write_bytes(b'{"schema":"newer"}'); path.chmod(0o600)
        with self.assertRaises(ContractError):
            with ProviderProfileStore(self.config) as store: store.read()
        self.assertNotEqual(raw, path.read_bytes())

    def test_in_git_nonprivate_and_research_directory_cannot_store_configuration(self):
        self.config.chmod(0o755)
        code, _, err = self.configure()
        self.assertEqual(1, code); self.assertIn('Provider configuration directory must be owned and mode 0700', err)
        self.config.chmod(0o700)
        (self.config/'.git').mkdir()
        code, _, err = self.configure()
        self.assertEqual(1, code); self.assertIn('Provider configuration directory must be outside Git', err)
        (self.config/'.git').rmdir()
        for filename in ('personal.cbp', 'work.cbw', 'backup.cbp', 'backup.cbw', 'project.json'):
            target = self.config/filename; target.write_bytes(b'retain research')
            self.assertEqual(1, self.configure()[0])
            self.assertEqual(b'retain research', target.read_bytes()); target.unlink()
        self.assertFalse((self.config/'provider.json').exists())

    def test_exact_wire_includes_instruction_schema_selected_science_and_explicit_draft_only(self):
        without, with_draft = prepared(), prepared(include_draft=True)
        for item in (without, with_draft):
            preview = item.preview(); body = json.loads(item.body)
            self.assertIn('claimbranch.provider-result/v2', body['messages'][0]['content'])
            selected = json.loads(body['messages'][1]['content'])['context']['records']
            self.assertEqual(['thesis', 'obs-a'], [r['id'] for r in selected if r['kind'] != 'draft'])
            self.assertEqual(body, preview['wire_body'])
            self.assertFalse(preview['sent']); self.assertFalse(preview['dispatch_available'])
            self.assertNotIn('MY_LLM_KEY', item.body.decode())
        self.assertNotIn('CPU-B is still unmeasured.', without.body.decode())
        self.assertIn('CPU-B is still unmeasured.', with_draft.body.decode())
        self.assertNotEqual(without.digest, with_draft.digest)

    def test_retention_in_wire_review_matches_preview_and_errors_name_configuration(self):
        item = prepared()
        self.assertEqual('workspace-history', decode(item.review.payload)['retention'])
        self.assertEqual(decode(item.review.payload)['retention'], item.preview()['policy']['local_retention'])
        code, _, err = self.invoke('inspect', '--directory', str(self.config))
        self.assertEqual(1, code)
        self.assertIn('provider configuration could not be read', err)
        self.assertNotIn('backup could not be read', err)
        code, _, err = self.invoke('inspect', '--directory', str(self.root/'missing'))
        self.assertEqual(1, code)
        self.assertIn('provider configuration directory', err)

    def test_complete_wire_bound_refuses_large_selected_context_before_any_effect(self):
        from claimbranch.core.context import ContextRecord, compile_context
        from tests.application.test_paper_proposals import context
        bundle = context(); records = []
        for record in bundle.records:
            fields = decode(record.fields); fields['statement'] = 'x'*16000
            if record.kind == 'observation': fields['conditions'] = 'x'*14000
            records.append(ContextRecord.create(record.project_id, record.id, record.kind,
                record.sensitivity, fields, schema_version=2))
        bundle = compile_context(tuple(records), bundle.selection)
        self.assertLess(len(bundle.payload), 65536)
        with self.assertRaisesRegex(ContractError, 'Complete provider request'):
            prepare_provider_request(profile(), bundle, request_id='r', nonce='n', now=100)

    def test_request_recheck_binds_endpoint_model_limits_secret_reference_context_and_expiry(self):
        item = prepared()
        item.recheck(item.profile, item.context, now=219)
        for update in ({'endpoint': 'https://elsewhere.example/v1'}, {'model': 'other-model'},
                       {'output_tokens': 100}, {'credential_env': 'OTHER_KEY'}, {'json_mode': 'prompt-only'}):
            changed = ProviderProfile(canonical_bytes(item.profile.value | update))
            with self.subTest(update=update), self.assertRaises(ContractError):
                item.recheck(changed, item.context, now=100)
        for now in (99, 220, True):
            with self.assertRaises(ContractError): item.recheck(item.profile, item.context, now=now)
        with self.assertRaises(ContractError):
            replace(item, body=item.body+b' ').recheck(item.profile, item.context, now=100)
        with self.assertRaises(ContractError):
            item.recheck(item.profile, prepared(include_draft=True).context, now=100)

    def test_wire_dialects_expose_exact_fields_and_loopback_is_not_local_only_or_qualified(self):
        body = json.loads(prepared('anthropic-messages').body)
        self.assertIn('system', body); self.assertEqual(4096, body['max_tokens'])
        self.assertNotIn('response_format', body)
        self.assertNotIn('tools', body)
        local = profile(endpoint='http://127.0.0.1:1234/v1/chat/completions', credential_env=None)
        self.assertTrue(local.destination.remote_capable)
        self.assertFalse(local.readiness()['dispatch_available'])
        self.assertEqual('owner/my-model:variant', profile(model='owner/my-model:variant').value['model'])
        custom = profile(output_limit_field='max_tokens', json_mode='prompt-only')
        item = prepared()
        custom_body = json.loads(prepare_provider_request(custom, item.context, request_id='r', nonce='n', now=100).body)
        self.assertNotIn('response_format', custom_body)
        self.assertNotIn('max_completion_tokens', custom_body)

    def test_both_api_results_pass_closed_typed_decoder_without_staging(self):
        app = fixture(); before = app.paper.history.manifest()
        for api in ('openai-chat', 'anthropic-messages'):
            item = prepared(api)
            raw = json.dumps(wrapper(api, canonical_bytes(response()).decode())).encode()
            self.assertEqual(response(), decode(decode_provider_response(item, raw)))
        self.assertEqual(before, app.paper.history.manifest())
        self.assertEqual([], app.paper.proposal_history())

    def test_truncated_refused_tools_multiple_choices_and_unselected_references_refuse(self):
        text = canonical_bytes(response()).decode()
        base = wrapper('openai-chat', text)
        bad = []
        for finish in ('length', 'tool_calls', 'content_filter', None):
            value = deepcopy(base); value['choices'][0]['finish_reason'] = finish; bad.append(value)
        for field in ('tool_calls', 'function_call', 'refusal'):
            value = deepcopy(base); value['choices'][0]['message'][field] = 'untrusted'; bad.append(value)
        value = deepcopy(base); value['choices'].append(value['choices'][0]); bad.append(value)
        value = deepcopy(base); value['choices'][0]['message']['content'] = '```json\n'+text+'\n```'; bad.append(value)
        value = response(); value['items'][1]['body']['source_id']['id'] = 'unselected-record'
        bad.append(wrapper('openai-chat', canonical_bytes(value).decode()))
        for value in bad:
            with self.subTest(value=str(value)[:80]), self.assertRaises(ContractError):
                decode_provider_response(prepared(), json.dumps(value).encode())
        for raw in (b'[]', b'{', b'{"choices":[],"choices":[]}', b'x'*65537):
            with self.assertRaises(ContractError): decode_provider_response(prepared(), raw)
        for stop in ('max_tokens', 'tool_use'):
            value = wrapper('anthropic-messages', text); value['stop_reason'] = stop
            with self.assertRaises(ContractError):
                decode_provider_response(prepared('anthropic-messages'), json.dumps(value).encode())

    def test_null_and_empty_tool_arrays_are_not_invocations_but_wrong_shapes_refuse(self):
        expected = response(); text = canonical_bytes(expected).decode()
        for fields in ({'tool_calls': []}, {'tool_calls': None}, {'function_call': None},
                       {'tool_calls': [], 'function_call': None, 'refusal': None}):
            value = wrapper('openai-chat', text); value['choices'][0]['message'].update(fields)
            self.assertEqual(expected, decode(decode_provider_response(prepared(), json.dumps(value).encode())))
        for fields in ({'tool_calls': {}}, {'tool_calls': False}, {'function_call': {}},
                       {'tool_calls': [{'type': 'function', 'function': {'name': 'write'}}]}):
            value = wrapper('openai-chat', text); value['choices'][0]['message'].update(fields)
            with self.assertRaises(ContractError): decode_provider_response(prepared(), json.dumps(value).encode())

    def test_nonfinite_overflow_metadata_refuses_without_rejecting_ordinary_fraction(self):
        raw = json.dumps(wrapper('openai-chat', canonical_bytes(response()).decode())).encode()
        self.assertEqual(response(), decode(decode_provider_response(prepared(), raw)))
        for value in (b'1e999', b'-1e999', b'NaN', b'Infinity'):
            with self.subTest(value=value), self.assertRaises(ContractError):
                decode_provider_response(prepared(), raw.replace(b'0.5', value))

    def personal_project(self):
        paper, work = self.root/'paper', self.root/'work'
        paper.mkdir(); work.mkdir(mode=0o700)
        subprocess.run(['git', 'init', '-q', str(paper)], check=True)
        source = b'% claimbranch:start id=anchor\nUndecided.\n% claimbranch:end id=anchor\n'
        (paper/'paper.tex').write_bytes(source)
        association = preview_association(paper, 'paper.tex', 'anchor', work)
        project = prepare_project(association, project_id='novel-study', title='New temperature study',
            thesis='Temperature may affect latency.', question='Is the latency change reproducible?')
        with PersonalProjectStore.create(work, project_id=project.project_id) as store:
            store.save(project, preview=association)
        app = project_workspace(project)
        return paper, work, app

    def test_public_saved_project_preview_is_read_only_and_unsupported_records_refuse(self):
        self.assertEqual(0, self.configure()[0])
        paper, work, app = self.personal_project()
        before = (work/'personal.cbp').read_bytes(); manuscript = (paper/'paper.tex').read_bytes()
        with patch('socket.socket', side_effect=AssertionError('network forbidden')):
            code, out, err = self.invoke('preview', '--directory', str(self.config),
                '--project-directory', str(work), '--node', 'thesis', '--record', 'thesis')
        self.assertEqual((0, ''), (code, err))
        preview = json.loads(out)
        self.assertIn('Temperature may affect latency.', json.dumps(preview))
        self.assertEqual(before, (work/'personal.cbp').read_bytes())
        self.assertEqual(manuscript, (paper/'paper.tex').read_bytes())
        self.assertEqual([], app.paper.proposal_history())
        for key in ('provisional-result', 'unknown-record'):
            code, _, _ = self.invoke('preview', '--directory', str(self.config),
                '--project-directory', str(work), '--node', 'thesis', '--record', key)
            self.assertEqual(1, code)

    def test_configuration_and_secrets_are_absent_from_research_backup(self):
        self.assertEqual(0, self.configure()[0])
        _, work, _ = self.personal_project()
        with PersonalProjectStore(work) as store:
            raw = store.backup()
        self.assertNotIn(b'MY_LLM_KEY', raw)
        self.assertNotIn(b'provider-profile', raw)
        self.assertNotIn(b'llm.example', raw)

    def test_research_and_archives_refuse_existing_provider_directory_in_reverse_order(self):
        from claimbranch.application.personal_archive import PersonalArchive, PersonalExport
        from claimbranch.application.work_archive import WorkArchive
        self.assertEqual(0, self.configure()[0])
        original = (self.config/'provider.json').read_bytes()
        for factory in (PersonalArchive, PersonalExport, WorkArchive,
                        lambda directory: PersonalProjectStore.create(directory, project_id='my-study')):
            with self.subTest(factory=factory), self.assertRaisesRegex(ContractError, 'separate directory'):
                with factory(self.config):
                    self.fail('Research/archive session must refuse before creating any file.')
        self.assertEqual(['provider.json'], [p.name for p in self.config.iterdir()])
        self.assertEqual(original, (self.config/'provider.json').read_bytes())
        with ProviderProfileStore(self.config) as store:
            self.assertEqual(original, store.read())

    def test_real_cli_process_shows_honest_readiness_without_key(self):
        self.assertEqual(0, self.configure()[0])
        result = subprocess.run([sys.executable, '-B', '-m', 'claimbranch', 'provider', 'inspect',
            '--directory', str(self.config)], capture_output=True, text=True, timeout=10)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertFalse(json.loads(result.stdout)['dispatch_available'])
