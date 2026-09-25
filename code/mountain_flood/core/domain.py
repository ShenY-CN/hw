# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-6，OpenAI；GPT-6 模型家族发布日期 2026-09-03）。
# 参赛队须自行理解、复核与改写；本会话未提供更细的子型号标识。
"""项目共用的物理模型。单位：米、秒、千克、千瓦时；坐标系为 WGS84。"""

# 支持直接运行本文件；此处将 code/ 加入模块搜索路径。
if __package__ in (None, ""):
    import sys
    from pathlib import Path as _BootstrapPath
    sys.path.insert(0, str(_BootstrapPath(__file__).resolve().parents[2]))
from pathlib import Path
import json, math, os
import numpy as np
import openpyxl
import rasterio
from pyproj import Geod

from mountain_flood.paths import ROOT, INPUT, RESULT
def save(name,data):
    (RESULT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2,default=lambda x:x.item() if hasattr(x,'item') else str(x)),encoding='utf-8')
def rows(name,sheet='数据'):
    p=next(INPUT.rglob(name+'.xlsx'))
    return list(openpyxl.load_workbook(p,data_only=True)[sheet].values)

class Model:
    def __init__(self):
        nr=rows('调度中心与服务区')
        self.nodes=[dict(id=r[0],name=r[1],lon=r[2],lat=r[3],z=r[4],pop=r[5] or 0) for r in [nr[2]]+nr[6:21]]
        self.idx={n['id']:i for i,n in enumerate(self.nodes)}
        self.geo=Geod(ellps='WGS84')
        self.raster=rasterio.open(next(INPUT.rglob('*.tif')))
        self.dem=self.raster.read(1)
        self.tf=self.raster.transform
        tr=rows('运输无人机数据')
        keys=['id','name','mass','Q','V','vc','L0','LF','E','rho','prep','load','handoff','perbox','vu','vd','eta','downeta']
        self.types={r[0]:dict(zip(keys,r)) for r in tr[2:5]}
        self.units={g:[r[0] for r in tr[8:16] if r[1]==g] for g in self.types}
        for r in tr[19:22]: self.types[r[0]].update(batteries=r[1],charge=r[2])
        self.boxes=[]
        for r in rows('物资需求与配送时限','逐箱货箱清单')[1:]:
            # 每个货箱都必须在其规定的送达时间前到达；若属于首批货物，
            # 首批截止时间还可能构成一个更早的额外硬时限。
            hard=min(r[7],r[6] if r[5]=='是' else 1e9)
            self.boxes.append(dict(id=r[0],node=self.idx[r[1]],kind=r[2],w=r[3],v=r[4],first=r[5]=='是',deadline=hard,due=r[7],priority=r[8]))
        self.xy=np.array([self.local(n['lon'],n['lat']) for n in self.nodes])
        self.op=np.array([n['z']+(30 if i else 0) for i,n in enumerate(self.nodes)])
        self.D=np.zeros((16,16));self.H=np.zeros((16,16))
        self.T={g:np.zeros((16,16)) for g in self.types}
        for i in range(16):
            for j in range(i+1,16):
                a,b=self.nodes[i],self.nodes[j]
                d=self.geo.inv(a['lon'],a['lat'],b['lon'],b['lat'])[2]
                h=max(self.line_max(a['lon'],a['lat'],b['lon'],b['lat'])+50,self.op[i],self.op[j])
                self.D[i,j]=self.D[j,i]=d;self.H[i,j]=self.H[j,i]=h
        for g,t in self.types.items():
            for i in range(16):
                for j in range(16):
                    if i!=j:self.T[g][i,j]=(self.H[i,j]-self.op[i])/t['vu']+self.D[i,j]/t['vc']+(self.H[i,j]-self.op[j])/t['vd']

    def local(self,lon,lat):
        o=self.nodes[0]; az,_,d=self.geo.inv(o['lon'],o['lat'],lon,lat)
        return (d*math.sin(math.radians(az)),d*math.cos(math.radians(az)))
    def lonlat(self,x,y):
        o=self.nodes[0];lon,lat,_=self.geo.fwd(o['lon'],o['lat'],math.degrees(math.atan2(x,y)),math.hypot(x,y));return lon,lat
    def ground(self,lon,lat):
        col=(np.asarray(lon)-self.tf.c)/self.tf.a; row=(np.asarray(lat)-self.tf.f)/self.tf.e
        return self.dem[np.clip(np.floor(row).astype(int),0,self.dem.shape[0]-1),np.clip(np.floor(col).astype(int),0,self.dem.shape[1]-1)]
    def cells(self,lon1,lat1,lon2,lat2):
        """精确遍历线段穿过的栅格边界，避免漏掉很短的单元穿越。"""
        c1,r1=(lon1-self.tf.c)/self.tf.a,(lat1-self.tf.f)/self.tf.e
        c2,r2=(lon2-self.tf.c)/self.tf.a,(lat2-self.tf.f)/self.tf.e
        cuts=[0.,1.]
        for a,b in [(c1,c2),(r1,r2)]:
            if abs(b-a)>1e-12:
                k=np.arange(math.floor(min(a,b))+1,math.ceil(max(a,b)))
                cuts.extend(((k-a)/(b-a)).tolist())
        cuts=np.unique(np.clip(cuts,0,1)); mids=(cuts[:-1]+cuts[1:])/2
        h=self.ground(lon1+(lon2-lon1)*mids,lat1+(lat2-lat1)*mids)
        return cuts,h
    def line_max(self,*args):
        _,h=self.cells(*args);return float(max(h))
    def blocked(self,a,b):
        cuts,h=self.cells(a[0],a[1],b[0],b[1]);z=a[2]+(b[2]-a[2])*cuts
        return bool(np.any(h>np.minimum(z[:-1],z[1:])+1e-8))
    def link_margin(self,a,b,threshold):
        d=math.hypot(self.geo.inv(a[0],a[1],b[0],b[1])[2],b[2]-a[2])/1000
        return threshold-(32.45+20*math.log10(2400)+20*math.log10(max(d,1e-6))+10*self.blocked(a,b))
    def energy(self,g,i,j,q):
        t=self.types[g]; L=t['L0']-(t['L0']-t['LF'])*(max(q,0)/t['Q'])**1.5
        return t['E']*self.D[i,j]/L+(t['mass']+q)*9.81*(self.H[i,j]-self.op[i])/(t['eta']*3.6e6)
    def route(self,g,ids,order=None,rho=.2):
        t=self.types[g];bs=[self.boxes[i] for i in ids]
        w=sum(b['w'] for b in bs);v=sum(b['v'] for b in bs)
        if w>t['Q']+1e-9 or v>t['V']+1e-9:return None
        order=list(order or sorted(set(b['node'] for b in bs)))
        if len(set(order))!=len(order) or set(order)!={b['node'] for b in bs}:return None
        clock=t['prep']+t['load']*len(ids);takeoff=clock;prev=0;e=0.;deliver={};segments=[]
        for node in order+[0]:
            h=self.H[prev,node];a=self.nodes[prev];b=self.nodes[node]
            up=(h-self.op[prev])/t['vu'];cruise=self.D[prev,node]/t['vc'];down=(h-self.op[node])/t['vd']
            segments.extend([dict(phase='爬升',a=[a['lon'],a['lat'],self.op[prev]],b=[a['lon'],a['lat'],h],start=clock,end=clock+up),dict(phase='巡航',a=[a['lon'],a['lat'],h],b=[b['lon'],b['lat'],h],start=clock+up,end=clock+up+cruise),dict(phase='下降',a=[b['lon'],b['lat'],h],b=[b['lon'],b['lat'],self.op[node]],start=clock+up+cruise,end=clock+up+cruise+down)])
            e+=self.energy(g,prev,node,w);clock+=up+cruise+down
            if node:
                here=[i for i in ids if self.boxes[i]['node']==node]
                hand=t['handoff']+t['perbox']*len(here)
                segments.append(dict(phase='交接',a=[b['lon'],b['lat'],self.op[node]],b=[b['lon'],b['lat'],self.op[node]],start=clock,end=clock+hand))
                clock+=hand
                for k in here:deliver[k]=clock
                w-=sum(self.boxes[k]['w'] for k in here)
            prev=node
        if e>(1-rho)*t['E']+1e-9:return None
        return dict(g=g,boxes=list(ids),order=order,w=sum(b['w'] for b in bs),v=v,energy=e,duration=clock,takeoff=takeoff,deliver=deliver,segments=segments,soc=1-e/t['E'])

def charge(s,T):
    return T*(.65*(.9-s)/.9+.35) if s<.9 else T*.35*(1-s)/.1

if __name__=='__main__':
    m=Model()
    save('data_profile.json',dict(nodes=m.nodes,boxes=m.boxes,types=m.types,dem=dict(shape=m.dem.shape,crs=str(m.raster.crs),bounds=list(m.raster.bounds),min=float(m.dem.min()),max=float(m.dem.max())),distance=m.D.tolist(),cruise=m.H.tolist(),mass=sum(b['w'] for b in m.boxes),volume=sum(b['v'] for b in m.boxes)))
    print('data profile saved')
