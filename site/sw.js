/* Khet Sathi's offline copy (owner, 2026-11-15). The public site only: it never runs on the laptop or its hotspot
   (LOCAL), and the app never registers it there. On a first visit it saves FIRST_VISIT (the app and the main field);
   other files the app loads (other fields, the world page) are saved when first opened. Same-origin GET requests only;
   NEVER, and anything fetched as always fresh (cache: 'no-store': the live reading, demo mode), always comes from the
   network. The copy is named VERSION; a new version replaces the old one. If the list cannot be saved, the worker
   removes itself and the app works as it did before. scripts/build_offline.py writes the block below. */
// BEGIN LIST (scripts/build_offline.py writes this block)
const VERSION = 'ks-cbe6ee2-eaa67e23af';
const FIRST_VISIT = [
 "css/app.css",
 "data/area/kharipati.json",
 "data/area/kharipati_bare_days.png",
 "data/area/kharipati_seasons.png",
 "data/basemap/demo.jpg",
 "data/basemap/kharipati.json",
 "data/behind.json",
 "data/checkup/kharipati.json",
 "data/drone/kharipati.jpg",
 "data/drone/kharipati.json",
 "data/fertiliser/kharipati.json",
 "data/fields/kharipati.json",
 "data/heatclock/kharipati.json",
 "data/index.json",
 "data/labels/kharipati.json",
 "data/pulse/kharipati.json",
 "data/rainrisk/kharipati.json",
 "data/replay/kharipati.json",
 "data/simple/kharipati.json",
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
