/* Khet Sathi: "Behind the scenes: your field, seen by NASA" (owner, 2026-11-15). Loaded only when the section is
   scrolled to, when How we know opens, or when a farmer answer's source tag is tapped. Every number and word comes from
   site/data/behind.json (pipeline/export/build_behind.py: counted from our own outputs); the charts are the ones in
   site/data/story.json, drawn by js/how.js. Text is set with textContent. No outside request. */
(function () {
  'use strict';
  var K = window.KS, h = K.h, T = K.T, P = K.P, S = K.S, svg = K.svg, I = K.I, digits = K.digits, D = document;
  var NS = 'http://www.w3.org/2000/svg', dataP = null;
  function s(tag, a, text) {
    var el = D.createElementNS(NS, tag);
    Object.keys(a || {}).forEach(function (k) { el.setAttribute(k, a[k]); });
    if (text != null) el.textContent = text;
    return el;
  }
  // behind.json, the charts of story.json and their drawing code (js/how.js); null when a file is missing, or when
  // behind.json was built for another field than the one open (its numbers are never shown on another field)
  function data() {
    dataP = dataP || Promise.all([K.getJSON('data/behind.json'), K.getJSON('data/story.json'),
      K.how ? null : new Promise(function (res) { var el = h('script', { src: 'js/how.js' }); el.onload = res; el.onerror = res; D.head.append(el); })]).then(function (r) {
      if (!r[0] || !r[1] || !K.how || !K.how.plot) return null;
      var by = {}; (r[1].charts || []).concat(r[0].charts || []).forEach(function (c) { by[c.id] = c; });
      return { b: r[0], charts: by };
    });
    return dataP.then(function (d) { return d && d.b.field === S.fid ? d : null; });
  }
  function count(n) { return digits(String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ',')); }
  function size(m, u) { return m >= 1000 ? digits(+(m / 1000).toFixed(1)) + ' ' + P(u.km) : digits(Math.round(m)) + ' ' + P(u.m); }
  // a source tag: name and years (the name alone inside a number's tile); a tap opens the source list (product, square size)
  function pill(src, short) { var b = K.srcTag(null, src); if (short) b.lastChild.textContent = String(src.name).replace(/\s*\(.*$/, ''); return b; }

  // ---------------- the big numbers, counted from our own files ----------------
  function tiles(b) {
    var all = b.numbers.filter(function (n) { return n.sources.length > 2; })[0];   // the datasets: one tag each, under the tiles
    return [h('div', { class: 'bnums' }, b.numbers.map(function (n, i) {
      return h('div', { class: 'bnum', style: 'animation-delay:' + (i * 70) + 'ms' }, h('b', null, count(n.value)), h('span', { class: 'bl' }, P(n.label)),
        h('span', { class: 'small' }, P(n.detail)), n.sources.length <= 2 ? h('div', { class: 'srcs' }, n.sources.map(function (x) { return pill(x, true); })) : null);
    })), all ? h('div', { class: 'srcs' }, all.sources.map(function (x) { return pill(x); })) : null];
  }
  // ---------------- NASA data, the field twin, the replay, the farmer's answers ----------------
  function flow(b) {
    return h('ol', { class: 'bflow' }, b.flow.map(function (f, i) {
      return h('li', null, i ? svg(I('arrow', 18, 2.6)) : null, h('span', { class: i === b.flow.length - 1 ? 'last' : '' }, P(f)));
    }));
  }
  // ---------------- one card per NASA mission: a real chart and one plain sentence ----------------
  function plot(d, c) {
    var ch = d.charts[c.chart];
    if (!ch) return K.notReady();
    if (c.only) {   // some rows of a chart only (SMAP and GLDAS among the checks)
      var keep = function (id) { return c.only.indexOf(id) >= 0; };
      ch = Object.assign({}, ch, { x: Object.assign({}, ch.x, { categories: ch.x.categories.filter(function (k) { return keep(k.id); }) }),
        series: ch.series.map(function (se) { return Object.assign({}, se, { points: se.points.filter(function (p) { return keep(p[0]); }) }); }) });
    }
    // bars with one value and a range: how.js names the range only beside a second value, so it is named here
    var rg = ch.kind === 'bars' && ch.series.length === 2 ? ch.series.filter(function (se) { return se.role === 'range'; })[0] : null;
    try { return h('figure', { class: 'bplot' }, h('figcaption', { class: 'small' }, P(ch.title)), K.how.plot(ch),
      rg ? h('p', { class: 'small', style: 'margin:0' }, svg('<svg width="28" height="12" viewBox="0 0 28 12"><path d="M3 1v10M25 1v10M3 6h22" stroke="#7A4A20" stroke-width="2" fill="none"/></svg>'), ' ', P(rg.name)) : null,
      ch.note ? h('p', { class: 'small', style: 'margin:0' }, svg(I('info', 13)), ' ', P(ch.note)) : null); }
    catch (e) { if (window.console) console.warn('chart', c.chart, e); return K.notReady(); }
  }
  function card(d, c) {
    return h('article', { class: 'bcard', id: 'behind-' + c.id },
      h('div', { class: 'bhead' }, h('span', { class: 'ic' }, svg(I(c.kind === 'model' ? 'pc' : 'sat', 20))),
        h('div', { class: 'grow' }, h('h3', { class: 'h3' }, c.mission), h('p', { class: 'small', style: 'margin:0' }, T('kind.' + c.kind) + ' · ' + c.resolution))),
      h('p', { class: 'lead' }, P(c.say)), plot(d, c),
      h('div', { class: 'srcs' }, pill({ name: c.source, resolution: c.resolution, years: c.years, type: c.kind })),
      c.also ? h('p', { class: 'small', style: 'margin:0' }, c.also) : null);
  }
  // ---------------- each dataset's square over the field, true to scale inside each picture ----------------
  // The squares differ ten-thousandfold, so they are drawn in steps: squares of a similar size share a picture, and each
  // picture also holds the biggest thing of the picture before it (the field first), at its true size (a dot when tiny).
  var DASH = [null, '6 4', '2 4', '10 4 2 4'];
  function pixelPics(b) {
    var px = b.pixels, groups = [], W = 150, k = 0;
    px.squares.forEach(function (q) { var g = groups[groups.length - 1]; if (g && q.size_m <= g[0].size_m * 3) g.push(q); else groups.push([q]); });
    var inner = { size_m: px.field_m, field: true };
    return h('div', { class: 'bpix' }, groups.map(function (g) {
      var span = Math.max(g[g.length - 1].size_m, inner.size_m) * 1.3, sc = W / span, sv = s('svg', { viewBox: '0 0 ' + W + ' ' + W, role: 'img', class: 'pix', 'aria-label': g.map(function (q) { return q.name + ' ' + size(q.size_m, b.units); }).join(', ') });
      function box(q, cls, dash) {
        var w = q.size_m * sc, x = (W - w) / 2;
        if (w < 5) { sv.append(s('circle', { cx: W / 2, cy: W / 2, r: 3, class: cls })); return; }
        sv.append(s('rect', { x: x.toFixed(1), y: x.toFixed(1), width: w.toFixed(1), height: w.toFixed(1), class: cls, 'stroke-dasharray': dash || '' }));
      }
      var first = inner.field && g[0].size_m < inner.size_m;   // squares smaller than the field: drawn as a grid over it
      if (first) {
        box(inner, 'pf');
        var w = inner.size_m * sc, x0 = (W - w) / 2, st = g[0].size_m * sc;
        for (var v = st; v < w - 0.5; v += st) { sv.append(s('line', { x1: x0 + v, y1: x0, x2: x0 + v, y2: x0 + w, class: 'pg' })); sv.append(s('line', { x1: x0, y1: x0 + v, x2: x0 + w, y2: x0 + v, class: 'pg' })); }
        sv.append(s('rect', { x: x0.toFixed(1), y: x0.toFixed(1), width: st.toFixed(1), height: st.toFixed(1), class: 'ps' }));
      } else {
        g.slice().reverse().forEach(function (q) { box(q, 'ps', DASH[k++ % 4]); });
        box(inner, inner.field ? 'pf' : 'pi');
      }
      var lines = g.map(function (q) { return h('li', null, h('b', null, q.name + ' · ' + size(q.size_m, b.units)), ' · ' + P(q.what)); });
      lines.push(h('li', { class: 'small' }, (inner.field ? T('where.your_farm') : inner.name) + ' · ' + size(inner.size_m, b.units)));
      if (!first) inner = g[g.length - 1];   // the next picture holds this one's biggest thing (the field after the first)
      return h('figure', { class: 'bpixf' }, sv, h('ul', { class: 'lines' }, lines));
    }));
  }

  function section(d) {
    var b = d.b;
    return h('div', { class: 'behind' }, b.placeholder ? K.sampleChip() : null, tiles(b), flow(b),
      h('div', { class: 'bcards' }, b.cards.map(function (c) { return card(d, c); }),
        h('article', { class: 'bcard', id: 'behind-pixels' }, h('div', { class: 'bhead' }, h('span', { class: 'ic' }, svg(I('near', 20))),
          h('div', { class: 'grow' }, h('h3', { class: 'h3' }, b.pixels.squares.map(function (q) { return size(q.size_m, b.units); }).join(' · ')))),
          h('p', { class: 'lead' }, P(b.pixels.say)), pixelPics(b), h('p', { class: 'small', style: 'margin:0' }, svg(I('info', 13)), ' ', P(b.pixels.note)))));
  }
  K.behind = {
    // the whole section (a Promise of its element; null when there is none for this field)
    section: function () { return data().then(function (d) { return d ? section(d) : null; }); },
    // the cards behind a farmer answer's source tag, in a sheet (kind: rain, weather or space; behind.json `tags`)
    open: function (kind) {
      function build() {
        var panel = K.openSheet(build), body = h('div', { class: 'col', style: 'display:flex;flex-direction:column;gap:12px;margin-top:8px' }, K.loading());
        K.add(panel, [K.sheetBar(T('farm.behind_title')), body]);
        data().then(function (d) {
          var ids = (d && d.b.tags[kind]) || [], cs = ids.map(function (id) { return d.b.cards.filter(function (x) { return x.id === id; })[0]; }).filter(Boolean);
          body.textContent = '';
          K.add(body, cs.length ? [h('div', { class: 'behind' }, cs.map(function (c) { return card(d, c); })),
            K.btn3(T('btn.how_we_know'), function () { K.closeSheet(); K.go('how/behind'); }, 'book')] : K.notReady());
        });
        panel.focus();
      }
      build();
    }
  };
})();
