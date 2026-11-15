/* Khet Sathi: the "How we know" page, loaded only when it is first opened. Charts are inline SVG or plain HTML bars
   drawn here from site/data/story.json and the field file; every label is set with textContent. No chart library,
   no outside service. */
(function () {
  'use strict';
  var K = window.KS, h = K.h, T = K.T, L = K.L, P = K.P, PL = K.PL, num = K.num, digits = K.digits, rng = K.rng, svg = K.svg, I = K.I, S = K.S;
  var NS = 'http://www.w3.org/2000/svg';
  function s(tag, a, text) {
    var el = document.createElementNS(NS, tag);
    if (a) Object.keys(a).forEach(function (k) { if (a[k] != null) el.setAttribute(k, a[k]); });
    if (text != null) el.textContent = text;
    return el;
  }
  function section(id, title, kids) { return h('section', { id: 'how-' + id }, h('h2', { class: 'h2' }, title), kids); }
  function sub(title, kids) { return h('div', { style: 'display:flex;flex-direction:column;gap:6px;padding-top:6px' }, h('h3', { class: 'h3' }, title), kids); }
  function said(text) { return K.lines(K.sentences(text), 'sub'); }
  // a number on a chart: whole numbers from 10 up, two decimals below (method charts only; plans never show decimals)
  function fv(v) { if (v == null || isNaN(v)) return ''; var a = Math.abs(v); return digits(a >= 10 ? Math.round(v) : a >= 1 ? +v.toFixed(2) : +v.toPrecision(2)); }

  K.how = function (F) {
    // the version stamp (data/version.json, written by scripts/final_check.py); nothing when it is not there
    var version = h('p', { class: 'small' });
    K.getJSON('data/version.json').then(function (v) {
      if (!v || !v.commit_short) return;
      version.textContent = T('your_plan.version') + ' ' + v.commit_short + (v.checked_on ? ', ' + T('your_plan.version_checked') + ' ' + K.fmtDate(v.checked_on) : '') +
        (v.uncommitted_changes ? ' (' + T('your_plan.version_unsaved') + ')' : '');
    });
    var root = h('div', { class: 'how' });
    var toc = h('nav', { class: 'prio', 'aria-label': T('btn.how_we_know') });
    root.append(h('div', { class: 'row wrap' }, K.isPlaceholder(F.field.name) ? K.sampleChip() : null, h('span', { class: 'small' }, F.field.name)),
      // first, the field twin in three pictures, then the 24 seasons played for each plan (owner, 2026-11-14 evening)
      twinPics(), animBox(F), toc);
    var storyBox = h('div', { style: 'display:flex;flex-direction:column;gap:16px' });
    var areaBox = h('div'), nr = h('div');
    // for judges: everything that is not on the farmer's seven screens (owner, 2026-11-14 evening), each from its own file
    var judges = h('div', { style: 'display:flex;flex-direction:column;gap:16px' });
    // every label and its why first, then the numbers and evidence that left the farmer's screens
    var J = [['labels', T('your_plan.lab_title'), null], ['plans', T('what_to_grow.three'), null], ['compare', T('last_years.cmp_title'), 'simple'],
      ['squares', T('last_years.replay_name', { year_count: (K.effPlans(F)[0].replay || []).length }), 'replay'], ['weather', T('weather.title'), null],
      ['checkup', T('your_plan.check_name'), 'checkup'], ['rainrisk', T('last_years.rr_title'), 'rainrisk'], ['heatclock', T('last_years.hc_title'), 'heatclock'],
      ['fertiliser', T('what_to_grow.fs_title'), 'fertiliser'], ['twin', T('each_part.twin_title'), null], ['pulse', T('from_space.pulse_name'), 'pulse'],
      ['fields', T('home.prepared_title'), null]];
    var BUILD = { compare: 'verdicts', squares: 'replay', checkup: 'checkup', rainrisk: 'rainRisk', heatclock: 'heatClock', fertiliser: 'fertiliser', pulse: 'pulse' };
    K.features().then(function () {
      J.forEach(function (j) {
        var sec = section(j[0], j[1], loadingEl()); judges.append(sec);
        var body = sec.lastChild;
        function put(el) { body.replaceWith(el || K.notReady()); }
        if (j[0] === 'fields') { put(K.fieldsList('how')); return; }
        if (j[0] === 'twin') { put(K.feat.twinParts(F)); return; }
        if (j[0] === 'labels') { put(K.feat.labelsList()); return; }
        if (j[0] === 'plans') { put(plansList(F)); return; }
        if (j[0] === 'weather') { put(weatherDetails(F)); return; }
        K.featData(j[2]).then(function (d) { put(d ? K.feat[BUILD[j[0]]](F, d) : null); });
      });
    });
    function loadingEl() { return h('div', null, K.loading()); }
    var mine = [judges, replay(F), future(F), method(F), areaBox, helped(), section('sources', T('your_plan.sources_title'), [K.sourcesList(F), version,
      // the acknowledgement NASA GIBS asks for, beside the map pictures (NASA HLS, NASA Blue Marble); kept in its own words
      h('p', { class: 'small', lang: 'en' }, 'We acknowledge the use of imagery provided by services from NASA\u2019s Global Imagery Browse Services (GIBS), part of NASA\u2019s Earth Science Data and Information System (ESDIS).')]), glossary(), nr];
    // the labels and the evidence that left the farmer's screens first, then the chapters of story.json
    mine.splice(1, 0, storyBox);
    var bh = K.behindBox(); mine.unshift(bh);   // first for judges: "Behind the scenes: your field, seen by NASA" (js/behind.js)
    mine.forEach(function (x) { root.append(x); });
    function addToc(id, title) { toc.append(h('a', { class: 'btn3', href: '#/how/' + id, style: 'min-height:40px;font-size:13px' }, title)); }
    K.getJSON('data/story.json').then(function (st) {
      if (!storyBox.isConnected) return;
      var hasArea = false;
      if (bh.isConnected) addToc('behind', T('farm.behind_title'));   // gone when there is none for this field
      J.forEach(function (j) { addToc(j[0], j[1]); });
      if (st) {
        story(F, st).forEach(function (x) { storyBox.append(x.el); addToc(x.id, x.title); });
        hasArea = (st.charts || []).some(function (c) { return c.kind === 'map' && c.link; });
      }
      [['replay', L(K.scr('last_years').title, { year_count: (K.effPlans(F)[0].replay || []).length })], ['future', T('your_plan.future_title')], ['method', T('your_plan.method_title')],
        ['sources', T('your_plan.sources_title')], ['notready', T('your_plan.not_ready_title')]].forEach(function (x) { addToc(x[0], x[1]); });
      var ar = K.indexEntry().area;   // the area map this field shares (index.json area), if any
      if (!hasArea && ar) K.getJSON('data/area/' + encodeURIComponent(ar) + '.json').then(function (a) { if (a && areaBox.isConnected) areaBox.append(section('area', T('your_plan.area_title'), area(F, a))); });
    });
    K.probeData().then(function (pd) { if (!nr.isConnected) return; var t = stickTest(pd); if (t) nr.append(t); nr.append(notReady(F, pd)); });
    return root;
  };

  // ---------------- the field twin in three pictures (owner, 2026-11-14 evening); pictures drawn here, words from words.json ----------------
  var TWIN_PIC = [
    // 1 a copy of your field in the computer: soil, a crop and water
    '<svg width="120" height="96" viewBox="0 0 120 96"><rect x="12" y="8" width="96" height="66" rx="8" fill="#14301E"/><rect x="18" y="14" width="84" height="54" rx="4" fill="#F3EAD8"/>' +
      '<rect x="18" y="46" width="84" height="22" fill="#B08A5C"/><rect x="18" y="56" width="84" height="12" fill="#8A6640"/><path d="M60 46V30" stroke="#5E8A3A" stroke-width="2.4"/>' +
      '<path d="M60 36c-6-1-9-5-9-10 6 0 9 4 9 10z" fill="#7FB24A"/><path d="M60 32c5-1 8-5 8-10-5 0-8 4-8 10z" fill="#93C258"/><path d="M84 22s-6 7-6 11a6 6 0 0012 0c0-4-6-11-6-11z" fill="#2F6E99"/>' +
      '<path d="M46 82h28M60 74v8" stroke="#14301E" stroke-width="3" stroke-linecap="round"/></svg>',
    // 2 NASA's weather replayed: a satellite over a grid of past years, one plan running through them
    '<svg width="120" height="96" viewBox="0 0 120 96"><g transform="translate(96 12) rotate(-20)"><rect x="-5" y="-4" width="10" height="8" rx="1.5" fill="#14301E"/><rect x="-18" y="-3" width="11" height="6" fill="#2F6E99"/><rect x="7" y="-3" width="11" height="6" fill="#2F6E99"/></g>' + (function () {
      var o = '';
      for (var r = 0; r < 4; r++) for (var c = 0; c < 6; c++) o += '<rect x="' + (6 + c * 14) + '" y="' + (26 + r * 17) + '" width="11" height="13" rx="2.5" fill="' + ((r * 6 + c) % 7 === 3 ? '#F0AE4C' : '#C8E05A') + '" stroke="#14301E" stroke-width="1"/>';
      return o;
    })() + '<path d="M4 64 C24 52 40 74 58 60 S84 50 92 58" fill="none" stroke="#9A5426" stroke-width="3" stroke-linecap="round"/><path d="M90 20 L80 40" stroke="#9A5426" stroke-width="1.6" stroke-dasharray="3 3"/></svg>',
    // 3 the plan that works most often wins; then what to do, on the phone
    '<svg width="120" height="96" viewBox="0 0 120 96"><rect x="4" y="44" width="22" height="30" rx="4" fill="#E9B7A6" stroke="#14301E" stroke-width="1.4"/><path d="M10 54l10 10M20 54l-10 10" stroke="#B8432A" stroke-width="2.6" stroke-linecap="round"/>' +
      '<rect x="30" y="30" width="26" height="44" rx="4" fill="#C8E05A" stroke="#14301E" stroke-width="1.6"/><path d="M36 52l5 5 9-11" stroke="#14301E" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>' +
      '<path d="M43 14l3 6 6 1-4.5 4 1 6-5.5-3-5.5 3 1-6-4.5-4 6-1z" fill="#F0AE4C"/>' +
      '<rect x="60" y="44" width="22" height="30" rx="4" fill="#E9B7A6" stroke="#14301E" stroke-width="1.4"/><path d="M66 54l10 10M76 54l-10 10" stroke="#B8432A" stroke-width="2.6" stroke-linecap="round"/>' +
      '<rect x="88" y="18" width="28" height="56" rx="6" fill="#14301E"/><rect x="92" y="24" width="20" height="42" rx="3" fill="#FBF4EA"/><path d="M96 36h12M96 44h12M96 52h8" stroke="#5E8A3A" stroke-width="2.4" stroke-linecap="round"/></svg>'
  ];
  function twinPics() {
    var n = (K.effPlans(K.S.field)[0].replay || []).length;
    var said = [['farm.twin3_1', null], ['farm.twin3_2', 'farm.twin3_2b'], ['farm.twin3_3', 'farm.twin3_3b']];
    return section('twinpics', T('twin.h1'), h('ol', { class: 'twinsteps three' }, said.map(function (x, i) {
      return h('li', { class: 'tstep', style: 'animation-delay:' + (100 + i * 140) + 'ms' }, h('span', { class: 'tn' }, num(i + 1)), svg(TWIN_PIC[i], 'tpic'),
        h('p', { class: 'tt' }, h('b', null, T(x[0], { year_count: n })), x[1] ? [' ', h('span', null, T(x[1]))] : null));
    })));
  }

  // ---------------- the 24 seasons, played for each plan in about ten seconds (site/data/simple/<id>.json animation) ----------------
  // One small field per plan, side by side: green with a tick when the plan did not fail that season, red with a cross when
  // it failed; a dot for every season below it; at the end the winner (the back end's choice) is marked. Never colour alone.
  var FIELD_PIC = '<svg width="96" height="64" viewBox="0 0 96 64"><path d="M4 50 L48 62 L92 50 L48 38Z" fill="currentColor" stroke="#14301E" stroke-width="1.6"/>' +
    '<path d="M18 50l30 8M30 47l30 8M42 44l30 8M54 41l26 7" stroke="#14301E" stroke-opacity=".25" stroke-width="1.4"/></svg>';
  function animBox(F) {
    var box = section('seasons', T('farm.anim_title'), h('div', null, K.loading()));
    K.featData('simple').then(function (sd) {
      var an = sd && sd.animation, body = box.lastChild;
      if (!an || !an.plans || !(an.seasons || []).length) { box.remove(); return; }   // a field without the replay (abroad): no animation
      var n = an.seasons.length, i = -1, tiles = [];
      // true: did not fail; false: failed; null: no result that season (grey, no mark)
      function green(p, k) { var g = (p.green || [])[k]; return g == null ? null : !!g; }
      var year = h('p', { class: 'anyear', 'aria-hidden': 'true' });
      var row = h('div', { class: 'anrow' }, an.plans.map(function (p) {
        var t = { p: p, tile: h('div', { class: 'antile' }), dots: h('div', { class: 'andots' }), cnt: h('span', { class: 'ancnt' }), ok: 0 };
        t.tile.innerHTML = FIELD_PIC; t.mark = h('span', { class: 'anmark' }); t.tile.append(t.mark);
        tiles.push(t);
        return h('div', { class: 'ancol' }, h('b', { class: 'anname' }, K.planName(F.plans.filter(function (x) { return x.id === p.id; })[0] || { id: p.id })), t.tile, t.cnt, t.dots);
      }));
      var end = h('p', { class: 'lead anend', 'aria-live': 'polite' });
      function stepTo(k) {
        year.textContent = digits(an.seasons[k]);
        tiles.forEach(function (t) {
          var ok = green(t.p, k), cls = ok == null ? 'na' : ok ? 'ok' : 'bad'; if (ok) t.ok++;
          t.tile.className = 'antile ' + cls; t.mark.innerHTML = ok == null ? '' : K.I(ok ? 'tick' : 'cross', 20, 3);
          t.dots.append(h('i', { class: cls, title: digits(an.seasons[k]) }));
          t.cnt.textContent = num(t.ok) + ' / ' + num(k + 1);
        });
      }
      function finish() {
        tiles.forEach(function (t) { t.tile.parentNode.classList.toggle('win', t.p.id === an.winner); t.tile.parentNode.classList.toggle('lose', t.p.id !== an.winner); });
        end.textContent = T('farm.anim_winner') + ' ' + K.planName((F.plans || []).filter(function (p) { return p.id === an.winner; })[0] || { id: an.winner });
      }
      function play() {
        i = -1; end.textContent = '';
        tiles.forEach(function (t) { t.ok = 0; t.dots.textContent = ''; t.cnt.textContent = ''; t.tile.className = 'antile'; t.mark.textContent = ''; t.tile.parentNode.classList.remove('win', 'lose'); });
        if (K.RM) { for (var k = 0; k < n; k++) stepTo(k); finish(); return; }
        (function tick() { if (!box.isConnected) return; i++; if (i >= n) { finish(); return; } stepTo(i); K.later(tick, Math.round(10000 / n)); })();   // stops when its page is gone
      }
      body.replaceWith(h('div', { class: 'anim' }, year, row, end,
        h('div', { class: 'row wrap', style: 'justify-content:space-between' }, h('p', { class: 'small', style: 'margin:0' }, svg(K.I('tick', 14, 3)), ' ', T('farm.anim_green'), ' · ', svg(K.I('cross', 14, 3)), ' ', T('farm.anim_red')),
          h('button', { type: 'button', class: 'round', 'aria-label': T('farm.anim_title'), title: T('farm.anim_title'), onclick: play }, svg(K.I('redo', 20, 2.4))))));
      play();
    });
    return box;
  }

  // ---------------- the three plans' full details (scores, five tabs, tips): the sheet each plan opens ----------------
  function plansList(F) {
    return h('div', { class: 'prepared', style: 'display:flex;flex-direction:column;gap:8px' }, K.effPlans(F).map(function (p) {
      return h('button', { type: 'button', class: 'pf', onclick: function () { K.go('plan/' + p.id); } },
        h('span', null, h('b', null, K.planName(p)), h('br'), h('span', { class: 'small' }, K.cropsLine(p))), K.svg(K.I('arrow', 18)));
    }));
  }
  // ---------------- Weather ahead's details: the six blocks the farmer sees, each behind its Why? ----------------
  function weatherDetails(F) {
    var wx = F.weather; if (!wx || !wx.blocks) return null;
    return h('div', { style: 'display:flex;flex-direction:column;gap:8px' }, h('p', { class: 'sub' }, T('weather.top', { year_count: wx.years }) + ' ' + T('weather.not_forecast')),
      K.sixBlocks(wx).map(function (b) { return h('details', { class: 'why' }, h('summary', null, K.bsMonth(b.key)), K.weatherWhy(F, b)); }),
      h('p', { class: 'small', style: 'margin:0;font-weight:700' }, T('weather.sources')),
      K.lines((wx.sources || []).map(function (x) { return x.name + ' · ' + x.product + ' · ' + x.resolution + ' · ' + digits(x.years); }), 'small'),
      K.lines((wx.limits || []).map(function (x) { return x.name; }), 'small'));
  }

  // ---------------- the method in plain words ----------------
  var WAYS = { threshold: 'way_threshold', changepoint: 'way_changepoint', detective: 'way_detective' };
  function method(F) {
    var m = F.method || {}, d = F.diary || {}, kids = [];
    if (m.rain_correction && m.rain_correction.words) kids.push(sub(T('your_plan.rain_fix_title'), [said(P(m.rain_correction.words)), K.srcs(F, ['gpm', 'station'])]));
    var rains = [].concat(m.onset ? PL(m.onset.words) : [], d.monsoon_start ? PL(d.monsoon_start.words) : [], d.shift_note ? PL(d.shift_note) : []);
    if (rains.length) kids.push(sub(T('your_plan.rains_title'), [K.lines(rains, 'sub'), K.srcs(F, [d.shift_source || 'dhm', 'gpm'])]));
    var sd = m.season_detection;
    if (sd && sd.methods) {
      var rows = sd.methods.map(function (x) {
        return { label: WAYS[x.id] ? T('your_plan.' + WAYS[x.id]) : x.id, vals: [x.score * 100], tag: x.id === sd.chosen ? T('your_plan.we_use_this') : null };
      });
      kids.push(sub(T('your_plan.seasons_title'), [h('p', { class: 'sub' }, T('your_plan.seasons_tested')), hbars(rows, { min: 0, max: 100, fmt: num, unit: T('btn.out_of_100') }), K.srcs(F, ['hls'])]));
    }
    if (m.field_memory && m.field_memory.words) kids.push(sub(T('your_plan.memory_title'), said(P(m.field_memory.words))));
    return section('method', T('your_plan.method_title'), kids.length ? kids : K.notReady());
  }
  // horizontal bars in plain HTML: rows [{label, vals: [v per series], range: [lo, hi] | null, tag}], opt {min, max, ref, refLabel, names, fmt, unit}
  var FILLS = ['#14301E', '#C99A5B', '#7FB24A', '#4C8DB5'];
  var STRIPES = [null, 'repeating-linear-gradient(135deg,rgba(255,255,255,.45) 0 3px,transparent 3px 7px)', 'repeating-linear-gradient(90deg,rgba(255,255,255,.5) 0 2px,transparent 2px 6px)', 'radial-gradient(rgba(255,255,255,.6) 1px,transparent 1.5px) 0 0/6px 6px'];
  function hbars(rows, opt) {
    opt = opt || {};
    var all = []; rows.forEach(function (r) { r.vals.forEach(function (v) { if (v != null) all.push(v); }); if (r.range) all.push(r.range[0], r.range[1]); });
    if (opt.ref != null) all.push(opt.ref);
    var lo = opt.min != null ? opt.min : Math.min(0, Math.min.apply(null, all)), hi = opt.max != null ? opt.max : Math.max.apply(null, all) * 1.08;
    if (hi <= lo) hi = lo + 1;
    var pc = function (v) { return (Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo) * 100; }, f = opt.fmt || fv;
    var wrap = h('div', { style: 'display:flex;flex-direction:column;gap:10px' });
    rows.forEach(function (r) {
      var lane = h('div', { style: 'position:relative;display:flex;flex-direction:column;gap:3px;margin-top:4px' });
      r.vals.forEach(function (v, j) {
        if (v == null) return;
        var a = pc(Math.min(0 > lo ? 0 : lo, v)), b = pc(Math.max(0 > lo ? 0 : lo, v));
        lane.append(h('div', { style: 'position:relative;height:14px;background:var(--line-2);border-radius:4px' },
          h('div', { style: 'position:absolute;top:0;bottom:0;left:' + a + '%;width:' + Math.max(0.8, b - a) + '%;border-radius:4px;background:' + FILLS[j % 4] + (STRIPES[j % 4] ? ';background-image:' + STRIPES[j % 4] : '') }),
          rows.length && r.vals.length > 1 ? null : null));
      });
      if (r.range) lane.append(h('div', { 'aria-hidden': 'true', style: 'position:relative;height:10px' },
        h('div', { style: 'position:absolute;top:4px;height:2px;background:#7A4A20;left:' + pc(r.range[0]) + '%;width:' + Math.max(0.8, pc(r.range[1]) - pc(r.range[0])) + '%' }),
        h('div', { style: 'position:absolute;top:0;height:10px;width:2px;background:#7A4A20;left:' + pc(r.range[0]) + '%' }),
        h('div', { style: 'position:absolute;top:0;height:10px;width:2px;background:#7A4A20;left:' + pc(r.range[1]) + '%' })));
      if (opt.ref != null) lane.append(h('div', { 'aria-hidden': 'true', style: 'position:absolute;top:0;bottom:0;width:0;border-left:2px dashed #9A5426;left:' + pc(opt.ref) + '%' }));
      var nums = r.vals.map(function (v) { return v == null ? '' : f(v); }).filter(Boolean).join(' · ') + (r.range ? ' (' + f(r.range[0]) + '–' + f(r.range[1]) + ')' : '');
      wrap.append(h('div', null,
        h('div', { class: 'row', style: 'justify-content:space-between;align-items:flex-start' }, h('span', { style: 'font-weight:700;font-size:14px;min-width:0' }, r.label),
          h('span', { class: 'row', style: 'gap:6px;flex-shrink:0' }, r.tag ? h('span', { class: 'chip', style: 'background:#E5F0CF;color:#2E5A1E' }, svg(I('tick', 14, 3)), r.tag) : null,
            h('b', { style: 'font-size:14px' }, nums), opt.unit ? h('small', { class: 'small' }, opt.unit) : null)),
        lane));
    });
    if (opt.names && opt.names.length > 1) wrap.append(h('div', { class: 'legend' }, opt.names.map(function (n, j) {
      return h('span', null, h('span', { class: 'sw', style: 'background:' + FILLS[j % 4] + (STRIPES[j % 4] ? ';background-image:' + STRIPES[j % 4] : '') }), n);
    }), opt.rangeName ? h('span', null, h('span', { class: 'sw', style: 'height:2px;border:0;background:#7A4A20;vertical-align:4px' }), opt.rangeName) : null));
    if (opt.ref != null && opt.refLabel) wrap.append(h('p', { class: 'small', style: 'margin:0' }, svg('<svg width="18" height="12"><line x1="9" y1="0" x2="9" y2="12" stroke="#9A5426" stroke-width="2" stroke-dasharray="3 2"/></svg>'), ' ', fv(opt.ref) + ': ' + opt.refLabel));
    return wrap;
  }

  // ---------------- the last years' replay: one basket per year, both water cases ----------------
  function replay(F) {
    var plans = K.effPlans(F), pid = S.howPlan || 'current';
    var box = h('div', { style: 'display:flex;flex-direction:column;gap:10px' });
    var chips = h('div', { class: 'prio', role: 'group', 'aria-label': T('last_years.which_plan') });
    var head = h('h2', { class: 'h2' });
    function draw() {
      var p = plans.filter(function (x) { return x.id === pid; })[0] || plans[0], rep = p.replay || [], cases = K.waterCases(F);
      head.textContent = L(K.scr('last_years').title, { year_count: rep.length });
      [].forEach.call(chips.children, function (b) { b.setAttribute('aria-pressed', String(b.dataset.id === p.id)); });
      box.textContent = '';
      if (!rep.length) { box.append(K.notReady()); return; }
      box.append(h('div', { class: 'row wrap', style: 'gap:12px' }, cases.map(function (c) {
        return h('span', { class: 'row', style: 'gap:6px;font-weight:700;font-size:14px' }, svg(K.basketSvg(70, 16, c === 'irrigated' ? '#7FB24A' : null)), T('lbl.last_years.water_case.' + c));
      })));
      var grid = h('div', { class: 'baskets', style: 'grid-template-columns:repeat(auto-fill,minmax(150px,1fr))' });
      rep.forEach(function (y) {
        var ev = y.event_season ? T('lbl.last_years.event_season.' + y.event_season) : (y.event && y.event !== 'none' ? T('lbl.last_years.event.' + y.event) : null);
        var vals = cases.map(function (c) {
          var v = c === 'rain_fed' ? rng.apply(null, K.yearRange(y, 'harvest')) : num(y.irrigated.harvest);
          var pct = c === 'rain_fed' ? y.harvest : y.irrigated.harvest;
          return h('span', { style: 'display:flex;flex-direction:column;align-items:center;gap:2px' }, svg(K.basketSvg(pct, 26, c === 'irrigated' ? '#7FB24A' : null)), h('span', { class: 'v' }, v));
        });
        var dry = rng.apply(null, K.yearRange(y, 'dry_days'));
        grid.append(h('div', { class: 'yr' }, h('span', { class: 'y' }, digits(y.year)), h('div', { class: 'bk' }, vals),
          cases.indexOf('rain_fed') >= 0 ? h('span', { class: 'small' }, T('last_years.thirsty_days', { dry_days: dry })) : null,
          ev ? h('span', { class: 'ev' }, svg(I(y.event === 'flood' ? 'rain' : 'sun', 13)), ' ', ev) : null));
      });
      box.append(grid);
      box.append(K.lines([T('last_years.basket'), T('last_years.full_basket'), T('last_years.computer_made'),
        cases.length > 1 ? T('last_years.water_unknown') + ' ' + T('last_years.both_shown') : null,
        cases.indexOf('irrigated') >= 0 ? T('what_to_grow.water_never_out') : null,
        T('what_to_grow.range_why') + (K.hasDhm(F) ? ' ' + T('what_to_grow.range_town') : '')], 'sub'));
      box.append(K.srcs(F, ['twin', 'gpm', 'power', 'soil'], 'harvest_years'), h('div', { class: 'srcs' }, K.labs('replay_dry_days'), K.labs('replay_event')));
    }
    plans.forEach(function (p) {
      chips.append(h('button', { type: 'button', class: 'choice', 'data-id': p.id, onclick: function () { pid = p.id; S.howPlan = p.id; draw(); } }, K.planName(p)));
    });
    draw();
    return h('section', { id: 'how-replay' }, head, h('p', { class: 'sub', style: 'font-weight:700;color:var(--ink)' }, T('last_years.which_plan')), chips, box);
  }

  // ---------------- the 2040 outlook (demo.json future, and each plan's own future) ----------------
  function gauge(lo, hi, mid) {
    var g = s('svg', { viewBox: '0 0 200 120', width: '100%', 'aria-hidden': 'true' }), cx = 100, cy = 104, r = 80;
    function pt(v, rr) { var a = Math.PI * (1 - Math.max(0, Math.min(100, v)) / 100); return [cx + (rr || r) * Math.cos(a), cy - (rr || r) * Math.sin(a)]; }
    function arc(a, b) { var p = pt(a), q = pt(b); return 'M' + p[0].toFixed(1) + ' ' + p[1].toFixed(1) + ' A' + r + ' ' + r + ' 0 0 1 ' + q[0].toFixed(1) + ' ' + q[1].toFixed(1); }
    g.append(s('path', { d: arc(0, 100), fill: 'none', stroke: '#EFE6D4', 'stroke-width': 18, 'stroke-linecap': 'round' }));
    g.append(s('path', { d: arc(lo, Math.max(hi, lo + 0.5)), fill: 'none', stroke: '#C99A5B', 'stroke-width': 18 }));
    var n = pt(mid, r - 4);
    g.append(s('line', { x1: cx, y1: cy, x2: n[0].toFixed(1), y2: n[1].toFixed(1), stroke: '#14301E', 'stroke-width': 4, 'stroke-linecap': 'round' }));
    g.append(s('circle', { cx: cx, cy: cy, r: 6, fill: '#14301E' }));
    [0, 50, 100].forEach(function (v) { var p = pt(v, r + 12); g.append(s('text', { x: p[0].toFixed(1), y: (p[1] + 4).toFixed(1), 'text-anchor': 'middle', 'font-size': 10, fill: '#4A5646' }, digits(v))); });
    return g;
  }
  function future(F) {
    var fu = F.future, title = T('your_plan.future_title');
    if (!fu || K.mocked(F, 'future') || !fu.years || !fu.years.length) return section('future', title, K.notReady());
    var i = fu.years.length - 1, yr = fu.years[i];
    var dials = h('div', { class: 'dials' });
    K.effPlans(F).forEach(function (p) {
      var f = p.future || (p.id === 'current' ? fu.nothing_changes : null);
      if (!f) return;
      var lo = f.harvest_low[i], hi = f.harvest_high[i], mid = f.harvest[i];
      K.alts(p, 'future_').forEach(function (fa) {
        if (fa.harvest_low && fa.harvest_low[i] != null) lo = Math.min(lo, fa.harvest_low[i]);
        if (fa.harvest_high && fa.harvest_high[i] != null) hi = Math.max(hi, fa.harvest_high[i]);
      });
      var today = K.scoreRange(p, 'harvest');
      var dir = today[1] < lo ? 'up' : (today[0] > hi ? 'down' : 'eq');
      dials.append(h('div', { class: 'dial' },
        h('h3', { class: 'h3' }, p.id === 'current' ? T('field_future.nothing_changes') : K.planName(p)),
        p.id === 'current' ? h('p', { class: 'small', style: 'margin:2px 0 0' }, K.planName(p)) : null,
        gauge(lo, hi, mid),
        h('p', { style: 'margin:0;font-weight:700' }, T('field_future.range', { future_low: lo, future_high: hi })),
        h('p', { class: 'small', style: 'margin:4px 0' }, T('home.card_today_big') + ': ' + rng(today[0], today[1]) + ' ' + T('btn.out_of_100')),
        K.vsChip(dir)));
    });
    return section('future', title, [
      h('p', { class: 'lead' }, T('field_future.by_year', { future_year: yr }) + (fu.period ? ' (' + digits(fu.period) + ')' : '')),
      dials,
      K.lines(PL(fu.words).concat([T('field_future.many_guesses'), T('field_future.nobody_knows')]), 'sub'),
      K.srcs(F, ['nex', 'twin'], 'outlook_2040')]);
  }

  // ---------------- the farmland around the sample field (area/<id>.json) ----------------
  function area(F, a) {
    var layers = a.layers || [], cur = layers[0], ov = null;
    var mapEl = h('div', { class: 'areamap' }), legend = h('div', { style: 'display:flex;flex-direction:column;gap:8px' });
    var tog = h('div', { class: 'prio' });
    function drawLegend() {
      legend.textContent = '';
      legend.append(h('div', { class: 'legend' }, (cur.classes || []).concat(cur.no_data ? [cur.no_data] : []).map(function (c) {
        return h('span', null, h('span', { class: 'sw', style: 'background:' + c.colour }), P(c));
      })));
      legend.append(K.lines(PL(cur.legend), 'small'));
      [].forEach.call(tog.children, function (b, j) { b.setAttribute('aria-pressed', String(layers[j] === cur)); });
    }
    layers.forEach(function (l) { tog.append(h('button', { type: 'button', class: 'choice', onclick: function () { cur = l; if (ov) ov.setUrl('data/area/' + l.image); drawLegend(); } }, P(l.title))); });
    if (cur) drawLegend();
    K.loadLeaflet().then(function (Lf) {
      var m = Lf.map(mapEl, { scrollWheelZoom: false });
      K.osm(Lf, m);
      if (cur) ov = Lf.imageOverlay('data/area/' + cur.image, a.bounds, { opacity: 0.85, className: 'pix' }).addTo(m);
      (F.field.sections || []).forEach(function (sec) { Lf.polygon(sec.polygon.map(function (p) { return [p[1], p[0]]; }), { color: '#14301E', weight: 2, fill: false }).addTo(m); });
      m.fitBounds(a.bounds);
      setTimeout(function () { m.invalidateSize(); m.fitBounds(a.bounds); }, 250);
    });
    var nums = (a.numbers || []).map(function (n) { return K.lines(PL(n), 'sub'); });
    return [a.placeholder ? K.sampleChip() : null, tog, mapEl, legend, nums, h('div', { class: 'srcs' }, (a.sources || []).map(function (x) { return K.srcTag(F, x); }))];
  }

  // ---------------- how the computer helped; words; what is not ready ----------------
  function helped() {
    return section('helped', T('your_plan.computer_helped'), K.lines([T('your_plan.helped_words'), T('your_plan.helped_check'), T('your_plan.helped_drafts'), T('your_plan.helped_seasons')], 'sub'));
  }
  function glossary() {
    var li = K.langInfo(S.lang);
    return section('words', T('btn.word_help'), (S.words.glossary || []).map(function (g) {
      return h('details', null, h('summary', null, L(g.term)), h('p', { style: 'margin:0 0 6px' }, L(g.say)),
        g.basis ? h('p', { class: 'quote', lang: 'en' }, (li && li.quote_label ? (li.quote_label[S.lang] || li.quote_label.en) + ': ' : '') + g.basis) : null);
    }));
  }
  // a garden or indoor test of the soil stick: shown here as bowls, never as the field's parts (owner, 2026-11-15)
  function stickTest(pd) {
    return pd && pd.test ? section('stick', T('check_soil.prototype'), [K.recordedLine(pd), K.bowlLines(pd)]) : null;
  }
  function notReady(F, pd) {
    var items = (F.mock || []).map(function (b) { return T('btn.not_ready') + ' (' + b + ')'; });
    items.push(T('your_plan.nr_photo'));
    if (!pd || pd.kind === 'none' || !K.forField(pd)) items.push(T('your_plan.nr_readings'));
    if (K.isPlaceholder(F.field.name)) items.push(T('your_plan.nr_own_field'));
    items.push(T('your_plan.nr_robot'));
    items.push(T('your_plan.nr_outlook') + ' ' + T('your_plan.nr_outlook_why1') + ' ' + T('your_plan.nr_outlook_why2'));   // rules.yaml weather_ahead.season_outlook
    return section('notready', T('your_plan.not_ready_title'), K.lines(items, 'sub'));
  }

  // ---------------- the data story (story.json) ----------------
  function story(F, st) {
    var out = [], byId = {}, done = {};
    (st.charts || []).forEach(function (c) { byId[c.id] = c; });
    var groups = (st.sections && st.sections.length) ? st.sections : [{ id: 'story', title: null, charts: (st.charts || []).map(function (c) { return c.id; }) }];
    groups.forEach(function (g) {
      var cards = (g.charts || []).filter(function (id) { return byId[id] && !done[id]; }).map(function (id) { done[id] = 1; return chartCard(F, byId[id]); });
      if (!cards.length) return;
      var title = g.title ? P(g.title) : T('your_plan.story_title');
      // each story section's numbers carry the labels of its output (story.json has no output ids: matched by section id)
      var oid = { rain: 'rain_months', seasons: 'season_dates', groundwater: 'groundwater', probe: 'probe_water', area: 'nearby_fields', future: 'outlook_2040' }[g.id];
      out.push({ id: 's-' + g.id, title: title, el: section('s-' + g.id, title, [oid ? K.labs(oid) : null].concat(cards)) });
    });
    if ((st.compliance || []).length) {          // owner's item 4: verified, estimate or not yet checkable
      var t0 = T('your_plan.report_card'), pct = function (x) { return digits(Math.round(x * 100)) + '%'; };
      out.push({ id: 'report', title: t0, el: section('report', t0, [st.compliance_note ? said(P(st.compliance_note)) : null].concat(st.compliance.map(function (r) {
        var ic = { VERIFIED: 'tick', ESTIMATE: 'warn' }[r.status] || 'fog';
        return h('div', { class: 'fact' }, h('span', { class: 'ic', style: 'background:#F7F1E4' }, svg(I(ic, 20))),
          h('div', { class: 'grow' }, h('b', null, P(r.thing)), ' ', h('span', { class: 'chip', style: 'margin-left:4px' }, P(r.status_words)),
            said(P(r.said)), r.n ? h('p', { class: 'small', style: 'margin:2px 0 0' }, pct(r.share) + ' (' + pct(r.ci95[0]) + '–' + pct(r.ci95[1]) + ')') : null));
      }))) });
    } else if ((st.report_card || []).length) {
      var t1 = T('your_plan.report_card');
      out.push({ id: 'report', title: t1, el: section('report', t1, st.report_card.map(function (r) {
        var lvl = { high: 3, medium: 2, low: 1 }[r.confidence] || 0;
        var bars = svg('<svg width="26" height="18" viewBox="0 0 26 18">' + [0, 1, 2].map(function (i) {
          return '<rect x="' + (i * 9) + '" y="' + (12 - i * 5) + '" width="7" height="' + (6 + i * 5) + '" rx="1.5" fill="' + (i < lvl ? '#14301E' : '#E3D6BF') + '"/>';
        }).join('') + '</svg>');
        return h('div', { class: 'fact' }, h('span', { class: 'ic', style: 'background:#F7F1E4' }, bars),
          h('div', { class: 'grow' }, h('b', null, P(r.thing)), ' ', h('span', { class: 'chip', style: 'margin-left:4px' }, T('your_plan.sure_' + (r.confidence || 'low'))),
            K.lines(K.sentences(P(r.why)), 'sub')));
      })) });
    }
    if ((st.satellites || []).length) {
      var t2 = T('your_plan.missions_title');
      out.push({ id: 'missions', title: t2, el: section('missions', t2, st.satellites.map(function (m) {
        return h('div', { class: 'fact' }, h('span', { class: 'ic' }, svg(I('sat', 20))),
          h('div', { class: 'grow' }, h('b', null, m.mission || ''), m.instrument ? h('div', { class: 'small' }, m.instrument) : null, m.dataset ? h('div', { class: 'small' }, m.dataset) : null,
            m.job ? h('p', { class: 'sub', style: 'margin:4px 0 0' }, P(m.job)) : null, m.checked ? h('p', { class: 'small', style: 'margin:2px 0 0' }, svg(I('tick', 13, 3)), ' ', P(m.checked)) : null));
      })) });
    }
    if ((st.resources || []).length) {
      var t3 = T('your_plan.links_title');
      out.push({ id: 'links', title: t3, el: section('links', t3, h('ul', { class: 'lines' }, st.resources.map(function (r) {
        if (typeof r === 'string') return h('li', null, /^https?:\/\//.test(r) ? h('a', { href: r, target: '_blank', rel: 'noopener' }, r) : r);
        var label = r.name || P(r.title || r.label) || r.url || '';
        return h('li', { style: 'padding:4px 0' }, r.url ? h('a', { href: r.url, target: '_blank', rel: 'noopener' }, label) : h('b', null, label),
          r.how ? h('span', { class: 'sub' }, ' · ' + P(r.how)) : null, r.note ? h('span', { class: 'small' }, ' · ' + P(r.note)) : null);
      }))) });
    }
    return out;
  }
  function chartCard(F, c) {
    var body = null, ready = !c.status || c.status === 'ready';
    if (ready) {
      try {
        body = c.kind === 'table' ? table(c) : c.kind === 'bars' ? bars(c) : c.kind === 'timeline' ? timeline(c) : c.kind === 'map' ? mapChart(F, c) :
          c.kind === 'bands' && !(c.series || []).length ? bandRows(c) : line(c);
      } catch (e) { body = K.notReady(); if (window.console) console.warn('chart', c.id, e); }
    }
    var tags = (c.sources || []).map(function (name) {
      var nm = String(name).toLowerCase();
      var hit = (F.sources || []).filter(function (x) { var n = String(x.name).toLowerCase().replace(/\s*\(.*$/, ''); return n.length > 3 && nm.indexOf(n) >= 0; })[0];
      return h('li', { class: 'small', style: 'font-size:12px' }, hit ? K.srcTag(F, hit) : svg(I('info', 12)), ' ', name);
    });
    return h('figure', { class: 'chart', style: 'margin:0;display:flex;flex-direction:column;gap:8px;padding:12px 0;border-top:1px solid var(--line-2)' },
      h('h3', { class: 'h3' }, P(c.title)), ready ? null : h('span', { class: 'chip' }, svg(I('fog', 14)), T('btn.not_ready')), body,
      h('figcaption', null, K.lines(K.sentences(P(c.caption)), 'sub'), c.note ? h('p', { class: 'small', style: 'margin:4px 0 0' }, svg(I('info', 13)), ' ', P(c.note)) : null),
      c.words ? K.lines(PL(c.words), 'small') : null,
      tags.length ? h('details', { style: 'background:transparent;padding:0' }, h('summary', { style: 'min-height:40px;font-size:13px' }, T('btn.source_label')), h('ul', { class: 'lines' }, tags)) : null);
  }
  // category ids → words (x.categories / y.categories)
  function catName(axis, id) {
    var c = ((axis && axis.categories) || []).filter(function (x) { return x.id === id; })[0];
    if (c) return P(c);
    if (axis && axis.type === 'month' && K.MONTHS.indexOf(String(id).slice(0, 3)) >= 0) return K.monthName(String(id).slice(0, 3), true);
    return typeof id === 'object' ? P(id) : String(id);
  }
  function isRange(p) { return Array.isArray(p[1]) || p.length >= 3; }
  function lohi(p) { return Array.isArray(p[1]) ? p[1] : [p[1], p[2]]; }
  function bars(c) {
    if (c.x && (c.x.type === 'year' || c.x.type === 'month')) return line(c, true);
    var series = c.series || [], ids = [];
    ((c.x && c.x.categories) || []).forEach(function (k) { ids.push(k.id); });
    series.forEach(function (se) { (se.points || []).forEach(function (p) { if (ids.indexOf(p[0]) < 0) ids.push(p[0]); }); });
    if (!ids.length) return K.notReady();
    var valS = series.filter(function (se) { return !(se.points || []).some(isRange); }), rangeS = series.filter(function (se) { return (se.points || []).some(isRange); })[0];
    var rows = ids.map(function (id) {
      var vals = valS.map(function (se) { var p = (se.points || []).filter(function (q) { return q[0] === id; })[0]; return p ? +p[1] : null; });
      var rp = rangeS ? (rangeS.points || []).filter(function (q) { return q[0] === id; })[0] : null;
      return { label: catName(c.x, id), vals: vals, range: rp ? lohi(rp) : null };
    });
    var unit = c.y ? (c.y.unit || '') : '';
    return h('div', { style: 'display:flex;flex-direction:column;gap:6px' },
      c.y && c.y.label ? h('p', { class: 'small', style: 'margin:0;font-weight:700' }, P(c.y.label) + (unit && unit.length < 12 ? ' (' + unit + ')' : '')) : null,
      hbars(rows, { ref: c.y ? c.y.ref : null, refLabel: c.y && c.y.ref_label ? P(c.y.ref_label) : null, names: valS.map(function (se) { return P(se.name); }), rangeName: rangeS ? P(rangeS.name) : null }));
  }
  function xinfo(c) {
    var t = (c.x && c.x.type) || 'year';
    function v(x) {
      if (t === 'date') return Date.parse(x);
      if (t === 'month') { if (typeof x === 'number') return x; var i = K.MONTHS.indexOf(String(x).slice(0, 3)); return i >= 0 ? i + 1 : NaN; }
      return +x;
    }
    function lab(n) {
      if (t === 'date') return digits(new Date(n).getUTCFullYear());
      if (t === 'month') return K.monthName(K.MONTHS[(Math.round(n) - 1 + 12) % 12], true);
      return digits(Math.round(n));
    }
    return { t: t, v: v, lab: lab };
  }
  function ticks(lo, hi, n) {
    var span = hi - lo || 1, step = Math.pow(10, Math.floor(Math.log10(span / n))), err = span / n / step;
    step *= err >= 7.5 ? 10 : err >= 3 ? 5 : err >= 1.5 ? 2 : 1;
    var out = []; for (var x = Math.ceil(lo / step) * step; x <= hi + 1e-9; x += step) out.push(+x.toFixed(10));
    return out;
  }
  var LSTYLE = [{ c: '#14301E', d: null, w: 2.6 }, { c: '#9A5426', d: '7 5', w: 2.2 }, { c: '#2F6E99', d: '2 4', w: 2.4 }, { c: '#6B5D42', d: '12 4 2 4', w: 2 }];
  function line(c, cols) {
    var xi = xinfo(c), series = c.series || [], xs = [], ys = [];
    series.forEach(function (se) {
      (se.points || []).forEach(function (p) {
        var v = xi.v(p[0]); if (!isNaN(v)) xs.push(v);
        if (isRange(p)) lohi(p).forEach(function (q) { if (q != null) ys.push(+q); }); else if (p[1] != null) ys.push(+p[1]);
      });
    });
    (c.markers || []).forEach(function (mk) { var v = xi.v(mk.x); if (!isNaN(v)) xs.push(v); });
    if (c.y && c.y.ref != null) ys.push(c.y.ref);
    xs = xs.filter(function (v) { return !isNaN(v); });
    if (!xs.length || !ys.length) return K.notReady();
    var Wd = 420, Ht = 250, m = { l: 36, r: 10, t: 14, b: 24 };
    var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs), y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
    if (y0 > 0 && (cols || y0 < (y1 - y0))) y0 = 0;
    var pad = (y1 - y0) * 0.06 || 1; y1 += pad; if (y0 !== 0) y0 -= pad;
    if (cols) { x0 -= 0.5; x1 += 0.5; }
    if (x0 === x1) { x0 -= 1; x1 += 1; }
    var X = function (v) { return m.l + (v - x0) / (x1 - x0) * (Wd - m.l - m.r); }, Y = function (v) { return Ht - m.b - (v - y0) / (y1 - y0) * (Ht - m.t - m.b); };
    var g = s('svg', { viewBox: '0 0 ' + Wd + ' ' + Ht, role: 'img', class: 'plot', 'aria-label': P(c.title) });
    var defs = s('defs'); g.append(defs);
    var pat = s('pattern', { id: 'stripe-' + c.id, width: 6, height: 6, patternUnits: 'userSpaceOnUse', patternTransform: 'rotate(45)' });
    pat.append(s('rect', { width: 6, height: 6, fill: '#9A5426', 'fill-opacity': .14 }), s('line', { x1: 0, y1: 0, x2: 0, y2: 6, stroke: '#9A5426', 'stroke-opacity': .4, 'stroke-width': 2 }));
    defs.append(pat);
    ticks(y0, y1, 5).forEach(function (v) {
      g.append(s('line', { x1: m.l, x2: Wd - m.r, y1: Y(v), y2: Y(v), stroke: '#EFE6D4' }));
      g.append(s('text', { x: m.l - 6, y: Y(v) + 4, 'text-anchor': 'end' }, fv(v)));
    });
    g.append(s('line', { x1: m.l, x2: Wd - m.r, y1: Ht - m.b, y2: Ht - m.b, stroke: '#CDBF9F' }));
    // bands (e.g. crop seasons): one fill per label, the second striped, never colour alone (legend below)
    var bandLabels = [];
    (c.bands || []).forEach(function (b) {
      var lab = P(b.label); if (bandLabels.indexOf(lab) < 0) bandLabels.push(lab);
      var k = bandLabels.indexOf(lab), a = X(xi.v(b.from)), z = X(xi.v(b.to));
      g.append(s('rect', { x: Math.min(a, z), y: m.t, width: Math.abs(z - a) || 2, height: Ht - m.t - m.b, fill: k === 0 ? '#C8E05A' : 'url(#stripe-' + c.id + ')', 'fill-opacity': k === 0 ? .3 : 1 }));
    });
    var tk;
    if (xi.t === 'date') { tk = []; var ya = new Date(x0).getUTCFullYear(), yb = new Date(x1).getUTCFullYear(), st = Math.max(1, Math.ceil((yb - ya + 1) / 7)); for (var y = ya; y <= yb; y += st) tk.push(Date.UTC(y, 0, 1)); }
    else if (xi.t === 'month') tk = [1, 3, 5, 7, 9, 11];
    else tk = ticks(x0, x1, cols ? 7 : 6).filter(function (v) { return Math.round(v) === v; });
    tk.filter(function (v) { return v >= x0 && v <= x1; }).forEach(function (v) { var x = X(v); g.append(s('text', { x: x, y: Ht - m.b + 16, 'text-anchor': x > Wd - 22 ? 'end' : x < m.l + 14 ? 'start' : 'middle' }, xi.lab(v))); });
    if (c.y && c.y.ref != null) g.append(s('line', { x1: m.l, x2: Wd - m.r, y1: Y(c.y.ref), y2: Y(c.y.ref), stroke: '#9A5426', 'stroke-dasharray': '3 3' }));
    var lineIdx = 0, legendItems = [];
    series.forEach(function (se) {
      var pts = (se.points || []).filter(function (p) { return !isNaN(xi.v(p[0])); }).sort(function (a, b) { return xi.v(a[0]) - xi.v(b[0]); });
      if (!pts.length) return;
      if (cols) {
        var bw = (X(1) - X(0)) * 0.78;
        if (pts.some(isRange)) {
          pts.forEach(function (p) { var r = lohi(p), x = X(xi.v(p[0])); g.append(s('line', { x1: x, x2: x, y1: Y(r[0]), y2: Y(r[1]), stroke: '#7A4A20', 'stroke-width': 2 }));
            [r[0], r[1]].forEach(function (v) { g.append(s('line', { x1: x - 4, x2: x + 4, y1: Y(v), y2: Y(v), stroke: '#7A4A20', 'stroke-width': 2 })); }); });
          legendItems.push({ name: P(se.name), sw: '<path d="M14 1v10M10 1h8M10 11h8" stroke="#7A4A20" stroke-width="2" fill="none"/>' });
          return;
        }
        var k = lineIdx++, n = series.filter(function (q) { return !(q.points || []).some(isRange); }).length || 1, w = bw / n;
        pts.forEach(function (p) { var x = X(xi.v(p[0])) - bw / 2 + k * w, v = +p[1], ya = Y(Math.max(0, v)), yb = Y(Math.min(0, v));
          g.append(s('rect', { x: x.toFixed(1), y: Math.min(ya, yb).toFixed(1), width: Math.max(1, w - 1).toFixed(1), height: Math.max(0.5, Math.abs(yb - ya)).toFixed(1), rx: 1.5, fill: FILLS[k % 4], stroke: k ? '#14301E' : null, 'stroke-width': k ? .6 : null })); });
        legendItems.push({ name: P(se.name), sw: '<rect x="6" y="1" width="16" height="10" rx="2" fill="' + FILLS[k % 4] + '" stroke="#14301E" stroke-width=".6"/>' });
        return;
      }
      if (pts.some(isRange)) {
        var top = pts.map(function (p) { return X(xi.v(p[0])).toFixed(1) + ' ' + Y(+lohi(p)[1]).toFixed(1); });
        var bot = pts.slice().reverse().map(function (p) { return X(xi.v(p[0])).toFixed(1) + ' ' + Y(+lohi(p)[0]).toFixed(1); });
        g.insertBefore(s('path', { d: 'M' + top.join(' L') + ' L' + bot.join(' L') + 'Z', fill: '#C99A5B', 'fill-opacity': .3 }), g.childNodes[2] || null);
        legendItems.push({ name: P(se.name), sw: '<rect x="1" y="2" width="26" height="8" fill="#C99A5B" fill-opacity=".45"/>' });
        return;
      }
      if (se.role === 'marker') {
        pts.forEach(function (p) { g.append(s('circle', { cx: X(xi.v(p[0])), cy: Y(+p[1]), r: 4.5, fill: '#14301E', stroke: '#fff', 'stroke-width': 1.5 })); });
        legendItems.push({ name: P(se.name), sw: '<circle cx="14" cy="6" r="4" fill="#14301E"/>' });
        return;
      }
      var stl = LSTYLE[se.role === 'main' && lineIdx === 0 ? 0 : Math.min(3, lineIdx === 0 ? 1 : lineIdx)]; lineIdx++;
      var d = pts.filter(function (p) { return p[1] != null; }).map(function (p, i) { return (i ? 'L' : 'M') + X(xi.v(p[0])).toFixed(1) + ' ' + Y(+p[1]).toFixed(1); }).join(' ');
      g.append(s('path', { d: d, fill: 'none', stroke: stl.c, 'stroke-width': stl.w, 'stroke-dasharray': stl.d, 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }));
      legendItems.push({ name: P(se.name), sw: '<line x1="1" y1="6" x2="27" y2="6" stroke="' + stl.c + '" stroke-width="2.5"' + (stl.d ? ' stroke-dasharray="' + stl.d + '"' : '') + '/>' });
    });
    (c.markers || []).forEach(function (mk, i) {
      var x = X(xi.v(mk.x));
      g.append(s('line', { x1: x, x2: x, y1: m.t, y2: Ht - m.b, stroke: '#9A5426', 'stroke-dasharray': '3 3' }));
      var lab = P(mk.label), right = x > Wd * 0.62;
      g.append(s('text', { x: right ? x - 4 : x + 4, y: m.t + 12 + (i % 3) * 13, 'text-anchor': right ? 'end' : 'start', fill: '#7A4A20', 'font-weight': 700 }, lab));
    });
    var yl = c.y ? P(c.y.label) + (c.y.unit && c.y.unit.length < 12 ? ' (' + c.y.unit + ')' : '') : '';
    bandLabels.forEach(function (bl, k) { legendItems.push({ name: bl, sw: k === 0 ? '<rect x="1" y="1" width="26" height="10" fill="#C8E05A" fill-opacity=".45"/>' : '<rect x="1" y="1" width="26" height="10" fill="#9A5426" fill-opacity=".14"/><path d="M4 11L12 1M12 11L20 1M20 11L27 3" stroke="#9A5426" stroke-opacity=".5" stroke-width="2"/>' }); });
    if (c.y && c.y.ref != null && c.y.ref_label) legendItems.push({ name: fv(c.y.ref) + ': ' + P(c.y.ref_label), sw: '<line x1="1" y1="6" x2="27" y2="6" stroke="#9A5426" stroke-width="2" stroke-dasharray="3 3"/>' });
    return h('div', null, yl ? h('p', { class: 'small', style: 'margin:0 0 4px;font-weight:700' }, yl) : null, g,
      c.x && c.x.label ? h('p', { class: 'small', style: 'margin:0;text-align:center' }, P(c.x.label)) : null,
      legendItems.length > 1 ? h('div', { class: 'legend', style: 'margin-top:6px' }, legendItems.map(function (it) { return h('span', { class: 'row', style: 'gap:6px' }, svg('<svg width="28" height="12" viewBox="0 0 28 12">' + it.sw + '</svg>'), it.name); })) : null);
  }
  function bandRows(c) {
    var xi = xinfo(c), bs = c.bands || [], xs = [];
    bs.forEach(function (b) { xs.push(xi.v(b.from), xi.v(b.to)); });
    xs = xs.filter(function (v) { return !isNaN(v); });
    if (!xs.length) return K.notReady();
    var wrap = h('div', { style: 'display:flex;flex-direction:column;gap:6px' }), x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs), sp = (x1 - x0) || 1;
    bs.forEach(function (b) {
      var a = (xi.v(b.from) - x0) / sp * 100, z = (xi.v(b.to) - x0) / sp * 100;
      wrap.append(h('div', null, h('div', { class: 'small', style: 'font-weight:700;color:var(--ink)' }, P(b.label) + ' · ' + xi.lab(xi.v(b.from)) + '–' + xi.lab(xi.v(b.to))),
        h('div', { style: 'position:relative;height:14px;background:var(--line-2);border-radius:99px' },
          h('div', { style: 'position:absolute;top:0;bottom:0;left:' + Math.min(a, z) + '%;width:' + Math.max(1.5, Math.abs(z - a)) + '%;background:var(--ink);border-radius:99px' }))));
    });
    return wrap;
  }
  // a timeline with category values (e.g. one weather event a year): a table of the years where something happened
  function timeline(c) {
    var series = c.series || [];
    if (c.y && c.y.type === 'category' && series.length) {
      var years = {};
      series.forEach(function (se, j) { (se.points || []).forEach(function (p) { (years[p[0]] = years[p[0]] || [])[j] = p[1]; }); });
      var keys = Object.keys(years).sort().filter(function (y) { return years[y].some(function (v) { return v && v !== 'none'; }); });
      var icon = function (v) { return v === 'flood' ? I('rain', 14) : v === 'drought' ? I('sun', 14) : null; };
      return h('div', { style: 'overflow-x:auto' }, h('table', null,
        h('thead', null, h('tr', null, h('th', null, P(c.x && c.x.label)), series.map(function (se) { return h('th', null, P(se.name)); }))),
        h('tbody', null, keys.map(function (y) {
          return h('tr', null, h('td', null, h('b', null, digits(y))), series.map(function (se, j) {
            var v = years[y][j];
            return h('td', null, v == null ? '–' : [icon(v) ? svg(icon(v)) : null, ' ', catName(c.y, v)]);
          }));
        }))));
    }
    var xi = xinfo(c), items = (c.markers || []).map(function (m) { return { x: m.x, label: m.label }; });
    series.forEach(function (se) { (se.points || []).forEach(function (p) { items.push({ x: p[0], label: p[2] || se.name }); }); });
    items = items.filter(function (it) { return !isNaN(xi.v(it.x)); }).sort(function (a, b) { return xi.v(a.x) - xi.v(b.x); });
    if (!items.length) return K.notReady();
    return h('ol', { class: 'lines', style: 'border-left:3px solid var(--ink);padding-left:14px;gap:10px' }, items.map(function (it) {
      return h('li', null, h('b', null, xi.lab(xi.v(it.x))), ' · ', P(it.label));
    }));
  }
  // a table: each row read in plain words (the localized fields first), never raw keys
  function table(c) {
    var rows = c.rows || [];
    if (!rows.length) return null;
    function loc(v) { return v && typeof v === 'object' && !Array.isArray(v) && ('en' in v); }
    return h('ul', { class: 'lines', style: 'gap:8px' }, rows.map(function (r) {
      if (Array.isArray(r)) return h('li', null, r.map(function (v) { return loc(v) ? P(v) : (typeof v === 'number' ? digits(v) : String(v)); }).join(' · '));
      var parts = Object.keys(r).filter(function (k) { return loc(r[k]); }).map(function (k) { return P(r[k]); });
      return h('li', null, h('b', null, parts[0] || ''), parts.length > 1 ? ': ' + parts.slice(1).join(' ') : '');
    }));
  }
  function mapChart(F, c) {
    if (c.link) {
      var box = h('div', { style: 'display:flex;flex-direction:column;gap:8px' }, K.loading());
      K.getJSON(String(c.link).replace(/^\/+/, '')).then(function (a) { box.textContent = ''; if (a) K.add(box, area(F, a)); else box.append(K.notReady()); });
      return box;
    }
    var el = h('div', { class: 'areamap', style: 'aspect-ratio:4/3' });
    K.loadLeaflet().then(function (Lf) {
      var m = Lf.map(el, { scrollWheelZoom: false }), pts = [];
      K.osm(Lf, m);
      (c.series || []).forEach(function (se) {
        (se.points || []).forEach(function (p) {
          var ll = [+p[1], +p[0]]; if (isNaN(ll[0]) || isNaN(ll[1])) return; pts.push(ll);
          var mk = Lf.circleMarker(ll, { radius: 7, color: '#14301E', weight: 2, fillColor: se.role === 'compare' ? '#C99A5B' : '#C8E05A', fillOpacity: 1 }).addTo(m);
          var t = document.createElement('span'); t.textContent = P(se.name); mk.bindTooltip(t);
        });
      });
      if (pts.length) m.fitBounds(pts, { padding: [30, 30], maxZoom: 12 }); else m.setView([F.field.lat, F.field.lon], 9);
      setTimeout(function () { m.invalidateSize(); }, 200);
    });
    return el;
  }
  K.how.plot = function (c) { return c.kind === 'bars' ? bars(c) : line(c); };   // one chart alone, for js/behind.js
})();
