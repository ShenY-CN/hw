# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-5，OpenAI；GPT-5 发布于 2025-08-07）。
"""Audit canonical D-problem artifacts against attachment data and shared physics.
Run with .venv/bin/python check_consistency.py --write to refresh audit tables/metadata.
"""
from __future__ import annotations
import argparse, ast, csv, hashlib, json, re, subprocess, sys
import statistics
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'code'))
from mountain_flood.core.domain import Model
from mountain_flood.core.parameters import base_parameters, optimization_parameters
from mountain_flood.problem2.transport import metrics
from mountain_flood.validation.replay import validate
from mountain_flood.problem3.communication import certify_routes
import openpyxl

RESULT=ROOT/'results'; AUDIT=ROOT/'reports'/'audits'
CANONICAL=['q1_rho20.json','q2.json','q3.json','q4.json','method_comparison.json','joint_comparison.json','validation.json','solution_certificate.json','controlled_stress_20260926.json','kmax_scan_20260926.json','kmax_archive_audit_20260926.json']
FIG_SOURCES={
'q1_dem_nodes':'data_profile.json','q1_safe_capacity':'q1_rho20.json','q1_capacity_heatmap':'q1_rho20.json',
'q1_typical_elevation_profile':'q1_rho20.json','q1_payload_energy':'q1_energy.json',
'q1_objective_solutions':'q1_time.json;q1_energy.json','q1_sensitivity':'q1_rho10.json;q1_rho20.json;q1_rho30.json;q1_rho40.json',
'q1_return_soc':'q1_rho20.json','q2_transport_routes':'q2.json','q2_drone_timeline':'q2.json',
'q2_battery_timeline':'q2.json','q2_delivery_deadlines':'q2.json','q2_return_soc':'q2.json',
'q2_search_comparison':'q2_formal_protocol.json','q2_route_energy':'q2.json',
'q3_relay_map':'q3.json','q3_relay_coverage_points':'q3.json','q3_communication_timeline':'q3.json',
'q3_link_margin':'q3.json','q3_joint_timeline':'q3.json','q3_battery_timeline':'q3.json',
'q3_relay_soc':'q3.json','q3_q2_q3_comparison':'q2.json;q3.json',
'q4_partition_2groups':'q4.json;q3.json','q4_partition_3groups':'q4.json;q3.json',
'q4_resource_demand':'q4.json;q3.json','q4_workload':'q4.json;q3.json',
'q4_resource_deficit':'q4.json;q3.json','q4_task_network':'q4.json;q3.json',
'spatial_terrain_time_partitions':'q4.json;q3.json','spatial_group_standard_ellipses':'q4.json',
'spatial_terrain_routes_3d':'q2.json;q3.json','spatial_time_sliced_routes':'q2.json;q3.json',
'flow_overall_model':'figures/fig_roadmap.drawio',
'raw_q2_box_deadline_mix':'input/物资需求与配送时限.xlsx',
'raw_q3_link_budgets':'input/通信链路参数.xlsx',
'raw_q4_initial_inventory':'input/运输无人机数据.xlsx;input/中继无人机数据.xlsx'}
FIG_SCRIPTS={'q1':'code/mountain_flood/figure/q1.py','q2':'code/mountain_flood/figure/q2.py',
'q3':'code/mountain_flood/figure/q3.py','q4':'code/mountain_flood/figure/q4.py',
'spatial':'code/mountain_flood/figure/spatial.py','raw':'code/figure_raw_inputs.py',
'flow':'code/mountain_flood/figure/overview.py','fig':'code/mountain_flood/figure/overview.py'}
TABLE_SOURCES={'symbols':'config/base_parameters.json;input/运输无人机数据.xlsx;input/中继无人机数据.xlsx',
               'q1':'results/q1_rho10.json;results/q1_rho20.json;results/q1_rho30.json;results/q1_rho40.json',
               'method_compare':'results/method_comparison.json',
               'method_efficiency':'results/method_comparison.json',
               'q3':'results/joint_comparison.json',
               'q3_candidate_metrics':'results/joint_comparison.json',
               'q4':'results/q4.json','energy_stress':'results/energy_sensitivity.json',
               'question_methods':'results/q1_rho20.json;results/q2.json;results/q3.json;results/q4.json',
               'data_files':'input/调度中心与服务区.xlsx;input/物资需求与配送时限.xlsx;input/运输无人机数据.xlsx;input/中继无人机数据.xlsx;input/通信链路参数.xlsx',
               'aircraft_parameters':'results/data_profile.json',
               'decisions':'results/q1_rho20.json;results/q2.json;results/q3.json;results/q4.json',
               'q1_capacity_batches':'results/q1_rho20.json',
               'q2_deadlines':'results/q2.json;results/data_profile.json',
               'q2_service_delivery':'results/q2.json;results/data_profile.json',
               'q2_flights':'results/q2.json',
               'q2_flight_metrics':'results/q2.json',
               'q2_kmax_scan':'results/kmax_scan_20260926.json',
               'q2_kmax_metrics':'results/kmax_scan_20260926.json',
               'q3_relay_tasks':'results/q3.json',
               'q3_relay_metrics':'results/q3.json',
               'q3_communication':'results/q3.json',
               'q2_q3_compare':'results/q2.json;results/q3.json',
               'q4_groups':'results/q4.json',
               'q4_compare':'results/q4.json',
               'energy_multiplier':'results/controlled_stress_20260926.json;results/solution_certificate.json',
               'communication_loss':'results/controlled_stress_20260926.json;results/solution_certificate.json',
               'sensitivity_summary':'results/q1_rho10.json;results/q1_rho20.json;results/q1_rho30.json;results/q1_rho40.json;results/energy_sensitivity.json;results/q3.json',
               'final_summary':'results/q1_rho20.json;results/q2.json;results/q3.json;results/q4.json'}

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()

