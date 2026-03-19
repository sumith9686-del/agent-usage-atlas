function renderTimeline(){
  const timeline = data.working_patterns.timeline;
  const chart = initChart('timeline-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {top: 4, textStyle: {color: TX}},
    grid: {top: 54, left: 56, right: 24, bottom: 46},
    tooltip: {...chartTheme().tooltip, trigger: 'axis'},
    xAxis: {type: 'category', data: timeline.days.map(day => day.label), axisLine: {lineStyle: {color: AX}}, axisTick: {show: false}, axisLabel: {color: TX}},
    yAxis: [
      {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: value => fmtShort(value)}},
      {type: 'value', splitLine: {show: false}, axisLabel: {color: TX, formatter: value => fmtShort(value)}}
    ],
    series: [
      {name: t('seriesDailyTotal'), type: 'bar', barMaxWidth: 24, itemStyle: {color: 'rgba(255,138,80,.32)', borderRadius: [6, 6, 0, 0]}, data: timeline.days.map(day => day.total_tokens)},
      {
        name: t('seriesCumulative'),
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbolSize: 6,
        lineStyle: {width: 3, color: _LINE_ACCENT()},
        itemStyle: {color: _LINE_DOT()},
        data: timeline.days.map(day => day.cumulative_tokens),
        markPoint: {
          symbol: 'pin',
          symbolSize: 38,
          label: {color: '#fff', fontSize: 10, formatter: params => fmtShort(params.value)},  /* white on pin is ok */
          itemStyle: {color: C.Codex},
          data: timeline.peak_markers.map(marker => ({name: marker.label, coord: [marker.label, marker.cumulative_tokens], value: marker.total_tokens}))
        }
      }
    ]
  });
}
