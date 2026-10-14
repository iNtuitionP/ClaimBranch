import hashlib,json,time,resource
from claimbranch.core.research_history import ResearchHistory
from claimbranch.core.paper_capacity import encode, decode
from claimbranch.core.canonical import digest

def combined(*, corrections=True, counts=256, episodes=32, edges=512, claims=63, plans=64):
    h=ResearchHistory.start_lifecycle('capacity-paper','Synthetic paper capacity','thesis','The synthetic conditions require separate claims.','anchor')
    seed=h.seed
    heads={'main':dict(h.heads)['main']}; watermark=0; commands=[]; current='episode-0'; last_events={}
    def add(kind,payload,episode=None):
        nonlocal watermark,current,heads
        if episode: current=episode
        key='operation-%s'%len(commands)
        cmd=dict(schema_version=4,id=key,project_id='capacity-paper',episode_id=current,
                 created_at='2026-10-13T00:00:00Z',operation_type=kind,
                 expected_heads=dict(heads),evidence_watermark=watermark,payload=payload)
        commands.append(encode(cmd,purpose='history'))
        if kind=='record-evidence-event': watermark+=1
        elif kind=='open-episode': heads={'main':heads['main']}
        elif kind=='create-reasoning-branch': heads['alternative']=key
        elif kind=='record-interpretation': heads['alternative']=key
        elif kind=='apply-selected-merge': heads['main']=key
    add('open-episode',dict(title='Initial complete argument',question='Which conditions change the claimed result?'))
    metric=dict(name='Synthetic response count',definition='Recorded synthetic counts for capacity checks, not a real measurement.',unit='count',comparison='Same-condition baseline')
    for i in range(counts):
        add('record-experiment',dict(id='run-%s'%i,question='Does condition %s change the measured score?'%i,
            method='Synthetic comparison; no real artifact was executed.', conditions='Condition %s on synthetic model M'%i,
            metric=metric, source_ref='synthetic/results-%s.json'%i))
        key='event-%s'%i;last_events[i]=key
        add('record-evidence-event',dict(event_id=key,target_id='observation-%s'%i,run_id='run-%s'%i,
            action='confirm',statement='Under condition %s the held-out score changes relative to its own baseline. '%i+('Synthetic result registration preserves the measurement and scope. '*5),value=str(i),
            rationale='Synthetic recorded value; researcher must check any actual source independently. '*3,supersedes_id=None))
    if corrections:
        for i in range(768):
            target=i%counts;key='correction-%s'%i
            add('record-evidence-event',dict(event_id=key,target_id='observation-%s'%target,run_id='run-%s'%target,
                action='correct',statement='Synthetic corrected value under the same condition and measurement.',value=str(i+1),rationale='Appended synthetic correction; all earlier measured values remain inspectable.',supersedes_id=last_events[target]));last_events[target]=key
    for ep in range(episodes):
        if ep: add('open-episode',dict(title='Judgment round %s'%ep,question='What should this round retain?'),'episode-%s'%ep)
        add('create-reasoning-branch',{})
        text='Synthetic round %s keeps condition-specific evidence and limitations distinct.'%ep
        judgment=dict(project_id='capacity-paper',episode_id=current,text=text,rationale='Synthetic human reasoning for this round.',history=[dict(contributor='human',text=text,rationale='Synthetic human reasoning for this round.',proposal_id=None,trace_digest=None,parent_digest=None)])
        changes=[dict(id='reading-%s'%ep,kind='interpretation',body=dict(statement=text,observation_ids=['observation-0']))]
        if ep==0:
            changes += [dict(id='claim-%s'%i,kind='claim',body=dict(role='main',statement='Condition %s changes the synthetic outcome relative to its defined baseline.'%i,scope='Synthetic condition %s, no generalization claimed.'%i,parent_ids=['thesis'])) for i in range(claims)]
            changes += [dict(id='edge-%s'%i,kind='scientific-edge',body=dict(edge_type=['supports','qualifies'][i%2],source_id='observation-%s'%(i%counts),target_id='claim-%s'%(i%claims),rationale='Only the stated measurement and condition support this synthetic relation.')) for i in range(edges)]
            changes += [dict(id='plan-%s'%i,kind='experiment-plan',body=dict(claim_id='claim-%s'%(i%claims),objective='Test held-out condition %s independently.'%i,status='planned',conditions='New synthetic condition %s, not measured.'%i,metric=metric)) for i in range(plans)]
        add('record-interpretation',dict(changes=changes,judgment=judgment))
        add('apply-selected-merge',dict(selected_ids=[x['id'] for x in changes],judgment=judgment,disposition='not-required',answers=[]))
        if ep!=episodes-1:add('close-episode',{})
    return seed,tuple(commands)

if __name__=='__main__':
    seed,commands=combined()
    began=time.monotonic(); h=ResearchHistory(seed,commands);elapsed=time.monotonic()-began
    print(json.dumps(dict(replay_seconds=elapsed,commands=len(commands),input_bytes=len(seed)+sum(map(len,commands)),manifest_bytes=len(h.manifest()),rss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,capacity=h.capacity())))
