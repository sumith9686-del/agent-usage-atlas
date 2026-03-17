"""HTML template and client-side chart rendering for the dashboard."""
from __future__ import annotations

import json


def build_html(data: dict | None = None, *, poll_interval_ms: int = 0) -> str:
    payload = "null" if data is None else json.dumps(data, ensure_ascii=False).replace("</", r"<\/")
    interval = max(1000, int(poll_interval_ms or 0))
    return _template().replace("__DATA__", payload).replace("__POLL_MS__", str(interval))


def _template() -> str:
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Usage Atlas</title>
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@fortawesome/fontawesome-free@6/css/all.min.css" media="print" onload="this.media='all'">
<script src="https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0d1016;
  --surface:rgba(255,255,255,.04);
  --surface-strong:rgba(255,255,255,.07);
  --border:rgba(255,255,255,.08);
  --text:#ece7df;
  --text-secondary:rgba(255,255,255,.7);
  --text-muted:rgba(255,255,255,.42);
  --accent:#f0b866;
  --codex:#ff8a50;
  --claude:#ffd43b;
  --cursor:#748ffc;
  --uncached:#f4b183;
  --cache-read:#51cf66;
  --cache-write:#b197fc;
  --output:#74c0fc;
  --reason:#e599f7;
  --cost:#ff6b6b;
  --radius:14px;
  --radius-sm:8px;
  --shadow:0 18px 70px rgba(0,0,0,.26);
}
body{
  min-height:100vh;
  color:var(--text);
  background:
    radial-gradient(circle at top left, rgba(255,138,80,.16), transparent 26%),
    radial-gradient(circle at top right, rgba(116,192,252,.12), transparent 24%),
    linear-gradient(180deg, #131722 0%, #0d1016 58%, #0b0d12 100%);
  font:14px/1.6 Inter,-apple-system,BlinkMacSystemFont,"PingFang SC","Helvetica Neue",sans-serif;
  -webkit-font-smoothing:antialiased;
}
.page{max-width:1460px;margin:0 auto;padding:20px 12px 40px}
.g{display:grid;gap:12px}
.g2{grid-template-columns:1fr 1fr}
.g3{grid-template-columns:repeat(3,1fr)}
.g4{grid-template-columns:repeat(4,1fr)}
.g-wide{grid-template-columns:2.1fr 1fr}
.g-story{grid-template-columns:1.15fr .85fr}
.mt{margin-top:12px}
.p{
  background:linear-gradient(180deg,rgba(255,255,255,.05),rgba(255,255,255,.025));
  border:1px solid var(--border);
  border-radius:var(--radius);
  padding:16px;
  box-shadow:var(--shadow);
}
.hero-wrap{backdrop-filter:blur(22px)}
.hero-wrap{position:relative;overflow:hidden;padding:28px 24px}
.hero-wrap::before{
  content:"";
  position:absolute;inset:0;
  background:
    radial-gradient(circle at 16% 18%, rgba(255,138,80,.18), transparent 18%),
    radial-gradient(circle at 86% 12%, rgba(240,184,102,.18), transparent 20%),
    linear-gradient(135deg, rgba(255,255,255,.02), transparent 55%);
  pointer-events:none;
}
/* ── Toast notification ── */
.toast{
  position:fixed;top:16px;left:50%;transform:translateX(-50%) translateY(-80px);
  z-index:9999;padding:10px 22px;border-radius:999px;
  font-size:12px;font-weight:600;letter-spacing:.02em;
  color:#fff;pointer-events:none;opacity:0;
  transition:transform .4s cubic-bezier(.16,1,.3,1), opacity .4s ease;
  box-shadow:0 8px 32px rgba(0,0,0,.45);
  display:flex;align-items:center;gap:8px;
  backdrop-filter:blur(16px);
}
.toast.show{transform:translateX(-50%) translateY(0);opacity:1}
.toast.ok{background:rgba(81,207,102,.18);border:1px solid rgba(81,207,102,.35);color:#a3e635}
.toast.err{background:rgba(255,107,107,.18);border:1px solid rgba(255,107,107,.35);color:#ff6b6b}
.toast.info{background:rgba(116,192,252,.15);border:1px solid rgba(116,192,252,.3);color:#74c0fc}
.toast .spinner{width:14px;height:14px;border:2px solid rgba(255,255,255,.2);border-top-color:currentColor;border-radius:50%;animation:spin .6s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}

/* ── Live badge ── */
.live-badge{
  display:inline-flex;align-items:center;gap:5px;
  margin-left:auto;padding:3px 10px;border-radius:999px;
  font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
  transition:background .3s,color .3s;
}
.live-badge.connected{background:rgba(81,207,102,.15);color:#51cf66}
.live-badge.connected .dot{background:#51cf66;box-shadow:0 0 6px #51cf66}
.live-badge.disconnected{background:rgba(255,107,107,.15);color:#ff6b6b}
.live-badge.disconnected .dot{background:#ff6b6b}
.live-badge.off{background:rgba(255,255,255,.06);color:var(--text-muted)}
.live-badge.off .dot{background:var(--text-muted)}
.dot{width:6px;height:6px;border-radius:50%;flex-shrink:0}
.live-badge.connected .dot{animation:pulse-dot 2s ease-in-out infinite}
@keyframes pulse-dot{0%,100%{opacity:1}50%{opacity:.35}}

.lang-btn{
  display:inline-flex;align-items:center;gap:4px;
  margin-left:8px;padding:3px 10px;border-radius:999px;
  font-size:10px;font-weight:700;letter-spacing:.08em;
  cursor:pointer;border:1px solid rgba(255,255,255,.12);background:rgba(255,255,255,.06);
  color:var(--text-muted);transition:all .2s;user-select:none;
}
.lang-btn:hover{background:rgba(255,255,255,.12);color:var(--text)}
.range-tabs{display:flex;gap:4px;margin-top:10px}
.range-tab{
  padding:5px 14px;border-radius:6px;font-size:12px;font-weight:700;
  cursor:pointer;border:1px solid rgba(255,255,255,.08);background:transparent;
  color:var(--text-muted);transition:all .2s;user-select:none;letter-spacing:.02em;
}
.range-tab:hover{background:rgba(255,255,255,.06);color:var(--text)}
.range-tab.active{background:var(--accent);color:#000;border-color:var(--accent)}

.eyebrow{
  display:flex;align-items:center;gap:8px;
  color:var(--accent);
  font-size:11px;font-weight:800;letter-spacing:.14em;text-transform:uppercase;
}
h1{
  margin-top:10px;
  max-width:13ch;
  font-size:clamp(28px,4vw,48px);
  line-height:.95;
  font-weight:900;
  letter-spacing:-.045em;
  background:linear-gradient(135deg,var(--text),var(--accent));
  -webkit-background-clip:text;
  -webkit-text-fill-color:transparent;
}
.hero-copy{margin-top:10px;max-width:62ch;color:var(--text-secondary);font-size:13px}
.chips{display:flex;gap:8px;flex-wrap:wrap;margin-top:12px}
.chip{
  display:inline-flex;align-items:center;gap:7px;
  padding:8px 14px;border-radius:999px;
  background:rgba(255,255,255,.06);
  border:1px solid var(--border);
  color:var(--text-secondary);font-size:12px
}
.side{display:grid;gap:12px;align-content:start}
.sc,.cc{
  background:rgba(255,255,255,.04);
  border:1px solid var(--border);
  border-radius:var(--radius-sm);
  padding:14px;
}
.sc .lbl,.metric-k{
  color:var(--text-muted);
  font-size:10px;
  font-weight:700;
  letter-spacing:.11em;
  text-transform:uppercase;
}
.sc .val,.metric-v{font-size:22px;font-weight:800;letter-spacing:-.03em;margin-top:6px}
.sc .hint,.tiny{color:var(--text-secondary);font-size:12px;margin-top:8px}
.divider{
  display:flex;align-items:center;gap:12px;
  margin:20px 0 12px;
  color:var(--text-muted);
  font-size:11px;font-weight:800;letter-spacing:.14em;text-transform:uppercase;
}
.divider::after{content:"";flex:1;height:1px;background:var(--border)}
.sh{display:flex;justify-content:space-between;align-items:baseline;gap:12px;margin-bottom:8px}
.sh h2{font-size:16px;font-weight:800;letter-spacing:-.02em}
.sh span{color:var(--text-muted);font-size:12px}
.src{position:relative;overflow:hidden}
.src::before,.cc::before{
  content:"";
  position:absolute;top:0;left:0;right:0;height:3px;
}
.src.codex::before{background:linear-gradient(90deg,var(--codex),transparent)}
.src.claude::before{background:linear-gradient(90deg,var(--claude),transparent)}
.src.cursor::before{background:linear-gradient(90deg,var(--cursor),transparent)}
.cc.cost::before{background:linear-gradient(90deg,var(--cost),transparent)}
.cc.save::before{background:linear-gradient(90deg,var(--cache-read),transparent)}
.src .title{display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;font-weight:700;font-size:14px}
.pill{
  padding:4px 10px;border-radius:999px;border:1px solid var(--border);
  color:var(--text-muted);font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
}
.src .big{font-size:32px;font-weight:900;letter-spacing:-.03em}
.src .sub{font-size:11px;color:var(--text-muted);margin-top:2px}
.mg{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:14px}
.mi{
  padding:10px 12px;border-radius:10px;
  background:rgba(255,255,255,.035);
  border:1px solid rgba(255,255,255,.05);
}
.mi .k{color:var(--text-muted);font-size:10px;font-weight:700;letter-spacing:.08em;text-transform:uppercase}
.mi .v{margin-top:4px;font-size:14px;font-weight:700}
.cc .big{font-size:24px;font-weight:900;letter-spacing:-.03em;margin-top:8px}
.chart{width:100%;height:300px}
.chart.tall{height:360px}
.chart.sm{height:280px}
.chart.short{height:240px}
.story{display:grid;gap:10px}
.si,.note{
  display:flex;gap:12px;align-items:flex-start;
  padding:12px 14px;border-radius:12px;
  background:rgba(255,255,255,.04);
  border:1px solid rgba(255,255,255,.06);
}
.si i,.note i{margin-top:3px;color:var(--accent)}
.nl{display:grid;gap:10px;margin-top:14px}
.legend{display:flex;gap:12px;flex-wrap:wrap;margin-top:14px;color:var(--text-secondary);font-size:12px}
.dot{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:6px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{text-align:left;padding:8px 8px;border-bottom:1px solid var(--border)}
th{color:var(--text-muted);font-size:10px;font-weight:800;letter-spacing:.12em;text-transform:uppercase}
td{color:var(--text-secondary)}
tr:hover td{background:rgba(255,255,255,.02)}
.footer{margin-top:16px;color:var(--text-muted);font-size:11px;line-height:1.65}
.footer code{
  padding:2px 6px;border-radius:6px;
  background:rgba(255,255,255,.06);
  color:var(--text-secondary);
}
@media (max-width:1180px){
  .g2,.g3,.g4,.g-wide,.g-story{grid-template-columns:1fr}
  .page{padding:16px 0 36px;width:calc(100vw - 24px)}
  .p{padding:14px}
  .hero-wrap{padding:24px 18px}
}
</style>
</head>
<body>
<div class="toast" id="toast"></div>
<main class="page">
  <section class="g g-wide">
    <article class="p hero-wrap">
      <div class="eyebrow"><i class="fa-solid fa-chart-line"></i> Agent Usage Atlas<span class="live-badge off" id="live-badge"><span class="dot"></span>Static</span><button class="lang-btn" id="lang-btn" onclick="toggleLang()">&#127760; ZH</button></div>
      <div class="range-tabs" id="range-tabs"></div>
      <h1 id="hero-title"></h1>
      <p class="hero-copy" id="hero-copy"></p>
      <div class="chips" id="hero-chips"></div>
    </article>
    <aside class="side" id="summary-side"></aside>
  </section>

  <div class="divider"><i class="fa-solid fa-layer-group"></i> <span data-i18n="divSources"></span></div>
  <section class="g g3" id="source-cards"></section>

  <div class="divider"><i class="fa-solid fa-dollar-sign"></i> <span data-i18n="divCost"></span></div>
  <section class="g g4" id="cost-cards"></section>
  <section class="g g-wide mt">
    <article class="p"><div class="sh"><h2 data-i18n="chartDailyCost"></h2><span data-i18n="chartDailyCostSub"></span></div><div class="chart tall" id="daily-cost-chart"></div></article>
    <article class="p"><div class="sh"><h2 data-i18n="chartCostBreakdown"></h2><span data-i18n="chartCostBreakdownSub"></span></div><div class="chart tall" id="cost-breakdown-chart"></div></article>
  </section>
  <section class="g g2 mt">
    <article class="p"><div class="sh"><h2 data-i18n="chartModelCost"></h2><span data-i18n="chartModelCostSub"></span></div><div class="chart sm" id="model-cost-chart"></div></article>
    <article class="p"><div class="sh"><h2 data-i18n="chartCostSankey"></h2><span data-i18n="chartCostSankeySub"></span></div><div class="chart sm" id="cost-sankey-chart"></div></article>
  </section>
  <section class="g g2 mt">
    <article class="p"><div class="sh"><h2 data-i18n="chartDailyCostType"></h2><span data-i18n="chartDailyCostTypeSub"></span></div><div class="chart tall" id="daily-cost-type-chart"></div></article>
    <article class="p"><div class="sh"><h2 data-i18n="chartCostCalendar"></h2><span data-i18n="chartCostCalendarSub"></span></div><div class="chart sm" id="cost-calendar-chart"></div></article>
  </section>

  <div class="divider"><i class="fa-solid fa-chart-bar"></i> <span data-i18n="divTokens"></span></div>
  <section class="g g-story">
    <article class="p"><div class="sh"><h2 data-i18n="chartStory"></h2><span data-i18n="chartStorySub"></span></div><div class="story" id="story-list"></div></article>
    <article class="p"><div class="sh"><h2 data-i18n="chartRose"></h2><span data-i18n="chartRoseSub"></span></div><div class="chart short" id="rose-chart"></div></article>
  </section>
  <section class="g g-wide mt">
    <article class="p">
      <div class="sh"><h2 data-i18n="chartDailyToken"></h2><span data-i18n="chartDailyTokenSub"></span></div>
      <div class="chart tall" id="daily-token-chart"></div>
      <div class="legend" id="token-legend"></div>
    </article>
    <article class="p">
      <div class="sh"><h2 data-i18n="chartTokenSankey"></h2><span data-i18n="chartTokenSankeySub"></span></div>
      <div class="chart tall" id="token-sankey-chart"></div>
      <div class="nl" id="source-notes"></div>
    </article>
  </section>

  <div class="divider"><i class="fa-solid fa-clock"></i> <span data-i18n="divActivity"></span></div>
  <section class="g g2">
    <article class="p"><div class="sh"><h2 data-i18n="chartHeatmap"></h2><span data-i18n="chartHeatmapSub"></span></div><div class="chart tall" id="heatmap-chart"></div></article>
    <article class="p"><div class="sh"><h2 data-i18n="chartSourceRadar"></h2><span data-i18n="chartSourceRadarSub"></span></div><div class="chart tall" id="source-radar-chart"></div></article>
  </section>
  <section class="g g2 mt">
    <article class="p"><div class="sh"><h2 data-i18n="chartTokenCalendar"></h2><span data-i18n="chartTokenCalendarSub"></span></div><div class="chart sm" id="token-calendar-chart"></div></article>
    <article class="p"><div class="sh"><h2 data-i18n="chartTimeline"></h2><span data-i18n="chartTimelineSub"></span></div><div class="chart sm" id="timeline-chart"></div></article>
  </section>
  <section class="g g2 mt">
    <article class="p"><div class="sh"><h2 data-i18n="chartBubble"></h2><span data-i18n="chartBubbleSub"></span></div><div class="chart sm" id="bubble-chart"></div></article>
    <article class="p"><div class="sh"><h2 data-i18n="chartTempo"></h2><span data-i18n="chartTempoSub"></span></div><div class="chart sm" id="tempo-chart"></div><div class="nl" id="tempo-notes"></div></article>
  </section>

  <div class="divider"><i class="fa-solid fa-wrench"></i> <span data-i18n="divTooling"></span></div>
  <section class="g g2">
    <article class="p"><div class="sh"><h2 data-i18n="chartToolRank"></h2><span data-i18n="chartToolRankSub"></span></div><div class="chart sm" id="tool-ranking-chart"></div></article>
    <article class="p"><div class="sh"><h2 data-i18n="chartToolDensity"></h2><span data-i18n="chartToolDensitySub"></span></div><div class="chart sm" id="tool-density-chart"></div></article>
  </section>
  <section class="g g2 mt">
    <article class="p"><div class="sh"><h2 data-i18n="chartToolBigram"></h2><span data-i18n="chartToolBigramSub"></span></div><div class="chart sm" id="tool-bigram-chart"></div></article>
    <article class="p"><div class="sh"><h2 data-i18n="chartTopCmd"></h2><span data-i18n="chartTopCmdSub"></span></div><div class="chart sm" id="top-commands-chart"></div></article>
  </section>
  <section class="g g2 mt">
    <article class="p"><div class="sh"><h2 data-i18n="chartCmdSuccess"></h2><span data-i18n="chartCmdSuccessSub"></span></div><div class="chart sm" id="command-success-chart"></div></article>
    <article class="p"><div class="sh"><h2 data-i18n="chartEfficiency"></h2><span data-i18n="chartEfficiencySub"></span></div><div class="chart sm" id="efficiency-chart"></div></article>
  </section>

  <div class="divider"><i class="fa-solid fa-diagram-project"></i> <span data-i18n="divProjects"></span></div>
  <section class="g g2">
    <article class="p"><div class="sh"><h2 data-i18n="chartProjectRank"></h2><span data-i18n="chartProjectRankSub"></span></div><div class="chart sm" id="project-ranking-chart"></div></article>
    <article class="p"><div class="sh"><h2 data-i18n="chartFileTypes"></h2><span data-i18n="chartFileTypesSub"></span></div><div class="chart sm" id="file-types-chart"></div></article>
  </section>
  <section class="g g2 mt">
    <article class="p"><div class="sh"><h2 data-i18n="chartBranch"></h2><span data-i18n="chartBranchSub"></span></div><div class="chart sm" id="branch-activity-chart"></div></article>
    <article class="p"><div class="sh"><h2 data-i18n="chartProductivity"></h2><span data-i18n="chartProductivitySub"></span></div><div class="chart sm" id="productivity-chart"></div></article>
  </section>
  <section class="g g2 mt">
    <article class="p"><div class="sh"><h2 data-i18n="chartBurnRate"></h2><span data-i18n="chartBurnRateSub"></span></div><div class="chart sm" id="burn-rate-chart"></div></article>
    <article class="p"><div class="sh"><h2 data-i18n="chartCostPerTool"></h2><span data-i18n="chartCostPerToolSub"></span></div><div class="chart sm" id="cost-per-tool-chart"></div></article>
  </section>

  <div class="divider"><i class="fa-solid fa-magnifying-glass-chart"></i> <span data-i18n="divSession"></span></div>
  <section class="g g2">
    <article class="p"><div class="sh"><h2 data-i18n="chartSessionDur"></h2><span data-i18n="chartSessionDurSub"></span></div><div class="chart sm" id="session-duration-chart"></div></article>
    <article class="p"><div class="sh"><h2 data-i18n="chartModelRadar"></h2><span data-i18n="chartModelRadarSub"></span></div><div class="chart sm" id="model-radar-chart"></div></article>
  </section>

  <div class="divider"><i class="fa-solid fa-gauge-high"></i> <span data-i18n="divExtended"></span></div>
  <section class="g g2">
    <article class="p"><div class="sh"><h2 data-i18n="chartTurnDur"></h2><span data-i18n="chartTurnDurSub"></span></div><div class="chart sm" id="turn-dur-chart"></div></article>
    <article class="p"><div class="sh"><h2 data-i18n="chartDailyTurnDur"></h2><span data-i18n="chartDailyTurnDurSub"></span></div><div class="chart sm" id="daily-turn-dur-chart"></div></article>
  </section>
  <section class="g g2 mt">
    <article class="p"><div class="sh"><h2 data-i18n="chartTaskRate"></h2><span data-i18n="chartTaskRateSub"></span></div><div class="chart sm" id="task-rate-chart"></div></article>
    <article class="p"><div class="sh"><h2 data-i18n="chartCodegenModel"></h2><span data-i18n="chartCodegenModelSub"></span></div><div class="chart sm" id="codegen-model-chart"></div></article>
  </section>
  <section class="g g2 mt">
    <article class="p"><div class="sh"><h2 data-i18n="chartCodegenDaily"></h2><span data-i18n="chartCodegenDailySub"></span></div><div class="chart sm" id="codegen-daily-chart"></div></article>
    <article class="p"><div class="sh"><h2 data-i18n="chartAiContrib"></h2><span data-i18n="chartAiContribSub"></span></div><div class="chart sm" id="ai-contribution-chart"></div></article>
  </section>

  <div class="divider"><i class="fa-solid fa-list-ol"></i> <span data-i18n="divLeaderboard"></span></div>
  <section>
    <article class="p">
      <table id="session-table"></table>
      <div class="footer" id="footer-text"></div>
      </div>
    </article>
  </section>
</main>

<script>
let data = __DATA__;

/* ── i18n ── */
let lang = localStorage.getItem('atlas-lang') || 'zh';
const I18N = {
  zh: {
    heroTitle: '三个 Agent 栈的联赛积分榜',
    heroCopyTpl: '统计窗口 {start} → {end}。累计处理 {tokens} tokens，估算花费 {cost}，缓存命中占 {cache}。这不是 usage report，是 Agent 生产力的赛后复盘。',
    heroWaiting: '等待 API 返回数据... 如果服务未启动，请先运行 --serve。',
    heroNoData: '缺少可用数据。',
    chipTokens: ' tokens', chipCost: ' cost', chipCached: ' cached', chipTools: ' tool calls',
    lblTotalTokens: 'Total Tokens', lblEstCost: 'Estimated Cost', lblCacheStack: 'Cache Stack', lblMedianSession: 'Median Session',
    hintTotalTokens: '日均 {avg}，峰值 {peak}',
    hintEstCost: '日均 {avg}，30 天投影 {proj}',
    hintCacheStack: '省下 {save}，命中率 {rate}',
    hintMedianSession: '{min} 分钟 / {cost}',
    lblTotalCost: 'Total Cost', lblDailyAvg: 'Daily Average', lblCostPerMsg: 'Cost / Message', lblCacheSavings: 'Cache Savings',
    hintTotalCost: '{days} 天累计',
    hintDailyAvg: '峰值 {peak}: {cost}',
    hintCostPerMsg: '中位 session {cost}',
    hintCacheSavings: '节省 {pct}',
    pillTokenTracked: 'token-tracked', pillActivityOnly: 'activity-only',
    subTrackedTokens: 'tracked tokens', subMessagesOnly: 'messages only',
    lblSessions: 'Sessions', lblCost: 'Cost', lblTopModel: 'Top Model', lblCache: 'Cache',
    divSources: 'Sources', divCost: 'Cost Analysis', divTokens: 'Token Analytics', divActivity: 'Activity Patterns',
    divTooling: 'Tooling & Commands', divProjects: 'Projects & Productivity', divSession: 'Session Deep Dive',
    divExtended: 'Extended Analytics', divLeaderboard: 'Session Leaderboard',
    chartDailyCost: '每日花费趋势', chartDailyCostSub: '按来源堆叠 + 累计花费线',
    chartCostBreakdown: '花费结构拆解', chartCostBreakdownSub: '钱花在哪种 Token 上',
    chartModelCost: '模型花费排行', chartModelCostSub: '哪些模型最烧钱',
    chartCostSankey: '来源花费桑基图', chartCostSankeySub: '从来源流到各类花费',
    chartDailyCostType: '每日花费结构', chartDailyCostTypeSub: '哪种 Token 最烧钱',
    chartCostCalendar: '花费日历', chartCostCalendarSub: '每天花了多少钱',
    chartStory: '剧情梗概', chartStorySub: '把数字翻译成人话',
    chartRose: '来源玫瑰图', chartRoseSub: '体量 + 气质一起看',
    chartDailyToken: '每日 Token 结构', chartDailyTokenSub: '堆叠柱 + 累计线',
    chartTokenSankey: 'Token 流向桑基图', chartTokenSankeySub: '从来源流到各类 token 桶',
    chartHeatmap: '活跃热区', chartHeatmapSub: '星期 × 小时，越深越忙',
    chartSourceRadar: '来源能力雷达', chartSourceRadarSub: '体量、缓存、输出、活跃度四维比较',
    chartTokenCalendar: 'Token 日历', chartTokenCalendarSub: '把高峰日钉在日历上',
    chartTimeline: 'Timeline', chartTimelineSub: '峰值、拐点与累计爬坡',
    chartBubble: 'Session 气泡图', chartBubbleSub: 'x=时长, y=token, 气泡=缓存',
    chartTempo: '小时节奏图', chartTempoSub: '24 小时内谁最爱开工',
    chartToolRank: '工具排行', chartToolRankSub: '按调用次数',
    chartToolDensity: '工具时段密度', chartToolDensitySub: '24h 分布',
    chartToolBigram: 'Tool Bigram Chord', chartToolBigramSub: '工具跳转关系图',
    chartTopCmd: 'Top Commands', chartTopCmdSub: '最常用命令',
    chartCmdSuccess: '命令成功率', chartCmdSuccessSub: '按天看 success vs fail',
    chartEfficiency: '效率指标', chartEfficiencySub: '推理比、缓存命中、tokens/message',
    chartProjectRank: '项目排行', chartProjectRankSub: '按 Token 量',
    chartFileTypes: '文件类型分布', chartFileTypesSub: '最常碰哪些扩展名',
    chartBranch: '分支活跃度', chartBranchSub: 'top branches by session count',
    chartProductivity: 'Productivity Score', chartProductivitySub: '0.3/0.2/0.3/0.2 复合分',
    chartBurnRate: 'Burn Rate Projection', chartBurnRateSub: '按近 7 天均值投影 30 天',
    chartCostPerTool: 'Cost / Tool Call', chartCostPerToolSub: '每天每次调用花多少钱',
    chartSessionDur: 'Session Duration Histogram', chartSessionDurSub: '会话时长分布',
    chartModelRadar: 'Model Radar Comparison', chartModelRadarSub: 'top 5 models on 5 axes',
    chartTurnDur: '响应时间分布', chartTurnDurSub: 'Turn Duration Histogram',
    chartDailyTurnDur: '每日响应时间', chartDailyTurnDurSub: '中位数趋势',
    chartTaskRate: '任务完成率', chartTaskRateSub: 'Codex task started vs completed',
    chartCodegenModel: 'Cursor 代码生成 · 模型', chartCodegenModelSub: '按模型的生成次数',
    chartCodegenDaily: 'Cursor 代码生成 · 趋势', chartCodegenDailySub: '每日生成次数',
    chartAiContrib: 'AI 代码贡献度', chartAiContribSub: 'AI vs Human lines in commits',
    legendUncached: 'Uncached Input', legendCacheRead: 'Cache Read', legendCacheWrite: 'Cache Write', legendOutputReason: 'Output + Reason',
    footerText: '数据源：Codex <code>~/.codex</code> · Claude <code>~/.claude/projects</code> · Cursor transcript 仅统计活动消息<br>花费为基于公开 API 定价的估算值 · 图表渲染使用 <code>Apache ECharts</code>',
    rangeFrom: '从 {since}', rangeDays: '{days} 天', rangeWeek: '近 7 天', rangeToday: '今日',
    badgeLive: 'Live', badgeOffline: 'Offline', badgeStatic: 'Static',
    toastRefreshFail: '刷新失败：{err}', toastRefreshEmpty: '刷新返回数据为空或格式异常',
    toastPollOk: '轮询连接正常', toastPollFallback: '当前环境不支持 EventSource，回退轮询更新。',
    toastSseInit: 'SSE 已连接，等待实时更新。', toastSseReconnect: '实时连接中断，正在自动重连…',
    toastSseOk: 'SSE 连接正常', toastSseParseFail: 'SSE 数据解析失败：{err}',
    toastSseInitFail: 'SSE 初始化失败：{err}，回退轮询更新。',
    toastSwitchFail: '切换失败: {err}',
    seriesCumulative: 'Cumulative', seriesDailyTotal: 'Daily Total',
    seriesSuccess: 'Success', seriesFail: 'Fail',
    seriesReasonRatio: 'Reasoning Ratio', seriesCacheHitRate: 'Cache Hit Rate', seriesTokensPerMsg: 'Tokens / Message',
    seriesActualCum: 'Actual Cumulative', seriesProjCum: 'Projected Cumulative',
    seriesProductivity: 'Productivity',
    axisMinutes: 'Minutes', axisTokens: 'Tokens',
    radarTotal: 'Total', radarCache: 'Cache', radarOutput: 'Output', radarSessions: 'Sessions',
    radarInput: 'Input', radarCost: 'Cost', radarMsgs: 'Msgs',
    tblSource: 'Source', tblSession: 'Session', tblTokens: 'Tokens', tblCost: 'Cost', tblTools: 'Tools', tblModel: 'Model', tblWindow: 'Window',
    tblEvents: '{n} events', tblMin: '{n} min',
    lblCompleted: 'Completed', lblIncomplete: 'Incomplete',
    lblAiAdded: 'AI Added', lblHumanAdded: 'Human Added', lblAiDeleted: 'AI Deleted', lblHumanDeleted: 'Human Deleted',
  },
  en: {
    heroTitle: 'Agent Stack Scoreboard',
    heroCopyTpl: 'Window {start} → {end}. Processed {tokens} tokens, est. cost {cost}, cache hit ratio {cache}. Not a usage report — a post-game analysis of Agent productivity.',
    heroWaiting: 'Waiting for API data... If server is not running, start with --serve.',
    heroNoData: 'No data available.',
    chipTokens: ' tokens', chipCost: ' cost', chipCached: ' cached', chipTools: ' tool calls',
    lblTotalTokens: 'Total Tokens', lblEstCost: 'Estimated Cost', lblCacheStack: 'Cache Stack', lblMedianSession: 'Median Session',
    hintTotalTokens: 'daily avg {avg}, peak {peak}',
    hintEstCost: 'daily avg {avg}, 30d projection {proj}',
    hintCacheStack: 'saved {save}, hit rate {rate}',
    hintMedianSession: '{min} min / {cost}',
    lblTotalCost: 'Total Cost', lblDailyAvg: 'Daily Average', lblCostPerMsg: 'Cost / Message', lblCacheSavings: 'Cache Savings',
    hintTotalCost: '{days} days total',
    hintDailyAvg: 'peak {peak}: {cost}',
    hintCostPerMsg: 'median session {cost}',
    hintCacheSavings: 'saved {pct}',
    pillTokenTracked: 'token-tracked', pillActivityOnly: 'activity-only',
    subTrackedTokens: 'tracked tokens', subMessagesOnly: 'messages only',
    lblSessions: 'Sessions', lblCost: 'Cost', lblTopModel: 'Top Model', lblCache: 'Cache',
    divSources: 'Sources', divCost: 'Cost Analysis', divTokens: 'Token Analytics', divActivity: 'Activity Patterns',
    divTooling: 'Tooling & Commands', divProjects: 'Projects & Productivity', divSession: 'Session Deep Dive',
    divExtended: 'Extended Analytics', divLeaderboard: 'Session Leaderboard',
    chartDailyCost: 'Daily Cost Trend', chartDailyCostSub: 'stacked by source + cumulative line',
    chartCostBreakdown: 'Cost Breakdown', chartCostBreakdownSub: 'where the money goes by token type',
    chartModelCost: 'Model Cost Ranking', chartModelCostSub: 'which models cost the most',
    chartCostSankey: 'Source Cost Sankey', chartCostSankeySub: 'flow from source to cost category',
    chartDailyCostType: 'Daily Cost by Type', chartDailyCostTypeSub: 'which token type costs the most',
    chartCostCalendar: 'Cost Calendar', chartCostCalendarSub: 'daily spending heatmap',
    chartStory: 'Story Summary', chartStorySub: 'numbers translated to words',
    chartRose: 'Source Rose Chart', chartRoseSub: 'volume + character at a glance',
    chartDailyToken: 'Daily Token Breakdown', chartDailyTokenSub: 'stacked bars + cumulative line',
    chartTokenSankey: 'Token Flow Sankey', chartTokenSankeySub: 'flow from source to token bucket',
    chartHeatmap: 'Activity Heatmap', chartHeatmapSub: 'weekday × hour, darker = busier',
    chartSourceRadar: 'Source Radar', chartSourceRadarSub: 'volume, cache, output, sessions comparison',
    chartTokenCalendar: 'Token Calendar', chartTokenCalendarSub: 'pin peak days on the calendar',
    chartTimeline: 'Timeline', chartTimelineSub: 'peaks, inflections & cumulative climb',
    chartBubble: 'Session Bubble Chart', chartBubbleSub: 'x=duration, y=tokens, bubble=cache',
    chartTempo: 'Hourly Rhythm', chartTempoSub: 'who works at which hour',
    chartToolRank: 'Tool Ranking', chartToolRankSub: 'by call count',
    chartToolDensity: 'Tool Hour Density', chartToolDensitySub: '24h distribution',
    chartToolBigram: 'Tool Bigram Chord', chartToolBigramSub: 'tool transition graph',
    chartTopCmd: 'Top Commands', chartTopCmdSub: 'most used commands',
    chartCmdSuccess: 'Command Success Rate', chartCmdSuccessSub: 'daily success vs fail',
    chartEfficiency: 'Efficiency Metrics', chartEfficiencySub: 'reasoning ratio, cache hit, tokens/message',
    chartProjectRank: 'Project Ranking', chartProjectRankSub: 'by token volume',
    chartFileTypes: 'File Type Distribution', chartFileTypesSub: 'most touched extensions',
    chartBranch: 'Branch Activity', chartBranchSub: 'top branches by session count',
    chartProductivity: 'Productivity Score', chartProductivitySub: '0.3/0.2/0.3/0.2 composite',
    chartBurnRate: 'Burn Rate Projection', chartBurnRateSub: '30-day projection from 7-day avg',
    chartCostPerTool: 'Cost / Tool Call', chartCostPerToolSub: 'daily cost per tool invocation',
    chartSessionDur: 'Session Duration Histogram', chartSessionDurSub: 'session length distribution',
    chartModelRadar: 'Model Radar Comparison', chartModelRadarSub: 'top 5 models on 5 axes',
    chartTurnDur: 'Response Time Distribution', chartTurnDurSub: 'turn duration histogram',
    chartDailyTurnDur: 'Daily Response Time', chartDailyTurnDurSub: 'median trend',
    chartTaskRate: 'Task Completion Rate', chartTaskRateSub: 'Codex task started vs completed',
    chartCodegenModel: 'Cursor Codegen · Model', chartCodegenModelSub: 'generation count by model',
    chartCodegenDaily: 'Cursor Codegen · Trend', chartCodegenDailySub: 'daily generation count',
    chartAiContrib: 'AI Code Contribution', chartAiContribSub: 'AI vs Human lines in commits',
    legendUncached: 'Uncached Input', legendCacheRead: 'Cache Read', legendCacheWrite: 'Cache Write', legendOutputReason: 'Output + Reason',
    footerText: 'Data: Codex <code>~/.codex</code> · Claude <code>~/.claude/projects</code> · Cursor transcript counts activity messages only<br>Costs are estimates based on public API pricing · Charts rendered with <code>Apache ECharts</code>',
    rangeFrom: 'From {since}', rangeDays: '{days} days', rangeWeek: 'Last 7 days', rangeToday: 'Today',
    badgeLive: 'Live', badgeOffline: 'Offline', badgeStatic: 'Static',
    toastRefreshFail: 'Refresh failed: {err}', toastRefreshEmpty: 'Refresh returned empty or malformed data',
    toastPollOk: 'Polling connected', toastPollFallback: 'EventSource unavailable, falling back to polling.',
    toastSseInit: 'SSE connected, awaiting updates.', toastSseReconnect: 'Connection lost, reconnecting…',
    toastSseOk: 'SSE connected', toastSseParseFail: 'SSE parse error: {err}',
    toastSseInitFail: 'SSE init failed: {err}, falling back to polling.',
    toastSwitchFail: 'Switch failed: {err}',
    seriesCumulative: 'Cumulative', seriesDailyTotal: 'Daily Total',
    seriesSuccess: 'Success', seriesFail: 'Fail',
    seriesReasonRatio: 'Reasoning Ratio', seriesCacheHitRate: 'Cache Hit Rate', seriesTokensPerMsg: 'Tokens / Message',
    seriesActualCum: 'Actual Cumulative', seriesProjCum: 'Projected Cumulative',
    seriesProductivity: 'Productivity',
    axisMinutes: 'Minutes', axisTokens: 'Tokens',
    radarTotal: 'Total', radarCache: 'Cache', radarOutput: 'Output', radarSessions: 'Sessions',
    radarInput: 'Input', radarCost: 'Cost', radarMsgs: 'Msgs',
    tblSource: 'Source', tblSession: 'Session', tblTokens: 'Tokens', tblCost: 'Cost', tblTools: 'Tools', tblModel: 'Model', tblWindow: 'Window',
    tblEvents: '{n} events', tblMin: '{n} min',
    lblCompleted: 'Completed', lblIncomplete: 'Incomplete',
    lblAiAdded: 'AI Added', lblHumanAdded: 'Human Added', lblAiDeleted: 'AI Deleted', lblHumanDeleted: 'Human Deleted',
  }
};
function t(key, params) {
  let s = I18N[lang][key] || I18N.zh[key] || key;
  if (params) Object.keys(params).forEach(k => { s = s.replace('{' + k + '}', params[k]); });
  return s;
}
function applyI18n() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    const val = t(key);
    if (val.includes('<')) el.innerHTML = val;
    else el.textContent = val;
  });
}
function toggleLang() {
  lang = lang === 'zh' ? 'en' : 'zh';
  localStorage.setItem('atlas-lang', lang);
  document.getElementById('lang-btn').textContent = '\\u{1F310} ' + lang.toUpperCase();
  _numPrevValues = new WeakMap();
  isFirstRender = false;
  /* Force re-create DOM elements */
  ['chip-tokens','sv-tokens','cc-total','src-' + ((data && data.source_cards && data.source_cards[0]) || {}).source].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.removeAttribute('id');
  });
  applyI18n();
  renderDashboard();
}

const pageParams = new URLSearchParams(window.location.search);
const baseRangeParams = new URLSearchParams();
if (pageParams.get('days')) baseRangeParams.set('days', pageParams.get('days'));
if (pageParams.get('since')) baseRangeParams.set('since', pageParams.get('since'));
const baseInterval = pageParams.get('interval');
const defaultDays = Number(baseRangeParams.get('days')) || 30;
const defaultSince = baseRangeParams.get('since') || null;

/* Active range tab state */
let activeRangeKey = 'all'; /* 'all' | 'today' */
function _dateFmt(d) {
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}
function _buildParams(rangeKey) {
  const p = new URLSearchParams();
  if (rangeKey === 'today') {
    p.set('since', _dateFmt(new Date()));
  } else if (rangeKey === 'week') {
    p.set('days', '7');
  } else {
    if (defaultSince) p.set('since', defaultSince);
    else p.set('days', String(defaultDays));
  }
  if (baseInterval) p.set('interval', baseInterval);
  return p;
}
function _apiUrl(rangeKey) {
  const p = _buildParams(rangeKey);
  p.delete('interval');
  return '/api/dashboard' + (p.toString() ? `?${p}` : '');
}
function _streamUrl(rangeKey) {
  const p = _buildParams(rangeKey);
  return '/api/dashboard/stream' + (p.toString() ? `?${p}` : '');
}
let dashboardApiUrl = _apiUrl('all');
let dashboardStreamUrl = _streamUrl('all');
const isLiveMode = data === null;
let lastDashboardHash = '';
let refreshTimer = null;
let streamSource = null;
let isStreamConnected = false;
const charts = [];
const chartCache = {};
const fmtInt = n => Number(n || 0).toLocaleString('en-US');
const fmtShort = n => {
  const v = Number(n || 0);
  const a = Math.abs(v);
  if (a >= 1e9) return (v / 1e9).toFixed(2) + 'B';
  if (a >= 1e6) return (v / 1e6).toFixed(2) + 'M';
  if (a >= 1e3) return (v / 1e3).toFixed(1) + 'K';
  return String(Math.round(v));
};
const fmtPct = v => ((Number(v || 0) * 100).toFixed(1)) + '%';
const fmtUSD = v => {
  const value = Number(v || 0);
  if (value >= 1000) return '$' + value.toLocaleString('en-US', {maximumFractionDigits: 0});
  if (value >= 100) return '$' + value.toFixed(1);
  if (value >= 1) return '$' + value.toFixed(2);
  if (value >= 0.01) return '$' + value.toFixed(3);
  return '$' + value.toFixed(4);
};
const C = {
  Codex: '#ff8a50',
  Claude: '#ffd43b',
  Cursor: '#748ffc',
  uncached: '#f4b183',
  cacheRead: '#51cf66',
  cacheWrite: '#b197fc',
  output: '#74c0fc',
  reason: '#e599f7',
  cost: '#ff6b6b'
};
const TX = 'rgba(255,255,255,.68)';
const AX = 'rgba(255,255,255,.06)';
const BG = 'rgba(255,255,255,.03)';
const getTokenSources = () => (data && data.source_cards ? data.source_cards.filter(card => card.token_capable) : []);

/* ── Number transition animation ── */
let _numPrevValues = new WeakMap();
/* Build a locked formatter that keeps the same decimal places / scale throughout animation */
function _lockFmt(formatter, targetVal) {
  const targetStr = formatter(targetVal);
  if (formatter === fmtShort) {
    const a = Math.abs(targetVal);
    if (a >= 1e9) return v => (v / 1e9).toFixed(2) + 'B';
    if (a >= 1e6) return v => (v / 1e6).toFixed(2) + 'M';
    if (a >= 1e3) return v => (v / 1e3).toFixed(1) + 'K';
    return v => String(Math.round(v));
  }
  if (formatter === fmtUSD) {
    const av = Math.abs(targetVal);
    if (av >= 1000) return v => '$' + v.toLocaleString('en-US', {maximumFractionDigits: 0});
    if (av >= 100) return v => '$' + v.toFixed(1);
    if (av >= 1) return v => '$' + v.toFixed(2);
    if (av >= 0.01) return v => '$' + v.toFixed(3);
    return v => '$' + v.toFixed(4);
  }
  if (formatter === fmtPct) {
    return v => ((Number(v || 0) * 100).toFixed(1)) + '%';
  }
  if (formatter === fmtInt) {
    return v => Math.round(v).toLocaleString('en-US');
  }
  return formatter;
}
function animateNum(el, newRaw, formatter) {
  if (!el) return;
  const newVal = Number(newRaw) || 0;
  const oldVal = _numPrevValues.has(el) ? _numPrevValues.get(el) : newVal;
  _numPrevValues.set(el, newVal);
  if (isFirstRender || oldVal === newVal) {
    el.textContent = formatter(newVal);
    return;
  }
  const locked = _lockFmt(formatter, newVal);
  const duration = 600;
  const startTime = performance.now();
  const step = (now) => {
    const t = Math.min((now - startTime) / duration, 1);
    const ease = 1 - Math.pow(1 - t, 3);
    const cur = oldVal + (newVal - oldVal) * ease;
    el.textContent = locked(cur);
    if (t < 1) requestAnimationFrame(step);
    else { _numPrevValues.set(el, newVal); el.textContent = formatter(newVal); }
  };
  requestAnimationFrame(step);
}

let isFirstRender = true;
const THEME_BASE = {
  textStyle: {color: TX, fontFamily: 'Inter,-apple-system,PingFang SC,sans-serif'},
  tooltip: {
    backgroundColor: 'rgba(15,18,28,.92)',
    borderColor: 'rgba(255,255,255,.08)',
    borderWidth: 1,
    textStyle: {color: '#ece7df', fontSize: 12}
  }
};
const chartTheme = () => ({...THEME_BASE, animationDuration: isFirstRender ? 700 : 0});
const initChart = id => {
  if (chartCache[id]) {
    return chartCache[id];
  }
  const chart = echarts.init(document.getElementById(id), null, {renderer: 'canvas'});
  chartCache[id] = chart;
  charts.push(chart);
  return chart;
};

function clearCharts(){
  charts.forEach(chart => chart.dispose());
  charts.length = 0;
  Object.keys(chartCache).forEach(key => delete chartCache[key]);
}

/* ── Lazy chart rendering via IntersectionObserver ── */
const lazyQueue = [];
let lazyObserver = null;
const lazyRendered = new Set();
const lazyRenderFns = {};

function registerLazy(chartId, renderFn) {
  lazyRenderFns[chartId] = renderFn;
  lazyQueue.push({chartId, renderFn});
}

function flushLazy() {
  /* Re-render charts already visible (live-mode update) */
  if (lazyRendered.size > 0) {
    lazyRendered.forEach(id => {
      const fn = lazyRenderFns[id];
      if (fn) requestAnimationFrame(() => fn());
    });
    /* Observe any newly registered charts not yet seen */
    if (lazyObserver) {
      lazyQueue.forEach(item => {
        if (lazyRendered.has(item.chartId)) return;
        const el = document.getElementById(item.chartId);
        if (el) lazyObserver.observe(el);
      });
    }
    return;
  }

  /* First render: set up observer from scratch */
  if (typeof IntersectionObserver === 'undefined') {
    lazyQueue.forEach(item => item.renderFn());
    lazyQueue.length = 0;
    return;
  }

  if (lazyObserver) {
    lazyObserver.disconnect();
  }

  lazyObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (!entry.isIntersecting) return;
      const id = entry.target.id;
      if (lazyRendered.has(id)) return;
      lazyRendered.add(id);
      lazyObserver.unobserve(entry.target);
      const fn = lazyRenderFns[id];
      if (fn) {
        requestAnimationFrame(() => fn());
      }
    });
  }, {rootMargin: '200px 0px'});

  lazyQueue.forEach(item => {
    const el = document.getElementById(item.chartId);
    if (el) lazyObserver.observe(el);
  });
}

function setDashboard(nextData){
  if (!nextData || typeof nextData !== 'object') {
    return false;
  }
  const meta = nextData._meta;
  const hash = meta ? meta.generated_at : '';
  if (!data) {
    data = nextData;
    lastDashboardHash = hash;
    return true;
  }
  if (hash && hash === lastDashboardHash) {
    return false;
  }
  data = nextData;
  lastDashboardHash = hash;
  return true;
}

let toastTimer = null;
function showToast(message, type = 'info', duration = 3000){
  const el = document.getElementById('toast');
  if (!el) return;
  clearTimeout(toastTimer);
  el.className = 'toast ' + type;
  const icon = type === 'ok' ? '<i class="fa-solid fa-check"></i>'
    : type === 'err' ? '<i class="fa-solid fa-xmark"></i>'
    : '<span class="spinner"></span>';
  el.innerHTML = icon + ' ' + message;
  requestAnimationFrame(() => el.classList.add('show'));
  if (duration > 0) {
    toastTimer = setTimeout(() => el.classList.remove('show'), duration);
  }
}

function updateLiveBadge(state){
  const badge = document.getElementById('live-badge');
  if (!badge) return;
  badge.className = 'live-badge ' + state;
  badge.querySelector('.dot') || badge.insertAdjacentHTML('afterbegin','<span class="dot"></span>');
  const label = state === 'connected' ? 'Live' : state === 'disconnected' ? 'Offline' : 'Static';
  const spans = badge.childNodes;
  if (spans.length > 1) spans[spans.length - 1].textContent = label;
  else badge.appendChild(document.createTextNode(label));
}

function setStatus(message, isError = false){
  if (!message) return;
  if (data === null || isError) {
    const copy = document.getElementById('hero-copy');
    if (copy) {
      copy.textContent = message;
    }
  }
  if (isError) {
    showToast(message, 'err', 5000);
    console.error(`[dashboard] ${message}`);
  } else {
    console.debug(`[dashboard] ${message}`);
  }
}

function buildDashboardUrl(){
  return dashboardApiUrl;
}

function setStreamStatus(message, isError = false){
  if (isError) {
    isStreamConnected = false;
    updateLiveBadge('disconnected');
  } else {
    isStreamConnected = true;
    updateLiveBadge('connected');
  }
  setStatus(message, isError);
}

async function fetchDashboardOnce(){
  if (!isLiveMode) return;
  const url = buildDashboardUrl();
  try {
    const res = await fetch(url, {cache: 'no-store'});
    if (!res.ok) {
      setStreamStatus(`刷新失败：${res.status} ${res.statusText}`, true);
      return;
    }
    const nextData = await res.json();
    if (!nextData || typeof nextData !== 'object') {
      setStreamStatus('刷新返回数据为空或格式异常', true);
      return;
    }
    if (setDashboard(nextData)) {
      renderDashboard();
    }
    setStreamStatus('轮询连接正常');
  } catch (err) {
    setStreamStatus(`刷新失败：${String(err && err.message ? err.message : err)}`, true);
    return;
  }
}

function stopStream(){
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
  if (streamSource && streamSource.readyState !== EventSource.CLOSED) {
    streamSource.close();
  }
  streamSource = null;
}

function startPollingFallback(){
  if (!isLiveMode || refreshTimer !== null) return;
  setStreamStatus('当前环境不支持 EventSource，回退轮询更新。');
  fetchDashboardOnce();
  const intervalMs = Math.max(1000, Number(__POLL_MS__) || 5000);
  refreshTimer = setInterval(() => {
    void fetchDashboardOnce();
  }, intervalMs);
}

function startSseDashboard(){
  if (!isLiveMode || streamSource) return;
  if (typeof EventSource === 'undefined') {
    startPollingFallback();
    return;
  }

  try {
    streamSource = new EventSource(dashboardStreamUrl);
  } catch (err) {
    setStreamStatus(`SSE 初始化失败：${String(err && err.message ? err.message : err)}，回退轮询更新。`, true);
    startPollingFallback();
    return;
  }

  streamSource.onopen = () => {
    setStreamStatus('SSE 已连接，等待实时更新。');
  };

  streamSource.onerror = () => {
    setStreamStatus('实时连接中断，正在自动重连…', true);
  };

  streamSource.onmessage = event => {
    try {
      const nextData = JSON.parse(event.data);
      if (setDashboard(nextData)) {
        renderDashboard();
      }
      setStreamStatus('SSE 连接正常');
    } catch (err) {
      setStreamStatus(`SSE 数据解析失败：${String(err && err.message ? err.message : err)}`, true);
    }
  };
}

function renderHero(){
  document.getElementById('hero-title').textContent = t('heroTitle');
  if (!data || !data.totals) {
    document.getElementById('hero-copy').textContent = t('heroWaiting');
    return;
  }
  const T = data.totals;
  document.getElementById('hero-copy').textContent = t('heroCopyTpl', {
    start: data.range.start_local, end: data.range.end_local,
    tokens: fmtShort(T.grand_total), cost: fmtUSD(T.grand_cost), cache: fmtPct(T.cache_ratio)
  });

  const chipsEl = document.getElementById('hero-chips');
  const chipDefs = [
    {id: 'chip-tokens', icon: 'fa-fire', color: 'var(--codex)', value: T.grand_total, fmt: fmtShort, suffix: t('chipTokens')},
    {id: 'chip-cost', icon: 'fa-dollar-sign', color: 'var(--cost)', value: T.grand_cost, fmt: fmtUSD, suffix: t('chipCost')},
    {id: 'chip-cache', icon: 'fa-database', color: 'var(--cache-read)', value: T.cache_ratio, fmt: fmtPct, suffix: t('chipCached')},
    {id: 'chip-tools', icon: 'fa-wrench', color: 'var(--accent)', value: T.tool_call_total, fmt: fmtInt, suffix: t('chipTools')}
  ];
  if (!document.getElementById('chip-tokens')) {
    chipsEl.innerHTML = chipDefs.map(c =>
      `<span class="chip"><i class="fa-solid ${c.icon}" style="color:${c.color}"></i><span id="${c.id}"></span>${c.suffix}</span>`
    ).join('');
  }
  chipDefs.forEach(c => animateNum(document.getElementById(c.id), c.value, c.fmt));

  const cardDefs = [
    {id: 'sv-tokens', label: t('lblTotalTokens'), value: T.grand_total, fmt: fmtShort, hint: t('hintTotalTokens', {avg: fmtShort(T.average_per_day), peak: T.peak_day_label})},
    {id: 'sv-cost', label: t('lblEstCost'), value: T.grand_cost, fmt: fmtUSD, hint: t('hintEstCost', {avg: fmtUSD(T.average_cost_per_day), proj: fmtUSD(T.burn_rate_projection_30d)})},
    {id: 'sv-cache', label: t('lblCacheStack'), value: T.cache_read + T.cache_write, fmt: fmtShort, hint: t('hintCacheStack', {save: fmtUSD(T.cache_savings_usd), rate: fmtPct(T.cache_ratio)})},
    {id: 'sv-session', label: t('lblMedianSession'), value: T.median_session_tokens, fmt: fmtShort, hint: t('hintMedianSession', {min: T.median_session_minutes, cost: fmtUSD(T.median_session_cost)})}
  ];
  const sideEl = document.getElementById('summary-side');
  if (!document.getElementById('sv-tokens')) {
    sideEl.innerHTML = cardDefs.map(c => `
      <div class="sc">
        <div class="lbl">${c.label}</div>
        <div class="val" id="${c.id}"></div>
        <div class="hint" id="${c.id}-hint">${c.hint}</div>
      </div>`).join('');
  }
  cardDefs.forEach(c => {
    animateNum(document.getElementById(c.id), c.value, c.fmt);
    const hintEl = document.getElementById(c.id + '-hint');
    if (hintEl) hintEl.textContent = c.hint;
  });
}

function renderSourceCards(){
  const container = document.getElementById('source-cards');
  const prefix = 'src-';
  if (!document.getElementById(prefix + (data.source_cards[0] || {}).source)) {
    container.innerHTML = data.source_cards.map(card => {
      const cls = card.source.toLowerCase();
      const id = prefix + card.source;
      const icon = card.source === 'Codex' ? 'fa-terminal' : card.source === 'Claude' ? 'fa-feather-pointed' : 'fa-arrow-pointer';
      return `<article class="p src ${cls}" id="${id}">
        <div class="title"><span><i class="fa-solid ${icon}"></i> ${card.source}</span><span class="pill">${card.token_capable ? t('pillTokenTracked') : t('pillActivityOnly')}</span></div>
        <div class="big" id="${id}-big"></div>
        <div class="sub">${card.token_capable ? t('subTrackedTokens') : t('subMessagesOnly')}</div>
        <div class="mg">
          <div class="mi"><div class="k">${t('lblSessions')}</div><div class="v" id="${id}-sess"></div></div>
          <div class="mi"><div class="k">${t('lblCost')}</div><div class="v" id="${id}-cost" style="color:var(--cost)"></div></div>
          <div class="mi"><div class="k">${t('lblTopModel')}</div><div class="v" style="font-size:12px">${card.top_model}</div></div>
          <div class="mi"><div class="k">${t('lblCache')}</div><div class="v" id="${id}-cache"></div></div>
        </div>
      </article>`;
    }).join('');
  }
  data.source_cards.forEach(card => {
    const id = prefix + card.source;
    animateNum(document.getElementById(id + '-big'), card.token_capable ? card.total : card.messages, card.token_capable ? fmtShort : fmtInt);
    animateNum(document.getElementById(id + '-sess'), card.sessions, fmtInt);
    if (card.token_capable) {
      animateNum(document.getElementById(id + '-cost'), card.cost, fmtUSD);
      animateNum(document.getElementById(id + '-cache'), card.cache_read + card.cache_write, fmtShort);
    } else {
      const costEl = document.getElementById(id + '-cost');
      if (costEl) costEl.textContent = '-';
      const cacheEl = document.getElementById(id + '-cache');
      if (cacheEl) cacheEl.textContent = '-';
    }
  });
}

function renderCostCards(){
  const T = data.totals;
  const defs = [
    {id: 'cc-total', label: t('lblTotalCost'), value: T.grand_cost, fmt: fmtUSD, hint: t('hintTotalCost', {days: data.range.day_count}), cls: 'cost'},
    {id: 'cc-avg', label: t('lblDailyAvg'), value: T.average_cost_per_day, fmt: fmtUSD, hint: t('hintDailyAvg', {peak: T.cost_peak_day_label, cost: fmtUSD(T.cost_peak_day_total)}), cls: 'cost'},
    {id: 'cc-msg', label: t('lblCostPerMsg'), value: T.cost_per_message, fmt: fmtUSD, hint: t('hintCostPerMsg', {cost: fmtUSD(T.median_session_cost)}), cls: 'cost'},
    {id: 'cc-save', label: t('lblCacheSavings'), value: T.cache_savings_usd, fmt: fmtUSD, hint: t('hintCacheSavings', {pct: fmtPct(T.cache_savings_ratio)}), cls: 'save'}
  ];
  const container = document.getElementById('cost-cards');
  if (!document.getElementById('cc-total')) {
    container.innerHTML = defs.map(c => `
      <article class="p cc ${c.cls}">
        <div class="metric-k">${c.label}</div>
        <div class="big" id="${c.id}"></div>
        <div class="tiny" id="${c.id}-hint">${c.hint}</div>
      </article>`).join('');
  }
  defs.forEach(c => {
    animateNum(document.getElementById(c.id), c.value, c.fmt);
    const hintEl = document.getElementById(c.id + '-hint');
    if (hintEl) hintEl.textContent = c.hint;
  });
}

function renderStory(){
  const storyKey = lang === 'en' ? 'narrative_en' : 'narrative';
  const jokesKey = lang === 'en' ? 'jokes_en' : 'jokes';
  const narrative = data.story[storyKey] || data.story.narrative || [];
  const jokes = data.story[jokesKey] || data.story.jokes || [];
  const blocks = [
    ...narrative,
    ...jokes.map(txt => ({icon: 'fa-comment-dots', text: txt}))
  ];
  document.getElementById('story-list').innerHTML = blocks.map(block => `
    <div class="si"><i class="fa-solid ${block.icon}"></i><div>${block.text}</div></div>
  `).join('');
}

function renderDailyCostChart(){
  const chart = initChart('daily-cost-chart');
  const sources = getTokenSources().map(card => card.source);
  chart.setOption({
    ...chartTheme(),
    legend: {top: 6, textStyle: {color: TX}},
    grid: {top: 58, left: 68, right: 68, bottom: 44},
    tooltip: {...chartTheme().tooltip, trigger: 'axis', axisPointer: {type: 'shadow'}, valueFormatter: value => fmtUSD(value)},
    xAxis: {type: 'category', data: data.days.map(day => day.label), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: [
      {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: value => fmtUSD(value)}},
      {type: 'value', splitLine: {show: false}, axisLabel: {color: TX, formatter: value => fmtUSD(value)}}
    ],
    series: [
      ...sources.map(source => ({
        name: source,
        type: 'bar',
        stack: 'cost',
        itemStyle: {color: C[source] || '#999', borderRadius: [6, 6, 0, 0]},
        data: data.days.map(day => +(day.cost_sources[source] || 0).toFixed(4))
      })),
      {
        name: t('seriesCumulative'),
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbolSize: 6,
        lineStyle: {width: 3, color: 'rgba(255,255,255,.75)'},
        itemStyle: {color: '#fff'},
        areaStyle: {color: 'rgba(255,255,255,.06)'},
        data: data.days.map(day => day.cost_cumulative)
      }
    ]
  });
}

function renderCostBreakdownChart(){
  const T = data.totals;
  const items = [
    {name: 'Uncached Input', value: T.cost_input, color: C.uncached},
    {name: 'Cache Read', value: T.cost_cache_read, color: C.cacheRead},
    {name: 'Cache Write', value: T.cost_cache_write, color: C.cacheWrite},
    {name: 'Output', value: T.cost_output, color: C.output},
    {name: 'Reasoning', value: T.cost_reasoning, color: C.reason}
  ].filter(item => item.value > 0);
  const chart = initChart('cost-breakdown-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {bottom: 0, textStyle: {color: TX}},
    tooltip: {...chartTheme().tooltip, formatter: params => `${params.name}<br>${fmtUSD(params.value)} (${params.percent}%)`},
    series: [{
      type: 'pie',
      radius: ['40%', '74%'],
      center: ['50%', '45%'],
      itemStyle: {borderRadius: 10, borderColor: 'rgba(13,16,22,.95)', borderWidth: 3},
      label: {color: TX, formatter: params => `${params.name}\n${params.percent}%`},
      data: items.map(item => ({name: item.name, value: +item.value.toFixed(4), itemStyle: {color: item.color}}))
    }]
  });
}

