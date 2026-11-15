/* Khet Sathi's offline copy (owner, 2026-11-15). The public site only: it never runs on the laptop or its hotspot
   (LOCAL), and the app never registers it there. On a first visit it saves FIRST_VISIT (the app and the main field);
   other files the app loads (other fields, the world page) are saved when first opened. Same-origin GET requests only;
   NEVER, and anything fetched as always fresh (cache: 'no-store': the live reading, demo mode), always comes from the
   network. The copy is named VERSION; a new version replaces the old one. If the list cannot be saved, the worker
   removes itself and the app works as it did before. scripts/build_offline.py writes the block below. */
// BEGIN LIST (scripts/build_offline.py writes this block)
const VERSION = 'ks-d05a98c-d312bc8551';
const FIRST_VISIT = [
 "css/app.css",
 "data/area/demo.json",
 "data/area/demo_bare_days.png",
 "data/area/demo_seasons.png",
 "data/area/kharipati.json",
 "data/area/kharipati_bare_days.png",
 "data/area/kharipati_seasons.png",
 "data/basemap/demo.jpg",
 "data/basemap/demo.json",
 "data/basemap/kharipati.json",
 "data/basemap/sample-1.json",
 "data/basemap/sample-2.json",
 "data/basemap/sample-3.json",
 "data/basemap/sample-4.json",
 "data/basemap/world.jpg",
 "data/basemap/world.json",
 "data/behind.json",
 "data/checkup/ambohidratrimo.json",
 "data/checkup/demo.json",
 "data/checkup/kharipati.json",
 "data/checkup/sample-1.json",
 "data/checkup/sample-2.json",
 "data/checkup/sample-3.json",
 "data/checkup/sample-4.json",
 "data/drone/dhulikhel.jpg",
 "data/drone/dhulikhel.json",
 "data/drone/kharipati.jpg",
 "data/drone/kharipati.json",
 "data/fertiliser/demo.json",
 "data/fertiliser/kharipati.json",
 "data/fertiliser/sample-1.json",
 "data/fertiliser/sample-2.json",
 "data/fertiliser/sample-3.json",
 "data/fertiliser/sample-4.json",
 "data/fields/ambohidratrimo.json",
 "data/fields/demo.json",
 "data/fields/kharipati.json",
 "data/fields/sample-1.json",
 "data/fields/sample-2.json",
 "data/fields/sample-3.json",
 "data/fields/sample-4.json",
 "data/heatclock/demo.json",
 "data/heatclock/kharipati.json",
 "data/heatclock/sample-1.json",
 "data/heatclock/sample-2.json",
 "data/heatclock/sample-3.json",
 "data/heatclock/sample-4.json",
 "data/index.json",
 "data/labels/ambohidratrimo.json",
 "data/labels/demo.json",
 "data/labels/kharipati.json",
 "data/labels/sample-1.json",
 "data/labels/sample-2.json",
 "data/labels/sample-3.json",
 "data/labels/sample-4.json",
 "data/pulse/ambohidratrimo.json",
 "data/pulse/demo.json",
 "data/pulse/kharipati.json",
 "data/pulse/sample-1.json",
 "data/pulse/sample-2.json",
 "data/pulse/sample-3.json",
 "data/pulse/sample-4.json",
 "data/rainrisk/demo.json",
 "data/rainrisk/kharipati.json",
 "data/rainrisk/sample-1.json",
 "data/rainrisk/sample-2.json",
 "data/rainrisk/sample-3.json",
 "data/rainrisk/sample-4.json",
 "data/replay/demo.json",
 "data/replay/kharipati.json",
 "data/replay/sample-1.json",
 "data/replay/sample-2.json",
 "data/replay/sample-3.json",
 "data/replay/sample-4.json",
 "data/simple/demo.json",
 "data/simple/kharipati.json",
 "data/simple/sample-1.json",
 "data/simple/sample-2.json",
 "data/simple/sample-3.json",
 "data/simple/sample-4.json",
 "data/story.json",
 "data/version.json",
 "data/words.json",
 "data/world.json",
 "fonts/OFL-Inter.txt",
 "fonts/OFL-InterTight.txt",
 "fonts/OFL-Mukta.txt",
 "fonts/fonts.css",
 "fonts/inter-latin-var.woff2",
 "fonts/inter-tight-latin-var.woff2",
 "fonts/mukta-devanagari-400.woff2",
 "fonts/mukta-devanagari-700.woff2",
 "icons/apple-touch-icon.png",
 "icons/icon-192.png",
 "icons/icon-512.png",
 "icons/icon-maskable-512.png",
 "img/bg-home.svg",
 "img/bg-phone.svg",
 "img/bg-web.svg",
 "img/farm.webp",
 "img/icon.svg",
 "index.html",
 "js/app.js",
 "js/behind.js",
 "js/features.js",
 "js/how.js",
 "js/world.js",
 "manifest.webmanifest",
 "vendor/leaflet/LICENSE",
 "vendor/leaflet/leaflet.css",
 "vendor/leaflet/leaflet.js"
];
const NEVER = ["data/live.json", "data/demo.json", "data/probe_log.json"];
// END LIST
const LOCAL = /^(localhost|127\.\d+\.\d+\.\d+|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+|.+\.local|\[::1\])$/i;
const BASE = new URL('./', self.location).href;   // the site's folder: the address's root, or /data-test-game/

self.addEventListener('install', function (e) {
  if (LOCAL.test(self.location.hostname)) { e.waitUntil(self.registration.unregister()); return; }
  e.waitUntil(caches.open(VERSION).then(function (c) { return c.addAll(FIRST_VISIT); }).then(function () { return self.skipWaiting(); })
    .catch(function (err) {                      // a wrong list: no broken copy, no worker
      return caches.delete(VERSION).then(function () { return self.registration.unregister(); }).then(function () { throw err; });
    }));
});

self.addEventListener('activate', function (e) {
  e.waitUntil(caches.keys().then(function (ks) {
    return Promise.all(ks.filter(function (k) { return k.indexOf('ks-') === 0 && k !== VERSION; }).map(function (k) { return caches.delete(k); }));
  }).then(function () { return self.clients.claim(); }));
});

self.addEventListener('fetch', function (e) {
  var r = e.request, u = new URL(r.url);
  if (r.method !== 'GET' || u.origin !== self.location.origin || r.url.indexOf(BASE) !== 0) return;
  if (r.cache === 'no-store' || NEVER.indexOf(u.pathname.slice(new URL(BASE).pathname.length)) >= 0) return;
  var key = r.mode === 'navigate' ? BASE + 'index.html' : r;   // every page of the app is index.html
  e.respondWith(caches.open(VERSION).then(function (c) {
    return c.match(key).then(function (hit) {
      return hit || fetch(r).then(function (res) {
        if (res.ok && res.type === 'basic' && r.mode !== 'navigate') c.put(r, res.clone());
        return res;
      });
    });
  }));
});
