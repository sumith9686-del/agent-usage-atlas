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

  /* ── hero-stats mini grid ── */
  const heroStatsDefs = [
    {id: 'hs-sessions', label: t('lblHeroSessions'), value: T.tracked_session_count, fmt: fmtInt},
    {id: 'hs-projects', label: t('lblHeroProjects'), value: T.project_count, fmt: fmtInt},
    {id: 'hs-days', label: t('lblHeroDays'), value: data.range.day_count, fmt: fmtInt},
    {id: 'hs-burn', label: t('lblHeroAvgBurn'), value: T.avg_daily_burn, fmt: fmtUSD, suffix: '/d'}
  ];
  const hsEl = document.getElementById('hero-stats');
  if (!document.getElementById('hs-sessions')) {
    hsEl.innerHTML = heroStatsDefs.map(c =>
      `<div class="hero-stat"><div class="k">${c.label}</div><div class="v" id="${c.id}"></div></div>`
    ).join('');
  }
  heroStatsDefs.forEach(c => {
    const el = document.getElementById(c.id);
    if (el) {
      if (c.suffix) {
        animateNum(el, c.value, v => c.fmt(v) + c.suffix);
      } else {
        animateNum(el, c.value, c.fmt);
      }
    }
  });

  /* ── source proportion bar ── */
  const sbEl = document.getElementById('source-bar');
  if (data.source_cards && data.source_cards.length && T.grand_total > 0 && !sbEl.querySelector('.source-bar')) {
    const segs = data.source_cards.map(card => {
      const pct = (card.total / T.grand_total * 100);
      const name = card.source.toLowerCase();
      return {name, pct, label: card.source};
    }).filter(s => s.pct > 0);
    sbEl.innerHTML =
      `<div class="source-bar">${segs.map(s =>
        `<div class="seg" style="width:${s.pct.toFixed(2)}%;background:var(--${s.name})"></div>`
      ).join('')}</div>` +
      `<div class="source-bar-legend">${segs.map(s =>
        `<span class="source-bar-label"><span class="sbl-dot" style="background:var(--${s.name})"></span>${s.label} ${s.pct.toFixed(1)}%</span>`
      ).join('')}</div>`;
  }
}
