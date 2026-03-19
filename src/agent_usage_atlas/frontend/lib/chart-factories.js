/**
 * Chart factory functions for reducing boilerplate across chart files.
 * makeCalendarHeatmap — shared setup for CostCalendar / TokenCalendar
 * makeHorizontalBar   — shared setup for horizontal bar charts
 */

/**
 * Create a calendar heatmap chart.
 * @param {string} containerId - DOM element id
 * @param {function} dataMapper - (day) => [dateStr, value]
 * @param {function} tooltipFmt - (params) => tooltip string
 * @param {string[]} colorRange - array of colors for visualMap inRange
 * @param {string[]} lightColorRange - array of colors for light theme
 * @returns {object|null} ECharts instance or null if data missing
 */
function makeCalendarHeatmap(containerId, dataMapper, tooltipFmt, colorRange, lightColorRange) {
  if (!data || !data.days || !data.days.length || !data.range) return null;
  const chart = initChart(containerId);
  const cells = data.days.map(dataMapper);
  const maxVal = Math.max(...cells.map(c => c[1]), 1);
  chart.setOption({
    ...chartTheme(),
    tooltip: {...chartTheme().tooltip, formatter: tooltipFmt},
    visualMap: {
      min: 0, max: maxVal, orient: 'horizontal', left: 'center', bottom: 8,
      textStyle: {color: TX},
      inRange: {color: _isLight() ? (lightColorRange || colorRange) : colorRange}
    },
    calendar: {
      orient: 'vertical', top: 28, left: 36, right: 16, bottom: 48,
      cellSize: ['auto', 'auto'],
      range: [data.range.start_local.slice(0, 10), data.range.end_local.slice(0, 10)],
      yearLabel: {show: false},
      monthLabel: {color: TX, ...(lang === 'zh' ? {nameMap: 'ZH'} : {}), margin: 8},
      dayLabel: {color: TX, firstDay: 1, ...(lang === 'zh' ? {nameMap: 'ZH'} : {})},
      splitLine: {lineStyle: {color: AX}},
      itemStyle: {borderWidth: 3, borderColor: _CARD_BG(), color: BG}
    },
    series: [{type: 'heatmap', coordinateSystem: 'calendar', data: cells}]
  });
  return chart;
}

/**
 * Create a horizontal bar chart.
 * @param {string} containerId - DOM element id
 * @param {object} opts
 * @param {Array} opts.rows - data rows
 * @param {function} opts.labelFn - (row) => label string
 * @param {function} opts.valueFn - (row) => numeric value
 * @param {function|string|string[]} opts.color - color string, array (indexed), or (row, index) => color
 * @param {number} [opts.leftMargin=120] - grid left margin
 * @param {function} [opts.tooltipFmt] - tooltip value formatter
 * @param {function} [opts.labelFmt] - bar label formatter
 * @param {function} [opts.xAxisFmt] - x-axis label formatter
 * @param {number} [opts.labelWidth] - y-axis label width (overflow: truncate)
 * @param {object} [opts.tooltipOpts] - extra tooltip config
 * @returns {object|null} ECharts instance or null if no data
 */
function makeHorizontalBar(containerId, opts) {
  if (!opts.rows || !opts.rows.length) return null;
  const chart = initChart(containerId);
  const rows = opts.rows;
  const labels = rows.map(opts.labelFn).reverse();
  const _getColor = (row, i) => {
    if (typeof opts.color === 'function') return opts.color(row, i);
    if (Array.isArray(opts.color)) return opts.color[i % opts.color.length];
    return opts.color || '#ffd43b';
  };
  const barData = rows.map((row, i) => ({
    value: opts.valueFn(row),
    itemStyle: {color: _getColor(row, i), borderRadius: [0, 6, 6, 0]}
  })).reverse();

  const seriesConfig = {
    type: 'bar',
    barMaxWidth: 22,
    data: barData,
    label: {show: true, position: 'right', color: TX, fontSize: 11}
  };
  if (opts.labelFmt) {
    seriesConfig.label.formatter = opts.labelFmt;
  }

  const yAxisConfig = {
    type: 'category', data: labels,
    axisLabel: {color: TX, fontSize: 11}
  };
  if (opts.labelWidth) {
    yAxisConfig.axisLabel.width = opts.labelWidth;
    yAxisConfig.axisLabel.overflow = 'truncate';
  }

  const chartOpts = {
    ...chartTheme(),
    grid: {top: 24, left: opts.leftMargin || 120, right: opts.rightMargin || 60, bottom: opts.bottomMargin || 24, ...(opts.containLabel ? {containLabel: true} : {})},
    xAxis: {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX}},
    yAxis: yAxisConfig,
    series: [seriesConfig]
  };
  if (opts.xAxisFmt) {
    chartOpts.xAxis.axisLabel.formatter = opts.xAxisFmt;
  }
  if (opts.tooltipFmt) {
    chartOpts.tooltip = {...chartTheme().tooltip, valueFormatter: opts.tooltipFmt};
  }
  if (opts.tooltipOpts) {
    chartOpts.tooltip = {...chartTheme().tooltip, ...opts.tooltipOpts};
  }

  chart.setOption(chartOpts);
  return chart;
}
