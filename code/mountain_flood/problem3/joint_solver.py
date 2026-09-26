# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-5，OpenAI；GPT-5 发布于 2025-08-07）。
# 参赛队须自行理解、复核与改写；本会话未提供更细的子型号标识。
"""从问题二路线构造问题三候选，并搜索中继站点和协同排程。"""

# 支持直接运行本文件；此处将 code/ 加入模块搜索路径。
if __package__ in (None, ""):
    import sys
    from pathlib import Path as _BootstrapPath
    sys.path.insert(0, str(_BootstrapPath(__file__).resolve().parents[2]))
from mountain_flood.core.domain import *
from itertools import product
from mountain_flood.problem2.transport import improve_schedule, metrics
from mountain_flood.problem3.communication import gateway, relay_flight, sample_segments, select_relays, certify_routes
from mountain_flood.problem3.schedule import solve as schedule_with_relays
from mountain_flood.validation.replay import validate
from mountain_flood.core.parameters import optimization_parameters


def components(routes):
    parent=list(range(16))
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]]
            x=parent[x]
        return x
    for r in routes:
        for n in r['order'][1:]:
            parent[find(n)]=find(r['order'][0])
    groups={}
    for n in range(1,16):groups.setdefault(find(n),[]).append(n)
    return list(groups.values())


def split_for_partitions(m,routes):
    existing=components(routes)
    if len(existing)>=3:
        return [dict(r) for r in routes],dict(split_route=None,extra_energy=0.,components=existing)
    candidates=[]
    for index,r in enumerate(routes):
        if len(r['order'])<2:continue
        pieces=[]
        for k,node in enumerate(r['order']):
            ids=[b for b in r['boxes'] if m.boxes[b]['node']==node]
            piece=m.route(r['g'],ids,[node])
            if piece is None:break
            piece.update(id=r['id']+chr(ord('a')+k),start=0.,end=piece['duration'])
            pieces.append(piece)
        if len(pieces)!=len(r['order']):continue
        trial=routes[:index]+routes[index+1:]+pieces
        if len(components(trial))<3:continue
        extra=sum(p['energy'] for p in pieces)-r['energy']
        candidates.append((extra,len(pieces)-1,index,pieces))
    if not candidates:raise RuntimeError('No route split permits three independent groups')
    extra,_,index,pieces=min(candidates,key=lambda x:(x[0],x[1]))
    out=[dict(r) for j,r in enumerate(routes) if j!=index]+pieces
    return out,dict(split_route=routes[index]['id'],extra_energy=extra,components=components(out))


def northern_sites(m,routes,west,east,limit=4):
    pts,_=sample_segments(routes,200);gw=gateway(m)
    direct=m.comm['thresholds_db']['direct'];access=m.comm['thresholds_db']['access'];backhaul=m.comm['thresholds_db']['backhaul']
    search=optimization_parameters()['relay_site_search']
    missed=[p for p in pts if m.link_margin(p,gw,direct)<search['direct_gap_threshold_db'] and
            m.link_margin(p,west['pos'],access)<search['required_margin_db'] and m.link_margin(p,east['pos'],access)<search['required_margin_db']]
    options=[]
    grid=search['grid_m']
    for x in np.arange(search['x_min_m'],search['x_stop_m'],grid):
        for y in np.arange(search['y_min_m'],search['y_stop_m'],grid):
            lon,lat=m.lonlat(float(x),float(y))
            if not (m.raster.bounds.left<=lon<=m.raster.bounds.right and m.raster.bounds.bottom<=lat<=m.raster.bounds.top):continue
            pos=[lon,lat,float(m.ground(lon,lat))+m.relay['max_agl']]
            if m.link_margin(pos,gw,backhaul)<search['required_margin_db']:continue
            covered=sum(m.link_margin(p,pos,access)>=search['required_margin_db'] for p in missed)
            if covered==len(missed):
                options.append(dict(x=float(x),y=float(y),pos=pos,**relay_flight(m,*pos)))
    if not options:raise RuntimeError('No northern site covers remaining sampled gaps')
    options.sort(key=lambda v:(v['fly_energy'],v['x'],v['y']))
    return options[:limit],len(missed)


def relay_plan(m,sites,west_end,east_end,north_end,late_end=None):
    if late_end is None:late_end=optimization_parameters()['q3_schedule_horizon_s']
    missions=[]
    def add(site,unit,start,end,code,component):
        v=sites[site];ready=start+v['ready']
        energy=v['fly_energy']+(end-ready+m.relay['link_setup'])*(m.relay['hover_power']+m.relay['comm_power'])/3600
        if end<=ready or energy>(1-m.relay['rho']/100)*m.relay['E']+1e-8:return False
        missions.append(dict(id=code,unit=unit,component=component,site=['W','E','N'][site],pos=v['pos'],
                             start=start,ready=ready,service_end=end,end=end+v['ret'],energy=energy,soc=1-energy/m.relay['E']))
        return True
    if not add(0,'R01',0,west_end,'RP01','RB01'):return None
    if not add(1,'R02',0,east_end,'RP02','RB02'):return None
    if not add(2,'R02',missions[1]['end']+m.relay['turnaround'],north_end,'RP03','RB03'):return None
    if not add(0,'R01',missions[0]['end']+m.relay['turnaround'],late_end,'RP04','RB04'):return None
    if not add(1,'R02',missions[2]['end']+m.relay['turnaround'],late_end,'RP05','RB05'):return None
    return missions