function renderModelCostChart(){
  const rows = data.trend_analysis.model_costs.slice(0, 10);
  const chart = initChart('model-cost-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 170, right: 60, bottom: 24},
    tooltip: {...chartTheme().tooltip, valueFormatter: value => fmtUSD(value)},
    xAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: value => fmtUSD(value)}},
    yAxis: {type: 'category', data: rows.map(row => row.model).reverse(), axisLabel: {color: TX, width: 150, overflow: 'truncate', fontSize: 11}},
    series: [{
      type: 'bar',
      barMaxWidth: 22,
      data: rows.map((row, index) => ({value: row.cost, itemStyle: {color: ['#ff6b6b','#ff8a50','#ffa94d','#ffd43b','#a9e34b','#51cf66','#74c0fc','#748ffc','#b197fc','#e599f7'][index % 10], borderRadius: [0, 6, 6, 0]}})).reverse(),
      label: {show: true, position: 'right', color: TX, formatter: params => fmtUSD(params.value), fontSize: 11}
    }]
  });
}

function renderCostSankey(){
  const chart = initChart('cost-sankey-chart');
  chart.setOption({
    ...chartTheme(),
    tooltip: {...chartTheme().tooltip, valueFormatter: value => fmtUSD(value)},
    series: [{
      type: 'sankey',
      left: 8,
      right: 8,
      top: 24,
      bottom: 12,
      nodeWidth: 18,
      nodeGap: 14,
      lineStyle: {color: 'gradient', curveness: .45, opacity: .3},
      label: {color: '#fff', fontSize: 11},
      data: data.trend_analysis.cost_sankey.nodes.map(node => ({
        name: node.name,
        itemStyle: {color: C[node.name] || ['Input Cost','Cache Read','Cache Write','Output','Reasoning'].includes(node.name)
          ? { 'Input Cost': C.uncached, 'Cache Read': C.cacheRead, 'Cache Write': C.cacheWrite, 'Output': C.output, 'Reasoning': C.reason }[node.name]
          : '#888'}
      })),
      links: data.trend_analysis.cost_sankey.links
    }]
  });
}

