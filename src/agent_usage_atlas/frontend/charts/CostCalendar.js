function renderCostCalendar(){
  const chart = initChart('cost-calendar-chart');
  const cells = data.days.map(day => [day.date, +day.cost.toFixed(2)]);
  const _updateHighlight = () => {
    chart.setOption({
      series: [{
        type: 'heatmap',
        coordinateSystem: 'calendar',
        data: cells,
        itemStyle: selectedDate ? {
          borderColor: function(params) { return params.value[0] === selectedDate ? '#fff' : 'transparent'; },
          borderWidth: function(params) { return params.value[0] === selectedDate ? 2 : 0; }
        } : undefined
      }]
    });
  };
  chart.setOption({
    ...chartTheme(),
    tooltip: {...chartTheme().tooltip, formatter: params => `${params.value[0]}<br>${fmtUSD(params.value[1])}`},
    visualMap: {min: 0, max: Math.max(...data.days.map(day => day.cost), 1), orient: 'horizontal', left: 'center', bottom: 8, textStyle: {color: TX}, inRange: {color: _isLight() ? ['#f5f0eb','#e8a898','#c0392b','#ff6b6b'] : ['rgba(255,255,255,.04)','#5c3a1e','#c0392b','#ff6b6b']}},
    calendar: {orient: 'vertical', top: 28, left: 36, right: 16, bottom: 48, cellSize: ['auto', 'auto'], range: [data.range.start_local.slice(0, 10), data.range.end_local.slice(0, 10)], yearLabel: {show: false}, monthLabel: {color: TX, ...(lang === 'zh' ? {nameMap: 'ZH'} : {}), margin: 8}, dayLabel: {color: TX, firstDay: 1, ...(lang === 'zh' ? {nameMap: 'ZH'} : {})}, splitLine: {lineStyle: {color: AX}}, itemStyle: {borderWidth: 3, borderColor: _CARD_BG(), color: BG}},
    series: [{type: 'heatmap', coordinateSystem: 'calendar', data: cells}]
  });
  chart.off('click');
  chart.on('click', params => {
    if (params.componentType === 'series' && params.value) {
      setSelectedDate(params.value[0]);
    }
  });
}
