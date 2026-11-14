/* Khet Sathi: the "How we know" page, loaded only when it is first opened. Charts are inline SVG drawn here from
   site/data/story.json and the field file; every label is set with textContent. No chart library, no outside service. */
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

  K.how = function (F) {
    var root = h('div', { class: 'how' });
    root.append(h('div', { class: 'row wrap' }, K.isPlaceholder(F.field.name) ? K.sampleChip() : null, h('span', { class: 'small' }, F.field.name)));
    var storyBox = h('div', { style: 'display:flex;flex-direction:column;gap:16px' });
    root.append(storyBox);
    K.getJSON('data/story.json').then(function (st) { if (st && storyBox.isConnected) story(F, st).forEach(function (x) { storyBox.append(x); }); });
    root.append(method(F), replay(F), future(F));
    var areaBox = h('div');
    root.append(areaBox);
    K.getJSON('data/area/' + encodeURIComponent(S.fid) + '.json').then(function (a) { if (a && areaBox.isConnected) areaBox.append(area(F, a)); });
    root.append(helped(), section('sources', T('your_plan.sources_title'), K.sourcesList(F)), glossary());
    var nr = h('div');
    root.append(nr);
    K.getJSON('data/probe_log.json').then(function (log) { if (nr.isConnected) nr.append(notReady(F, log)); });
    return root;
  };

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
        var name = WAYS[x.id] ? T('your_plan.' + WAYS[x.id]) : x.id;
        return { label: name, value: x.score * 100, tag: x.id === sd.chosen ? T('your_plan.we_use_this') : null };
      });
      kids.push(sub(T('your_plan.seasons_title'), [h('p', { class: 'sub' }, T('your_plan.seasons_tested')), hbars(rows), K.srcs(F, ['hls'])]));
    }
    if (m.field_memory && m.field_memory.words) kids.push(sub(T('your_plan.memory_title'), said(P(m.field_memory.words))));
    return section('method', T('your_plan.method_title'), kids.length ? kids : K.notReady());
  }
  function hbars(rows) {
    var wrap = h('div', { style: 'display:flex;flex-direction:column;gap:8px' });
    rows.forEach(function (r) {
      wrap.append(h('div', null,
        h('div', { class: 'row', style: 'justify-content:space-between' }, h('span', { style: 'font-weight:700;font-size:14px' }, r.label),
          h('span', { class: 'row', style: 'gap:6px' }, r.tag ? h('span', { class: 'chip', style: 'background:#E5F0CF;color:#2E5A1E' }, svg(I('tick', 14, 3)), r.tag) : null,
            h('b', null, num(r.value)), h('small', { class: 'small' }, T('btn.out_of_100')))),
        h('div', { style: 'height:12px;border-radius:99px;background:var(--line-2);overflow:hidden;margin-top:4px' },
          h('div', { style: 'height:100%;width:' + Math.max(0, Math.min(100, r.value)) + '%;background:' + (r.tag ? 'var(--ink)' : 'var(--brown)') + ';border-radius:99px' }))));
    });
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
        var a = K.altYear(y), ev = y.event_season ? T('lbl.last_years.event_season.' + y.event_season) : (y.event && y.event !== 'none' ? T('lbl.last_years.event.' + y.event) : null);
        var vals = cases.map(function (c) {
          var v = c === 'rain_fed' ? rng(y.harvest, a ? a.harvest : null) : num(y.irrigated.harvest);
          var pct = c === 'rain_fed' ? y.harvest : y.irrigated.harvest;
          return h('span', { style: 'display:flex;flex-direction:column;align-items:center;gap:2px' }, svg(K.basketSvg(pct, 26, c === 'irrigated' ? '#7FB24A' : null)), h('span', { class: 'v' }, v));
        });
        var dry = rng(y.dry_days, a ? a.dry_days : null);
        grid.append(h('div', { class: 'yr' }, h('span', { class: 'y' }, digits(y.year)), h('div', { class: 'bk' }, vals),
          cases.indexOf('rain_fed') >= 0 ? h('span', { class: 'small' }, T('last_years.thirsty_days', { dry_days: dry })) : null,
          ev ? h('span', { class: 'ev' }, svg(I(y.event === 'flood' ? 'rain' : 'sun', 13)), ' ', ev) : null));
      });
      box.append(grid);
      box.append(K.lines([T('last_years.basket'), T('last_years.full_basket'), T('last_years.computer_made'),
        cases.length > 1 ? T('last_years.water_unknown') + ' ' + T('last_years.both_shown') : null,
        cases.indexOf('irrigated') >= 0 ? T('what_to_grow.water_never_out') : null,
        T('what_to_grow.range_why') + (K.hasDhm(F) ? ' ' + T('what_to_grow.range_town') : '')], 'sub'));
      box.append(K.srcs(F, ['twin', 'gpm', 'power', 'soil']));
    }
    plans.forEach(function (p) {
      chips.append(h('button', { type: 'button', class: 'choice', 'data-id': p.id, onclick: function () { pid = p.id; S.howPlan = p.id; draw(); } }, K.planName(p)));
    });
    draw();
    return h('section', { id: 'how-replay' }, head, h('p', { class: 'sub', style: 'font-weight:700;color:var(--ink)' }, T('last_years.which_plan')), chips, box);
  }

  // ---------------- the 2040 outlook (demo.json future, and each plan's own future) ----------------
  function gauge(lo, hi, mid) {
    var g = s('svg', { viewBox: '0 0 200 120', width: '100%', role: 'img' }), cx = 100, cy = 104, r = 80;
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
      var fa = K.alt(p, 'future');
      var lo = f.harvest_low[i], hi = f.harvest_high[i], mid = f.harvest[i];
      if (fa) { lo = Math.min(lo, fa.harvest_low[i]); hi = Math.max(hi, fa.harvest_high[i]); }
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
      K.srcs(F, ['nex', 'twin'])]);
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
    K.loadLeaflet().then(function (L) {
      if (!mapEl.isConnected && !document.body.contains(mapEl)) return;
      var m = L.map(mapEl, { scrollWheelZoom: false });
      K.osm(L, m);
      if (cur) ov = L.imageOverlay('data/area/' + cur.image, a.bounds, { opacity: 0.85, className: 'pix' }).addTo(m);
      (F.field.sections || []).forEach(function (sec) { L.polygon(sec.polygon.map(function (p) { return [p[1], p[0]]; }), { color: '#14301E', weight: 2, fill: false }).addTo(m); });
      m.fitBounds(a.bounds);
      setTimeout(function () { m.invalidateSize(); }, 200);
    });
    var nums = (a.numbers || []).map(function (n) { return K.lines(PL(n), 'sub'); });
    return section('area', T('your_plan.area_title'), [a.placeholder ? K.sampleChip() : null, tog, mapEl, legend, nums,
      h('div', { class: 'srcs' }, (a.sources || []).map(function (x) { return K.srcTag(F, x); }))]);
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
  function notReady(F, log) {
    var items = (F.mock || []).map(function (b) { return T('btn.not_ready') + ' (' + b + ')'; });
    items.push(T('your_plan.nr_photo'));
    if (!log) items.push(T('your_plan.nr_readings'));
    if (K.isPlaceholder(F.field.name)) items.push(T('your_plan.nr_own_field'));
    items.push(T('your_plan.nr_robot'));
    return section('notready', T('your_plan.not_ready_title'), K.lines(items, 'sub'));
  }

  // ---------------- the data story (story.json) ----------------
  function story(F, st) {
    var out = [];
    var charts = (st.charts || []).map(function (c) { return chartCard(F, c); });
    if (charts.length) out.push(section('story', T('your_plan.story_title'), charts));
    if ((st.report_card || []).length) {
      out.push(section('report', T('your_plan.report_card'), st.report_card.map(function (r) {
        var lvl = { high: 3, medium: 2, low: 1 }[r.confidence] || 0;
        var bars = svg('<svg width="26" height="18" viewBox="0 0 26 18">' + [0, 1, 2].map(function (i) {
          return '<rect x="' + (i * 9) + '" y="' + (12 - i * 5) + '" width="7" height="' + (6 + i * 5) + '" rx="1.5" fill="' + (i < lvl ? '#14301E' : '#E3D6BF') + '"/>';
        }).join('') + '</svg>');
        return h('div', { class: 'fact' }, h('span', { class: 'ic', style: 'background:#F7F1E4' }, bars),
          h('div', { class: 'grow' }, h('b', null, P(r.thing)), ' ', h('span', { class: 'chip', style: 'margin-left:4px' }, T('your_plan.sure_' + (r.confidence || 'low'))),
            h('p', { class: 'sub', style: 'margin-top:4px' }, P(r.why))));
      })));
    }
    if ((st.satellites || []).length) {
      out.push(section('missions', T('your_plan.missions_title'), st.satellites.map(function (m) {
        return h('div', { class: 'fact' }, h('span', { class: 'ic' }, svg(I('sat', 20))),
          h('div', { class: 'grow' }, h('b', null, [m.mission, m.instrument].filter(Boolean).join(' · ')), m.dataset ? h('div', { class: 'small' }, m.dataset) : null,
            m.job ? h('p', { class: 'sub', style: 'margin-top:4px' }, P(m.job)) : null, m.checked ? h('p', { class: 'small', style: 'margin:2px 0 0' }, svg(I('tick', 13, 3)), ' ', P(m.checked)) : null));
      })));
    }
    if ((st.resources || []).length) {
      out.push(section('links', T('your_plan.links_title'), h('ul', { class: 'lines' }, st.resources.map(function (r) {
        if (typeof r === 'string') return h('li', null, /^https?:\/\//.test(r) ? h('a', { href: r, target: '_blank', rel: 'noopener' }, r) : r);
        var label = P(r.title || r.name || r.label || r) || r.url;
        return h('li', null, r.url ? h('a', { href: r.url, target: '_blank', rel: 'noopener' }, label) : label, r.note ? h('span', { class: 'small' }, ' · ' + P(r.note)) : null);
      }))));
    }
    return out;
  }
  function chartCard(F, c) {
    var body;
    try {
      body = c.kind === 'table' ? table(c) : c.kind === 'bars' ? bars(c) : c.kind === 'timeline' ? timeline(c) : c.kind === 'map' ? mapChart(c) :
        c.kind === 'bands' && !(c.series || []).length ? bandRows(c) : line(c);
    } catch (e) { body = K.notReady(); }
    var tags = (c.sources || []).map(function (name) {
      var hit = (F.sources || []).filter(function (x) { return String(x.name).toLowerCase().indexOf(String(name).toLowerCase()) === 0 || String(name).toLowerCase().indexOf(String(x.name).toLowerCase()) === 0; })[0];
      return hit ? K.srcTag(F, hit) : h('span', { class: 'src' }, svg(I('info', 12)), name);
    });
    return h('figure', { class: 'chart', style: 'margin:0;display:flex;flex-direction:column;gap:8px;padding:12px 0;border-top:1px solid var(--line-2)' },
      h('h3', { class: 'h3' }, P(c.title)), body, h('figcaption', { class: 'sub' }, P(c.caption)),
      h('div', { class: 'srcs' }, h('span', { class: 'small', style: 'font-weight:700' }, T('btn.source_label')), tags));
  }
  // x values of any type onto a number line
  function xinfo(c) {
    var t = (c.x && c.x.type) || 'year', cats = [];
    function key(x) { return typeof x === 'object' && x ? P(x) : String(x); }
    if (t === 'category') (c.series || []).forEach(function (se) { (se.points || []).forEach(function (p) { var k = key(p[0]); if (cats.indexOf(k) < 0) cats.push(k); }); });
    function v(x) {
      if (t === 'date') return Date.parse(x);
      if (t === 'month') { if (typeof x === 'number') return x; var i = K.MONTHS.indexOf(String(x).slice(0, 3)); return i >= 0 ? i + 1 : NaN; }
      if (t === 'category') return cats.indexOf(key(x));
      return +x;
    }
    function lab(n) {
      if (t === 'date') { var d = new Date(n); return digits(d.getFullYear()); }
      if (t === 'month') return K.monthName(K.MONTHS[(Math.round(n) - 1 + 12) % 12], true);
      if (t === 'category') return cats[Math.round(n)] || '';
      return digits(Math.round(n));
    }
    return { t: t, v: v, lab: lab, cats: cats };
  }
  function ticks(lo, hi, n) {
    var span = hi - lo || 1, step = Math.pow(10, Math.floor(Math.log10(span / n))), err = span / n / step;
    step *= err >= 7.5 ? 10 : err >= 3 ? 5 : err >= 1.5 ? 2 : 1;
    var out = []; for (var x = Math.ceil(lo / step) * step; x <= hi + 1e-9; x += step) out.push(+x.toFixed(10));
    return out;
  }
  function frame(c, xs, ys) {
    var Wd = 640, Ht = 300, m = { l: 52, r: 14, t: 18, b: 46 };
    var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs), y0 = Math.min.apply(null, ys), y1 = Math.max.apply(null, ys);
    if (y0 > 0 && y0 < (y1 - y0)) y0 = 0;
    var pad = (y1 - y0) * 0.06 || 1; y1 += pad; if (y0 !== 0) y0 -= pad;
    if (x0 === x1) { x0 -= 1; x1 += 1; }
    var g = s('svg', { viewBox: '0 0 ' + Wd + ' ' + Ht, role: 'img', 'aria-label': P(c.title) });
    var X = function (v) { return m.l + (v - x0) / (x1 - x0) * (Wd - m.l - m.r); }, Y = function (v) { return Ht - m.b - (v - y0) / (y1 - y0) * (Ht - m.t - m.b); };
    ticks(y0, y1, 5).forEach(function (v) {
      g.append(s('line', { x1: m.l, x2: Wd - m.r, y1: Y(v), y2: Y(v), stroke: '#EFE6D4' }));
      g.append(s('text', { x: m.l - 6, y: Y(v) + 4, 'text-anchor': 'end' }, digits(+v.toFixed(2))));
    });
    g.append(s('line', { x1: m.l, x2: Wd - m.r, y1: Ht - m.b, y2: Ht - m.b, stroke: '#CDBF9F' }));
    var yl = c.y ? P(c.y.label) + (c.y.unit ? ' (' + c.y.unit + ')' : '') : '';
    if (yl) g.append(s('text', { x: 4, y: 12, 'font-weight': 700 }, yl));
    if (c.x && c.x.label) g.append(s('text', { x: Wd / 2, y: Ht - 6, 'text-anchor': 'middle', 'font-weight': 700 }, P(c.x.label)));
    return { g: g, X: X, Y: Y, x0: x0, x1: x1, y0: y0, y1: y1, m: m, Wd: Wd, Ht: Ht };
  }
  var DASH = { main: null, compare: '7 5', range: '2 4', marker: null };
  function legendFor(series) {
    return h('div', { class: 'legend' }, series.map(function (se) {
      var role = se.role || 'main';
      var sw = '<svg width="28" height="12" viewBox="0 0 28 12">' + (role === 'marker' ? '<circle cx="14" cy="6" r="4" fill="#14301E"/>' :
        role === 'range' ? '<rect x="1" y="2" width="26" height="8" fill="#C99A5B" fill-opacity=".35"/>' :
        '<line x1="1" y1="6" x2="27" y2="6" stroke="' + (role === 'compare' ? '#9A5426' : '#14301E') + '" stroke-width="2.5"' + (DASH[role] ? ' stroke-dasharray="' + DASH[role] + '"' : '') + '/>') + '</svg>';
      return h('span', { class: 'row', style: 'gap:6px' }, svg(sw), P(se.name));
    }));
  }
  function line(c) {
    var xi = xinfo(c), series = c.series || [], xs = [], ys = [];
    series.forEach(function (se) { (se.points || []).forEach(function (p) { var v = xi.v(p[0]); if (!isNaN(v)) xs.push(v); for (var k = 1; k < p.length; k++) if (p[k] != null) ys.push(+p[k]); }); });
    (c.bands || []).forEach(function (b) { xs.push(xi.v(b.from), xi.v(b.to)); });
    (c.markers || []).forEach(function (mk) { xs.push(xi.v(mk.x)); });
    xs = xs.filter(function (v) { return !isNaN(v); });
    if (!xs.length) return K.notReady();
    if (!ys.length) ys = [0, 1];
    var f = frame(c, xs, ys), g = f.g;
    (c.bands || []).forEach(function (b) {
      var a = f.X(xi.v(b.from)), z = f.X(xi.v(b.to));
      g.append(s('rect', { x: Math.min(a, z), y: f.m.t, width: Math.abs(z - a) || 2, height: f.Ht - f.m.t - f.m.b, fill: '#C8E05A', 'fill-opacity': .22 }));
      g.append(s('text', { x: Math.min(a, z) + 4, y: f.m.t + 12, 'font-weight': 700, fill: '#14301E' }, P(b.label)));
    });
    var tk = xi.t === 'category' ? xi.cats.map(function (x, i) { return i; }) : xi.t === 'month' ? [1, 3, 5, 7, 9, 11] : ticks(f.x0, f.x1, 6);
    tk.forEach(function (v) { g.append(s('text', { x: f.X(v), y: f.Ht - f.m.b + 16, 'text-anchor': 'middle' }, xi.lab(v))); });
    series.forEach(function (se) {
      var role = se.role || 'main', pts = (se.points || []).filter(function (p) { return !isNaN(xi.v(p[0])); }).sort(function (a, b) { return xi.v(a[0]) - xi.v(b[0]); });
      if (!pts.length) return;
      if (role === 'range' && pts[0].length >= 3) {
        var top = pts.map(function (p) { return f.X(xi.v(p[0])).toFixed(1) + ' ' + f.Y(+p[2]).toFixed(1); });
        var bot = pts.slice().reverse().map(function (p) { return f.X(xi.v(p[0])).toFixed(1) + ' ' + f.Y(+p[1]).toFixed(1); });
        g.append(s('path', { d: 'M' + top.join(' L') + ' L' + bot.join(' L') + 'Z', fill: '#C99A5B', 'fill-opacity': .3 }));
        return;
      }
      if (role === 'marker') { pts.forEach(function (p) { g.append(s('circle', { cx: f.X(xi.v(p[0])), cy: f.Y(+p[1]), r: 4.5, fill: '#14301E', stroke: '#fff', 'stroke-width': 1.5 })); }); return; }
      var d = pts.filter(function (p) { return p[1] != null; }).map(function (p, i) { return (i ? 'L' : 'M') + f.X(xi.v(p[0])).toFixed(1) + ' ' + f.Y(+p[1]).toFixed(1); }).join(' ');
      g.append(s('path', { d: d, fill: 'none', stroke: role === 'compare' ? '#9A5426' : role === 'range' ? '#C99A5B' : '#14301E', 'stroke-width': role === 'main' ? 2.6 : 2,
        'stroke-dasharray': DASH[role], 'stroke-linejoin': 'round', 'stroke-linecap': 'round' }));
    });
    (c.markers || []).forEach(function (mk, i) {
      var x = f.X(xi.v(mk.x));
      g.append(s('line', { x1: x, x2: x, y1: f.m.t, y2: f.Ht - f.m.b, stroke: '#9A5426', 'stroke-dasharray': '3 3' }));
      g.append(s('text', { x: x + 4, y: f.m.t + 26 + (i % 3) * 13, fill: '#7A4A20', 'font-weight': 700 }, P(mk.label)));
    });
    return h('div', null, g, series.length > 1 ? legendFor(series) : null);
  }
  function bars(c) {
    var xi = xinfo(Object.assign({}, c, { x: Object.assign({ type: 'category' }, c.x || {}, { type: (c.x && c.x.type === 'month') ? 'month' : 'category' }) }));
    var series = c.series || [], keys = [], ys = [0];
    function key(x) { return typeof x === 'object' && x ? P(x) : String(x); }
    series.forEach(function (se) { (se.points || []).forEach(function (p) { var k = key(p[0]); if (keys.indexOf(k) < 0) keys.push(k); ys.push(+p[1]); }); });
    if (!keys.length) return K.notReady();
    var f = frame(Object.assign({}, c, { x: null }), [0, keys.length], ys), g = f.g, bw = (f.X(1) - f.X(0)) * 0.8 / Math.max(1, series.length);
    keys.forEach(function (k, i) {
      var lab = (c.x && c.x.type === 'month') ? K.monthName(K.MONTHS[(K.MONTHS.indexOf(k.slice(0, 3)) + 12) % 12], true) : (c.x && c.x.type === 'year' ? digits(k) : k);
      g.append(s('text', { x: f.X(i + 0.5), y: f.Ht - f.m.b + 16, 'text-anchor': 'middle' }, lab));
    });
    series.forEach(function (se, j) {
      (se.points || []).forEach(function (p) {
        var i = keys.indexOf(key(p[0])), x = f.X(i + 0.1) + j * bw, y = f.Y(Math.max(0, +p[1])), y0 = f.Y(Math.min(0, +p[1]));
        g.append(s('rect', { x: x, y: Math.min(y, y0), width: bw - 2, height: Math.abs(y0 - y), rx: 3, fill: j === 0 ? '#14301E' : j === 1 ? '#C99A5B' : '#7FB24A',
          stroke: j === 1 ? '#7A4A20' : null, 'stroke-dasharray': j === 1 ? '3 2' : null }));
      });
    });
    if (c.x && c.x.label) {} // drawn by frame()
    return h('div', null, g, series.length > 1 ? legendFor(series.map(function (se, j) { return Object.assign({}, se, { role: j === 1 ? 'compare' : 'main' }); })) : null);
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
  function timeline(c) {
    var xi = xinfo(c), items = (c.markers || []).map(function (m) { return { x: m.x, label: m.label }; });
    (c.series || []).forEach(function (se) { (se.points || []).forEach(function (p) { items.push({ x: p[0], label: p[2] || se.name }); }); });
    items = items.filter(function (it) { return !isNaN(xi.v(it.x)); }).sort(function (a, b) { return xi.v(a.x) - xi.v(b.x); });
    if (!items.length) return K.notReady();
    return h('ol', { class: 'lines', style: 'border-left:3px solid var(--ink);padding-left:14px;gap:10px' }, items.map(function (it) {
      return h('li', null, h('b', null, xi.lab(xi.v(it.x))), ' · ', P(it.label));
    }));
  }
  function table(c) {
    var rows = c.rows || [];
    if (!rows.length) return K.notReady();
    function cell(v) { return v != null && typeof v === 'object' ? P(v) : (typeof v === 'number' ? digits(v) : (v == null ? '' : String(v))); }
    var isObj = rows[0] && typeof rows[0] === 'object' && !Array.isArray(rows[0]) && !('en' in rows[0]);
    var cols = isObj ? Object.keys(rows[0]) : null;
    return h('div', { style: 'overflow-x:auto' }, h('table', null,
      cols ? h('thead', null, h('tr', null, cols.map(function (k) { return h('th', null, k); }))) : null,
      h('tbody', null, rows.map(function (r) { return h('tr', null, (cols ? cols.map(function (k) { return r[k]; }) : (Array.isArray(r) ? r : [r])).map(function (v) { return h('td', null, cell(v)); })); }))));
  }
  function mapChart(c) {
    var el = h('div', { class: 'areamap', style: 'aspect-ratio:4/3' });
    K.loadLeaflet().then(function (L) {
      var m = L.map(el, { scrollWheelZoom: false }), pts = [];
      K.osm(L, m);
      (c.series || []).forEach(function (se) {
        (se.points || []).forEach(function (p) {
          var ll = [+p[1], +p[0]]; if (isNaN(ll[0]) || isNaN(ll[1])) return; pts.push(ll);
          var mk = L.circleMarker(ll, { radius: 7, color: '#14301E', weight: 2, fillColor: se.role === 'compare' ? '#C99A5B' : '#C8E05A', fillOpacity: 1 }).addTo(m);
          var t = document.createElement('span'); t.textContent = P(se.name); mk.bindTooltip(t);
        });
      });
      if (pts.length) m.fitBounds(pts, { padding: [30, 30], maxZoom: 12 }); else m.setView([S.field.field.lat, S.field.field.lon], 9);
      setTimeout(function () { m.invalidateSize(); }, 200);
    });
    return h('div', null, el, (c.series || []).length > 1 ? legendFor(c.series) : null);
  }
})();
