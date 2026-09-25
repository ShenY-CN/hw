# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-6，OpenAI；GPT-6 模型家族发布日期 2026-09-03）。
# 参赛队须自行理解、复核与改写；本会话未提供更细的子型号标识。
from common import *
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

FIG=ROOT/'figures';FIG.mkdir(exist_ok=True)
FONT='DejaVu Sans'
for candidate in ('PingFang SC','Noto Sans CJK SC','Microsoft YaHei'):
    try:
        font_manager.findfont(candidate,fallback_to_default=False)
        FONT=candidate
        break
    except ValueError:
        pass
plt.rcParams.update({'font.family':FONT,'font.size':10,'axes.unicode_minus':False,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False,'savefig.bbox':'tight'})
COL={'A':'#0072B2','B':'#D55E00','C':'#009E73'}
def load(n):return json.loads((RESULT/n).read_text(encoding='utf8'))
def finish(fig,n):
    fig.tight_layout();fig.savefig(FIG/(n+'.pdf'));fig.savefig(FIG/(n+'.png'),dpi=180);plt.close(fig)

def base(ax,m):
    ax.set_aspect('equal');ax.set_xlabel('东向距离 / km');ax.set_ylabel('北向距离 / km')
    lon=np.linspace(109.16,109.30,350);lat=np.linspace(22.999,23.09,250);xx,yy=np.meshgrid(lon,lat)
    z=m.ground(xx,yy);o=m.nodes[0]
    ext=[m.local(lon[0],o['lat'])[0]/1000,m.local(lon[-1],o['lat'])[0]/1000,m.local(o['lon'],lat[0])[1]/1000,m.local(o['lon'],lat[-1])[1]/1000]
    ax.imshow(z,origin='lower',extent=ext,cmap='Greys',alpha=.32,aspect='equal')
    ax.scatter(0,0,s=100,marker='*',color='black',zorder=6)
    ax.text(.13,-.4,'O01',fontsize=9)
    for i,(x,y) in enumerate(m.xy[1:],1):
        ax.scatter(x/1000,y/1000,s=30,color='black',zorder=5)
        ax.annotate(f'S{i:03}',(x/1000,y/1000),xytext=(4,5),textcoords='offset points',fontsize=8)
    ax.set_xlim(-8,8);ax.set_ylim(-1,10)

