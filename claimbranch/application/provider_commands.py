"""Public BYO preparation and personal-session attachment with a closed live gate."""
import json
import secrets
import sys
import time

from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_context import FIELDS
from .personal_project import PersonalProjectStore
from .provider_profile import (ProviderProfile, CodexProfile, ProviderProfileStore,
    load_provider_profile, prepare_personal_provider_request)
from .tui_model import clean
from .tui_project import project_workspace


class PersonalProviderConnection:
    """Session-only selected profile; configuration cannot qualify a deployment.

    Actual provider evidence is still missing. The public qualification gate
    deliberately refuses before transport creation or credential lookup. Owned
    test peers replace that check to exercise the downstream integration only.
    No serialized flag, CLI switch or restored checkpoint can bypass it.
    """
    def __init__(self, directory):
        self.store = ProviderProfileStore(directory)
        self.profile = self.workspace = None
        self.enabled = False
        self.transports = {}

    def __enter__(self):
        self.store.__enter__()
        try:
            self.profile = load_provider_profile(self.store.read())
        except BaseException:
            self.close()
            raise
        self.enabled = True
        return self

    def attach(self, app):
        from .tui_retention import personal
        if not personal(app):
            raise ContractError('Personal LLM attachment requires the personal project entry.')
        self.current_profile()
        self.workspace = app.paper
        app.provider_connection = self
        app.message = 'Personal LLM selected for unsent previews. Live provider not qualified; manual work remains available.'

    def current_profile(self):
        if not self.enabled:
            raise ContractError('AI OFF. Manual work and earlier AI origins remain available.')
        current = load_provider_profile(self.store.read())
        if current != self.profile:
            raise ContractError('Provider configuration changed. Reopen with the intended profile and review a new request.')
        return current

    def require_qualification(self, profile):
        raise ContractError('Actual provider not qualified. No key was read or request sent. '
                            'Continue manually; actual research-file, mount, credential, IPC and API evidence is required.')

    def begin(self, worker, prepared):
        profile = self.current_profile()
        if worker.workspace is not self.workspace or prepared.profile != profile:
            raise ContractError('The selected personal connection or request owner changed; review again.')
        if type(profile) is CodexProfile:
            from .paper_proposal_work import CodexProposalPreview
            if type(worker) is not CodexProposalPreview:
                raise ContractError('The selected Codex preview owner changed.')
            worker.recheck_preview(prepared, profile)
            raise ContractError('Actual Codex client not qualified. No client, login credential or request was used. '
                'Restricted runtime access, exact destinations/wrapper and checked return must be verified. '
                'This is an application input preview; continue manually.')
        self.require_qualification(profile)
        from .provider_transport import ProviderTransport
        transport = self.transports.get(worker.owner)
        if transport is None:
            transport = self.transports[worker.owner] = ProviderTransport()
        worker.begin(prepared, transport=transport, confirmed_digest=prepared.digest, current_profile=profile)

    def close(self):
        self.enabled = False
        for transport in self.transports.values():
            transport.close()
        for transport in self.transports.values():
            transport.wait_closed(2)
        self.transports.clear()
        self.store.close()


