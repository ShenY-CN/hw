# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-6，OpenAI；GPT-6 模型家族发布日期 2026-09-03）。
# 参赛队须自行理解、复核与改写；本会话未提供更细的子型号标识。
from common import *
from functools import lru_cache
from collections import Counter,defaultdict

def peak(intervals):
    events=sorted([(a,1) for a,b in intervals]+[(b,-1) for a,b in intervals])
    count=maximum=0
    for _,d in events:count+=d;maximum=max(maximum,count)
    return maximum

def partition(m,data):
    rs=data['routes'];rel=data['relays'];com=data['communication']
    parent=list(range(16))
    def find(x):
        while parent[x]!=x:x=parent[x]
        return x
    for r in rs:
        for n in r['order'][1:]:parent[find(n)]=find(r['order'][0])
    components=defaultdict(list)
    for n in range(1,16):components[find(n)].append(n)
    components=list(components.values());nc=len(components)
    print('partition components',components,flush=True)
    inventory=[4,2,2,6,4,4,2,6]
    @lru_cache(None)
    def group(mask):
        nodes=[n for j,ns in enumerate(components) if mask>>j&1 for n in ns]
        tasks=[r for r in rs if r['order'][0] in nodes];tids={r['id'] for r in tasks}
        relay_ids={c['relay_task'] for c in com if c['route'] in tids and c['relay_task']}
        rts=[r for r in rel if r['id'] in relay_ids]
        resources=[]
        for g in m.types:resources.append(peak([(r['start'],r['end']) for r in tasks if r['g']==g]))
        for g in m.types:resources.append(peak([(r['start'],r['end']+charge(r['soc'],m.types[g]['charge'])) for r in tasks if r['g']==g]))
        resources.append(peak([(r['start'],r['end']+300) for r in rts]))
        resources.append(peak([(r['start'],r['end']+charge(r['soc'],1800)) for r in rts]))
        return dict(nodes=nodes,resources=resources,work=sum(r['duration'] for r in tasks),boxes=sum(len(r['boxes']) for r in tasks),transport_ids=sorted(tids),relay_ids=sorted(relay_ids))
    allmask=(1<<nc)-1;answer={}
    for K in [2,3]:
        best=None;balanced=None;count=0;pareto={}
        def visit(j,masks):
            nonlocal best,balanced,count
            if j==nc:
                if len(masks)!=K:return
                count+=1;gs=[group(k) for k in masks];total=np.sum([g['resources'] for g in gs],axis=0).astype(int).tolist()
                deficit=[max(0,t-i) for t,i in zip(total,inventory)]
                workloads=[g['work'] for g in gs];cv=float(np.std(workloads)/np.mean(workloads))
                score=(sum(deficit),sum(total),cv)
                rec=dict(K=K,groups=gs,total=total,deficit=deficit,unused=[max(0,i-t) for t,i in zip(total,inventory)],cv=cv,score=score)
                if best is None or score<tuple(best['score']):best=rec
                bal=(sum(deficit),cv,sum(total))
                if balanced is None or bal<(sum(balanced['deficit']),balanced['cv'],sum(balanced['total'])):balanced=rec
                key=(sum(deficit),sum(total))
                if key not in pareto or cv<pareto[key]['cv']:pareto[key]=rec
                return
            for i in range(len(masks)):
                mm=masks.copy();mm[i]|=1<<j;visit(j+1,mm)
            if len(masks)<K:visit(j+1,masks+[1<<j])
        visit(0,[])
        if best is None:raise RuntimeError('Too few indivisible components for requested groups')
        answer[str(K)]=dict(selected=best,balanced=balanced,evaluated=count,frontier=list(pareto.values()))
        print('Q4',K,'evaluated',count,'resources',best['total'],'deficit',best['deficit'],'cv',best['cv'],flush=True)
    save('q4.json',dict(components=components,inventory=inventory,schemes=answer))

