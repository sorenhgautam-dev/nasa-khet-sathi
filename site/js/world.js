/* Fields around the world (owner, 2026-11-15): every prepared field of data/index.json on NASA's Blue Marble picture
   (data/basemap/world.jpg, already in the site and credited in data/basemap/world.json: no outside request), one dot per
   place, each field opening its own steps with its own labels; then three plain steps to run it for your own field.
   Loaded when the page is first opened (app.js SCREENS.world). */
(function () {
  'use strict';
  var K = window.KS, h = K.h, T = K.T, P = K.P;
  var N = 1024, TOP = 75, BOT = -60;   // world.jpg: a Web Mercator square, 1024 px; the latitudes shown
  var README = 'https://github.com/sorenhgautam-dev/data-test-game#how-to-run-it-for-a-new-field';
  function my(lat) { var r = lat * Math.PI / 180; return (1 - Math.log(Math.tan(Math.PI / 4 + r / 2)) / Math.PI) / 2 * N; }
  // fields within 2 degrees of a place's first field share its dot (Bhaktapur's fields lie a few km apart)
  function places(fields) {
    var out = [];
    fields.forEach(function (f) {
      var p = out.filter(function (q) { return Math.abs(q.lat - f.lat) < 2 && Math.abs(q.lon - f.lon) < 2; })[0];
      if (!p) { p = { lat: f.lat, lon: f.lon, country: f.country, fields: [] }; out.push(p); }
      p.fields.push(f);
    });
    return out;
  }
  function fieldBtn(f) {
    return h('button', { type: 'button', class: 'pf', 'aria-pressed': String(f.id === K.S.fid), onclick: function () { K.chooseField(f.id); K.go('photo'); } },
      h('span', null, h('b', null, f.name), f.note ? [h('br'), h('span', { class: 'small' }, P(f.note))] : null),
      K.svg(K.I(f.id === K.S.fid ? 'tick' : 'arrow', 18)));
  }
  K.world = function () {
    var ix = (K.S.index && K.S.index.fields) || [], ps = places(ix), y0 = my(TOP), y1 = my(BOT);
    var lists = ps.map(function (p, i) {
      return h('div', { class: 'wplace', id: 'wplace-' + i }, h('p', { class: 'wcountry' }, K.svg(K.I('pin', 16)), p.country),
        h('div', { class: 'prepared' }, p.fields.map(fieldBtn)));
    });
    var map = h('div', { class: 'wmap', role: 'group', 'aria-label': T('farm.world_title'), style: 'aspect-ratio:' + N + '/' + (y1 - y0).toFixed(1) },
      h('img', { src: 'data/basemap/world.jpg', alt: '', width: String(N), height: String(N), decoding: 'async', style: 'margin-top:-' + (y0 / N * 100).toFixed(3) + '%' }),
      ps.map(function (p, i) {
        var left = (p.lon + 180) / 360 * 100, top = (my(p.lat) - y0) / (y1 - y0) * 100;
        return h('button', { type: 'button', class: 'wdot' + (left > 50 ? ' w' : ''), style: 'left:' + left.toFixed(2) + '%;top:' + top.toFixed(2) + '%',
          onclick: function () { var el = document.getElementById('wplace-' + i); if (el) { el.scrollIntoView({ behavior: K.RM ? 'auto' : 'smooth', block: 'center' }); var b = el.querySelector('button'); if (b) b.focus({ preventScroll: true }); } } },
          h('i', { 'aria-hidden': 'true' }), h('span', null, p.country + ' · ' + K.digits(p.fields.length)));
      }));
    return h('div', { class: 'how world' },
      h('section', null, map, h('p', { class: 'small' }, T('farm.world_tap')), h('p', { class: 'small' }, T('farm.world_map_src'))),
      h('section', null, lists),
      h('section', { id: 'how-own' }, h('h2', { class: 'h2' }, T('farm.world_own_title')),
        h('ol', { class: 'wsteps' }, ['world_step_1', 'world_step_2', 'world_step_3'].map(function (k) { return h('li', null, T('farm.' + k)); })),
        h('a', { class: 'judges', href: README, target: '_blank', rel: 'noopener' }, K.svg(K.I('book', 16)), T('farm.world_readme'))));
  };
})();
