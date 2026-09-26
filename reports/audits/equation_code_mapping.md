# 论文公式与代码逐项对应（2026-09-25）

核对范围：`paper/sections/*.tex` 对应当前 `results/q1_rho20.json`、`q2.json`、`q3.json`、`q4.json`。数值单位以 m、s、kg、kWh、dB 为基准。以下“实际采用”指归档主方案重算与校验代码。参考文献公式仅解释机理，不作为求解公式。

| 论文公式／规则 | 数学含义 | Python 文件、函数及变量 | 实际实现 | 差异判断 |
|---|---|---|---|---|
| §数据处理 `H_ij=max(DEM+50,z_i,z_j)` | 山体净空 | `core/domain.py::Model.__init__`, `Model.cells`, `Model.line_max`, `H`, `op` | 逐栅格交点精确扫线，巡航海拔加50 m；服务区作业高度地面+30 m | 一致；50/30进入统一配置 |
| 式 `L_g(q)` | 载荷相关等效航程 | `core/domain.py::Model.energy`, `L0,LF,Q` | 幂指数1.5，逐段扣除已交付载荷 | 一致 |
| 式 `t^g_ij` | 上升、巡航、下降时间 | `core/domain.py::Model.__init__` 和 `Model.route`, `vu,vc,vd` | 三段相加，站点交接另计 | 一致 |
| 式 `E^g_ij(q)` | 水平航程标定能耗+爬升势能 | `core/domain.py::Model.energy`, `E,D,L,mass,eta` | `E*D/L + (mass+q)*9.81*up/(eta*3.6e6)`；下降不另计 | 一致 |
| `sum E <= (1-rho)Euse` | 返航安全余量 | `core/domain.py::Model.route`, `rho` | 默认逐机型从附件读20%；Q1敏感性显式传入10/20/30/40% | 一致；Q1灵敏度属合法场景差异 |
| `sum w<=Q_g`, `sum v<=V_g` | 重量与容积 | `core/domain.py::Model.route`, `w,v,Q,V` | 候选路线生成和独立回放均检查 | 一致 |
| `D_b<=h_b` | 医疗期望时刻与首批截止硬约束 | `core/domain.py::Model.__init__`, `deadline`; `problem2/search.py::refine_timefirst`; `problem3/schedule.py::allowed_starts`; `validation/replay.py::validate` | 医疗取due、首批取first_deadline、重合取较小值；31箱有硬截止 | 一致 |
| `T_b=max(0,D_b-d_b)` | 其他物资期望时刻软迟到 | `problem2/transport.py::metrics`, `weighted_tardiness`; `problem2/search.py::refine_timefirst`; `problem3/schedule.py::solve` | 仅对非医疗箱累计软迟到；医疗箱期望时刻单独作为硬截止 | 一致；审计时移除了医疗零迟到冗余项 |
| `C_T=max_p f_p` | Q2运输最后返航 | `problem2/transport.py::metrics`, `makespan` | 运输路线`end`最大值 | 一致 |
| `C_J=max(C_T,max relay end)` | Q3联合最后返航 | `problem3/hard_deadline.py::solve_choices`; `workflow/promote_fusion.py::checked` | 运输与中继返航最大值 | 一致 |
| `sum pi_b D_b / sum pi_b` | 优先加权平均交付 | `problem2/transport.py::metrics`, `weighted_arrival`; 图表/论文除以附件优先系数总和 | `weighted_arrival`结果字段是未除分母的分子（系数·s），论文表中才转换成分钟平均值 | **变量语义易混**；审计表区分“加权交付总和”与“加权平均交付” |
| 两阶段充电 `SOC→90%→100%` | 共享电池占用 | `core/domain.py::charge`, `charge_soc_break,charge_first_stage_fraction,charge_second_stage_fraction`; `validation/replay.py::validate` | 充电至满电前不允许复用；机型充电时间读附件 | 一致；比例来自统一配置 |
| `P_R=P_hover+P_comm` | 中继悬停通信耗能 | `problem3/communication.py::relay_flight`; `problem3/joint_solver.py::relay_plan`; `validation/replay.py::validate` | 1.05+0.05=1.10 kW，能源3.2 kWh，20%储备；来源为中继附件 | 一致；改为附件读取 |
| `FSPL=32.45+20log f+20log D` | 自由空间损耗 | `core/domain.py::Model.link_margin`; `problem3/communication.py::certificate` | f=2400 MHz，D=3D km | 一致 |
| `FSPL+10B<=Lmax` | 地形遮挡与双向门限 | `core/domain.py::Model.blocked`, `Model.link_margin`; `problem3/communication.py::certificate` | 遮挡加10 dB；双向门限由端点收发功率、增益、灵敏度、裕量、系统损耗取较弱方向得122/116/126 dB | 一致；门限改为附件推导 |
| `∀t`直连或中继接入+回传 | 连续通信 | `problem3/communication.py::certify_routes`, `certificate`; `validation/replay.py::validate` | 10 s初分割、递归6层；逐段保守距离+DEM扫掠；回放无缺口 | 一致；4061段证书。扫掠证书最小裕量0.09378 dB |
| 机体/电池并发不超库存 | 资源约束 | `problem2/search.py::refine_timefirst`, `problem3/hard_deadline.py::solve_choices`, `validation/replay.py::validate` | CP-SAT cumulative 与独立区间峰值检查；库存读附件 | 一致 |
| `CV=std(work)/mean(work)` | Q4分区均衡度 | `problem4/partition.py::partition`, `cv` | 任务固定后穷举8组件的2组127种、3组966种；不重新优化运输与中继 | 一致 |
| `deficit=max(0,total-inventory)` | Q4独立配置库存缺口 | `problem4/partition.py::partition`, `inventory,total,deficit` | 对组内运输、中继及充电占用求峰值后按组求和；库存读附件 | 一致 |

## 审计后仍需在论文中明确的限定

1. Q3固定候选的 `hard_deadline.py::solve_choices` 实际CP-SAT目标为运输收尾 `makespan`，最终跨候选排序再采用软迟到、**联合**收尾、加权交付。论文现有文字区分了“固定候选”与“有限候选排序”，数值无冲突，但不应把固定候选的OPTIMAL状态解释成联合全局最优。
2. Q1的 `time` 是架次作业时长之和，Q2、Q3的 `makespan` 是最后返航时刻。两个字段不可横向当作同一指标比较。
3. `weighted_arrival` 字段是优先加权总和，不是平均值；论文分钟数须再除以`sum(priority)*60`。
