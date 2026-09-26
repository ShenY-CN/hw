# D 题赛题分析与建模设计（M1 返工摘要）

详细模型、假设—偏差—验证表和来源见项目根目录题目分析报告.md；全局符号见术语表格.md。未运行的 ε-约束、鲁棒优化和分解迭代均为待验证合同。

## 1. Q1 精确模型边界

对服务区 \(i\) 的同型箱计数 \(\boldsymbol n_i\)，枚举所有满足质量、体积和

\[
E_{gi}(\boldsymbol a)\le(1-\rho_g)E_g^{\mathrm{use}}
\]

的非零单点直送模式 \((g,\boldsymbol a)\in\mathcal A_i\)。状态 \(F_i(\boldsymbol r)\) 的边界和转移为

\[
F_i(\boldsymbol0)=(0,0),\qquad
F_i(\boldsymbol r)=\min_{\mathrm{lex}}
\{F_i(\boldsymbol r-\boldsymbol a)+(1,E_{gi}(\boldsymbol a))\}.
\]

目标依次最少架次、最少飞行能耗。装载、交接时间进入航次时长，但当前模型不据此额外虚构地面作业耗电。完整枚举模式时可由最优子结构归纳证明，在“单服务区直送、固定轨迹/能耗模型”内全局最优；不外推到 Q2 多站与实体排程。

## 2. Q2 两层模型

概念完整层用航次槽 \(k\)，含启用、箱组、访问、弧、机型、实体机、电池和时刻变量。必须满足 \(x_{bk}\le a_k\)、仓库出入度等于 \(a_k\)、服务区流守恒、MTZ 子回路、容量/能源、\(C_k=s_k+\Delta_k\)、条件交付和硬截止。条件交付优先用 enforcement literal；如用大 \(M\)，其值取时间域上界与最早可达时刻之差的有效上界。实体机和电池分别建立以分配变量为 presence 的 optional intervals 并 NoOverlap。

实际层用完整路线列

\[
r=(B_r,\sigma_r,g_r,E_r,\Delta_r,\{\tau_{rb}\}),
\]

启发式直接搜索完整路线列集合；固定集合后 CP-SAT 只排 \(s_r,C_r\)、实体机和电池。当前没有独立 set-partitioning 列选择主问题，概念槽 \(k\) 与路线列 \(r\) 不得混称。

先求 \(T_\pi^*\)，在 \(T_\pi\le T_\pi^*+\varepsilon_T\) 下对 \(C_T,E_T,N_T,-\gamma_E\) 生成前沿。以

\[
\gamma_E\le r_k^E+M_E(1-a_k)
\]

保证最小能源裕度只取启用航次。历史 24 架次解只作共享 warm-start/基线。

## 3. Q3 正式约束

对中继任务槽 \(\ell\)，启用、站点、机体和组件满足

\[
\sum_hq_{\ell h}=e_\ell,\qquad
\sum_uz^R_{\ell u}=e_\ell,\qquad
\sum_rw^R_{\ell r}=e_\ell.
\]

当 \(e_\ell=1\) 时，用 OnlyEnforceIf 强制

\[
0\le t_\ell\le a_\ell\le b_\ell\le c_\ell\le H,
\]

并强制按所选站点计算飞抵/返航时刻与飞行—建链—悬停能量等式；当 \(e_\ell=0\) 时固定

\[
t_\ell=a_\ell=b_\ell=c_\ell=E_\ell^R=0.
\]

等价大 \(M\) 写法须双向条件化全部等式，并用 \(He_\ell\) 约束时间上界。占机（含周转）、服务、组件（至充满）均为 optional intervals；具体机体和组件 NoOverlap，未启用任务不存在区间。启用任务能量不超过 \((1-\rho_R)E_R^{\mathrm{use}}\)。

对运输区间 \((k,m)\)，直连、接入和回程连续证书分别为 \(\kappa^{\mathrm{dir}}_{km}\)、\(\kappa^{\mathrm{acc}}_{kmh}\)、\(\kappa^{\mathrm{back}}_h\)。中继覆盖 \(c_{km\ell}\) 必须同时受启用、站点接入证书、回程证书和区间落入服务窗口约束。全覆盖为

\[
d_{km}+\sum_\ell c_{km\ell}\ge1,\qquad
d_{km}\le\kappa^{\mathrm{dir}}_{km}.
\]

损耗上界

\[
\bar L_I=32.45+20\log_{10}f_{\mathrm{MHz}}
+20\log_{10}\bar D_{I,\mathrm{km}}+\bar B_I
\]

不超过允许损耗才可置证书为 1。不能证明则二分；采样不替代证明。主问题与连续通信子问题之间回传覆盖割，保存每轮冲突、扩张和停止原因后才称联合优化。运输与中继能源裕度分别记为 \(\gamma_E^T,\gamma_E^R\)，各自只在启用任务取最小值；联合指标定义为无量纲后的 \(\gamma_E^J=\min(\gamma_E^T,\gamma_E^R)\)。

## 4. Q4 分组和目标

组件分组变量 \(a_{ch}\) 满足每组件恰属一组、每组非空，并以组最小组件编号递增消除对称。对固定任务区间端点事件集 \(\mathcal T\)，资源峰值满足

\[
r_{hk}\ge\sum_jd_{jk}a_{c(j),h}\mathbf1\{t\in I_j\},
\qquad t\in\mathcal T.
\]

在后续最小化总配置的目标下，\(r_{hk}\) 自动等于事件集上的最大并发需求；若脱离该目标，则须显式使用最大值等式。

令 \(R_k=\sum_hr_{hk}\)，则代码字段统一为

\[
\mathrm{duplicated}_k=R_k-r_k^{\mathrm{pool}},\quad
\mathrm{unused}_k=\max(0,A_k-R_k),\quad
\mathrm{deficit}_k=\max(0,R_k-A_k).
\]

正式词典序为缺口总数→配置总数（等价于重复冗余）→工作量 CV。另存缺口→CV→配置的均衡备选，不得混称。

## 5. 来源与自检

来源：题目七项附件；Dorling et al., 2017, DOI 10.1109/TSMC.2016.2582745；Zhang et al., 2021, DOI 10.1016/j.trd.2020.102668；ITU-R P.525-5, 2024。详细报告已列每项假设的依据、偏差和复验方法。本作者不自行发起 M1。
