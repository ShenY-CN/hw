%% MATLAB version of the results-based figures from figure/q1.py ... q4.py
% Run in MATLAB: run('.../code/mountain_flood/figure_matlab/run_all.m')
% Reads the existing verified JSON results and writes PNG/PDF to figures_matlab/.
clear; close all; clc;
here = fileparts(mfilename('fullpath'));
root = fileparts(fileparts(fileparts(here)));
out = fullfile(root,'figures_matlab'); if ~exist(out,'dir'), mkdir(out); end
q1=json(fullfile(root,'results','q1_rho20.json'));
q2=json(fullfile(root,'results','q2.json'));
q3=json(fullfile(root,'results','q3.json'));
q4=json(fullfile(root,'results','q4.json'));
q1e=json(fullfile(root,'results','q1_energy.json'));
q1t=json(fullfile(root,'results','q1_time.json'));
rho={json(fullfile(root,'results','q1_rho10.json')),q1,json(fullfile(root,'results','q1_rho30.json'))};
profile=json(fullfile(root,'results','data_profile.json'));
C=palette();
set(groot,'defaultFigureColor','w','defaultAxesFontName','PingFang SC', ...
    'defaultTextFontName','PingFang SC','defaultAxesFontSize',10, ...
    'defaultAxesBox','off','defaultLineLineWidth',1.5);

q1Capacity(q1,out,C);
q1Heatmap(q1,out);
q1Objective(q1e,q1t,out,C);
q1Sensitivity(rho,out,C);
socPlot(q1.routes,out,C,'q1_return_soc','问题一组批架次（按机型排序）',false);
q2Timeline(q2.routes,profile,out,C,'unit','q2_drone_timeline','运输无人机',false);
q2Timeline(q2.routes,profile,out,C,'battery','q2_battery_timeline','共享电池',true);
q2RouteEnergy(q2,out,C);
q2Search(root,profile,out,C);
q3Communication(q3,out,C);
q3Margins(q3,out,C);
q3RelaySoc(q3,out,C);
q3Compare(q2,q3,out);
q4Resources(q4,out);
q4Workload(q4,out,C);
q4Deficit(q4,out);
fprintf('已输出 %d 张 MATLAB 图表：%s\n',numel(dir(fullfile(out,'*.png'))),out);

function d=json(p), d=jsondecode(fileread(p)); end
function C=palette()
C.A=[0 114 178]/255; C.B=[213 94 0]/255; C.C=[0 158 115]/255;
C.W=[204 121 167]/255; C.E=[117 112 179]/255;
C.gray=[0.42 0.42 0.42]; C.orange=C.B;
end
function f=fig(w,h), f=figure('Visible','off','Color','w','Position',[80 80 w h]); end
function ax=axes0(f), ax=axes(f); hold(ax,'on'); grid(ax,'on'); ax.GridAlpha=.18; ax.TickDir='out'; end
function savefig0(f,out,name)
 drawnow; exportgraphics(f,fullfile(out,[name '.png']),'Resolution',180,'BackgroundColor','white');
 exportgraphics(f,fullfile(out,[name '.pdf']),'ContentType','image','Resolution',180,'BackgroundColor','white'); close(f);
end
function c=tc(C,g), c=C.(char(g)); end

function q1Capacity(d,out,C)
f=fig(1080,560); ax=axes0(f); hold(ax,'on'); types='ABC'; offsets=[-.2 0 .2]; marks={'o','s','^'};
for k=1:3
    ix=string({d.capacities.g})==string(types(k)); r=d.capacities(ix); [~,o]=sort([r.node]); r=r(o);
    scatter(ax,[r.node]+offsets(k),[r.maxload],38,tc(C,types(k)),marks{k},'filled','DisplayName',[types(k) '型']);
end
xticks(ax,1:15); xticklabels(ax,compose('%03d',1:15)); xlabel(ax,'服务区编号'); ylabel(ax,'最大安全载荷 / kg');
legend(ax,'Location','northoutside','Orientation','horizontal'); title(ax,'不同机型的最大安全载荷'); savefig0(f,out,'q1_safe_capacity');
end
function q1Heatmap(d,out)
M=zeros(3,15); types='ABC';
caps=d.capacities;
for i=1:numel(types)
    ix=strcmp({caps.g},types(i));
    M(i,[caps(ix).node])=[caps(ix).maxload];
