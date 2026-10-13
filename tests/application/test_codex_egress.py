"""Literal outbound expectations; no model request or login access."""
from dataclasses import replace
import hashlib
import json
import unittest

from claimbranch.core.canonical import ContractError
from claimbranch.application.codex_egress import compile_codex_http, codex_http_preview
from claimbranch.application.provider_profile import (CodexProfile, prepare_codex_request,
    _codex_input_binding, _json_bytes)
from claimbranch.core.canonical import canonical_bytes
from tests.application.test_paper_proposal_work import fixture, request


class CodexEgressTests(unittest.TestCase):
    def setUp(self):
        app=fixture()
        self.context=app.paper.draft(*app.context_key()).compile_proposal_context(request(app))
        self.profile=CodexProfile.create(model='gpt-6-sol')

    def prepared(self):
        return prepare_codex_request(self.profile,
            self.context, request_id='owned-request', nonce='owned-nonce', now=100)

    def compile(self, prepared, *, now=100):
        return compile_codex_http(prepared, current_profile=self.profile,
            current_context=self.context, now=now)

    def test_only_selected_input_and_explicit_generation_are_in_http(self):
        prepared = self.prepared()
        body = json.loads(self.compile(prepared))
        self.assertEqual({'model','instructions','input','tools','tool_choice',
            'parallel_tool_calls','reasoning','store','stream','include','text'},set(body))
        self.assertEqual('gpt-6-sol',body['model'])
        self.assertEqual([],body['tools'])
        self.assertEqual('none',body['tool_choice'])
        self.assertIs(body['parallel_tool_calls'],False)
        self.assertIs(body['store'],False)
        self.assertIs(body['stream'],True)
        self.assertEqual([],body['include'])
        self.assertEqual({'effort':'medium'},body['reasoning'])
        self.assertEqual(1,len(body['input']))
        self.assertEqual('user',body['input'][0]['role'])
        self.assertEqual({'type','text'},set(body['input'][0]['content'][0]))
        application = json.loads(prepared.body)
        self.assertEqual(application['input'],json.loads(body['input'][0]['content'][0]['text']))
        self.assertEqual(application['instructions'],body['instructions'])
        self.assertEqual(application['output_schema'],body['text']['format']['schema'])
        self.assertIs(body['text']['format']['strict'],True)

    def test_discussion_uses_plain_text_and_binds_the_question(self):
        discussion={'prompt':'Rubric 점수와 실제 글쓰기 품질을 어떻게 구분할까요?', 'previous':[]}
        prepared=prepare_codex_request(self.profile,self.context,
            request_id='discussion-request',nonce='nonce',now=100,discussion=discussion)
        body=json.loads(self.compile(prepared))
        self.assertEqual({'format':{'type':'text'}},body['text'])
        self.assertEqual([],body['tools'])
        selected=json.loads(body['input'][0]['content'][0]['text'])
        self.assertEqual(discussion,selected['discussion'])
        self.assertEqual('claimbranch.provider-advice/v1',json.loads(prepared.review.payload)['result_schema'])
        with self.assertRaises(ContractError):
            self.compile(replace(prepared,discussion=canonical_bytes({'prompt':'Different question', 'previous':[]})))

    def test_empty_or_control_bearing_discussion_refuses_before_send(self):
        for prompt in ('', '   ', 'untrusted\x1b[2J'):
            with self.subTest(prompt=repr(prompt)), self.assertRaises(ContractError):
                prepare_codex_request(self.profile,self.context,request_id='discussion-request',
                    nonce='nonce',now=100,discussion={'prompt':prompt,'previous':[]})

    def test_preview_names_actual_endpoint_and_does_not_grant_send(self):
        prepared=self.prepared(); preview=codex_http_preview(prepared,
            current_profile=self.profile, current_context=self.context, now=100)
        self.assertEqual('https://chatgpt.com/backend-api/codex/responses',preview['endpoint'])
        self.assertEqual('POST',preview['method'])
        self.assertEqual(self.compile(prepared),json.dumps(preview['body'],
            ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())
        self.assertEqual(1,preview['request_budget'])
        self.assertEqual(0,preview['automatic_retries'])
        self.assertIs(preview['sent'],False)
        self.assertIs(preview['dispatch_available'],False)
        self.assertEqual(len(self.compile(prepared)),preview['body_bytes'])
        self.assertEqual(hashlib.sha256(self.compile(prepared)).hexdigest(),preview['body_sha256'])

    def test_altered_input_and_unowned_values_refuse_before_compilation(self):
        prepared=self.prepared()
        for bad in (None,{},replace(prepared,body=prepared.body+b' '),
                    replace(prepared,digest='0'*64)):
            with self.subTest(kind=type(bad).__name__):
                with self.assertRaises(ContractError): self.compile(bad)

    def test_recomputed_digest_cannot_add_unselected_fields(self):
        prepared=self.prepared(); body=json.loads(prepared.body)
        body['input']['ambient_instructions']='Unselected outside context'
        raw=_json_bytes(body)
        forged=replace(prepared,body=raw,digest=hashlib.sha256(canonical_bytes(
            _codex_input_binding(prepared.profile,prepared.review,raw))).hexdigest())
        with self.assertRaises(ContractError): self.compile(forged)

    def test_actual_clock_rejects_expired_future_and_noninteger_reviews(self):
        prepared=self.prepared()
        for now in (99, prepared.review.expires_at, True, 100.0):
            with self.subTest(now=now):
                with self.assertRaises(ContractError): self.compile(prepared,now=now)

    def test_current_profile_and_context_are_independent_of_prepared_values(self):
        prepared=self.prepared()
        changed_profile=CodexProfile.create(model='gpt-6-sol',reasoning_effort='low')
        changed_context=replace(self.context, digest='0'*64)
        for profile,context in ((changed_profile,self.context),(self.profile,changed_context)):
            with self.subTest(profile=profile.digest,context=context.digest):
                with self.assertRaises(ContractError):
                    compile_codex_http(prepared,current_profile=profile,current_context=context,now=100)
