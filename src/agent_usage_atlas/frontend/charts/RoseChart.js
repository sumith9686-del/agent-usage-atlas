function renderRoseChart(){
  const chart = initChart('rose-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {bottom: 0, textStyle: {color: TX}},
    series: [{
      type: 'pie',
      radius: ['24%', '74%'],
      center: ['50%', '46%'],
      roseType: 'radius',
      itemStyle: {borderRadius: 10, borderColor: _CARD_BG(), borderWidth: 3},
      label: {color: TX, formatter: params => `${params.name}\n${params.percent}%`},
      data: data.source_cards.map(card => ({
        name: card.source,
        value: card.token_capable ? card.total : Math.max(card.messages, 1),
        itemStyle: {color: C[card.source] || '#888'}
      }))
    }]
  });
}