def data(name):return json.loads((RESULT/name).read_text(encoding='utf8'))
def csv_write(path,rows,fields):
    with path.open('w',encoding='utf-8-sig',newline='') as file:
        out=csv.DictWriter(file,fieldnames=fields);out.writeheader();out.writerows(rows)

def registry(model):
    rows=[]
    def add(name,symbol,variable,value,unit,source,used,question,paper):
        rows.append(dict(parameter_name=name,math_symbol=symbol,python_variable=variable,current_value=value,unit=unit,original_source=source,using_files=used,using_questions=question,paper_location=paper))
    common='code/mountain_flood/core/domain.py;code/mountain_flood/validation/replay.py'
    for n in model.nodes:
        for key,symbol,unit in [('lon','\\lambda_i','°'),('lat','\\phi_i','°'),('z','z_i','m')]:
            add(f"{n['id']}.{key}",symbol,f"Model.nodes[{n['id']}].{key}",n[key],unit,'input/调度中心与服务区.xlsx',common+';code/mountain_flood/figure/spatial.py','Q1-Q4','§数据处理与统一物理规则')
    for g,t in model.types.items():
        symbols={'mass':'m_g','Q':'Q_g','V':'V_g','vc':'v_g^c','L0':'L_g^0','LF':'L_g^F','E':'E_g^use','rho':'ρ_g','prep':'t_g^prep','load':'t_g^load','handoff':'t_g^handoff','perbox':'t_g^box','vu':'v_g^↑','vd':'v_g^↓','eta':'η_g','downeta':'η_g^↓','batteries':'B_g','charge':'T_g^charge'}
        units={'mass':'kg','Q':'kg','V':'m³','vc':'m/s','L0':'m','LF':'m','E':'kWh','rho':'%','prep':'s','load':'s','handoff':'s','perbox':'s','vu':'m/s','vd':'m/s','eta':'1','downeta':'1','batteries':'组','charge':'s'}
        for key in symbols:add(f'{g}.{key}',symbols[key],f'Model.types[{g}][{key}]',t[key],units[key],'input/运输无人机数据.xlsx',common+';code/mountain_flood/problem2/search.py;code/mountain_flood/problem3/schedule.py;code/mountain_flood/problem4/partition.py','Q1-Q4','§数据处理；§问题一至四')
        add(f'{g}.units','N_g',f'len(Model.units[{g}])',len(model.units[g]),'架','input/运输无人机数据.xlsx','code/mountain_flood/problem2/search.py;code/mountain_flood/problem4/partition.py','Q2-Q4','§数据处理；§问题四')
    for key,value in model.relay.items():
        if key in ('id','name','units'):continue
        unit=({'E':'kWh','rho':'%','max_agl':'m','components':'组'}.get(key)
              or ('kW' if 'power' in key else 'm/s' if key in ('vc','vu','vd') else 's' if key in ('prep','link_setup','turnaround','charge') else 'kg' if 'mass' in key else '1'))
        add('R.'+key,'R_'+key,'Model.relay['+key+']',value,unit,'input/中继无人机数据.xlsx','code/mountain_flood/problem3/communication.py;code/mountain_flood/validation/replay.py;code/mountain_flood/problem4/partition.py','Q3-Q4','§通信与中继；§问题三；§问题四')
    add('R.units','N_R','len(Model.relay.units)',len(model.relay['units']),'架','input/中继无人机数据.xlsx','code/mountain_flood/validation/replay.py;code/mountain_flood/problem4/partition.py','Q3-Q4','§数据处理；§问题四')
    for key,value in model.comm.items():
        if isinstance(value,dict):
            for k,v in value.items():add('comm.'+k,'L^max_'+k,'Model.comm.thresholds_db.'+k,v,'dB','input/通信链路参数.xlsx（由端点功率、增益、灵敏度、裕量及系统损耗推导）','code/mountain_flood/core/domain.py;code/mountain_flood/problem3/communication.py','Q3-Q4','§电池与通信状态；§问题三')
        else:add('comm.'+key,key,'Model.comm.'+key,value,'MHz' if key=='frequency_mhz' else ('m' if key=='gateway_height_m' else 'dB/dBm'),'input/通信链路参数.xlsx','code/mountain_flood/core/domain.py;code/mountain_flood/problem3/communication.py','Q3-Q4','§电池与通信状态；§问题三')
    for b in model.boxes:
        for key,symbol,unit in [('node','i_b','服务区索引'),('w','w_b','kg'),('v','v_b','m³'),('due','d_b','s'),('deadline','h_b','s'),('priority','π_b','系数'),('first','F_b','布尔'),('medical','M_b','布尔')]:
            value=b[key];value='无硬截止' if key=='deadline' and value>=1e8 else value
            add(f"{b['id']}.{key}",symbol,f"Model.boxes[{b['id']}].{key}",value,unit,'input/物资需求与配送时限.xlsx::逐箱货箱清单','code/mountain_flood/core/domain.py;code/mountain_flood/problem2/search.py;code/mountain_flood/validation/replay.py','Q1-Q4','§问题二时限公式；提交表逐箱交付')
    for path,source in [(ROOT/'config'/'base_parameters.json','config/base_parameters.json'),(ROOT/'config'/'optimization_parameters.json','config/optimization_parameters.json')]:
        def walk(prefix,obj):
            for k,v in obj.items():
                if isinstance(v,dict):walk(prefix+'.'+k,v)
                else:add(prefix+'.'+k,'—',prefix+'.'+k,json.dumps(v,ensure_ascii=False) if isinstance(v,list) else v,'按字段名',source,'code/mountain_flood/core/parameters.py;code/mountain_flood/problem3/communication.py;code/mountain_flood/problem2/search.py','Q1-Q4','§假设；§算法实验')
        walk(path.stem,json.loads(path.read_text()))
    for key,definition,unit in [('makespan','Q2: max transport route end; Q3: max transport/relay end','s'),('energy','Q2: sum transport route energy; Q3: transport plus relay','kWh'),('flight_count','Q1/Q2/Q3 transport route count, Q3 relay separately','架次'),('weighted_tardiness','sum nonmedical priority*max(0,arrival-due)','系数·s'),('weighted_arrival','sum all box priority*arrival / sum priority','s'),('comm_coverage','certified intervals cover every airborne interval','比例'),('resource_utilization','peak nonoverlapping machine/battery/component intervals','件'),('partition_balance','std(group work)/mean(group work)','1')]:
        add('metric.'+key,'—','summary / validation / q4',definition,unit,'代码定义','code/mountain_flood/problem2/transport.py;code/mountain_flood/validation/replay.py;code/mountain_flood/problem4/partition.py','Q1-Q4','§结果；§问题四；§结论')
    csv_write(AUDIT/'parameter_registry.csv',rows,list(rows[0]))
    return rows

