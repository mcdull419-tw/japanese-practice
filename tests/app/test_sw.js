import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, existsSync } from 'node:fs';

const root = new URL('../../', import.meta.url);
const sw = readFileSync(new URL('sw.js', root), 'utf8');

function precacheList() {
  const m = /const PRECACHE = \[([\s\S]*?)\];/.exec(sw);
  assert.ok(m, 'sw.js 找不到 PRECACHE 陣列');
  return m[1].split(',')
    .map((s) => s.trim().replace(/^'|'$/g, ''))
    .filter((s) => s.length > 0);
}

function walkJs(dir, prefix, out = []) {
  for (const e of readdirSync(new URL(dir, root), { withFileTypes: true })) {
    if (e.isDirectory()) walkJs(`${dir}${e.name}/`, `${prefix}${e.name}/`, out);
    else if (e.name.endsWith('.js')) out.push(`${prefix}${e.name}`);
  }
  return out;
}

test('app/ 下每一個模組都在預快取清單中（漏一個離線就靜默壞掉）', () => {
  const listed = new Set(precacheList());
  for (const f of walkJs('app/', 'app/')) {
    assert.ok(listed.has(f), `${f} 未列入預快取，離線時會載入失敗`);
  }
});

test('15 課資料與人工維護的資料檔都在預快取清單中', () => {
  const listed = new Set(precacheList());
  for (let n = 1; n <= 15; n++) {
    assert.ok(listed.has(`data/lessons/${String(n).padStart(2, '0')}.json`), `第 ${n} 課未列入`);
  }
  for (const f of ['verbs.json', 'adjectives.json', 'concepts.json', 'particles.json',
    'drills.json', 'ruby-lexicon.json', 'corrections.json']) {
    assert.ok(listed.has(`data/${f}`), `data/${f} 未列入`);
  }
});

test('預快取清單中的每個檔案都真的存在（打錯字會讓整個 install 失敗）', () => {
  for (const p of precacheList()) {
    if (p === './') continue;
    assert.ok(existsSync(new URL(p, root)), `預快取清單中的 ${p} 不存在`);
  }
});

test('插畫不進預快取（3.6MB，2b 用不到）', () => {
  assert.ok(!precacheList().some((p) => p.startsWith('data/images/')), '插畫不該進快取');
});

test('cache 名稱帶版本，改版才換得掉舊快取', () => {
  assert.match(sw, /const CACHE = '[^']*v\d+'/, 'sw.js 的 CACHE 常數必須帶版本號');
});

test('activate 會清掉舊版快取（否則版本換了也吃不到新檔）', () => {
  assert.match(sw, /caches\.delete/, 'sw.js 必須在 activate 清掉舊快取');
});

test('sw.js 不得使用 import（Service Worker 以 classic script 註冊）', () => {
  assert.ok(!/^\s*import\s/m.test(sw), 'sw.js 不得使用 ES import');
});

test('manifest 欄位齊備且圖示存在', () => {
  const m = JSON.parse(readFileSync(new URL('manifest.json', root), 'utf8'));
  assert.equal(typeof m.name, 'string');
  assert.equal(typeof m.short_name, 'string');
  assert.equal(m.display, 'standalone');
  assert.equal(m.start_url, '.');
  assert.ok(m.icons.length >= 2);
  for (const i of m.icons) assert.ok(existsSync(new URL(i.src, root)), `圖示 ${i.src} 不存在`);
});

test('index.html 連上 manifest 與圖示', () => {
  const html = readFileSync(new URL('index.html', root), 'utf8');
  assert.match(html, /rel="manifest"/, 'index.html 缺 manifest 連結');
  assert.match(html, /apple-touch-icon/, 'iOS 加入主畫面需要 apple-touch-icon');
});
