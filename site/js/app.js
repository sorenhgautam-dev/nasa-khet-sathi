/* Khet Sathi: the static site (plain JavaScript, no build step, no key, no server).
   Every number and sentence on screen comes from site/data/: fields/<id>.json, words.json, index.json, area/<id>.json,
   story.json, probe_log.json and live.json (the last three only when they exist). Text goes on the page with
   textContent; innerHTML is used only for the static icons written in this file. Every fetch path is relative. */
(function () {
  'use strict';
  var D = document, W = window;
  var RM = !!(W.matchMedia && W.matchMedia('(prefers-reduced-motion: reduce)').matches);
  // the UI teammate's seven steps are the app (owner, 2026-11-14 evening); the features live inside them and on "How we know"
  var STEPS = ['home', 'photo', 'parts', 'soil', 'choose', 'today', 'next'];
  // weather: "Weather ahead", the Choose screen's extra choice (owner, 2026-11-14 evening)
  var ROUTES = STEPS.concat(['weather', 'how', 'plan', 'trial', 'world']);
  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  // sun x, sun y, tint, sunset, road progress (the phone prototype P0, per step)
  var SKY = { home: [30, 300, 0, 0, 0], photo: [79, 197, 0, 0, 0.16], parts: [131, 119, 0, 0, 0.33], soil: [183, 81, 0.05, 0.1, 0.5],
    choose: [236, 96, 0.15, 0.3, 0.66], today: [288, 159, 0.4, 0.65, 0.84], next: [325, 223, 0.65, 0.95, 1], weather: [325, 223, 0.65, 0.95, 1],
    how: [325, 223, 0.5, 0.8, 1], world: [325, 223, 0.5, 0.8, 1] };
  var S = { lang: 'ne', words: null, index: null, fid: null, field: null, fieldP: null, winter: null, water: null, prio: null,
    timers: [], cur: null, arg: null, prev: null, sheetFor: null };

  // ---------------- small helpers ----------------
  var store = {
    get: function (k) { try { return W.localStorage.getItem('ks.' + k); } catch (e) { return null; } },
    set: function (k, v) { try { if (v == null) W.localStorage.removeItem('ks.' + k); else W.localStorage.setItem('ks.' + k, v); } catch (e) { /* private window */ } }
  };
  var jsonCache = {};
  function getJSON(path, fresh) {
    if (!fresh && jsonCache[path]) return jsonCache[path];
    var p = fetch(path, fresh ? { cache: 'no-store' } : undefined)
      .then(function (r) { return r.ok ? r.json() : null; })
      .catch(function () { return null; });
    if (!fresh) jsonCache[path] = p;
    return p;
  }
  function $(s, r) { return (r || D).querySelector(s); }
  function h(tag, a) {
    var el = D.createElement(tag);
    if (a) Object.keys(a).forEach(function (k) {
      var v = a[k];
      if (v == null || v === false) return;
      if (k === 'class') el.className = v;
      else if (k === 'style') el.setAttribute('style', v);
      else if (k === 'text') el.textContent = v;
      else if (k.slice(0, 2) === 'on') el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? '' : v);
    });
    for (var i = 2; i < arguments.length; i++) add(el, arguments[i]);
    return el;
  }
  function add(el, c) {
    if (c == null || c === false || c === '') return el;
    if (Array.isArray(c)) { c.forEach(function (x) { add(el, x); }); return el; }
    el.appendChild(typeof c === 'object' ? c : D.createTextNode(String(c)));
    return el;
  }
  // an icon: a static SVG string written in this file (never data)
  function svg(str, cls) { var s = D.createElement('span'); s.className = 'ico' + (cls ? ' ' + cls : ''); s.setAttribute('aria-hidden', 'true'); s.innerHTML = str; s.style.display = 'inline-flex'; s.style.lineHeight = '0'; return s; }
  function later(fn, ms) { var t = setTimeout(fn, RM ? 0 : ms); S.timers.push(t); return t; }
  function every(fn, ms) { var t = setInterval(fn, ms); S.timers.push(t); return t; }
  function clearTimers() { S.timers.forEach(function (t) { clearTimeout(t); clearInterval(t); }); S.timers = []; }
  var uid = 0;

  // ---------------- icons (static) ----------------
  function ic(path, size, sw, extra) {
    return '<svg width="' + (size || 20) + '" height="' + (size || 20) + '" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="' + (sw || 2) +
      '" stroke-linecap="round" stroke-linejoin="round"' + (extra || '') + '>' + path + '</svg>';
  }
  var P_ = {
    arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>', back: '<path d="M19 12H5M11 6l-6 6 6 6"/>',
    leaf: '<path d="M12 21V11"/><path d="M12 11C12 7 9 5 5 5c0 4 3 6 7 6z"/><path d="M12 13c0-4 3-6 7-6 0 4-3 6-7 6z"/>',
    robot: '<rect x="5" y="7" width="14" height="9" rx="2"/><circle cx="9" cy="11.5" r="1"/><circle cx="15" cy="11.5" r="1"/><path d="M12 7V4M7 16v2M17 16v2M12 16v5"/>',
    sat: '<path d="M13 7L9 3 5 7l4 4"/><path d="M17 11l4 4-4 4-4-4"/><path d="M8 12l4 4 6-6-4-4z"/><path d="M9 21a6 6 0 0 0-6-6"/>',
    sun: '<circle cx="12" cy="12" r="4"/><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"/>',
    snow: '<path d="M12 2v20M4.9 6.5l14.2 11M4.9 17.5l14.2-11M9 4l3 2 3-2M9 20l3-2 3 2"/>',
    rain: '<path d="M7 14a4 4 0 010-8 5 5 0 019.6 1.2A3.4 3.4 0 0117 14zM9 17.5l-1 3M13 17.5l-1 3"/>',
    cloud: '<path d="M7 17a4 4 0 010-8 5 5 0 019.6 1.2A3.4 3.4 0 0117 17z"/>',
    fog: '<path d="M7 14a4 4 0 010-8 5 5 0 019.6 1.2A3.4 3.4 0 0117 14z"/><path d="M4 18h16M6 21h12"/>',
    drop: '<path d="M12 3s-6 7-6 11a6 6 0 0012 0c0-4-6-11-6-11z"/>',
    therm: '<path d="M14 14.8V5a2 2 0 10-4 0v9.8a4 4 0 104 0z"/>',
    sprout: '<path d="M12 21v-8"/><path d="M12 13c0-4-3-6-7-6 0 4 3 6 7 6z"/><path d="M12 11c0-4 3-6 7-6 0 4-3 6-7 6z"/>',
    soil: '<path d="M3 10h18M3 14h18M3 18h18"/><path d="M12 3v7"/>',
    pc: '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
    mast: '<path d="M12 3v6M7 21l5-12 5 12M9 16h6"/><path d="M8 5a6 6 0 018 0"/>',
    stick: '<path d="M10 2h4v12l-2 8-2-8z"/><path d="M10 7h4"/>',
    ruler: '<path d="M3 17L17 3l4 4L7 21z"/><path d="M7 13l2 2M10 10l2 2M13 7l2 2"/>',
    hand: '<path d="M8 13V5.5a1.5 1.5 0 013 0V12M11 11V4a1.5 1.5 0 013 0v7M14 11V5.5a1.5 1.5 0 013 0V14a7 7 0 01-7 7h-.5a6 6 0 01-5-2.7L3 15.5a1.5 1.5 0 012.5-1.7L8 16"/>',
    info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.5"/>',
    up: '<path d="M12 19V5M6 11l6-6 6 6"/>', down: '<path d="M12 5v14M6 13l6 6 6-6"/>', eq: '<path d="M5 9h14M5 15h14"/>',
    tick: '<path d="M5 12l5 5 9-10"/>', cross: '<path d="M6 6l12 12M18 6L6 18"/>', warn: '<path d="M12 6v8"/><path d="M12 18v.5"/>',
    pin: '<path d="M12 21s-7-6.5-7-12a7 7 0 0114 0c0 5.5-7 12-7 12z"/><circle cx="12" cy="9" r="2.5"/>',
    book: '<path d="M4 5a2 2 0 012-2h13v16H6a2 2 0 00-2 2z"/><path d="M4 21V5"/>',
    redo: '<path d="M3 12a9 9 0 0115-6.7L21 8"/><path d="M21 3v5h-5"/>', low: '<path d="M3 20h18"/><path d="M6 20l6-9 6 9"/><path d="M12 4v3"/>',
    shirt: '<path d="M3 21h18"/>', wave: '<path d="M2 9c2.5-2 4.5-2 7 0s4.5 2 7 0 4.5-2 6 0M2 15c2.5-2 4.5-2 7 0s4.5 2 7 0 4.5-2 6 0"/>', shield: '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/><path d="M8.5 12l2.5 2.5 4.5-5"/>',
    near: '<circle cx="12" cy="12" r="2.5"/><circle cx="12" cy="12" r="8" stroke-dasharray="3 3"/>', valley: '<path d="M2 19l6-10 4 6 3-4 7 8z"/>',
    globe: '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18"/>', pulse: '<path d="M3 12h4l2.5-6 4 12 2.5-6H21"/>',
    quarter: '<rect x="4" y="4" width="16" height="16" rx="2"/><path d="M12 4v16M4 12h16"/><path d="M5 5h6v6H5z" fill="currentColor" stroke="none"/>',
    check: '<rect x="5" y="4" width="14" height="17" rx="2"/><path d="M9 3h6v3H9z"/><path d="M9 13l2 2 4-4"/>',
    camera: '<path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/>'
  };
  function I(name, size, sw) { return ic(P_[name] || P_.info, size, sw); }
  var KIND_ICON = { satellite: 'sat', model: 'pc', station: 'mast', probe: 'stick' };
  var JAR = 'M13 15h38v57a7 7 0 01-7 7H20a7 7 0 01-7-7z';
  function basketSvg(pct, w, fill) {
    var id = 'k' + (++uid), top = 15 + 64 * (1 - Math.max(0, Math.min(100, pct)) / 100);
    return '<svg width="' + w + '" height="' + Math.round(w * 84 / 64) + '" viewBox="0 0 64 84"><defs><clipPath id="' + id + '"><path d="' + JAR + '"/></clipPath></defs>' +
      '<path d="' + JAR + '" fill="#FBF4EA"/><rect x="0" y="' + top.toFixed(1) + '" width="64" height="84" fill="' + (fill || '#C99A5B') + '" clip-path="url(#' + id + ')"/>' +
      '<path d="' + JAR + '" fill="none" stroke="#25362B" stroke-width="3"/><path d="M8 15h48" stroke="#25362B" stroke-width="4" stroke-linecap="round"/></svg>';
  }
  var DROP = 'M12 2.5s-6.5 7.4-6.5 11.6a6.5 6.5 0 0013 0C18.5 9.9 12 2.5 12 2.5z';
  function dropSvg(pct, w) {
    var id = 'd' + (++uid), top = 2.5 + 18.1 * (1 - Math.max(0, Math.min(100, pct)) / 100);
    return '<svg width="' + w + '" height="' + w + '" viewBox="0 0 24 24"><defs><clipPath id="' + id + '"><path d="' + DROP + '"/></clipPath></defs><path d="' + DROP +
      '" fill="#FBF4EA"/><rect x="0" y="' + top.toFixed(1) + '" width="24" height="24" fill="#4C8DB5" clip-path="url(#' + id + ')"/><path d="' + DROP + '" fill="none" stroke="#25362B" stroke-width="1.6"/></svg>';
  }
  // five pictures for a 0-100 score: each basket (or drop) holds 20 points
  function pics(score, kind, w) {
    var out = '';
    for (var i = 0; i < 5; i++) { var p = Math.max(0, Math.min(1, (score - i * 20) / 20)) * 100; out += kind === 'drop' ? dropSvg(p, w || 18) : basketSvg(p, w || 16); }
    return svg(out, 'icons');
  }
  function faceSvg(status, size) {
    var s = size || 40;
    var fill = { green: '#E5F0CF', yellow: '#FBEFD2', red: '#F6E0D6', grey: '#ECEBE6' }[status] || '#ECEBE6';
    var mouth = { green: '<path d="M13 23q7 6 14 0" stroke="#14301E" stroke-width="2.4" fill="none" stroke-linecap="round"/>',
      yellow: '<path d="M14 25h12" stroke="#14301E" stroke-width="2.4" stroke-linecap="round"/>',
      red: '<path d="M13 28q7-6 14 0" stroke="#14301E" stroke-width="2.4" fill="none" stroke-linecap="round"/>',
      grey: '<path d="M16 25h8" stroke="#6B6F66" stroke-width="2.4" stroke-linecap="round" stroke-dasharray="2 3"/>' }[status] || '';
    var badge = { green: ['#14301E', '#C8E05A', '<path d="M27.5 32.5l2.5 2.5 4.5-5"/>'], yellow: ['#C98A1B', '#FFFFFF', '<path d="M31 28.5v4M31 35.2v.3"/>'],
      red: ['#B8432A', '#FFFFFF', '<path d="M28.5 29.5l5 5M33.5 29.5l-5 5"/>'], grey: ['#8B8F86', '#FFFFFF', '<path d="M29.3 30a1.8 1.8 0 113 1.3c-.8.5-1.3.9-1.3 1.9M31 35.4v.2"/>'] }[status] || ['#8B8F86', '#FFF', ''];
    var eyes = status === 'grey' ? '<circle cx="15" cy="17" r="1.8" fill="#6B6F66"/><circle cx="25" cy="17" r="1.8" fill="#6B6F66"/>' : '<circle cx="15" cy="17" r="2" fill="#14301E"/><circle cx="25" cy="17" r="2" fill="#14301E"/>';
    return '<svg width="' + s + '" height="' + s + '" viewBox="0 0 40 40"><circle cx="20" cy="20" r="17" fill="' + fill + '" stroke="#14301E" stroke-width="2"' +
      (status === 'grey' ? ' stroke-dasharray="3 3"' : '') + '/>' + eyes + mouth + '<circle cx="31" cy="32" r="7" fill="' + badge[0] + '" stroke="#FBF4EA" stroke-width="2"/><g stroke="' +
      badge[1] + '" stroke-width="2.2" fill="none" stroke-linecap="round" stroke-linejoin="round">' + badge[2] + '</g></svg>';
  }
  var SPROUT = '<svg width="18" height="21" viewBox="0 0 24 28" style="display:block;overflow:visible"><path d="M12 18 L22 22 L12 26 L2 22Z" fill="#B08A5C"/><path d="M2 22 L12 26 V28 L2 24Z" fill="#8A6640"/><path d="M22 22 L12 26 V28 L22 24Z" fill="#9C7650"/><path d="M12 22 V10" stroke="#5E8A3A" stroke-width="2" stroke-linecap="round"/><path d="M12 14 C 8 13 5 10 5 6 C 9 6 12 9 12 14Z" fill="#7FB24A"/><path d="M12 12 C 16 11 19 8 19 4 C 15 4 12 7 12 12Z" fill="#93C258"/></svg>';
  var ROBOT = '<svg width="48" height="62" viewBox="-18 -40 36 46"><ellipse cx="0" cy="1" rx="15" ry="3" fill="rgba(0,0,0,.2)"/><g class="bod"><rect class="drill" x="-1.5" y="-6" width="3" height="12" fill="#5B4630"/>' +
    '<rect x="-15" y="-21" width="30" height="15" rx="5" fill="#C46A43" stroke="#7A3A22" stroke-width="1"/><rect x="-9" y="-28" width="18" height="8" rx="3" fill="#EFE3C9" stroke="#7A3A22" stroke-width="1"/>' +
    '<circle cx="4" cy="-24" r="2.2" fill="#25362B"/><path d="M-5 -28L-7 -36" stroke="#7A3A22" stroke-width="1.3"/><circle class="led" cx="-7" cy="-37" r="2.8" fill="#E9A948"/></g>' +
    '<g transform="translate(-8 -4)"><g class="whs"><circle r="5" fill="#26302A"/><path d="M-3 0H3M0 -3V3" stroke="#8C958C" stroke-width="1"/></g></g>' +
    '<g transform="translate(8 -4)"><g class="whs"><circle r="5" fill="#26302A"/><path d="M-3 0H3M0 -3V3" stroke="#8C958C" stroke-width="1"/></g></g></svg>';

  // ---------------- words (site/data/words.json) ----------------
  function scr(id) { return ((S.words && S.words.screens) || []).filter(function (s) { return s.id === id; })[0] || {}; }
  function node(ref) {
    var w = S.words; if (!w) return null;
    var p = ref.split('.'), a = p[0];
    if (a === 'btn') return (w.shared.buttons || []).filter(function (b) { return b.id === p[1]; })[0];
    if (a === 'crop') return w.shared.crop_names[p[1]];
    if (a === 'month') return w.shared.months[p[1]];
    if (a === 'kind') return w.shared.source_kinds[p[1]];
    if (a === 'join') return w.shared.join[p[1]];
    if (a === 'title') return scr(p[1]).title;
    if (a === 'lbl') { var l = scr(p[1]).labels; return l && l[p[2]] && l[p[2]].items[p[3]]; }
    // shared groups keyed by id, e.g. shared.weather.why and shared.twin.h1 (owner, 2026-11-14 evening)
    if (w.shared[a] && !Array.isArray(w.shared[a])) return w.shared[a][p[1]];
    return (scr(a).texts || []).filter(function (t) { return t.id === p[1]; })[0];
  }
  function digits(s) { return S.lang === 'ne' ? String(s).replace(/[0-9]/g, function (d) { return '०१२३४५६७८९'[d]; }) : String(s); }
  function num(n) { return digits(Math.round(n)); }
  function fmt(v) { return typeof v === 'number' ? num(v) : digits(v); }
  function fill(t, vals) { return String(t).replace(/\{([a-z0-9_]+)\}/g, function (m, k) { return vals && vals[k] != null ? fmt(vals[k]) : m; }); }
  function L(n, vals) {
    if (!n) return ''; var t = n[S.lang]; if (t == null || t === '') t = n.en;
    var out = fill(t, vals);
    // a sentence that starts with a filled name ("rice: plant in June") starts with a capital in Latin scripts
    if (t.charAt(0) === '{' && !/^(ne|hi|bn)$/.test(S.lang)) out = out.charAt(0).toUpperCase() + out.slice(1);
    return out;
  }
  function T(ref, vals) { var n = node(ref); if (!n && W.console) console.warn('word missing:', ref); return L(n, vals); }
  // a {en, ne} text (or list) from a data file; draft languages fall back to English
  function P(o) { if (o == null) return ''; if (typeof o === 'string') return o; var v = o[S.lang]; return v != null ? v : (o.en != null ? o.en : ''); }
  function PL(o) { var v = P(o); return Array.isArray(v) ? v : (v ? [v] : []); }
  function rng(a, b) { if (b == null || Math.round(a) === Math.round(b)) return num(a); var lo = Math.min(a, b), hi = Math.max(a, b); return num(lo) + '–' + num(hi); }
  function crop(c) { return T('crop.' + c) || c; }
  function monthName(key, short) {
    var n = node('month.' + key); if (!n) return key;
    if (short && S.lang === 'ne') return n.ne.split(' (')[0];
    return L(n);
  }
  function gregInNepali(key) { var n = node('month.' + key); var m = n && n.ne.match(/\(([^–)]+)/); return m ? m[1] : L(n); }
  function fmtDate(iso) {
    var p = String(iso).split('-').map(Number); if (p.length < 3) return iso;
    var key = MONTHS[p[1] - 1];
    var name = S.lang === 'ne' ? gregInNepali(key) : L(node('month.' + key));
    return digits(p[2]) + ' ' + name + ' ' + digits(p[0]);
  }
  function lines(arr, cls) { return h('ul', { class: 'lines' + (cls ? ' ' + cls : '') }, arr.filter(Boolean).map(function (t) { return h('li', null, t); })); }
  function sentences(t) {
    if (!t) return [];
    var marked = S.lang === 'ne' ? String(t).replace(/([।?!])\s*/g, '$1\n') : String(t).replace(/([.?!])\s+/g, '$1\n');
    return marked.split('\n').map(function (x) { return x.trim(); }).filter(Boolean);
  }
  function isPlaceholder(name) { return /placeholder/i.test(name || ''); }
  function langInfo(code) { return ((S.words && S.words.languages) || []).filter(function (l) { return l.code === code; })[0]; }

  // ---------------- the field file ----------------
  function fieldReady() {
    if (S.fieldP) return S.fieldP;
    var id = encodeURIComponent(S.fid);
    var dr = indexEntry().drone;
    S.fieldP = Promise.all([getJSON('data/fields/' + id + '.json'), getJSON('data/labels/' + id + '.json'), dr ? getJSON(dr) : null]).then(function (r) {
      S.field = r[0]; S.labels = r[1]; if (r[0] && r[2]) r[0]._drone = r[2]; return r[0];
    });
    return S.fieldP;
  }
  function mocked(F, block) { return (F.mock || []).indexOf(block) >= 0; }
  // the other rain versions beside the central (gauge-tuned) one: DHM-scaled and untuned (owner, 2026-11-14);
  // older files carry only "uncorrected", read as a fallback. A range runs over the central value and every version present.
  function alts(o, base) {
    if (!o) return [];
    var a = [o[base + 'dhm_rain'], o[base + 'untuned_rain']].filter(Boolean);
    if (!a.length && o[base + 'uncorrected_rain']) a.push(o[base + 'uncorrected_rain']);
    return a;
  }
  function spread(v, others, k) {
    var xs = [v].concat(others.map(function (o) { return o[k]; })).filter(function (x) { return typeof x === 'number'; });
    return xs.length ? [Math.min.apply(null, xs), Math.max.apply(null, xs)] : [v, v];
  }
  function yearRange(y, k) { return spread(y[k], alts(y, ''), k); }
  function hasDhm(F) { return JSON.stringify(F.plans).indexOf('_dhm_rain') >= 0; }
  function scoreRange(p, k) { return spread(p.score[k], alts(p, 'score_'), k); }
  // what the farmer grows now (fix A3, owner 2026-11-15: one answer on every screen): their answer once given, until then
  // our guess from space (the option whose crops are the diary's guess), else the file's default. Pure.
  function winterId(F, answer) {
    var co = F.current_options; if (!co || !co.options) return null;
    var g = ((F.diary && F.diary.guess) || []).join('+');
    var guess = co.options.filter(function (o) { return o.crops.map(function (c) { return c.crop; }).join('+') === g; })[0];
    return answer || (guess && guess.id) || co['default'];
  }
  // the option that replaces the 'current' plan: none while it is the file's default and the farmer has not answered
  function swapId(F, answer) { var co = F.current_options, id = winterId(F, answer); return co && (answer || id !== co['default']) ? id : null; }
  function curOption(F) {
    var co = F.current_options, id = winterId(F, S.winter); if (!id) return null;
    return co.options.filter(function (o) { return o.id === id; })[0] || null;
  }
  // the three plans with the farmer's winter-crop answer applied (CONTRACT_CHANGES, current_options)
  function effPlans(F) {
    var co = F.current_options, opt = co && swapId(F, S.winter) ? curOption(F) : null;
    return F.plans.map(function (p) {
      var q;
      if (p.id === 'current' && opt) {
        q = { id: p.id, name: p.name };
        ['crops', 'score', 'score_dhm_rain', 'score_untuned_rain', 'score_uncorrected_rain', 'tabs', 'tips', 'tabs_ne', 'tips_ne',
          'future', 'future_dhm_rain', 'future_untuned_rain', 'future_uncorrected_rain']
          .forEach(function (k) { if (opt[k] != null) q[k] = opt[k]; });
        q.replay = opt.replay;
        return q;
      }
      q = Object.assign({}, p, { replay: (F.replay || {})[p.id] || [] });
      if (opt && opt.compared && opt.compared[p.id]) { q.tabs = opt.compared[p.id].tabs || q.tabs; q.tabs_ne = opt.compared[p.id].tabs_ne || q.tabs_ne; }
      return q;
    });
  }
  // a field abroad whose third plan is rice alone keeps the name "Safest in bad years" (not "Feed your soil")
  function planName(p) { var n = node('lbl.what_to_grow.plan.' + (p.id === 'safest' && p.name === 'Safest in bad years' ? 'safest_bad_years' : p.id)); return n ? L(n) : p.name; }
  function cropsLine(p) { return p.crops.map(function (c) { return crop(c.crop); }).join(' → '); }
  function vsNow(p, cur, k) {
    var a = scoreRange(p, k), b = scoreRange(cur, k);
    if (a[0] > b[1]) return 'up'; if (a[1] < b[0]) return 'down'; return 'eq';
  }
  function vsChip(dir) {
    var key = { up: 'more_than_now', down: 'less_than_now', eq: 'same_as_now' }[dir];
    return h('span', { class: 'vs ' + dir }, svg(I(dir, 14, 2.6)), T('what_to_grow.' + key));
  }
  function waterCases(F) {
    var ws = F.field.water_source;
    if (ws && ws !== 'unknown') return ws === 'rain-only' ? ['rain_fed'] : ['irrigated'];
    if (S.water === 'rain_only') return ['rain_fed'];
    if (S.water === 'canal' || S.water === 'well' || S.water === 'other') return ['irrigated'];
    return ['rain_fed', 'irrigated'];
  }

  // ---------------- sources: a small tag next to each number ----------------
  var SRC = { gpm: /^GPM/i, power: /^NASA POWER/i, station: /station/i, hls: /Harmonized Landsat|^HLS/i, grace: /GRACE/i, soil: /SoilGrids/i,
    dem: /NASADEM/i, smap: /SMAP/i, twin: /twin/i, dhm: /^DHM/i, nex: /NEX-GDDP/i };
  function srcObj(F, key) { return (F.sources || []).filter(function (s) { return SRC[key] && SRC[key].test(s.name); })[0]; }
  function srcTag(F, key) {
    var s = typeof key === 'string' ? srcObj(F, key) : key;
    if (!s) return null;
    var short = String(s.name).replace(/\s*\(.*$/, '');
    return h('button', { type: 'button', class: 'src', title: s.name + ' · ' + s.resolution + ' · ' + s.years,
      onclick: function (e) { e.stopPropagation(); openSources(s.name); } }, svg(I(KIND_ICON[s.type] || 'info', 12, 2.2)), short + ' · ' + digits(s.years));
  }
  function srcs(F, keys, oid) { return h('div', { class: 'srcs' }, oid ? labs(oid) : null, keys.map(function (k) { return srcTag(F, k); })); }

  // ---------------- two labels on every number: how sure, how close (data/labels/<id>.json, by output id) ----------------
  // Pictures plus words, never colour alone; a tap explains. A third mark sends numbers made with the fixed rain to the Check-up.
  var SURE_IC = { verified: 'shield', estimate: 'pc' }, SCALE_IC = { field: 'pin', neighbourhood: 'near', valley: 'valley', region: 'globe' };
  function labOf(oid, own) { return own || (S.labels && S.labels.outputs && S.labels.outputs[oid]) || null; }
  function scaleName(sc) { var x = S.labels && S.labels.scales && S.labels.scales[sc]; return x && x[S.lang] ? x[S.lang] : T('your_plan.lab_' + sc); }
  function labs(oid, own) {
    var l = labOf(oid, own); if (!l) return null;
    function b(cls, icon, word) { return h('button', { type: 'button', class: 'lab ' + cls, onclick: function (e) { e.stopPropagation(); openLabel(l); } }, svg(I(icon, 12, 2.4)), word); }
    return h('span', { class: 'labs' }, l.sure ? b(l.sure, SURE_IC[l.sure] || 'info', T('your_plan.lab_' + l.sure)) : null,
      l.scale ? b('scale', SCALE_IC[l.scale] || 'pin', scaleName(l.scale)) : null, l.rain_corrected ? rainMark() : null);
  }
  function rainMark() {
    return h('button', { type: 'button', class: 'lab rain', title: T('your_plan.lab_rain_why'), onclick: function (e) { e.stopPropagation(); go('how/checkup'); } }, svg(I('drop', 12, 2.4)), T('your_plan.lab_rain'));
  }
  function openLabel(l) {
    function build() {
      var panel = openSheet(build), sc = S.labels && S.labels.scales && S.labels.scales[l.scale];
      add(panel, [sheetBar(T('your_plan.lab_title')), h('div', { class: 'col', style: 'gap:12px;margin-top:8px' },
        l.sure ? h('div', { class: 'card' }, h('p', { class: 'lead', style: 'margin:0' }, svg(I(SURE_IC[l.sure] || 'info', 18)), ' ', T('your_plan.lab_' + l.sure)),
          lines(sentences(T('your_plan.lab_' + l.sure + '_why')), 'sub'),
          l.n ? h('p', { class: 'small', style: 'margin:0' }, T('your_plan.lab_checks') + ' ' + num(l.k) + ' / ' + num(l.n)) : null) : null,
        l.scale ? h('div', { class: 'card' }, h('p', { class: 'lead', style: 'margin:0' }, svg(I(SCALE_IC[l.scale] || 'pin', 18)), ' ', scaleName(l.scale)),
          lines([T('your_plan.lab_' + l.scale + '_why')], 'sub'), sc && sc.about && S.lang === 'en' ? h('p', { class: 'small', style: 'margin:0' }, sc.about) : null) : null,
        l.rain_corrected ? h('div', { class: 'card' }, h('p', { class: 'lead', style: 'margin:0' }, svg(I('drop', 18)), ' ', T('your_plan.lab_rain')),
          lines([T('your_plan.lab_rain_why')], 'sub'), btn3(T('your_plan.check_name'), function () { closeSheet(); go('how/checkup'); }, 'check')) : null)]);
      panel.focus();
    }
    build();
  }

  // ---------------- shared pieces ----------------
  function bigTitle(a, b) { return h('h1', { class: 'big' }, h('span', null, a), b ? h('span', { class: 'b' }, b) : null); }
  function cta(label, onclick, opts) {
    opts = opts || {};
    return h('button', { type: 'button', class: 'cta', onclick: onclick }, opts.sweep && !RM ? h('span', { class: 'sweep', 'aria-hidden': 'true' }) : null,
      h('span', null, label), svg(ic(P_.arrow, 22, 2.6), 'lime'));
  }
  function btn2(label, onclick, icon) { return h('button', { type: 'button', class: 'btn2', onclick: onclick }, icon ? svg(I(icon, 18)) : null, label); }
  function btn3(label, onclick, icon) { return h('button', { type: 'button', class: 'btn3', onclick: onclick }, icon ? svg(I(icon, 18)) : null, label); }
  function sampleChip() { return h('span', { class: 'chip sample' }, svg(I('pin', 14)), T('btn.sample_field')); }
  // a real farm from a drone photo (owner, 2026-11-15): its own label where a sample field shows its chip
  function fieldChip(F) { return F._drone ? h('p', { class: 'small dronelabel' }, svg(I('pin', 14)), ' ', droneLabel(F._drone)) : isPlaceholder(F.field.name) ? sampleChip() : null; }
  // the drone file's own label and satellite line ({en, ne}; Kharipati), else the shared words (Dhulikhel's preview); its credit
  function droneLabel(d) { return d.label ? P(d.label) : T('your_plan.drone_label'); }
  function droneSat(d) { return d.sat ? P(d.sat) : T('your_plan.drone_sat'); }
  function droneCredit(d) { return h('p', { class: 'small dronecredit', lang: 'en', style: 'margin:6px 0 0' }, d.credit); }
  function loading() { return h('div', { class: 'loading', role: 'status' }, h('span', { class: 'dots' }, h('i'), h('i'), h('i'))); }
  function notReady(extra) { return h('div', { class: 'card soft' }, h('p', { class: 'lead' }, T('btn.not_ready')), extra || null); }
  function stepsBar(n) { return h('div', { class: 'steps', 'aria-hidden': 'true' }, [1, 2, 3].map(function (i) { return h('span', { class: i <= n ? 'on' : '' }); })); }
  function screen(name, parts) {
    return h('section', { class: 'scr scr-' + name },
      h('div', { class: 's-head' }, parts.head), parts.scene ? h('div', { class: 's-scene' }, parts.scene) : null,
      h('div', { class: 's-body' }, parts.body), h('div', { class: 's-cta' }, parts.cta), parts.foot ? h('div', { class: 's-foot' }, parts.foot) : null);
  }
  function withField(name, build) {
    if (S.field) return build(S.field);
    var box = h('section', { class: 'scr scr-' + name }, h('div', { class: 's-body' }, loading()));
    fieldReady().then(function (F) {
      if (!box.isConnected) return;
      box.replaceWith(F ? build(F) : screen(name, { body: notReady() }));
    });
    return box;
  }
  function fogLayer(sure) { var o = Math.max(0, Math.min(1, 1 - (sure == null ? 0 : sure))); return h('span', { class: 'fog', 'aria-hidden': 'true', style: 'opacity:' + (o * 0.6).toFixed(2) }); }
  function fogTag() { return h('span', { class: 'fogtag' }, svg(I('fog', 16)), T('btn.not_sure')); }

  // ---------------- the field drawn as a box of parts ----------------
  var SVGNS = 'http://www.w3.org/2000/svg';
  function geom(F) {
    var secs = F.field.sections || [], x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
    secs.forEach(function (s) { s.polygon.forEach(function (p) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); y0 = Math.min(y0, p[1]); y1 = Math.max(y1, p[1]); }); });
    var dx = (x1 - x0) || 1, dy = (y1 - y0) || 1;
    var G = secs.map(function (s) {
      var a = 1e9, b = -1e9, c = 1e9, d = -1e9;
      s.polygon.forEach(function (p) { a = Math.min(a, p[0]); b = Math.max(b, p[0]); c = Math.min(c, p[1]); d = Math.max(d, p[1]); });
      var g = { s: s, l: (a - x0) / dx * 100, r: (b - x0) / dx * 100, t: (y1 - d) / dy * 100, b: (y1 - c) / dy * 100, n: String(s.id).replace(/^\D+/, '') };
      g.pts = s.polygon.map(function (p) { return [(p[0] - x0) / dx * 100, (y1 - p[1]) / dy * 100]; });
      var A = 0, X = 0, Y = 0;   // the centre of the part's own area (a rectangle's is its middle)
      g.pts.forEach(function (p, i) { var q = g.pts[(i + 1) % g.pts.length], k = p[0] * q[1] - q[0] * p[1]; A += k; X += (p[0] + q[0]) * k; Y += (p[1] + q[1]) * k; });
      g.cx = A ? X / (3 * A) : (g.l + g.r) / 2; g.cy = A ? Y / (3 * A) : (g.t + g.b) / 2;
      return g;
    }).sort(function (p, q) { return p.n - q.n; });   // part 1 first: the ids run from the south-west (owner, 2026-11-15)
    // the field's width over its height on the ground, and whether its parts make a plain grid (as Bhaktapur's 2 x 2)
    G.aspect = dx * Math.cos((y0 + y1) / 2 * Math.PI / 180) / dy;
    var cols = {}, rows = {};
    G.forEach(function (g) { cols[Math.round(g.l)] = 1; rows[Math.round(g.t)] = 1; });
    G.grid = G.every(function (g) { return g.pts.length === 4; }) && Object.keys(cols).length * Object.keys(rows).length === G.length;
    return G;
  }
  // a drawn field's drone photo (data/drone/<id>.json; owner, 2026-11-15): the picture, the outline and the lines between
  // patches drawn over it as vector lines (crisp at any size), a number at each patch's centre. G: each patch in percent of
  // the picture, as geom() gives it, so the soil screen's robot walks on the photo.
  function droneView(d, sections) {
    var W0 = d.size_px[0], H0 = d.size_px[1], s0 = d.bounds[0][0], w0 = d.bounds[0][1], n0 = d.bounds[1][0], e0 = d.bounds[1][1];
    function px(p) { return [(p[0] - w0) / (e0 - w0) * W0, (n0 - p[1]) / (n0 - s0) * H0]; }
    function pathOf(ring) { return 'M' + ring.map(function (p) { var q = px(p); return q[0].toFixed(1) + ' ' + q[1].toFixed(1); }).join('L') + 'Z'; }
    var box = h('div', { class: 'dronebox', style: 'aspect-ratio:' + W0 + '/' + H0 }, h('img', { src: d.image, alt: '', decoding: 'async' }));
    var sv = D.createElementNS(SVGNS, 'svg');
    sv.setAttribute('viewBox', '0 0 ' + W0 + ' ' + H0); sv.setAttribute('preserveAspectRatio', 'none'); sv.setAttribute('aria-hidden', 'true');
    function el(tag, attrs) { var e = D.createElementNS(SVGNS, tag); Object.keys(attrs).forEach(function (k) { e.setAttribute(k, attrs[k]); }); sv.append(e); return e; }
    var byId = {}; (sections || []).forEach(function (s) { byId[s.id] = s; });
    var G = d.patches.map(function (p) {
      var xs = p.polygon.map(function (q) { return px(q)[0] / W0 * 100; }), ys = p.polygon.map(function (q) { return px(q)[1] / H0 * 100; }), c = px(p.centre);
      return { s: byId[p.id] || { id: p.id, polygon: p.polygon }, n: p.id.replace(/^[sp]/, ''), q: el('path', { d: pathOf(p.polygon), class: 'dq' }),
               l: Math.min.apply(null, xs), r: Math.max.apply(null, xs), t: Math.min.apply(null, ys), b: Math.max.apply(null, ys), cx: c[0] / W0 * 100, cy: c[1] / H0 * 100 };
    });
    d.lines.forEach(function (ln) { var a = px(ln[0]), b = px(ln[1]); el('line', { x1: a[0], y1: a[1], x2: b[0], y2: b[1], class: 'dl' }); });
    el('path', { d: pathOf(d.outline), class: 'do' });
    box.append(sv);
    return { el: box, G: G };
  }
  function fieldBox(F, mode, opt) {
    opt = opt || {};
    if (F._drone && !opt.photo) {
      var dv = droneView(F._drone, F.field.sections), dbox = dv.el;
      dbox.classList.add('fieldbox', 'drone'); dbox.setAttribute('role', 'img'); dbox.setAttribute('aria-label', T('parts.split', { section_count: dv.G.length }));
      dv.G.forEach(function (g, i) {
        g.num = h('span', { class: 'n', style: 'left:' + g.cx + '%;top:' + g.cy + '%;width:24px;height:24px;margin:-12px 0 0 -12px;font-size:12px;border-width:2px;' +
          (mode === 'grow' ? 'animation-delay:' + (300 + i * 60) + 'ms' : 'animation:none') }, digits(g.n));
        dbox.append(g.num);
      });
      dbox._g = dv.G;
      return dbox;
    }
    var G = geom(F), box = h('div', { class: 'fieldbox' + (opt.photo ? ' photo' : ''), role: 'img', 'aria-label': T('parts.split', { section_count: G.length }) });
    if (opt.photo) box.append(h('img', { class: 'ph', src: opt.photo, alt: '' }));   // phone as drone: the photo from above, drawn under the parts
    else box.append(h('div', { class: 'wm', 'aria-hidden': 'true' }, T('where.your_farm')));
    var colour = { green: 'rgba(63,122,46,.16)', yellow: 'rgba(201,138,27,.2)', red: 'rgba(184,67,42,.2)', grey: 'rgba(139,143,134,.14)' };
    // parts that are not a plain grid (a drawn field's patches, owner 2026-11-15): the field at its true shape, each part's
    // own outline as a crisp vector line, no sprouts
    var shapes = !G.grid && D.createElementNS(SVGNS, 'svg');
    if (shapes) {
      box.style.aspectRatio = String(Math.max(0.8, Math.min(2.4, G.aspect || 1)));
      shapes.setAttribute('class', 'shapes'); shapes.setAttribute('viewBox', '0 0 100 100'); shapes.setAttribute('preserveAspectRatio', 'none'); shapes.setAttribute('aria-hidden', 'true');
      box.append(shapes);
    }
    G.forEach(function (g, i) {
      var st = 'left:' + g.l + '%;top:' + g.t + '%;width:' + (g.r - g.l) + '%;height:' + (g.b - g.t) + '%;';
      var bg = opt.photo ? 'transparent' : mode === 'status' ? colour[g.s.status] || colour.grey : (i % 3 === 0 ? 'rgba(20,48,30,.06)' : 'rgba(154,84,38,.06)');
      if (shapes) {
        g.q = D.createElementNS(SVGNS, 'path');
        g.q.setAttribute('d', 'M' + g.pts.map(function (p) { return p[0].toFixed(2) + ' ' + p[1].toFixed(2); }).join('L') + 'Z');
        g.q.setAttribute('style', 'fill:' + bg); shapes.append(g.q);
        return;
      }
      var q = h('span', { class: 'q', style: st + 'background:' + bg + (mode === 'grow' ? ';animation:ks-soft 280ms ease ' + (1300 + i * 100) + 'ms both' : '') });   // gentle motion (2026-11-15)
      g.q = q; box.append(q);
    });
    var xs = {}, ys = {};
    if (!shapes) G.forEach(function (g) { if (g.l > 0.5) xs[g.l.toFixed(2)] = 1; if (g.t > 0.5) ys[g.t.toFixed(2)] = 1; });
    Object.keys(xs).forEach(function (x) { box.append(h('span', { class: 'vl', style: 'left:' + x + '%' + (mode === 'grow' ? '' : ';animation:none') })); });
    Object.keys(ys).forEach(function (y) { box.append(h('span', { class: 'hl', style: 'top:' + y + '%' + (mode === 'grow' ? '' : ';animation:none') })); });
    if (!shapes && !opt.photo && (mode === 'grow' || mode === 'sway' || mode === 'robot')) {
      G.forEach(function (g, qi) {
        for (var r = 0; r < 3; r++) for (var c = 0; c < 4; c++) {
          var x = g.l + (g.r - g.l) * (0.16 + c * 0.23), y = g.t + (g.b - g.t) * (0.28 + r * 0.28);
          if (Math.abs(x - g.cx) < (g.r - g.l) * 0.2 && Math.abs(y - g.cy) < (g.b - g.t) * 0.28) continue;
          var d = 2000 + qi * 160 + ((r * 4 + c) % 9) * 50;
          var sp = h('span', { class: 'sprout ' + (mode === 'grow' ? 'g' : 's'), style: 'left:' + x + '%;top:' + y + '%;' +
            (mode === 'grow' ? 'animation-delay:' + d + 'ms,' + (d + 300) + 'ms' : 'animation-delay:-' + ((r + c) * 0.4) + 's') });   // gentle motion (2026-11-15)
          sp.innerHTML = SPROUT; box.append(sp);
        }
      });
    }
    G.forEach(function (g, i) {
      if (mode === 'status') {
        var f = h('span', { class: 'face', style: 'left:' + g.cx + '%;top:' + g.cy + '%;animation-delay:' + (200 + i * 120) + 'ms' });
        f.innerHTML = faceSvg(g.s.status, 54); box.append(f);
        var fo = 1 - (g.s.sure == null ? 0 : g.s.sure);
        box.append(h('span', { class: 'pfog', style: 'left:' + g.l + '%;top:' + g.t + '%;width:' + (g.r - g.l) + '%;height:' + (g.b - g.t) + '%;opacity:' + (fo * 0.6).toFixed(2) }));
        box.append(h('span', { class: 'n', style: 'left:' + (g.l + 9) + '%;top:' + (g.t + 12) + '%;width:30px;height:30px;margin:-15px 0 0 -15px;font-size:14px;border-width:2px' }, digits(g.n)));
      } else {
        // robot: the number below the robot's spot, kept inside its own part; smaller numbers when the parts are many
        var px = G.length <= 4 ? (mode === 'robot' ? 32 : 0) : G.length <= 12 ? 28 : G.length <= 24 ? 24 : 22;
        g.ny = mode === 'robot' && !shapes ? g.cy + Math.max(0, Math.min(14, (g.b - g.t) / 2 - 11)) : g.cy;   // the number's height, % of the box
        g.num = h('span', { class: 'n', style: 'left:' + g.cx + '%;top:' + g.ny + '%;' +
          (px ? 'width:' + px + 'px;height:' + px + 'px;margin:-' + px / 2 + 'px 0 0 -' + px / 2 + 'px;font-size:' + Math.round(px * 0.47) + 'px;' + (px < 32 ? 'border-width:2px;' : '') : '') +
          (mode === 'grow' ? 'animation-delay:' + (1300 + i * 100) + 'ms' : 'animation:none') }, digits(g.n));
        box.append(g.num);
      }
    });
    box._g = G;
    return box;
  }

  // ---------------- header ----------------
  function renderTop(r) {
    var top = $('#top'); top.textContent = '';
    var left = h('div', { class: 'left' });
    if (r === 'home') left.append(h('span', { class: 'logo', 'aria-hidden': 'true' }, svg(ic(P_.leaf, 22, 2.2))));
    else left.append(h('button', { type: 'button', class: 'round', 'aria-label': T('btn.back'), onclick: goBack }, svg(I('back', 22, 2.4))));
    left.append(h('span', { class: 'brand' }, L(scr('home').title)));
    var langs = h('div', { class: 'langs', role: 'group', 'aria-label': T('btn.language') });
    [['en', 'EN'], ['ne', 'नेपाली']].forEach(function (x) {   // the design's order; Nepali stays the first language shown
      langs.append(h('button', { type: 'button', lang: x[0], 'aria-pressed': String(S.lang === x[0]), onclick: function () { setLang(x[0]); } }, x[1]));
    });
    var drafts = ((S.words && S.words.languages) || []).filter(function (l) { return l.draft; });
    if (drafts.length) {
      var isDraft = drafts.some(function (l) { return l.code === S.lang; });
      var sel = h('select', { 'aria-label': T('btn.language'), class: isDraft ? 'on' : '', onchange: function (e) { if (e.target.value) setLang(e.target.value); } },
        h('option', { value: '' }, isDraft ? '' : '···'),
        drafts.map(function (l) { var o = h('option', { value: l.code, lang: l.code }, l.name + ' · ' + (l.label[l.code] || l.label.en)); if (l.code === S.lang) o.selected = true; return o; }));
      if (isDraft) sel.firstChild.remove();
      langs.append(sel);
    }
    top.append(left, langs);
    var old = $('.draftnote'); if (old) old.remove();
    var li = langInfo(S.lang);
    if (li && li.draft) top.after(h('div', { class: 'draftnote', role: 'note' }, (li.label[S.lang] || '') + ' · ' + li.label.en));
  }
  function goBack() {
    if (S.prev && S.prev !== S.cur && W.history.length > 1) { W.history.back(); return; }
    var back = { photo: 'home', parts: 'photo', soil: 'parts', choose: 'soil', today: 'choose', next: 'choose', weather: 'choose', how: 'home', world: 'home' };
    go(back[S.cur] || 'home');
  }
  function setLang(l) {
    S.lang = l; store.set('lang', l); D.documentElement.lang = l;
    renderTop(S.cur);
    rerender();
  }

  // ---------------- routing ----------------
  function go(r) { location.hash = '#/' + r; }
  function parse() {
    var p = (location.hash || '').replace(/^#\/?/, '').split('/');
    var r = ROUTES.indexOf(p[0]) >= 0 ? p[0] : 'home';
    return { r: ROUTES.indexOf(p[0]) >= 0 ? p[0] : 'home', a: p[1] ? decodeURIComponent(p[1]) : null };
  }
  function setSky(r) {
    var v = SKY[r] || SKY.next, s = $('#sky');
    s.style.setProperty('--sx', v[0]); s.style.setProperty('--sy', v[1]); s.style.setProperty('--tint', v[2]);
    s.style.setProperty('--set', v[3]); s.style.setProperty('--prog', v[4]); s.style.setProperty('--land', r === 'home' ? 0 : 1);
  }
  function onRoute() {
    var x = parse();
    if (x.r === 'plan') { if (!S.cur) show('next'); openPlan(x.a); return; }
    if (x.r === 'trial') { if (!S.cur) show('next'); openTrial(x.a); return; }
    if (S.sheetFor) closeSheet();
    if (x.r === S.cur) { var sx = SCREENS[x.r]; if (x.a && sx.onArg) sx.onArg(x.a); else if (x.a && sx.scrollTo) sx.scrollTo(x.a); return; }
    show(x.r, x.a);
  }
  var SCREENS = {};
  function show(r, arg) {
    var app = $('#app'), old = app.firstElementChild, prev = S.cur;
    S.prev = prev; S.cur = r; S.arg = arg;
    clearTimers();
    setSky(r); D.body.className = 'r-' + r; renderTop(r);
    function build() {
      app.textContent = '';
      app.append(SCREENS[r](arg));
      W.scrollTo(0, 0);
      try { app.focus({ preventScroll: true }); } catch (e) { /* old browsers */ }
    }
    if (!old || RM) { build(); return; }
    if (prev === 'home' && r === 'photo') {
      old.classList.add('diving');
      var veil = h('div', { id: 'veil', 'aria-hidden': 'true' }); D.body.append(veil);
      setTimeout(build, 1150); setTimeout(function () { veil.remove(); }, 1600);
      return;
    }
    old.classList.add('leaving');
    setTimeout(build, 180);   // gentle motion (2026-11-15): a short fade out (css: .scr.leaving)
  }
  function rerender() {
    if (!S.cur) return;
    clearTimers();
    var app = $('#app'); app.textContent = ''; app.append(SCREENS[S.cur](S.arg, true));
    if (S.sheetFor) { var y = $('#sheet .panel') ? $('#sheet .panel').scrollTop : 0; S.sheetFor(true); if ($('#sheet .panel')) $('#sheet .panel').scrollTop = y; }
  }

  // ---------------- 1 home (design: Main, W1_Home) ----------------
  // a file next to the field file: site/data/<kind>/<field id>.json (null while it is not there: "not ready yet")
  // a field built with the global settings (abroad, index.json profile "default") has only its field, labels, pulse and
  // check-up files: the Nepal-only files are not asked for, so nothing fails to load
  function indexEntry() { return ((S.index && S.index.fields) || []).filter(function (x) { return x.id === S.fid; })[0] || {}; }
  function abroad() { return indexEntry().profile === 'default'; }
  // the field's country (index.json; none given: Nepal). Outside Nepal: Gregorian months and English unless the visitor
  // chose a language (rules.yaml global_use.months_language, owner 2026-11-15)
  function inNepal(id) { var e = id ? ((S.index && S.index.fields) || []).filter(function (x) { return x.id === id; })[0] || {} : indexEntry(); return (e.country || 'Nepal') === 'Nepal'; }
  function defaultLang(id) { return inNepal(id) ? 'ne' : 'en'; }
  function featData(kind) { return abroad() && ['pulse', 'checkup', 'labels'].indexOf(kind) < 0 ? Promise.resolve(null) : getJSON('data/' + kind + '/' + encodeURIComponent(S.fid) + '.json'); }
  function island() {
    return h('div', { class: 'island' },
      [[-30, 208, 190, 70, 7, -1, 1], [90, 232, 190, 64, 8, -3, 1], [200, 206, 190, 72, 6.5, -2, 1], [-40, 150, 120, 52, 9, -4, -1], [270, 120, 120, 50, 8.5, -1.5, -1],
        [40, 20, 110, 40, 10, -5, -1], [20, 250, 130, 50, 7.5, -0.5, 1], [190, 252, 140, 50, 8, -2, 1]].map(function (p) {
        return h('span', { class: 'puff', 'aria-hidden': 'true', style: 'left:' + (p[0] / 3.42) + '%;top:' + (p[1] / 2.89) + '%;width:' + (p[2] / 3.42) + '%;height:' + p[3] + 'px;z-index:' + p[6] + ';animation-duration:' + p[4] + 's;animation-delay:' + p[5] + 's' });
      }),
      h('img', { src: 'img/farm.webp', alt: '', width: '342', height: '289', decoding: 'async', fetchpriority: 'high' }));
  }
  SCREENS.home = function () {
    var ix = (S.index && S.index.fields) || [];
    var f0 = ix.filter(function (f) { return f.id === S.fid; })[0] || ix[0];
    var sample = f0 && isPlaceholder(f0.name);
    var cap = h('div', { 'aria-live': 'polite' }), sel = -1, cards = [];
    var CAPS = [['home.intro', 'home.you_decide'], ['check_soil.wide_close', 'check_soil.together'], ['home.card_months_sub', null]];
    function showCap() {
      var c = CAPS[sel + 1]; cap.textContent = '';
      var sub = c[1] ? T(c[1]) : '';
      cap.append(h('div', { class: 'caption' }, h('p', { class: 'lead' }, T(c[0])), sub ? h('p', { class: 'sub' }, sub) : null));
    }
    function pick(i) { sel = sel === i ? -1 : i; cards.forEach(function (c, j) { c.setAttribute('aria-pressed', String(j === sel)); }); showCap(); }
    cards = [
      h('button', { type: 'button', class: 'hcard', 'aria-pressed': 'false', onclick: function () { pick(0); } },
        h('span', { class: 'tag' }, svg(I('stick', 18)), T('home.card_today_tag')), h('span', { class: 'big' }, T('home.card_today_big')), h('span', { class: 'lbl' }, T('home.card_today_sub'))),
      h('button', { type: 'button', class: 'hcard', 'aria-pressed': 'false', onclick: function () { pick(1); } },
        h('span', { class: 'tag b' }, svg(I('sat', 18)), T('home.card_months_tag')), h('span', { class: 'big' }, T('home.card_months_big')), h('span', { class: 'lbl' }, T('home.card_months_sub')))
    ];
    showCap();
    // the web home's floating cards and its strip along the bottom (design W1_Home), in our words
    var floats = h('div', { class: 'floats', 'aria-hidden': 'true' },
      [['pin', '#FBF4EA', '#9A5426', 'home.map_tag', 'home.map_sub', 'left:4%;top:4%'],
        ['stick', '#14301E', '#C8E05A', 'home.card_today_tag', 'home.card_today_sub', 'right:0;top:14%;animation-delay:.8s'],
        ['sat', '#E3EEDC', '#2E5A2A', 'home.card_months_tag', 'home.card_months_big', 'left:2%;bottom:26%;animation-delay:1.4s'],
        ['sprout', '#E9F2C2', '#3F5E1E', 'what_to_grow.next_h2', 'home.what_to_grow', 'right:3%;bottom:8%;animation-delay:2s']].map(function (f) {
        return h('div', { class: 'fl', style: f[5] }, h('span', { class: 'ic', style: 'background:' + f[1] + ';color:' + f[2] }, svg(I(f[0], 20))),
          h('span', null, h('span', { class: 'tg' }, T(f[3])), h('br'), h('span', { class: 'tx' }, T(f[4]))));
      }));
    var strip = h('div', { class: 'hstrip' },
      [['stick', 'home.card_today_tag', 'home.card_today_sub'], ['sat', 'home.card_months_tag', 'home.card_months_sub'], ['hand', 'home.farmer_first', 'home.you_decide']].map(function (x) {
        return h('div', { class: 'hs' }, h('span', { class: 'hsi' }, svg(I(x[0], 20))), h('span', null, h('span', { class: 'tg' }, T(x[1])), h('br'), h('span', { class: 'tx' }, T(x[2]))));
      }));
    var scr = screen('home', {
      head: [h('span', { class: 'chip nasa' }, h('i'), T('home.open_records')), bigTitle(T('home.hero_1'), T('home.hero_2')), sample ? sampleChip() : null],
      scene: [island(), floats],
      body: [h('div', { class: 'homecards' }, cards), cap],
      cta: [cta(T('home.try_sample'), function () { go('photo'); }, { sweep: true }),
        sample ? h('p', { class: 'small', style: 'margin:0;text-align:center' }, T('home.sample_note')) : null,
        // the prepared fields, folded away (CLAUDE.md: "a short list of prepared fields"); How we know is for judges only
        // (owner, 2026-11-14 evening): one small link here, none on the farmer's other screens
        ix.length > 1 ? h('details', { class: 'fieldsfold' }, h('summary', null, T('home.prepared_title')), worldLink(), fieldsList()) : null,
        h('a', { class: 'judges', href: '#/how' }, svg(I('book', 16)), T('farm.judges_link'))],
      foot: strip
    });
    // for judges, at the end of the scroll and below the first screen: "Behind the scenes" (loaded when it is scrolled to)
    var both = D.createDocumentFragment(); both.append(scr, promiseBox(true), limitsBox(true), behindBox(true));
    return both;
  };
  // the prepared fields (index.json); a field built with the global settings carries its note (owner, 2026-11-14 evening)
  function fieldsList(target) {
    var ix = (S.index && S.index.fields) || [];
    return h('div', { class: 'prepared', style: 'display:flex;flex-direction:column;gap:8px' }, ix.map(function (f) {
      // from How we know a field opens its own How we know (its own labels); from Home, its farmer steps
      return h('button', { type: 'button', class: 'pf', 'aria-pressed': String(f.id === S.fid), onclick: function () {
        chooseField(f.id);
        if (target !== 'how') { go(target || 'photo'); return; }
        try { W.history.replaceState(null, '', '#/how'); } catch (e) { /* old browsers */ }
        show('how'); } },   // the field's own How we know, from its top; the old page's timers stop
        h('span', null, h('b', null, f.name), h('br'), h('span', { class: 'small' }, f.country), f.profile === 'default' && f.note ? [h('br'), h('span', { class: 'small' }, P(f.note))] : null),
        f.id === S.fid ? svg(I('tick', 18, 2.6)) : svg(I('arrow', 18)));
    }));
  }
  function chooseField(id) {
    if (id === S.fid) return;
    S.fid = id; S.field = null; S.fieldP = null; S.labels = null; S.winter = null; S.probe = null; store.set('fid', id); store.set('winter', null);
    if (!store.get('lang') && langInfo(defaultLang(id))) { S.lang = defaultLang(id); D.documentElement.lang = S.lang; }   // the field's own default until the visitor picks
  }

  // ---------------- 2 your field from above (map; the farmer's winter crop; what space shows) ----------------
  function hull(pts) {
    pts = pts.slice().sort(function (a, b) { return a[0] - b[0] || a[1] - b[1]; });
    function cross(o, a, b) { return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]); }
    var lo = [], up = [];
    pts.forEach(function (p) { while (lo.length >= 2 && cross(lo[lo.length - 2], lo[lo.length - 1], p) <= 0) lo.pop(); lo.push(p); });
    pts.slice().reverse().forEach(function (p) { while (up.length >= 2 && cross(up[up.length - 2], up[up.length - 1], p) <= 0) up.pop(); up.push(p); });
    return lo.slice(0, -1).concat(up.slice(0, -1));
  }
  function loadLeaflet() {
    if (W.L) return Promise.resolve(W.L);
    if (S.leafP) return S.leafP;
    S.leafP = new Promise(function (res, rej) {
      D.head.append(h('link', { rel: 'stylesheet', href: 'vendor/leaflet/leaflet.css' }));
      var s = h('script', { src: 'vendor/leaflet/leaflet.js' });
      s.onload = function () { res(W.L); }; s.onerror = function () { S.leafP = null; rej(new Error('leaflet')); };
      D.head.append(s);
    });
    return S.leafP;
  }
  // the map's picture: NASA basemap images kept in site/data/basemap/ (no tile server at runtime). The field's own box
  // first; the whole world (a coarse picture) when asked, e.g. when the farmer marks a field elsewhere, and for a field abroad
  // (no basemap of its own yet).
  function osm(L, m, world) {
    if (m.attributionControl) m.attributionControl.setPrefix('Leaflet');
    m.getContainer().style.background = '#C9D6BE';
    if (!m.getPane('ksbase')) m.createPane('ksbase').style.zIndex = 150;   // the pictures stay under any overlay (a drone photo: fix A1, 2026-11-15)
    if (abroad()) world = 'only';
    ['world'].concat(world === 'only' ? [] : [S.fid]).forEach(function (id, i) {
      if (id === 'world' && !world) return;
      getJSON('data/basemap/' + encodeURIComponent(id) + '.json').then(function (b) {
        if (!b || !b.image || !b.bounds) return;
        var o = L.imageOverlay(b.image, b.bounds, { attribution: b.attribution || '', interactive: false, pane: 'ksbase' }).addTo(m);
        if (i === 0) o.bringToBack();
      });
    });
  }
  function winterQuestion(F, after) {
    var co = F.current_options;
    if (!co || !co.options || co.options.length < 2) {
      var g = (F.diary.guess || []).map(function (c) { return crop(c); }).join(' ' + T('join.then') + ' ');
      return h('p', { class: 'lead' }, T('from_space.guess', { guess_list: g }));
    }
    var a = co.options[0], b = co.options[1];
    var ca = a.crops.map(function (c) { return c.crop; }), cb = b.crops.map(function (c) { return c.crop; });
    var first = ca[0], onlyA = ca.filter(function (c) { return cb.indexOf(c) < 0; })[0], onlyB = cb.filter(function (c) { return ca.indexOf(c) < 0; })[0];
    var box = h('div', { class: 'row wrap', role: 'group', 'aria-label': T('from_space.guess_which') });
    co.options.forEach(function (o) {
      var own = o.crops.map(function (c) { return c.crop; }).filter(function (c) { return (o === a ? cb : ca).indexOf(c) < 0; })[0];
      box.append(h('button', { type: 'button', class: 'choice', 'aria-pressed': String(S.winter === o.id), onclick: function () {
        S.winter = o.id; store.set('winter', o.id);
        [].forEach.call(box.children, function (bt, i) { bt.setAttribute('aria-pressed', String(co.options[i].id === o.id)); });
        if (after) after();
      } }, crop(own)));
    });
    return h('div', { class: 'col', style: 'display:flex;flex-direction:column;gap:8px' },
      h('p', { class: 'lead' }, T('from_space.guess_first', { first_crop: crop(first) }) + ' ' + T('from_space.guess_options', { option_a: crop(onlyA), option_b: crop(onlyB) })),
      h('p', { class: 'sub', style: 'font-weight:700;color:var(--ink)' }, T('from_space.guess_which')), box,
      h('p', { class: 'small', style: 'margin:0' }, svg(I('sat', 14)), ' ', T('from_space.guess_cannot_tell')));
  }
  // the crops we think the farmer grows, as a question (owner, 2026-11-14 evening): "We think you grow rice, then potato.
  // Is that right?" Yes keeps our guess; the other rotation is the second button. The answer stays on the phone.
  // its buttons (owner, 2026-11-15: two buttons never mean the same answer): 'Yes' is the option whose crops are the guess,
  // first; every other option is named by its crops; no option is the guess: every one is named. Pure.
  function guessButtons(guess, co) {
    var opts = (co && co.options) || [], g = (guess || []).join('+');
    if (!opts.length) return [{ id: null, yes: true, crops: [] }];
    return opts.map(function (o) {
      var cs = o.crops.map(function (c) { return c.crop; });
      return { id: o.id, yes: cs.join('+') === g, crops: cs };
    }).sort(function (a, b) { return b.yes - a.yes; });
  }
  function guessCard(F, box, after) {
    featData('simple').then(function (sd) {
      if (!sd || !sd.guess || !box.isConnected) return;
      var opts = guessButtons(sd.guess.fill && sd.guess.fill.guess_list, F.current_options);
      function draw() {
        box.textContent = '';
        add(box, [h('p', { class: 'lead' }, say(sd.guess) + ' ' + T('farm.guess_ask')),
          h('div', { class: 'row wrap', role: 'group', 'aria-label': T('farm.guess_ask') }, opts.map(function (o) {
            var label = o.yes ? T('from_space.yes') : cap(o.crops.map(crop).join(', ' + T('join.then') + ' '));
            return h('button', { type: 'button', class: 'choice', 'aria-pressed': String(!!o.id && S.winter === o.id), onclick: function () {
              if (o.id) { S.winter = o.id; store.set('winter', o.id); } draw(); if (after) after();
            } }, label);
          })),
          opts.length > 1 ? h('p', { class: 'small', style: 'margin:0' }, svg(I('sat', 14)), ' ', T('from_space.guess_cannot_tell')) : null,
          nasaTags([['space', yearSpan(srcObj(F, 'hls'))]])]);
      }
      draw(); box.hidden = false;
    });
  }
  function fact(icon, textLines, tags) {
    return h('div', { class: 'fact' }, h('span', { class: 'ic' }, svg(I(icon, 20))), h('div', { class: 'grow', style: 'display:flex;flex-direction:column;gap:6px' }, lines(textLines), tags));
  }
  // ---------------- 2 your farm from the sky (design: Photo, W2_Photo) ----------------
  // NASA's map picture of the field (data/basemap/<id>.json) until a real photo comes; one line from Field Pulse below it.
  var BS_ORDER = [3, 4, 5, 6, 7, 8, 9, 10, 11, 0, 1, 2];   // Baisakh (mid-April) first: the Nepali year
  // the Bikram Sambat months (from the 15th of their Gregorian month) whose days are mostly outside every growing period
  // (site/data/simple/<id>.json pulse_card.growing)
  function restMonths(growing) {
    return BS_ORDER.filter(function (m) {
      var n = 0;
      for (var d = 0; d < MDAYS[m]; d++) if (growing.some(function (g) { return covers({ start: g.from, end: g.to }, (CUM[m] + 14 + d) % 365); })) n++;
      return n * 2 <= MDAYS[m];
    });
  }
  function joinList(xs) { return xs.length < 2 ? (xs[0] || '') : xs.slice(0, -1).join(', ') + ' ' + T('join.and') + ' ' + xs[xs.length - 1]; }
  function restsLine(box) {
    featData('simple').then(function (sd) {
      var g = sd && sd.pulse_card && sd.pulse_card.growing;
      if (!g || !g.length) return;
      var rest = restMonths(g), names = bothMonths() ? monthRuns(rest).map(function (r) { return monthSpan(MONTHS[r[0]], MONTHS[r[1]]); }) : rest.map(function (m) { return bsMonth(MONTHS[m]); });
      box.textContent = '';
      add(box, [h('p', { class: 'rests' }, svg(I('sprout', 20)), h('span', null, rest.length ? [T('home.rests_in'), ' ', h('b', null, joinList(names))] : T('home.never_rests'))),
        rest.length && inNepal() ? h('p', { class: 'small', style: 'margin:0' }, T('from_space.months_note')) : null]);
    });
  }
  var DRONE = '<svg width="64" height="44" viewBox="0 0 120 80"><path d="M30 34 L18 22 M90 34 L102 22 M30 46 L18 56 M90 46 L102 56" stroke="#9A8A6A" stroke-width="5" stroke-linecap="round"/><rect x="34" y="28" width="52" height="24" rx="11" fill="#9A8A6A"/><circle cx="60" cy="58" r="6" fill="#9A8A6A"/><ellipse cx="18" cy="20" rx="13" ry="3" fill="#CDBF9F"/><ellipse cx="102" cy="20" rx="13" ry="3" fill="#CDBF9F"/><ellipse cx="18" cy="58" rx="13" ry="3" fill="#CDBF9F"/><ellipse cx="102" cy="58" rx="13" ry="3" fill="#CDBF9F"/></svg>';
  function roundBtn(label, icon, onclick) { return h('button', { type: 'button', class: 'round big', 'aria-label': label, title: label, onclick: onclick }, svg(I(icon, 24, 2.2))); }
  function leadRow(lead, sub) { return h('div', { class: 'leadrow' }, h('div', { class: 'grow', style: 'display:flex;flex-direction:column;gap:4px' }, lead, sub)); }
  // the day NASA's picture under the field was taken (site/data/basemap/<field>.json 'date', pipeline/fetch/basemap.py):
  // only the field's own picture with a full date; abroad fields show only the world picture, so no line
  function seenLine() {
    var p = h('p', { class: 'seen', hidden: true });
    if (!abroad()) getJSON('data/basemap/' + encodeURIComponent(S.fid) + '.json').then(function (b) {
      if (!b || !/^\d{4}-\d\d-\d\d$/.test(String(b.date || ''))) return;
      add(p, [svg(I('sat', 18)), h('span', null, T('where.seen_space', { date: fmtDate(b.date) }))]); p.hidden = false;
    });
    return p;
  }

  // ---------------- phone as drone: the in-person demo, on the laptop's hotspot only (owner, 2026-11-15) ----------------
  // Never on the public site: demo mode needs BOTH a page served from the laptop or its hotspot (a private address, never
  // github.io) AND the git-ignored switch site/data/demo.json (scripts/demo_mode.py on|off; scripts/check_site.py --final
  // refuses it). The phone's photo from above stays on the phone: an object URL in this page's memory, never sent anywhere,
  // never saved (a reload forgets it). 4 pots stand in for the field's 4 parts (pot n = part n = s<n>); their readings
  // (live.json from robot/bridge.py) show only on the demo's soil screen, on the photo, never as the field's parts anywhere
  // else (probeData ignores live.json in demo mode). A pot's fog clears only with a calibrated reading (sureOf).
  function demoHost(hn) {
    hn = String(hn || '').toLowerCase();
    if (!hn || /github\.io$/.test(hn)) return false;
    return /^(localhost|127(\.\d{1,3}){3}|10(\.\d{1,3}){3}|192\.168(\.\d{1,3}){2}|172\.(1[6-9]|2\d|3[01])(\.\d{1,3}){2}|[a-z0-9-]+\.local)$/.test(hn);
  }
  function demoOn() {
    if (!S.demoP) S.demoP = demoHost(location.hostname) ? getJSON('data/demo.json', true).then(function (d) { return !!d && d.demo === true; }) : Promise.resolve(false);
    return S.demoP;
  }
  // the offline copy (owner, 2026-11-15; sw.js): the public site only, never on the laptop or its hotspot (demoHost: any
  // worker there is removed); without a worker, or if it fails, the app works as before. A new version takes over with one
  // reload. One quiet line while there is no signal.
  function offline() {
    var sw = navigator.serviceWorker;
    try {
      if (!sw) return;
      if (demoHost(location.hostname)) { sw.getRegistrations().then(function (rs) { rs.forEach(function (r) { r.unregister(); }); }).catch(function () {}); return; }
      var had = !!sw.controller;
      sw.addEventListener('controllerchange', function () { if (had) { had = false; location.reload(); } });
      sw.register('sw.js', { updateViaCache: 'none' }).catch(function () {});
    } catch (e) { /* no worker: the app as before */ }
  }
  function offlineLine() {
    var p = h('p', { class: 'offline-line', role: 'status', hidden: navigator.onLine !== false }, T('offline.line'));
    D.body.append(p);
    W.addEventListener('online', function () { p.hidden = true; });
    W.addEventListener('offline', function () { p.hidden = false; });
  }
  function demoLabel() { return h('p', { class: 'demolabel', role: 'note' }, svg(I('camera', 18)), h('span', null, T('drone.label'))); }
  // the phone's camera (a file input: it works over the hotspot's plain http); the photo becomes an object URL in memory
  function takeBtn(round) {
    var id = 'drone-photo-' + (++uid), label = T(S.demoRaw ? 'drone.again' : 'drone.take');
    var input = h('input', { type: 'file', accept: 'image/*', capture: 'environment', class: 'vh', id: id, tabindex: '-1' });
    input.addEventListener('change', function () {
      var f = input.files && input.files[0];
      if (!f || !/^image\//.test(f.type || 'image/')) return;
      if (S.demoRaw) URL.revokeObjectURL(S.demoRaw.url);
      if (S.demoPhoto) URL.revokeObjectURL(S.demoPhoto.url);
      S.demoRaw = { url: URL.createObjectURL(f), at: new Date(), quad: null };   // the phone's own clock, when the photo came back
      S.demoPhoto = null;                                                    // the corners first, then the parts
      rerender();
    });
    var btn = round ? h('label', { for: id, class: 'round big', role: 'button', tabindex: '0', 'aria-label': label, title: label }, svg(I('camera', 24, 2.2)))
      : h('label', { for: id, class: 'cta take', role: 'button', tabindex: '0' }, svg(I('camera', 24, 2.2)), h('span', null, label));
    btn.addEventListener('keydown', function (e) { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.click(); } });
    return [input, btn];
  }
  function takenAt(d) {
    function two(n) { return ('0' + n).slice(-2); }
    return fmtDate(d.getFullYear() + '-' + two(d.getMonth() + 1) + '-' + two(d.getDate())) + ', ' + digits(two(d.getHours()) + ':' + two(d.getMinutes()));
  }
  // The square on the camera step and the corners after it (owner, 2026-11-15). A page on the hotspot's plain http cannot
  // draw over the phone's own camera, so the square shows before the camera opens; after the photo the four corners are
  // dragged onto the pots, and the photo inside them is straightened into the square the 4 parts are drawn on, on the phone.
  // quadMap: the unit square (u, v) onto the corners [top-left, top-right, bottom-right, bottom-left], the projective
  // square-to-quad mapping of Heckbert (1989, Fundamentals of Texture Mapping, sec. 2.2.3).
  function quadMap(q) {
    var x0 = q[0][0], y0 = q[0][1], x1 = q[1][0], y1 = q[1][1], x2 = q[2][0], y2 = q[2][1], x3 = q[3][0], y3 = q[3][1];
    var sx = x0 - x1 + x2 - x3, sy = y0 - y1 + y2 - y3, g = 0, k = 0, a = x1 - x0, b = x3 - x0, d = y1 - y0, e = y3 - y0;
    if (Math.abs(sx) > 1e-12 || Math.abs(sy) > 1e-12) {
      var dx1 = x1 - x2, dx2 = x3 - x2, dy1 = y1 - y2, dy2 = y3 - y2, den = dx1 * dy2 - dx2 * dy1;
      g = (sx * dy2 - dx2 * sy) / den; k = (dx1 * sy - sx * dy1) / den;
      a = x1 - x0 + g * x1; b = x3 - x0 + k * x3; d = y1 - y0 + g * y1; e = y3 - y0 + k * y3;
    }
    return function (u, v) { var w = g * u + k * v + 1; return [(a * u + b * v + x0) / w, (d * u + e * v + y0) / w]; };
  }
  function guideBox() {   // before the camera: 4 pots inside a square, numbered as the parts (3 4 at the back, 1 2 in front)
    var pot = function (x, y, n) {
      return '<circle cx="' + x + '" cy="' + y + '" r="23" fill="#9A5426"/><circle cx="' + x + '" cy="' + y + '" r="16" fill="#5E3A1C"/>' +
        '<text x="' + x + '" y="' + (y + 6) + '" text-anchor="middle" font-size="17" font-weight="800" fill="#FBF4EA">' + digits(n) + '</text>';
    };
    var g = h('div', { class: 'mapbox photo guide' });
    g.append(svg('<svg viewBox="0 0 200 200" aria-hidden="true"><rect x="22" y="22" width="156" height="156" rx="8" fill="none" stroke="#C8E05A" stroke-width="4" stroke-dasharray="12 9"/>' +
      pot(65, 65, 3) + pot(135, 65, 4) + pot(65, 135, 1) + pot(135, 135, 2) + '</svg>'), h('p', { class: 'gtext' }, T('drone.fit_guide')));
    return g;
  }
  function fitView(raw) {   // the photo with four corners to drag; a preview of the 4 parts inside them
    var box = h('div', { class: 'fitbox' }), img = h('img', { class: 'fitimg', src: raw.url, alt: '' }), lines_ = D.createElementNS(SVGNS, 'svg');
    lines_.setAttribute('viewBox', '0 0 100 100'); lines_.setAttribute('preserveAspectRatio', 'none'); lines_.setAttribute('class', 'fitlines');
    box.append(img, lines_);
    var nums = [[0.25, 0.25, 3], [0.75, 0.25, 4], [0.25, 0.75, 1], [0.75, 0.75, 2]].map(function (n) { var el = h('span', { class: 'fn' }, digits(n[2])); box.append(el); return { u: n[0], v: n[1], el: el }; });
    var hs = [0, 1, 2, 3].map(function (i) { var el = h('span', { class: 'fithandle', tabindex: '0', role: 'button', 'aria-label': T('drone.fit_drag') + ' ' + digits(i + 1) }); box.append(el); return el; });
    function clamp(x) { return Math.max(0, Math.min(1, x)); }
    function pt(p) { return (p[0] * 100).toFixed(2) + ',' + (p[1] * 100).toFixed(2); }
    function draw() {
      var q = raw.quad;
      if (!q) return;
      var m = quadMap(q);
      lines_.innerHTML = '<polygon points="' + q.map(pt).join(' ') + '"/><line x1="' + m(0.5, 0)[0] * 100 + '" y1="' + m(0.5, 0)[1] * 100 + '" x2="' + m(0.5, 1)[0] * 100 + '" y2="' + m(0.5, 1)[1] * 100 + '"/>' +
        '<line x1="' + m(0, 0.5)[0] * 100 + '" y1="' + m(0, 0.5)[1] * 100 + '" x2="' + m(1, 0.5)[0] * 100 + '" y2="' + m(1, 0.5)[1] * 100 + '"/>';
      hs.forEach(function (el, i) { el.style.left = q[i][0] * 100 + '%'; el.style.top = q[i][1] * 100 + '%'; });
      nums.forEach(function (n) { var c = m(n.u, n.v); n.el.style.left = c[0] * 100 + '%'; n.el.style.top = c[1] * 100 + '%'; });
    }
    function start() {   // first time: a square in the middle, 80% of the photo's shorter side
      if (!raw.quad) {
        var w = img.naturalWidth || 1, hh = img.naturalHeight || 1, sd = 0.8 * Math.min(w, hh), fx = sd / w / 2, fy = sd / hh / 2;
        raw.quad = [[0.5 - fx, 0.5 - fy], [0.5 + fx, 0.5 - fy], [0.5 + fx, 0.5 + fy], [0.5 - fx, 0.5 + fy]];
      }
      draw();
    }
    if (img.complete && img.naturalWidth) start(); else img.addEventListener('load', start);
    var drag = -1;
    hs.forEach(function (el, i) {
      el.addEventListener('pointerdown', function (e) { e.preventDefault(); el.setPointerCapture(e.pointerId); drag = i; el.classList.add('on'); });
      el.addEventListener('pointermove', function (e) {
        if (drag !== i || !raw.quad) return;
        var r = box.getBoundingClientRect();
        raw.quad[i] = [clamp((e.clientX - r.left) / r.width), clamp((e.clientY - r.top) / r.height)]; draw();
      });
      function up() { drag = -1; el.classList.remove('on'); }
      el.addEventListener('pointerup', up); el.addEventListener('pointercancel', up);
      el.addEventListener('keydown', function (e) {   // the keyboard too: arrows move a corner by 1%
        var dv = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[e.key];
        if (!dv || !raw.quad) return;
        e.preventDefault(); raw.quad[i] = [clamp(raw.quad[i][0] + dv[0] / 100), clamp(raw.quad[i][1] + dv[1] / 100)]; draw();
      });
    });
    return { el: box, img: img };
  }
  // the photo inside the corners, straightened into a square (bilinear, at most 1600 px read, 900 px out), kept in memory
  function straighten(raw, img, done) {
    var nw = img.naturalWidth, nh = img.naturalHeight, sc = Math.min(1, 1600 / Math.max(nw, nh)), cw = Math.max(1, Math.round(nw * sc)), ch = Math.max(1, Math.round(nh * sc));
    var src = D.createElement('canvas'); src.width = cw; src.height = ch;
    var sx = src.getContext('2d'); sx.drawImage(img, 0, 0, cw, ch);
    var sd = sx.getImageData(0, 0, cw, ch).data, N = 900, out = D.createElement('canvas'); out.width = N; out.height = N;
    var ox = out.getContext('2d'), od = ox.createImageData(N, N), o = od.data;
    var m = quadMap(raw.quad.map(function (p) { return [p[0] * cw, p[1] * ch]; }));
    for (var j = 0; j < N; j++) for (var i = 0; i < N; i++) {
      var p = m((i + 0.5) / N, (j + 0.5) / N), x = Math.min(cw - 1, Math.max(0, p[0] - 0.5)), y = Math.min(ch - 1, Math.max(0, p[1] - 0.5));
      var x0 = Math.floor(x), y0 = Math.floor(y), x1 = Math.min(cw - 1, x0 + 1), y1 = Math.min(ch - 1, y0 + 1), fx = x - x0, fy = y - y0;
      var i00 = (y0 * cw + x0) * 4, i10 = (y0 * cw + x1) * 4, i01 = (y1 * cw + x0) * 4, i11 = (y1 * cw + x1) * 4, t = (j * N + i) * 4;
      for (var c = 0; c < 3; c++) o[t + c] = (sd[i00 + c] * (1 - fx) + sd[i10 + c] * fx) * (1 - fy) + (sd[i01 + c] * (1 - fx) + sd[i11 + c] * fx) * fy;
      o[t + 3] = 255;
    }
    ox.putImageData(od, 0, 0);
    out.toBlob(function (b) { done(b ? URL.createObjectURL(b) : null); }, 'image/jpeg', 0.9);
  }
  function demoPhoto(F) {
    var raw = S.demoRaw, p = S.demoPhoto, head = [stepsBar(1), bigTitle(T('where.sky_h1'), T('where.sky_h2')), demoLabel()];
    if (raw && !p) {         // the corners first
      var fv = fitView(raw), doneBtn = cta(T('drone.fit_done'), function () {
        if (!raw.quad || doneBtn.disabled) return;
        doneBtn.disabled = true;
        setTimeout(function () {   // let the button show it was pressed before the straightening runs
          straighten(raw, fv.img, function (url) { doneBtn.disabled = false; if (!url) return; S.demoPhoto = { url: url, at: raw.at }; rerender(); });
        }, 30);
      });
      return screen('photo', { head: head, scene: fv.el, body: [h('p', { class: 'lead' }, T('drone.fit_drag')), h('p', { class: 'sub' }, T('drone.stays'))],
        cta: h('div', { class: 'ctarow' }, takeBtn(true), doneBtn) });
    }
    return screen('photo', {
      head: head,
      scene: p ? fieldBox(F, 'sway', { photo: p.url })
        : guideBox(),
      body: p ? [h('p', { class: 'taken' }, svg(I('camera', 18)), h('span', null, T('drone.taken') + ' ' + takenAt(p.at)), svg(I('tick', 18, 3), 'ok')),
        leadRow(h('p', { class: 'lead' }, T('where.is_this')), h('p', { class: 'sub' }, T('drone.stays'))),
        btn2(T('drone.fit_again'), function () { URL.revokeObjectURL(p.url); S.demoPhoto = null; rerender(); }, 'redo')] : [seenLine()],
      cta: h('div', { class: 'ctarow' }, takeBtn(!!raw), p ? cta(T('drone.yes'), function () { go('parts'); }) : null)
    });
  }
  // a pot's result in the stick's own words: drier, wetter or about the same as the other pots (robot/calibrate.py
  // relative, rules.yaml probe.same_band_pct); 'none' when it gave no steady reading; nothing before its reading
  function potWord(p) {
    if (!p) return null;
    if (p.state === 'test_again') return 'none';
    if (p.state !== 'done' || !p.relative) return null;
    return { drier: 'drier', wetter: 'wetter' }[p.relative] || 'same';
  }
  function potMarks(box, G, parts) {   // a word on each pot's part of the photo
    G.forEach(function (g) {
      var w = potWord(parts[g.s.id]);
      if (g.chip) { g.chip.remove(); g.chip = null; }
      if (!w || w === 'none') return;
      g.chip = h('span', { class: 'pchip ' + w, style: 'left:' + (g.l + 2) + '%;top:' + (g.b - 3) + '%' },
        w === 'same' ? null : svg(I(w === 'wetter' ? 'drop' : 'sun', 13, 2.4)), T('drone.chip_' + w));
      box.append(g.chip);
    });
  }
  function potLines(G, parts) {        // "Pot 3 is wetter than the others.", one line per pot read, right under the photo
    var out = G.map(function (g) { var w = potWord(parts[g.s.id]); return w ? T('drone.pot_' + w, { section: g.n }) : null; }).filter(Boolean);
    return out.length ? lines(out, 'potlines') : null;
  }
  function demoProbe() {               // the pots' walk: live.json from a real serial port only, as the field's walk
    return getJSON('data/live.json', true).then(function (lv) {
      return lv && isReal(lv.source) && (lv.section || (lv.parts || []).length) ? { kind: 'live', live: lv, parts: liveParts(lv), demo: true }
        : { kind: 'none', parts: {}, demo: true };
    });
  }
  // ---------------- end of phone as drone ----------------
  SCREENS.photo = function () {
    return withField('photo', function (F) {
      if (S.demo) return demoPhoto(F);
      var sample = isPlaceholder(F.field.name) && !F._drone, dr = F._drone;
      var mapEl = h('div', { style: 'position:absolute;inset:0' });
      var mbox = h('div', { class: 'mapbox photo' }, h('div', { class: 'msg' }, svg(DRONE), h('span', { class: 'yf' }, T('where.your_farm')), h('span', { class: 'hint' }, T('where.photo_later'))), mapEl,
        sample ? h('div', { class: 'mapnote' }, sampleChip()) : null);
      var drawbar = h('div', { class: 'drawbar', hidden: true }), msg = h('div', { 'aria-live': 'polite' });
      var map = null, Lf = null, draw = null;
      loadLeaflet().then(function (L) {
        if (!mapEl.isConnected) return;
        Lf = L; mbox.querySelector('.msg').remove();
        map = L.map(mapEl, { scrollWheelZoom: false, zoomSnap: 0.5, maxZoom: dr ? 21 : 18 });
        osm(L, map);
        if (dr) {   // the drone photo and the field's outline only (fix A1, 2026-11-15: the parts come on the next screen)
          L.imageOverlay(dr.image, dr.bounds, { attribution: dr.credit, interactive: false }).addTo(map);
          var dro = L.polygon(dr.outline.map(function (p) { return [p[1], p[0]]; }), { color: '#C8E05A', weight: 3, fill: false, interactive: false }).addTo(map);
          map.fitBounds(dro.getBounds(), { padding: [24, 24], maxZoom: 21 });
        }
        var pts = [];
        (dr ? [] : F.field.sections || []).forEach(function (s) {
          var ll = s.polygon.map(function (p) { return [p[1], p[0]]; }); pts = pts.concat(s.polygon);
          L.polygon(ll, { color: '#FBF4EA', weight: 1.5, dashArray: '4 5', fill: false, interactive: false }).addTo(map);
        });
        if (pts.length && !dr) {
          var hl = hull(pts).map(function (p) { return [p[1], p[0]]; });
          L.polygon(hl, { color: '#14301E', weight: 7, opacity: .35, fill: false, interactive: false }).addTo(map);
          var outline = L.polygon(hl, { color: '#C8E05A', weight: 4, fillColor: '#C8E05A', fillOpacity: .12, interactive: false }).addTo(map);
          map.fitBounds(outline.getBounds(), { padding: [60, 60], maxZoom: abroad() ? 9 : 16 });   // abroad: only the coarse world picture
          if (!abroad()) getJSON('data/basemap/' + encodeURIComponent(S.fid) + '.json').then(function (b) { if (b && b.bounds && !draw) map.setMaxBounds(L.latLngBounds(b.bounds).pad(0.1)); });
        } else if (!dr) map.setView([F.field.lat, F.field.lon], 17);
      }).catch(function () { /* the drone picture and "a real photo comes when we visit" stay */ });
      function startDraw() {
        if (!map) return;
        if (draw) { draw.layer.remove(); }
        if (!draw) { osm(Lf, map, 'only'); map.setMaxBounds(null); }   // the world picture, so a field outside the box still shows something
        draw = { pts: [], layer: Lf.layerGroup().addTo(map) };
        msg.textContent = '';
        drawbar.hidden = false; drawbar.textContent = '';
        var done = h('button', { type: 'button', class: 'btn2', disabled: true, onclick: finish }, T('where.done'));
        drawbar.append(h('span', null, T('where.corners')), done);
        map.on('click', onTap);
        function onTap(e) {
          if (draw.pts.length >= 4) return;
          draw.pts.push(e.latlng);
          Lf.circleMarker(e.latlng, { radius: 8, color: '#14301E', weight: 3, fillColor: '#C8E05A', fillOpacity: 1 }).addTo(draw.layer);
          if (draw.pts.length > 1) Lf.polyline(draw.pts, { color: '#9A5426', weight: 3 }).addTo(draw.layer);
          if (draw.pts.length === 4) { Lf.polygon(draw.pts, { color: '#9A5426', weight: 3, fillOpacity: .15 }).addTo(draw.layer); done.disabled = false; }
        }
        function finish() {
          map.off('click', onTap); drawbar.hidden = true;
          var lat = 0, lon = 0; draw.pts.forEach(function (p) { lat += p.lat / 4; lon += p.lng / 4; });
          var inside = ((S.index && S.index.fields) || []).filter(function (f) { var b = f.bbox; return lon >= b[0] && lon <= b[2] && lat >= b[1] && lat <= b[3]; })[0];
          msg.textContent = '';
          if (inside) msg.append(h('div', { class: 'card soft' }, h('p', { class: 'lead' }, T('where.inside_sample'))));
          else msg.append(h('div', { class: 'card soft' }, h('p', { class: 'lead' }, T('where.outside')),
            btn2(T('where.outside_try'), function () { draw.layer.remove(); draw = null; msg.textContent = ''; }, 'redo')));
        }
      }
      mbox.append(drawbar);
      var rests = h('div', { class: 'col', style: 'display:flex;flex-direction:column;gap:4px' });
      restsLine(rests);
      var guess = h('div', { class: 'card guess', hidden: true });
      guessCard(F, guess);
      return screen('photo', {
        head: [stepsBar(1), bigTitle(T('where.sky_h1'), T('where.sky_h2')), dr ? fieldChip(F) : null],
        scene: mbox,
        body: [msg, dr ? null : seenLine(), leadRow(h('p', { class: 'lead' }, T('where.is_this')), h('p', { class: 'sub' }, T('where.split_next'))), guess, rests,
          dr ? lines([droneSat(dr)], 'sub') : null, dr ? droneCredit(dr) : null],
        cta: h('div', { class: 'ctarow' }, roundBtn(T('where.draw_own'), 'pin', startDraw), cta(T('where.yes_parts'), function () { go('parts'); }))
      });
    });
  };

  // ---------------- 3 your farm, in parts (design: Parts, W3_Parts) ----------------
  SCREENS.parts = function () {
    return withField('parts', function (F) {
      var n = (F.field.sections || []).length, ph = S.demo && S.demoPhoto;
      var lead = h('p', { class: 'lead', 'aria-live': 'polite' }, T('parts.making'));
      later(function () { lead.textContent = T('parts.here', { section_count: n }); }, 2000);
      return screen('parts', {
        head: [stepsBar(2), bigTitle(T('parts.h1'), T('parts.h2', { section_count: n })), S.demo ? demoLabel() : fieldChip(F)],
        scene: [fieldBox(F, 'grow', ph ? { photo: ph.url } : null), F._drone && !ph ? droneCredit(F._drone) : null],
        body: leadRow(lead, h('p', { class: 'sub' }, T('parts.middle'))),
        cta: cta(T('parts.start_test'), function () { go('soil'); })
      });
    });
  };

  // ---------------- 4 the soil test, part by part (design: Robot, W4_Robot) ----------------
  // The walk is the real one: live.json during the in-person demo, else the recorded walk (probe_log.json); with neither,
  // every part says "not tested yet". Only readings of the field from a real serial port are shown (robot/bridge.py
  // is_real), each with its date; a practice run and a garden or indoor test never show as the field's parts (owner,
  // 2026-11-15; rules.yaml probe.live): the screen then says "Readings come after our team tests it". The robot is
  // drawn as the plan (Krishi Scout); the words say a person carries the prototype soil stick, so no sentence says a robot
  // tested anything.
  function liveParts(lv) {
    var m = {};
    (lv.parts || []).forEach(function (p) { if (p && p.section) m[p.section] = Object.assign({ state: 'done' }, p); });
    if (lv.section) m[lv.section] = Object.assign({}, m[lv.section] || {}, lv);
    return m;
  }
  function isReal(src) { return /^serial:./.test(String(src || '')); }
  // Owner, 2026-11-15: practice and indoor-bowl readings never show as the field's parts (a practice reading is not read at
  // all; a garden or indoor test shows only on How we know, as bowls); the soil screen waits for the field's real test
  function forField(pd) { return !!pd && !pd.test; }   // readings that may stand for the field itself
  var TEST_LABEL = { garden_test: ['garden_on'], indoor_test: ['indoor_title', 'indoor_on'] };   // a test of the stick, not the field
  function probeData() {
    return Promise.all([demoOn(), getJSON('data/live.json', true), getJSON('data/probe_log.json')]).then(function (r) {
      var demo = r[0], lv = r[1], log = r[2];   // phone as drone: in demo mode live.json holds the 4 pots, never the field
      if (lv && !demo && isReal(lv.source) && (lv.section || (lv.parts || []).length))
        return (S.probe = { kind: 'live', live: lv, parts: liveParts(lv) });
      var sess = log && (log.sessions || []).filter(function (x) { return isReal(x.source); }).pop();
      if (sess && sess.parts && sess.parts.length) {
        var m = {}; sess.parts.forEach(function (p) { m[p.section] = p; });
        return (S.probe = { kind: 'log', log: log, sess: sess, parts: m, test: TEST_LABEL[log.kind] ? log.kind : null });
      }
      return (S.probe = { kind: 'none', parts: {} });
    });
  }
  function anyTested(pd) { return !!pd && Object.keys(pd.parts).some(function (k) { return pd.parts[k].state === 'done'; }); }
  // ---------------- space guesses, the ground checks: fog on each part (owner, 2026-11-15) ----------------
  // How sure we are of a part's soil water, out of 100. Before the stick: the twin alone (field.sections[].sure, or the
  // recorded or live reading's own "before"). After: the Kalman update robot/bridge.py made with that reading (only once
  // the bench test gave the stick's error; rules.yaml probe.kalman.r). A test away from the field (garden, bowls) never
  // changes the field's number, and no number means the fog stays: nothing is guessed.
  function sureOf(F, pd, sid) {
    var sec = mocked(F, 'field.sections') ? null : (F.field.sections || []).filter(function (s) { return s.id === sid; })[0];
    var out = { before: sec && typeof sec.sure === 'number' ? sec.sure : null, after: null }, ok = pd && !pd.test, r = ok && pd.parts[sid];
    // the update's own "before" once a reading exists: the twin aged to the reading's day (rec: every recorded part)
    var rb = ok && pd.kind === 'log' ? (r && r.before) || (pd.rec && pd.rec[sid] && pd.rec[sid].before) : ok && pd.kind === 'live' ? pd.live && pd.live.prior : null;
    if (rb && rb.sure != null) out.before = rb.sure;
    if (r && r.state === 'done') out.after = pd.kind === 'log' ? (r.after ? r.after.sure : null) : pd.kind === 'live' && r.sure != null ? r.sure : null;
    if (pd && pd.demo && !(r && r.water_pct != null)) out.after = null;   // phone as drone: only a calibrated reading clears a pot's fog
    return out;
  }
  function fogOpacity(s) { return (0.85 * (1 - Math.max(0, Math.min(1, s == null ? 0 : s)))).toFixed(2); }
  // the fog over every part of a field box and its number; .set(pd) clears each part the stick has checked to its new
  // number (a gentle fade and count; under reduced motion the before and after numbers only); .note(pd) says why not
  function fogParts(box, F) {
    var G = box._g, roomy = G.length <= 6, tpl = T('fog.sure_n'), at = tpl.indexOf('{sure_pct}'), fogs = {};
    function label(v) { return at < 0 ? num(v) : [tpl.slice(0, at), h('b', { class: 'fn' }, num(v)), tpl.slice(at + 10)]; }
    G.forEach(function (g) {
      var s0 = sureOf(F, null, g.s.id).before, svgPart = g.q.namespaceURI === SVGNS, f = { s0: s0, now: s0 };
      if (s0 == null) return;
      if (svgPart) { g.q.style.fill = 'rgba(250,247,240,' + fogOpacity(s0) + ')'; f.q = g.q; fogs[g.s.id] = f; return; }
      f.el = h('span', { class: 'sfog', style: 'left:' + g.l + '%;top:' + g.t + '%;width:' + (g.r - g.l) + '%;height:' + (g.b - g.t) + '%;--fog:' + fogOpacity(s0) });
      f.lab = h('span', { class: 'flab' + (roomy ? '' : ' small') }, roomy ? h('span', { class: 'fq' }, T('fog.how_sure')) : null, h('span', { class: 'fv' }, label(Math.round(s0 * 100))), h('span', { class: 'fb' }));
      f.el.append(f.lab); box.append(f.el); fogs[g.s.id] = f;
    });
    // a part not checked yet takes the update's own "before" at once (no animation); a checked one clears to its "after"
    function set(pd) {
      Object.keys(fogs).forEach(function (sid) {
        var f = fogs[sid], s = sureOf(F, pd, sid), a = s.after, to = a != null ? a : s.before;
        if (to == null || to === f.now) return;
        var b = Math.round((s.before == null ? f.s0 : s.before) * 100), n = Math.round(to * 100);
        f.now = to;
        if (f.q) { f.q.style.fill = 'rgba(250,247,240,' + fogOpacity(to) + ')'; return; }
        var fv = f.lab.querySelector('.fv'), fb = f.lab.querySelector('.fb');
        function show(v) { fv.textContent = ''; add(fv, label(v)); }
        if (a == null) {   // no fade: the style is read once with the transition off
          f.el.classList.add('still'); f.el.style.setProperty('--fog', fogOpacity(to)); W.getComputedStyle(f.el, '::before').opacity; f.el.classList.remove('still'); show(n); return;
        }
        f.el.style.setProperty('--fog', fogOpacity(a)); f.el.classList.add('clear');
        fb.textContent = T('fog.sure_before') + ': ' + num(b);
        if (RM) { show(n); return; }
        var t0 = Date.now();
        // gentle motion (2026-11-15): the number counts in 300 ms, as the fog clears (css .sfog::before)
        (function tick() { var k = Math.min(1, (Date.now() - t0) / 300); show(Math.round(b + (n - b) * k)); if (k < 1 && fv.isConnected) W.requestAnimationFrame(tick); })();
      });
    }
    // one line under the field when a checked part keeps its fog: a test away from the field, or no bench test yet
    function note(pd) {
      if (!Object.keys(fogs).length || !anyTested(pd)) return null;
      if (pd.test) return T('fog.fog_test');
      return Object.keys(pd.parts).some(function (k) { return fogs[k] && pd.parts[k].state === 'done' && sureOf(F, pd, k).after == null; }) ? T('fog.sure_wait') : null;
    }
    return { set: set, note: note, any: Object.keys(fogs).length > 0 };
  }
  // one part's word from its reading: the probe's band (good, needs water, too wet) once the bench calibration exists,
  // else only drier or wetter than the other parts; "not tested yet" without a reading
  function partWord(r) {
    if (!r || !r.state) return { k: 'none', word: T('check_soil.not_tested') };
    if (r.state === 'test_again') return { k: 'care', word: T('check_soil.again') };
    if (r.state !== 'done') return { k: 'now', word: T('check_soil.' + (r.state === 'settling' ? 'settling' : 'measuring')) };
    if (r.band) return { k: r.band === 'good' ? 'good' : 'care', word: T('check_soil.band_' + r.band.replace(/ /g, '_')), band: r.band };
    if (r.off_scale) return { k: 'care', word: T('check_soil.off_scale') };
    if (r.relative) return { k: 'info', word: T('check_soil.' + ({ drier: 'drier', wetter: 'wetter' }[r.relative] || 'about_same')) };
    return { k: 'info', word: T('check_soil.tested') };
  }
  function recordedLine(pd) {
    var days = !pd ? [] : pd.kind === 'log' ? pd.log.recorded_on || [] : pd.kind === 'live' && pd.live.time ? [String(pd.live.time).slice(0, 10)] : [];
    if (!days.length) return null;
    return h('p', { class: 'small', style: 'margin:0;font-weight:700;color:var(--ink)' }, svg(I('stick', 14)), ' ', (pd.test ? TEST_LABEL[pd.test] : ['recorded_on']).map(function (k) { return T('check_soil.' + k); }).join(' ') + ' ' +
      days.map(fmtDate).join(', ') + (pd.kind === 'log' && pd.log.place ? ' · ' + pd.log.place : ''));
  }
  // an indoor test: one plain line per bowl, then the watered bowl's check (rules.yaml probe.live.watered_check)
  function bowlLines(pd) {
    if (!pd || pd.test !== 'indoor_test') return null;
    var c = pd.sess.check, out = Object.keys(pd.parts).sort().map(function (s) {
      var p = pd.parts[s], w = !p || p.state !== 'done' ? 'none' : { drier: 'drier', wetter: 'wetter' }[p.relative] || 'same';
      return T('check_soil.bowl_' + w, { section: +s.slice(1) });
    });
    if (c && c.possible) out.push(T('check_soil.bowl_watered_' + (c.passed ? 'yes' : 'no'), { section: +c.watered.slice(1) }));
    return lines(out, 'sub');
  }
  SCREENS.soil = function () {
    return withField('soil', function (F) {
      var demo = !!S.demo, ph = demo && S.demoPhoto, pcap = h('div', { class: 'potcap', 'aria-live': 'polite' });   // phone as drone: the photo, and the pots' results under it
      var box = fieldBox(F, 'robot', ph ? { photo: ph.url } : null), G = box._g, fog = fogParts(box, F), fnote = h('p', { class: 'small fognote' }), liveNow = null;
      var route = D.createElementNS('http://www.w3.org/2000/svg', 'svg');
      route.setAttribute('class', 'route'); route.setAttribute('viewBox', '0 0 100 100'); route.setAttribute('preserveAspectRatio', 'none');
      box.append(route);
      // with the fog's labels at the top of each part, the robot stands just above its part's number, clear of the label
      var atnum = !!box.querySelector('.sfog .flab'), spot = function (g) { return [g.cx, atnum && g.ny != null ? g.ny : g.cy]; };
      var pos = G.length ? spot(G[0]) : [7, 50];   // the robot waits on part 1, where its path starts
      var robot = h('div', { class: 'robot' + (G.length > 6 ? ' small' : '') + (atnum ? ' atnum' : ''), style: 'left:' + pos[0] + '%;top:' + pos[1] + '%' }); robot.innerHTML = ROBOT; box.append(robot);
      var ring = h('span', { class: 'ring', hidden: true }); box.append(ring);
      function moveTo(g, then) {
        var b = spot(g), ms = RM ? 0 : Math.max(900, Math.round(Math.hypot(b[0] - pos[0], b[1] - pos[1]) * 22));
        if (!RM) {
          var ln = D.createElementNS('http://www.w3.org/2000/svg', 'line');
          [['x1', pos[0]], ['y1', pos[1]], ['x2', b[0]], ['y2', b[1]], ['pathLength', 1], ['stroke-dasharray', 1], ['stroke', '#9A5426'], ['stroke-width', 0.6], ['stroke-linecap', 'round'], ['stroke-opacity', .5]]
            .forEach(function (kv) { ln.setAttribute(kv[0], kv[1]); });
          ln.setAttribute('style', 'stroke-dashoffset:1;animation:ks-draw ' + ms + 'ms cubic-bezier(.45,0,.3,1) forwards');
          route.append(ln);
        }
        robot.style.transitionDuration = ms + 'ms';
        robot.firstChild.setAttribute('class', 'moving');
        robot.firstChild.style.transform = b[0] < pos[0] - 1 ? 'scaleX(-1)' : '';
        robot.style.left = b[0] + '%'; robot.style.top = b[1] + '%';
        pos = b;
        later(function () {
          robot.firstChild.setAttribute('class', 'probing'); ring.hidden = false; ring.style.left = b[0] + '%'; ring.style.top = b[1] + '%';
          robot.querySelector('.led').setAttribute('fill', '#F2C230');
          if (then) then();
        }, ms);
      }
      function rest(happy) {
        ring.hidden = true; robot.firstChild.setAttribute('class', happy ? 'happy' : '');
        robot.querySelector('.led').setAttribute('fill', happy ? '#5FBF6A' : '#E9A948');
      }
      var rows = h('div', { class: 'prows', 'aria-live': 'polite' }), info = h('div', { class: 'col', style: 'display:flex;flex-direction:column;gap:8px' });
      var ctaBox = h('div', { class: 'ctarow' }), shown = {}, pd = null;
      function drawRows(cur) {
        rows.textContent = '';
        G.forEach(function (g) {
          var r = shown[g.s.id], w = partWord(r), done = !!(r && r.state === 'done');
          rows.append(h('div', { class: 'prow ' + (done ? 'done' : r ? 'now' : 'wait') + (cur === g.s.id ? ' cur' : '') },
            h('span', { class: 'pn' }, T('each_part.part_name', { section: g.n })),
            h('span', { class: 'ps' }, done ? [T('check_soil.tested'), ' ', svg(I('tick', 14, 3))] : w.word)));
          var prop = g.q.namespaceURI === SVGNS ? 'fill' : 'background';
          if (g.q.dataset.bg == null) g.q.dataset.bg = g.q.style[prop];
          g.q.style[prop] = done ? 'rgba(200,224,90,' + (prop === 'fill' ? '.45' : '.28') + ')' : g.q.dataset.bg;   // the design's tested quarter
          if (g.num) { g.num.classList.toggle('ok', done); g.num.textContent = done ? '' : digits(g.n); if (done) g.num.append(svg(I('tick', 16, 3.2))); }
        });
        var now = { kind: pd ? pd.kind : 'none', test: pd && pd.test, live: liveNow, parts: shown, rec: pd && pd.parts, demo: !!(pd && pd.demo) };
        fog.set(now); fnote.textContent = fog.note(now) || '';   // the fog clears where the stick checked the field
        if (demo) { potMarks(box, G, shown); pcap.textContent = ''; add(pcap, potLines(G, shown)); }
      }
      function drawCta(active) {
        ctaBox.textContent = '';
        if (active) { ctaBox.append(h('button', { type: 'button', class: 'cta wait', disabled: true }, T('check_soil.measuring'))); return; }
        if (pd && pd.kind === 'log' && forField(pd)) ctaBox.append(roundBtn(T('check_soil.replay_check'), 'redo', function () { walk(pd.sess.parts); }));
        ctaBox.append(cta(T('check_soil.see_what'), function () { go('choose'); }));
      }
      // the recorded walk, part by part, at the pace of the design's animation (the readings are the recorded ones)
      function walk(parts) {
        clearTimers(); shown = {}; [].slice.call(route.childNodes).forEach(function (n) { n.remove(); }); drawRows(); drawCta(true); tbox.textContent = '';
        if (G.length) { pos = spot(G[0]); robot.style.transitionDuration = '0ms'; robot.style.left = pos[0] + '%'; robot.style.top = pos[1] + '%'; }   // a replay starts again at part 1
        var i = 0;
        function step() {
          if (i >= parts.length) { rest(true); drawRows(); drawCta(false); add(tbox, bowlLines(pd)); return; }
          var p = parts[i], g = G.filter(function (x) { return x.s.id === p.section; })[0];
          if (!g) { i++; step(); return; }
          moveTo(g, function () {
            shown[p.section] = { state: 'measuring' }; drawRows(p.section);
            later(function () { shown[p.section] = p; ring.hidden = true; drawRows(); i++; step(); }, 1200);
          });
        }
        later(step, 700);
      }
      var lastSec = null;
      function fromLive(lv) {
        if (pd && pd.demo) { pd.kind = 'live'; pd.live = lv; pd.parts = liveParts(lv); }
        shown = liveParts(lv); liveNow = lv; drawRows(lv.section);
        var g = G.filter(function (x) { return x.s.id === lv.section; })[0];
        if (g && lv.section !== lastSec) { lastSec = lv.section; moveTo(g); }
        if (lv.state === 'done' && g) ring.hidden = true;
        var active = !lv.stale && (lv.state === 'settling' || lv.state === 'measuring');
        info.textContent = '';
        add(info, recordedLine({ kind: 'live', live: lv }));
        if (lv.stale) info.append(h('p', { class: 'lead', style: 'margin:0' }, svg(I('warn', 18, 3)), ' ', T('check_soil.not_connected')));
        else if (active) info.append(h('p', { class: 'sub', style: 'margin:0' }, T('check_soil.hold')));
        drawCta(active);
      }
      drawRows(); drawCta(false);
      (demo ? demoProbe() : probeData()).then(function (d) {
        pd = d;
        if (d.kind === 'live' || demo) {
          if (d.kind === 'live') fromLive(d.live);
          else info.append(h('p', { class: 'sub', style: 'margin:0;font-weight:600;color:var(--ink)' }, T('drone.start')));
          every(function () { getJSON('data/live.json', true).then(function (x) { if (x && isReal(x.source) && rows.isConnected) fromLive(x); }); }, 2000);
        } else if (d.kind === 'log' && forField(d)) {
          add(info, recordedLine(d));
          walk(d.sess.parts);
        } else {
          info.append(h('p', { class: 'sub', style: 'margin:0;font-weight:600;color:var(--ink)' }, T('check_soil.after_test')));
          drawCta(false);
        }
      });
      var honest = h('div', { class: 'card honest' }, lines([T('check_soil.prototype'), T('check_soil.by_hand'), T('check_soil.robot_next')], 'sub')), tbox = h('div');
      return screen('soil', {
        head: [stepsBar(3), bigTitle(T('check_soil.h1'), T('check_soil.h2')), demo ? demoLabel() : fieldChip(F),
          fog.any ? h('p', { class: 'fogline' }, T('fog.fog_line')) : null],
        scene: ph ? h('div', { class: 'photocard' }, box, pcap) : [box, F._drone ? droneCredit(F._drone) : null],
        body: [demo && !ph ? h('div', { class: 'card soft' }, h('p', { class: 'lead' }, T('drone.no_photo')), btn2(T('drone.take'), function () { go('photo'); }, 'camera')) : null, rows, fnote, info, tbox, honest],
        cta: ctaBox
      });
    });
  };

  // ---------------- 5 what to see (design: Choose, W5_Choose) ----------------
  // a field built with the global settings (abroad) has Gregorian months; Nepal's fields have Bikram Sambat months
  function chipKeys(n) { if (!abroad()) return blockKeys(n); var m = new Date().getMonth(), out = []; for (var i = 0; i < n; i++) out.push(MONTHS[(m + i) % 12]); return out; }
  function chipName(k) { return abroad() ? monthShort(k) : monthSpanEl(k); }
  // the keys of n Bikram Sambat months from the one holding today (a month starts on the 15th of the Gregorian month of its key)
  function blockKeys(n) { var now = new Date(), m = now.getMonth(), hold = now.getDate() >= 15 ? m : (m + 11) % 12, out = []; for (var i = 0; i < n; i++) out.push(MONTHS[(hold + i) % 12]); return out; }
  // a month name short enough for a chip: Bikram Sambat in Nepali, three letters in Latin scripts (the How we know charts)
  function monthShort(key) { if (S.lang === 'ne') return monthName(key, true); var n = monthName(key); return /^(en|es|fr|sw)$/.test(S.lang) ? n.slice(0, 3) : n; }
  var DOT_COL = { none: '#E3D6BF', now: '#E9C77A', good: '#7FB24A', care: '#9A5426', info: '#C9A86A' };
  // the months of a Choose card, one under the other (owner, 2026-11-14 night: the chips were cramped); past three rows the
  // list scrolls inside the card, and a fade with a bouncing arrow shows there is more below (phone and web)
  function monthList(keys) {
    var list = h('div', { class: 'mlist' }, keys.map(function (m) { return h('span', null, chipName(m)); }));
    var wrap = h('div', { class: 'mwrap', 'aria-hidden': 'true' }, list, h('span', { class: 'mhint' }, svg(ic(P_.arrow, 16, 2.6))));
    function upd() { wrap.classList.toggle('more', list.scrollHeight - list.scrollTop - list.clientHeight > 2); }
    list.addEventListener('scroll', upd, { passive: true });
    if (W.ResizeObserver) new ResizeObserver(upd).observe(list);
    if (W.MutationObserver) new MutationObserver(upd).observe(list, { childList: true });
    wrap.list = list; return wrap;
  }
  // B6 (owner, 2026-11-15): the small field picture on the "Your field today" card: every part at its true shape (geom: a
  // 2 x 2 field and a drawn one alike), grey until the soil stick has tested it, then its word's colour (as the swatches)
  function partsMini(F, pd) {
    var G = geom(F), tested = pd && forField(pd) ? pd.parts || {} : {}, s = D.createElementNS(SVGNS, 'svg');
    s.setAttribute('viewBox', '-1 -1 102 102'); s.setAttribute('preserveAspectRatio', 'none'); s.setAttribute('class', 'minif'); s.setAttribute('aria-hidden', 'true');
    s.style.aspectRatio = String(Math.max(0.8, Math.min(2.4, G.aspect || 1)));
    G.forEach(function (g) {
      var p = D.createElementNS(SVGNS, 'path'), r = tested[g.s.id], k = r ? partWord(r).k : 'none';
      p.setAttribute('d', 'M' + g.pts.map(function (q) { return q[0].toFixed(2) + ' ' + q[1].toFixed(2); }).join('L') + 'Z');
      p.setAttribute('style', 'fill:' + (k === 'none' ? '#D6D3CB' : DOT_COL[k]));
      s.append(p);
    });
    return s;
  }
  SCREENS.choose = function () {
    var title = h('h1', { class: 'big' }, h('span', null, T('check_soil.choose_h1')), h('span', { class: 'b' }, T('check_soil.choose_h2')));
    var swatches = h('div', { class: 'row', style: 'gap:6px', 'aria-hidden': 'true' });
    var m6 = monthList(chipKeys(6)), crops6 = m6.list, mini = h('div', { class: 'grow minibox' });
    fieldReady().then(function (F) {
      if (!F) return;
      mini.append(partsMini(F, null));   // B6: grey parts until the soil stick's readings arrive
      // the six month chips coloured by the suggestion's crops in the middle of each month (empty months stay plain)
      featData('simple').then(function (sd) {
        var x = sd && sd.plan_words && farmPlans(F, sd, 6, sd.start || 'medium').pick, seen = [];
        if (!x) return;
        crops6.textContent = '';
        blockKeys(6).forEach(function (k) {
          var c = cropOn(x.p, (CUM[MONTHS.indexOf(k)] + 29) % 365); if (c && seen.indexOf(c) < 0) seen.push(c);
          crops6.append(h('span', { style: c ? 'background:' + CROP_COL[seen.indexOf(c) % CROP_COL.length] + ';color:#14301E' : '' }, monthSpanEl(k)));
        });
      });
      probeData().then(function (pd) {
        if (!forField(pd)) return;
        mini.textContent = ''; mini.append(partsMini(F, pd));
        swatches.textContent = '';
        geom(F).forEach(function (g) { swatches.append(h('span', { class: 'sw4', style: 'background:' + DOT_COL[partWord(pd.parts[g.s.id]).k] })); });
        if (anyTested(pd)) { title.firstChild.textContent = T('check_soil.tested_h1'); title.lastChild.textContent = T('check_soil.tested_h2'); }
      });
    });
    var a = h('button', { type: 'button', class: 'bigcard light', onclick: function () { go('today'); } },
      h('div', { class: 'row', style: 'justify-content:space-between' }, h('span', { class: 'chip' }, svg(I('stick', 16)), T('check_soil.from_test')), swatches),
      mini,
      h('div', { class: 'row', style: 'align-items:flex-end;justify-content:space-between' },
        h('div', { style: 'display:flex;flex-direction:column;gap:6px' }, h('span', { class: 't' }, T('each_part.today_h1') + ' ' + T('each_part.today_h2')), h('span', { class: 's' }, T('home.card_today_sub'))),
        h('span', { class: 'go' }, svg(ic(P_.arrow, 22, 2.6), 'lime'))));
    a.querySelector('.go .ico').style.color = '#C8E05A';
    var orbit = svg('<svg width="230" height="230" viewBox="0 0 230 230"><circle cx="115" cy="115" r="110" fill="none" stroke="#FFF" stroke-opacity=".07" stroke-width="2"/><circle cx="115" cy="115" r="78" fill="none" stroke="#FFF" stroke-opacity=".07" stroke-width="2"/><circle cx="115" cy="115" r="46" fill="#C8E05A" fill-opacity=".08"/><g><circle cx="115" cy="37" r="6" fill="#C8E05A"/></g></svg>', 'orbit');
    function monthsCard(n, cls, extra, sub) {
      return h('button', { type: 'button', class: 'bigcard ' + cls, onclick: function () { go('next/' + n); } }, extra,
        h('div', { class: 'row', style: 'position:relative;justify-content:space-between;flex-wrap:wrap;gap:8px' },
          h('span', { class: 'chip' }, svg(I('sat', 16)), T('home.card_months_tag'))),
        n === 6 ? m6 : monthList(chipKeys(3)),
        h('div', { class: 'grow' }),
        h('div', { class: 'row', style: 'align-items:flex-end;justify-content:space-between;position:relative' },
          h('div', { style: 'display:flex;flex-direction:column;gap:6px' }, h('span', { class: 't' }, T('what_to_grow.next_h1') + ' ' + T(n === 6 ? 'what_to_grow.next_h2_6' : 'what_to_grow.next_h2')),
            h('span', { class: 's' }, T(sub))),
          h('span', { class: 'go' }, svg(ic(P_.arrow, 22, 2.6)))));
    }
    var path6 = svg('<svg width="200" height="120" viewBox="0 0 200 120"><path d="M10 110 Q 60 20 100 70 T 190 30" fill="none" stroke="#FBF4EA" stroke-width="2" stroke-dasharray="4 7"/></svg>', 'path6');
    var box = h('div', { class: 'choose' });
    var wc = weatherCard(function () { box.classList.add('four'); });
    add(box, [a, monthsCard(3, 'darkc', orbit, 'what_to_grow.three'), monthsCard(6, 'greenc', path6, 'what_to_grow.three'), wc]);
    if (!wc.hidden) box.classList.add('four');
    return screen('choose', {
      head: title,
      scene: box,
      body: null,
      cta: null
    });
  };

  // ---------------- 6 your field today, from the soil stick (design: Today, W6_Today) ----------------
  function dotEl(k) {
    var ico = k === 'good' ? I('tick', 18, 3) : k === 'care' ? I('warn', 18, 3) : k === 'none' ? I('info', 18, 2.4) : I('drop', 18, 2.4);
    return h('span', { class: 'dot ' + k }, svg(ico));
  }
  // one line per patch (owner, 2026-11-14 evening). Until the soil stick's cup test passes (simple.today.mode 'compare'),
  // a patch is only drier or wetter than the others (the bridge's `relative`); after it ('band'), dry, fine or too wet.
  var TODAY = { drier: ['farm.today_drier', 'farm.today_water_first', 'care'], wetter: ['farm.today_wetter', 'farm.today_water_last', 'info'],
    about_same: ['farm.today_same', null, 'good'], 'needs water': ['farm.today_dry', 'farm.today_water_today', 'care'],
    good: ['farm.today_fine', 'farm.today_no_water', 'good'], 'too wet': ['farm.today_too_wet', 'farm.today_dont_water', 'care'] };
  function patchLine(r, mode, n) {
    var w = partWord(r);
    if (!r || !r.state) return { k: 'none', text: T('farm.today_untested', { section: n }) };
    if (r.state !== 'done') return { k: w.k, text: w.word };   // settling, measuring or test again: the stick's own step
    var rel = r.relative ? ({ drier: 'drier', wetter: 'wetter' }[r.relative] || 'about_same') : null;   // the bridge writes "about the same"
    var x = TODAY[mode === 'band' && r.band ? r.band : rel];
    return x ? { k: x[2], text: T(x[0], { section: n }) + (x[1] ? ' ' + T(x[1]) : '') } : { k: w.k, text: w.word };
  }
  SCREENS.today = function () {
    return withField('today', function (F) {
      var G = geom(F), cards = h('div', { class: 'tcards lines1' }), more = h('div', { class: 'row wrap' }), mode = 'compare';
      var last = null, drawn = 0;
      function draw(pd) {
        if (!forField(pd)) pd = { kind: 'none', parts: {} };   // a garden or indoor test never shows as the field's parts
        var key = JSON.stringify(pd.parts) + S.lang + mode;
        if (key === last) return;   // the live file is read again every few seconds: redraw only when a reading changed
        last = key; cards.classList.toggle('still', drawn++ > 1);
        cards.textContent = ''; more.textContent = '';
        G.forEach(function (g, i) {
          var x = patchLine(pd.parts[g.s.id], mode, g.n);
          cards.append(h('div', { class: 'tcard ' + x.k, style: 'animation-delay:' + (i * 110 + 100) + 'ms' }, dotEl(x.k), h('span', { class: 'word' }, x.text)));
        });
        if (!anyTested(pd)) more.append(btn2(T('parts.start_test'), function () { go('soil'); }, 'stick'));
        else add(more, [h('span', { class: 'chip' }, svg(I('stick', 16)), T('check_soil.from_test')), recordedLine(pd)]);
      }
      draw({ kind: 'none', parts: {} });
      Promise.all([probeData(), featData('simple')]).then(function (r) {
        var pd = r[0]; mode = (r[1] && r[1].today && r[1].today.mode) || 'compare';
        if (cards.isConnected) draw(pd);
        if (pd.kind === 'live') every(function () { probeData().then(function (x) { if (cards.isConnected) draw(x); }); }, 4000);
      });
      return screen('today', {
        head: [bigTitle(T('each_part.today_h1'), T('each_part.today_h2')), fieldChip(F)],
        scene: [cards, more],
        body: null,
        cta: cta(T('what_to_grow.see3'), function () { go('next/3'); })
      });
    });
  };

  // ---------------- 7 next 3 and 6 months: our three plans, in plain actions (design: Future, Future6, W7, W8) ----------------
  // (owner, 2026-11-14 evening) The back end picks every sentence: site/data/simple/<id>.json actions (sow, harvest, then
  // plant; Bikram Sambat months) and plan_words (one word per plan against the farmer's own plan, by their winter answer,
  // the window m3 or m6 and the soil at the start). No number, year or count on these screens.
  // the farmer's winter crop (their answer to the guess on the Photo screen), the key of plan_words and weather_lines
  function winterCrop(F, sd) {
    var list = (sd && sd.answers && sd.answers.winter) || [], opt = curOption(F);
    var c = opt && list.filter(function (x) { return opt.crops.some(function (y) { return y.crop === x; }); })[0];
    return c || (sd && sd.answers && sd.answers.default_winter) || null;
  }
  // the soil at the start: the soil stick's band once its cup test passed (the most common band of the tested patches), else the file's
  var START_OF = { 'needs water': 'dry', good: 'medium', 'too wet': 'wet' };
  function startState(pd, sd) {
    var n = {}, best = null;
    if (sd.today && sd.today.mode === 'band' && forField(pd)) Object.keys(pd.parts).forEach(function (k) { var b = START_OF[pd.parts[k].band]; if (b) n[b] = (n[b] || 0) + 1; });
    Object.keys(n).forEach(function (k) { if (!best || n[k] > n[best]) best = k; });
    return best || sd.start || 'medium';
  }
  var VERDICT_ORDER = { better: 0, mixed: 1, same: 2, worse: 3 };
  // the plans to show, the suggestion first (the best word; ties keep the file's order), the farmer's own plan last
  function farmPlans(F, sd, n, start) {
    var win = n === 6 ? 'm6' : 'm3', pw = (((sd.plan_words || {})[winterCrop(F, sd)] || {})[win] || {})[start] || {}, opt = curOption(F);
    var own = null, rest = [];
    Object.keys(pw).forEach(function (id, i) {
      var e = pw[id], p = F.plans.filter(function (x) { return x.id === id; })[0]; if (!p) return;
      if (e.now) { var aid = opt ? opt.id : id; own = { id: id, own: true, p: opt ? { id: 'current', crops: opt.crops } : p, acts: ((sd.actions || {})[aid] || {})[win] || [] }; return; }
      rest.push({ id: id, p: p, word: e.text, v: VERDICT_ORDER[e.verdict] == null ? 9 : VERDICT_ORDER[e.verdict], i: i, acts: ((sd.actions || {})[id] || {})[win] || [] });
    });
    rest.sort(function (a, b) { return a.v - b.v || a.i - b.i; });
    return { pick: rest[0] || own, others: rest.slice(1), own: own };
  }
  // a plan's title: the crop it adds to what the farmer grows; the plan's name (or its crops, for a plan named "what you do now" that is not)
  function addedCrop(x, own) {
    var mine = own ? own.p.crops.map(function (c) { return c.crop; }) : [];
    var c = x.p.crops.filter(function (c) { return mine.indexOf(c.crop) < 0; })[0];
    return (c || x.p.crops[x.p.crops.length - 1]).crop;
  }
  function farmPlanName(x) { return x.own || x.id !== 'current' ? planName(x.own ? { id: 'current' } : x.p) : cropsLine(x.p); }
  function tryBtn(id, dark) {
    return h('button', { type: 'button', class: 'trybtn' + (dark ? ' dark' : ''), onclick: function (e) { e.stopPropagation(); go('trial/' + id); } }, svg(I('quarter', 18)), T('what_to_grow.try_part'));
  }
  function ticks(list) { return h('ul', { class: 'ticks' }, list.filter(Boolean).map(function (t) { return h('li', null, svg(I('tick', 16, 2.6)), h('span', null, t)); })); }
  function wordLine(x) { return x.word ? h('p', { class: 'pword' }, svg(I(x.v === 0 ? 'up' : x.v === 3 ? 'down' : 'eq', 18, 2.6)), T(x.word)) : null; }
  function bestCard(x, own, brief) {
    return h('div', { class: 'best' }, h('span', { class: 'tag' }, T('what_to_grow.our_pick')),
      h('span', { class: 'bc' }, cap(crop(addedCrop(x, own)))), h('span', { class: 'bp' }, farmPlanName(x)),
      wordLine(x), brief ? null : ticks(x.acts.map(say)), x.own ? null : tryBtn(x.id));
  }
  // Next 3 months (B5): one row per month, what to do (the plan's own sentence, else growing or resting) and the month's
  // watch-out from Weather ahead for the crop of that row, when the file has one for that crop
  function monthRows(steps, wlOf) {
    return h('div', { class: 'card mrows' }, steps.map(function (st) {
      var wl = st.crop && wlOf(st.crop), w = wl && wl[st.key], what = st.acts.length ? st.acts.map(say).join(' ') : st.kind === 'grow' ? T('farm.m_grows', { crop: cap(crop(st.crop)) }) : T('farm.m_rest');
      return h('div', { class: 'mrow' + (bothMonths() ? ' both' : '') }, h('span', { class: 'mm' }, monthSpanEl(st.key)),
        h('div', { class: 'mw' }, h('p', null, what), w && w.tip ? h('p', { class: 'mwatch' }, svg(I('warn', 16, 2.6)), ' ', h('b', null, T('weather.watch')), ' ', say(w.danger)) : null));
    }));
  }
  // Next 6 months (B5): the six months side by side, from sowing to harvest and what follows
  var STEP_IC = { sow: 'soil', plant: 'sprout', harvest: 'hand', grow: 'sprout', rest: 'leaf', do: 'info' };
  function sixRow(steps) {
    return h('div', { class: 'card msix' }, h('p', { class: 'wh' }, T('farm.m_row')), h('div', { class: 'mstrip' }, steps.map(function (st) {
      return h('div', { class: 'mcell k-' + st.kind }, h('span', { class: 'mm' }, bsMonth(st.key)), svg(I(STEP_IC[st.kind], 20)),
        h('span', { class: 'mk' }, T('farm.k_' + (st.kind === 'do' ? 'grow' : st.kind))), st.crop ? h('span', { class: 'mc' }, cap(crop(st.crop))) : null);
    })));
  }
  function pickLine(x, own) {
    return h('div', { class: 'card pickline' }, h('span', { class: 'tag' }, T('what_to_grow.our_pick')),
      h('p', null, h('b', null, cap(crop(addedCrop(x, own)))), ' · ' + farmPlanName(x)), wordLine(x));
  }
  function wxLines(F, sd, c) { var wl = sd && sd.weather_lines && sd.weather_lines[c || winterCrop(F, sd)]; return wl && wl[canWater(F) ? 'yes' : 'no']; }
  // B1 (owner, 2026-11-15): the other choices folded into one closed row ("2 other choices"), opened by a tap
  function othersCard(list) {
    if (!list.length) return null;
    return h('details', { class: 'olistbox ofold' }, h('summary', { class: 'oh' }, T(list.length === 1 ? 'farm.others_1' : 'farm.others_n', { count: list.length })),
      h('div', { class: 'card olist' }, list.map(function (x) {
        return h('div', { class: 'orow' }, h('span', { class: 'on' }, x.own ? planName({ id: 'current' }) : cap(crop(addedCrop(x, list[list.length - 1].own ? list[list.length - 1] : null))) + ' · ' + farmPlanName(x)),
          wordLine(x), h('ul', { class: 'lines os' }, x.acts.map(function (a) { return h('li', null, say(a)); })), x.own ? null : tryBtn(x.id, true));
      })));
  }
  // the closing note, one line (B1, B3): a first sentence if any, then "You know your land best. Talk to a farm advisor ..."
  function noteBox(first) { return h('p', { class: 'note' }, first ? [first, ' '] : null, T('your_plan.know_best'), ' ', T('your_plan.advisor')); }
  function monthsNote() { return inNepal() ? T('what_to_grow.months_note') : null; }
  function ctaTo(label, icon, route) {
    return h('button', { type: 'button', class: 'cta', onclick: function () { go(route); } }, svg(I(icon, 22, 2.6), 'lime'), h('span', null, label));
  }
  function doneCta() { return ctaTo(T('where.done'), 'tick', 'home'); }
  SCREENS.next = function (arg) {
    var n = arg === '6' ? 6 : arg === '3' ? 3 : (S.nextN || 3);
    S.nextN = n;
    return withField('next', function (F) {
      var scene = h('div', { class: 'col', style: 'display:flex;flex-direction:column;gap:14px' }, loading()), body = h('div', { class: 'col', style: 'display:flex;flex-direction:column;gap:14px' });
      Promise.all([featData('simple'), probeData()]).then(function (r) {
        var sd = r[0]; scene.textContent = '';
        if (!sd || !sd.plan_words) { scene.append(notReady()); return; }
        var s = farmPlans(F, sd, n, startState(r[1], sd));
        if (!s.pick) { scene.append(notReady()); return; }
        var years = (effPlans(F)[0].replay || []).length, tags = nasaTags([['rain', years], ['weather', years]]);
        var steps = monthSteps(s.pick.p, s.pick.acts, blockKeys(n)), wl = F.weather && F.weather.blocks && wxLines(F, sd);
        if (n === 6) {   // B2: one line naming the suggestion, then each of the six months as on Weather ahead (else the plan's steps)
          scene.append(pickLine(s.pick, s.own)); scene.lastChild.append(tags);
          add(body, [wl ? h('div', { class: 'wblocks' }, sixBlocks(F.weather).map(function (b, i) { return wxCard(wl[b.key] || {}, b, monthSpan(b.key), i); })) : sixRow(steps),
            noteBox(monthsNote())]);
          return;
        }
        // B1: the suggestion (its NASA tags once), one row for each of the next three months, the other choices folded
        scene.append(bestCard(s.pick, s.own, true)); scene.lastChild.append(tags);
        add(body, [monthRows(steps, function (c) { return wxLines(F, sd, c); }), othersCard(s.others.concat(s.own && s.pick !== s.own ? [s.own] : [])),
          noteBox(monthsNote())]);
      });
      return screen('next', {
        head: [bigTitle(T('what_to_grow.next_h1'), T(n === 6 ? 'what_to_grow.next_h2_6' : 'what_to_grow.next_h2')), fieldChip(F)],
        scene: scene,
        body: body,
        // B1: no "Done" here, the main button opens the six months; B2: back to the start, or on to Weather ahead
        cta: n === 6 ? h('div', { class: 'ctapair' }, ctaTo(T('farm.back_start'), 'back', 'home'), btn2(T('weather.title'), function () { go('weather'); }, 'sun')) :
          ctaTo(T('farm.see6'), 'arrow', 'next/6')
      });
    });
  };
  SCREENS.next.onArg = function (a) { if (a === S.arg) return; S.arg = a; rerender(); W.scrollTo(0, 0); };

  // ---------------- Weather ahead: what usually happens this month and the five after, never a forecast ----------------
  // (owner, 2026-11-14 evening) The back end picks every sentence (site/data/simple/<id>.json weather_lines, by the farmer's
  // winter crop and water answer); this page only shows them. The details (years, rain, temperatures, sources) are on How
  // we know. fields/<id>.json weather: twelve blocks, each an approximate Bikram Sambat month from the 15th of the
  // Gregorian month named by its key ('Nov' = Mangsir, 15 Nov to 14 Dec).
  function sixBlocks(wx) { return blockKeys(6).map(function (k) { return (wx.blocks || []).filter(function (x) { return x.key === k; })[0]; }).filter(Boolean); }
  // a Bikram Sambat month by its block key, in both languages (words.json shared.bs_months: 'Oct' = Kartik)
  // a field outside Nepal: Gregorian months (rules.yaml global_use.months_language); Nepal's fields keep Bikram Sambat
  function bsMonth(key) { if (!inNepal()) return S.lang === 'ne' ? gregInNepali(key) : monthName(key); var n = S.words && S.words.shared.bs_months && S.words.shared.bs_months[key]; return n ? L(n) : monthName(key, true); }
  // B4 (owner, 2026-11-15): each Bikram Sambat month's approximate Gregorian span, by block key: from about the 15th of the
  // Gregorian month its key names to about the 14th of the next ('Nov' = Mangsir = mid-Nov to mid-Dec), as the weather blocks
  var BS_SPAN = { Jan: ['Jan', 'Feb'], Feb: ['Feb', 'Mar'], Mar: ['Mar', 'Apr'], Apr: ['Apr', 'May'], May: ['May', 'Jun'], Jun: ['Jun', 'Jul'],
    Jul: ['Jul', 'Aug'], Aug: ['Aug', 'Sep'], Sep: ['Sep', 'Oct'], Oct: ['Oct', 'Nov'], Nov: ['Nov', 'Dec'], Dec: ['Dec', 'Jan'] };
  // the months from block key `from` to `to`: [the approximate dates, the Bikram Sambat names] (w: the words to use)
  function spanText(from, to, w) {
    var dates = w.span.replace('{month_from}', w.mon[BS_SPAN[from][0]]).replace('{month_to}', w.mon[BS_SPAN[to][1]]);
    return [dates, from === to ? w.bs[from] : w.range.replace('{month_from}', w.bs[from]).replace('{month_to}', w.bs[to])];
  }
  // month numbers (0-11, in order) as runs of months next to each other, [first, last]; December runs on into January
  function monthRuns(ms) {
    var out = [];
    ms.forEach(function (m) { var r = out[out.length - 1]; if (r && (r[1] + 1) % 12 === m) r[1] = m; else out.push([m, m]); });
    if (out.length > 1 && (out[out.length - 1][1] + 1) % 12 === out[0][0]) out[0][0] = out.pop()[0];
    return out;
  }
  // B4: Nepali shows Bikram Sambat months only and a field outside Nepal Gregorian only; English (and the drafts) on a Nepal
  // field the approximate dates first, the Bikram Sambat months in brackets: "Mid-Nov to mid-Feb (Mangsir to Magh)"
  function bothMonths() { return inNepal() && S.lang !== 'ne'; }
  function spanWords() {
    var mon = {}, bs = {};
    MONTHS.forEach(function (k) { mon[k] = monthShort(k); bs[k] = bsMonth(k); });
    return { mon: mon, bs: bs, span: T('farm.mid_span'), range: T('farm.wx_range') };
  }
  function monthSpan(from, to) {
    to = to || from;
    if (!bothMonths()) return from === to ? bsMonth(from) : T('farm.wx_range', { month_from: bsMonth(from), month_to: bsMonth(to) });
    var p = spanText(from, to, spanWords()); return p[0] + ' (' + p[1] + ')';
  }
  // the same as page text: the dates, then the Bikram Sambat months small, in brackets
  function monthSpanEl(from, to) {
    if (!bothMonths()) return monthSpan(from, to);
    var p = spanText(from, to || from, spanWords()); return h('span', { class: 'mspan' }, cap(p[0]), ' ', h('small', null, '(' + p[1] + ')'));
  }
  // a sentence the back end picked: {text: words key, fill: {placeholder: value}}. Month values are block keys (monthSpan),
  // crop values crop ids, a crop list is joined with "then", rain and heat words are ids.
  function say(o, over) {
    if (!o || !o.text) return '';
    var v = {};
    Object.keys(o.fill || {}).forEach(function (k) {
      var x = o.fill[k];
      v[k] = k === 'guess_list' ? x.map(crop).join(', ' + T('join.then') + ' ') : k === 'rain_word' ? T('weather.rain_' + x) : k === 'temp_word' ? T('weather.temp_' + x) :
        /month/.test(k) ? monthSpan(x) : /crop/.test(k) ? crop(x) : x;
    });
    Object.keys(over || {}).forEach(function (k) { v[k] = over[k]; });   // e.g. a joined card's "Mangsir to Magh" (B7)
    return cap(T(o.text, v));   // a sentence may now start with "mid-Nov"
  }
  // B7 (owner, 2026-11-15): months next to each other that say the same thing (weather, danger and tip; only the month
  // differs) share one card, "Mangsir to Magh"
  function sameWx(a, b) {
    function sig(x) { var u = x.usual || {}, f = u.fill || {}; return JSON.stringify([u.text, Object.keys(f).filter(function (k) { return k !== 'month'; }).sort().map(function (k) { return f[k]; }), x.danger || null, x.tip || null]); }
    return !!(a && b) && sig(a) === sig(b);
  }
  function joinBlocks(keys, wl) {
    var out = [];
    keys.forEach(function (k) { var last = out[out.length - 1]; if (last && sameWx(wl[last.keys[last.keys.length - 1]], wl[k])) last.keys.push(k); else out.push({ keys: [k], x: wl[k] || {} }); });
    return out;
  }
  // "they can water": the field's own water source, else the farmer's answer in a plan's sheet
  function canWater(F) { var ws = F.field.water_source; if (ws && ws !== 'unknown') return ws !== 'rain-only'; return /^(canal|well|other)$/.test(S.water || ''); }
  var RAIN_IC = { dry: 'sun', some_rain: 'cloud', wet: 'rain' };
  function blockIcon(u) { return u.frost !== 'none' ? 'snow' : RAIN_IC[u.rain] || 'cloud'; }
  // one Weather ahead card (B7; Next 6 months too, B2): the month's picture, then at most three short lines: "[Months]: usually
  // [weather]." / "Watch out: [danger]" or "Usually no big danger." / "Do this: [its tip]" or "Keep your usual care."
  function wxCard(x, b, months, i, tags) {
    var icon = blockIcon(b.usual);
    return h('div', { class: 'card wblock', style: 'animation-delay:' + (120 + i * 70) + 'ms' },
      h('span', { class: 'wbi', style: icon === 'sun' ? 'color:#D27A2C' : '' }, svg(I(icon, 40))),
      h('div', { class: 'wpara' }, h('p', null, h('b', null, say(x.usual, { month: months }))),
        h('p', null, x.tip ? [h('b', null, T('weather.watch')), ' ', say(x.danger)] : say(x.danger)),
        h('p', null, h('b', null, T('weather.do')), ' ', x.tip ? say(x.tip) : T('farm.wx_usual_care')), tags || null));
  }
  // W (owner, 2026-11-15): two or three of a month block's own words, "Dry, cold" or, on frosty months, "Cold, frost possible"
  function wxWords(u) { return cap(u.frost !== 'none' ? T('weather.temp_' + u.temp) + ', ' + T('weather.frost_' + u.frost) : T('weather.rain_' + u.rain) + ', ' + T('weather.temp_' + u.temp)); }
  // the Choose screen's extra card (shown only when the field file has the weather block: Nepal fields), in the Weather
  // screen's sky colours (W): the next three months, one row each with its picture and words; a tap opens Weather ahead
  function weatherCard(onShow) {
    var rows = h('div', { class: 'wrows' });
    var deco = svg('<svg width="170" height="130" viewBox="0 0 170 130"><circle cx="112" cy="46" r="26" fill="#F0AE4C" fill-opacity=".55"/><path class="wcloud" d="M58 98a22 22 0 010-44 28 28 0 0153.8 6.7A19 19 0 01112 98z" fill="#FFFFFF" fill-opacity=".6"/></svg>', 'wdeco');
    var c = h('button', { type: 'button', class: 'bigcard skyc', hidden: true, onclick: function () { go('weather'); } }, deco,
      h('div', { class: 'row', style: 'position:relative;justify-content:space-between' }, h('span', { class: 'chip' }, svg(I('sat', 16)), T('home.card_months_tag'))),
      rows, h('div', { class: 'grow' }),
      h('div', { class: 'row', style: 'align-items:flex-end;justify-content:space-between;position:relative' },
        h('div', { style: 'display:flex;flex-direction:column;gap:6px' }, h('span', { class: 't' }, T('weather.title')), h('span', { class: 's' }, T('weather.choice_sub'))),
        h('span', { class: 'go' }, svg(ic(P_.arrow, 22, 2.6)))));
    function put(F) {
      var wx = F && F.weather; if (!wx || !wx.blocks) return;
      sixBlocks(wx).slice(0, 3).forEach(function (b) {
        var icon = blockIcon(b.usual);
        rows.append(h('span', { class: 'wrow' }, svg(I(icon, 20)), h('span', { class: 'wrt' }, h('b', null, monthSpanEl(b.key)), h('span', null, wxWords(b.usual)))));
      });
      c.hidden = false; if (onShow) onShow();
    }
    if (S.field) put(S.field); else fieldReady().then(put);
    return c;
  }
  SCREENS.weather = function () {
    return withField('weather', function (F) {
      var wx = F.weather, head = [bigTitle(T('weather.title')), fieldChip(F)];
      if (!wx || !wx.blocks) return screen('weather', { head: head, body: notReady(), cta: doneCta() });
      var list = h('div', { class: 'wblocks' }, loading());
      featData('simple').then(function (sd) {
        var wl = sd && sd.weather_lines && sd.weather_lines[winterCrop(F, sd)];
        wl = wl && wl[canWater(F) ? 'yes' : 'no'];
        list.textContent = '';
        if (!wl) { list.append(notReady()); return; }
        // B7 (owner, 2026-11-15): months next to each other that say the same thing share one card ("Mangsir to Magh"); at
        // most three short lines: "[Months]: usually [weather]." / "Watch out: [danger]" or "Usually no big danger." / "Do
        // this: [its tip]" or "Keep your usual care."; "Check with your local expert" once, below the cards
        var blocks = sixBlocks(wx), byKey = {};
        blocks.forEach(function (b) { byKey[b.key] = b; });
        joinBlocks(blocks.map(function (b) { return b.key; }), wl).forEach(function (g, i) {
          list.append(wxCard(g.x, byKey[g.keys[0]], monthSpan(g.keys[0], g.keys[g.keys.length - 1]), i, nasaTags([['weather', wx.years]])));
        });
      });
      return screen('weather', {
        head: head,
        scene: h('p', { class: 'srcline' }, svg(I('sat', 16)), T('weather.choice_sub') + ' ' + T('weather.not_forecast')),
        // B3 (owner, 2026-11-15): "Check with your local expert." and the closing note in one line
        body: [list, noteBox(T('weather.tip_end'))],
        cta: doneCta()
      });
    });
  };

  // ---------------- for How we know: the details behind each weather block (js/how.js) ----------------
  // one line per danger and crop: the file lists each sowing day apart, ranked most years first, so the first one stays
  function uniqDangers(list) { var seen = {}; return list.filter(function (d) { var k = d.check + '|' + d.crop; if (seen[k]) return false; seen[k] = 1; return true; }); }
  function dangerText(d) { return T('weather.' + d.check, { crop: crop(d.crop) }); }
  function dayMonth(mmdd) { var k = MONTHS[+mmdd.slice(0, 2) - 1]; return digits(+mmdd.slice(3, 5)) + ' ' + (S.lang === 'ne' ? gregInNepali(k) : monthName(k)); }
  // the rain in a block: lowest year, highest year, and the usual year (a range over the rain versions, as everywhere)
  function rainBar(r) {
    var mm = T('your_plan.mm'), vs = [r.median].concat(Object.keys(r.versions || {}).map(function (k) { return r.versions[k]; })),
      a = Math.min.apply(null, vs), b = Math.max.apply(null, vs), span = (r.high - r.low) || 1;
    function pc(v) { return Math.max(0, Math.min(100, (v - r.low) / span * 100)); }
    return h('div', { class: 'rbar' },
      h('p', { style: 'margin:0' }, h('b', null, cap(T('weather.usual_year')) + ': '), rng(a, b) + ' ' + mm),
      h('div', { class: 'rtrack', 'aria-hidden': 'true' }, h('span', { class: 'rmid', style: 'left:' + pc(a).toFixed(1) + '%;width:' + Math.max(3, pc(b) - pc(a)).toFixed(1) + '%' })),
      h('div', { class: 'rends' }, h('span', null, num(r.low) + ' ' + mm), h('span', null, num(r.high) + ' ' + mm)));
  }
  function weatherWhy(F, b) {
    var wx = F.weather, u = b.usual, ds = uniqDangers((b.dangers || []).filter(function (d) { return d.years > 0; }));
    var none = uniqDangers((b.none_seen || []).filter(function (n) { return !ds.some(function (d) { return d.check === n.check && d.crop === n.crop; }); }));
    var kinds = ds.map(function (d) { return d.kind; });
    function row(icon, kids) { return h('div', { class: 'wd' }, h('p', { style: 'margin:0;font-weight:700' }, svg(I(icon, 16)), ' ', kids[0]), kids.slice(1)); }
    return h('div', { class: 'col', style: 'display:flex;flex-direction:column;gap:6px' },
      h('p', { class: 'small', style: 'margin:0' }, dayMonth(b.from) + ' – ' + dayMonth(b.to) + ' · ' + T('weather.not_forecast')),
      ds.map(function (d) {
        var rainy = d.kind === 'dry_spell' || d.kind === 'big_rain';
        return row('warn', [dangerText(d), h('p', { class: 'small', style: 'margin:0' }, T('weather.years', { danger_years: d.years, year_count: d.of }) + ' ',
          h('b', null, T('weather.changing')), ' ', T('weather.change_' + d.change), rainy ? [' ', rainMark()] : null)]);
      }),
      ds.length ? null : row('tick', [T('weather.nothing')]),
      none.map(function (n) { return h('p', { class: 'small', style: 'margin:0' }, dangerText(n) + ' ' + T('weather.none_seen')); }),
      kinds.indexOf('big_rain') >= 0 ? h('p', { class: 'small', style: 'margin:0' }, T('weather.big_rain_note1') + ' ' + T('weather.big_rain_note2')) : null,
      row('rain', [T('weather.rain_label'), rainBar(u.rain_mm)]),
      row('therm', [T('weather.day_label') + ': ' + num(u.tmax_c) + ' °C · ' + T('weather.night_label') + ': ' + num(u.tmin_c) + ' °C']),
      row('sun', [T('weather.dry_label'), h('p', { style: 'margin:0' }, cap(T('weather.usual_year')) + ': ' + num(b.dry_run.typical) + ' ' + T('weather.days_word') + ' · ' +
        cap(T('weather.worst_years')) + ': ' + (b.dry_run.worst || []).map(function (x) { return digits(x.year) + ': ' + num(x.days); }).join(', ')),
        h('p', { class: 'small', style: 'margin:0' }, T('weather.dry_note'))]),
      row('snow', [T('weather.frost_label') + ': ' + T('weather.frost_' + u.frost), kinds.indexOf('cold') >= 0 || u.frost !== 'none' ?
        h('p', { class: 'small', style: 'margin:0' }, T('weather.frost_note1') + ' ' + T('weather.frost_note2')) : null]),
      h('div', { class: 'row wrap', style: 'gap:6px' }, labs(null, wx.label), rainMark()));
  }

  // ---------------- "Try it in one part first": the Safe Trial in the plan's sheet (js/features.js) ----------------
  function loadScript(src) { return new Promise(function (res) { var s = h('script', { src: src }); s.onload = res; s.onerror = res; D.head.append(s); }); }
  function features() { S.featP = S.featP || loadScript('js/features.js'); return S.featP; }
  function openTrial(id) {
    Promise.all([fieldReady(), features()]).then(function (r) {
      var F = r[0]; if (!F || !W.KS.feat) return;
      function build() {
        var p = F.plans.filter(function (x) { return x.id === id; })[0];   // the plan as the file has it (a suggestion, never the farmer's own)
        if (!p) { closeSheet(); return; }
        var panel = openSheet(build);
        add(panel, [sheetBar(T('what_to_grow.try_part')), W.KS.feat.trial(F, p)]);
        panel.focus();
      }
      build();
    });
  }

  // the plans' days: crop seasons from each plan's crops (start and end, MM-DD), in a 365-day year
  var CUM = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334], MDAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  function doy(mmdd) { return CUM[+mmdd.slice(0, 2) - 1] + (+mmdd.slice(3, 5)) - 1; }
  function covers(c, d) { var a = doy(c.start), b = doy(c.end); return a <= b ? d >= a && d <= b : d >= a || d <= b; }
  function cropOn(p, d) { for (var i = 0; i < p.crops.length; i++) if (covers(p.crops[i], d)) return p.crops[i].crop; return null; }
  // what happens on a plan in each month block (B5, owner 2026-11-15): its own actions in that month (simple/<id>.json
  // actions: sow, harvest, then plant), else the crop growing in the middle of the month, else the field rests
  function actMonth(a) { var f = a.fill || {}; return f.sow_month || f.harvest_month || f.month || null; }
  function actKind(a) { return /harvest/.test(a.text) ? 'harvest' : /plant/.test(a.text) ? 'plant' : /sow/.test(a.text) ? 'sow' : 'do'; }
  function monthSteps(p, acts, keys) {
    return keys.map(function (k) {
      var here = acts.filter(function (a) { return actMonth(a) === k; }), grow = cropOn(p, (CUM[MONTHS.indexOf(k)] + 29) % 365);
      var f = here[0] ? here[0].fill || {} : {};
      return { key: k, acts: here, kind: here[0] ? actKind(here[0]) : grow ? 'grow' : 'rest', crop: here[0] ? f.crop || f.new_crop || grow : grow };
    });
  }
  function cap(s) { return /^(ne|hi|bn)$/.test(S.lang) ? s : s.charAt(0).toUpperCase() + s.slice(1); }
  var CROP_COL = ['#C8E05A', '#F0AE4C', '#9CC8E3', '#E6B8DA'];

  // ---------------- the detail view of one plan (five tabs, tips, both water cases) ----------------
  function openSheet(build) {
    var sh = $('#sheet');
    S.sheetFor = build;
    sh.hidden = false; D.body.style.overflow = 'hidden';
    sh.textContent = '';
    var panel = h('div', { class: 'panel', role: 'dialog', 'aria-modal': 'true', tabindex: '-1' });
    sh.append(panel);
    sh.onclick = function (e) { if (e.target === sh) closeSheetNav(); };
    return panel;
  }
  function closeSheet() { var sh = $('#sheet'); sh.hidden = true; sh.textContent = ''; S.sheetFor = null; D.body.style.overflow = ''; }
  function closeSheetNav() { if (/^#\/(plan|trial)\//.test(location.hash)) { if (S.cur) go(S.cur + (S.cur === 'next' && S.arg ? '/' + S.arg : '')); else go('next'); } else closeSheet(); }
  D.addEventListener('keydown', function (e) { if (e.key === 'Escape' && S.sheetFor) closeSheetNav(); });
  function sheetBar(title) {
    return h('div', { class: 'bar' }, h('button', { type: 'button', class: 'round', 'aria-label': T('btn.close'), onclick: closeSheetNav }, svg(I('back', 22, 2.4))),
      h('h2', { class: 'h2 grow' }, title));
  }
  function openPlan(id) {
    fieldReady().then(function (F) {
      if (!F) return;
      var tab = 'why';
      function build(keep) {
        var ps = effPlans(F), p = ps.filter(function (x) { return x.id === id; })[0], cur = ps.filter(function (x) { return x.id === 'current'; })[0];
        if (!p) { closeSheet(); return; }
        var panel = openSheet(build);
        var tabs = (S.lang === 'ne' ? p.tabs_ne : p.tabs) || p.tabs || {}, tips = (S.lang === 'ne' ? p.tips_ne : p.tips) || p.tips || [];
        var tabBox = h('div', { class: 'tabtext card', 'aria-live': 'polite' });
        var tabBtns = h('div', { class: 'tabs', role: 'tablist' });
        function showTab(k) {
          tab = k;
          [].forEach.call(tabBtns.children, function (b) { b.setAttribute('aria-selected', String(b.dataset.k === k)); });
          tabBox.textContent = ''; sentences(tabs[k]).forEach(function (s) { tabBox.append(h('p', null, s)); });
        }
        ['why', 'evidence', 'benefits', 'unknown', 'check'].forEach(function (k) {
          tabBtns.append(h('button', { type: 'button', role: 'tab', 'data-k': k, onclick: function () { showTab(k); } }, T('lbl.what_to_grow.tab.' + k)));
        });
        showTab(tab);
        function scoreRow(k, kind) {
          var r = scoreRange(p, k);
          return h('div', { class: 'score' }, h('span', { class: 'lbl' }, T('lbl.what_to_grow.score.' + k)), kind ? pics(p.score[k], kind, kind === 'drop' ? 18 : 16) : null,
            h('span', { class: 'num', style: 'font-size:22px' }, rng(r[0], r[1]), ' ', h('small', null, T('btn.out_of_100'))),
            k === 'harvest' && p.id !== 'current' ? vsChip(vsNow(p, cur, k)) : null);
        }
        // both water cases, while the field's water is unknown
        var cases = waterCases(F), rep = p.replay || [];
        var irr = rep.length ? rep.reduce(function (s, y) { return s + y.irrigated.harvest; }, 0) / rep.length : null;
        var hr = scoreRange(p, 'harvest');
        var waterQ = null;
        if (!F.field.water_source || F.field.water_source === 'unknown') {
          var wq = h('div', { class: 'row wrap', role: 'group', 'aria-label': T('where.q_water') }, ['rain_only', 'canal', 'well', 'other', 'unknown'].map(function (k) {
            return h('button', { type: 'button', class: 'choice', 'aria-pressed': String((S.water || 'unknown') === k), onclick: function () { S.water = k; store.set('water', k); build(true); } },
              T('lbl.where.water.' + k));
          }));
          waterQ = [h('p', { class: 'lead' }, T('where.q_water')), wq, cases.length > 1 ? h('p', { class: 'small', style: 'margin:0' }, T('last_years.water_unknown'), ' ', T('last_years.both_shown')) : null];
        }
        var caseRows = h('div', { class: 'row wrap', style: 'gap:10px;align-items:stretch' }, cases.map(function (c) {
          var val = c === 'rain_fed' ? rng(hr[0], hr[1]) : (irr == null ? null : num(irr));
          return h('div', { class: 'card', style: 'flex:1 1 180px;border:1.5px solid var(--line)' },
            h('p', { class: 'small', style: 'margin:0 0 4px;font-weight:700;color:var(--ink)' }, svg(I(c === 'rain_fed' ? 'rain' : 'drop', 16)), ' ', T('lbl.last_years.water_case.' + c)),
            val == null ? h('span', null, T('btn.not_ready')) : h('span', { class: 'num' }, val, ' ', h('small', null, T('btn.out_of_100'))),
            c === 'irrigated' ? h('p', { class: 'small', style: 'margin:4px 0 0' }, T('what_to_grow.water_never_out')) : null);
        }));
        var cropRows = h('ul', { class: 'tips' }, p.crops.map(function (c) {
          return h('li', null, h('span', { class: 'k' }, svg(I('sprout', 16))), h('span', null,
            T('your_plan.plant_in', { crop: crop(c.crop), sow_month: monthName(MONTHS[+c.start.slice(0, 2) - 1]) }), h('br'),
            h('span', { class: 'small' }, T('your_plan.harvest_in', { crop: crop(c.crop), harvest_month: monthName(MONTHS[+c.end.slice(0, 2) - 1]) }))));
        }));
        var ex = (S.words.crop_explainers ? Object.keys(S.words.crop_explainers) : []).map(function (k) { return S.words.crop_explainers[k]; })
          .filter(function (e) { return (e.examples || []).some(function (c) { return p.crops.some(function (x) { return x.crop === c; }); }); });
        var li = langInfo(S.lang);
        var explain = ex.length ? h('details', null, h('summary', null, T('what_to_grow.learn_more')), ex.map(function (e) {
          return h('div', { style: 'padding:6px 0 10px' }, h('h3', { class: 'h3' }, L(e.title)), e.claims.map(function (c) {
            var s = c.source || {};
            return h('div', null, h('p', { style: 'margin:6px 0 2px' }, L(c)),
              h('p', { class: 'quote', lang: 'en' }, (li && li.quote_label ? (li.quote_label[S.lang] || li.quote_label.en) + ': ' : '') + '“' + (s.quote || '') + '” ',
                s.url ? h('a', { href: s.url, target: '_blank', rel: 'noopener' }, s.publisher + (s.year ? ' ' + s.year : '')) : null));
          }));
        })) : null;
        add(panel, [
          sheetBar(planName(p)),
          fieldChip(F),
          h('div', { style: 'display:flex;flex-direction:column;gap:14px;margin-top:10px' },
            p.id === 'current' && F.current_options ? h('div', { class: 'card' }, winterQuestion(F, function () { rerender(); })) : null,
            h('div', { class: 'card' }, h('h3', { class: 'h3' }, T('your_plan.what_when')), cropRows, h('p', { class: 'small', style: 'margin:0' }, T('your_plan.months_note'))),
            h('div', { class: 'card', style: 'display:flex;flex-direction:column;gap:10px' }, scoreRow('harvest', 'basket'), scoreRow('water', 'drop'), scoreRow('cover'), scoreRow('soil_kept'),
              h('p', { class: 'small', style: 'margin:0' }, T('what_to_grow.range_why'), hasDhm(F) ? ' ' + T('what_to_grow.range_town') : ''), srcs(F, ['twin', 'gpm', 'power', 'soil'])),
            h('div', { class: 'card', style: 'display:flex;flex-direction:column;gap:10px' }, waterQ, caseRows),
            tabBtns, tabBox,
            tips.length ? h('div', { class: 'card' }, h('h3', { class: 'h3' }, T('what_to_grow.tips_title')),
              h('ul', { class: 'tips' }, tips.map(function (t, i) { return h('li', null, h('span', { class: 'k' }, num(i + 1)), h('span', null, t)); })),
              h('p', { class: 'small', style: 'margin:0' }, T('what_to_grow.months_note'))) : null,
            explain,
            btn3(T('what_to_grow.see_years', { year_count: rep.length }), function () { S.howPlan = p.id; go('how/replay'); }, 'book'),
            h('p', { class: 'note' }, T('your_plan.know_best'), ' ', T('your_plan.advisor')))
        ]);
        if (!keep) panel.focus();
      }
      build();
    });
  }
  function openSources(name) {
    fieldReady().then(function (F) {
      if (!F) return;
      function build() {
        var panel = openSheet(build);
        add(panel, [sheetBar(T('your_plan.sources_title')), sourcesList(F, name)]);
        var hl = panel.querySelector('.srcitem.hl'); if (hl) setTimeout(function () { hl.scrollIntoView({ block: 'center' }); }, 50);
        panel.focus();
      }
      build();
    });
  }
  function sourcesList(F, name) {
    var all = (F.sources || []).slice();
    if (F.diary && F.diary.shift_source && !all.some(function (s) { return s.name === F.diary.shift_source.name; })) all.push(F.diary.shift_source);
    return h('div', null, all.map(function (s) {
      return h('div', { class: 'srcitem' + (s.name === name ? ' hl' : '') },
        h('h3', { class: 'h3' }, svg(I(KIND_ICON[s.type] || 'info', 18)), ' ', s.name),
        h('p', { class: 'small', style: 'margin:4px 0 0;font-weight:700;color:var(--brown-2)' }, T('kind.' + s.type)),
        h('p', { class: 'small', style: 'margin:2px 0 0' }, s.product), h('p', { class: 'small', style: 'margin:2px 0 0' }, s.resolution + ' · ' + s.years));
    }));
  }

  // ---------------- How we know (js/how.js, loaded when first opened) ----------------
  SCREENS.how = function (arg) {
    var box = h('section', { class: 'scr scr-how' }, h('div', { class: 's-head' }, bigTitle(T('btn.how_we_know'))), h('div', { class: 's-body' }, loading()));
    var p = W.KS.how ? Promise.resolve() : new Promise(function (res) { var s = h('script', { src: 'js/how.js' }); s.onload = res; s.onerror = res; D.head.append(s); });
    Promise.all([p, fieldReady()]).then(function (r) {
      if (!box.isConnected) return;
      var body = box.querySelector('.s-body'); body.textContent = '';
      if (!r[1] || !W.KS.how) { body.append(notReady()); return; }
      body.append(W.KS.how(r[1]));
      if (arg) setTimeout(function () { SCREENS.how.scrollTo(arg); }, 80);
    });
    return box;
  };
  // ---------------- Fields around the world (js/world.js, loaded when first opened; owner, 2026-11-15) ----------------
  function worldLink() { return h('a', { class: 'judges', href: '#/world' }, svg(I('globe', 16)), T('farm.world_link')); }
  SCREENS.world = function () {
    var body = h('div', { class: 's-body' }, loading());
    (S.worldP = S.worldP || loadScript('js/world.js')).then(function () { body.textContent = ''; body.append(W.KS.world ? W.KS.world() : notReady()); });
    return h('section', { class: 'scr scr-how' }, h('div', { class: 's-head' }, bigTitle(T('farm.world_title'))), body);
  };
  SCREENS.how.scrollTo = function (id) { var el = D.getElementById('how-' + id); if (el) el.scrollIntoView({ behavior: RM ? 'auto' : 'smooth', block: 'start' }); };

  // ---------------- start ----------------
  function grass() {
    var g = $('#sky .grass'), out = '', seed = 7;
    function rnd() { seed = (seed * 9301 + 49297) % 233280; return seed / 233280; }
    var cols = ['#5F8A4B', '#6E9A55', '#7FA862', '#8DB46E'];
    for (var x = 0; x <= 385; x += 7) {
      var top = 16 + rnd() * 40, lean = (rnd() - 0.5) * 8;
      out += '<path class="blade" d="M ' + x + ' 82 Q ' + (x + lean * 0.3).toFixed(1) + ' ' + (82 - (82 - top) * 0.6).toFixed(1) + ' ' + (x + lean).toFixed(1) + ' ' + top.toFixed(1) +
        '" fill="none" stroke="' + cols[Math.floor(rnd() * 4)] + '" stroke-width="' + (2 + rnd() * 1.6).toFixed(1) + '" stroke-linecap="round" style="animation-duration:' +
        (2.6 + rnd() * 1.8).toFixed(2) + 's;animation-delay:-' + (rnd() * 3).toFixed(2) + 's"/>';
    }
    g.innerHTML = out;
    var sky = $('#sky');
    [[-40, 90, 189, 79, 8.8, -4.1], [300, 70, 177, 74, 9.3, -5.7], [-30, 380, 116, 48, 7.6, -2.8], [320, 330, 141, 59, 7.5, -1.5], [-50, 600, 137, 57, 7.9, -5.2],
      [310, 560, 159, 66, 11, -0.8], [30, 690, 189, 79, 7.7, -5.8], [280, 700, 131, 55, 11.8, -3.2], [110, 790, 159, 66, 8.8, -1]].forEach(function (p) {
      sky.append(h('span', { class: 'puff', style: 'left:' + (p[0] / 3.9) + '%;top:' + p[1] + 'px;width:' + p[2] + 'px;height:' + p[3] + 'px;animation-duration:' + p[4] + 's;animation-delay:' + p[5] + 's' }));
    });
  }
  // self-hosted fonts (fonts/fonts.css), after the first screen so it stays small; no request leaves the site
  function loadFonts() { if (!D.querySelector('link[href="fonts/fonts.css"]')) D.head.append(h('link', { rel: 'stylesheet', href: 'fonts/fonts.css' })); }   // index.html links it since 2026-11-15
  // The loading curtain (owner, 2026-11-15; index.html #curtain, css "curtain"). The welcome: "Welcome" in the site's 7
  // languages (the words of pipeline/words shared.welcome), one after another, Nepali first, once per visit, while the app
  // loads; the curtain slides up when the data is in AND every word has shown, all within 2 s (HELLO_FIRST_MS + 6 steps +
  // HELLO_HOLD_MS + LIFT_MS); a tap or a key skips it. Later loads in the same visit: no words, it lifts as soon as Home
  // is drawn. Reduced motion: the leaf and "स्वागत छ · Welcome", still, then gone without sliding. Returns how long the
  // welcome wants the curtain (ms from now; 0: no welcome); on any failure, 0.
  var HELLO_FIRST_MS = 80, HELLO_STEP_MS = 190, HELLO_HOLD_MS = 100, HELLO_STILL_MS = 1200, LIFT_MS = 540, REPEAT_MIN_MS = 350;
  function hello(cur) {
    try {
      var box = cur.querySelector('.hello'), ss = W.sessionStorage;
      if (!box || ss.getItem('ks.hello')) return 0;
      ss.setItem('ks.hello', '1');
      var words = [].slice.call(box.children);
      if (RM) {
        box.textContent = words[0].textContent + ' · ' + words[1].textContent;
        box.hidden = false; box.classList.add('still');
        return HELLO_STILL_MS;
      }
      var i = -1;
      box.hidden = false;
      (function next(ms) {
        setTimeout(function () {
          if (!cur.isConnected || cur.classList.contains('lift')) return;
          if (i >= 0) words[i].className = 'off';
          i = (i + 1) % words.length; words[i].className = 'on';   // loops while the data loads
          next(HELLO_STEP_MS);
        }, ms);
      })(HELLO_FIRST_MS);
      return HELLO_FIRST_MS + HELLO_STEP_MS * (words.length - 1) + HELLO_HOLD_MS;
    } catch (e) { return 0; }
  }
  function init() {
    grass();
    S.winter = store.get('winter'); S.water = store.get('water');
    var t0 = Date.now(), cur = $('#curtain'), ready = false, wantMs = hello(cur);
    var bar = cur && cur.querySelector('.cbar span'), prog = 0;
    function step(x) { prog = Math.max(prog, Math.min(1, x)); if (bar) bar.style.transform = 'scaleX(' + prog.toFixed(3) + ')'; }   // the progress line
    step(0.12);                                                      // the page and its script are in
    function lift() {
      if (!ready || !cur.isConnected || cur.classList.contains('lift')) return;
      step(1);
      if (RM) { cur.remove(); return; }
      cur.classList.add('lift');
      setTimeout(function () { cur.remove(); }, LIFT_MS + 60);
    }
    function skip() { wantMs = 0; lift(); }
    cur.addEventListener('click', skip); D.addEventListener('keydown', skip, { once: true });
    Promise.all([getJSON('data/words.json').then(function (x) { step(prog + 0.45); return x; }),
                 getJSON('data/index.json').then(function (x) { step(prog + 0.18); return x; }), demoOn()]).then(function (r) {
      S.words = r[0]; S.index = r[1]; S.demo = r[2] === true;   // phone as drone (hotspot only)
      if (!S.words) { cur.append(h('button', { type: 'button', class: 'round', style: 'position:absolute;bottom:40px', 'aria-label': 'reload', onclick: function () { location.reload(); } }, svg(I('redo', 22)))); return; }
      var ids = ((S.index && S.index.fields) || []).map(function (f) { return f.id; });
      var fid = store.get('fid');
      S.fid = ids.indexOf(fid) >= 0 ? fid : (ids[0] || 'demo');
      var want = store.get('lang') || defaultLang(S.fid);
      S.lang = langInfo(want) ? want : 'ne';
      D.documentElement.lang = S.lang;
      W.addEventListener('hashchange', onRoute);
      onRoute();
      offlineLine(); offline();
      step(0.9);                                                     // Home is drawn
      ready = true;
      setTimeout(lift, Math.max(0, (wantMs || (RM ? 0 : REPEAT_MIN_MS)) - (Date.now() - t0)));   // data first, then the welcome's time
      var idle = W.requestIdleCallback || function (f) { return setTimeout(f, 300); };
      idle(function () { fieldReady(); });
      if (D.readyState === 'complete') loadFonts(); else W.addEventListener('load', loadFonts);
    });
  }
  W.KS = { sureOf: sureOf, S: S, h: h, add: add, svg: svg, ic: ic, I: I, T: T, L: L, P: P, PL: PL, num: num, digits: digits, rng: rng, crop: crop, lines: lines, node: node, scr: scr,
    srcTag: srcTag, srcs: srcs, srcObj: srcObj, effPlans: effPlans, planName: planName, alts: alts, yearRange: yearRange, hasDhm: hasDhm, scoreRange: scoreRange,
    waterCases: waterCases, pics: pics, basketSvg: basketSvg, getJSON: getJSON, loadLeaflet: loadLeaflet, osm: osm, go: go, notReady: notReady, loading: loading,
    sampleChip: sampleChip, isPlaceholder: isPlaceholder, sourcesList: sourcesList, mocked: mocked, fogLayer: fogLayer, langInfo: langInfo, monthName: monthName,
    MONTHS: MONTHS, RM: RM, later: later, sentences: sentences, btn3: btn3, vsChip: vsChip,
    btn2: btn2, cta: cta, screen: screen, labs: labs, rainMark: rainMark, closeSheet: closeSheet, bigTitle: bigTitle, store: store, fmtDate: fmtDate, geom: geom, fieldBox: fieldBox,
    cropsLine: cropsLine, monthShort: monthShort, fogTag: fogTag, features: features, featData: featData, probeData: probeData, forField: forField, partWord: partWord, recordedLine: recordedLine, bowlLines: bowlLines,
    labOf: labOf, scaleName: scaleName, faceSvg: faceSvg, monthName: monthName, curOption: curOption, winterId: winterId, swapId: swapId, winterQuestion: winterQuestion, chooseField: chooseField, rerender: rerender,
    gregInNepali: gregInNepali, blockKeys: blockKeys, restMonths: restMonths, joinList: joinList, BS_ORDER: BS_ORDER, openSheet: openSheet, sheetBar: sheetBar, fieldsList: fieldsList, droneView: droneView, droneLabel: droneLabel, droneSat: droneSat, droneCredit: droneCredit, indexEntry: indexEntry, abroad: abroad, every: every, uid: function () { return ++uid; },
    say: say, bsMonth: bsMonth, monthSpanEl: monthSpanEl, sixBlocks: sixBlocks, weatherWhy: weatherWhy, worldLink: worldLink, inNepal: inNepal };

  // ---------------- Behind the scenes: your field, seen by NASA (owner, 2026-11-15; js/behind.js) ----------------
  // For judges: the section sits at the end of Home's scroll, below the first screen, and on How we know; nothing of it
  // loads until it is scrolled to. A farmer's answer shows only a small tag: a tap opens the matching NASA card.
  function behind() { S.behindP = S.behindP || loadScript('js/behind.js'); return S.behindP; }
  function behindBox(lazy) {
    var body = h('div'), box = h('section', { class: 'behindbox', id: 'how-behind' }, h('h2', { class: 'h2' }, T('farm.behind_title')), body);
    function fill() {
      if (body.firstChild) return;   // once
      body.append(loading());
      behind().then(function () { return W.KS.behind ? W.KS.behind.section() : null; }).then(function (el) {
        body.textContent = '';
        if (el) { body.append(el); return; }
        if (lazy) { body.append(notReady()); return; }   // none for this field: Home says so, How we know drops it and its link
        box.remove(); var a = D.querySelector('.how a[href="#/how/behind"]'); if (a) a.remove();
      });
    }
    if (lazy && W.IntersectionObserver) {
      var io = new IntersectionObserver(function (es) { if (es.some(function (e) { return e.isIntersecting; })) { io.disconnect(); fill(); } });
      io.observe(box); box.addEventListener('click', fill);   // a tap on the title fills it too
    } else fill();
    return box;
  }
  // "What this tool can and cannot tell you" (owner's plan, part A2, 2026-11-15; story.json limits): on Home below the
  // first screen (loaded when scrolled to) and first on How we know. The checked and estimate lists come from the
  // compliance table of the field story.json was built for, so they show only on that field.
  function limitsBox(lazy) {
    var box = h('section', { class: 'card limitsbox', id: 'how-limits' }, loading());
    function fill() {
      if (box._done) return; box._done = true;
      getJSON('data/story.json').then(function (st) {
        var Lm = st && st.limits; box.textContent = '';
        if (!Lm) { box.remove(); return; }
        var mine = st.field === S.fid;
        add(box, [h('h2', { class: 'h2' }, P(Lm.title)), lines(Lm.lines.map(P)),
          mine ? h('p', { class: 'small', style: 'font-weight:700;margin:4px 0 0' }, P(Lm.checked.title)) : null,
          mine ? ticks(Lm.checked.items.map(P)) : null,
          mine ? h('details', null, h('summary', { class: 'small', style: 'font-weight:700;cursor:pointer' }, P(Lm.estimates.title) + ' ' + num(Lm.estimates.items.length)),
            h('ul', { class: 'lines os' }, Lm.estimates.items.map(function (x) { return h('li', null, P(x)); }))) : null]);
      });
    }
    if (lazy && W.IntersectionObserver) {
      var io = new IntersectionObserver(function (es) { if (es.some(function (e) { return e.isIntersecting; })) { io.disconnect(); fill(); } });
      io.observe(box);
    } else fill();
    return box;
  }
  // "Our promise" (owner, 2026-11-15 afternoon): free for every farmer, always; no ads, no accounts; data and photos stay
  // on the phone; open code and open data. Words from story.json `promise` (pipeline/export/build_story.promise_block).
  function promiseBox(lazy) {
    var box = h('section', { class: 'card limitsbox', id: 'how-promise' }, loading());
    function fill() {
      if (box._done) return; box._done = true;
      getJSON('data/story.json').then(function (st) {
        var Pr = st && st.promise; box.textContent = '';
        if (!Pr) { box.remove(); return; }
        add(box, [h('h2', { class: 'h2' }, P(Pr.title)), lines(Pr.lines.map(P))]);
      });
    }
    if (lazy && W.IntersectionObserver) {
      var io = new IntersectionObserver(function (es) { if (es.some(function (e) { return e.isIntersecting; })) { io.disconnect(); fill(); } });
      io.observe(box);
    } else fill();
    return box;
  }
  function yearSpan(s) { var m = s && String(s.years).match(/^(\d{4})-(\d{4})$/); return m ? m[2] - m[1] + 1 : 0; }
  // the tags of one farmer answer, [[kind, years], ...]: kind is rain, weather or space (behind.json `tags`), years the
  // number of years the answer stands on. Shown only on the field behind.json was built for.
  function nasaTags(pairs) {
    var row = h('div', { class: 'srcs nasa', hidden: true });
    getJSON('data/behind.json').then(function (b) {
      if (!b || b.field !== S.fid) return;
      pairs.forEach(function (p) {
        if (!p[1] || !b.tags[p[0]]) return;
        row.append(h('button', { type: 'button', class: 'src', onclick: function (e) { e.stopPropagation(); behind().then(function () { if (W.KS.behind) W.KS.behind.open(p[0]); }); } },
          svg(I('sat', 12, 2.2)), T('farm.tag_' + p[0], { year_count: p[1] })));
      });
      row.hidden = !row.firstChild;
    });
    return row;
  }
  W.KS.behindBox = behindBox; W.KS.limitsBox = limitsBox; W.KS.promiseBox = promiseBox;
  if (D.readyState === 'loading') D.addEventListener('DOMContentLoaded', init); else init();
})();