end
f=fig(1120,420); ax=axes0(f); imagesc(ax,M); colormap(ax,parula(128)); cb=colorbar(ax); cb.Label.String='最大安全载荷 / kg';
xticks(ax,1:15); xticklabels(ax,compose('%03d',1:15)); yticks(ax,1:3); yticklabels(ax,{'A型','B型','C型'});
xlabel(ax,'服务区编号'); title(ax,'服务区—机型最大安全载荷热力图');
for i=1:3, for j=1:15, if M(i,j)>.62*max(M(:)), col='w'; else, col='k'; end; text(ax,j,i,sprintf('%.0f',M(i,j)),'HorizontalAlignment','center','FontSize',8,'Color',col); end, end
savefig0(f,out,'q1_capacity_heatmap');
end
function q1Objective(a,b,out,C)
f=fig(850,550); ax=axes0(f); rows={a.summary,b.summary}; labels={'最小能耗方案','最短时间方案'}; types='AB';
for k=1:2, r=rows{k}; scatter(ax,r.energy,r.time/60,80,tc(C,types(k)),'filled','DisplayName',labels{k}); text(ax,r.energy,r.time/60,['  ' labels{k}],'FontSize',9); end
xlabel(ax,'总能耗 / kWh'); ylabel(ax,'总飞行时间 / min'); legend(ax,'Location','best'); title(ax,'能耗与飞行时间的单目标方案'); savefig0(f,out,'q1_objective_solutions');
end
function q1Sensitivity(d,out,C)
x=[10 20 30]; count=cellfun(@(z)z.summary.count,d); energy=cellfun(@(z)z.summary.energy,d);
f=fig(960,440); tiledlayout(f,1,2,'TileSpacing','compact');
ax=nexttile; plot(ax,x,count,'o-','Color',C.A,'MarkerFaceColor',C.A); grid(ax,'on'); xlabel(ax,'返航安全余量 / %'); ylabel(ax,'最少架次'); xticks(ax,x);
ax=nexttile; plot(ax,x,energy,'s-','Color',C.orange,'MarkerFaceColor',C.orange); grid(ax,'on'); xlabel(ax,'返航安全余量 / %'); ylabel(ax,'总能耗 / kWh'); xticks(ax,x);
savefig0(f,out,'q1_sensitivity');
end
function socPlot(r,out,C,name,xlabelText,sortId)
if sortId, [~,ix]=sort(string({r.id})); r=r(ix); else, [~,ix]=sort(string({r.g})); r=r(ix); end
f=fig(1080,490); ax=axes0(f); hold(ax,'on');
for k=1:numel(r), scatter(ax,k,r(k).soc*100,34,tc(C,r(k).g),'filled','HandleVisibility','off'); end
yline(ax,20,'--','Color',C.orange,'DisplayName','最低返航储备 20%');
if sortId, xticks(ax,1:numel(r)); xticklabels(ax,{r.id}); xtickangle(ax,55);
else, for g='ABC', ix=find(string({r.g})==string(g)); scatter(ax,ix,[r(ix).soc]*100,36,tc(C,g),'filled','DisplayName',[g '型']); end, end
xlabel(ax,xlabelText); ylabel(ax,'返航剩余电量 / %'); ylim(ax,[0 105]); legend(ax,'Location','best'); title(ax,name); savefig0(f,out,name);
end

function q2Timeline(r,p,out,C,field,name,ylabelText,battery)
units=sort(unique(string({r.(field)}))); f=fig(1180,max(560,24*numel(units))); ax=axes0(f); hold(ax,'on');
for k=1:numel(r)
    lane=find(units==string(r(k).(field))); a=r(k).start/60; b=r(k).end/60; col=tc(C,r(k).g);
    rectangle(ax,'Position',[a lane-.31 b-a .62],'FaceColor',col,'EdgeColor','w','LineWidth',.5);
    if battery
        spec=p.types.(char(r(k).g)); soc=r(k).soc; if soc<.9, charge=spec.charge*(.65*(.9-soc)/.9+.35); else, charge=spec.charge*.35*(1-soc)/.1; end
        ce=b+charge/60; rectangle(ax,'Position',[b lane-.31 ce-b .62],'FaceColor',[.84 .84 .84],'EdgeColor',[.65 .65 .65]);
    elseif isfield(r,'id'), text(ax,(a+b)/2,lane,r(k).id,'Color','w','FontSize',7,'HorizontalAlignment','center','VerticalAlignment','middle'); end