function renderDailyCostTypeChart(){
  const chart = initChart('daily-cost-type-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {top: 6, textStyle: {color: TX}},
    grid: {top: 58, left: 68, right: 24, bottom: 44},
    tooltip: {...chartTheme().tooltip, trigger: 'axis', axisPointer: {type: 'shadow'}, valueFormatter: value => fmtUSD(value)},
    xAxis: {type: 'category', data: data.days.map(day => day.label), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: value => fmtUSD(value)}},
    series: [
      {name: 'Input', type: 'bar', stack: 'cost-type', itemStyle: {color: C.uncached}, data: data.days.map(day => day.cost_input)},
      {name: 'Cache Read', type: 'bar', stack: 'cost-type', itemStyle: {color: C.cacheRead}, data: data.days.map(day => day.cost_cache_read)},
      {name: 'Cache Write', type: 'bar', stack: 'cost-type', itemStyle: {color: C.cacheWrite}, data: data.days.map(day => day.cost_cache_write)},
      {name: 'Output', type: 'bar', stack: 'cost-type', itemStyle: {color: C.output}, data: data.days.map(day => day.cost_output)},
      {name: 'Reasoning', type: 'bar', stack: 'cost-type', itemStyle: {color: C.reason, borderRadius: [6, 6, 0, 0]}, data: data.days.map(day => day.cost_reasoning)}
    ]
  });
}

