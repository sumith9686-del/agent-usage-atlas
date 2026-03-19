function renderModelRadarChart(){
  const rows = data.trend_analysis.model_radar;
  const chart = initChart('model-radar-chart');
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
        {name: t('radarInput'), max: 1},
        {name: t('radarOutput'), max: 1},
        {name: t('radarCache'), max: 1},
        {name: t('radarCost'), max: 1},
        {name: t('radarMsgs'), max: 1}
      ]
    },
    series: [{
      type: 'radar',
      symbol: 'circle',
      symbolSize: 5,
      lineStyle: {width: 2},
      areaStyle: {opacity: .08},
      data: rows.map((row, index) => ({
        name: row.name,
        value: row.normalized,
        lineStyle: {color: ['#ff6b6b','#ff8a50','#ffd43b','#74c0fc','#b197fc'][index % 5]},
        itemStyle: {color: ['#ff6b6b','#ff8a50','#ffd43b','#74c0fc','#b197fc'][index % 5]},
        areaStyle: {color: ['#ff6b6b','#ff8a50','#ffd43b','#74c0fc','#b197fc'][index % 5], opacity: .08}
      }))
    }]
  });
}

/* ── Extended Analytics charts ── */