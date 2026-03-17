function renderExpensivePrompts(){
  const p = data.prompts;
  if (!p) return;
  const el = document.getElementById('expensive-table');
  if (!el) return;
  const rows = (p.expensive_prompts || []).slice(0, 30);
  if (!rows.length) {
    el.innerHTML = '<tbody><tr><td class="tiny" style="padding:12px">No prompt cost data available.</td></tr></tbody>';
    return;
  }
  el.innerHTML = `
    <thead>
      <tr>
        <th>${t('tblRank')}</th>
        <th>${t('tblPrompt')}</th>
        <th>${t('tblPromptTokens')}</th>
        <th>${t('tblPromptCost')}</th>
        <th>${t('tblPromptModel')}</th>
        <th>${t('tblPromptSource')}</th>
      </tr>
    </thead>
    <tbody>
      ${rows.map((row, i) => `
        <tr>
          <td style="color:var(--text-muted);font-weight:700">${i + 1}</td>
          <td title="${_escHtml(row.text)}" style="max-width:260px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px">${_escHtml(row.text.slice(0, 60))}${row.text.length > 60 ? '...' : ''}</td>
          <td>${fmtShort(row.tokens)}</td>
          <td style="color:var(--cost);font-weight:700">${fmtUSD(row.cost)}</td>
          <td style="font-size:11px">${row.model}</td>
          <td>${row.source}</td>
        </tr>
      `).join('')}
    </tbody>`;
}
