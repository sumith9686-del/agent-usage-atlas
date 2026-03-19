let data = __DATA__;


const pageParams = new URLSearchParams(window.location.search);
const baseRangeParams = new URLSearchParams();
if (pageParams.get('days')) baseRangeParams.set('days', pageParams.get('days'));
if (pageParams.get('since')) baseRangeParams.set('since', pageParams.get('since'));
const baseInterval = pageParams.get('interval');
const defaultDays = Number(baseRangeParams.get('days')) || 30;
const defaultSince = baseRangeParams.get('since') || null;

/* Active range tab state */
let activeRangeKey = 'all'; /* 'all' | 'today' */
function _dateFmt(d) {
  return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
}
function _buildParams(rangeKey) {
  const p = new URLSearchParams();
  if (rangeKey === 'today') {
    p.set('since', _dateFmt(new Date()));
  } else if (rangeKey === '3day') {
    p.set('days', '3');
  } else if (rangeKey === 'week') {
    p.set('days', '7');
  } else {
    if (defaultSince) p.set('since', defaultSince);
    else p.set('days', String(defaultDays));
  }
  if (baseInterval) p.set('interval', baseInterval);
  return p;
}
function _apiUrl(rangeKey) {
  const p = _buildParams(rangeKey);
  p.delete('interval');
  return '/api/dashboard' + (p.toString() ? `?${p}` : '');
}
function _streamUrl(rangeKey) {
  const p = _buildParams(rangeKey);
  return '/api/dashboard/stream' + (p.toString() ? `?${p}` : '');
}
let dashboardApiUrl = _apiUrl('all');
let dashboardStreamUrl = _streamUrl('all');
const isLiveMode = data === null;
let lastDashboardHash = '';
let refreshTimer = null;
let streamSource = null;
let isStreamConnected = false;
const charts = [];
const chartCache = {};

/* ── Date drill-down filter (cost family) ── */
let selectedDate = null;
const _dateFilterListeners = [];
function onDateFilter(fn) { _dateFilterListeners.push(fn); }
function setSelectedDate(date) {
  selectedDate = (date === selectedDate) ? null : date;
  _dateFilterListeners.forEach(fn => fn(selectedDate));
}

function setDashboard(nextData){
  if (!nextData || typeof nextData !== 'object') {
    return false;
  }
  const meta = nextData._meta;
  const hash = meta ? meta.generated_at : '';
  if (!data) {
    data = nextData;
    lastDashboardHash = hash;
    return true;
  }
  if (hash && hash === lastDashboardHash) {
    return false;
  }
  data = nextData;
  lastDashboardHash = hash;
  return true;
}