end
yticks(ax,1:numel(units)); yticklabels(ax,units); set(ax,'YDir','reverse'); xlabel(ax,'时刻 / min'); ylabel(ax,ylabelText);
if battery, title(ax,'运输电池使用与充电时间轴'); else, title(ax,'运输无人机任务时间轴'); end
savefig0(f,out,name);
end
function q2RouteEnergy(d,out,C)
r=d.routes; [~,ix]=sort(string({r.id})); r=r(ix); f=fig(1180,480); ax=axes0(f); b=bar(ax,[r.energy],'FaceColor','flat');
for k=1:numel(r), b.CData(k,:)=tc(C,r(k).g); end
xticks(ax,1:numel(r)); xticklabels(ax,{r.id}); xtickangle(ax,55); xlabel(ax,'运输架次'); ylabel(ax,'架次能耗 / kWh'); title(ax,'运输架次能耗'); savefig0(f,out,'q2_route_energy');
end
function q2Search(root,p,out,C)
d=json(fullfile(root,'results','method_comparison.json')); methods={'grasp','hill','anneal','tabu','existing_baseline'};
labels={'随机化构造','局部爬山','模拟退火','禁忌搜索','历史可行解基线'}; cols=[C.A;C.orange;C.C;C.W;C.gray]; priority=sum([p.boxes.priority]);
f=fig(1450,470); tiledlayout(f,1,3,'TileSpacing','compact'); axs=gobjects(1,3); for j=1:3, axs(j)=nexttile; hold(axs(j),'on'); grid(axs(j),'on'); axs(j).GridAlpha=.18; end
for m=1:numel(methods)
    ix=find(string({d.candidates.method})==methods{m});
    for j=ix
        it=d.candidates(j); if ~it.validation.pass_, continue; end
        ys=[it.metrics.weighted_tardiness/priority/60 it.metrics.weighted_arrival/priority/60 it.metrics.makespan/60];
        for a=1:3, scatter(axs(a),it.metrics.energy,ys(a),42,cols(m,:),'filled','DisplayName',labels{m}); if it.selected, scatter(axs(a),it.metrics.energy,ys(a),115,'ko','LineWidth',1.1); end, end
    end
end
xlabel(axs(1),'运输能耗 / kWh'); ylabel(axs(1),'优先加权平均迟到 / min');
xlabel(axs(2),'运输能耗 / kWh'); ylabel(axs(2),'优先加权平均送达 / min');
xlabel(axs(3),'运输能耗 / kWh'); ylabel(axs(3),'最晚返航 / min'); legend(axs(1),'Location','best','FontSize',8);
savefig0(f,out,'q2_search_comparison');
end

function q3Communication(d,out,C)
r=d.routes; [~,ix]=sort(string({r.id})); r=r(ix); ids=string({r.id}); providers=unique(string({d.communication.provider}));
f=fig(1260,max(680,23*numel(r))); ax=axes0(f); hold(ax,'on');
for k=1:numel(d.communication)
    it=d.communication(k); lane=find(ids==string(it.route)); if isempty(lane), continue; end
    if strcmp(it.provider,'G01'), col=C.gray; elseif strcmp(it.provider,'R01'), col=C.A; else, col=C.orange; end
    plot(ax,[it.start it.end]/60,[lane lane],'Color',col,'LineWidth',5,'HandleVisibility','off');
end
for g=1:numel(providers), name=providers(g); if name=="G01", label='调度中心直连'; elseif name=="R01", label='R01中继'; else, label='R02中继'; end
    if name=="G01", col=C.gray; elseif name=="R01", col=C.A; else, col=C.orange; end
    plot(ax,nan,nan,'Color',col,'LineWidth',4,'DisplayName',label);
