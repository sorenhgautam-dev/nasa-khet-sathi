/* Khet Sathi: the four features on Home (owner, 2026-11-14), loaded when one is first opened.
   25-Year Replay (data/replay/<id>.json), Field Pulse (data/pulse/<id>.json), Safe Trial (no file: the farmer's own
   trial, kept on the phone) and the record check-up (data/checkup/<id>.json). Every number comes from those files or
   the field file; text goes on the page with textContent. Photos stay on the phone (IndexedDB). */
(function () {
  'use strict';
  var K = window.KS, S = K.S, h = K.h, add = K.add, svg = K.svg, I = K.I, T = K.T, L = K.L, P = K.P, PL = K.PL, num = K.num, digits = K.digits;
  var D = document;

  function card(cls) { var c = h('div', { class: 'card ' + (cls || ''), style: 'display:flex;flex-direction:column;gap:10px' }); for (var i = 1; i < arguments.length; i++) add(c, arguments[i]); return c; }
  function stepH(t) { return h('h2', { class: 'h3' }, t); }
  function sample(F) { return K.isPlaceholder(F.field.name) ? K.sampleChip() : null; }
  function today() { var d = new Date(); return d.getFullYear() + '-' + ('0' + (d.getMonth() + 1)).slice(-2) + '-' + ('0' + d.getDate()).slice(-2); }
  function srcList(F, list) {
    var seen = {};
    return h('div', { class: 'srcs' }, (list || []).filter(function (s) { if (!s || !s.name || seen[s.name]) return false; seen[s.name] = 1; return true; }).map(function (s) { return K.srcTag(F, s); }));
  }
  function stop() { return /^(ne|hi|bn)$/.test(S.lang) ? '।' : '.'; }
  function cap(s) { return /^(ne|hi|bn)$/.test(S.lang) ? s : s.charAt(0).toUpperCase() + s.slice(1); }
  function readJSON(k) { try { return JSON.parse(K.store.get(k) || 'null'); } catch (e) { return null; } }

  // ---------------- 3 Safe Trial: one quarter of the field, the soil stick's four spots, a photo each week ----------------
  // No new numbers: the results come after the season. Everything the farmer enters stays on this phone.
  var QUARTERS = [[0, 0], [50, 0], [0, 50], [50, 50]];   // left, top (%) of each quarter of the field's box
  function quarterNames(F) {
    var G = K.geom(F);
    return QUARTERS.map(function (q, i) {
      if (G.length !== 4) return digits(i + 1);
      var g = G.filter(function (x) { return x.cx >= q[0] && x.cx < q[0] + 50 && x.cy >= q[1] && x.cy < q[1] + 50; })[0];
      return g ? g.n : digits(i + 1);
    });
  }
  function photoDB() {
    return new Promise(function (res, rej) {
      try {
        var rq = window.indexedDB.open('khet-sathi', 1);
        rq.onupgradeneeded = function () { rq.result.createObjectStore('photos', { keyPath: 'id', autoIncrement: true }); };
        rq.onsuccess = function () { res(rq.result); };
        rq.onerror = function () { rej(rq.error); };
      } catch (e) { rej(e); }
    });
  }
  function tx(db, mode, fn) {
    return new Promise(function (res, rej) {
      var t = db.transaction('photos', mode), st = t.objectStore('photos'), out = fn(st);
      t.oncomplete = function () { res(out && out.result !== undefined ? out.result : null); };
      t.onerror = function () { rej(t.error); };
    });
  }
  // a smaller copy of the photo (longest side 1024 px), so a season of photos fits on a cheap phone
  function shrink(file) {
    return new Promise(function (res) {
      var url = URL.createObjectURL(file), img = new Image();
      img.onload = function () {
        var k = Math.min(1, 1024 / Math.max(img.naturalWidth, img.naturalHeight)), c = D.createElement('canvas');
        c.width = Math.round(img.naturalWidth * k); c.height = Math.round(img.naturalHeight * k);
        c.getContext('2d').drawImage(img, 0, 0, c.width, c.height);
        URL.revokeObjectURL(url);
        c.toBlob(function (b) { res(b || file); }, 'image/jpeg', 0.8);
      };
      img.onerror = function () { URL.revokeObjectURL(url); res(file); };
      img.src = url;
    });
  }
  function trial(F) {
    var key = 'trial.' + S.fid, saved = readJSON(key) || {};
    var o = K.orderedPlans(F), tries = o.rest.length ? o.rest : [o.cur];
    var st = { plan: saved.plan || tries[0].id, quarter: saved.quarter != null ? saved.quarter : 0, start: saved.start || null };
    var names = quarterNames(F), body = h('div', { class: 'trial' });
    function save() { K.store.set(key, JSON.stringify(st)); }
    function draw() {
      body.textContent = '';
      var planBtns = h('div', { class: 'col', role: 'group', 'aria-label': T('check_soil.trial_pick_plan') }, tries.map(function (p) {
        return h('button', { type: 'button', class: 'choice wide', 'aria-pressed': String(st.plan === p.id), onclick: function () { st.plan = p.id; if (st.start) save(); draw(); } },
          h('span', { style: 'display:flex;flex-direction:column;gap:2px;text-align:left' }, h('b', null, K.planName(p)), h('span', { class: 'small' }, K.cropsLine(p))));
      }));
      // the field in four quarters, the trial quarter marked with a tick and a word, the stick's four spots
      var box = h('div', { class: 'qbox', role: 'group', 'aria-label': T('check_soil.trial_pick_part') }, QUARTERS.map(function (q, i) {
        var on = st.quarter === i;
        return h('button', { type: 'button', class: 'qpart' + (on ? ' on' : ''), 'aria-pressed': String(on), style: 'left:' + q[0] + '%;top:' + q[1] + '%',
          onclick: function () { st.quarter = i; if (st.start) save(); draw(); } },
          h('span', { class: 'qn' }, T('each_part.part_name', { section: names[i] })),
          h('span', { class: 'spot' + (on ? ' t' : '') }, svg(I('stick', 16, 2.2))),
          h('span', { class: 'qw' }, on ? [svg(I('tick', 14, 3)), ' ', T('check_soil.trial_this')] : T('check_soil.trial_as_now')));
      }));
      var p = tries.filter(function (x) { return x.id === st.plan; })[0] || tries[0];
      add(body, [
        card('', stepH(T('check_soil.trial_pick_plan')), planBtns),
        card('', stepH(T('check_soil.trial_pick_part')), box, K.lines([T('check_soil.trial_rest')], 'sub')),
        card('', stepH(T('check_soil.trial_spots')), K.lines([T('check_soil.trial_spot_one'), T('check_soil.trial_spot_three')]),
          h('p', { class: 'small', style: 'margin:0' }, T('check_soil.prototype'))),
        st.start ? null : K.cta(T('check_soil.trial_start'), function () { st.start = today(); save(); draw(); }),
        st.start ? card('', h('p', { class: 'lead', style: 'margin:0' }, svg(I('tick', 18, 3)), ' ', T('check_soil.trial_started') + ' ' + K.fmtDate(st.start)),
          h('p', { class: 'sub' }, K.planName(p) + ' · ' + T('each_part.part_name', { section: names[st.quarter] })), h('p', { class: 'small', style: 'margin:0' }, T('check_soil.trial_saved'))) : null,
        st.start ? diary(st) : null,
        card('', stepH(T('check_soil.trial_compare')),
          h('div', { class: 'fact' }, h('span', { class: 'ic' }, svg(I('quarter', 20))), K.lines([T('check_soil.trial_vs_rest')])),
          h('div', { class: 'fact' }, h('span', { class: 'ic' }, svg(I('redo', 20))), h('div', { class: 'grow' }, K.lines([T('check_soil.trial_vs_replay')]),
            K.btn3(K.featName('replay'), function () { K.go('replay'); }, 'redo'))),
          h('p', { class: 'note', style: 'margin:0' }, T('check_soil.trial_after'), ' ', T('check_soil.trial_no_numbers')))
      ]);
    }
    function diary(st) {
      var box = card('', stepH(T('check_soil.trial_diary'))), grid = h('div', { class: 'photos' }), msg = h('p', { class: 'small', style: 'margin:0' }, T('check_soil.trial_photo_phone'));
      var input = h('input', { type: 'file', accept: 'image/*', capture: 'environment', class: 'vh', id: 'trial-photo' });
      var addBtn = h('label', { for: 'trial-photo', class: 'btn2' }, svg(I('camera', 18)), T('check_soil.trial_photo_add'));
      add(box, [input, addBtn, msg, grid]);
      var urls = [];
      function week(d) { return Math.floor((new Date(d) - new Date(st.start)) / 6048e5) + 1; }
      function show(db) {
        tx(db, 'readonly', function (s) { return s.getAll(); }).then(function (all) {
          urls.forEach(URL.revokeObjectURL); urls = [];
          var mine = (all || []).filter(function (x) { return x.fid === S.fid && x.start === st.start; }).sort(function (a, b) { return a.date < b.date ? 1 : -1; });
          grid.textContent = '';
          if (!mine.length) { grid.append(h('p', { class: 'small', style: 'margin:0' }, T('check_soil.trial_photo_none'))); return; }
          mine.forEach(function (x) {
            var u = URL.createObjectURL(x.blob); urls.push(u);
            grid.append(h('figure', null, h('img', { src: u, alt: T('check_soil.trial_week') + ' ' + digits(week(x.date)), width: '160', height: '120', loading: 'lazy' }),
              h('figcaption', null, h('b', null, T('check_soil.trial_week') + ' ' + digits(week(x.date))), h('br'), K.fmtDate(x.date)),
              h('button', { type: 'button', class: 'btn3 small', onclick: function () { tx(db, 'readwrite', function (s) { return s.delete(x.id); }).then(function () { show(db); }); } }, T('check_soil.trial_remove'))));
          });
        }).catch(cannot);
      }
      function cannot() { msg.textContent = T('check_soil.trial_photo_cannot'); addBtn.hidden = true; }
      photoDB().then(function (db) {
        show(db);
        input.addEventListener('change', function () {
          var f = input.files && input.files[0]; if (!f) return;
          shrink(f).then(function (b) { return tx(db, 'readwrite', function (s) { return s.add({ fid: S.fid, start: st.start, date: today(), blob: b }); }); })
            .then(function () { input.value = ''; show(db); }).catch(cannot);
        });
      }).catch(cannot);
      return box;
    }
    draw();
    return K.screen('trial', {
      head: [K.bigTitle(T('check_soil.trial_h1'), T('check_soil.trial_h2')), h('p', { class: 'lead' }, T('check_soil.trial_sub')), sample(F)],
      body: body,
      cta: K.btn3(T('btn.how_we_know'), function () { K.go('how'); }, 'book')
    });
  }

  // ---------------- 1 the Replay: each plan's coming months run through every past season ----------------
  var RES = { worked: 'tick', struggled: 'warn', failed: 'cross' };
  var BAND = { 'needs water': 'band_needs_water', good: 'band_good', 'too wet': 'band_too_wet' };
  function resIcon(r) { return svg(I(RES[r] || 'eq', 16, 2.8)); }
  function resWord(r) { return T('last_years.res_' + (r || 'none')); }
  function monthOf(mm) { return K.monthName(K.MONTHS[+mm - 1]); }
  function pair(label, value) { return h('p', { class: 'kv' }, h('span', null, label), ' ', h('b', null, value)); }
  // the soil stick's latest band (live.json during the demo, else the recorded readings), or null
  function stickBand() {
    return Promise.all([K.getJSON('data/live.json', true), K.getJSON('data/probe_log.json')]).then(function (r) {
      var lv = r[0], log = r[1], last = null;
      var lp = lv && (lv.parts || []).filter(function (x) { return x && x.band; }).pop();
      if (lv && (lv.band || lp)) return { band: lv.band || lp.band, time: lv.time };
      var rd = log && (log.readings || (log.sessions || []).reduce(function (a, s) { return a.concat(s.parts || []); }, []));
      (rd || []).forEach(function (x) { if (x && x.band) last = x; });
      return last ? { band: last.band, time: last.time || last.date } : null;
    });
  }
  function replay(F, R) {
    if (!R || !R.plans || !R.windows || !R.windows.length) return null;
    S.years = R.year_count;
    var cur = R.plans.filter(function (p) { return p.role === 'current'; })[0];
    var opt = S.winter && R.plans.filter(function (p) { return p.id === S.winter && p.role === 'current_option'; })[0];
    var plans = [opt || cur].concat(R.plans.filter(function (p) { return p.role === 'suggested'; })).filter(Boolean);
    var st = { win: S.rpWin || R.windows[0].id, plan: S.rpPlan || plans[0].id, start: R.start_default, by: 'default', sel: null };
    if (!plans.some(function (p) { return p.id === st.plan; })) st.plan = plans[0].id;
    var same = (R.enso && R.enso.same_as_now) || [], box = h('div', { class: 'col', style: 'gap:14px' });
    function pname(p) { return K.planName({ id: p.role === 'suggested' ? p.id : 'current' }); }
    function chips(list, cur, set, label) {
      return h('div', { class: 'prio', role: 'group', 'aria-label': label }, list.map(function (x) {
        return h('button', { type: 'button', class: 'choice', 'aria-pressed': String(cur === x[0]), onclick: function () { set(x[0]); draw(); } }, x[1]);
      }));
    }
    function draw() {
      S.rpWin = st.win; S.rpPlan = st.plan;
      var p = plans.filter(function (x) { return x.id === st.plan; })[0], rows = ((p.results || {})[st.win] || {})[st.start] || [];
      var win = R.windows.filter(function (w) { return w.id === st.win; })[0];
      var sum = ((p.summary || {})[st.win] || {})[st.start];
      box.textContent = '';
      var tabs = h('div', { class: 'tabs', role: 'tablist' }, R.windows.map(function (w) {
        return h('button', { type: 'button', role: 'tab', 'aria-selected': String(w.id === st.win), onclick: function () { st.win = w.id; st.sel = null; draw(); } },
          T(w.months === 6 ? 'what_to_grow.next_h2_6' : 'what_to_grow.next_h2'));
      }));
      var starts = chips(R.starts.map(function (s, i) {
        return [s.id, [svg(Array(i + 2).join(I('drop', 14, 2.2))), ' ', T('last_years.start_' + s.id)]];
      }), st.start, function (v) { st.start = v; st.by = 'farmer'; st.sel = null; }, T('last_years.start_q'));
      var tw = R.twin_today, startNote = st.by === 'stick' ? T('last_years.start_stick') : st.by !== 'default' ? null
        : tw ? T('last_years.start_twin') + ' ' + K.fmtDate(tw.date) : T('last_years.start_none') + ' ' + T('last_years.start_' + R.start_default);
      var crops = ((p.crops_in_window || {})[st.win] || []).map(function (c) {
        return h('li', null, h('b', null, K.crop(c.crop)), ' · ', c.in_ground_at_start ? T('last_years.in_ground') : T('your_plan.plant_in', { crop: K.crop(c.crop), sow_month: monthOf(c.start.slice(0, 2)) }));
      });
      var grid = h('div', { class: 'squares' }, rows.map(function (y, i) {
        var ring = same.indexOf(y.season) >= 0;
        return h('button', { type: 'button', class: 'sq ' + (y.result || 'none') + (ring ? ' ring' : '') + (st.sel === i ? ' on' : ''), 'aria-pressed': String(st.sel === i),
          'aria-label': digits(y.season) + ': ' + resWord(y.result) + stop() + ' ' + T('your_plan.lab_estimate') + (ring ? stop() + ' ' + T('last_years.enso_same') : ''),
          onclick: function () { st.sel = st.sel === i ? null : i; draw(); } },
          h('span', { class: 'sy' }, digits(y.season)), resIcon(y.result), h('span', { class: 'sw' }, resWord(y.result)),
          ring ? h('span', { class: 'enso' }, svg(I('wave', 11, 2.4)), T('last_years.enso_like_now')) : null,
          h('span', { class: 'marks', 'aria-hidden': 'true' }, svg(I('pc', 11, 2.4)), y.sensitive ? svg(I('drop', 11, 2.6)) : null));
      }));
      var counts = sum ? h('div', { class: 'row wrap', style: 'gap:8px' }, ['worked', 'struggled', 'failed'].map(function (r) {
        return h('span', { class: 'cnt ' + r }, resIcon(r), resWord(r) + ': ', h('b', null, num(sum[r] || 0)));
      }), sum.no_crop ? h('span', { class: 'cnt' }, resIcon(null), resWord(null) + ': ', h('b', null, num(sum.no_crop))) : null) : null;
      var th = R.thresholds || {}, legend = th.worked_min != null ? K.lines([
        [resIcon('worked'), ' ', resWord('worked'), ' · ', T('last_years.need_met'), ' ', digits(th.worked_min + '–100')],
        [resIcon('struggled'), ' ', resWord('struggled'), ' · ', T('last_years.need_met'), ' ', digits(th.failed_below + '–' + (th.worked_min - 1))],
        [resIcon('failed'), ' ', resWord('failed'), ' · ', T('last_years.need_met'), ' ', digits('0–' + (th.failed_below - 1))]].map(function (x) { return h('span', null, x); }), 'small') : null;
      add(box, [
        h('div', { class: 'card col' }, h('p', { class: 'sub', style: 'font-weight:700;color:var(--ink)' }, T('last_years.which_plan')),
          chips(plans.map(function (x) { return [x.id, pname(x)]; }), st.plan, function (v) { st.plan = v; st.sel = null; }, T('last_years.which_plan')),
          tabs, win ? h('p', { class: 'small', style: 'margin:0' }, K.monthShort(K.MONTHS[+win.from.slice(0, 2) - 1]) + ' – ' + K.monthShort(K.MONTHS[+win.to.slice(0, 2) - 1]) + ' · ' + T('from_space.months_note')) : null,
          crops.length ? h('ul', { class: 'lines' }, crops) : null, crops.length ? h('p', { class: 'small', style: 'margin:0' }, T('last_years.calendar_note')) : null),
        h('div', { class: 'card col' }, h('p', { class: 'sub', style: 'font-weight:700;color:var(--ink)' }, T('last_years.start_q')), starts,
          startNote ? h('p', { class: 'small', style: 'margin:0' }, startNote) : null,
          tw && tw.band && BAND[tw.band] && st.by === 'default' ? h('p', { class: 'small', style: 'margin:0' }, T('check_soil.water_in_soil') + ' ' + T('check_soil.' + BAND[tw.band])) : null),
        h('div', { class: 'card col' }, h('h2', { class: 'h3' }, T('last_years.replay_sub')),
          R.water_case === 'rain-fed' ? h('p', { class: 'lead', style: 'margin:0' }, svg(I('rain', 18)), ' ', T('lbl.last_years.water_case.rain_fed')) : null, counts,
          K.labs('replay_window', R.label), grid, detail(rows[st.sel]),
          R.enso && R.enso.now ? h('p', { class: 'small', style: 'margin:0' }, h('span', { class: 'enso' }, svg(I('wave', 11, 2.4)), T('last_years.enso_like_now')), ' ',
            T('last_years.enso_now') + ' ' + T('last_years.enso_' + R.enso.now.state) + stop() + ' ' + T('last_years.enso_same') + stop()) : null,
          h('p', { class: 'small', style: 'margin:0' }, svg(I('pc', 12, 2.4)), ' ', T('last_years.every_estimate'), ' ', svg(I('drop', 12, 2.4)), ' ', T('last_years.rain_marked')),
          legend, R.watering && R.watering.removes_dry_stress ? h('p', { class: 'lead', style: 'margin:0' }, svg(I('drop', 18)), ' ', T('last_years.if_water')) : null,
          srcList(F, (R.sources || []).concat(R.enso && R.enso.source ? [R.enso.source] : [])))
      ]);
    }
    function detail(y) {
      if (!y) return h('p', { class: 'small', style: 'margin:0' }, T('last_years.tap_square'));
      var vs = y.other_versions || {}, sc = [y.score].concat(Object.keys(vs).map(function (k) { return vs[k].score; })).filter(function (x) { return typeof x === 'number'; });
      var words = [y.result].concat(Object.keys(vs).map(function (k) { return vs[k].result; })).filter(function (r, i, a) { return a.indexOf(r) === i; });
      var rs = y.reason || {}, why = rs.code === 'dry_spell' ? [T(y.result === 'worked' ? 'last_years.why_dry_spell_ok' : 'last_years.why_dry_spell'),
        pair(T('last_years.dry_in_row'), num(rs.days)), pair(T('last_years.dry_from'), monthOf(rs.month))]
        : rs.code === 'no_crop_in_window' ? [T('last_years.why_no_crop')] : (rs.code ? [T('last_years.why_' + rs.code)] : []);
      return h('div', { class: 'ydetail', 'aria-live': 'polite' },
        h('p', { class: 'lead', style: 'margin:0' }, resIcon(y.result), ' ', digits(y.season), ' · ', resWord(y.result)),
        why.map(function (x) { return typeof x === 'string' ? h('p', { style: 'margin:0' }, x) : x; }),
        sc.length ? pair(T('last_years.need_met'), K.rng(Math.min.apply(null, sc), Math.max.apply(null, sc)) + ' ' + T('btn.out_of_100')) : null,
        pair(T('last_years.dry_days'), num(y.dry_days)), y.rain_mm != null ? pair(T('last_years.rain_in_window'), num(y.rain_mm) + ' ' + T('your_plan.mm')) : null,
        y.enso ? pair(T('last_years.enso_then'), T('last_years.enso_' + y.enso)) : null,
        y.sensitive ? h('p', { class: 'small', style: 'margin:0' }, svg(I('drop', 12, 2.4)), ' ', T('last_years.rain_changes'), ' ', words.map(resWord).join(' / ')) : null,
        K.labs('replay_year', R.label));
    }
    draw();
    stickBand().then(function (b) {
      var s = b && R.starts.filter(function (x) { return x.probe_band === b.band; })[0];
      if (s && st.by === 'default' && box.isConnected) { st.start = s.id; st.by = 'stick'; draw(); }
    });
    return K.screen('replay', {
      head: [K.bigTitle(T('last_years.replay_h1', { year_count: R.year_count }), T('last_years.replay_h2')), h('p', { class: 'lead' }, T('last_years.replay_intro')), sample(F)],
      body: box,
      cta: [K.btn3(K.featName('trial'), function () { K.go('trial'); }, 'quarter'), K.btn3(K.featName('checkup'), function () { K.go('checkup'); }, 'check')]
    });
  }

  // ---------------- 2 Field Pulse: the greenness line, its seasons, the farmer's own dates, the fields nearby ----------------
  function svgEl(tag, a) { var e = D.createElementNS('http://www.w3.org/2000/svg', tag); Object.keys(a || {}).forEach(function (k) { e.setAttribute(k, a[k]); }); return e; }
  function heartbeat(U) {
    var pts = (U.curve.points || []).filter(function (p) { return /^\d{4}-\d\d-\d\d$/.test(p[0]) && typeof p[1] === 'number'; });
    if (!pts.length) return null;
    var y0 = +pts[0][0].slice(0, 4), y1 = +pts[pts.length - 1][0].slice(0, 4), PX = 168, Wd = (y1 - y0 + 1) * PX, Ht = 170, top = 18, bot = 34;
    function X(d) { var t = new Date(d + 'T00:00:00Z'), a = Date.UTC(+d.slice(0, 4), 0, 1); return (+d.slice(0, 4) - y0) * PX + (t - a) / 31536e6 * PX; }
    function Y(v) { return top + (1 - Math.max(0, Math.min(1, v))) * (Ht - top - bot); }
    var g = svgEl('svg', { width: Wd, height: Ht, viewBox: '0 0 ' + Wd + ' ' + Ht, class: 'beat', role: 'img', 'aria-label': T('from_space.pulse_line') });
    if (U.bare_threshold != null) g.append(svgEl('line', { x1: 0, x2: Wd, y1: Y(U.bare_threshold), y2: Y(U.bare_threshold), stroke: '#6B5D42', 'stroke-dasharray': '2 3', 'stroke-width': 1.6 }));
    for (var y = y0; y <= y1; y++) {
      var x = (y - y0) * PX;
      g.append(svgEl('line', { x1: x, x2: x, y1: top - 6, y2: Ht - bot + 4, stroke: '#14301E', 'stroke-opacity': .18 }));
      var yl = svgEl('text', { x: x + 3, y: 11, 'font-size': 11, 'font-weight': 700, fill: '#14301E' }); yl.textContent = digits(y); g.append(yl);
      [0, 3, 6, 9].forEach(function (m) {
        var t = svgEl('text', { x: x + (m + 0.5) * PX / 12, y: Ht - 12, 'font-size': 10, fill: '#3F4A3C', 'text-anchor': 'middle' }); t.textContent = K.monthShort(K.MONTHS[m]); g.append(t);
      });
    }
    ['modis', 'hls'].forEach(function (src) {
      var d = '', prev = null;
      pts.forEach(function (p) { if (p[2] !== src) { prev = null; return; } d += (prev ? 'L' : 'M') + X(p[0]).toFixed(1) + ' ' + Y(p[1]).toFixed(1); prev = p; });
      if (d) g.append(svgEl('path', { d: d, fill: 'none', stroke: src === 'hls' ? '#14301E' : '#9A5426', 'stroke-width': 2.2, 'stroke-dasharray': src === 'hls' ? '' : '5 3', 'stroke-linejoin': 'round' }));
    });
    var wrap = h('div', { class: 'beatwrap', tabindex: '0' }); wrap.append(g);
    setTimeout(function () { wrap.scrollLeft = wrap.scrollWidth; }, 0);
    return wrap;
  }
  function monthSelect(val, label) {
    return h('label', { class: 'msel' }, h('span', { class: 'small' }, label), h('select', null, K.MONTHS.map(function (m) { var o = h('option', { value: m }, K.monthName(m)); if (m === val) o.selected = true; return o; })));
  }
  function pulse(F, U) {
    if (!U || !U.curve) return null;
    var key = 'pulse.' + S.fid, mine = readJSON(key) || {}, box = h('div', { class: 'col', style: 'gap:14px' }), fixing = null;
    var lab = U.labels || {};
    function draw() {
      box.textContent = '';
      var seasons = (U.typical || []).map(function (t) {
        var m = mine[t.slot], sat = [K.MONTHS[+t.planting.slice(0, 2) - 1], K.MONTHS[+t.harvest.slice(0, 2) - 1]];
        var c = h('div', { class: 'card col' }, h('p', { class: 'lead', style: 'margin:0' }, svg(I('sprout', 18)), ' ', cap(K.crop(t.crop)) + ' · ' + T('from_space.slot_' + t.slot)),
          pair(T('from_space.planting'), T('btn.about') + ' ' + K.monthName(sat[0])), pair(T('from_space.harvest'), T('btn.about') + ' ' + K.monthName(sat[1])),
          K.labs('pulse_typical', lab.pulse_typical));
        if (fixing === t.slot) {
          var a = monthSelect(m ? m.planting : sat[0], T('from_space.planting')), b = monthSelect(m ? m.harvest : sat[1], T('from_space.harvest'));
          add(c, [h('div', { class: 'row wrap' }, a, b), K.btn2(T('from_space.save_dates'), function () {
            mine[t.slot] = { planting: a.querySelector('select').value, harvest: b.querySelector('select').value, ok: false };
            K.store.set(key, JSON.stringify(mine)); fixing = null; draw();
          }, 'tick')]);
        } else if (m) {
          add(c, [h('p', { class: 'kv' }, svg(I('hand', 16)), ' ', m.ok ? T('from_space.you_said_yes') : T('from_space.you_said') + ' ' + K.monthName(m.planting) + ' → ' + K.monthName(m.harvest)),
            h('p', { class: 'small', style: 'margin:0' }, T('check_soil.trial_saved')), K.btn3(T('from_space.fix_dates'), function () { fixing = t.slot; draw(); }, 'redo')]);
        } else {
          add(c, [h('p', { class: 'sub', style: 'font-weight:700;color:var(--ink)' }, T('from_space.dates_right')), h('div', { class: 'row wrap' },
            K.btn2(T('from_space.yes'), function () { mine[t.slot] = { planting: sat[0], harvest: sat[1], ok: true }; K.store.set(key, JSON.stringify(mine)); draw(); }, 'tick'),
            K.btn3(T('from_space.fix_dates'), function () { fixing = t.slot; draw(); }, 'redo'))]);
        }
        return c;
      });
      var nb = U.nearby, near = nb ? h('div', { class: 'card col' }, h('h2', { class: 'h3' }, T('from_space.nearby_title')),
        h('p', { class: 'small', style: 'margin:0' }, T('from_space.nearby_totals')),
        nb.median_bare_days ? pair(T('from_space.nearby_bare'), T('btn.about') + ' ' + num(nb.median_bare_days.value) + ' (' + K.rng(nb.median_bare_days.low, nb.median_bare_days.high) + ')') : null,
        nb.this_field && nb.this_field.mean_bare_days != null ? pair(T('from_space.yours_bare'), T('btn.about') + ' ' + num(nb.this_field.mean_bare_days)) : null,
        nb.share_two_seasons ? pair(T('from_space.nearby_two'), num(nb.share_two_seasons.value * 100) + ' ' + T('btn.out_of_100') + ' (' + K.rng(nb.share_two_seasons.low * 100, nb.share_two_seasons.high * 100) + ')') : null,
        nb.share_long_bare ? pair(T('from_space.nearby_long_bare'), num(nb.share_long_bare.value * 100) + ' ' + T('btn.out_of_100') + ' (' + K.rng(nb.share_long_bare.low * 100, nb.share_long_bare.high * 100) + ')') : null,
        K.labs('nearby_fields', nb.label), srcList(F, (U.sources || []).slice(0, 1))) : null;
      add(box, [
        h('div', { class: 'card col' }, h('p', { class: 'sub', style: 'font-weight:700;color:var(--ink)' }, T('from_space.pulse_line')),
          heartbeat(U) || K.notReady(),
          h('div', { class: 'legend' }, h('span', null, h('span', { class: 'sw', style: 'background:#14301E' }), T('from_space.pulse_new')), K.labs('pulse_hls', lab.pulse_hls)),
          h('div', { class: 'legend' }, h('span', null, h('span', { class: 'sw dash' }), T('from_space.pulse_old')), K.labs('pulse_modis', lab.pulse_modis)),
          U.bare_threshold != null ? h('p', { class: 'small', style: 'margin:0' }, h('span', { class: 'sw bare', 'aria-hidden': 'true' }), ' ', T('from_space.pulse_bare')) : null,
          h('p', { class: 'small', style: 'margin:0' }, T('from_space.months_note')), srcList(F, U.sources)),
        h('h2', { class: 'h3' }, T('from_space.your_seasons')), seasons, near
      ]);
    }
    draw();
    return K.screen('pulse', {
      head: [K.bigTitle(T('from_space.pulse_h1'), T('from_space.pulse_h2')), h('p', { class: 'lead' }, T('from_space.pulse_sub')), sample(F)],
      body: box,
      cta: K.btn3(K.featName('replay'), function () { K.go('replay'); }, 'redo')
    });
  }

  // ---------------- 4 the record check-up: how this field's rain record was checked, and fixed ----------------
  function bars(items) {
    var mx = Math.max.apply(null, items.map(function (x) { return x[1]; }));
    return h('div', { class: 'hbars' }, items.map(function (x) {
      return h('div', { class: 'hb' + (x[2] ? ' on' : '') }, h('span', { class: 'hl' }, x[0], x[2] ? [' · ', h('b', null, T('your_plan.we_use_this'))] : null),
        h('span', { class: 'track' }, h('i', { style: 'width:' + (x[1] / mx * 100).toFixed(1) + '%' })), h('b', { class: 'hv' }, num(x[1]) + ' ' + T('your_plan.mm')));
    }));
  }
  function yearlyChart(Y, fix) {
    var yrs = (Y.years || []).filter(function (y) { return typeof y === 'number'; });
    if (yrs.length < 2) return null;
    var keys = [['gpm', '#9A5426', '5 3'], ['twin', '#14301E', ''], ['chirps', '#2F6E99', '2 3']], Wd = 340, Ht = 190, m = { l: 40, r: 8, t: 10, b: 26 };
    var all = []; keys.forEach(function (k) { (Y[k[0]] || []).forEach(function (v) { if (typeof v === 'number') all.push(v); }); });
    var lo = 0, hi = Math.ceil(Math.max.apply(null, all) / 500) * 500;
    function X(i) { return m.l + i / (yrs.length - 1) * (Wd - m.l - m.r); }
    function YY(v) { return m.t + (1 - v / hi) * (Ht - m.t - m.b); }
    var g = svgEl('svg', { viewBox: '0 0 ' + Wd + ' ' + Ht, class: 'plot', role: 'img', 'aria-label': T('your_plan.check_yearly') });
    [0, hi / 2, hi].forEach(function (v) { g.append(svgEl('line', { x1: m.l, x2: Wd - m.r, y1: YY(v), y2: YY(v), stroke: '#14301E', 'stroke-opacity': .12 }));
      var t = svgEl('text', { x: m.l - 4, y: YY(v) + 4, 'font-size': 10, 'text-anchor': 'end', fill: '#3F4A3C' }); t.textContent = num(v); g.append(t); });
    [0, yrs.length - 1].concat(fix ? [yrs.indexOf(fix)] : []).forEach(function (i) {
      if (i < 0) return; var t = svgEl('text', { x: X(i), y: Ht - 8, 'font-size': 10, 'text-anchor': i === yrs.length - 1 ? 'end' : i ? 'middle' : 'start', fill: '#3F4A3C' }); t.textContent = digits(yrs[i]); g.append(t);
    });
    if (fix && yrs.indexOf(fix) >= 0) g.append(svgEl('line', { x1: X(yrs.indexOf(fix)), x2: X(yrs.indexOf(fix)), y1: m.t, y2: Ht - m.b, stroke: '#9A5426', 'stroke-dasharray': '3 3' }));
    keys.forEach(function (k) {
      var d = ''; (Y[k[0]] || []).forEach(function (v, i) { if (typeof v === 'number' && i < yrs.length) d += (d ? 'L' : 'M') + X(i).toFixed(1) + ' ' + YY(v).toFixed(1); });
      if (d) g.append(svgEl('path', { d: d, fill: 'none', stroke: k[1], 'stroke-width': 2.2, 'stroke-dasharray': k[2] }));
    });
    return h('div', null, g, h('div', { class: 'legend' }, keys.map(function (k) {
      return h('span', null, svg('<svg width="26" height="10"><line x1="1" y1="5" x2="25" y2="5" stroke="' + k[1] + '" stroke-width="2.4" stroke-dasharray="' + k[2] + '"/></svg>'), ' ', T('your_plan.line_' + k[0]));
    })));
  }
  function x(v) { return '×' + digits((Math.round(v * 100) / 100).toFixed(2).replace(/0$/, '')); }
  function checkup(F, C) {
    if (!C || !C.break_test) return null;
    var bt = C.break_test, ev = {}, yr = { rain_fix_year: bt.year }, cor = C.correction || {};
    (C.evidence || []).forEach(function (e) { ev[e.id] = e; });
    var e1 = ev.gauge_weight, e2 = ev.gpcc_stations, e3 = ev.gpm_vs_chirps, e4 = ev.dhm_normals, e5 = ev.imerg_late;
    var ref = cor.break && cor.break.reference_years, gf = cor.gauge_factors;
    var vers = (C.versions || []).filter(function (v) { return typeof v.mean_mm_per_year === 'number'; });
    var body = [
      h('div', { class: 'card col' }, K.lines([T('your_plan.check_what'), T('your_plan.check_auto')]),
        h('p', { class: 'lead', style: 'margin:0' }, svg(I(bt.found ? 'info' : 'tick', 18)), ' ', bt.found ? T('your_plan.check_found', yr) : T('your_plan.check_none')), K.labs('checkup_break')),
      bt.found ? h('div', { class: 'card col' }, h('h2', { class: 'h3' }, T('your_plan.check_how')),
        e1 ? h('div', { class: 'fact' }, h('span', { class: 'ic' }, svg(I('mast', 20))), h('div', { class: 'grow col', style: 'gap:4px' }, h('p', { style: 'margin:0' }, T('your_plan.check_gauge_share')),
          pair(T('your_plan.check_before', yr), K.rng(e1.before_pct[0], e1.before_pct[1]) + ' ' + T('btn.out_of_100')),
          pair(T('your_plan.check_from', yr), K.rng(e1.after_yearly_pct[0], e1.after_yearly_pct[1]) + ' ' + T('btn.out_of_100')))) : null,
        e2 ? h('div', { class: 'fact' }, h('span', { class: 'ic' }, svg(I('mast', 20))), h('div', { class: 'grow col', style: 'gap:4px' }, h('p', { style: 'margin:0' }, T('your_plan.check_gauges_near')),
          pair(T('your_plan.check_before', yr), T('btn.about') + ' ' + num(e2.before)), pair(T('your_plan.check_from', yr), T('btn.about') + ' ' + num(e2.after)))) : null,
        e3 ? h('div', { class: 'fact' }, h('span', { class: 'ic' }, svg(I('sat', 20))), h('div', { class: 'grow col', style: 'gap:4px' },
          h('p', { style: 'margin:0' }, T('your_plan.check_other_map')), pair(T('your_plan.check_jump'), x(e3.step)))) : null,
        e5 ? h('div', { class: 'fact' }, h('span', { class: 'ic' }, svg(I('sat', 20))), h('div', { class: 'grow col', style: 'gap:4px' },
          h('p', { style: 'margin:0' }, T('your_plan.check_late')), pair(T('your_plan.check_late_jump'), x(e5.step_late)), pair(T('your_plan.check_final_jump'), x(e5.step_final)))) : null,
        e4 ? h('div', { class: 'fact' }, h('span', { class: 'ic' }, svg(I('mast', 20))), h('div', { class: 'grow col', style: 'gap:4px' },
          pair(T('your_plan.check_office'), T('btn.about') + ' ' + num(e4.normal_mm) + ' ' + T('your_plan.mm')),
          h('p', { style: 'margin:0' }, T('your_plan.check_office_times')), pair(T('your_plan.check_before', yr), x(e4.gpm_2001_2016_ratio)), pair(T('your_plan.check_from', yr), x(e4.gpm_2017_2025_ratio)),
          pair(T('your_plan.check_ours'), x(e4.twin_ratio)))) : null) : null,
      bt.found ? h('div', { class: 'card col' }, h('h2', { class: 'h3' }, T('your_plan.check_fix_title')),
        K.lines([T('your_plan.check_fix', yr), ref ? T('your_plan.check_ref') + ' ' + digits(ref[0] + '–' + ref[1]) : null,
          gf && gf.applied ? T('your_plan.check_gauge_fix') : null]),
        gf && gf.applied ? pair(T('your_plan.check_monsoon'), x(gf.jjas)) : null, gf && gf.applied ? pair(T('your_plan.check_other_months'), x(gf.other)) : null) : null,
      vers.length ? h('div', { class: 'card col' }, h('h2', { class: 'h3' }, T('your_plan.check_versions')),
        bars(vers.map(function (v) { return [T('your_plan.ver_' + v.id), v.mean_mm_per_year, v.central]; })), K.labs('checkup_rain', C.label),
        h('p', { class: 'small', style: 'margin:0' }, T('what_to_grow.range_why'))) : null,
      C.yearly ? h('div', { class: 'card col' }, h('h2', { class: 'h3' }, T('your_plan.check_yearly')), yearlyChart(C.yearly, bt.found ? bt.year : null)) : null,
      h('div', { class: 'card col' }, h('p', { style: 'margin:0' }, T('your_plan.check_marked')), h('div', null, K.rainMark())),
      srcList(F, C.sources)
    ];
    return K.screen('checkup', {
      head: [K.bigTitle(T('your_plan.check_h1'), T('your_plan.check_h2')), h('p', { class: 'lead' }, T('your_plan.check_sub')), sample(F)],
      body: h('div', { class: 'col', style: 'gap:14px' }, body),
      cta: K.btn3(K.featName('replay'), function () { K.go('replay'); }, 'redo')
    });
  }

  K.feat = { replay: replay, pulse: pulse, trial: trial, checkup: checkup };
})();