function renderCostCalendar(){
  const chart = initChart('cost-calendar-chart');
  const cells = data.days.map(day => [day.date, +day.cost.toFixed(2)]);
  chart.setOption({
    ...chartTheme(),
    tooltip: {...chartTheme().tooltip, formatter: params => `${params.value[0]}<br>${fmtUSD(params.value[1])}`},
    visualMap: {min: 0, max: Math.max(...data.days.map(day => day.cost), 1), orient: 'horizontal', left: 'center', bottom: 8, textStyle: {color: TX}, inRange: {color: ['rgba(255,255,255,.04)','#5c3a1e','#c0392b','#ff6b6b']}},
    calendar: {orient: 'vertical', top: 28, left: 36, right: 16, bottom: 48, cellSize: ['auto', 'auto'], range: [data.range.start_local.slice(0, 10), data.range.end_local.slice(0, 10)], yearLabel: {show: false}, monthLabel: {color: TX, nameMap: 'ZH', margin: 8}, dayLabel: {color: TX, firstDay: 1, nameMap: 'ZH'}, splitLine: {lineStyle: {color: AX}}, itemStyle: {borderWidth: 3, borderColor: '#0d1016', color: BG}},
    series: [{type: 'heatmap', coordinateSystem: 'calendar', data: cells}]
  });
}