def add_provider_commands(commands):
    provider = commands.add_parser('provider', help='Prepare your own LLM API or Codex login connection; live dispatch is not enabled')
    actions = provider.add_subparsers(dest='provider_action', required=True)
    for name in ('configure', 'configure-codex', 'inspect', 'preview'):
        action = actions.add_parser(name)
        action.add_argument('--directory', required=True, help='Existing private configuration directory outside Git, separate from research/backup')
        if name == 'configure-codex':
            action.add_argument('--model', required=True, help='Explicit Codex model; no automatic selection')
            action.add_argument('--reasoning-effort', choices=('low','medium','high','xhigh'), default='medium')
            action.add_argument('--dry-run', action='store_true', help='Validate/show configuration; no client, key read or write')
        elif name == 'configure':
            action.add_argument('--api', required=True, choices=('openai-chat', 'anthropic-messages'))
            action.add_argument('--endpoint', required=True, help='Exact POST URL, including /chat/completions or /messages; no key/query/fragment')
            action.add_argument('--model', required=True, help='Your server\'s model ID; no automatic model selection')
            action.add_argument('--credential-env', help='Environment variable NAME only; never put a key on the command line')
            action.add_argument('--output-tokens', type=int, default=4096)
            action.add_argument('--output-limit-field', choices=('max_tokens', 'max_completion_tokens'))
            action.add_argument('--json-mode', choices=('json-object', 'prompt-only'))
            action.add_argument('--dry-run', action='store_true', help='Validate/show configuration; write nothing')
        elif name == 'preview':
            action.add_argument('--project-directory', required=True, help='Saved personal project; close its TUI first')
            action.add_argument('--node', required=True, help='Recorded node owning the judgment; never a provisional result')
            action.add_argument('--episode', help='Episode ID; defaults to saved selection')
            action.add_argument('--ref', help='Reasoning ref; defaults to saved selection')
            action.add_argument('--record', action='append', default=[], help='Explicit recorded context ID, repeatable; no hidden neighbors')
            action.add_argument('--relation', action='append', default=[], help='Scientific relation ID; explicitly include its endpoints with --record')
            action.add_argument('--purpose', choices=('compare-evidence', 'critique-interpretation', 'plan-experiment'), default='critique-interpretation')
            action.add_argument('--include-draft', action='store_true', help='Explicitly include the kept, possibly unfinished owning judgment and reason')


def preview_saved_request(profile, args):
    with PersonalProjectStore(args.project_directory) as store:
        project = store.load()
        app = project_workspace(project)
        app.switch_context(args.episode or app.episode_id, args.ref or app.ref)
        if args.node not in {row['id'] for row in app.view['nodes']}:
            raise ContractError('Choose a recorded node in this episode/ref; provisional/candidate context is excluded.')
        app.select(args.node, remember=False)
        nodes = {row['id']: row for row in app.view['nodes']}
        if len(args.record) != len(set(args.record)) or len(args.relation) != len(set(args.relation)):
            raise ContractError('Select each context record or relation once.')
        selections = []
        for key in args.record:
            row = nodes.get(key)
            if row is None or row['kind'] not in FIELDS:
                raise ContractError('Requested context record is unavailable or unsupported in this view.')
            selections.append({'record_id': key, 'fields': list(FIELDS[row['kind']])})
        request = {'schema_version': 1, 'project_id': project.project_id, 'episode_id': app.episode_id,
            'ref': app.ref, 'view_digest': app.view['digest'], 'purpose': args.purpose,
            'selections': selections, 'scientific_edge_ids': args.relation}
        session = app.paper.draft(*app.full_context(app.work_key()))
        context = session.compile_proposal_context(request, include_draft=args.include_draft)
        prepared = prepare_personal_provider_request(profile, context, request_id='request-'+secrets.token_hex(16),
            nonce=secrets.token_hex(24), now=int(time.time()))
        store.verify_unchanged()
        return prepared.preview()


def run_provider_command(args):
    try:
        if args.provider_action in ('configure', 'configure-codex'):
            profile = (CodexProfile.create(model=args.model, reasoning_effort=args.reasoning_effort)
                if args.provider_action == 'configure-codex' else ProviderProfile.create(api=args.api, endpoint=args.endpoint, model=args.model,
                credential_env=args.credential_env, output_tokens=args.output_tokens,
                output_limit_field=args.output_limit_field, json_mode=args.json_mode))
            # Check private placement even for dry run; do not create the directory.
            with ProviderProfileStore(args.directory) as store:
                if not args.dry_run:
                    store.write(profile.payload)
            result = profile.readiness()
            result['configuration_saved'] = not args.dry_run
        else:
            with ProviderProfileStore(args.directory) as store:
                profile = load_provider_profile(store.read())
            result = (preview_saved_request(profile, args) if args.provider_action == 'preview'
                      else profile.readiness())
        print(clean(json.dumps(result, ensure_ascii=False, indent=2)))
        return 0
    except KeyboardInterrupt:
        print('Provider preparation interrupted. No research was sent. Preserve any incomplete configuration; '
              'inspect it or retry in a fresh private configuration directory.', file=sys.stderr)
        return 130
    except (ContractError, OSError) as error:
        print('Provider preparation unavailable: '+clean(str(error))+'\nNo research was sent; manual project work remains available.', file=sys.stderr)
        return 1
