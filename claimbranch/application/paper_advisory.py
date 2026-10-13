"""Resolve explicitly selected earlier discussion without expanding graph context."""
from claimbranch.core.advisory import checked_advice, discussion_input
from claimbranch.core.canonical import ContractError, canonical_bytes, digest


def select_discussion(workspace, owner, prompt, previous_requests=()):
    if type(previous_requests) not in (list, tuple) or len(previous_requests) > 2:
        raise ContractError('Select at most two earlier responses')
    previous = []
    entries = {entry['request_id']: entry for entry in workspace._proposal_entries}
    for key in previous_requests:
        entry = entries.get(key) if type(key) is str else None
        if (entry is None or tuple(entry['owner']) != tuple(owner) or not ('discussion' in entry or 'edit' in entry)
                or entry['result'] is None or entry['provider_disposition'] != 'proposed'):
            raise ContractError('Select retained advice from this judgment; unavailable replies remain historical')
        result = entry['result']
        if 'discussion' in entry:
            result = checked_advice(canonical_bytes(result)); text = result['text']
        elif result['items'] or not result['critique']:
            raise ContractError('Select readable advice or a clarification without graph items')
        else: text = result['critique']
        if digest(result) != entry['normalized_digest']:
            raise ContractError('Earlier response changed')
        previous.append({'request_id':key, 'prompt':entry.get('discussion',entry.get('edit'))['prompt'],
            'text':text, 'context_digest':entry['context_digest'],
            'reply_digest':entry['normalized_digest']})
    return discussion_input({'prompt':prompt, 'previous':previous})


def check_discussion_sources(entry, earlier):
    discussion = discussion_input(entry.get('discussion',entry.get('edit')))
    for message in discussion['previous']:
        source = earlier.get(message['request_id'])
        if source is None or not ('discussion' in source or 'edit' in source):
            raise ContractError('Selected conversation lacks its original response')
        result = ({'schema':'claimbranch.provider-advice/v1','status':'ok','text':message['text']}
            if 'discussion' in source else {'schema':'claimbranch.provider-result/v2','status':'ok',
                'critique':message['text'],'items':[]})
        if (source['owner'] != entry['owner'] or source['provider_disposition'] != 'proposed'
                or source['normalized_digest'] != message['reply_digest']
                or source.get('discussion',source.get('edit'))['prompt'] != message['prompt']
                or source['context_digest'] != message['context_digest']
                or digest(result) != message['reply_digest']):
            raise ContractError('Selected conversation differs from its earlier owned response')



class AdviceEdits:
    """Fresh local passage comparison; creates only an editable unaccepted form."""
    def __init__(self, workspace, owner, request_id, *, clock=None):
        self.workspace, self.owner, self.request_id = workspace, tuple(owner), request_id
        self.session = workspace.draft(*owner)
        self.work = workspace.candidates(*owner)
        self.clock = clock or self.session._clock
        self._previews = {}
        app = workspace._checkpoint_app
        if app is None:
            raise ContractError('Passage preparation requires an owning writing workspace')
        self.inputs = app.review.candidate_inputs.setdefault(self.owner,{})
        self._source()

    def _source(self):
        from .paper_proposal_work import _bundle
        entry = next((e for e in self.workspace._proposal_entries if e['request_id']==self.request_id), None)
        if (entry is None or tuple(entry['owner']) != self.owner or 'discussion' not in entry
                or entry['result'] is None or entry['provider_disposition'] != 'proposed'
                or entry['payload_availability'] != 'available'):
            raise ContractError('Select retained advice from this owning judgment')
        reply = checked_advice(canonical_bytes(entry['result']))
        if digest(reply) != entry['normalized_digest']:
            raise ContractError('Retained advice changed')
        original = _bundle(self.workspace.history,entry)
        current = self.session.compile_proposal_context(entry['request'],include_draft=entry['draft_fields'] is not None)
        if current != original or entry['source']['digest'] != self.session._view_digest:
            raise ContractError('Research context changed; read old advice or request new assistance')
        self.work.require_current()
        return entry, reply

    def preview(self, kind, start, end):
        import secrets
        from claimbranch.core.paper_changes import advice_prefill
        from claimbranch.core.research_schema import TEXT, normalize
        with self.workspace._lock:
            entry,reply = self._source()
            if (type(start) is not int or type(end) is not int or not 0 <= start < end <= len(reply['text'])):
                raise ContractError('Choose an exact range of the retained answer')
            passage = normalize(reply['text'][start:end],TEXT)
            if not passage.strip(): raise ContractError('Choose a nonblank passage')
            value = {'request_id':self.request_id,'entry_digest':digest(entry),'kind':kind,
                'start':start,'end':end,'passage':passage,'body':advice_prefill(kind,passage),
                'record_id':self.work.allocate_id(),'action_id':'passage-'+secrets.token_hex(16),
                'work_revision':self.work.revision,'draft_revision':self.session._revision,
                'created_at':int(self.clock()),'expires_at':int(self.clock())+60}
            value['digest']=digest(value)
            self._previews[value['digest']]=canonical_bytes(value)
            return value

    def prefill(self, comparison):
        from copy import deepcopy
        from claimbranch.core.paper_changes import AmendmentLineage
        from .paper_proposal_work import check_capacity, proposal_snapshot
        with self.workspace._lock:
            entry,reply = self._source()
            if (type(comparison) is not dict or self._previews.get(comparison.get('digest')) != canonical_bytes(comparison)
                    or digest(entry)!=comparison['entry_digest'] or self.work.revision!=comparison['work_revision']
                    or self.session._revision!=comparison['draft_revision']
                    or not comparison['created_at'] <= int(self.clock()) < comparison['expires_at']):
                raise ContractError('Reopen this exact passage comparison; no draft was created')
            for lineage in self.work.origins.values():
                from claimbranch.core.canonical import decode
                for revision in decode(lineage.payload)['revisions']:
                    origin=revision.get('advisory_origin')
                    if (origin and origin['request_id']==self.request_id and origin['start']==comparison['start']
                            and origin['end']==comparison['end'] and revision['amendment']['kind']==comparison['kind']):
                        raise ContractError('This passage already has a draft here; open argument drafts to continue it')
            record={'id':comparison['record_id'],'kind':comparison['kind'],'body':deepcopy(comparison['body'])}
            origin={k:entry[k] for k in ('request_id','request_digest','context_digest','response_digest','trace_digest')}
            origin.update(reply_digest=entry['normalized_digest'],
                passage=comparison['passage'],passage_digest=digest(comparison['passage']),
                start=comparison['start'],end=comparison['end'],action_id=comparison['action_id'])
            lineage=AmendmentLineage.start(self.session._project,self.owner[0],record,advisory_origin=origin)
            inputs={**self.inputs,record['id']:record}
            origins={**self.work.origins,record['id']:lineage}
            if len(set(inputs)|set(self.work.records))>64: raise ContractError('This work holds at most 64 candidates')
            check_capacity(self.workspace,proposal_snapshot(self.workspace,origins={self.owner:origins}),
                unfinished={self.owner:inputs})
            self.inputs[record['id']]=record
            self.work._origins=origins
            self.work._changed()
            self._previews.pop(comparison['digest'])
            return record['id']
