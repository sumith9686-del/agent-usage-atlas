function renderTokenCalendar(){
  makeCalendarHeatmap(
    'token-calendar-chart',
    day => [day.date, day.total_tokens],
    params => `${params.value[0]}<br>${fmtInt(params.value[1])} tokens`,
    ['rgba(255,255,255,.03)','#3a4a2e','#51cf66','#a9e34b'],
    ['#edf5ea','#a3d99a','#51cf66','#a9e34b']
  );
}
