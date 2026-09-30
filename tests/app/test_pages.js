// GitHub Pages 部署設定的護欄（規格 §11：tools/ 不部署到網站）。
//
// 這裡釘的是「打包清單」與「預快取清單」之間的一致性。少了這道測試，
// workflow 漏掉一個目錄的症狀是：線上版某支模組 404、整頁空白，而本機
// `python3 -m http.server` 開起來永遠正常——只有部署後才現形，和 test_sw.js
// 防的是同一類靜默失敗。
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, existsSync } from 'node:fs';

const root = new URL('../../', import.meta.url);
const workflowPath = new URL('.github/workflows/pages.yml', root);

function workflow() {
  assert.ok(existsSync(workflowPath), '.github/workflows/pages.yml 不存在');
  return readFileSync(workflowPath, 'utf8');
}

// 打包步驟把要上線的路徑逐一複製到 _site/。這裡解析出那份清單，
// 用來比對 sw.js 的 PRECACHE——兩份清單必須互相涵蓋。
function stagedPaths() {
  const m = /# STAGE-BEGIN\n([\s\S]*?)# STAGE-END/.exec(workflow());
  assert.ok(m, 'pages.yml 找不到 STAGE-BEGIN/STAGE-END 之間的打包清單');
  return m[1].split('\n')
    .map((line) => /^\s*(?:cp -R|cp)\s+(\S+)/.exec(line))
    .filter(Boolean)
    .map((m2) => m2[1]);
}

function precacheList() {
  const sw = readFileSync(new URL('sw.js', root), 'utf8');
  const m = /const PRECACHE = \[([\s\S]*?)\];/.exec(sw);
  assert.ok(m, 'sw.js 找不到 PRECACHE 陣列');
  return m[1].split(',')
    .map((s) => s.trim().replace(/^'|'$/g, ''))
    .filter((s) => s.length > 0 && s !== './');
}

test('預快取的每個檔案都在部署打包範圍內（漏一個，線上版才會壞）', () => {
  const staged = stagedPaths();
  for (const p of precacheList()) {
    const covered = staged.some((s) => p === s || p.startsWith(`${s.replace(/\/$/, '')}/`));
    assert.ok(covered, `${p} 在 PRECACHE 中，但不在 pages.yml 的打包清單裡`);
  }
});

// sw.js 不在自己的 PRECACHE 裡（Service Worker 由瀏覽器另外抓），所以上面那條
// 測試涵蓋不到它。漏掉它的症狀最惡劣：網站照常運作，只有離線功能無聲消失。
test('sw.js 在打包清單內（漏掉它，離線功能會無聲消失）', () => {
  assert.ok(stagedPaths().includes('sw.js'), 'sw.js 沒有列入打包清單');
});

test('tools/ 與 tests/ 不進打包清單（規格 §11）', () => {
  for (const s of stagedPaths()) {
    assert.ok(!s.startsWith('tools'), 'tools/ 不得部署到網站');
    assert.ok(!s.startsWith('tests'), 'tests/ 不得部署到網站');
  }
});

test('打包清單中的每個路徑都真的存在（打錯字會讓部署缺檔）', () => {
  for (const s of stagedPaths()) {
    assert.ok(existsSync(new URL(s, root)), `打包清單中的 ${s} 不存在`);
  }
});

test('部署前會先跑測試（紅燈的版本不該上線）', () => {
  assert.match(workflow(), /node --test/, 'pages.yml 必須在部署前執行測試');
});

test('robots.txt 擋掉搜尋引擎索引', () => {
  const p = new URL('robots.txt', root);
  assert.ok(existsSync(p), 'robots.txt 不存在');
  const txt = readFileSync(p, 'utf8');
  assert.match(txt, /User-agent:\s*\*/i, 'robots.txt 必須涵蓋所有 user-agent');
  assert.match(txt, /Disallow:\s*\/\s*$/im, 'robots.txt 必須 Disallow: /');
});

test('.nojekyll 存在（否則 Jekyll 會吃掉底線開頭的檔案）', () => {
  assert.ok(existsSync(new URL('.nojekyll', root)), '.nojekyll 不存在');
});

test('robots.txt 與 .nojekyll 本身也要部署出去', () => {
  const staged = stagedPaths();
  for (const f of ['robots.txt', '.nojekyll']) {
    assert.ok(staged.includes(f), `${f} 沒有列入打包清單，部署後不會生效`);
  }
});