function renderRoseChart(){
  const chart = initChart('rose-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {bottom: 0, textStyle: {color: TX}},
    series: [{
      type: 'pie',
      radius: ['24%', '74%'],
      center: ['50%', '46%'],
      roseType: 'radius',
      itemStyle: {borderRadius: 10, borderColor: '#0d1016', borderWidth: 3},
      label: {color: TX, formatter: params => `${params.name}\n${params.percent}%`},
      data: data.source_cards.map(card => ({
        name: card.source,
        value: card.token_capable ? card.total : Math.max(card.messages, 1),
        itemStyle: {color: C[card.source] || '#888'}
      }))
    }]
  });
}

function renderDailyTokenChart(){
  const chart = initChart('daily-token-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {top: 6, textStyle: {color: TX}},
    grid: {top: 58, left: 60, right: 60, bottom: 44},
    tooltip: {...chartTheme().tooltip, trigger: 'axis', axisPointer: {type: 'shadow'}},
    xAxis: {type: 'category', data: data.days.map(day => day.label), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: [
      {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: value => fmtShort(value)}},
      {type: 'value', splitLine: {show: false}, axisLabel: {color: TX, formatter: value => fmtShort(value)}}
    ],
    series: [
      {name: 'Uncached Input', type: 'bar', stack: 'tokens', itemStyle: {color: C.uncached}, data: data.days.map(day => day.uncached_input)},
      {name: 'Cache Read', type: 'bar', stack: 'tokens', itemStyle: {color: C.cacheRead}, data: data.days.map(day => day.cache_read)},
      {name: 'Cache Write', type: 'bar', stack: 'tokens', itemStyle: {color: C.cacheWrite}, data: data.days.map(day => day.cache_write)},
      {name: 'Output + Reason', type: 'bar', stack: 'tokens', itemStyle: {color: C.output, borderRadius: [6, 6, 0, 0]}, data: data.days.map(day => day.output + day.reasoning)},
      {name: t('seriesCumulative'), type: 'line', yAxisIndex: 1, smooth: true, symbolSize: 6, lineStyle: {width: 3, color: 'rgba(255,255,255,.76)'}, itemStyle: {color: '#fff'}, areaStyle: {color: 'rgba(255,255,255,.05)'}, data: data.days.map(day => day.cumulative_tokens)}
    ]
  });
}

