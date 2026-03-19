function renderModelCostChart(){
  if (!data || !data.trend_analysis || !data.trend_analysis.model_costs) return;
  const palette = ['#ff6b6b','#ff8a50','#ffa94d','#ffd43b','#a9e34b','#51cf66','#74c0fc','#748ffc','#b197fc','#e599f7'];
  makeHorizontalBar('model-cost-chart', {
    rows: data.trend_analysis.model_costs.slice(0, 10),
    labelFn: row => row.model,
    valueFn: row => row.cost,
    color: palette,
    leftMargin: 170,
    tooltipFmt: value => fmtUSD(value),
    xAxisFmt: value => fmtUSD(value),
    labelFmt: params => fmtUSD(params.value),
    labelWidth: 150
  });
}
