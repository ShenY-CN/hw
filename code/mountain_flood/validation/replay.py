# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-5，OpenAI；GPT-5 发布于 2025-08-07）。
# 参赛队须自行理解、复核与改写；本会话未提供更细的子型号标识。
"""独立回算路线方案，检查物理量、交付时限、资源占用和通信约束。"""

from collections import Counter, defaultdict

from mountain_flood.core.domain import charge
from mountain_flood.validation.resources import peak

def validate(m,data,q):
    errors=[];routes=data['routes'];cover=Counter(b for r in routes for b in r['boxes'])
    if cover!=Counter(range(80)):errors.append('box coverage')
    hard=[];medical_slacks=[];first_slacks=[];due_slacks=[];soft_late=[];soc=[];occupy=defaultdict(list);bat=defaultdict(list)
    for r in routes:
        for b in r['boxes']:
            if m.boxes[b]['node'] not in r['order']:
                errors.append(m.boxes[b]['id']+' wrong delivery service area')
        fresh=m.route(r['g'],r['boxes'],r['order'])
        if fresh is None:errors.append(r['id']+' physical infeasible');continue
        if abs(fresh['energy']-r['energy'])>1e-8:errors.append(r['id']+' energy mismatch')
        if abs(r['end']-r['start']-fresh['duration'])>1e-6:errors.append(r['id']+' duration mismatch')
        saved_deliver={int(b):t for b,t in r['deliver'].items()}
        if saved_deliver.keys()!=fresh['deliver'].keys() or any(abs(saved_deliver[b]-t)>1e-6 for b,t in fresh['deliver'].items()):
            errors.append(r['id']+' delivery mismatch')
        if abs(r['soc']-fresh['soc'])>1e-8:errors.append(r['id']+' SOC mismatch')
        for b,t in fresh['deliver'].items():
            box=m.boxes[b];arrival=r['start']+t
            slack=box['deadline']-arrival
            if slack< -1e-7:errors.append(m.boxes[b]['id']+' deadline')
            if box['deadline']<1e8:hard.append(slack)
            if box['medical']:medical_slacks.append(box['due']-arrival)
            if box['first']:first_slacks.append(box['first_deadline']-arrival)
            due_slack=box['due']-arrival
            due_slacks.append(due_slack)
            if not box['medical'] and due_slack< -1e-7:
                soft_late.append(dict(box=box['id'],kind=box['kind'],delay_s=-due_slack,priority=box['priority']))
        soc.append(r['soc']);occupy[r['unit']].append((r['start'],r['end']))
        bat[r['battery']].append((r['start'],r['end']+charge(r['soc'],m.types[r['g']]['charge'])))
    for id,ints in list(occupy.items())+list(bat.items()):
        if peak(ints)>1:errors.append(id+' overlaps')
    checks=dict(boxes=80,hard_boxes=len(hard),medical_boxes=len(medical_slacks),first_boxes=len(first_slacks),min_hard_slack=min(hard),min_medical_slack=min(medical_slacks),min_first_slack=min(first_slacks),min_due_slack=min(due_slacks),late_boxes=len(soft_late),soft_late_boxes=soft_late,weighted_soft_tardiness_s=sum(x['priority']*x['delay_s'] for x in soft_late),min_transport_SOC=min(soc),machines_used=len(occupy),batteries_used=len(bat),max_machine_overlap=max(peak(v) for v in occupy.values()),max_battery_overlap=max(peak(v) for v in bat.values()))
    if q==3:
        from mountain_flood.problem3.communication import relay_flight
        gw=[m.nodes[0]['lon'],m.nodes[0]['lat'],m.nodes[0]['z']+m.comm['gateway_height_m']]
        rt={r['id']:r for r in data['relays']}
        relay_units=defaultdict(list);relay_components=defaultdict(list)
        for r in data['relays']:
            physical=relay_flight(m,*r['pos'])
            if abs(r['ready']-r['start']-physical['ready'])>1e-6:errors.append(r['id']+' ready mismatch')
            if abs(r['end']-r['service_end']-physical['ret'])>1e-6:errors.append(r['id']+' return mismatch')
            expected_energy=physical['fly_energy']+(r['service_end']-r['ready']+m.relay['link_setup'])*(m.relay['hover_power']+m.relay['comm_power'])/3600
            if abs(r['energy']-expected_energy)>1e-6:errors.append(r['id']+' energy mismatch')
            if r['service_end']<r['ready']-1e-7:errors.append(r['id']+' negative service')
            if r['energy']>(1-m.relay['rho']/100)*m.relay['E']+1e-8:errors.append(r['id']+' SOC')
            if abs(r['soc']-(1-r['energy']/m.relay['E']))>1e-8:errors.append(r['id']+' SOC mismatch')
            if r['pos'][2]-float(m.ground(*r['pos'][:2]))>m.relay['max_agl']+1e-7:errors.append(r['id']+' altitude')
            if m.link_margin(r['pos'],gw,m.comm['thresholds_db']['backhaul'])<0:errors.append(r['id']+' backhaul')
            relay_units[r['unit']].append((r['start'],r['end']+m.relay['turnaround']))
            relay_components[r['component']].append((r['start'],r['end']+charge(r['soc'],m.relay['charge'])))
        if len(relay_units)>len(m.relay['units']):errors.append('relay unit inventory')
        if len(relay_components)>m.relay['components']:errors.append('relay component inventory')
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
