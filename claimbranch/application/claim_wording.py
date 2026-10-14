"""Reviewed personal wording restrictions and conservative read-only lint."""
import base64
import hashlib
import json
import re
import secrets
import sys
import unicodedata
from datetime import datetime, timezone
from claimbranch.core.canonical import ContractError
from claimbranch.core.paper_capacity import decode
from .manuscript_anchors import source_statuses
from .paper_work_store import PaperWork
from claimbranch.core.wording_policy import visible_text, anchor_commitment


def literal_present(text,phrase):
    text=re.sub(r'\s+',' ',unicodedata.normalize('NFC',text).casefold())
    phrase=re.sub(r'\s+',' ',unicodedata.normalize('NFC',phrase).casefold())
    pattern=(r'(?<!\w)' if phrase[0].isalnum() or phrase[0]=='_' else '')+re.escape(phrase)+(r'(?!\w)' if phrase[-1].isalnum() or phrase[-1]=='_' else '')
    return re.search(pattern,text) is not None


def lint(history):
    view=history.view('main');warnings=[];freshness=source_statuses(history)
    anchors=view.get('manuscript_anchors',{});policies=view.get('wording_policies',{})
    dependencies=view.get('companion_dependencies',{});contexts=view.get('anchor_contexts',{})
    def warn(code,anchor,claim=None,**detail): warnings.append(dict(code=code,anchor_id=anchor,claim_id=claim,**detail))
    for key,anchor in sorted(anchors.items()):
        if not freshness[key]['block_matches'] or freshness[key]['status']=='identity-changed':
            warn('source-unavailable-or-changed',key);continue
        block=b''.join(base64.b64decode(part) for part in anchor['block']).decode('utf-8')
        # Comments are outside lexical checks; escaped percent remains literal.
        text=visible_text(block)
        if '\\' in text: warn('unsupported-tex-semantics',key)
        context=contexts.get(key,{})
        if context and context.get('anchor_commitment')!=anchor_commitment(anchor):
            warn('anchor-context-stale',key);context={}
        for claim in anchor['expresses']:
            policy=policies.get(claim)
            if policy:
                where=context.get('placement','unknown')
                if where=='unknown': warn('placement-unknown',key,claim)
                elif where not in policy['placement']: warn('placement-mismatch',key,claim,placement=where,allowed=policy['placement'])
                for phrase in policy['banned_phrases']:
                    if literal_present(text,phrase): warn('banned-phrase',key,claim,phrase=phrase)
                for phrase in policy['required_caveats']:
                    if not literal_present(text,phrase): warn('caveat-text-not-found',key,claim,phrase=phrase)
            for dependency in dependencies.values():
                if dependency['status']!='active' or dependency['target_id']!=claim:continue
                companion=dependency['companion_id']; did=dependency['id']
                if companion not in anchor['expresses']+anchor['plots']:
                    warn('missing-companion-association',key,claim,dependency_id=did,companion_id=companion)
                elif dependency['scope']=='paragraph':
                    if not context or context.get('block_digest')!=anchor['block_digest']:
                        warn('paragraph-coverage-unknown',key,claim,dependency_id=did);continue
                    paragraphs=context['paragraphs'];uses=[p for p in paragraphs if claim in p['expresses']]
                    if not uses:warn('paragraph-coverage-unknown',key,claim,dependency_id=did)
                    for paragraph in uses:
                        if companion not in paragraph['expresses']+paragraph['plots']:
                            warn('missing-paragraph-companion',key,claim,dependency_id=did,index=paragraph['index'],companion_id=companion)
    return dict(warnings=warnings,freshness=freshness,registered_anchor_count=len(anchors),policy_count=len(policies),paragraph_completeness_verified=False,write_available=False,scientific_validity_verified=False,
        coverage='Registered current blocks and explicit declarations only. Case-insensitive literal word boundaries; no semantic, macro, include, graphics or complete-paragraph certification. No debt or status changes.')


