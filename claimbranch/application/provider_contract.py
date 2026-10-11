"""Closed credential-free connection/request schemas; no store or I/O imports."""
from claimbranch.core.research_schema import nullable, obj

PROFILE_SCHEMA = obj(
    schema={'const': 'claimbranch.provider-profile/v1'},
    api={'enum': ['openai-chat', 'anthropic-messages']},
    endpoint={'type': 'string', 'minLength': 1, 'maxLength': 1024},
    # API model names are not scientific record IDs: e.g. owner/model:variant.
    model={'type': 'string', 'minLength': 1, 'maxLength': 128, 'x-utf8-maxBytes': 128,
           'pattern': '^[A-Za-z0-9][A-Za-z0-9._:/@+\u002d]*$'},
    credential_env=nullable({'type': 'string', 'minLength': 1, 'maxLength': 128,
                             'pattern': '^[A-Z_][A-Z0-9_]*$'}),
    output_tokens={'type': 'integer', 'minimum': 1, 'maximum': 8192},
    output_limit_field={'enum': ['max_tokens', 'max_completion_tokens']},
    json_mode={'enum': ['json-object', 'prompt-only']})
MAX_PROFILE_BYTES = 4096
MAX_WIRE_BYTES = 65_536
POLICY = {
    'review_seconds': 120, 'connect_seconds': 5, 'read_seconds': 15,
    'total_seconds': 60, 'header_seconds': 60, 'attempts_per_judgment': 3,
    'request_bytes': MAX_WIRE_BYTES, 'response_bytes': 65_536,
    'streaming': False, 'automatic_retry': False, 'redirects': False,
    'model_fallback': False, 'environment_proxies': False,
    'tls_trust': 'Python default trust; no environment CA overrides or verification bypass',
    'local_retention': 'workspace-history',
    'local_retention_details': 'Existing bounded workspace history and required origins; no credentials. '
                       'Optional response payload may be unavailable; no automatic expiry or upload.',
    'provider_retention': 'Unknown; check the selected service and account. No zero-retention guarantee.'}
# Historical v1 literals must not borrow from running defaults, profile fields
# or byte limits. A changed writer needs an explicit new version and reader.
WIRE_POLICY_V1 = {
    'review_seconds': 120, 'connect_seconds': 5, 'read_seconds': 15,
    'total_seconds': 60, 'header_seconds': 60, 'attempts_per_judgment': 3,
    'request_bytes': 65_536, 'response_bytes': 65_536,
    'streaming': False, 'automatic_retry': False, 'redirects': False,
    'model_fallback': False, 'environment_proxies': False,
    'tls_trust': 'Python default trust; no environment CA overrides or verification bypass',
    'local_retention': 'workspace-history',
    'local_retention_details': 'Existing bounded workspace history and required origins; no credentials. '
                       'Optional response payload may be unavailable; no automatic expiry or upload.',
    'provider_retention': 'Unknown; check the selected service and account. No zero-retention guarantee.'}
RETAINED_POLICY = obj(**{key: {'const': value} for key, value in WIRE_POLICY_V1.items()})
WIRE_MODEL_V1 = {'type': 'string', 'minLength': 1, 'maxLength': 128, 'x-utf8-maxBytes': 128,
                 'pattern': '^[A-Za-z0-9][A-Za-z0-9._:/@+\u002d]*$'}
WIRE_DESTINATION_URL_V1 = {'type': 'string', 'minLength': 1, 'maxLength': 1024, 'x-utf8-maxBytes': 1024}
REQUEST_SETTINGS = obj(
    api={'enum': ['openai-chat', 'anthropic-messages']},
    output_tokens={'type': 'integer', 'minimum': 1, 'maximum': 8192},
    output_limit_field={'enum': ['max_tokens', 'max_completion_tokens']},
    json_mode={'enum': ['json-object', 'prompt-only']})
WIRE_HEADERS_V1 = {'openai-chat':{'Content-Type':'application/json', 'Accept':'application/json',
    'Accept-Encoding':'identity', 'Connection':'close'},
    'anthropic-messages':{'Content-Type':'application/json', 'Accept':'application/json',
        'Accept-Encoding':'identity', 'Connection':'close', 'anthropic-version':'2023-06-01'}}
WIRE_REQUEST = obj(schema={'const':'claimbranch.provider-wire-binding/v1'},
    headers_without_credentials={'oneOf':[obj(**{k:{'const':v} for k,v in headers.items()})
                                        for headers in WIRE_HEADERS_V1.values()]},
    profile_digest={'type':'string', 'pattern':'^[0-9a-f]{64}$', 'minLength':64, 'maxLength':64},
    settings=REQUEST_SETTINGS, policy=RETAINED_POLICY,
    context_review_digest={'type':'string', 'pattern':'^[0-9a-f]{64}$', 'minLength':64, 'maxLength':64},
    wire_body_digest={'type':'string', 'pattern':'^[0-9a-f]{64}$', 'minLength':64, 'maxLength':64})

# A CLI login is not an API credential. Do not add this transport to frozen v1
# API settings or pretend that its input is the CLI's complete HTTP wire body.
CODEX_PROFILE_SCHEMA = obj(
    schema={'const':'claimbranch.codex-profile/v1'},
    authentication={'const':'chatgpt-login'},
    client_version={'const':'0.158.0'},
    model={'type':'string', 'minLength':1, 'maxLength':128, 'x-utf8-maxBytes':128,
           'pattern':'^[A-Za-z0-9][A-Za-z0-9._:/@+\u002d]*$'},
    reasoning_effort={'enum':['low','medium','high','xhigh']})
CODEX_INPUT_BINDING = obj(
    schema={'const':'claimbranch.codex-input-binding/v1'},
    profile_digest={'type':'string', 'pattern':'^[0-9a-f]{64}$', 'minLength':64, 'maxLength':64},
    context_review_digest={'type':'string', 'pattern':'^[0-9a-f]{64}$', 'minLength':64, 'maxLength':64},
    application_input_digest={'type':'string', 'pattern':'^[0-9a-f]{64}$', 'minLength':64, 'maxLength':64})

# Historical commitments are independent of future connection defaults and
# prompt compilers. They contain neither login data nor a launch capability.
CODEX_RETAINED_MODEL_V1 = {'type':'string','minLength':1,'maxLength':128,'x-utf8-maxBytes':128,
    'pattern':'^[A-Za-z0-9][A-Za-z0-9._:/@+\u002d]*$'}
CODEX_RETAINED_REQUEST = obj(binding=CODEX_INPUT_BINDING,
    client_version={'const':'0.158.0'}, reasoning_effort={'enum':['low','medium','high','xhigh']})
