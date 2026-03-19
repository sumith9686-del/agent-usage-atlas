function renderEfficiencyGauges(){
  const em = data.efficiency_metrics || {};
  const summary = (em.summary || {});
  const cacheHit = summary.avg_cache_hit_rate || 0;
  const reasonRatio = summary.avg_reasoning_ratio || 0;
  const savingsRatio = (data.totals || {}).cache_savings_ratio || 0;

  const gauges = [
    {id: 'cache-gauge', value: cacheHit, name: lang === 'zh' ? '缓存命中' : 'Cache Hit', color: C.cacheRead},
    {id: 'reason-gauge', value: reasonRatio, name: lang === 'zh' ? '推理比' : 'Reasoning', color: C.reason},
    {id: 'savings-gauge', value: savingsRatio, name: lang === 'zh' ? '缓存节省' : 'Savings', color: C.output}
  ];

  gauges.forEach(g => {
    const chart = initChart(g.id);
    chart.setOption({
      ...chartTheme(),
      series: [{
        type: 'gauge',
        startAngle: 220,
        endAngle: -40,
        radius: '90%',
        center: ['50%', '55%'],
        min: 0,
        max: 1,
        splitNumber: 5,
        progress: {show: true, width: 10, roundCap: true, itemStyle: {color: g.color}},
        pointer: {show: false},
        axisLine: {lineStyle: {width: 10, color: [[1, _isLight() ? 'rgba(0,0,0,.06)' : 'rgba(255,255,255,.08)']]}},
        axisTick: {show: false},
        splitLine: {show: false},
        axisLabel: {show: false},
        title: {
          offsetCenter: [0, '70%'],
          fontSize: 11,
          fontWeight: 700,
          color: TX
        },
        detail: {
          valueAnimation: true,
          offsetCenter: [0, '20%'],
          fontSize: 20,
          fontWeight: 800,
          formatter: v => (v * 100).toFixed(1) + '%',
          color: TX
        },
        data: [{value: g.value, name: g.name}]
      }]
    });
  });
}
