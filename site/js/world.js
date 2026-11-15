/* Fields around the world (owner, 2026-11-15): the world's land outline from data/world.json (Natural Earth 1:110m, public
   domain; pipeline/export/build_world.py), a dot for every prepared field of data/index.json, and "Could Khet Sathi work
   here?": a tap anywhere answers from the FIXED rules of config/rules.yaml global_use (each NASA dataset's coverage from its
   own documentation; build_world.py's coverage(), inside() and haversine_km(), tested in tests/test_world.py, mirrored here).
   The answer never shows a number from a field file for a spot that is not prepared. No outside request: every file is ours.
   Loaded when the page is first opened (app.js SCREENS.world). */
(function () {
  'use strict';
  var K = window.KS, h = K.h, T = K.T, P = K.P, NS = 'http://www.w3.org/2000/svg';
  var README = 'https://github.com/sorenhgautam-dev/data-test-game#how-to-run-it-for-a-new-field';
  var W = null, answer = null, marker = null, ring = null;
  function proj(lon, lat) { var r = lat * Math.PI / 180; return [(lon + 180) / 360 * 1000, (1 - Math.log(Math.tan(Math.PI / 4 + r / 2)) / Math.PI) / 2 * 1000]; }
  function unproj(x, y) { return [Math.atan(Math.sinh(Math.PI * (1 - 2 * y / 1000))) * 180 / Math.PI, x / 1000 * 360 - 180]; }
  function inside(x, y, rings) {
    var hit = false;
    rings.forEach(function (r) {
      for (var n = r.length / 2, i = 0; i < n; i++) {
        var x1 = r[2 * i], y1 = r[2 * i + 1], j = (i + 1) % n, x2 = r[2 * j], y2 = r[2 * j + 1];
        if ((y1 > y) !== (y2 > y) && x < (x2 - x1) * (y - y1) / (y2 - y1) + x1) hit = !hit;
      }
    });
    return hit;
  }
  function km(lat1, lon1, lat2, lon2) {
    var p1 = lat1 * Math.PI / 180, p2 = lat2 * Math.PI / 180, dl = (lon2 - lon1) * Math.PI / 180;
    var a = Math.pow(Math.sin((p2 - p1) / 2), 2) + Math.cos(p1) * Math.cos(p2) * Math.pow(Math.sin(dl / 2), 2);
    return 2 * 6371 * Math.asin(Math.sqrt(a));
  }
  function el(tag, a) { var e = document.createElementNS(NS, tag); Object.keys(a || {}).forEach(function (k) { e.setAttribute(k, a[k]); }); return e; }
  function fields() { return (K.S.index && K.S.index.fields) || []; }
  // fields within 2 degrees of a place's first field share its dot (Bhaktapur's fields lie a few km apart)
  function places() {
    var out = [];
    fields().forEach(function (f) {
      var p = out.filter(function (q) { return Math.abs(q.lat - f.lat) < 2 && Math.abs(q.lon - f.lon) < 2; })[0];
      if (!p) { p = { lat: f.lat, lon: f.lon, country: f.country, fields: [] }; out.push(p); }
      p.fields.push(f);
    });
    return out;
  }
  function openField(f) { K.chooseField(f.id); K.go('photo'); }
  function fieldBtn(f) {
    return h('button', { type: 'button', class: 'pf', 'aria-pressed': String(f.id === K.S.fid), onclick: function () { openField(f); } },
      h('span', null, h('b', null, f.name), f.note ? [h('br'), h('span', { class: 'small' }, P(f.note))] : null),
      K.svg(K.I(f.id === K.S.fid ? 'tick' : 'arrow', 18)));
  }
  function deg(v, pos, neg) { return K.digits(Math.abs(v).toFixed(1)) + '° ' + (v >= 0 ? pos : neg); }
  // the answer for one spot: coverage, crops, what we can't do yet, the nearest field; never a number from a field file
  function answerAt(lat, lon) {
    if (!W || !answer) return;
    var xy = proj(lon, lat), land = inside(xy[0], xy[1], W.outline.rings);
    marker.setAttribute('cx', xy[0].toFixed(1)); marker.setAttribute('cy', xy[1].toFixed(1)); marker.style.display = '';
    ring.setAttribute('cx', xy[0].toFixed(1)); ring.setAttribute('cy', xy[1].toFixed(1)); ring.style.display = '';
    var here = fields().filter(function (f) { var b = f.bbox; return b && lon >= b[0] && lon <= b[2] && lat >= b[1] && lat <= b[3]; })[0];
    var near = fields().map(function (f) { return [f, km(lat, lon, f.lat, f.lon)]; }).sort(function (a, b) { return a[1] - b[1]; })[0];
    var rows = W.coverage.map(function (c) {
      var ok = lat >= c.lat[0] && lat <= c.lat[1] && (land || !c.land_only);
      var st = !ok ? 'no' : (c.caution_abs_lat != null && Math.abs(lat) > c.caution_abs_lat ? 'caution' : 'yes');
      return h('li', { class: 'wc ' + st }, K.svg(K.I(st === 'yes' ? 'tick' : st === 'no' ? 'cross' : 'warn', 18, 2.6)),
        h('span', null, h('b', null, T('farm.w_' + c.what)), ' · ', c.name, h('br'), h('span', { class: 'small' }, T(st === 'yes' ? 'farm.world_yes' : st === 'no' ? 'farm.world_no' : 'farm.world_caution'))));
    });
    answer.textContent = '';
    K.add(answer, [
      h('p', { class: 'wspot' }, K.svg(K.I('pin', 18)), deg(lat, 'N', 'S') + ', ' + deg(lon, 'E', 'W'), land ? null : [' · ', T('farm.world_sea')]),
      here ? h('div', { class: 'card soft' }, h('p', { class: 'lead', style: 'margin:0 0 8px' }, T('farm.world_here')), K.btn2(T('farm.world_open') + ': ' + here.name, function () { openField(here); }, 'arrow')) : null,
      h('p', { class: 'wh' }, T('farm.world_covers')), h('ul', { class: 'wcov' }, rows),
      h('p', { class: 'wh' }, T('farm.world_crops')), h('p', { class: 'wtxt' }, W.crops.map(function (c) { return K.crop(c); }).join(', ')),
      h('p', { class: 'small' }, T('farm.world_crops_need')),
      h('p', { class: 'wh' }, T('farm.world_cant')), K.lines(['world_nm_snow', 'world_nm_orchards', 'world_nm_other'].map(function (k) { return T('farm.' + k); })),
      near ? [h('p', { class: 'wh' }, T('farm.world_nearest')), h('p', { class: 'wtxt' }, h('b', null, near[0].name), ' · ' + K.digits(Math.round(near[1]).toLocaleString('en-US')) + ' ' + T('farm.world_km'))] : null,
      here ? null : h('div', { class: 'card soft' }, K.lines([T('farm.world_not_ready'), T('farm.world_one_command'), T('farm.world_hours')]),
        h('a', { class: 'judges', href: README, target: '_blank', rel: 'noopener' }, K.svg(K.I('book', 16)), T('farm.world_readme'))),
      here ? null : h('p', { class: 'small' }, T('farm.world_no_numbers'))]);
  }
  function mapBox(w) {
    var o = w.outline, box = h('div', { class: 'wmap', style: 'aspect-ratio:' + o.size + '/' + (o.y1 - o.y0).toFixed(1) });
    var s = el('svg', { viewBox: '0 ' + o.y0 + ' ' + o.size + ' ' + (o.y1 - o.y0).toFixed(1), class: 'wsvg', role: 'img', 'aria-label': T('farm.world_tap_any') });
    s.append(el('rect', { x: 0, y: o.y0, width: o.size, height: o.y1 - o.y0, class: 'sea' }),
      el('path', { d: o.rings.map(function (r) { for (var d = 'M' + r[0] + ' ' + r[1], i = 2; i < r.length; i += 2) d += 'L' + r[i] + ' ' + r[i + 1]; return d + 'Z'; }).join(''), class: 'land', 'fill-rule': 'evenodd' }));
    ring = el('circle', { r: 14, class: 'tapring', style: 'display:none' }); marker = el('circle', { r: 6, class: 'tap', style: 'display:none' });
    s.append(ring, marker);
    s.addEventListener('click', function (e) {
      var r = s.getBoundingClientRect(), x = (e.clientX - r.left) / r.width * o.size, y = o.y0 + (e.clientY - r.top) / r.height * (o.y1 - o.y0), ll = unproj(x, y);
      answerAt(ll[0], ll[1]);
    });
    box.append(s);
    places().forEach(function (p) {
      var xy = proj(p.lon, p.lat), left = xy[0] / o.size * 100, top = (xy[1] - o.y0) / (o.y1 - o.y0) * 100;
      box.append(h('button', { type: 'button', class: 'wdot' + (left > 50 ? ' w' : ''), style: 'left:' + left.toFixed(2) + '%;top:' + top.toFixed(2) + '%',
        onclick: function () { answerAt(p.lat, p.lon); } }, h('i', { 'aria-hidden': 'true' }), h('span', null, p.country + ' · ' + K.digits(p.fields.length))));
    });
    return box;
  }
  function list(titleKey, keys) { return h('div', null, h('p', { class: 'wh' }, T('farm.' + titleKey)), K.lines(keys.map(function (k) { return T('farm.' + k); }))); }
  K.worldAt = function (lat, lon) { answerAt(lat, lon); if (answer) answer.scrollIntoView({ block: 'start' }); };   // for the screenshots
  K.world = function () {
    answer = h('div', { class: 'wanswer', 'aria-live': 'polite' }, h('p', { class: 'small' }, T('farm.world_tap_any')));
    var mapSlot = h('div', null, K.loading());
    K.getJSON('data/world.json').then(function (w) { W = w; mapSlot.textContent = ''; mapSlot.append(w ? mapBox(w) : K.notReady()); });
    var lists = places().map(function (p) {
      return h('div', { class: 'wplace' }, h('p', { class: 'wcountry' }, K.svg(K.I('pin', 16)), p.country), h('div', { class: 'prepared' }, p.fields.map(fieldBtn)));
    });
    return h('div', { class: 'how world' },
      h('section', { id: 'how-could' }, h('h2', { class: 'h2' }, T('farm.world_could_title')), mapSlot, answer, h('p', { class: 'small' }, T('farm.world_map_src'))),
      h('section', null, lists),
      h('section', { id: 'how-anywhere' }, list('world_anywhere', ['world_any_1', 'world_any_2', 'world_any_3', 'world_any_4', 'world_any_5']),
        list('world_nepal_only', ['world_np_1', 'world_np_2', 'world_np_3', 'world_np_4'])),
      h('section', { id: 'how-own' }, h('h2', { class: 'h2' }, T('farm.world_own_title')),
        h('ol', { class: 'wsteps' }, ['world_step_1', 'world_step_2', 'world_step_3'].map(function (k) { return h('li', null, T('farm.' + k)); })),
        h('a', { class: 'judges', href: README, target: '_blank', rel: 'noopener' }, K.svg(K.I('book', 16)), T('farm.world_readme'))));
  };
})();