end
yticks(ax,1:numel(r)); yticklabels(ax,ids); set(ax,'YDir','reverse'); xlabel(ax,'时刻 / min'); ylabel(ax,'运输架次'); legend(ax,'Location','northeastoutside'); title(ax,'运输任务通信提供方时间轴'); savefig0(f,out,'q3_communication_timeline');
end
function q3Margins(d,out,C)
m=[d.communication.margin]; direct=string({d.communication.provider})=="G01";
f=fig(900,500); ax=axes0(f); histogram(ax,m(direct),28,'FaceColor',C.gray,'FaceAlpha',.72,'DisplayName','调度中心直连');
histogram(ax,m(~direct),28,'FaceColor',C.A,'FaceAlpha',.68,'DisplayName','中继链路'); xline(ax,0,'--','Color',C.orange,'DisplayName','链路可行阈值');
xline(ax,min(m),':','Color',C.C,'DisplayName',sprintf('最小证书裕量 %.2f dB',min(m))); xlabel(ax,'链路裕量 / dB'); ylabel(ax,'认证区间数'); legend(ax,'Location','best'); title(ax,'通信链路裕量分布'); savefig0(f,out,'q3_link_margin');
end
function q3RelaySoc(d,out,C)
r=d.relays; [~,ix]=sort(string({r.id})); r=r(ix); f=fig(900,500); ax=axes0(f); hold(ax,'on');
for k=1:numel(r)
    site=char(r(k).site);
    if strcmp(site,'E'), col=[117 112 179]/255; else, col=C.W; end
    bar(ax,k,r(k).soc*100,'FaceColor',col);
end
yline(ax,20,'--','Color',C.orange,'DisplayName','最低返航储备 20%'); xticks(ax,1:numel(r)); xticklabels(ax,{r.id}); xlabel(ax,'中继任务'); ylabel(ax,'返航剩余电量 / %'); title(ax,'中继无人机返航电量'); savefig0(f,out,'q3_relay_soc');
end
function q3Compare(a,b,out)
f=fig(1100,420); tiledlayout(f,1,3,'TileSpacing','compact'); vals={[a.summary.energy b.summary.energy],[a.summary.makespan/60 b.summary.makespan/60],[a.summary.count b.summary.count]}; labs={'总能耗 / kWh','完工时间 / min','运输架次数'};
for k=1:3, ax=nexttile; b0=bar(ax,vals{k},'FaceColor','flat'); b0.CData=[0 114 178;213 94 0]/255; xticks(ax,1:2); xticklabels(ax,{'问题二','问题三'}); ylabel(ax,labs{k}); grid(ax,'on'); ax.GridAlpha=.18; end
savefig0(f,out,'q3_q2_q3_comparison');
end

function labs=resourceLabels(), labs={'A型机','B型机','C型机','A型电池','B型电池','C型电池','中继无人机','中继电池'}; end
function q4Resources(d,out)
labs=resourceLabels(); f=fig(1200,520); ax=axes0(f); x=1:numel(labs); bar(ax,x,[d.schemes.x2.selected.total(:) d.schemes.x3.selected.total(:)],'grouped'); hold(ax,'on'); scatter(ax,x,d.inventory,36,'kd','filled','DisplayName','现有库存');
xticks(ax,x); xticklabels(ax,labs); xtickangle(ax,25); ylabel(ax,'资源数量'); legend(ax,{'2组需求','3组需求','现有库存'},'Location','best'); title(ax,'分组方案资源需求与现有库存'); savefig0(f,out,'q4_resource_demand');
end
function q4Workload(d,out,C)
f=fig(1000,470); tiledlayout(f,1,2,'TileSpacing','compact');
types='ABC';
for n=2:3, g=d.schemes.(sprintf('x%d',n)).selected.groups; ax=nexttile; vals=[g.work]/3600; b=bar(ax,vals,'FaceColor','flat');
    for k=1:numel(g), b.CData(k,:)=tc(C,types(k)); text(ax,k,vals(k),sprintf(' %d箱',g(k).boxes),'HorizontalAlignment','center','FontSize',8); end
    xticks(ax,1:numel(g)); xticklabels(ax,compose('第%d组',1:numel(g))); ylabel(ax,'累计飞行工作时长 / h'); title(ax,sprintf('%d组方案',n)); grid(ax,'on'); ax.GridAlpha=.18;
end
savefig0(f,out,'q4_workload');
end
function q4Deficit(d,out)
labs=resourceLabels(); f=fig(1180,490); ax=axes0(f); x=1:numel(labs); bar(ax,x,[d.schemes.x2.selected.deficit(:) d.schemes.x3.selected.deficit(:)],'grouped');
xticks(ax,x); xticklabels(ax,labs); xtickangle(ax,25); ylabel(ax,'缺少数量'); ylim(ax,[0 inf]); legend(ax,{'2组方案','3组方案'},'Location','best'); title(ax,'不同分组方案的库存缺口'); savefig0(f,out,'q4_resource_deficit');
end
