function renderCodegenModelChart(){
  const ext = data && data.extended;
  if (!ext || !ext.cursor_codegen || !ext.cursor_codegen.total) return;
  const rows = ext.cursor_codegen.by_model;
  if (!rows || !rows.length) return;
  const colors = ['#ff8a50','#ffd43b','#74c0fc','#51cf66','#b197fc','#e599f7','#ff6b6b','#f4b183'];
  makeHorizontalBar('codegen-model-chart', {
    rows: rows.slice(0, 8),
    labelFn: r => r.model,
    valueFn: r => r.count,
    color: colors,
    leftMargin: 8,
    rightMargin: 24,
    bottomMargin: 44,
    containLabel: true,
    labelWidth: 140,
    tooltipOpts: {trigger: 'axis'}
  });
}
