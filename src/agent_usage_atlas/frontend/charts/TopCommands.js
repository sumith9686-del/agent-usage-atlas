function renderTopCommands(){
  if (!data || !data.commands || !data.commands.top_commands) return;
  makeHorizontalBar('top-commands-chart', {
    rows: data.commands.top_commands.slice(0, 15),
    labelFn: row => row.command,
    valueFn: row => row.count,
    color: (row) => row.failure_rate > .3 ? '#ff6b6b' : '#51cf66',
    leftMargin: 110
  });
}
