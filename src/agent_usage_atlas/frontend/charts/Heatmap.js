function renderHeatmap(){
  const chart = initChart('heatmap-chart');
  const points = [];
  data.working_patterns.heatmap.forEach((row, y) => row.values.forEach((value, x) => points.push([x, y, value])));
  chart.setOption({
    ...chartTheme(),
    grid: {top: 44, left: 70, right: 24, bottom: 34},
    xAxis: {type: 'category', data: Array.from({length: 24}, (_, i) => `${i}`), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}},
    yAxis: {type: 'category', data: data.working_patterns.heatmap.map(row => row.weekday), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}},
    visualMap: {min: 0, max: Math.max(...points.map(point => point[2]), 1), orient: 'horizontal', left: 'center', bottom: 0, textStyle: {color: TX}, inRange: {color: _isLight() ? ['#f5f0eb','#e8c99b','#ff8a50','#ffd43b'] : ['rgba(255,255,255,.03)','#5c3a1e','#ff8a50','#ffd43b']}},
    series: [{type: 'heatmap', data: points, itemStyle: {borderRadius: 6, borderColor: _CARD_BG(), borderWidth: 3}}]
  });
}
