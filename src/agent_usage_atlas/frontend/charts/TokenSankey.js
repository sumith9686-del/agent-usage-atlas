function renderTokenSankey(){
  const chart = initChart('token-sankey-chart');
  chart.setOption({
    ...chartTheme(),
    series: [{
      type: 'sankey',
      left: 8,
      right: 8,
      top: 24,
      bottom: 12,
      nodeWidth: 18,
      nodeGap: 14,
      lineStyle: {color: 'gradient', curveness: .45, opacity: .28},
      label: {color: _LINE_DOT(), fontSize: 11},
      data: data.trend_analysis.token_sankey.nodes.map(node => ({
        name: node.name,
        itemStyle: {color: C[node.name] || {'Uncached Input': C.uncached, 'Cache Read': C.cacheRead, 'Cache Write': C.cacheWrite, 'Output': C.output, 'Reasoning': C.reason}[node.name] || '#888'}
      })),
      links: data.trend_analysis.token_sankey.links
    }]
  });
  const snKey = lang === 'en' ? 'source_notes_en' : 'source_notes';
  const jkKey = lang === 'en' ? 'jokes_en' : 'jokes';
  document.getElementById('source-notes').innerHTML = [
    ...(data.story[snKey] || data.story.source_notes).map(txt => `<div class="note"><i class="fa-solid fa-circle-info"></i><div>${txt}</div></div>`),
    ...(data.story[jkKey] || data.story.jokes).map(txt => `<div class="note"><i class="fa-solid fa-face-smile"></i><div>${txt}</div></div>`)
  ].join('');
}
