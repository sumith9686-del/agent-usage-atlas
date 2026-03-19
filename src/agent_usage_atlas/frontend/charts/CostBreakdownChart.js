function renderCostBreakdownChart(){
  const chart = initChart('cost-breakdown-chart');
  const _buildItems = (filterDate) => {
    if (filterDate) {
      const day = data.days.find(d => d.date === filterDate);
      if (!day) return [];
      const cbd = day.cost_breakdown || {};
      return [
        {name: 'Uncached Input', value: cbd.input || 0, color: C.uncached},
        {name: 'Cache Read', value: cbd.cache_read || 0, color: C.cacheRead},
        {name: 'Cache Write', value: cbd.cache_write || 0, color: C.cacheWrite},
        {name: 'Output', value: cbd.output || 0, color: C.output},
        {name: 'Reasoning', value: cbd.reasoning || 0, color: C.reason}
      ].filter(item => item.value > 0);
    }
    const T = data.totals;
    return [
      {name: 'Uncached Input', value: T.cost_input, color: C.uncached},
      {name: 'Cache Read', value: T.cost_cache_read, color: C.cacheRead},
      {name: 'Cache Write', value: T.cost_cache_write, color: C.cacheWrite},
      {name: 'Output', value: T.cost_output, color: C.output},
      {name: 'Reasoning', value: T.cost_reasoning, color: C.reason}
    ].filter(item => item.value > 0);
  };
  const _applyFilter = (filterDate) => {
    const items = _buildItems(filterDate);
    chart.setOption({
      series: [{
        data: items.map(item => ({name: item.name, value: +item.value.toFixed(4), itemStyle: {color: item.color}}))
      }]
    });
  };
  const items = _buildItems(null);
  chart.setOption({
    ...chartTheme(),
    legend: {bottom: 0, textStyle: {color: TX}},
    tooltip: {...chartTheme().tooltip, formatter: params => `${params.name}<br>${fmtUSD(params.value)} (${params.percent}%)`},
    series: [{
      type: 'pie',
      radius: ['40%', '74%'],
      center: ['50%', '45%'],
      itemStyle: {borderRadius: 10, borderColor: _CARD_BG(), borderWidth: 3},
      label: {color: TX, formatter: params => `${params.name}\n${params.percent}%`},
      data: items.map(item => ({name: item.name, value: +item.value.toFixed(4), itemStyle: {color: item.color}}))
    }]
  });
  onDateFilter(_applyFilter);
}