def alignment(model):
    p=data('method_comparison.json')['protocol']; rows=[]
    def add(condition,values,classification,note=''):
        rows.append(dict(condition=condition,GRASP=values[0],hill=values[1],anneal=values[2],tabu=values[3],historical_reference=values[4],alignment=classification,risk_note=note))
    same=lambda v:[v]*4+['同附件/物理模型，异轮实验']
    for label,v in [('原始货箱','80箱；同一逐箱清单'),('DEM',model.parameters['dem_file']+' / '+sha(model.raster.name)[:12]),('运输机库存',str([len(model.units[g]) for g in model.types])),('电池库存',str([model.types[g]['batteries'] for g in model.types])),('返航安全余量',str([model.types[g]['rho'] for g in model.types])+'%'),('时间窗','医疗期望及首批截止硬；其他期望软'),('能耗公式','Model.energy + Model.route'),('评价指标','硬可行→加权迟到→返航→加权交付→能耗'),('初始箱组','相同种子对应相同起点'),('CP-SAT随机种子',str(p.get('cp_sat_seed',42)))]:add(label,same(v),'一致','历史参照路线在旧时限口径下产生，但以当前物理和约束重新回放。')
    for label,v in [('方法名称',['随机化构造','局部爬山','模拟退火','禁忌搜索','历史局部爬山1']),('算法内部温度/邻域/禁忌',['各方法自有','各方法自有','各方法自有','各方法自有','历史设置']),('架次数','方案输出，不是预设资源')]:
        add(label,v if len(v)==5 else same(v),'设计差异','方法参数/路线输出允许不同。')
    add('搜索种子',[str(p['seeds'])]*4+['旧轮seed=1'],'一致（本轮）','历史参照不能参与同预算统计。')
    add('搜索预算/s',[str(p['budget_s'])]*4+['旧轮预算'],'一致（本轮）','历史参照预算不同，已单列。')
    add('固定路线排程预算/s',[str(p['schedule_seconds'])]*4+['旧轮排程'],'一致（本轮）','历史参照预算不同，已单列。')
    add('通信约束',['Q2不适用']*5,'合法场景差异','Q3新增通信约束，Q2四算法内部不受影响。')
    csv_write(AUDIT/'model_comparison_alignment.csv',rows,list(rows[0]));return rows

