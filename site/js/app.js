/* Khet Sathi: the static site (plain JavaScript, no build step, no key, no server).
   Every number and sentence on screen comes from site/data/: fields/<id>.json, words.json, index.json, area/<id>.json,
   story.json, probe_log.json and live.json (the last three only when they exist). Text goes on the page with
   textContent; innerHTML is used only for the static icons written in this file. Every fetch path is relative. */
(function () {
  'use strict';
  var D = document, W = window;
  var RM = !!(W.matchMedia && W.matchMedia('(prefers-reduced-motion: reduce)').matches);
  var STEPS = ['home', 'photo', 'parts', 'soil', 'choose', 'today', 'next'];
  var ROUTES = STEPS.concat(['how', 'plan']);
  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  // sun x, sun y, tint, sunset, road progress (the phone prototype P0, per step)
  var SKY = { home: [30, 300, 0, 0, 0], photo: [79, 197, 0, 0, 0.16], parts: [131, 119, 0, 0, 0.33], soil: [183, 81, 0.05, 0.1, 0.5],
    choose: [236, 96, 0.15, 0.3, 0.66], today: [288, 159, 0.4, 0.65, 0.84], next: [325, 223, 0.65, 0.95, 1], how: [325, 223, 0.5, 0.8, 1] };
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
    shirt: '<path d="M3 21h18"/>'
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
    S.fieldP = getJSON('data/fields/' + encodeURIComponent(S.fid) + '.json').then(function (f) { S.field = f; return f; });
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
  function curOption(F) {
    var co = F.current_options; if (!co || !co.options) return null;
    var id = S.winter || co['default'];
    return co.options.filter(function (o) { return o.id === id; })[0] || null;
  }
  // the three plans with the farmer's winter-crop answer applied (CONTRACT_CHANGES, current_options)
  function effPlans(F) {
    var co = F.current_options, opt = co && S.winter ? curOption(F) : null;
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
  function planName(p) { var n = node('lbl.what_to_grow.plan.' + p.id); return n ? L(n) : p.name; }
  function cropsLine(p) { return p.crops.map(function (c) { return crop(c.crop); }).join(' → '); }
  function nextSow(p, now) {
    now = now || new Date();
    var best = null;
    p.crops.forEach(function (c) {
      var mm = +c.start.slice(0, 2), dd = +c.start.slice(3, 5);
      var d = new Date(now.getFullYear(), mm - 1, dd);
      if (d < new Date(now.getFullYear(), now.getMonth(), now.getDate())) d = new Date(now.getFullYear() + 1, mm - 1, dd);
      if (!best || d < best.d) best = { d: d, c: c };
    });
    return best;
  }
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
    dem: /NASADEM/i, twin: /twin/i, dhm: /^DHM/i, nex: /NEX-GDDP/i };
  function srcObj(F, key) { return (F.sources || []).filter(function (s) { return SRC[key] && SRC[key].test(s.name); })[0]; }
  function srcTag(F, key) {
    var s = typeof key === 'string' ? srcObj(F, key) : key;
    if (!s) return null;
    var short = String(s.name).replace(/\s*\(.*$/, '');
    return h('button', { type: 'button', class: 'src', title: s.name + ' · ' + s.resolution + ' · ' + s.years,
      onclick: function (e) { e.stopPropagation(); openSources(s.name); } }, svg(I(KIND_ICON[s.type] || 'info', 12, 2.2)), short + ' · ' + digits(s.years));
  }
  function srcs(F, keys) { return h('div', { class: 'srcs' }, keys.map(function (k) { return srcTag(F, k); })); }

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
  function loading() { return h('div', { class: 'loading', role: 'status' }, h('span', { class: 'dots' }, h('i'), h('i'), h('i'))); }
  function notReady(extra) { return h('div', { class: 'card soft' }, h('p', { class: 'lead' }, T('btn.not_ready')), extra || null); }
  function stepsBar(n) { return h('div', { class: 'steps', 'aria-hidden': 'true' }, [1, 2, 3].map(function (i) { return h('span', { class: i <= n ? 'on' : '' }); })); }
  function screen(name, parts) {
    return h('section', { class: 'scr scr-' + name },
      h('div', { class: 's-head' }, parts.head), parts.scene ? h('div', { class: 's-scene' }, parts.scene) : null,
      h('div', { class: 's-body' }, parts.body), h('div', { class: 's-cta' }, parts.cta));
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
  function geom(F) {
    var secs = F.field.sections || [], x0 = 1e9, x1 = -1e9, y0 = 1e9, y1 = -1e9;
    secs.forEach(function (s) { s.polygon.forEach(function (p) { x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0]); y0 = Math.min(y0, p[1]); y1 = Math.max(y1, p[1]); }); });
    var dx = (x1 - x0) || 1, dy = (y1 - y0) || 1;
    return secs.map(function (s) {
      var a = 1e9, b = -1e9, c = 1e9, d = -1e9;
      s.polygon.forEach(function (p) { a = Math.min(a, p[0]); b = Math.max(b, p[0]); c = Math.min(c, p[1]); d = Math.max(d, p[1]); });
      var g = { s: s, l: (a - x0) / dx * 100, r: (b - x0) / dx * 100, t: (y1 - d) / dy * 100, b: (y1 - c) / dy * 100, n: String(s.id).replace(/^s/, '') };
      g.cx = (g.l + g.r) / 2; g.cy = (g.t + g.b) / 2;
      return g;
    }).sort(function (p, q) { return (Math.round(p.t) - Math.round(q.t)) || (p.l - q.l); });
  }
  function fieldBox(F, mode, opt) {
    opt = opt || {};
    var G = geom(F), box = h('div', { class: 'fieldbox', role: 'img', 'aria-label': T('parts.split', { section_count: G.length }) });
    box.append(h('div', { class: 'wm', 'aria-hidden': 'true' }, T('where.photo_h1')));
    var colour = { green: 'rgba(63,122,46,.16)', yellow: 'rgba(201,138,27,.2)', red: 'rgba(184,67,42,.2)', grey: 'rgba(139,143,134,.14)' };
    G.forEach(function (g, i) {
      var st = 'left:' + g.l + '%;top:' + g.t + '%;width:' + (g.r - g.l) + '%;height:' + (g.b - g.t) + '%;';
      var bg = mode === 'status' ? colour[g.s.status] || colour.grey : (i % 3 === 0 ? 'rgba(20,48,30,.06)' : 'rgba(154,84,38,.06)');
      var q = h('span', { class: 'q', style: st + 'background:' + bg + (mode === 'grow' ? ';animation:ks-rise 500ms ease ' + (1300 + i * 100) + 'ms both' : '') });
      g.q = q; box.append(q);
    });
    var xs = {}, ys = {};
    G.forEach(function (g) { if (g.l > 0.5) xs[g.l.toFixed(2)] = 1; if (g.t > 0.5) ys[g.t.toFixed(2)] = 1; });
    Object.keys(xs).forEach(function (x) { box.append(h('span', { class: 'vl', style: 'left:' + x + '%' + (mode === 'grow' ? '' : ';animation:none') })); });
    Object.keys(ys).forEach(function (y) { box.append(h('span', { class: 'hl', style: 'top:' + y + '%' + (mode === 'grow' ? '' : ';animation:none') })); });
    if (mode === 'grow' || mode === 'sway' || mode === 'robot') {
      G.forEach(function (g, qi) {
        for (var r = 0; r < 3; r++) for (var c = 0; c < 4; c++) {
          var x = g.l + (g.r - g.l) * (0.16 + c * 0.23), y = g.t + (g.b - g.t) * (0.28 + r * 0.28);
          if (Math.abs(x - g.cx) < (g.r - g.l) * 0.2 && Math.abs(y - g.cy) < (g.b - g.t) * 0.28) continue;
          var d = 2000 + qi * 160 + ((r * 4 + c) % 9) * 50;
          var sp = h('span', { class: 'sprout ' + (mode === 'grow' ? 'g' : 's'), style: 'left:' + x + '%;top:' + y + '%;' +
            (mode === 'grow' ? 'animation-delay:' + d + 'ms,' + (d + 600) + 'ms' : 'animation-delay:-' + ((r + c) * 0.4) + 's') });
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
        g.num = h('span', { class: 'n', style: 'left:' + g.cx + '%;top:' + (mode === 'robot' ? g.cy + 14 : g.cy) + '%;' +
          (mode === 'robot' ? 'width:32px;height:32px;margin:-16px 0 0 -16px;font-size:15px;' : '') + (mode === 'grow' ? 'animation-delay:' + (1300 + i * 100) + 'ms' : 'animation:none') }, digits(g.n));
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
    [['ne', 'नेपाली'], ['en', 'EN']].forEach(function (x) {
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
    var back = { photo: 'home', parts: 'photo', soil: 'parts', choose: 'soil', today: 'choose', next: 'choose', how: 'home' };
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
    setTimeout(build, 380);
  }
  function rerender() {
    if (!S.cur) return;
    clearTimers();
    var app = $('#app'); app.textContent = ''; app.append(SCREENS[S.cur](S.arg, true));
    if (S.sheetFor) { var y = $('#sheet .panel') ? $('#sheet .panel').scrollTop : 0; S.sheetFor(true); if ($('#sheet .panel')) $('#sheet .panel').scrollTop = y; }
  }

  // ---------------- 1 home ----------------
  SCREENS.home = function () {
    var ix = (S.index && S.index.fields) || [];
    var f0 = ix.filter(function (f) { return f.id === S.fid; })[0] || ix[0];
    var sample = f0 && isPlaceholder(f0.name);
    var cap = h('div', { 'aria-live': 'polite' }), sel = -1, cards = [];
    var CAPS = [['home.intro', 'home.you_decide'], ['check_soil.wide_close', 'check_soil.together'], ['home.card_months_sub', 'home.records_years']];
    function showCap() {
      var c = CAPS[sel + 1]; cap.textContent = '';
      var sub = c[1];
      if (sub === 'home.records_years') {
        var gpm = S.field && srcObj(S.field, 'gpm');
        sub = gpm ? T(sub, { source_years: gpm.years }) : '';
        if (!S.field) fieldReady().then(function () { if (cap.isConnected && sel === 1) showCap(); });
      } else sub = T(sub);
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
    var island = h('div', { class: 'island' },
      [[-30, 208, 190, 70, 7, -1, 1], [90, 232, 190, 64, 8, -3, 1], [200, 206, 190, 72, 6.5, -2, 1], [-40, 150, 120, 52, 9, -4, -1], [270, 120, 120, 50, 8.5, -1.5, -1],
        [40, 20, 110, 40, 10, -5, -1], [20, 250, 130, 50, 7.5, -0.5, 1], [190, 252, 140, 50, 8, -2, 1]].map(function (p) {
        return h('span', { class: 'puff', 'aria-hidden': 'true', style: 'left:' + (p[0] / 3.42) + '%;top:' + (p[1] / 2.89) + '%;width:' + (p[2] / 3.42) + '%;height:' + p[3] + 'px;z-index:' + p[6] + ';animation-duration:' + p[4] + 's;animation-delay:' + p[5] + 's' });
      }),
      h('img', { src: 'img/farm.webp', alt: '', width: '342', height: '289', decoding: 'async', fetchpriority: 'high' }));
    var floats = h('div', { class: 'floats', 'aria-hidden': 'true' },
      [['stick', '#14301E', '#C8E05A', 'home.card_today_tag', 'home.card_today_sub', 'left:2%;top:8%'],
        ['sat', '#E3EEDC', '#2E5A2A', 'home.card_months_tag', 'home.card_months_big', 'right:0;top:22%;animation-delay:.8s'],
        ['pin', '#FFF3C9', '#6B4B00', 'btn.sample_field', 'home.sample_note', 'left:0;bottom:12%;animation-delay:1.4s']].map(function (f) {
        if (f[2] === '#6B4B00' && !sample) return null;
        return h('div', { class: 'fl', style: f[5] }, h('span', { class: 'ic', style: 'background:' + f[1] + ';color:' + f[2] }, svg(I(f[0], 20))),
          h('span', null, h('span', { class: 'tg' }, T(f[3])), h('br'), h('span', { class: 'tx' }, T(f[4]))));
      }));
    var list = null;
    if (ix.length) {
      list = h('details', { class: 'prepared' }, h('summary', null, T('home.prepared_title')),
        ix.map(function (f) {
          return h('button', { type: 'button', class: 'pf', onclick: function () { chooseField(f.id); go('photo'); } },
            h('span', null, h('b', null, f.name), h('br'), h('span', { class: 'small' }, f.country)), isPlaceholder(f.name) ? sampleChip() : svg(I('arrow', 18)));
        }));
    }
    return screen('home', {
      head: [bigTitle(T('home.hero_1'), T('home.hero_2')), sample ? sampleChip() : null],
      scene: [island, floats],
      body: [h('div', { class: 'homecards' }, cards), cap],
      cta: [cta(T('home.try_sample'), function () { go('photo'); }, { sweep: true }),
        sample ? h('p', { class: 'small', style: 'margin:0;text-align:center' }, T('home.sample_note')) : null,
        btn3(T('btn.how_we_know'), function () { go('how'); }, 'book'), list]
    });
  };
  function chooseField(id) {
    if (id === S.fid) return;
    S.fid = id; S.field = null; S.fieldP = null; S.winter = null; store.set('fid', id); store.set('winter', null);
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
  function osm(L, m) {
    if (m.attributionControl) m.attributionControl.setPrefix('<a href="https://leafletjs.com">Leaflet</a>');
    L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>' }).addTo(m);
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
  function fact(icon, textLines, tags) {
    return h('div', { class: 'fact' }, h('span', { class: 'ic' }, svg(I(icon, 20))), h('div', { class: 'grow', style: 'display:flex;flex-direction:column;gap:6px' }, lines(textLines), tags));
  }
  SCREENS.photo = function () {
    return withField('photo', function (F) {
      var sample = isPlaceholder(F.field.name);
      var mapEl = h('div', { style: 'position:absolute;inset:0' });
      var mbox = h('div', { class: 'mapbox' }, h('div', { class: 'msg' }, svg(I('pin', 40, 1.6)), T('where.map_not_photo')), mapEl,
        sample ? h('div', { class: 'mapnote' }, sampleChip()) : null);
      var drawbar = h('div', { class: 'drawbar', hidden: true }), msg = h('div', { 'aria-live': 'polite' });
      var map = null, Lf = null, draw = null;
      loadLeaflet().then(function (L) {
        if (!mapEl.isConnected) return;
        Lf = L; mbox.querySelector('.msg').remove();
        map = L.map(mapEl, { scrollWheelZoom: false, zoomSnap: 0.5 });
        osm(L, map);
        var pts = [];
        (F.field.sections || []).forEach(function (s) {
          var ll = s.polygon.map(function (p) { return [p[1], p[0]]; }); pts = pts.concat(s.polygon);
          L.polygon(ll, { color: '#FBF4EA', weight: 1.5, dashArray: '4 5', fill: false, interactive: false }).addTo(map);
        });
        if (pts.length) {
          var hl = hull(pts).map(function (p) { return [p[1], p[0]]; });
          L.polygon(hl, { color: '#14301E', weight: 7, opacity: .35, fill: false, interactive: false }).addTo(map);
          var outline = L.polygon(hl, { color: '#C8E05A', weight: 4, fillColor: '#C8E05A', fillOpacity: .12, interactive: false }).addTo(map);
          map.fitBounds(outline.getBounds(), { padding: [70, 70], maxZoom: 17 });
        } else map.setView([F.field.lat, F.field.lon], 17);
      }).catch(function () { var m = mbox.querySelector('.msg'); if (m) m.append(h('p', null, T('btn.not_ready'))); });
      function startDraw() {
        if (!map) return;
        if (draw) { draw.layer.remove(); }
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
      var D_ = F.diary, gw = D_.groundwater || {};
      var facts = h('div', null,
        fact('soil', [T('from_space.bare', { bare_days: D_.bare_days }), T('from_space.bare_why')], srcs(F, ['hls'])),
        D_.shift_note ? fact('rain', PL(D_.shift_note), srcs(F, [D_.shift_source || 'dhm'])) : null,
        gw.direction ? fact('drop', [T('from_space.water_' + gw.direction), gw.confidence >= 0.95 ? T('from_space.water_wide') : null, T('from_space.water_not_yours')], srcs(F, ['grace'])) : null);
      return screen('photo', {
        head: [stepsBar(1), bigTitle(T('where.photo_h1'), T('where.photo_h2'))],
        scene: mbox,
        body: [msg,
          h('div', { class: 'card soft' }, sample ? h('p', { class: 'lead' }, T('home.sample_note')) : null,
            lines([T('where.map_not_photo'), T('where.line_is_field'), T('where.photo_later')], 'sub')),
          h('div', { class: 'card' }, h('h2', { class: 'h2' }, L(scr('from_space').title)), winterQuestion(F), facts)],
        cta: [btn2(T('where.draw_own'), startDraw, 'pin'), cta(T('where.make_parts'), function () { go('parts'); })]
      });
    });
  };

  // ---------------- 3 your field's parts ----------------
  SCREENS.parts = function () {
    return withField('parts', function (F) {
      var n = (F.field.sections || []).length;
      var lead = h('p', { class: 'lead', 'aria-live': 'polite' }, T('parts.making'));
      later(function () { lead.textContent = T('parts.split', { section_count: n }); }, 2000);
      return screen('parts', {
        head: [stepsBar(2), bigTitle(L(scr('parts').title)), isPlaceholder(F.field.name) ? sampleChip() : null],
        scene: fieldBox(F, 'grow'),
        body: h('div', { class: 'card soft', style: 'display:flex;flex-direction:column;gap:6px' }, lead, lines([T('parts.numbers'), T('parts.look_same'), T('parts.stick_tells')], 'sub')),
        cta: cta(L(scr('check_soil').title), function () { go('soil'); })
      });
    });
  };

  // ---------------- 4 soil test: the prototype stick, carried by hand; Krishi Scout is the plan ----------------
  function readingWords(r) {
    var out = [];
    if (r.state === 'done') {
      if (r.off_scale) out.push(T('check_soil.off_scale'));
      else if (r.steady !== false && r.wetness != null) out.push(T('each_part.how_wet', { wetness: r.wetness }));
      if (r.relative) out.push(T('check_soil.' + ({ drier: 'drier', wetter: 'wetter', 'about the same': 'about_same' }[r.relative] || 'about_same')));
      if (r.band) out.push(T('check_soil.band_' + r.band.replace(/ /g, '_')));
      if (r.water_pct != null) out.push(T('check_soil.water_in_soil') + ' ' + T('btn.about') + ' ' + num(r.water_pct) + '%' +
        (r.give_or_take_pct != null ? ', ' + T('check_soil.give_or_take') + ' ' + num(r.give_or_take_pct) : ''));
      if (r.temp != null) out.push(T('each_part.how_warm', { temp: r.temp }));
    }
    return out;
  }
  function stateEl(state) {
    if (state === 'settling' || state === 'measuring') return h('span', { class: 'state now' }, T('check_soil.' + state), h('span', { class: 'dots' }, h('i'), h('i'), h('i')));
    if (state === 'done') return h('span', { class: 'state done' }, svg(I('tick', 14, 3)), ' ', T('check_soil.measured'));
    if (state === 'test_again') return h('span', { class: 'state now' }, svg(I('redo', 14)), ' ', T('check_soil.test_again'));
    return h('span', { class: 'state' }, T('check_soil.no_reading'));
  }
  SCREENS.soil = function () {
    return withField('soil', function (F) {
      var box = fieldBox(F, 'robot'), G = box._g;
      // the Krishi Scout idea: drive to the middle of each part and test (an illustration, not a reading)
      var route = D.createElementNS('http://www.w3.org/2000/svg', 'svg');
      route.setAttribute('class', 'route'); route.setAttribute('viewBox', '0 0 100 100'); route.setAttribute('preserveAspectRatio', 'none');
      box.append(route);
      var robot = h('div', { class: 'robot', style: 'left:7%;top:50%' }); robot.innerHTML = ROBOT; box.append(robot);
      var ring = h('span', { class: 'ring', hidden: true }); box.append(ring);
      var pos = [7, 50];
      function leg(i) {
        if (i >= G.length) { robot.firstChild.setAttribute('class', 'happy'); robot.querySelector('.led').setAttribute('fill', '#5FBF6A'); ring.hidden = true; return; }
        var g = G[i], b = [g.cx, g.cy], ms = Math.max(900, Math.round(Math.hypot(b[0] - pos[0], b[1] - pos[1]) * 22));
        var ln = D.createElementNS('http://www.w3.org/2000/svg', 'line');
        [['x1', pos[0]], ['y1', pos[1]], ['x2', b[0]], ['y2', b[1]], ['pathLength', 1], ['stroke-dasharray', 1], ['stroke', '#9A5426'], ['stroke-width', 0.6], ['stroke-linecap', 'round'], ['stroke-opacity', .5]]
          .forEach(function (kv) { ln.setAttribute(kv[0], kv[1]); });
        ln.setAttribute('style', 'stroke-dashoffset:1;animation:ks-draw ' + ms + 'ms cubic-bezier(.45,0,.3,1) forwards');
        route.append(ln);
        robot.style.transitionDuration = ms + 'ms';
        robot.firstChild.setAttribute('class', 'moving');
        robot.firstChild.style.transform = b[0] < pos[0] - 1 ? 'scaleX(-1)' : '';
        robot.style.left = b[0] + '%'; robot.style.top = b[1] + '%';
        pos = b;
        later(function () { robot.firstChild.setAttribute('class', 'probing'); ring.hidden = false; ring.style.left = b[0] + '%'; ring.style.top = b[1] + '%'; robot.querySelector('.led').setAttribute('fill', '#F2C230'); }, ms);
        later(function () { g.q.classList.add('t'); ring.hidden = true; }, ms + 1000);
        later(function () { leg(i + 1); }, ms + 1400);
      }
      if (RM) { G.forEach(function (g) { g.q.classList.add('t'); }); robot.style.left = G.length ? G[G.length - 1].cx + '%' : '7%'; }
      else later(function () { leg(0); }, 800);

      var cards = h('div', { class: 'parts', 'aria-live': 'polite' }), status = h('div', { 'aria-live': 'polite' });
      function drawCards(byPart, live) {
        cards.textContent = '';
        G.forEach(function (g, i) {
          var r = byPart[g.s.id] || null;
          var sure = r ? (r.sure != null ? r.sure : (r.after ? r.after.sure : null)) : g.s.sure;
          var st = live && live.section === g.s.id ? live.state : (r ? r.state : null);
          var c = h('div', { class: 'part fogwrap' + (live && live.stale ? ' stale' : ''), style: 'animation-delay:' + (i * 90) + 'ms' },
            h('div', { class: 'top' }, h('span', { class: 'name' }, T('each_part.part_name', { section: g.n })), stateEl(st)),
            r ? lines(readingWords(r)) : null,
            r && r.before ? h('p', { class: 'small', style: 'margin:0' }, T('check_soil.before_reading') + ' ' + T('each_part.how_sure', { sure_pct: r.before.sure * 100 })) : null,
            r && sure == null ? fogTag() : h('p', { class: 'small', style: 'margin:0' }, T('each_part.how_sure', { sure_pct: (sure || 0) * 100 })),
            fogLayer(sure == null ? g.s.sure : sure));
          cards.append(c);
        });
      }
      function fromLive(lv) {
        var m = {}; (lv.parts || []).forEach(function (p) { m[p.section] = p; });
        if (lv.section && (lv.state === 'done' || lv.state === 'test_again')) m[lv.section] = Object.assign({}, m[lv.section] || {}, lv);
        return m;
      }
      function liveStatus(lv) {
        status.textContent = '';
        var g = G.filter(function (x) { return x.s.id === lv.section; })[0];
        status.append(h('div', { class: 'card' + (lv.stale ? ' stale' : '') },
          lv.stale ? h('p', { class: 'lead' }, svg(I('warn', 18, 3)), ' ', T('check_soil.not_connected')) : null,
          g ? h('p', { class: 'lead' }, T('check_soil.part_of', { section: g.n, section_count: lv.parts_total || G.length })) : null,
          lv.state ? stateEl(lv.state) : null,
          lv.state === 'settling' || lv.state === 'measuring' ? h('p', { class: 'sub' }, T('check_soil.hold')) : null,
          (lv.caveats || []).length ? lines((lv.caveats || []).map(P), 'small') : null));
      }
      drawCards({}, null);
      Promise.all([getJSON('data/live.json', true), getJSON('data/probe_log.json')]).then(function (res) {
        if (!cards.isConnected) return;
        var lv = res[0], log = res[1];
        if (lv) {
          liveStatus(lv); drawCards(fromLive(lv), lv);
          every(function () { getJSON('data/live.json', true).then(function (x) { if (x && cards.isConnected) { liveStatus(x); drawCards(fromLive(x), x); } }); }, 2000);
        } else if (log && log.sessions && log.sessions.length) {
          var sess = log.sessions[log.sessions.length - 1];
          status.append(btn2(T('check_soil.replay_check'), function () {
            var shown = {}; drawCards({}, null);
            sess.parts.forEach(function (p, i) {
              later(function () { shown[p.section] = Object.assign({ state: 'measuring' }, { before: p.before }); drawCards(shown, null); }, i * 2200);
              later(function () { shown[p.section] = Object.assign({}, p, { sure: p.after ? p.after.sure : null }); drawCards(shown, null); }, i * 2200 + 1400);
            });
          }, 'redo'));
        } else {
          status.append(h('div', { class: 'card soft' }, h('p', { class: 'lead', style: 'margin:0' }, T('check_soil.after_test'))));
        }
      });
      var robotCap = h('div', { class: 'card soft', style: 'display:flex;flex-direction:column;gap:4px' },
        h('p', { class: 'lead', style: 'margin:0' }, svg(I('robot', 18)), ' ', T('check_soil.robot_name')), h('p', { class: 'sub' }, T('check_soil.robot_shows')));
      var honest = h('div', { class: 'card' },
        fact('stick', [T('check_soil.prototype')]), fact('hand', [T('check_soil.by_hand')]), fact('ruler', [T('check_soil.top_only')]), fact('robot', [T('check_soil.robot_next')]));
      return screen('soil', {
        head: [stepsBar(3), bigTitle(L(scr('check_soil').title)), isPlaceholder(F.field.name) ? sampleChip() : null],
        scene: [box, h('div', { style: 'height:10px' }), robotCap],
        body: [honest, status, cards, h('p', { class: 'small', style: 'margin:0' }, svg(I('fog', 16)), ' ', T('each_part.fog'), ' ', T('check_soil.clears'))],
        cta: cta(T('btn.next'), function () { go('choose'); })
      });
    });
  };

  // ---------------- 5 what to see ----------------
  function nextMonths(n) { var m = new Date().getMonth(), out = []; for (var i = 1; i <= (n || 3); i++) out.push(MONTHS[(m + i) % 12]); return out; }
  // a month name short enough for a chip: Bikram Sambat in Nepali, three letters in Latin scripts
  function monthShort(key) { if (S.lang === 'ne') return monthName(key, true); var n = monthName(key); return /^(en|es|fr|sw)$/.test(S.lang) ? n.slice(0, 3) : n; }
  SCREENS.choose = function () {
    var a = h('button', { type: 'button', class: 'bigcard light', onclick: function () { go('today'); } },
      h('div', { class: 'row', style: 'justify-content:space-between' }, h('span', { class: 'chip' }, svg(I('pc', 16)), T('kind.model')),
        h('span', { 'aria-hidden': 'true' }, pics(80, 'basket', 22))),
      h('div', { class: 'grow' }),
      h('div', { class: 'row', style: 'align-items:flex-end;justify-content:space-between' },
        h('div', { style: 'display:flex;flex-direction:column;gap:6px' }, h('span', { class: 't' }, T('each_part.today_h1') + ' ' + T('each_part.today_h2')), h('span', { class: 's' }, T('home.card_today_sub'))),
        h('span', { class: 'go' }, svg(ic(P_.arrow, 22, 2.6), 'lime'))));
    a.querySelector('.go .ico').style.color = '#C8E05A';
    var orbit = svg('<svg width="230" height="230" viewBox="0 0 230 230"><circle cx="115" cy="115" r="110" fill="none" stroke="#FFF" stroke-opacity=".07" stroke-width="2"/><circle cx="115" cy="115" r="78" fill="none" stroke="#FFF" stroke-opacity=".07" stroke-width="2"/><circle cx="115" cy="115" r="46" fill="#C8E05A" fill-opacity=".08"/><g><circle cx="115" cy="37" r="6" fill="#C8E05A"/></g></svg>', 'orbit');
    function monthsCard(n, cls, extra, sub) {
      return h('button', { type: 'button', class: 'bigcard ' + cls, onclick: function () { go('next/' + n); } }, extra,
        h('div', { class: 'row', style: 'position:relative;justify-content:space-between;flex-wrap:wrap;gap:8px' },
          h('span', { class: 'chip' }, svg(I('sat', 16)), T('home.card_months_tag')),
          n === 3 ? h('div', { class: 'row', style: 'gap:5px', 'aria-hidden': 'true' }, nextMonths(3).map(function (m) { return h('span', { class: 'mchip' }, monthShort(m)); })) : null),
        n === 6 ? h('div', { class: 'mstrip', 'aria-hidden': 'true' }, nextMonths(6).map(function (m) { return h('span', null, monthShort(m)); })) : null,
        h('div', { class: 'grow' }),
        h('div', { class: 'row', style: 'align-items:flex-end;justify-content:space-between;position:relative' },
          h('div', { style: 'display:flex;flex-direction:column;gap:6px' }, h('span', { class: 't' }, T('what_to_grow.next_h1') + ' ' + T(n === 6 ? 'what_to_grow.next_h2_6' : 'what_to_grow.next_h2')),
            h('span', { class: 's' }, T(sub))),
          h('span', { class: 'go' }, svg(ic(P_.arrow, 22, 2.6)))));
    }
    var path6 = svg('<svg width="200" height="120" viewBox="0 0 200 120"><path d="M10 110 Q 60 20 100 70 T 190 30" fill="none" stroke="#FBF4EA" stroke-width="2" stroke-dasharray="4 7"/></svg>', 'path6');
    return screen('choose', {
      head: bigTitle(T('check_soil.choose_h1'), T('check_soil.choose_h2')),
      scene: h('div', { class: 'choose' }, a, monthsCard(3, 'darkc', orbit, 'home.card_months_sub'), monthsCard(6, 'greenc', path6, 'what_to_grow.three')),
      body: null,
      cta: btn3(T('btn.how_we_know'), function () { go('how'); }, 'book')
    });
  };

  // ---------------- 6 your field today ----------------
  function greenerMark(g) {
    if (g === 'more' || g === 'less') return h('span', { class: 'mark' }, svg(I('leaf', 16)), T('each_part.greener_' + g));
    if (g === 'unknown') return h('span', { class: 'mark' }, svg(I('info', 16)), T('each_part.greener_unknown'));
    return null;
  }
  SCREENS.today = function () {
    return withField('today', function (F) {
      var G = geom(F), mock = mocked(F, 'field.sections');
      var cards = h('div', { class: 'parts' }, G.map(function (g, i) {
        var s = g.s, status = mock ? 'grey' : s.status;
        var c = h('div', { class: 'part fogwrap', style: 'animation-delay:' + (i * 90) + 'ms' },
          h('div', { class: 'top' }, h('span', { class: 'name' }, T('each_part.part_name', { section: g.n })), svg(faceSvg(status, 40))),
          h('span', { class: 'word' }, T('lbl.each_part.status.' + status)),
          !mock && s.wetness != null ? h('span', null, T('each_part.how_wet', { wetness: s.wetness })) : h('span', null, T('btn.not_ready')),
          !mock && s.temp != null ? h('span', { class: 'small' }, T('each_part.how_warm', { temp: s.temp })) : null,
          h('span', { class: 'small' }, T('each_part.how_sure', { sure_pct: (s.sure || 0) * 100 })),
          (s.sure || 0) < 0.5 ? fogTag() : null,
          greenerMark(s.greener), s.low_ground === true ? h('span', { class: 'mark' }, svg(I('low', 16)), T('each_part.low_ground')) : null,
          fogLayer(s.sure));
        return c;
      }));
      return screen('today', {
        head: [bigTitle(T('each_part.today_h1'), T('each_part.today_h2')), isPlaceholder(F.field.name) ? sampleChip() : null],
        scene: fieldBox(F, 'status'),
        body: [h('div', { class: 'row wrap' }, F.field.status_date ? h('span', { class: 'chip' }, T('each_part.as_of') + ' ' + fmtDate(F.field.status_date)) : null, srcs(F, ['twin'])),
          cards,
          h('div', { class: 'card soft' }, lines([T('each_part.faces'), T('each_part.fog'), T('each_part.one_soil'), T('parts.stick_tells')], 'sub'))],
        cta: cta(T('what_to_grow.next_h1') + ' ' + T('what_to_grow.next_h2'), function () { go('next'); })
      });
    });
  };

  // ---------------- 7 next 3 months, and the three plans ----------------
  function monthRow(F, key) {
    var m = (F.diary.months || []).filter(function (x) { return x.m === key; })[0];
    if (!m) return null;
    var icon = m.frost === 'high' || m.frost === 'risk' ? 'snow' : (m.rain === 'high' ? 'rain' : (m.rain === 'medium' ? 'cloud' : 'sun'));
    var less = m.cover_sure != null && m.cover_sure < 0.9;
    function bit(ic_, grp, val) { return h('span', { class: 'chip', style: 'background:#F7F1E4;color:var(--ink);font-weight:600' }, svg(I(ic_, 15)), T('lbl.from_space.' + grp + '.' + val)); }
    var coverChip = bit('sprout', 'cover', m.cover);
    if (less) { coverChip.classList.add('fogwrap'); coverChip.append(fogLayer(m.cover_sure)); }
    return h('div', { class: 'mrow' },
      h('span', { class: 'mic', style: 'color:' + (icon === 'sun' ? '#D27A2C' : '#14301E') }, svg(I(icon, 28))),
      h('div', { class: 'grow', style: 'display:flex;flex-direction:column;gap:6px' },
        h('span', { class: 'mname', style: 'width:auto' }, monthName(key)),
        h('span', { class: 'small', style: 'font-weight:700' }, T('from_space.usually')),
        h('div', { class: 'row wrap', style: 'gap:6px' }, bit('rain', 'rain', m.rain), bit('soil', 'soil', m.soil), bit('therm', 'heat', m.heat),
          m.frost !== 'none' ? bit('snow', 'frost', m.frost) : null, coverChip),
        less ? h('span', { class: 'fogtag' }, svg(I('fog', 16)), T('from_space.month_less_sure')) : null));
  }
  function planCard(F, p, cur, i) {
    var isCur = p.id === 'current', ns = nextSow(p);
    var hr = scoreRange(p, 'harvest'), wr = scoreRange(p, 'water');
    var open = function () { go('plan/' + p.id); };
    return h('article', { class: 'plan' + (isCur ? ' now' : ''), style: 'animation-delay:' + (100 + i * 140) + 'ms', onclick: open },
      h('button', { type: 'button', class: 'go', 'aria-label': planName(p), onclick: function (e) { e.stopPropagation(); open(); } }, svg(ic(P_.arrow, 20, 2.6), 'lime')),
      h('span', { class: 'pname', style: 'padding-right:52px' }, planName(p)),
      h('span', { class: 'crops' }, cropsLine(p)),
      ns ? h('span', { class: 'small', style: 'color:var(--ink)' }, h('b', null, T('what_to_grow.next_to_plant')), ' ',
        T('your_plan.plant_in', { crop: crop(ns.c.crop), sow_month: monthName(MONTHS[ns.d.getMonth()]) })) : null,
      h('div', { class: 'score' }, h('span', { class: 'lbl' }, T('lbl.what_to_grow.score.harvest')), pics(p.score.harvest, 'basket', 16),
        h('span', { class: 'num' }, rng(hr[0], hr[1]), ' ', h('small', null, T('btn.out_of_100'))), isCur ? null : vsChip(vsNow(p, cur, 'harvest'))),
      h('div', { class: 'score' }, h('span', { class: 'lbl' }, T('lbl.what_to_grow.score.water')), pics(p.score.water, 'drop', 18),
        h('span', { class: 'num', style: 'font-size:20px' }, rng(wr[0], wr[1]), ' ', h('small', null, T('btn.out_of_100')))),
      srcs(F, ['twin']));
  }
  // the choices in the order shown: the current one, then the others (by the farmer's priority, when given)
  function orderedPlans(F) {
    var ps = effPlans(F), cur = ps.filter(function (p) { return p.id === 'current'; })[0] || ps[0];
    var rest = ps.filter(function (p) { return p !== cur; });
    if (S.prio) { var k = { harvest: 'harvest', water: 'water', soil: 'soil_kept' }[S.prio]; rest.sort(function (a, b) { return b.score[k] - a.score[k]; }); }
    return { cur: cur, rest: rest };
  }
  function prioChips(onchange) {
    var prio = h('div', { class: 'prio', role: 'group', 'aria-label': T('what_to_grow.priority_q') }, ['harvest', 'water', 'soil'].map(function (k) {
      return h('button', { type: 'button', class: 'choice', 'aria-pressed': String(S.prio === k), onclick: function (e) {
        S.prio = S.prio === k ? null : k;
        [].forEach.call(prio.children, function (b) { b.setAttribute('aria-pressed', 'false'); });
        if (S.prio) e.currentTarget.setAttribute('aria-pressed', 'true');
        onchange();
      } }, svg(I(k === 'harvest' ? 'sprout' : k === 'water' ? 'drop' : 'soil', 18)), T('lbl.what_to_grow.priority.' + k));
    }));
    return prio;
  }
  function spanTabs(n) {
    return h('div', { class: 'tabs', role: 'tablist', style: 'margin-bottom:10px' }, [3, 6].map(function (k) {
      return h('button', { type: 'button', role: 'tab', 'aria-selected': String(n === k), onclick: function () { location.replace('#/next/' + k); } },
        T(k === 6 ? 'what_to_grow.next_h2_6' : 'what_to_grow.next_h2'));
    }));
  }
  SCREENS.next = function (arg) {
    var n = arg === '6' ? 6 : arg === '3' ? 3 : (S.nextN || 3);
    S.nextN = n;
    return withField('next', n === 6 ? six : function (F) {
      var span = 'what_to_grow.next_h2';
      var keys = nextMonths(n), months = keys.map(function (k) { return monthRow(F, k); });
      var monsoon = keys.some(function (k) { return k === 'Jun' || k === 'Jul'; }) && F.diary.monsoon_start;
      var frost = (F.diary.months || []).some(function (m) { return keys.indexOf(m.m) >= 0 && m.frost !== 'none'; });
      var monthCard = h('div', { class: 'card', style: 'animation:ks-reveal 800ms var(--ease) 100ms both;padding:4px 16px' }, months,
        monsoon ? h('div', { class: 'fact' }, h('span', { class: 'ic' }, svg(I('rain', 20))), h('div', { class: 'grow' }, lines(PL(F.diary.monsoon_start.words)), srcs(F, [F.diary.shift_source || 'dhm']))) : null);
      var plansBox = h('div', { style: 'display:flex;flex-direction:column;gap:12px' });
      function drawPlans() {
        var o = orderedPlans(F);
        plansBox.textContent = '';
        [o.cur].concat(o.rest).forEach(function (p, i) { plansBox.append(planCard(F, p, o.cur, i)); });
      }
      drawPlans();
      var prio = prioChips(drawPlans);
      return screen('next', {
        head: [bigTitle(T('what_to_grow.next_h1'), T(span)), isPlaceholder(F.field.name) ? sampleChip() : null],
        scene: [spanTabs(n), h('p', { class: 'sub', style: 'font-weight:600;color:var(--ink);margin-bottom:8px' }, T('home.card_months_sub')), monthCard,
          h('div', { style: 'height:8px' }), srcs(F, ['gpm', 'power', 'hls', 'twin']),
          h('p', { class: 'small' }, frost ? T('from_space.frost_note') + ' ' : '', T('from_space.months_note'))],
        body: [h('h2', { class: 'h2' }, T('what_to_grow.choices_title')), h('p', { class: 'sub' }, T('what_to_grow.tap_choice')),
          h('p', { class: 'sub', style: 'font-weight:700;color:var(--ink)' }, T('what_to_grow.priority_q')), prio,
          plansBox,
          h('p', { class: 'small' }, T('what_to_grow.more_baskets'), ' ', T('what_to_grow.more_drops'), ' ', T('what_to_grow.range_why'), hasDhm(F) ? ' ' + T('what_to_grow.range_town') : ''),
          h('p', { class: 'note' }, T('your_plan.know_best'), ' ', T('your_plan.advisor'), ' ', T('your_plan.small_first'))],
        cta: [btn3(T('btn.how_we_know'), function () { go('how'); }, 'book'), btn2(T('your_plan.again'), function () { go('home'); }, 'redo')]
      });
    });
  };
  // #/next/3 and #/next/6 switch the view in place (the tabs replace the address, so Back still leads to "What do you want to see?")
  SCREENS.next.onArg = function (a) { if (a === S.arg) return; S.arg = a; rerender(); W.scrollTo(0, 0); };

  // ---------------- 7b next 6 months: one choice step by step, and the field month by month (design Future6) ----------------
  // Crop seasons come from each plan's crops (start and end, MM-DD); a month counts as empty when most of its days have no crop.
  var CUM = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334], MDAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
  function doy(mmdd) { return CUM[+mmdd.slice(0, 2) - 1] + (+mmdd.slice(3, 5)) - 1; }
  function covers(c, d) { var a = doy(c.start), b = doy(c.end); return a <= b ? d >= a && d <= b : d >= a || d <= b; }
  function cropOn(p, d) { for (var i = 0; i < p.crops.length; i++) if (covers(p.crops[i], d)) return p.crops[i].crop; return null; }
  function monthRuns(p, key) {
    var mi = MONTHS.indexOf(key), runs = [];
    for (var d = 0; d < MDAYS[mi]; d++) { var c = cropOn(p, CUM[mi] + d), last = runs[runs.length - 1]; if (last && last[0] === c) last[1]++; else runs.push([c, 1]); }
    return runs;
  }
  function mainCrop(runs) { var t = {}, n = 0; runs.forEach(function (r) { t[r[0]] = (t[r[0]] || 0) + r[1]; n += r[1]; }); var best = null; Object.keys(t).forEach(function (k) { if (k !== 'null' && t[k] * 2 > n) best = k; }); return best; }
  // the plan's crops in the order they come, from the first day of the window (a crop already in the ground comes first)
  function cropsFrom(p, d0) {
    return p.crops.map(function (c) { return { c: c, k: covers(c, d0) ? -1 : (doy(c.start) - d0 + 365) % 365 }; })
      .sort(function (x, y) { return x.k - y.k; }).map(function (x) { return x.c; });
  }
  function explainersFor(id) { var ex = (S.words && S.words.crop_explainers) || {}; return Object.keys(ex).map(function (k) { return ex[k]; }).filter(function (e) { return (e.examples || []).indexOf(id) >= 0; }); }
  function cap(s) { return /^(ne|hi|bn)$/.test(S.lang) ? s : s.charAt(0).toUpperCase() + s.slice(1); }
  var CROP_COL = ['#C8E05A', '#F0AE4C', '#9CC8E3', '#E6B8DA'];
  function six(F) {
    var keys = nextMonths(6), d0 = CUM[MONTHS.indexOf(keys[0])], DM = F.diary.months || [];
    var frost = DM.some(function (m) { return keys.indexOf(m.m) >= 0 && m.frost !== 'none'; });
    var monsoon = keys.some(function (k) { return k === 'Jun' || k === 'Jul'; }) && F.diary.monsoon_start;
    var tiles = h('div', { class: 'wtiles' }, keys.map(function (k, i) {
      var m = DM.filter(function (x) { return x.m === k; })[0], mn = node('month.' + k), g = S.lang === 'ne' && mn ? (mn.ne.match(/\(([^)]+)\)/) || [])[1] : null;
      var head = [h('span', { class: 'wm' }, monthShort(k)), g ? h('span', { class: 'wg' }, g) : null];
      if (!m) return h('div', { class: 'wtile' }, head, h('span', { class: 'wl' }, T('btn.not_ready')));
      var icon = m.frost === 'high' || m.frost === 'risk' ? 'snow' : (m.rain === 'high' ? 'rain' : (m.rain === 'medium' ? 'cloud' : 'sun'));
      return h('div', { class: 'wtile', style: 'animation-delay:' + (120 + i * 60) + 'ms' }, head,
        h('span', { style: 'color:' + (icon === 'sun' ? '#D27A2C' : 'var(--ink)') }, svg(I(icon, 24))),
        h('span', { class: 'wl' }, T('lbl.from_space.rain.' + m.rain)),
        m.frost !== 'none' ? h('span', { class: 'wl' }, T('lbl.from_space.frost.' + m.frost)) : (m.heat !== 'none' ? h('span', { class: 'wl' }, T('lbl.from_space.heat.' + m.heat)) : null));
    }));
    var weather = h('div', { class: 'card', style: 'display:flex;flex-direction:column;gap:10px;animation:ks-reveal 800ms var(--ease) 100ms both' },
      h('h3', { class: 'h3' }, T('home.card_months_sub')), tiles,
      monsoon ? h('div', { class: 'fact' }, h('span', { class: 'ic' }, svg(I('rain', 20))), h('div', { class: 'grow' }, lines(PL(F.diary.monsoon_start.words)), srcs(F, [F.diary.shift_source || 'dhm']))) : null,
      srcs(F, ['gpm', 'power', 'hls', 'twin']),
      h('p', { class: 'small', style: 'margin:0' }, frost ? T('from_space.frost_note') + ' ' : '', T('from_space.months_note')));

    var choiceBox = h('div', { class: 'sixbox' }), fieldCard = h('div', { class: 'card', style: 'display:flex;flex-direction:column;gap:10px' }), otherBox = h('div', { class: 'sixbox' });
    function draw() {
      var o = orderedPlans(F), pick = o.rest[0] || o.cur, rest = [o.cur].concat(o.rest).filter(function (p) { return p !== pick; });
      // one choice, step by step
      var steps = [];
      cropsFrom(pick, d0).forEach(function (c, i) {
        var ex = explainersFor(c.crop);
        if (i) steps.push(h('span', { class: 'stepjoin', 'aria-hidden': 'true' }, svg(I('down', 16, 2.6))));
        steps.push(h('div', { class: 'step' + (i % 2 ? ' then' : ''), style: 'animation-delay:' + (200 + i * 160) + 'ms' },
          h('span', { class: 'sl' }, T(i ? 'what_to_grow.step_then' : 'what_to_grow.step_first')),
          h('span', { class: 'sc' }, cap(crop(c.crop))),
          ex.length ? h('ul', { class: 'why' }, ex.map(function (e) { return h('li', null, svg(I('tick', 16, 2.6)), L(e.title)); })) : null,
          h('span', { class: 'when' }, T('your_plan.plant_in', { crop: crop(c.crop), sow_month: monthName(MONTHS[+c.start.slice(0, 2) - 1]) }), h('br'),
            T('your_plan.harvest_in', { crop: crop(c.crop), harvest_month: monthName(MONTHS[+c.end.slice(0, 2) - 1]) }))));
      });
      var hr = scoreRange(pick, 'harvest'), wr = scoreRange(pick, 'water');
      var open = function () { go('plan/' + pick.id); };
      choiceBox.textContent = '';
      add(choiceBox, [h('p', { class: 'sub', style: 'font-weight:700;color:var(--ink)' }, T('what_to_grow.six_pick')),
        h('h2', { class: 'h2' }, planName(pick)), h('div', { class: 'steps6' }, steps),
        h('button', { type: 'button', class: 'card pickscore', onclick: open },
          h('div', { class: 'score' }, h('span', { class: 'lbl' }, T('lbl.what_to_grow.score.harvest')), pics(pick.score.harvest, 'basket', 16),
            h('span', { class: 'num' }, rng(hr[0], hr[1]), ' ', h('small', null, T('btn.out_of_100'))), pick === o.cur ? null : vsChip(vsNow(pick, o.cur, 'harvest'))),
          h('div', { class: 'score' }, h('span', { class: 'lbl' }, T('lbl.what_to_grow.score.water')), pics(pick.score.water, 'drop', 18),
            h('span', { class: 'num', style: 'font-size:20px' }, rng(wr[0], wr[1]), ' ', h('small', null, T('btn.out_of_100')))),
          h('span', { class: 'row', style: 'justify-content:space-between;font-weight:700;font-size:14px' }, T('what_to_grow.tap_choice'), svg(I('arrow', 20, 2.6)))),
        srcs(F, ['twin', 'gpm', 'power'])]);
      // the field month by month: now, and with this choice
      var rows = pick === o.cur ? [[T('what_to_grow.now_short'), o.cur]] : [[T('what_to_grow.now_short'), o.cur], [T('what_to_grow.this_choice'), pick]];
      var seen = [];
      rows.forEach(function (r) { keys.forEach(function (k) { monthRuns(r[1], k).forEach(function (x) { if (x[0] && seen.indexOf(x[0]) < 0) seen.push(x[0]); }); }); });
      var letters = seen.map(function (c) { return crop(c).charAt(0).toUpperCase(); });
      letters = seen.map(function (c, i) { return letters.indexOf(letters[i]) !== letters.lastIndexOf(letters[i]) ? cap(crop(c)).slice(0, 2) : letters[i]; });
      function col(c) { return CROP_COL[seen.indexOf(c) % CROP_COL.length]; }
      var said = rows.map(function (r) {
        return r[0] + ': ' + keys.map(function (k) { var c = mainCrop(monthRuns(r[1], k)); return monthName(k, true) + ' ' + crop(c || 'bare'); }).join(', ');
      }).join('. ');
      var grid = h('div', { class: 'tline', role: 'img', 'aria-label': said },
        h('div', { class: 'trow', 'aria-hidden': 'true' }, h('span', { class: 'tl' }), keys.map(function (k) { return h('span', { class: 'tm' }, monthShort(k)); })),
        rows.map(function (r, ri) {
          return h('div', { class: 'trow', 'aria-hidden': 'true' }, h('span', { class: 'tl' }, r[0]), keys.map(function (k, i) {
            var runs = monthRuns(r[1], k), big = runs.filter(function (x) { return x[0]; }).sort(function (a, b) { return b[1] - a[1]; })[0];
            return h('span', { class: 'tc', style: 'animation-delay:' + (500 + ri * 200 + i * 70) + 'ms' }, runs.map(function (x) {
              return h('i', { style: 'flex:' + x[1] + (x[0] ? ';background:' + col(x[0]) : '') }, x[0] && x === big && x[1] >= 12 ? letters[seen.indexOf(x[0])] : null);
            }));
          }));
        }));
      var legend = h('div', { class: 'legend' }, seen.map(function (c, i) {
        return h('span', null, h('span', { class: 'sw lt', style: 'background:' + col(c) }, letters[i]), crop(c));
      }), h('span', null, h('span', { class: 'sw lt empty' }), crop('bare')));
      var empties = rows.map(function (r) { return r[0] + ' ' + num(keys.filter(function (k) { return !mainCrop(monthRuns(r[1], k)); }).length); }).join(' · ');
      fieldCard.textContent = '';
      add(fieldCard, [h('h3', { class: 'h3' }, T('what_to_grow.field_6')), grid, legend,
        h('p', { style: 'margin:0;font-weight:700;font-size:14px' }, T('what_to_grow.empty_months') + ' ' + empties), srcs(F, ['twin', 'hls'])]);
      // the other choices
      otherBox.textContent = '';
      add(otherBox, [h('h2', { class: 'h3' }, T('what_to_grow.other_choices')),
        h('div', { class: 'card olist' }, rest.map(function (p) {
          var r = scoreRange(p, 'harvest');
          return h('button', { type: 'button', class: 'orow', onclick: function () { go('plan/' + p.id); } },
            h('span', { class: 'grow', style: 'display:flex;flex-direction:column;gap:4px' }, h('span', { class: 'on' }, planName(p)), h('span', { class: 'crops' }, cropsLine(p)),
              h('span', { class: 'score' }, pics(p.score.harvest, 'basket', 14), h('span', { style: 'font-weight:800' }, rng(r[0], r[1]), ' ', h('small', { class: 'small' }, T('btn.out_of_100'))),
                p === o.cur ? null : vsChip(vsNow(p, o.cur, 'harvest')))),
            svg(I('arrow', 20, 2.6)));
        }))]);
    }
    draw();
    var sc = screen('next', {
      head: [bigTitle(T('what_to_grow.next_h1'), T('what_to_grow.next_h2_6')), isPlaceholder(F.field.name) ? sampleChip() : null],
      scene: [spanTabs(6), weather, h('div', { style: 'height:14px' }), fieldCard],
      body: [h('p', { class: 'sub', style: 'font-weight:700;color:var(--ink)' }, T('what_to_grow.priority_q')), prioChips(draw), choiceBox, otherBox,
        h('p', { class: 'small' }, T('what_to_grow.more_baskets'), ' ', T('what_to_grow.more_drops'), ' ', T('what_to_grow.range_why'), hasDhm(F) ? ' ' + T('what_to_grow.range_town') : ''),
        h('p', { class: 'note' }, T('your_plan.know_best'), ' ', T('your_plan.advisor'), ' ', T('your_plan.small_first'))],
      cta: [btn3(T('btn.how_we_know'), function () { go('how'); }, 'book'), btn2(T('your_plan.again'), function () { go('home'); }, 'redo')]
    });
    sc.classList.add('six');
    return sc;
  }

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
  function closeSheetNav() { if (/^#\/plan\//.test(location.hash)) { if (S.cur) go(S.cur); else go('next'); } else closeSheet(); }
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
          isPlaceholder(F.field.name) ? sampleChip() : null,
          h('div', { style: 'display:flex;flex-direction:column;gap:14px;margin-top:10px' },
            p.id === 'current' && F.current_options ? h('div', { class: 'card' }, winterQuestion(F, function () { build(true); })) : null,
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
  function loadFonts() {
    D.head.append(h('link', { rel: 'stylesheet', href: 'https://fonts.googleapis.com/css2?family=Inter+Tight:wght@700;800;900&family=Inter:wght@400;500;600;700&family=Mukta:wght@400;700&display=swap' }));
  }
  function init() {
    grass();
    S.winter = store.get('winter'); S.water = store.get('water');
    var t0 = Date.now();
    Promise.all([getJSON('data/words.json'), getJSON('data/index.json')]).then(function (r) {
      S.words = r[0]; S.index = r[1];
      var cur = $('#curtain');
      if (!S.words) { cur.append(h('button', { type: 'button', class: 'round', style: 'position:absolute;bottom:40px', 'aria-label': 'reload', onclick: function () { location.reload(); } }, svg(I('redo', 22)))); return; }
      var want = store.get('lang') || 'ne';
      S.lang = langInfo(want) ? want : 'ne';
      D.documentElement.lang = S.lang;
      var ids = ((S.index && S.index.fields) || []).map(function (f) { return f.id; });
      var fid = store.get('fid');
      S.fid = ids.indexOf(fid) >= 0 ? fid : (ids[0] || 'demo');
      W.addEventListener('hashchange', onRoute);
      onRoute();
      setTimeout(function () {
        cur.classList.add('lift');
        setTimeout(function () { cur.remove(); }, RM ? 0 : 1000);
      }, RM ? 0 : Math.max(0, 900 - (Date.now() - t0)));
      var idle = W.requestIdleCallback || function (f) { return setTimeout(f, 300); };
      idle(function () { fieldReady(); });
      if (D.readyState === 'complete') loadFonts(); else W.addEventListener('load', loadFonts);
    });
  }
  W.KS = { S: S, h: h, add: add, svg: svg, ic: ic, I: I, T: T, L: L, P: P, PL: PL, num: num, digits: digits, rng: rng, crop: crop, lines: lines, node: node, scr: scr,
    srcTag: srcTag, srcs: srcs, srcObj: srcObj, effPlans: effPlans, planName: planName, alts: alts, yearRange: yearRange, hasDhm: hasDhm, scoreRange: scoreRange,
    waterCases: waterCases, pics: pics, basketSvg: basketSvg, getJSON: getJSON, loadLeaflet: loadLeaflet, osm: osm, go: go, notReady: notReady, loading: loading,
    sampleChip: sampleChip, isPlaceholder: isPlaceholder, sourcesList: sourcesList, mocked: mocked, fogLayer: fogLayer, langInfo: langInfo, monthName: monthName,
    MONTHS: MONTHS, RM: RM, later: later, sentences: sentences, btn3: btn3, vsChip: vsChip };
  if (D.readyState === 'loading') D.addEventListener('DOMContentLoaded', init); else init();
})();
