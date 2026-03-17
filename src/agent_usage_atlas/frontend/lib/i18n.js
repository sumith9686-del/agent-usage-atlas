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
    lblHeroSessions: '会话', lblHeroProjects: '项目', lblHeroDays: '天数', lblHeroAvgBurn: '日均花费',
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
    divInsights: 'Insights & Prompts',
    chartVagueList: '模糊提示排行', chartVagueListSub: '最常见的低效提示',
    chartExpensive: '最贵 Prompt 排行', chartExpensiveSub: '按响应花费排序',
    lblVagueCount: 'Vague Prompts', lblVagueRatio: 'Vague Ratio',
    lblWastedTokens: 'Wasted Tokens', lblWastedCost: 'Wasted Cost',
    hintVagueCount: '共 {total} 条用户消息',
    hintVagueRatio: '{count} / {total}',
    hintWastedTokens: '因模糊提示消耗',
    hintWastedCost: '可优化的浪费',
    tblRank: '#', tblPrompt: 'Prompt', tblPromptTokens: 'Tokens', tblPromptCost: 'Cost', tblPromptModel: 'Model', tblPromptSource: 'Source',
    insightAction: '建议', insightActionEn: 'Suggestion',
    lblInsightHigh: '高', lblInsightMedium: '中', lblInsightLow: '低', lblInsightInfo: '提示',
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
    lblHeroSessions: 'Sessions', lblHeroProjects: 'Projects', lblHeroDays: 'Days', lblHeroAvgBurn: 'Avg Burn',
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
    divInsights: 'Insights & Prompts',
    chartVagueList: 'Top Vague Prompts', chartVagueListSub: 'most common low-effort prompts',
    chartExpensive: 'Most Expensive Prompts', chartExpensiveSub: 'ranked by response cost',
    lblVagueCount: 'Vague Prompts', lblVagueRatio: 'Vague Ratio',
    lblWastedTokens: 'Wasted Tokens', lblWastedCost: 'Wasted Cost',
    hintVagueCount: '{total} total user messages',
    hintVagueRatio: '{count} / {total}',
    hintWastedTokens: 'consumed by vague prompts',
    hintWastedCost: 'optimization opportunity',
    tblRank: '#', tblPrompt: 'Prompt', tblPromptTokens: 'Tokens', tblPromptCost: 'Cost', tblPromptModel: 'Model', tblPromptSource: 'Source',
    insightAction: 'Suggestion', insightActionEn: 'Suggestion',
    lblInsightHigh: 'High', lblInsightMedium: 'Medium', lblInsightLow: 'Low', lblInsightInfo: 'Info',
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
  document.getElementById('lang-btn').textContent = '\u{1F310} ' + lang.toUpperCase();
  _numPrevValues = new WeakMap();
  isFirstRender = false;
  /* Force re-create DOM elements by clearing containers */
  ['hero-chips','hero-stats','source-bar','summary-side','source-cards','cost-cards','vague-stats','vague-list','expensive-table','insight-cards'].forEach(id => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = '';
  });
  renderRangeTabs();
  renderDashboard();
}

/* ── Theme toggle ── */
let currentTheme = localStorage.getItem('atlas-theme') || 'dark';
function applyTheme() {
  if (currentTheme === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
  } else {
    document.documentElement.removeAttribute('data-theme');
  }
}
function toggleTheme() {
  currentTheme = currentTheme === 'dark' ? 'light' : 'dark';
  localStorage.setItem('atlas-theme', currentTheme);
  applyTheme();
  /* Re-render charts with updated theme colors */
  clearCharts();
  isFirstRender = false;
  renderDashboard();
}
applyTheme();