function renderTokenSankey(){
  const chart = initChart('token-sankey-chart');
  chart.setOption({
    ...chartTheme(),
    series: [{
      type: 'sankey',
      left: 8,
      right: 8,
      top: 24,
      bottom: 12,
      nodeWidth: 18,
      nodeGap: 14,
      lineStyle: {color: 'gradient', curveness: .45, opacity: .28},
      label: {color: '#fff', fontSize: 11},
      data: data.trend_analysis.token_sankey.nodes.map(node => ({
        name: node.name,
        itemStyle: {color: C[node.name] || {'Uncached Input': C.uncached, 'Cache Read': C.cacheRead, 'Cache Write': C.cacheWrite, 'Output': C.output, 'Reasoning': C.reason}[node.name] || '#888'}
      })),
      links: data.trend_analysis.token_sankey.links
    }]
  });
  document.getElementById('source-notes').innerHTML = [
    ...data.story.source_notes.map(text => `<div class="note"><i class="fa-solid fa-circle-info"></i><div>${text}</div></div>`),
    ...data.story.jokes.map(text => `<div class="note"><i class="fa-solid fa-face-smile"></i><div>${text}</div></div>`)
  ].join('');
}

function renderHeatmap(){
  const chart = initChart('heatmap-chart');
  const points = [];
  data.working_patterns.heatmap.forEach((row, y) => row.values.forEach((value, x) => points.push([x, y, value])));
  chart.setOption({
    ...chartTheme(),
    grid: {top: 44, left: 70, right: 24, bottom: 34},
    xAxis: {type: 'category', data: Array.from({length: 24}, (_, i) => `${i}`), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}},
    yAxis: {type: 'category', data: data.working_patterns.heatmap.map(row => row.weekday), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}},
    visualMap: {min: 0, max: Math.max(...points.map(point => point[2]), 1), orient: 'horizontal', left: 'center', bottom: 0, textStyle: {color: TX}, inRange: {color: ['rgba(255,255,255,.03)','#5c3a1e','#ff8a50','#ffd43b']}},
    series: [{type: 'heatmap', data: points, itemStyle: {borderRadius: 6, borderColor: '#0d1016', borderWidth: 3}}]
  });
}

function renderSourceRadar(){
  const rows = data.working_patterns.source_radar;
  const chart = initChart('source-radar-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {bottom: 0, textStyle: {color: TX}},
    radar: {
      radius: '62%',
      center: ['50%', '46%'],
      splitNumber: 5,
      axisName: {color: TX, fontSize: 11},
      splitLine: {lineStyle: {color: AX}},
      splitArea: {areaStyle: {color: ['rgba(255,255,255,.02)','rgba(255,255,255,.01)']}},
      indicator: [
        {name: t('radarTotal'), max: Math.max(...rows.map(row => row.total_tokens), 1)},
        {name: t('radarCache'), max: Math.max(...rows.map(row => row.cache_total), 1)},
        {name: t('radarOutput'), max: Math.max(...rows.map(row => row.output_total), 1)},
        {name: t('radarSessions'), max: Math.max(...rows.map(row => row.sessions), 1)}
      ]
    },
    series: [{
      type: 'radar',
      symbol: 'circle',
      symbolSize: 6,
      areaStyle: {opacity: .08},
      lineStyle: {width: 2},
      data: rows.map(row => ({
        name: row.name,
        value: [row.total_tokens, row.cache_total, row.output_total, row.sessions],
        lineStyle: {color: C[row.name] || '#888'},
        itemStyle: {color: C[row.name] || '#888'},
        areaStyle: {color: C[row.name] || '#888', opacity: .08}
      }))
    }]
  });
}

function renderTokenCalendar(){
  const chart = initChart('token-calendar-chart');
  const cells = data.days.map(day => [day.date, day.total_tokens]);
  chart.setOption({
    ...chartTheme(),
    tooltip: {...chartTheme().tooltip, formatter: params => `${params.value[0]}<br>${fmtInt(params.value[1])} tokens`},
    visualMap: {min: 0, max: Math.max(...data.days.map(day => day.total_tokens), 1), orient: 'horizontal', left: 'center', bottom: 8, textStyle: {color: TX}, inRange: {color: ['rgba(255,255,255,.03)','#3a4a2e','#51cf66','#a9e34b']}},
    calendar: {orient: 'vertical', top: 28, left: 36, right: 16, bottom: 48, cellSize: ['auto', 'auto'], range: [data.range.start_local.slice(0, 10), data.range.end_local.slice(0, 10)], yearLabel: {show: false}, monthLabel: {color: TX, nameMap: 'ZH', margin: 8}, dayLabel: {color: TX, firstDay: 1, nameMap: 'ZH'}, splitLine: {lineStyle: {color: AX}}, itemStyle: {borderWidth: 3, borderColor: '#0d1016', color: BG}},
    series: [{type: 'heatmap', coordinateSystem: 'calendar', data: cells}]
  });
}

function renderTimeline(){
  const timeline = data.working_patterns.timeline;
  const chart = initChart('timeline-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {top: 4, textStyle: {color: TX}},
    grid: {top: 54, left: 56, right: 24, bottom: 46},
    tooltip: {...chartTheme().tooltip, trigger: 'axis'},
    xAxis: {type: 'category', data: timeline.days.map(day => day.label), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: [
      {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: value => fmtShort(value)}},
      {type: 'value', splitLine: {show: false}, axisLabel: {color: TX, formatter: value => fmtShort(value)}}
    ],
    series: [
      {name: 'Daily Total', type: 'bar', barMaxWidth: 24, itemStyle: {color: 'rgba(255,138,80,.32)', borderRadius: [6, 6, 0, 0]}, data: timeline.days.map(day => day.total_tokens)},
      {
        name: 'Cumulative',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbolSize: 6,
        lineStyle: {width: 3, color: 'rgba(255,255,255,.76)'},
        itemStyle: {color: '#fff'},
        data: timeline.days.map(day => day.cumulative_tokens),
        markPoint: {
          symbol: 'pin',
          symbolSize: 38,
          label: {color: '#fff', fontSize: 10, formatter: params => fmtShort(params.value)},
          itemStyle: {color: C.Codex},
          data: timeline.peak_markers.map(marker => ({name: marker.label, coord: [marker.label, marker.cumulative_tokens], value: marker.total_tokens}))
        }
      }
    ]
  });
}

