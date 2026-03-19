function renderProjectRanking(){
  if (!data || !data.projects || !data.projects.ranking) return;
  makeHorizontalBar('project-ranking-chart', {
    rows: data.projects.ranking.slice(0, 15),
    labelFn: row => row.project,
    valueFn: row => row.total_tokens,
    color: '#74c0fc',
    leftMargin: 140,
    tooltipFmt: value => fmtShort(value),
    xAxisFmt: value => fmtShort(value),
    labelFmt: params => fmtShort(params.value)
  });
}