def run():
    m=Model();q1=load('q1_rho20.json');q2=load('q2.json');q3=load('q3.json');q4=load('q4.json')
    fig,ax=plt.subplots(figsize=(6.4,3.5))
    for g,offset,marker in [('A',-.18,'o'),('B',0,'s'),('C',.18,'^')]:
        vals=[r['maxload'] for r in q1['capacities'] if r['g']==g]
        ax.scatter(np.arange(1,16)+offset,vals,color=COL[g],marker=marker,label=g+'型',s=35)
    ax.set_xticks(range(1,16),[f'{i:03}' for i in range(1,16)]);ax.set_xlabel('服务区编号');ax.set_ylabel('最大安全载荷 / kg');ax.set_ylim(0,85);ax.legend(ncol=3);ax.grid(axis='y',alpha=.2)
    finish(fig,'capacity')
    fig,ax=plt.subplots(figsize=(6.4,4.4));base(ax,m)
    for r in q2['routes']:
        points=m.xy[[0]+r['order']+[0]]/1000
        ax.plot(points[:,0],points[:,1],color=COL[r['g']],lw=1,alpha=.7)
    ax.legend(handles=[Line2D([0],[0],color=c,label=g+'型航线') for g,c in COL.items()],loc='lower left',fontsize=8)
    finish(fig,'routes')
    for q,label in [(q2,'transport_gantt'),(q3,'joint_gantt')]:
        fig,ax=plt.subplots(figsize=(6.4,4.1))
        us=[f'U{i:02}' for i in range(1,9)]+(list(dict.fromkeys(r['unit'] for r in q3['relays'])) if label=='joint_gantt' else [])
        for r in q['routes']:
            j=us.index(r['unit']);ax.barh(j,(r['end']-r['start'])/60,left=r['start']/60,height=.64,color=COL[r['g']])
            ax.text((r['start']+r['end'])/120,j,r['id'],ha='center',va='center',fontsize=7,color='white')
        if label=='joint_gantt':
            for r in q3['relays']:
                j=us.index(r['unit']);ax.barh(j,(r['end']-r['start'])/60,left=r['start']/60,height=.64,color='#CC79A7');ax.barh(j,(r['service_end']-r['ready'])/60,left=r['ready']/60,height=.64,color='#78518B')
        ax.set_yticks(range(len(us)),us);ax.invert_yaxis();ax.set_xlabel('时刻 / min');ax.grid(axis='x',alpha=.2);finish(fig,label)
    fig,ax=plt.subplots(figsize=(6.4,4.5))
    bats=sorted(set(r['battery'] for r in q3['routes']))
    for r in q3['routes']:
        j=bats.index(r['battery']);ax.barh(j,(r['end']-r['start'])/60,left=r['start']/60,color=COL[r['g']],height=.7)
        ax.barh(j,charge(r['soc'],m.types[r['g']]['charge'])/60,left=r['end']/60,color='#D9D9D9',height=.7,hatch='///',edgecolor='white')
    ax.set_yticks(range(len(bats)),bats);ax.invert_yaxis();ax.set_xlabel('时刻 / min');ax.legend(handles=[Patch(facecolor='#777777',label='任务占用'),Patch(facecolor='#D9D9D9',hatch='///',label='充电')],loc='upper right');finish(fig,'battery_gantt')
    fig,ax=plt.subplots(figsize=(6.4,4.5));base(ax,m)
    for r in q3['routes']:
        p=m.xy[[0]+r['order']+[0]]/1000;ax.plot(p[:,0],p[:,1],color='#777777',lw=.6,alpha=.4)
    sitecolors={'W':'#CC79A7','E':'#0072B2','N':'#D55E00'}
    shown=set()
    for r in q3['relays']:
        if r['site'] in shown:continue
        shown.add(r['site']);x,y=m.local(*r['pos'][:2]);color=sitecolors[r['site']]
        ax.scatter(x/1000,y/1000,s=90,marker='D',color=color,zorder=7);ax.text(x/1000+.2,y/1000-.3,r['site'],color=color)
        ax.plot([0,x/1000],[0,y/1000],ls='--',color=color)
    for r in q3['relays']:
        tids={c['route'] for c in q3['communication'] if c['relay_task']==r['id']};ns={n for t in q3['routes'] if t['id'] in tids for n in t['order']}
        x,y=m.local(*r['pos'][:2])
        for n in ns:ax.plot([x/1000,m.xy[n,0]/1000],[y/1000,m.xy[n,1]/1000],color=sitecolors[r['site']],ls=':',lw=.8)
    finish(fig,'relay_map')
    fig,axes=plt.subplots(1,2,figsize=(6.4,3.6))
    for ax,k in zip(axes,[2,3]):
        groups=q4['schemes'][str(k)]['selected']['groups']
        for j,g in enumerate(groups):
            xy=m.xy[g['nodes']]/1000;ax.scatter(xy[:,0],xy[:,1],color=list(COL.values())[j],marker=['o','s','^'][j],s=35,label=f'组{j+1}')
            for n in g['nodes']:ax.annotate(f'{n:03}',m.xy[n]/1000,xytext=(2,4),textcoords='offset points',fontsize=7)
        ax.scatter(0,0,marker='*',color='black');ax.set_xlabel('东向 / km');ax.set_ylabel('北向 / km');ax.set_title(f'{k}个任务组',fontsize=10);ax.legend(fontsize=8);ax.set_xlim(-8,7);ax.set_ylim(-1,9)
    finish(fig,'partitions')
    fig,axes=plt.subplots(1,2,figsize=(6.4,3.0))
    qs=[load(f'q1_rho{r}.json') for r in [10,20,30]]
    axes[0].plot([10,20,30],[x['summary']['count'] for x in qs],marker='o',color='#0072B2');axes[0].set_ylabel('最少架次');axes[0].set_yticks(range(18,22));axes[0].set_xlabel('安全余量 / %')
    axes[1].plot([10,20,30],[x['summary']['energy'] for x in qs],marker='s',color='#D55E00');axes[1].set_ylabel('能耗 / kWh');axes[1].set_xlabel('安全余量 / %')
    for ax in axes:ax.set_xticks([10,20,30]);ax.grid(alpha=.2)
    finish(fig,'sensitivity')
    print('figures complete')

if __name__=='__main__':run()