function renderBubble(){
  const rows = data.session_deep_dive.complexity_scatter.slice(0, 50);
  const chart = initChart('bubble-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 30, left: 62, right: 24, bottom: 54},
    tooltip: {
      ...chartTheme().tooltip,
      formatter: params => `${params.seriesName}<br>${params.data.session}<br>${fmtShort(params.data.value[1])} tokens<br>${params.data.value[0]} min`
    },
    xAxis: {name: 'Minutes', nameTextStyle: {color: TX}, splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    yAxis: {name: 'Tokens', nameTextStyle: {color: TX}, splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: value => fmtShort(value)}},
    series: ['Codex', 'Claude', 'Cursor'].map(source => ({
      name: source,
      type: 'scatter',
      data: rows.filter(row => row.source === source).map(row => ({
        value: [Math.max(row.duration_minutes, 1), row.total_tokens, Math.max(12, Math.sqrt(row.cache_total || 1) / 180)],
        session: row.session_id.slice(0, 12) + '…'
      })),
      symbolSize: value => value[2],
      itemStyle: {color: C[source] || '#888', opacity: .82}
    }))
  });
}

function renderTempo(){
  const rows = data.working_patterns.hourly_source_totals;
  const chart = initChart('tempo-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {top: 4, textStyle: {color: TX}},
    grid: {top: 52, left: 56, right: 24, bottom: 46},
    xAxis: {type: 'category', data: rows.map(row => `${row.hour}`), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: value => fmtShort(value)}},
    series: ['Codex', 'Claude', 'Cursor'].map(source => ({
      name: source,
      type: source === 'Cursor' ? 'line' : 'bar',
      smooth: source === 'Cursor',
      barMaxWidth: 18,
      itemStyle: {color: C[source] || '#888'},
      lineStyle: {width: 2, color: C[source] || '#888'},
      data: rows.map(row => row[source] || 0)
    }))
  });
  document.getElementById('tempo-notes').innerHTML = data.story.tempo_notes.map(text => `<div class="note"><i class="fa-solid fa-clock"></i><div>${text}</div></div>`).join('');
}

function renderToolRanking(){
  const rows = data.tooling.ranking.slice(0, 20);
  const chart = initChart('tool-ranking-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 120, right: 60, bottom: 24},
    xAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    yAxis: {type: 'category', data: rows.map(row => row.name).reverse(), axisLabel: {color: TX, fontSize: 11}},
    series: [{
      type: 'bar',
      barMaxWidth: 22,
      data: rows.map(row => ({value: row.count, itemStyle: {color: '#ffd43b', borderRadius: [0, 6, 6, 0]}})).reverse(),
      label: {show: true, position: 'right', color: TX, fontSize: 11}
    }]
  });
}

function renderToolDensity(){
  const rows = data.working_patterns.hourly_tool_density;
  const chart = initChart('tool-density-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 48, right: 24, bottom: 44},
    xAxis: {type: 'category', data: rows.map(row => `${row.hour}h`), axisLabel: {color: TX}},
    yAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    series: [{type: 'bar', data: rows.map(row => ({value: row.count, itemStyle: {color: '#ffd43b', borderRadius: [6, 6, 0, 0]}}))}]
  });
}

function renderToolBigramChart(){
  const rows = data.tooling.bigram_chord;
  const chart = initChart('tool-bigram-chart');
  chart.setOption({
    ...chartTheme(),
    series: [{
      type: 'graph',
      layout: 'circular',
      circular: {rotateLabel: true},
      roam: true,
      label: {show: true, color: TX},
      lineStyle: {color: 'source', opacity: .4, width: 2, curveness: .2},
      edgeSymbol: ['none', 'arrow'],
      edgeSymbolSize: [0, 8],
      data: rows.nodes.map((node, index) => ({
        name: node.name,
        value: node.value,
        symbolSize: 18 + Math.min(node.value * 1.5, 36),
        itemStyle: {color: ['#ffd43b','#ff8a50','#74c0fc','#51cf66','#b197fc','#e599f7','#ffa94d','#94d82d'][index % 8]}
      })),
      links: rows.links.map(link => ({source: link.source, target: link.target, value: link.value, lineStyle: {width: 1 + Math.log2(link.value + 1)}}))
    }]
  });
}

function renderTopCommands(){
  const rows = data.commands.top_commands.slice(0, 15);
  const chart = initChart('top-commands-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 110, right: 60, bottom: 24},
    xAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    yAxis: {type: 'category', data: rows.map(row => row.command).reverse(), axisLabel: {color: TX, fontSize: 11}},
    series: [{
      type: 'bar',
      barMaxWidth: 22,
      data: rows.map(row => ({
        value: row.count,
        itemStyle: {color: row.failure_rate > .3 ? '#ff6b6b' : '#51cf66', borderRadius: [0, 6, 6, 0]}
      })).reverse(),
      label: {show: true, position: 'right', color: TX, fontSize: 11}
    }]
  });
}

function renderCommandSuccessChart(){
  const rows = data.commands.daily_success;
  const chart = initChart('command-success-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {top: 4, textStyle: {color: TX}},
    grid: {top: 52, left: 56, right: 24, bottom: 44},
    tooltip: {...chartTheme().tooltip, trigger: 'axis'},
    xAxis: {type: 'category', data: rows.map(row => row.label), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    series: [
      {name: 'Success', type: 'line', smooth: true, areaStyle: {color: 'rgba(81,207,102,.2)'}, itemStyle: {color: '#51cf66'}, lineStyle: {width: 3, color: '#51cf66'}, data: rows.map(row => row.successes)},
      {name: 'Fail', type: 'line', smooth: true, areaStyle: {color: 'rgba(255,107,107,.16)'}, itemStyle: {color: '#ff6b6b'}, lineStyle: {width: 3, color: '#ff6b6b'}, data: rows.map(row => row.failures)}
    ]
  });
}

function renderEfficiencyChart(){
  const rows = data.efficiency_metrics.daily;
  const chart = initChart('efficiency-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {top: 4, textStyle: {color: TX}},
    grid: {top: 52, left: 56, right: 56, bottom: 44},
    tooltip: {...chartTheme().tooltip, trigger: 'axis'},
    xAxis: {type: 'category', data: rows.map(row => row.label), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: [
      {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: value => fmtPct(value)}},
      {type: 'value', splitLine: {show: false}, axisLabel: {color: TX, formatter: value => fmtShort(value)}}
    ],
    series: [
      {name: 'Reasoning Ratio', type: 'line', smooth: true, itemStyle: {color: C.reason}, lineStyle: {width: 3, color: C.reason}, data: rows.map(row => row.reasoning_ratio)},
      {name: 'Cache Hit Rate', type: 'line', smooth: true, itemStyle: {color: C.cacheRead}, lineStyle: {width: 3, color: C.cacheRead}, data: rows.map(row => row.cache_hit_rate)},
      {name: 'Tokens / Message', type: 'line', yAxisIndex: 1, smooth: true, itemStyle: {color: C.output}, lineStyle: {width: 3, color: C.output}, data: rows.map(row => row.tokens_per_message)}
    ]
  });
}

function renderProjectRanking(){
  const rows = data.projects.ranking.slice(0, 15);
  const chart = initChart('project-ranking-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 140, right: 60, bottom: 24},
    tooltip: {...chartTheme().tooltip, valueFormatter: value => fmtShort(value)},
    xAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: value => fmtShort(value)}},
    yAxis: {type: 'category', data: rows.map(row => row.project).reverse(), axisLabel: {color: TX, fontSize: 11}},
    series: [{
      type: 'bar',
      barMaxWidth: 22,
      data: rows.map(row => ({value: row.total_tokens, itemStyle: {color: '#74c0fc', borderRadius: [0, 6, 6, 0]}})).reverse(),
      label: {show: true, position: 'right', color: TX, fontSize: 11, formatter: params => fmtShort(params.value)}
    }]
  });
}

function renderFileTypesChart(){
  const rows = data.projects.file_types.slice(0, 12);
  const chart = initChart('file-types-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {bottom: 0, textStyle: {color: TX}},
    tooltip: {...chartTheme().tooltip, formatter: params => `${params.name}<br>${fmtInt(params.value)} touches`},
    series: [{
      type: 'pie',
      radius: ['34%', '72%'],
      center: ['50%', '45%'],
      label: {color: TX},
      itemStyle: {borderRadius: 8, borderColor: '#0d1016', borderWidth: 3},
      data: rows.map((row, index) => ({
        name: row.extension,
        value: row.count,
        itemStyle: {color: ['#74c0fc','#ff8a50','#ffd43b','#51cf66','#b197fc','#e599f7','#ffa94d','#94d82d','#4dabf7','#ff8787','#fcc419','#9775fa'][index % 12]}
      }))
    }]
  });
}

function renderBranchActivityChart(){
  const rows = data.projects.branch_activity.slice(0, 12);
  const chart = initChart('branch-activity-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 120, right: 60, bottom: 24},
    xAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    yAxis: {type: 'category', data: rows.map(row => row.branch).reverse(), axisLabel: {color: TX, fontSize: 11}},
    series: [{
      type: 'bar',
      barMaxWidth: 22,
      data: rows.map(row => ({value: row.sessions, itemStyle: {color: '#b197fc', borderRadius: [0, 6, 6, 0]}})).reverse(),
      label: {show: true, position: 'right', color: TX, fontSize: 11}
    }]
  });
}

function renderProductivityChart(){
  const rows = data.working_patterns.daily_productivity;
  const chart = initChart('productivity-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 56, right: 24, bottom: 44},
    tooltip: {...chartTheme().tooltip, trigger: 'axis'},
    xAxis: {type: 'category', data: rows.map(row => row.label), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: {type: 'value', min: 0, max: 1, splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    series: [{
      name: 'Productivity',
      type: 'line',
      smooth: true,
      symbolSize: 8,
      lineStyle: {width: 3, color: '#ffd43b'},
      itemStyle: {color: '#ffd43b'},
      areaStyle: {color: 'rgba(255,212,59,.14)'},
      data: rows.map(row => row.score)
    }]
  });
}

function renderBurnRateChart(){
  const history = data.trend_analysis.burn_rate_30d.history;
  const projection = data.trend_analysis.burn_rate_30d.projection;
  const labels = [...history.map(row => row.label), ...projection.map(row => row.label)];
  const actualSeries = [...history.map(row => row.cumulative_cost), ...projection.map(() => null)];
  const projectedSeries = [
    ...history.map((row, index) => index === history.length - 1 ? row.cumulative_cost : null),
    ...projection.map(row => row.projected_cumulative_cost)
  ];
  const chart = initChart('burn-rate-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {top: 4, textStyle: {color: TX}},
    grid: {top: 52, left: 56, right: 24, bottom: 44},
    tooltip: {...chartTheme().tooltip, trigger: 'axis', valueFormatter: value => value == null ? '-' : fmtUSD(value)},
    xAxis: {type: 'category', data: labels, axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: value => fmtUSD(value)}},
    series: [
      {name: 'Actual Cumulative', type: 'line', smooth: true, symbolSize: 6, lineStyle: {width: 3, color: '#74c0fc'}, itemStyle: {color: '#74c0fc'}, data: actualSeries},
      {name: 'Projected Cumulative', type: 'line', smooth: true, symbolSize: 6, lineStyle: {width: 3, type: 'dashed', color: '#ff8a50'}, itemStyle: {color: '#ff8a50'}, data: projectedSeries}
    ]
  });
}

function renderCostPerToolChart(){
  const rows = data.trend_analysis.daily_cost_per_tool_call;
  const chart = initChart('cost-per-tool-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 56, right: 24, bottom: 44},
    tooltip: {...chartTheme().tooltip, trigger: 'axis', valueFormatter: value => fmtUSD(value)},
    xAxis: {type: 'category', data: rows.map(row => row.label), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: value => fmtUSD(value)}},
    series: [{
      type: 'line',
      smooth: true,
      symbolSize: 7,
      lineStyle: {width: 3, color: '#ff8a50'},
      itemStyle: {color: '#ff8a50'},
      areaStyle: {color: 'rgba(255,138,80,.14)'},
      data: rows.map(row => row.value)
    }]
  });
}

function renderSessionDurationChart(){
  const rows = data.session_deep_dive.duration_histogram;
  const chart = initChart('session-duration-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 48, right: 24, bottom: 44},
    xAxis: {type: 'category', data: rows.map(row => row.label), axisLabel: {color: TX}},
    yAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    series: [{type: 'bar', barMaxWidth: 30, data: rows.map(row => ({value: row.count, itemStyle: {color: '#51cf66', borderRadius: [6, 6, 0, 0]}}))}]
  });
}

