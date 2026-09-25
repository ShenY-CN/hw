# 本程序及代码在人工智能工具辅助下完成：OpenAI Codex（GPT-6，OpenAI；GPT-6 模型家族发布日期 2026-09-03）。
# 参赛队须自行理解、复核与改写。
"""Vector plots for common-protocol method comparison."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from common import Model, ROOT, RESULT

font='DejaVu Sans'
for candidate in ('PingFang SC','Noto Sans CJK SC','Microsoft YaHei'):
    try:font_manager.findfont(candidate,fallback_to_default=False);font=candidate;break
    except ValueError:pass
plt.rcParams.update({'font.family':font,'font.size':10,'axes.unicode_minus':False,'pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False,'savefig.bbox':'tight'})
colors={'grasp':'#0072B2','hill':'#D55E00','anneal':'#009E73','tabu':'#CC79A7','existing_baseline':'#555555'}
labels={'grasp':'随机化构造','hill':'局部爬山','anneal':'模拟退火','tabu':'禁忌搜索','existing_baseline':'既有方案'}

def run():
    d=json.loads((RESULT/'method_comparison.json').read_text())
    m=Model();total_priority=sum(b['priority'] for b in m.boxes)
    fig,axes=plt.subplots(1,2,figsize=(9.2,3.5))
    for method in labels:
        items=[x for x in d['candidates'] if x['method']==method and x['validation']['pass_']]
        if not items:continue
        x=[v['metrics']['energy'] for v in items]
        y=[v['metrics']['weighted_arrival']/total_priority/60 for v in items]
        z=[v['metrics']['makespan']/60 for v in items]
        for ax,vals in [(axes[0],y),(axes[1],z)]:
            ax.scatter(x,vals,c=colors[method],s=47,label=labels[method],alpha=.85)
        for ax,vals in [(axes[0],y),(axes[1],z)]:
            for item,xi,yi in zip(items,x,vals):
                if item['selected']:
                    ax.scatter([xi],[yi],facecolors='none',edgecolors='black',s=145,linewidths=1.3,zorder=5)
    axes[0].set_xlabel('运输总能耗 / kWh');axes[0].set_ylabel('优先加权平均交付时刻 / min')
    axes[1].set_xlabel('运输总能耗 / kWh');axes[1].set_ylabel('最后返航时刻 / min')
    for ax in axes:ax.grid(alpha=.2)
    axes[0].legend(loc='best',fontsize=8)
    fig.tight_layout()
    path=ROOT/'figures'/'method_tradeoff'
    fig.savefig(path.with_suffix('.pdf'));fig.savefig(path.with_suffix('.png'),dpi=180)
    plt.close(fig)
    print(path.with_suffix('.pdf'))

if __name__=='__main__':run()
