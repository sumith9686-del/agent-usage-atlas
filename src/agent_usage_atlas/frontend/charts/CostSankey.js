function renderCostSankey(){
  const chart = initChart('cost-sankey-chart');
  chart.setOption({
    ...chartTheme(),
    tooltip: {...chartTheme().tooltip, valueFormatter: value => fmtUSD(value)},
    series: [{
      type: 'sankey',
      left: 8,
      right: 8,
      top: 24,
      bottom: 12,
      nodeWidth: 18,
      nodeGap: 14,
      lineStyle: {color: 'gradient', curveness: .45, opacity: .3},
      label: {color: _LINE_DOT(), fontSize: 11},
      data: data.trend_analysis.cost_sankey.nodes.map(node => ({
        name: node.name,
        itemStyle: {color: C[node.name] || ['Input Cost','Cache Read','Cache Write','Output','Reasoning'].includes(node.name)
          ? { 'Input Cost': C.uncached, 'Cache Read': C.cacheRead, 'Cache Write': C.cacheWrite, 'Output': C.output, 'Reasoning': C.reason }[node.name]
          : '#888'}
      })),
      links: data.trend_analysis.cost_sankey.links
    }]
  });
}
