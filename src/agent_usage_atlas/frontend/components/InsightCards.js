function renderInsights(){
  const insights = data.insights;
  if (!insights || !insights.length) return;
  const el = document.getElementById('insight-cards');
  if (!el) return;

  const severityLabel = {
    high: t('lblInsightHigh'),
    medium: t('lblInsightMedium'),
    low: t('lblInsightLow'),
    info: t('lblInsightInfo'),
  };

  el.innerHTML = insights.map(ins => {
    const title = lang === 'en' ? (ins.title_en || ins.title) : ins.title;
    const body = lang === 'en' ? (ins.body_en || ins.body) : ins.body;
    const action = lang === 'en' ? (ins.action_en || ins.action) : ins.action;
    const sev = ins.severity || 'info';
    return `
      <div class="insight-card ${sev}">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">
          <i class="fa-solid ${ins.icon || 'fa-circle-info'}" style="font-size:16px"></i>
          <strong style="flex:1;font-size:14px">${title}</strong>
          <span class="insight-badge ${sev}">${severityLabel[sev] || sev}</span>
        </div>
        <div style="color:var(--text-secondary);font-size:13px">${body}</div>
        <div class="insight-action">
          <i class="fa-solid fa-wand-magic-sparkles" style="font-size:11px;margin-right:6px;color:var(--accent)"></i>
          <span style="font-size:12px">${action}</span>
        </div>
      </div>
    `;
  }).join('');
}