def prepare_revision(project,kind,payload,*,contribution_origin=None):
    history=project.work.history
    if history.schema_version not in (4,5):raise ContractError('Wording restrictions require a paper profile.')
    command=dict(schema_version=7,id='wording-'+secrets.token_hex(12),project_id=project.project_id,
        episode_id=history.view('main')['episode_id'],created_at=datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
        operation_type=kind,expected_heads=dict(history.heads),evidence_watermark=history.watermark,payload=payload)
    from .metadata_batch import origin_command
    command=origin_command(command,contribution_origin)
    candidate=history.append(command)
    from .paper_service import PaperService
    before=PaperService(history).query('main');after=PaperService(candidate).query('main')
    roots=[payload['claim_id']] if kind=='set-claim-wording' else [payload['target_id'],payload['companion_id']] if kind=='set-claim-companion' else [payload['anchor_id']]
    review_companions=[]
    if kind=='set-claim-wording':
        review_companions=sorted({d['companion_id'] for d in candidate.view('main').get('companion_dependencies',{}).values() if d['status']=='active' and d['target_id']==payload['claim_id']})
        roots+=review_companions
    impact=PaperService(candidate).anchor_impact(roots)
    impact['review_companion_ids']=review_companions # context reach, not a scientific edit
    workspace=decode(project.work.payload,purpose='project').get('workspace')
    if workspace is not None:
        from .tui_project import project_workspace
        from .personal_research import _install
        from .tui_work_recovery import snapshot_value
        app=project_workspace(project);_install(app,candidate,app.episode_id,app.ref,app.selected_id);workspace=snapshot_value(app)
    result=project.with_work(PaperWork.create(candidate,workspace=workspace))
    return result,dict(project_digest=hashlib.sha256(project.payload).hexdigest(),operation=command,
        before=before,after=after,impact=impact,lint=lint(candidate),freshness=source_statuses(history),
        write_available=False,authority='personal explicit confirmation; no protected approval')


def recheck_revision(project,preview):
    if hashlib.sha256(project.payload).hexdigest()!=preview['project_digest'] or source_statuses(project.work.history)!=preview['freshness']:
        raise ContractError('wording review project or manuscript changed; preview again')


def run_wording_command(args):
    from .personal_project import PersonalProjectStore
    with PersonalProjectStore(args.directory) as store:
        project=store.load()
        if args.project_action=='wording-lint':print(json.dumps(lint(project.work.history),ensure_ascii=False,sort_keys=True,indent=2));return 0
        if args.project_action=='claim-policy':
            kind='set-claim-wording';payload=dict(claim_id=args.claim,grade=args.grade,limitation=args.limitation,
                allowed_wording=args.allowed,required_caveats=args.caveat,banned_phrases=args.ban,placement=args.placement,rationale=args.reason)
        elif args.project_action=='claim-companion':
            kind='set-claim-companion';payload=dict(id=args.id,target_id=args.claim,companion_id=args.companion,
                scope=args.scope,status='retired' if args.retire else 'active',rationale=args.reason)
        else:
            kind='set-anchor-context';payload=dict(anchor_id=args.anchor,placement=args.placement,paragraphs=[],rationale=args.reason)
            if args.paragraphs:
                from .project_commands import _read_argument_input
                payload['paragraphs']=decode(_read_argument_input(args.paragraphs),purpose='project')
        result,preview=prepare_revision(project,kind,payload,contribution_origin=args.origin)
        from .tui_model import clean
        lines=clean(json.dumps(preview,ensure_ascii=False,indent=2)).splitlines()
        if args.dry_run:print('\n'.join(lines));return 0
        if not sys.stdin.isatty() or not sys.stdout.isatty():raise ContractError('Wording changes require an interactive terminal; use --dry-run.')
        for start in range(0,len(lines),60):
            print('\n'.join(lines[start:start+60]),flush=True)
            if start+60<len(lines) and input('Enter: next page / q: cancel: ').strip().lower()=='q':return 0
        if input('Type record to save this reporting restriction, or Enter to cancel: ').strip()!='record':return 0
        recheck_revision(store.load(),preview);store.verify_unchanged();recheck_revision(project,preview);store.save(result)
        print('Reporting restriction saved; manuscript, evidence status and understanding work unchanged.')
    return 0
