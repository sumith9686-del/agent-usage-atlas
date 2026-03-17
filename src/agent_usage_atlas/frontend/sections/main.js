function renderDashboard(){
  if (!data || !data.totals) {
    return;
  }
  /* Apply i18n to data-i18n elements */
  applyI18n();
  /* Token legend */
  const legendEl = document.getElementById('token-legend');
  if (legendEl) legendEl.innerHTML = [
    `<span><i class="dot" style="background:var(--uncached)"></i>${t('legendUncached')}</span>`,
    `<span><i class="dot" style="background:var(--cache-read)"></i>${t('legendCacheRead')}</span>`,
    `<span><i class="dot" style="background:var(--cache-write)"></i>${t('legendCacheWrite')}</span>`,
    `<span><i class="dot" style="background:var(--output)"></i>${t('legendOutputReason')}</span>`
  ].join('');
  /* Footer */
  const footerEl = document.getElementById('footer-text');
  if (footerEl) footerEl.innerHTML = t('footerText');
  /* DOM-only sections render immediately */
  renderHero();
  renderSourceCards();
  renderCostCards();
  renderStory();
  renderSessionTable();
  renderVaguePrompts();
  renderExpensivePrompts();
  renderInsights();

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
    if (typeof refreshSectionHeights === 'function') refreshSectionHeights();
  });
}

function renderRangeTabs(){
  const el = document.getElementById('range-tabs');
  if (!el) return;
  const allLabel = defaultSince ? t('rangeFrom', {since: defaultSince}) : t('rangeDays', {days: defaultDays});
  const tabs = [
    {key: 'all', label: allLabel},
    {key: 'week', label: t('rangeWeek')},
    {key: 'today', label: t('rangeToday')}
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
      showToast(t('toastSwitchFail', {err: e.message || e}), 'err', 3000);
    }
  }
}

function bootDashboard(){
  document.getElementById('lang-btn').textContent = '\u{1F310} ' + lang.toUpperCase();
  applyI18n();
  document.getElementById('hero-title').textContent = t('heroTitle');
  renderRangeTabs();
  if (data && data.totals) {
    if (!isLiveMode) updateLiveBadge('off');
    renderDashboard();
    return;
  }
  if (!isLiveMode) {
    updateLiveBadge('off');
    document.getElementById('hero-copy').textContent = t('heroNoData');
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

/* ── Section collapse / expand ── */
const COLLAPSE_KEY = 'atlas-collapsed';
function _loadCollapsed(){try{return JSON.parse(localStorage.getItem(COLLAPSE_KEY))||{}}catch(e){return{}}}
function _saveCollapsed(state){localStorage.setItem(COLLAPSE_KEY,JSON.stringify(state))}

function initCollapse(){
  const state = _loadCollapsed();
  document.querySelectorAll('.divider[id]').forEach(div => {
    const id = div.id;
    const wrap = document.querySelector(`.section-wrap[data-section="${id}"]`);
    if (!wrap) return;
    /* Restore saved state */
    if (state[id]) {
      div.classList.add('collapsed');
      wrap.classList.add('collapsed');
      wrap.style.maxHeight = '0';
    } else {
      wrap.style.maxHeight = wrap.scrollHeight + 'px';
    }
    div.addEventListener('click', (e) => {
      /* Don't trigger on anchor link clicks inside nav */
      if (e.target.closest('a')) return;
      const isCollapsed = wrap.classList.toggle('collapsed');
      div.classList.toggle('collapsed', isCollapsed);
      const cs = _loadCollapsed();
      if (isCollapsed) {
        wrap.style.maxHeight = wrap.scrollHeight + 'px';
        requestAnimationFrame(() => { wrap.style.maxHeight = '0'; });
        cs[id] = true;
      } else {
        wrap.style.maxHeight = wrap.scrollHeight + 'px';
        cs[id] = false;
        /* Resize charts inside the section after expand animation */
        setTimeout(() => {
          wrap.style.maxHeight = 'none';
          wrap.querySelectorAll('.chart').forEach(el => {
            const c = chartCache[el.id];
            if (c) c.resize();
          });
          /* Trigger lazy observer for charts that haven't rendered yet */
          if (lazyObserver) {
            wrap.querySelectorAll('.chart').forEach(el => {
              if (!lazyRendered.has(el.id)) lazyObserver.observe(el);
            });
          }
        }, 420);
      }
      _saveCollapsed(cs);
    });
  });
}

/* ── Quick nav scroll highlight + back-to-top ── */
function initQuickNav(){
  const backTop = document.getElementById('back-top');
  const navLinks = document.querySelectorAll('.quick-nav a');
  const sectionIds = Array.from(navLinks).map(a => a.getAttribute('href').slice(1));

  window.addEventListener('scroll', () => {
    /* Back-to-top visibility */
    if (backTop) backTop.classList.toggle('show', window.scrollY > 400);
    /* Active section highlight */
    let currentId = sectionIds[0];
    for (const id of sectionIds) {
      const el = document.getElementById(id);
      if (el && el.getBoundingClientRect().top <= 80) currentId = id;
    }
    navLinks.forEach(a => {
      a.classList.toggle('active', a.getAttribute('href') === '#' + currentId);
    });
  }, {passive: true});

  /* Smooth scroll for nav links */
  navLinks.forEach(a => {
    a.addEventListener('click', (e) => {
      e.preventDefault();
      const id = a.getAttribute('href').slice(1);
      const el = document.getElementById(id);
      if (el) {
        /* Expand section if collapsed */
        const wrap = document.querySelector(`.section-wrap[data-section="${id}"]`);
        if (wrap && wrap.classList.contains('collapsed')) {
          el.click();
        }
        el.scrollIntoView({behavior: 'smooth'});
      }
    });
  });
}

/* Update max-height after data re-render (for non-collapsed sections) */
function refreshSectionHeights(){
  document.querySelectorAll('.section-wrap').forEach(wrap => {
    if (!wrap.classList.contains('collapsed')) {
      wrap.style.maxHeight = 'none';
    }
  });
}

bootDashboard();
initCollapse();
initQuickNav();