// Service Worker（規格 §11、Phase 2 驗收：離線可完成一次完整練習）。
//
// 這個檔是整個專案唯一不是 ES module 的 JS：SW 以 classic script 註冊，
// import 在此不可用。
//
// PRECACHE 清單由 tests/app/test_sw.js 把關——app/ 下新增模組而忘了列進來，
// 測試會紅燈。沒有這道測試的話，離線時會是「某個模組 404、整個頁面空白」的
// 靜默失敗，而且只在沒網路時才重現。
const CACHE = 'jp-practice-v1';

const PRECACHE = [
  './',
  'index.html',
  'manifest.json',
  'icon-192.png',
  'icon-512.png',
  'app/core/conceptdefs.js',
  'app/core/concepts.js',
  'app/core/corrections.js',
  'app/core/data.js',
  'app/core/grading.js',
  'app/core/normalize.js',
  'app/core/ruby.js',
  'app/core/scheduler.js',
  'app/core/srs.js',
  'app/core/store.js',
  'app/core/tts.js',
  'app/engines/cloze.js',
  'app/engines/index.js',
  'app/engines/recall.js',
  'app/engines/substitute.js',
  'app/engines/text.js',
  'app/engines/transform.js',
  'app/generators/cloze.js',
  'app/generators/drills.js',
  'app/generators/quantity.js',
  'app/generators/recall.js',
  'app/generators/substitute.js',
  'app/generators/transform.js',
  'app/lang/adjective.js',
  'app/lang/altforms.js',
  'app/lang/conjugation.js',
  'app/lang/counters.js',
  'app/lang/kana.js',
  'app/lang/numbers.js',
  'app/main.js',
  'app/ui/dashboard.js',
  'app/ui/html.js',
  'app/ui/player.js',
  'app/ui/present.js',
  'app/ui/session.js',
  'app/ui/settings.js',
  'data/adjectives.json',
  'data/concepts.json',
  'data/corrections.json',
  'data/drills.json',
  'data/particles.json',
  'data/ruby-lexicon.json',
  'data/verbs.json',
  'data/lessons/01.json',
  'data/lessons/02.json',
  'data/lessons/03.json',
  'data/lessons/04.json',
  'data/lessons/05.json',
  'data/lessons/06.json',
  'data/lessons/07.json',
  'data/lessons/08.json',
  'data/lessons/09.json',
  'data/lessons/10.json',
  'data/lessons/11.json',
  'data/lessons/12.json',
  'data/lessons/13.json',
  'data/lessons/14.json',
  'data/lessons/15.json',
];

self.addEventListener('install', (e) => {
  e.waitUntil(caches.open(CACHE).then((c) => c.addAll(PRECACHE)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (e) => {
  e.waitUntil(caches.keys()
    .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
    .then(() => self.clients.claim()));
});

// cache-first：題庫是靜態檔，改版時換 CACHE 版本號即可整批換掉。
// 網路優先會讓離線變成「每次都等 timeout」，在手機上特別明顯。
self.addEventListener('fetch', (e) => {
  if (e.request.method !== 'GET') return;
  e.respondWith(caches.match(e.request).then((hit) => hit || fetch(e.request)));
});
