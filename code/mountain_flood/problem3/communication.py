# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-6，OpenAI；GPT-6 模型家族发布日期 2026-09-03）。
# 参赛队须自行理解、复核与改写；本会话未提供更细的子型号标识。
"""执行地形感知链路检查，并为连续飞行区间生成保守覆盖证书。"""

# 支持直接运行本文件；此处将 code/ 加入模块搜索路径。
if __package__ in (None, ""):
    import sys
    from pathlib import Path as _BootstrapPath
    sys.path.insert(0, str(_BootstrapPath(__file__).resolve().parents[2]))
from mountain_flood.core.domain import *
from rasterio.features import rasterize
from affine import Affine
from itertools import combinations

def gateway(m):
    n=m.nodes[0];return [n['lon'],n['lat'],n['z']+20]

def certificate(m,a,b,fixed,threshold):
    """证明移动端点沿线段 [a,b] 运动时始终能与 fixed 建立链路。

    距离上界取线段两端中的最大值；遮挡部分使用 10 dB 最坏损耗，或通过
    栅格化扫掠三角形给出保守视距证明。局部切平面距离额外放大 0.02%。
    """
    ds=[math.hypot(m.geo.inv(p[0],p[1],fixed[0],fixed[1])[2]*1.0002,p[2]-fixed[2]) for p in [a,b]]
    fspl=32.45+20*math.log10(2400)+20*math.log10(max(max(ds)/1000,1e-6))
    if fspl+10<=threshold:return threshold-fspl-10,'worst_obstruction'
    if fspl>threshold:return -1.,'distance'
    a=np.array(a);b=np.array(b);f=np.array(fixed)
    ab=b[:2]-a[:2];af=f[:2]-a[:2]
    det=ab[0]*af[1]-ab[1]*af[0]
    if abs(det)<1e-15:
        # 仅垂直移动时，较低端点的射线覆盖较高端点对应的更严格遮挡情况。
        if np.linalg.norm(ab)<1e-12:
            low=a if a[2]<=b[2] else b
            return (threshold-fspl,'vertical_LOS') if not m.blocked(low,f) else (-1.,'blocked')
        return -1.,'degenerate'
    # 将视距扫掠三角形覆盖到所有相交栅格；平面在每个完整栅格内的最低值
    # 可作为该栅格内所有实际射线高度的保守下界。
    xy=np.array([a[:2],b[:2],f[:2]])
    cols=(xy[:,0]-m.tf.c)/m.tf.a;rows_=(xy[:,1]-m.tf.f)/m.tf.e
    c0=max(0,int(math.floor(cols.min()))-1);c1=min(m.dem.shape[1],int(math.ceil(cols.max()))+1)
    r0=max(0,int(math.floor(rows_.min()))-1);r1=min(m.dem.shape[0],int(math.ceil(rows_.max()))+1)
    tf=m.tf*Affine.translation(c0,r0)
    geom={'type':'Polygon','coordinates':[[a[:2].tolist(),b[:2].tolist(),f[:2].tolist(),a[:2].tolist()]]}
    mask=rasterize([(geom,1)],out_shape=(r1-r0,c1-c0),transform=tf,all_touched=True).astype(bool)
    rr,cc=np.where(mask)
    slopes=np.linalg.solve(np.array([ab,af]),np.array([b[2]-a[2],f[2]-a[2]]))
    lon=m.tf.c+(c0+cc+.5)*m.tf.a;lat=m.tf.f+(r0+rr+.5)*m.tf.e
    z=a[2]+slopes[0]*(lon-a[0])+slopes[1]*(lat-a[1])
    z-=abs(slopes[0]*m.tf.a)/2+abs(slopes[1]*m.tf.e)/2
    clear=np.all(m.dem[r0+rr,c0+cc]<=z+1e-8)
    return (threshold-fspl,'swept_LOS') if clear else (-1.,'unproven')

def relay_flight(m,lon,lat,z):
    o=m.nodes[0];h=max(m.line_max(o['lon'],o['lat'],lon,lat)+50,z)
    d=m.geo.inv(o['lon'],o['lat'],lon,lat)[2]
    out=(h-o['z'])/4+d/15+(h-z)/3
    ret=(h-z)/4+d/15+(h-o['z'])/3
    e=2*1.15*d/15/3600+23.5*9.81*((h-o['z'])+(h-z))/(.72*3.6e6)
    return dict(out=out,ret=ret,fly_energy=e,ready=180+out+30,max_service=(2.56-e)*3600/1.1-30)