function renderModelRadarChart(){
  const rows = data.trend_analysis.model_radar;
  const chart = initChart('model-radar-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {bottom: 0, textStyle: {color: TX}},
    radar: {
      radius: '62%',
      center: ['50%', '46%'],
      splitNumber: 5,
      axisName: {color: TX, fontSize: 11},
      splitLine: {lineStyle: {color: AX}},
      splitArea: {areaStyle: {color: ['rgba(255,255,255,.02)','rgba(255,255,255,.01)']}},
      indicator: [
        {name: 'Input', max: 1},
        {name: 'Output', max: 1},
        {name: 'Cache', max: 1},
        {name: 'Cost', max: 1},
        {name: 'Msgs', max: 1}
      ]
    },
    series: [{
      type: 'radar',
      symbol: 'circle',
      symbolSize: 5,
      lineStyle: {width: 2},
      areaStyle: {opacity: .08},
      data: rows.map((row, index) => ({
        name: row.name,
        value: row.normalized,
        lineStyle: {color: ['#ff6b6b','#ff8a50','#ffd43b','#74c0fc','#b197fc'][index % 5]},
        itemStyle: {color: ['#ff6b6b','#ff8a50','#ffd43b','#74c0fc','#b197fc'][index % 5]},
        areaStyle: {color: ['#ff6b6b','#ff8a50','#ffd43b','#74c0fc','#b197fc'][index % 5], opacity: .08}
      }))
    }]
  });
}

/* ── Extended Analytics charts ── */
function renderTurnDurChart(){
  const ext = data.extended;
  if (!ext || !ext.turn_durations) return;
  const rows = ext.turn_durations.histogram;
  const chart = initChart('turn-dur-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 48, right: 24, bottom: 44},
    tooltip: {...chartTheme().tooltip, trigger: 'axis'},
    xAxis: {type: 'category', data: rows.map(r => r.label), axisLabel: {color: TX}},
    yAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    series: [{
      type: 'bar', barMaxWidth: 30,
      data: rows.map(r => ({value: r.count, itemStyle: {color: '#74c0fc', borderRadius: [6,6,0,0]}}))
    }]
  });
}

function renderDailyTurnDurChart(){
  const ext = data.extended;
  if (!ext || !ext.turn_durations) return;
  const rows = ext.turn_durations.daily.filter(r => r.count > 0);
  if (!rows.length) return;
  const chart = initChart('daily-turn-dur-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 56, right: 24, bottom: 44},
    tooltip: {...chartTheme().tooltip, trigger: 'axis', valueFormatter: v => v == null ? '-' : (v/1000).toFixed(1)+'s'},
    xAxis: {type: 'category', data: rows.map(r => r.label), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: {type: 'value', name: 'ms', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: v => (v/1000).toFixed(0)+'s'}},
    series: [{
      type: 'line', smooth: true, symbolSize: 5,
      lineStyle: {width: 2, color: '#b197fc'}, itemStyle: {color: '#b197fc'},
      areaStyle: {color: 'rgba(177,151,252,.12)'},
      data: rows.map(r => r.median_ms)
    }]
  });
}

function renderTaskRateChart(){
  const ext = data.extended;
  if (!ext || !ext.task_events) return;
  const te = ext.task_events;
  if (!te.started) return;
  const chart = initChart('task-rate-chart');
  const failed = te.started - te.completed;
  chart.setOption({
    ...chartTheme(),
    tooltip: {...chartTheme().tooltip, trigger: 'item'},
    legend: {bottom: 0, textStyle: {color: TX}},
    series: [{
      type: 'pie', radius: ['40%', '68%'], center: ['50%', '44%'],
      label: {color: TX, formatter: '{b}: {c} ({d}%)'},
      data: [
        {value: te.completed, name: 'Completed', itemStyle: {color: '#51cf66'}},
        {value: failed, name: 'Incomplete', itemStyle: {color: '#ff6b6b'}}
      ]
    }]
  });
}

function renderCodegenModelChart(){
  const ext = data.extended;
  if (!ext || !ext.cursor_codegen || !ext.cursor_codegen.total) return;
  const rows = ext.cursor_codegen.by_model.slice(0, 8);
  const chart = initChart('codegen-model-chart');
  const colors = ['#ff8a50','#ffd43b','#74c0fc','#51cf66','#b197fc','#e599f7','#ff6b6b','#f4b183'];
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 8, right: 24, bottom: 44, containLabel: true},
    tooltip: {...chartTheme().tooltip, trigger: 'axis'},
    xAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    yAxis: {type: 'category', data: rows.map(r => r.model).reverse(), axisLabel: {color: TX, fontSize: 10, width: 140, overflow: 'truncate'}},
    series: [{
      type: 'bar', barMaxWidth: 22,
      data: rows.map((r,i) => ({value: r.count, itemStyle: {color: colors[i%8], borderRadius: [0,6,6,0]}})).reverse()
    }]
  });
}

function renderCodegenDailyChart(){
  const ext = data.extended;
  if (!ext || !ext.cursor_codegen || !ext.cursor_codegen.total) return;
  const rows = ext.cursor_codegen.daily;
  const chart = initChart('codegen-daily-chart');
  chart.setOption({
    ...chartTheme(),
    grid: {top: 24, left: 48, right: 24, bottom: 44},
    tooltip: {...chartTheme().tooltip, trigger: 'axis'},
    xAxis: {type: 'category', data: rows.map(r => r.label), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    series: [{
      type: 'bar', barMaxWidth: 14,
      itemStyle: {color: '#748ffc', borderRadius: [4,4,0,0]},
      data: rows.map(r => r.count)
    }]
  });
}

function renderAiContributionChart(){
  const ext = data.extended;
  if (!ext || !ext.ai_contribution || !ext.ai_contribution.total_commits) return;
  const ai = ext.ai_contribution;
  const chart = initChart('ai-contribution-chart');
  chart.setOption({
    ...chartTheme(),
    tooltip: {...chartTheme().tooltip, trigger: 'item'},
    legend: {bottom: 0, textStyle: {color: TX}},
    series: [{
      type: 'pie', radius: ['40%', '68%'], center: ['50%', '44%'],
      label: {color: TX, formatter: '{b}\\n{c} lines ({d}%)'},
      data: [
        {value: ai.ai_lines_added, name: 'AI Added', itemStyle: {color: '#74c0fc'}},
        {value: ai.human_lines_added, name: 'Human Added', itemStyle: {color: '#ffd43b'}},
        {value: ai.ai_lines_deleted, name: 'AI Deleted', itemStyle: {color: '#b197fc'}},
        {value: ai.human_lines_deleted, name: 'Human Deleted', itemStyle: {color: '#ff6b6b'}}
      ].filter(d => d.value > 0)
    }]
  });
}

function renderSessionTable(){
  document.getElementById('session-table').innerHTML = `
    <thead>
      <tr><th>Source</th><th>Session</th><th>Tokens</th><th>Cost</th><th>Tools</th><th>Model</th><th>Window</th></tr>
    </thead>
    <tbody>
      ${data.top_sessions.map(row => `
        <tr>
          <td><strong style="color:var(--text)">${row.source}</strong><div class="tiny">${fmtInt(row.messages)} events</div></td>
          <td><strong style="color:var(--text)">${row.session_id.slice(0, 10)}…</strong><div class="tiny">${row.minutes} min</div></td>
          <td>${fmtShort(row.total)}</td>
          <td style="color:var(--cost);font-weight:700">${fmtUSD(row.cost)}</td>
          <td>${fmtInt(row.tool_calls)}</td>
          <td style="font-size:11px">${row.top_model}</td>
          <td><div style="font-size:11px">${row.first_local}</div><div class="tiny">→ ${row.last_local}</div></td>
        </tr>
      `).join('')}
    </tbody>`;
}

function renderDashboard(){
  if (!data || !data.totals) {
    return;
  }
  /* DOM-only sections render immediately */
  renderHero();
  renderSourceCards();
  renderCostCards();
  renderStory();
  renderSessionTable();

  /* First two charts render eagerly (above the fold) */
  renderDailyCostChart();
  renderCostBreakdownChart();

  /* All remaining charts are lazy — only init when scrolled into view */
  lazyQueue.length = 0;
  registerLazy('model-cost-chart', renderModelCostChart);
  registerLazy('cost-sankey-chart', renderCostSankey);
  registerLazy('daily-cost-type-chart', renderDailyCostTypeChart);
  registerLazy('cost-calendar-chart', renderCostCalendar);
  registerLazy('rose-chart', renderRoseChart);
  registerLazy('daily-token-chart', renderDailyTokenChart);
  registerLazy('token-sankey-chart', renderTokenSankey);
  registerLazy('heatmap-chart', renderHeatmap);
  registerLazy('source-radar-chart', renderSourceRadar);
  registerLazy('token-calendar-chart', renderTokenCalendar);
  registerLazy('timeline-chart', renderTimeline);
  registerLazy('bubble-chart', renderBubble);
  registerLazy('tempo-chart', renderTempo);
  registerLazy('tool-ranking-chart', renderToolRanking);
  registerLazy('tool-density-chart', renderToolDensity);
  registerLazy('tool-bigram-chart', renderToolBigramChart);
  registerLazy('top-commands-chart', renderTopCommands);
  registerLazy('command-success-chart', renderCommandSuccessChart);
  registerLazy('efficiency-chart', renderEfficiencyChart);
  registerLazy('project-ranking-chart', renderProjectRanking);
  registerLazy('file-types-chart', renderFileTypesChart);
  registerLazy('branch-activity-chart', renderBranchActivityChart);
  registerLazy('productivity-chart', renderProductivityChart);
  registerLazy('burn-rate-chart', renderBurnRateChart);
  registerLazy('cost-per-tool-chart', renderCostPerToolChart);
  registerLazy('session-duration-chart', renderSessionDurationChart);
  registerLazy('model-radar-chart', renderModelRadarChart);
  registerLazy('turn-dur-chart', renderTurnDurChart);
  registerLazy('daily-turn-dur-chart', renderDailyTurnDurChart);
  registerLazy('task-rate-chart', renderTaskRateChart);
  registerLazy('codegen-model-chart', renderCodegenModelChart);
  registerLazy('codegen-daily-chart', renderCodegenDailyChart);
  registerLazy('ai-contribution-chart', renderAiContributionChart);
  flushLazy();

  requestAnimationFrame(() => {
    charts.forEach(chart => chart.resize());
    isFirstRender = false;
  });
}

function renderRangeTabs(){
  const el = document.getElementById('range-tabs');
  if (!el) return;
  const allLabel = defaultSince ? `从 ${defaultSince}` : `${defaultDays} 天`;
  const tabs = [
    {key: 'all', label: allLabel},
    {key: 'week', label: '近 7 天'},
    {key: 'today', label: '今日'}
  ];
  el.innerHTML = tabs.map(t =>
    `<button class="range-tab${t.key === activeRangeKey ? ' active' : ''}" data-range="${t.key}">${t.label}</button>`
  ).join('');
  el.querySelectorAll('.range-tab').forEach(btn => {
    btn.addEventListener('click', () => switchRange(btn.dataset.range));
  });
}

async function switchRange(key){
  if (key === activeRangeKey) return;
  activeRangeKey = key;
  dashboardApiUrl = _apiUrl(key);
  dashboardStreamUrl = _streamUrl(key);
  lastDashboardHash = '';
  /* Clear prev values so numbers animate on tab switch */
  _numPrevValues = new WeakMap();
  isFirstRender = false;
  renderRangeTabs();
  if (isLiveMode) {
    stopStream();
    /* Fetch once immediately, then reconnect SSE */
    await fetchDashboardOnce();
    startSseDashboard();
  } else {
    /* Static mode: fetch from API if available, otherwise we can't switch */
    try {
      const res = await fetch(dashboardApiUrl, {cache: 'no-store'});
      if (res.ok) {
        const nextData = await res.json();
        data = nextData;
        lastDashboardHash = (nextData._meta || {}).generated_at || '';
        renderDashboard();
      }
    } catch (e) {
      showToast('切换失败: ' + (e.message || e), 'err', 3000);
    }
  }
}

function bootDashboard(){
  renderRangeTabs();
  if (data && data.totals) {
    if (!isLiveMode) updateLiveBadge('off');
    renderDashboard();
    return;
  }
  if (!isLiveMode) {
    updateLiveBadge('off');
    document.getElementById('hero-copy').textContent = '缺少可用数据。';
    return;
  }
  startSseDashboard();
}

let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => charts.forEach(chart => chart.resize()), 150);
});
window.addEventListener('beforeunload', stopStream);
bootDashboard();
</script>
</body>
</html>
"""
