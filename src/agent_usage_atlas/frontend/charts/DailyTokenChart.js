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
      {name: t('seriesCumulative'), type: 'line', yAxisIndex: 1, smooth: true, symbolSize: 6, lineStyle: {width: 3, color: _LINE_ACCENT()}, itemStyle: {color: _LINE_DOT()}, areaStyle: {color: _isLight() ? 'rgba(0,0,0,.04)' : 'rgba(255,255,255,.05)'}, data: data.days.map(day => day.cumulative_tokens)}
    ]
  });
}