def sample_segments(rs,step=150):
    pts=[];meta=[]
    for j,r in enumerate(rs):
        for k,s in enumerate(r['segments']):
            a=np.array(s['a']);b=np.array(s['b'])
            n=max(1,math.ceil((s['end']-s['start'])*15/step)) if s['phase']!='交接' else 1
            for f in np.linspace(0,1,n+1):
                pts.append((a+(b-a)*f).tolist());meta.append([j,k,float(f)])
    return pts,meta

def select_relays(m,rs):
    pts,meta=sample_segments(rs,200);gw=gateway(m)
    bad=[i for i,p in enumerate(pts) if m.link_margin(p,gw,122)<.2]
    pts=[pts[i] for i in bad];meta=[meta[i] for i in bad]
    candidates=[];covers=[]
    # 在任务范围内按 750 m 网格枚举站点，并加入各服务区位置；高度按规则取值。
    coords=[]
    for x in np.arange(-6000,6750,750):
        for y in np.arange(0,9750,750):coords.append((x,y))
    coords.extend(map(tuple,m.xy[1:]))
    for x,y in coords:
        lon,lat=m.lonlat(x,y);z=float(m.ground(lon,lat))+300
        p=[lon,lat,z]
        if m.link_margin(p,gw,126)<.3:continue
        coverage=np.array([m.link_margin(q,p,116)>=.3 for q in pts])
        if not coverage.any():continue
        candidates.append(dict(pos=p,x=x,y=y,**relay_flight(m,*p)));covers.append(coverage)
    best=None
    for a,b in combinations(range(len(candidates)),2):
        missed=int((~(covers[a]|covers[b])).sum())
        score=(missed,candidates[a]['fly_energy']+candidates[b]['fly_energy'])
        if best is None or score<best[0]:best=(score,a,b)
    print('relay grid',len(candidates),'required points',len(pts),'best',best[0],flush=True)
    save('relay_search.json',dict(required_points=len(pts),candidates=len(candidates),best_score=best[0],selected=[candidates[best[1]],candidates[best[2]]]))
    return [candidates[best[1]],candidates[best[2]]]

def certify_routes(m,rs,relays,verbose=True):
    gw=gateway(m);records=[];fails=[]
    for ri,r in enumerate(rs):
        for si,s in enumerate(r['segments']):
            def split(f0,f1,depth=0):
                a=np.array(s['a']);b=np.array(s['b']);p=a+(b-a)*f0;q=a+(b-a)*f1
                t0=r['start']+s['start']+(s['end']-s['start'])*f0
                t1=r['start']+s['start']+(s['end']-s['start'])*f1
                options=[('G01',gw,122,None)]+[(v['unit'],v['pos'],116,v['id']) for v in relays if t0>=v['ready']-1e-7 and t1<=v['service_end']+1e-7]
                best=None
                for provider,fixed,threshold,mission in options:
                    margin,method=certificate(m,p,q,fixed,threshold)
                    if margin>=0:
                        if best is None or margin>best[0]:best=(margin,method,provider,mission)
                        # 直连裕量至少为 1 dB 时，无需分配中继。
                        if provider=='G01' and margin>=1:break
                if best is not None:
                    margin,method,provider,mission=best
                    records.append(dict(route=r['id'],phase=s['phase'],start=t0,end=t1,provider=provider,relay_task=mission,margin=margin,method=method));return
                if depth<6:
                    mid=(f0+f1)/2;split(f0,mid,depth+1);split(mid,f1,depth+1)
                else:fails.append(dict(route=r['id'],phase=s['phase'],time=[t0,t1],pos=((p+q)/2).tolist()))
            dur=s['end']-s['start'];cuts=list(np.linspace(0,1,max(1,math.ceil(dur/10))+1))
            if dur>0:
                for v in relays:
                    for edge in [v['ready'],v['service_end']]:
                        frac=(edge-r['start']-s['start'])/dur
                        if 0<frac<1:cuts.append(frac)
            cuts=sorted(set(cuts))
            for f0,f1 in zip(cuts[:-1],cuts[1:]):split(f0,f1)
        if verbose:print('certified',ri+1,'/',len(rs),'fail',len(fails),flush=True)
    return records,fails

def run():
    from mountain_flood.problem3.joint_solver import run as solve_joint
    solve_joint()

if __name__=='__main__':run()
