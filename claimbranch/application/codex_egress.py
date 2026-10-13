"""Finite request compiler for the selected Codex service.

The CLI's generated messages, environment, nested tools and metadata are not
outbound authority. The separate relay sends these independently compiled bytes
only after foreground review. This module opens no socket or credential.
"""
import hashlib
import json

from claimbranch.core.canonical import ContractError
from .provider_profile import PreparedCodexRequest, _json_bytes

ENDPOINT = 'https://chatgpt.com/backend-api/codex/responses'
MAX_HTTP_BYTES = 262144


def compile_codex_http(prepared, *, current_profile, current_context, now):
    """Compile against current owner-supplied science, profile and clock.

    The caller still owns preview identity and one-shot consent. This pure
    compiler cannot establish ownership or grant sending authority.
    """
    if type(prepared) is not PreparedCodexRequest:
        raise ContractError('Owned Codex application input required.')
    # Recompile the original selected context too: an untrusted caller can
    # recompute a public digest, which is not authority to expand the input.
    prepared.recheck(current_profile, current_context, now=now)
    body = json.loads(prepared.body)
    request = {
        'model': prepared.profile.value['model'],
        'instructions': body['instructions'],
        'input': [{'role': 'user', 'content': [{'type': 'input_text',
            'text': _json_bytes(body['input']).decode('utf-8')}]}],
        'tools': [], 'tool_choice': 'none', 'parallel_tool_calls': False,
        'reasoning': {'effort': prepared.profile.value['reasoning_effort']},
        'store': False, 'stream': True,
        'include': [],
        'text': {'format': {'type': 'text'} if prepared.discussion is not None and not prepared.edit else
            {'type': 'json_schema', 'name': 'claimbranch_proposal',
             'strict': True, 'schema': body['output_schema']}},
    }
    raw = _json_bytes(request)
    if len(raw) > MAX_HTTP_BYTES:
        raise ContractError('Complete Codex HTTP input exceeds its byte limit.')
    return raw


def codex_http_preview(prepared, *, current_profile, current_context, now):
    raw = compile_codex_http(prepared, current_profile=current_profile,
        current_context=current_context, now=now)
    return {'endpoint': ENDPOINT, 'method': 'POST',
        'body': json.loads(raw), 'body_bytes': len(raw),
        'body_sha256': hashlib.sha256(raw).hexdigest(),
        'headers': {'Content-Type': 'application/json',
            'Accept': 'text/event-stream', 'Accept-Encoding': 'identity',
            'Connection': 'close'},
        'authentication': 'Opaque existing-login authorization and optional account header; values excluded.',
        'request_budget': 1, 'automatic_retries': 0,
        'retention': 'Request store=false; actual service retention is not established by this compiler.',
        'sent': False, 'dispatch_available': False}
