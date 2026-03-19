function renderToolRanking(){
  if (!data || !data.tooling || !data.tooling.ranking) return;
  makeHorizontalBar('tool-ranking-chart', {
    rows: data.tooling.ranking.slice(0, 20),
    labelFn: row => row.name,
    valueFn: row => row.count,
    color: '#ffd43b'
  });
}
