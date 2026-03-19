function renderBranchActivityChart(){
  if (!data || !data.projects || !data.projects.branch_activity) return;
  makeHorizontalBar('branch-activity-chart', {
    rows: data.projects.branch_activity.slice(0, 12),
    labelFn: row => row.branch,
    valueFn: row => row.sessions,
    color: '#b197fc'
  });
}
