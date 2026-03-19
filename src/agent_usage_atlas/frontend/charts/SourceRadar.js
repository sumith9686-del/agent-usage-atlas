function renderSourceRadar(){
  const rows = data.working_patterns.source_radar;
  const chart = initChart('source-radar-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {bottom: 0, textStyle: {color: TX}},
    radar: {
      radius: '62%',
      center: ['50%', '46%'],
      splitNumber: 5,
      axisName: {color: TX, fontSize: 11},
      splitLine: {lineStyle: {color: AX}},
      splitArea: {areaStyle: {color: _isLight() ? ['rgba(0,0,0,.02)','rgba(0,0,0,.01)'] : ['rgba(255,255,255,.02)','rgba(255,255,255,.01)']}},
      indicator: [
        {name: t('radarTotal'), max: Math.max(...rows.map(row => row.total_tokens), 1)},
        {name: t('radarCache'), max: Math.max(...rows.map(row => row.cache_total), 1)},
        {name: t('radarOutput'), max: Math.max(...rows.map(row => row.output_total), 1)},
        {name: t('radarSessions'), max: Math.max(...rows.map(row => row.sessions), 1)}
      ]
    },
    series: [{
      type: 'radar',
      symbol: 'circle',
      symbolSize: 6,
      areaStyle: {opacity: .08},
      lineStyle: {width: 2},
      data: rows.map(row => ({
        name: row.name,
        value: [row.total_tokens, row.cache_total, row.output_total, row.sessions],
        lineStyle: {color: C[row.name] || '#888'},
        itemStyle: {color: C[row.name] || '#888'},
        areaStyle: {color: C[row.name] || '#888', opacity: .08}
      }))
    }]
  });
}
