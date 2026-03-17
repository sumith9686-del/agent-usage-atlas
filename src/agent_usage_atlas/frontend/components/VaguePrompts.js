function renderVaguePrompts(){
  const p = data.prompts;
  if (!p) return;
  const el = document.getElementById('vague-stats');
  if (!el) return;
  el.innerHTML = [
    {lbl: t('lblVagueCount'), val: fmtInt(p.vague_count), hint: t('hintVagueCount', {total: fmtInt(p.total_user_messages)}), cls: 'cost'},
    {lbl: t('lblVagueRatio'), val: fmtPct(p.vague_ratio), hint: t('hintVagueRatio', {count: fmtInt(p.vague_count), total: fmtInt(p.total_user_messages)}), cls: 'cost'},
    {lbl: t('lblWastedTokens'), val: fmtShort(p.estimated_wasted_tokens), hint: t('hintWastedTokens'), cls: 'cost'},
    {lbl: t('lblWastedCost'), val: fmtUSD(p.estimated_wasted_cost), hint: t('hintWastedCost'), cls: 'cost'},
  ].map(c => `
    <article class="cc ${c.cls}">
      <div class="metric-k">${c.lbl}</div>
      <div class="big">${c.val}</div>
      <div class="tiny">${c.hint}</div>
    </article>
  `).join('');

  const listEl = document.getElementById('vague-list');
  if (!listEl) return;
  const items = (p.top_vague_prompts || []);
  if (!items.length) {
    listEl.innerHTML = '<div class="tiny" style="padding:12px">No vague prompts detected.</div>';
    return;
  }
  listEl.innerHTML = items.map((item, i) => `
    <div class="vague-row">
      <span class="vague-text">"${_escHtml(item.text)}"</span>
      <span class="vague-count">${item.count}x</span>
    </div>
  `).join('');
}
function _escHtml(s){return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');}