def score(data):
    s=data['summary']
    return (round(s['weighted_tardiness'],6),s['makespan'],s['energy'],s['count']+s['relay_count'])


def finish_candidate(m,data,sites,west_end,east_end,north_end):
    final_end=max(r['end'] for r in data['routes'])+30
    relays=relay_plan(m,sites,west_end,east_end,north_end,late_end=final_end)
    if relays is None:return None
    records,fails=certify_routes(m,data['routes'],relays,verbose=False)
    if fails:return None
    data['relays']=relays;data['communication']=records
    s=data['summary'];s['relay_energy']=sum(r['energy'] for r in relays)
    s['energy']=s['transport_energy']+s['relay_energy']
    s['makespan']=max(s['transport_makespan'],max(r['end'] for r in relays))
    s['comm_intervals']=len(records);s['comm_min_margin']=min(r['margin'] for r in records)
    if not validate(m,data,3)['pass_']:return None
    return data

def direct_relief_candidates(m,routes,data):
    """针对每个软时限迟到货箱尝试单独直送，同时保留该架次的其他货物。"""
    candidates=[]
    source={r['id']:r for r in routes}
    next_id=f'T{len(routes)+1:03}'
    for scheduled in data['routes']:
        r=source[scheduled['id']]
        for b,t in scheduled['deliver'].items():
            b=int(b)
            if scheduled['start']+t<=m.boxes[b]['due']+1e-7:continue
            kept=[x for x in r['boxes'] if x!=b]
            if not kept:continue
            order=[n for n in r['order'] if any(m.boxes[x]['node']==n for x in kept)]
            remainder=m.route(r['g'],kept,order)
            if remainder is None:continue
            remainder.update(id=next_id,start=0.,end=remainder['duration'])
            for g in m.types:
                direct=m.route(g,[b],[m.boxes[b]['node']])
                if direct is None:continue
                direct.update(id=r['id'],start=0.,end=direct['duration'])
                trial=[dict(x) for x in routes if x['id']!=r['id']]+[direct,dict(remainder)]
                candidates.append((m.boxes[b]['id'],g,trial))
    return candidates


def run():
    m=Model()
    q2=json.loads((RESULT/'q2.json').read_text(encoding='utf8'))
    rs,split=split_for_partitions(m,q2['routes'])
    rs,transport_solver=improve_schedule(m,rs,seconds=15)
    transport=dict(routes=rs,summary=metrics(m,rs),solver=transport_solver,**split)
    save('q3_transport.json',transport)
    west,east=select_relays(m,rs)
    norths,missed=northern_sites(m,rs,west,east)
    best=None;tried=[]
    for north,west_end,east_end,north_end in product(norths,[7800,8100],[1931,2100,2500,3400,3665],[7600,7900]):
        relays=relay_plan(m,[west,east,north],west_end,east_end,north_end)
        if relays is None:continue
        data=schedule_with_relays(m,rs,relays,seconds=3)
        if data is not None:
            data=finish_candidate(m,data,[west,east,north],west_end,east_end,north_end)
        rec=dict(north=[north['x'],north['y']],west_end=west_end,east_end=east_end,north_end=north_end,
                 feasible=data is not None)
        if data is not None:
            rec['score']=score(data)
            if best is None or score(data)<score(best[0]):
                best=(data,north,west_end,east_end,north_end)
        tried.append(rec)
        print('Q3 candidate',len(tried),rec,flush=True)
    if best is None:raise RuntimeError('No fully certified joint candidate')
    data,north,west_end,east_end,north_end=best
    relays=relay_plan(m,[west,east,north],west_end,east_end,north_end)
    refined=schedule_with_relays(m,rs,relays,seconds=20)
    if refined is not None:
        refined=finish_candidate(m,refined,[west,east,north],west_end,east_end,north_end)
    if refined is not None and score(refined)<score(data):data=refined
    adjustments=[]
    for box_id,g,trial in direct_relief_candidates(m,rs,data):
        candidate=schedule_with_relays(m,trial,relays,seconds=12)
        if candidate is not None:
            candidate=finish_candidate(m,candidate,[west,east,north],west_end,east_end,north_end)
        rec=dict(box=box_id,type=g,feasible=candidate is not None)
        if candidate is not None:
            rec['score']=score(candidate)
            if score(candidate)<score(data):
                data=candidate
                data['route_adjustment']=dict(kind='direct_relief',box=box_id,type=g)
        adjustments.append(rec)
    check=validate(m,data,3)
    if not check['pass_']:raise RuntimeError(f'Q3 failed validation: {check["errors"]}')
    save('q3_transport_delayed.json',dict(routes=data['routes'],summary=metrics(m,data['routes']),solver=data['solver']))
    save('relay_search.json',dict(selected=[west,east],northern_candidates=norths,missed_points=missed,
                                  search=tried,route_adjustments=adjustments,chosen_north=[north['x'],north['y']]))
    save('comm_failed.json',[])
    save('q3.json',data)
    print('Q3 selected',score(data),data['summary'],flush=True)


if __name__=='__main__':run()
