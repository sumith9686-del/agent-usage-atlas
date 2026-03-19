/* ── Token Burn Curve — stock-chart style with interval tabs & MA lines ── */
function _movingAvg(arr, w) {
  const out = [];
  for (let i = 0; i < arr.length; i++) {
    if (i < w - 1) { out.push(null); continue; }
    let s = 0;
    for (let j = i - w + 1; j <= i; j++) s += arr[j];
    out.push(+(s / w).toFixed(1));
  }
  return out;
}

/* Derive display label from compact time key "2026-03-15 14:30" → "03/15 14:30" */
function _burnLabel(t) {
  const parts = t.split(' ');
  return parts[0].slice(5).replace('-', '/') + ' ' + parts[1];
}

let _burnInterval = '5';

function _getBurnBins() {
  const multi = data.token_burn;
  if (multi && multi[_burnInterval]) return multi[_burnInterval];
  return [];
}

function _buildBurnOption(bins) {
  const labels = bins.map(b => _burnLabel(b.t));
  const totals = bins.map(b => b.v);
  const costs = bins.map(b => b.c || 0);

  /* MA multipliers: 3x (short/fast), 5x (mid), 8x (long/slow)
     Colors: short=bright green, mid=amber, long=magenta — all high-contrast vs blue/red bars */
  const base = Math.max(2, Math.round(bins.length / 30));
  const maWindows = [
    {mul: 3, w: Math.max(3, base * 3), color: '#00e676'},
    {mul: 5, w: Math.max(5, base * 5), color: '#ffab00'},
    {mul: 8, w: Math.max(8, base * 8), color: '#e040fb'}
  ];

  const maSeries = maWindows.map(({mul, w, color}) => ({
    name: `MA(${mul}x)`,
    type: 'line',
    data: _movingAvg(totals, w),
    smooth: true,
    symbol: 'none',
    lineStyle: {width: 2, color, type: 'solid'},
    itemStyle: {color},
    z: 10
  }));

  return {
    ...chartTheme(),
    legend: {top: 6, textStyle: {color: TX, fontSize: 11}, itemGap: 16},
    grid: {top: 52, left: 60, right: 60, bottom: 44},
    tooltip: {
      ...chartTheme().tooltip,
      trigger: 'axis',
      axisPointer: {type: 'cross'},
      formatter: params => {
        const idx = params[0].dataIndex;
        let s = `<b>${bins[idx].t}</b><br>`;
        params.forEach(p => {
          if (p.value == null) return;
          const isCost = p.seriesName.includes('Cost') || p.seriesName.includes('花费');
          const v = isCost ? fmtUSD(p.value) : fmtShort(p.value);
          s += `${p.marker} ${p.seriesName}: ${v}<br>`;
        });
        return s;
      }
    },
    dataZoom: [
      {type: 'inside', start: 0, end: 100},
      {type: 'slider', height: 20, bottom: 4, borderColor: AX,
        fillerColor: _isLight() ? 'rgba(0,0,0,.08)' : 'rgba(255,255,255,.08)',
        handleStyle: {color: _LINE_ACCENT()}}
    ],
    xAxis: {
      type: 'category', data: labels,
      axisLine: {lineStyle: {color: AX}},
      axisTick: {show: false},
      axisLabel: {color: TX, rotate: 45, fontSize: 10}
    },
    yAxis: [
      {type: 'value', splitLine: {lineStyle: {color: AX}}, axisLabel: {color: TX, formatter: v => fmtShort(v)}},
      {type: 'value', splitLine: {show: false}, axisLabel: {color: TX, formatter: v => '$' + (v >= 1 ? v.toFixed(1) : v.toFixed(2))}}
    ],
    series: [
      {name: t('seriesBurnRate'), type: 'bar', data: totals, itemStyle: {color: C.output, borderRadius: [2, 2, 0, 0]}, barMaxWidth: 6, opacity: 0.85},
      {name: t('seriesBurnCost'), type: 'bar', yAxisIndex: 1, data: costs, itemStyle: {color: C.cost, borderRadius: [2, 2, 0, 0]}, barMaxWidth: 6, opacity: 0.7},
      ...maSeries
    ]
  };
}

function _initBurnTabs() {
  const wrap = document.getElementById('burn-interval-tabs');
  if (!wrap) return;
  const intervals = ['1', '3', '5', '15', '30', '60'];
  const labelKeys = {
    '1': 'burnInterval1', '3': 'burnInterval3', '5': 'burnInterval5',
    '15': 'burnInterval15', '30': 'burnInterval30', '60': 'burnInterval60'
  };
  wrap.innerHTML = intervals.map(iv =>
    `<button class="burn-tab${iv === _burnInterval ? ' active' : ''}" data-iv="${iv}">${t(labelKeys[iv])}</button>`
  ).join('');
  wrap.querySelectorAll('.burn-tab').forEach(btn => {
    btn.addEventListener('click', () => {
      if (btn.dataset.iv === _burnInterval) return;
      _burnInterval = btn.dataset.iv;
      wrap.querySelectorAll('.burn-tab').forEach(b => b.classList.toggle('active', b.dataset.iv === _burnInterval));
      const bins = _getBurnBins();
      if (bins.length) {
        const chart = chartCache['token-burn-curve'];
        if (chart) chart.setOption(_buildBurnOption(bins), true);
      }
    });
  });
}

function renderTokenBurnCurve() {
  const bins = _getBurnBins();
  if (!bins || !bins.length) return;
  _initBurnTabs();
  const chart = initChart('token-burn-curve');
  chart.setOption(_buildBurnOption(bins));
}
