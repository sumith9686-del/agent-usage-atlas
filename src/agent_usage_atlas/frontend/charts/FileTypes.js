function renderFileTypesChart(){
  const rows = data.projects.file_types.slice(0, 12);
  const chart = initChart('file-types-chart');
  chart.setOption({
    ...chartTheme(),
    legend: {bottom: 0, textStyle: {color: TX}},
    tooltip: {...chartTheme().tooltip, formatter: params => `${params.name}<br>${fmtInt(params.value)} touches`},
    series: [{
      type: 'pie',
      radius: ['34%', '72%'],
      center: ['50%', '45%'],
      label: {color: TX},
      itemStyle: {borderRadius: 8, borderColor: _CARD_BG(), borderWidth: 3},
      data: rows.map((row, index) => ({
        name: row.extension,
        value: row.count,
        itemStyle: {color: ['#74c0fc','#ff8a50','#ffd43b','#51cf66','#b197fc','#e599f7','#ffa94d','#94d82d','#4dabf7','#ff8787','#fcc419','#9775fa'][index % 12]}
      }))
    }]
  });
}