def validate(m,data,q):
    errors=[];routes=data['routes'];cover=Counter(b for r in routes for b in r['boxes'])
    if cover!=Counter(range(80)):errors.append('box coverage')
    hard=[];soc=[];occupy=defaultdict(list);bat=defaultdict(list)
    for r in routes:
        fresh=m.route(r['g'],r['boxes'],r['order'])
        if fresh is None:errors.append(r['id']+' physical infeasible');continue
        if abs(fresh['energy']-r['energy'])>1e-8:errors.append(r['id']+' energy mismatch')
        if abs(r['end']-r['start']-fresh['duration'])>1e-6:errors.append(r['id']+' duration mismatch')
        saved_deliver={int(b):t for b,t in r['deliver'].items()}
        if saved_deliver.keys()!=fresh['deliver'].keys() or any(abs(saved_deliver[b]-t)>1e-6 for b,t in fresh['deliver'].items()):
            errors.append(r['id']+' delivery mismatch')
        if abs(r['soc']-fresh['soc'])>1e-8:errors.append(r['id']+' SOC mismatch')
        for b,t in fresh['deliver'].items():
            slack=m.boxes[b]['deadline']-r['start']-t
            if slack< -1e-7:errors.append(m.boxes[b]['id']+' deadline')
            if m.boxes[b]['deadline']<1e8:hard.append(slack)
        soc.append(r['soc']);occupy[r['unit']].append((r['start'],r['end']))
        bat[r['battery']].append((r['start'],r['end']+charge(r['soc'],m.types[r['g']]['charge'])))
    for id,ints in list(occupy.items())+list(bat.items()):
        if peak(ints)>1:errors.append(id+' overlaps')
    checks=dict(boxes=80,min_hard_slack=min(hard),min_transport_SOC=min(soc),machines_used=len(occupy),batteries_used=len(bat),max_machine_overlap=max(peak(v) for v in occupy.values()),max_battery_overlap=max(peak(v) for v in bat.values()))
    if q==3:
        gw=[m.nodes[0]['lon'],m.nodes[0]['lat'],m.nodes[0]['z']+20]
        rt={r['id']:r for r in data['relays']}
        relay_units=defaultdict(list);relay_components=defaultdict(list)
        for r in data['relays']:
            if r['energy']>2.56+1e-8:errors.append(r['id']+' SOC')
            if abs(r['soc']-(1-r['energy']/3.2))>1e-8:errors.append(r['id']+' SOC mismatch')
            if r['pos'][2]-float(m.ground(*r['pos'][:2]))>300+1e-7:errors.append(r['id']+' altitude')
            if m.link_margin(r['pos'],gw,126)<0:errors.append(r['id']+' backhaul')
            relay_units[r['unit']].append((r['start'],r['end']+300))
            relay_components[r['component']].append((r['start'],r['end']+charge(r['soc'],1800)))
        if len(relay_units)>2:errors.append('relay unit inventory')
        if len(relay_components)>6:errors.append('relay component inventory')
        for id,ints in list(relay_units.items())+list(relay_components.items()):
            if peak(ints)>1:errors.append(id+' overlaps')
        for r in routes:
            intervals=sorted([c for c in data['communication'] if c['route']==r['id']],key=lambda c:c['start'])
            cursor=r['start']+r['takeoff']
            for c in intervals:
                if abs(cursor-c['start'])>1e-6:errors.append(r['id']+' coverage gap')
                cursor=c['end']
                if c['relay_task']:
                    rr=rt[c['relay_task']]
                    if c['start']<rr['ready']-1e-6 or c['end']>rr['service_end']+1e-6:errors.append(r['id']+' relay timing')
            if abs(cursor-r['end'])>1e-6:errors.append(r['id']+' end coverage')
        checks.update(communication_intervals=len(data['communication']),min_comm_margin=min(c['margin'] for c in data['communication']),min_relay_SOC=min(r['soc'] for r in data['relays']))
    return dict(pass_=not errors,errors=errors,checks=checks)

if __name__=='__main__':
    m=Model();out={}
    for q in [2,3]:
        d=json.loads((RESULT/f'q{q}.json').read_text(encoding='utf8'));out[str(q)]=validate(m,d,q)
        if q==3:partition(m,d)
    save('validation.json',out);print(out,flush=True)