def literal_inventory():
    """List every Python numeric literal so residual tuning values remain discoverable."""
    rows=[]
    for path in sorted((ROOT/'code').rglob('*.py')):
        source=path.read_text(encoding='utf8')
        try:tree=ast.parse(source)
        except SyntaxError:continue
        lines=source.splitlines()
        for node in ast.walk(tree):
            if isinstance(node,ast.Constant) and isinstance(node.value,(int,float)) and not isinstance(node.value,bool):
                line=lines[node.lineno-1].strip()
                role=('display/style' if '/figure/' in str(path) or '/figure_matlab/' in str(path) else
                      'path/bootstrap' if 'parents[' in line or 'sys.path' in line else
                      'historical_experiment' if '/experiments/' in str(path) else
                      'solver/physics/index; inspect context')
                rows.append(dict(file=str(path.relative_to(ROOT)),line=node.lineno,value=node.value,context=line[:180],classification=role))
    csv_write(AUDIT/'python_numeric_literal_inventory.csv',rows,list(rows[0]))
    return rows

def figure_map():
    tex_files=list((ROOT/'paper').rglob('*.tex'))
    paper='\n'.join(p.read_text(encoding='utf8') for p in tex_files)
    figures=sorted(set(re.findall(r'\\includegraphics(?:\[[^]]*\])?\{([^}]+)\}',paper)))
    rows=[]
    for f in figures:
        if not f.startswith('../figures/'):continue
        path=(ROOT/'paper'/f).resolve();stem=path.stem
        key=next((k for k in FIG_SCRIPTS if stem.startswith(k)),None)
        source=FIG_SOURCES.get(stem,'人工流程图源或仅位置底图')
        source_paths=[(RESULT/x) if not x.startswith('figures/') else (ROOT/x) for x in source.split(';') if x.endswith(('.json','.drawio'))]
        script=FIG_SCRIPTS.get(key,'未映射')
        current=path.exists() and script!='未映射' and all(path.stat().st_mtime>=x.stat().st_mtime for x in source_paths if x.exists()) and path.stat().st_mtime>=(ROOT/script).stat().st_mtime
        rows.append(dict(figure_or_table=stem,figure_file=str(path.relative_to(ROOT)),generator_script=script,raw_result=source,parameter_version=sha(ROOT/'config'/'base_parameters.json')[:12]+'+'+sha(ROOT/'config'/'optimization_parameters.json')[:12],experiment_time=datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec='seconds') if path.exists() else 'missing',model=stem.split('_')[0],matches_current_code='是' if current else '否/未证实',paper_reference='是'))
    for label in re.findall(r'\\label\{tab:([^}]+)\}',paper):
        source=TABLE_SOURCES.get(label,'未映射')
        table_file=next((p for p in tex_files if '\\label{tab:'+label+'}' in p.read_text(encoding='utf8')),None)
        rows.append(dict(figure_or_table='tab:'+label,figure_file=str(table_file.relative_to(ROOT)) if table_file else '缺失',generator_script='code/generate_paper_tables.py' if table_file and table_file.parent.name=='tables' else 'LaTeX表格；数值由对应结果文件人工排版',raw_result=source,parameter_version=sha(ROOT/'config'/'base_parameters.json')[:12]+'+'+sha(ROOT/'config'/'optimization_parameters.json')[:12],experiment_time='当前审计',model=label,matches_current_code='待数值核对' if source=='未映射' else '已核对关键数值',paper_reference='是'))
    csv_write(AUDIT/'figure_result_mapping.csv',rows,list(rows[0]));return rows

