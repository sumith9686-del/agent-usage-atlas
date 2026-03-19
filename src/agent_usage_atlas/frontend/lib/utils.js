const fmtInt = n => Number(n || 0).toLocaleString('en-US');
const fmtShort = n => {
  const v = Number(n || 0);
  const a = Math.abs(v);
  if (a >= 1e9) return (v / 1e9).toFixed(2) + 'B';
  if (a >= 1e6) return (v / 1e6).toFixed(2) + 'M';
  if (a >= 1e3) return (v / 1e3).toFixed(1) + 'K';
  return String(Math.round(v));
};
const fmtPct = v => ((Number(v || 0) * 100).toFixed(1)) + '%';
const fmtUSD = v => {
  const value = Number(v || 0);
  if (value >= 1000) return '$' + value.toLocaleString('en-US', {maximumFractionDigits: 0});
  if (value >= 100) return '$' + value.toFixed(1);
  if (value >= 1) return '$' + value.toFixed(2);
  if (value >= 0.01) return '$' + value.toFixed(3);
  return '$' + value.toFixed(4);
};
const _C_DARK = {Codex:'#ff8a50',Claude:'#ffd43b',Cursor:'#748ffc',uncached:'#f4b183',cacheRead:'#51cf66',cacheWrite:'#b197fc',output:'#74c0fc',reason:'#e599f7',cost:'#ff6b6b'};
const _C_LIGHT = {Codex:'#e06830',Claude:'#d4960a',Cursor:'#5a73d9',uncached:'#d4845a',cacheRead:'#2b8a3e',cacheWrite:'#8b6cc0',output:'#3a8fd4',reason:'#c06ad0',cost:'#dc3545'};
const C = new Proxy(_C_DARK, {get(_, key) { return (_isLight() ? _C_LIGHT : _C_DARK)[key]; }});
const _TX = () => _isLight() ? 'rgba(0,0,0,.55)' : 'rgba(255,255,255,.68)';
const _AX = () => _isLight() ? 'rgba(0,0,0,.09)' : 'rgba(255,255,255,.06)';
const _BG = () => _isLight() ? 'rgba(0,0,0,.03)' : 'rgba(255,255,255,.03)';
const _CARD_BG = () => _isLight() ? '#ffffff' : '#0d1016';
const _LINE_ACCENT = () => _isLight() ? 'rgba(0,0,0,.55)' : 'rgba(255,255,255,.75)';
const _LINE_DOT = () => _isLight() ? '#1a1a2e' : '#fff';
/* Backward-compatible: TX/AX/BG are now getters so existing chart code keeps working */
Object.defineProperty(window, 'TX', {get: _TX});
Object.defineProperty(window, 'AX', {get: _AX});
Object.defineProperty(window, 'BG', {get: _BG});
const getTokenSources = () => (data && data.source_cards ? data.source_cards.filter(card => card.token_capable) : []);

/* ── Number transition animation ── */
let _numPrevValues = new WeakMap();
/* Build a locked formatter that keeps the same decimal places / scale throughout animation */
function _lockFmt(formatter, targetVal) {
  const targetStr = formatter(targetVal);
  if (formatter === fmtShort) {
    const a = Math.abs(targetVal);
    if (a >= 1e9) return v => (v / 1e9).toFixed(2) + 'B';
    if (a >= 1e6) return v => (v / 1e6).toFixed(2) + 'M';
    if (a >= 1e3) return v => (v / 1e3).toFixed(1) + 'K';
    return v => String(Math.round(v));
  }
  if (formatter === fmtUSD) {
    const av = Math.abs(targetVal);
    if (av >= 1000) return v => '$' + v.toLocaleString('en-US', {maximumFractionDigits: 0});
    if (av >= 100) return v => '$' + v.toFixed(1);
    if (av >= 1) return v => '$' + v.toFixed(2);
    if (av >= 0.01) return v => '$' + v.toFixed(3);
    return v => '$' + v.toFixed(4);
  }
  if (formatter === fmtPct) {
    return v => ((Number(v || 0) * 100).toFixed(1)) + '%';
  }
  if (formatter === fmtInt) {
    return v => Math.round(v).toLocaleString('en-US');
  }
  return formatter;
}
function animateNum(el, newRaw, formatter) {
  if (!el) return;
  const newVal = Number(newRaw) || 0;
  const oldVal = _numPrevValues.has(el) ? _numPrevValues.get(el) : newVal;
  _numPrevValues.set(el, newVal);
  if (isFirstRender || oldVal === newVal) {
    el.textContent = formatter(newVal);
    return;
  }
  /* Stock-style color flash */
  const dir = newVal > oldVal ? 'num-up' : 'num-down';
  el.classList.remove('num-up', 'num-down');
  /* Force reflow so re-adding the same class restarts the animation */
  void el.offsetWidth;
  el.classList.add(dir);
  const locked = _lockFmt(formatter, newVal);
  const duration = 600;
  const startTime = performance.now();
  const step = (now) => {
    const t = Math.min((now - startTime) / duration, 1);
    const ease = 1 - Math.pow(1 - t, 3);
    const cur = oldVal + (newVal - oldVal) * ease;
    el.textContent = locked(cur);
    if (t < 1) requestAnimationFrame(step);
    else { _numPrevValues.set(el, newVal); el.textContent = formatter(newVal); }
  };
  requestAnimationFrame(step);
}