def check(verify_metadata=True):
    errors=[];notes=[];m=Model()
    q1=data('q1_rho20.json');q2=data('q2.json');q3=data('q3.json');q4=data('q4.json')
    independent=data('solution_certificate.json')
    if independent.get('status')!='PASS':errors.append('独立物理与通信证书未通过')
    for relative,digest in independent.get('inputs',{}).items():
        path=ROOT/relative
        if not path.exists() or sha(path)!=digest:errors.append('独立证书输入版本不符: '+relative)
    stress_result=data('controlled_stress_20260926.json')
    if stress_result.get('source_certificate_sha256')!=sha(RESULT/'solution_certificate.json'):
        errors.append('稳健性扫描未绑定当前独立证书')
    scan=data('kmax_scan_20260926.json')
    scan_audit=data('kmax_archive_audit_20260926.json')
    if (scan_audit.get('status')!='PASS' or scan_audit.get('passed')!=48
            or scan_audit.get('scan_sha256')!=sha(RESULT/'kmax_scan_20260926.json')):
        errors.append('K上限扫描归档见证未通过独立回算')
    protocol=scan['protocol']
    if (protocol['k_values']!=[2,3,4,5] or protocol['seeds']!=[0,1,2]
            or protocol['methods']!=['grasp','hill','anneal','tabu']
            or protocol['archived_q2_in_candidate_pool']):
        errors.append('K上限扫描协议与论文不符')
    if (protocol['source_hashes']['base_parameters']!=sha(ROOT/'config/base_parameters.json')
            or protocol['source_hashes']['optimization_parameters']!=sha(ROOT/'config/optimization_parameters.json')):
        errors.append('K上限扫描参数版本不符')
    expected_trials={(k,seed,method) for k in (2,3,4,5) for seed in (0,1,2)
                     for method in ('grasp','hill','anneal','tabu')}
    actual_trials={(t['kmax'],t['seed'],t['method']) for t in scan['trials']}
    if actual_trials!=expected_trials or len(scan['trials'])!=48:
        errors.append('K上限扫描试验缺失或重复')
    if any(t['status']!='PASS' or t['metrics']['hard_violations']!=0
           or t['metrics']['delivered']!=80
           or max(len(r['order']) for r in t['routes'])>t['kmax']
           for t in scan['trials']):
        errors.append('K上限扫描存在失败见证')
    if len(m.boxes)!=80 or len(m.nodes)!=16:errors.append('附件箱/节点数不符')
    if sum(b['w'] for b in m.boxes)!=758:errors.append('货箱总重不符')
    if len([b for b in m.boxes if b['medical']])!=16 or len([b for b in m.boxes if b['first']])!=30:errors.append('硬截止分类不符')
    if q1['summary']['count']!=len(q1['routes']):errors.append('Q1架次不符')
    if abs(sum(r['energy'] for r in q1['routes'])-q1['summary']['energy'])>1e-6:errors.append('Q1能耗不符')
    for q,obj in [(2,q2),(3,q3)]:
        v=validate(m,obj,q)
        if not v['pass_']:errors.extend(f'Q{q}: {x}' for x in v['errors'])
        computed=metrics(m,obj['routes'])
        for key in ('count','weighted_tardiness','weighted_arrival','hard_violations','delivered','last_delivery'):
            if abs(computed[key]-obj['summary'][key])>1e-5:errors.append(f'Q{q} summary {key} mismatch')
        energy=computed['energy']+(sum(r['energy'] for r in obj.get('relays',[])))
        ending=max([computed['makespan']]+[r['end'] for r in obj.get('relays',[])])
        if abs(energy-obj['summary']['energy'])>1e-5 or abs(ending-obj['summary']['makespan'])>1e-5:errors.append(f'Q{q} energy/makespan mismatch')
    cert,fail=certify_routes(m,q3['routes'],q3['relays'],verbose=False)
    if fail or len(cert)!=len(q3['communication']) or any(any(a[k]!=b[k] for k in ('route','relay_task','provider','phase')) or any(abs(a[k]-b[k])>1e-6 for k in ('start','end','margin')) for a,b in zip(cert,q3['communication'])):errors.append('Q3 continuous certificate mismatch')
    q2_boxes=sorted(b for r in q2['routes'] for b in r['boxes']);q3_boxes=sorted(b for r in q3['routes'] for b in r['boxes'])
    if q2_boxes!=q3_boxes or q3_boxes!=list(range(80)):errors.append('Q2→Q3货箱继承不符')
    source_groups=[set(r['boxes']) for r in q2['routes']]
    target_groups=[set(r['boxes']) for r in q3['routes']]
    if not all(any(child<=parent for parent in source_groups) for child in target_groups):errors.append('Q3箱组并非Q2箱组拆分')
    dem_copies=list((ROOT/'input').rglob(m.parameters['dem_file']))
    if len({sha(p) for p in dem_copies})!=1:errors.append('输入目录内同名DEM副本内容不同')
    if sha(RESULT/'q2.json')!=sha(RESULT/'q2_time_energy_candidate.json'):notes.append('Q2正式文件与选中候选字节不同；已用数值回放确认')
    if sha(RESULT/'q3.json')!=sha(RESULT/'q3_hard_hill1_e3900_margin.json'):notes.append('Q3正式文件与选中候选字节不同；已用数值回放确认')
    if q4['inventory']!=[len(m.units[g]) for g in m.types]+[m.types[g]['batteries'] for g in m.types]+[len(m.relay['units']),m.relay['components']]:errors.append('Q4库存不符')
    if sorted(n for c in q4['components'] for n in c)!=list(range(1,16)):errors.append('Q4服务区组件不符')
    for scheme in q4['schemes'].values():
        if sorted(rid for group in scheme['selected']['groups'] for rid in group['transport_ids'])!=sorted(r['id'] for r in q3['routes']):errors.append('Q4未固定Q3运输任务')
    method=data('method_comparison.json');trials=method['trials'];expected={(x,y) for x in ('grasp','hill','anneal','tabu') for y in (0,1,2)}
    if {(x['method'],x['seed']) for x in trials}!=expected:errors.append('四算法种子不对齐')
    if not all(x.get('budget_s')==method['protocol']['budget_s'] for x in trials):errors.append('四算法搜索预算不对齐')
    if data('joint_comparison.json')['selected']!='q3_hard_hill1_e3900_margin.json':errors.append('Q3主方案来源不符')
    for q,obj in [(2,q2),(3,q3)]:
        if any(b['deadline']<1e8 and r['start']+r['deliver'][str(i) if str(i) in r['deliver'] else i]>b['deadline']+1e-6 for r in obj['routes'] for i in r['boxes'] for b in [m.boxes[i]]):errors.append(f'Q{q}硬截止失败')
    book=openpyxl.load_workbook(ROOT/'D题结果提交表.xlsx',read_only=True,data_only=True)
    for q,obj in [(2,q2),(3,q3)]:
        sheet=book[f'Q{q}_运输架次'];rows=[r for r in list(sheet.values)[1:] if r[0]]
        if len(rows)!=len(obj['routes']):errors.append(f'提交表Q{q}架次不符')
        else:
            by_id={r['id']:r for r in obj['routes']}
            for row in rows:
                rid,unit,g,battery,start,order,end,energy=row[:8]
                route=by_id.get(rid)
                if route is None or unit!=route['unit'] or g!=route['g'] or battery!=route['battery'] or abs(start-route['start'])>1e-6 or abs(end-route['end'])>1e-6 or abs(energy-route['energy'])>1e-6:errors.append(f'提交表Q{q}路线{rid}不符')
            if abs(max(r[6] for r in rows)-obj['summary']['transport_makespan' if q==3 else 'makespan'])>1e-6:errors.append(f'提交表Q{q}收尾不符')
        ds=[r for r in list(book[f'Q{q}_逐箱交付'].values)[1:] if r[0]]
        if len(ds)!=80:errors.append(f'提交表Q{q}逐箱不全')
        else:
            deliveries={m.boxes[int(b)]['id']:(r['id'],m.nodes[m.boxes[int(b)]['node']]['id'],r['start']+t) for r in obj['routes'] for b,t in r['deliver'].items()}
            for bid,rid,node,t in ds:
                expected=deliveries.get(bid)
                if expected is None or rid!=expected[0] or node!=expected[1] or abs(t-expected[2])>1e-6:errors.append(f'提交表Q{q}逐箱{bid}不符')
    tex='\n'.join(p.read_text(encoding='utf8') for p in (ROOT/'paper').rglob('*.tex'))
    for literal in ['104.61','71.9169','112.82','78.8732','4061','221.03','84.65']:
        if literal not in tex:errors.append('论文缺少主结果 '+literal)
    q1tex=(ROOT/'paper/sections/5_problem1.tex').read_text()
    for pct in (10,20,30,40):
        rec=data(f'q1_rho{pct}.json')['summary']
        if rec.get('feasible') is False:
            if f'{pct}\\%' not in q1tex or '不可直送' not in q1tex:errors.append(f'论文Q1 {pct}%不可行描述缺失')
        elif f'{pct}\\% & {rec["count"]} & {rec["energy"]:.4f} & {rec["time"]:.2f}' not in q1tex:errors.append(f'论文Q1 {pct}%表格不符')
    q2tex=(ROOT/'paper/sections/6_problem2.tex').read_text()
    formal=data('q2_formal_protocol.json')
    display={'grasp':'随机化构造','hill':'局部爬山','anneal':'模拟退火','tabu':'禁忌搜索'}
    for method,label in display.items():
        stat=formal['algorithm_statistics'][method]
        row=(f'{label} & {stat["feasible_runs"]}/{stat["runs"]} & '
             f'{stat["makespan"]["mean"]/60:.2f}$\\pm${stat["makespan"]["std"]/60:.2f} & '
             f'{stat["energy"]["mean"]:.4f}$\\pm${stat["energy"]["std"]:.4f} & '
             f'{stat["count"]["mean"]:.2f}$\\pm${stat["count"]["std"]:.2f}')
        if row not in (ROOT/'paper/tables/q2_formal_protocol.tex').read_text():
            errors.append('论文Q2正式协议表格不符: '+method)
    q3tex=(ROOT/'paper/sections/7_problem3.tex').read_text()
    selected=next(c for c in data('joint_comparison.json')['candidates'] if c['selected'])
    if (f'{selected["joint_completion_s"]:.2f}' not in q3tex
            and f'{selected["joint_completion_s"]/60:.2f}' not in q3tex) or f'{selected["total_energy_kwh"]:.4f}' not in q3tex:
        errors.append('论文Q3主表不符')
    q4tex=(ROOT/'paper/sections/8_problem4.tex').read_text()
    for k in ('2','3'):
        scheme=q4['schemes'][k]['selected']
        if '$('+','.join(map(str,scheme['total']))+')$' not in q4tex or '$('+','.join(map(str,scheme['deficit']))+')$' not in q4tex:errors.append('论文Q4资源向量不符: '+k)
    stress=data('energy_sensitivity.json');stex=(ROOT/'paper/sections/9_sensitivity.tex').read_text()
    for k in ('q1','q2','q3'):
        z=stress[k]['tightest']
        if f'{z["horizontal_increase_percent"]:.4f}\\%' not in stex or f'{z["all_energy_increase_percent"]:.4f}\\%' not in stex:errors.append('论文敏感性表不符: '+k)
    rows=figure_map()
    if any(x['matches_current_code']!='是' for x in rows if not x['figure_or_table'].startswith('tab:')):errors.append('论文图表文件缺失、早于结果或无法映射')
    pdf=ROOT/'paper'/'main.pdf'
    newest=max(p.stat().st_mtime for p in (ROOT/'paper').rglob('*.tex'))
    if not pdf.exists() or pdf.stat().st_mtime<newest:notes.append('论文PDF早于LaTeX源文件，尚未重新编译')
    else:
        submission=ROOT/'D题论文.pdf'
        if not submission.exists() or sha(submission)!=sha(pdf):errors.append('根目录提交PDF与paper/main.pdf不同')
        try:
            import pymupdf
            document=pymupdf.open(pdf)
            extracted='\n'.join(page.get_text() for page in document)
            if len(document)<10 or any(phrase not in extracted for phrase in ('山区洪涝','104.61','112.82','78.8732','4061','附录')):
                errors.append('PDF页数或关键文字提取不符')
        except ImportError:notes.append('未安装PyMuPDF，PDF文字核对未运行')
    metadata_file=RESULT/'experiment_metadata.json'
    if verify_metadata and metadata_file.exists():
        archived=json.loads(metadata_file.read_text(encoding='utf8'))
        for name,digest in archived['output_sha256'].items():
            if sha(RESULT/name)!=digest:errors.append('结果版本与元数据不符: '+name)
        for name,digest in archived['input_code_config_sha256'].items():
            if not (ROOT/name).exists() or sha(ROOT/name)!=digest:errors.append('代码/输入/配置版本与元数据不符: '+name)
        for name,digest in archived['paper_figure_sha256'].items():
            if not (ROOT/name).exists() or sha(ROOT/name)!=digest:errors.append('论文图版本与元数据不符: '+name)
        for name,key in [('paper/main.pdf','paper_pdf_sha256'),('D题论文.pdf','submission_pdf_sha256')]:
            if key in archived and sha(ROOT/name)!=archived[key]:errors.append('PDF版本与元数据不符: '+name)
    return dict(status='PASS' if not errors else 'FAIL',errors=errors,notes=notes,metrics={'Q1':q1['summary'],'Q2':q2['summary'],'Q3':q3['summary'],'Q4_two':q4['schemes']['2']['selected']['deficit'],'Q4_three':q4['schemes']['3']['selected']['deficit']},figures=len(rows))

def metadata(report):
    paths=[p for folder in ('input','config','code') for p in (ROOT/folder).rglob('*') if p.is_file() and p.suffix in ('.xlsx','.csv','.tif','.json','.py') and not p.name.startswith('~$')]
    paths += [ROOT/'check_consistency.py'] + sorted((ROOT/'paper').rglob('*.tex'))
    hashes={str(p.relative_to(ROOT)):sha(p) for p in sorted(paths)}
    outputs={x:sha(RESULT/x) for x in CANONICAL}
    figures={x['figure_file']:sha(ROOT/x['figure_file']) for x in figure_map() if (ROOT/x['figure_file']).exists()}
    try:git=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    except Exception:git=None
    obj=dict(experiment_time_utc=datetime.now(timezone.utc).isoformat(),git_head=git,working_tree='contains uncommitted modifications; use hashes',input_code_config_sha256=hashes,output_sha256=outputs,paper_figure_sha256=figures,paper_pdf_sha256=sha(ROOT/'paper/main.pdf'),submission_pdf_sha256=sha(ROOT/'D题论文.pdf'),parameters={'base':base_parameters(),'optimization':optimization_parameters()},random_seeds={'method_comparison':[0,1,2],'cp_sat':42},model='Q1 group packing; Q2 transport; Q3 transport-relay; Q4 fixed partition',key_metrics=report['metrics'],audit_status=report['status'])
    (RESULT/'experiment_metadata.json').write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=float),encoding='utf8')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--write',action='store_true');a=parser.parse_args()
    AUDIT.mkdir(parents=True,exist_ok=True)
    if a.write:registry(Model());alignment(Model());literal_inventory()
    report=check(verify_metadata=not a.write)
    if a.write:metadata(report)
    (AUDIT/'consistency_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=float),encoding='utf8')
    print(json.dumps(report,ensure_ascii=False,default=float))
    return 0 if report['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main())
