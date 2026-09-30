# Phase 2b 呈現與平台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 補齊振假名顯示、聽力呈現、單字循環播放、`jp2zh` 選擇題、練習Ｂ 題源與 PWA 離線能力，使需求 #14 #15 #16 可用、#11 #13 的題量翻倍，並讓整個網站可裝到手機主畫面離線使用。

**Architecture:** 新增一層 `app/engines/`——Phase 1/2a 刻意延後它（規格 §13 決定 1），因為在此之前所有題型都是打字作答，多一層沒有行為差異的轉接；`jp2zh` 是選擇題，這層現在才有分歧可承載。`ui/session.js` 隨之退化成驅動器：只管進度、按鈕與事件寫入，題幹與作答控制項改由引擎渲染。振假名與語音都是**呈現修飾**而非新引擎（規格 §6.2）：`core/ruby.js` 與 `core/tts.js` 為純函式／可注入模組，DOM 只在 `ui/` 與 `engines/` 出現。練習Ｂ 不寫新解析器，而是人工標註成練習Ａ 的形狀後重用 `generators/substitute.js`（規格 §13 決定 7）。

**Tech Stack:** Vanilla JS ES modules（無 build step）、`node --test`（Node 內建）、Service Worker（classic script，非 module）、Web Speech API、Python 3 標準函式庫（僅 `tools/draft/`，不部署）、Swift + AppKit（僅 `tools/` 產圖示，不部署）。

**Spec:** `docs/superpowers/specs/2026-09-10-japanese-practice-design.md`（Phase 2b 範圍見 §13；決定 7 ~ 10 為本計畫的直接前提）

## Global Constraints

- **無 build step、無第三方依賴。** 瀏覽器端一律 ES modules 直接載入；測試一律 `node --test`，不得引入測試框架。`sw.js` 是唯一的例外檔：Service Worker 以 classic script 註冊，不得使用 `import`。
- **`tools/` 不部署到網站**（規格 §11），只用 Python 3 標準函式庫或 macOS 內建 Swift。
- **Item `id` 必須決定性**（規格 §5.3）：禁止亂數與時間戳。`jp2zh` 的誘答選項也必須決定性——同一題每次展開得到同一組選項，否則 id 相同而內容不同，SRS 記到的是哪一題就失去意義。
- **`requires_lesson` = max(素材課次, 形態／句型解鎖課次)**（規格 §5.3）。
- **概念技能由 ID 前綴推導**，`core/concepts.js` 的 `skillOf()` 是唯一真相來源；資料檔不得自帶 `skills` 欄位（規格 §13 決定 2）。
- **判斷邏輯不得寫進 `ui/` 或 `engines/`。** 對錯比對走 `core/normalize.js`，評分走 `core/grading.js`——選擇題也一樣，引擎只負責把「選到的選項文字」交出來當作答輸入。
- **`app/core/` 與 `app/lang/` 不得出現 `document.` 或 `window.`**（Phase 1 已以 grep 驗收，須維持）。`core/tts.js` 因此收 `speechSynthesis` 為注入參數，不自行抓全域。
- **手維護資料檔須有漂移偵測測試**（規格 §13 決定 6）：`data/ruby-lexicon.json` 的 `auto` 區須能從當前語料回推、`data/drills.json` 須通過往返驗證。
- **全部註解與提交訊息使用繁體中文**，與既有程式碼一致。
- 提交訊息結尾附：
  ```
  Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_0193bNt3UCNnaU8xePLSt53W
  ```

## 檔案結構

| 檔案 | 責任 |
|---|---|
| `app/core/ruby.js` | 振假名切詞（純函式，回傳 token 陣列，不碰 DOM） |
| `app/core/tts.js` | Web Speech API 封裝（合成器以參數注入） |
| `app/ui/html.js` | `escapeHtml` 與 token → `<ruby>` HTML（純字串處理） |
| `app/engines/text.js` | 打字作答的共用渲染（含 IME 防呆） |
| `app/engines/recall.js` | 對照題：有 `choices` 走選擇題，否則走 text |
| `app/engines/transform.js`／`substitute.js`／`cloze.js` | 薄包裝 text，只差題幹排版 |
| `app/engines/index.js` | `engineFor(item)` 分派 |
| `app/ui/player.js` | 單字循環播放（讀 SRS 狀態，不寫事件） |
| `data/ruby-lexicon.json` | 振假名詞典（`auto` 自語料產生／`manual` 人工補） |
| `data/drills.json` | 練習Ｂ 的 template ＋ slots ＋ rows（人工標註） |
| `tools/draft/ruby_lexicon.py` | 產 `auto` 區草稿 |
| `tools/draft/drills.py` | 產 `data/drills.json` 草稿（只做機械拆分） |
| `tools/make_icons.swift` | 產 PWA 圖示 PNG（離線執行一次） |
| `manifest.json`／`sw.js` | PWA 宣告與離線快取 |

修改：`app/ui/session.js`（退化為驅動器）、`app/generators/recall.js`（加 `jp2zh`）、`app/generators/substitute.js`（支援 `answer_part` 與練習Ｂ 出處）、`app/ui/settings.js`（聽力開關、播放器入口）、`app/main.js`（接線、SW 註冊）、`data/concepts.json`（補練習Ｂ 反查）、`index.html`（播放器區塊與 ruby 樣式）。

---

### Task 1: `core/ruby.js` — 依課本標註切詞

課本 430 句中有 351 句帶 `ruby[]`（`{at, base, kana}`，`at` 是 `base` 在 `jp` 中的起始索引）。這是最精確的來源，優先於任何推測。

**Files:**
- Create: `app/core/ruby.js`
- Test: `tests/app/test_ruby.js`

**Interfaces:**
- Produces: `annotateWithMarks(text, marks)` → `Token[]`，`Token` 為 `{ t: 'text', s: string }` 或 `{ t: 'ruby', base: string, kana: string }`。`marks` 為 `[{ at, base, kana }]`。標註位置對不上 `text` 時**跳過該筆**而非拋錯（語料重抽位移時寧可少注也不要整頁壞掉，漂移由 Task 3 的測試抓）。

- [ ] **Step 1: 寫失敗的測試**

建立 `tests/app/test_ruby.js`：

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { annotateWithMarks } from '../../app/core/ruby.js';

test('依標註切出 text 與 ruby 交錯的 token', () => {
  const text = 'わたしは  ワープロで  手紙を  書きます。';
  const marks = [
    { at: 13, base: '手紙', kana: 'てがみ' },
    { at: 18, base: '書', kana: 'か' },
  ];
  assert.deepEqual(annotateWithMarks(text, marks), [
    { t: 'text', s: 'わたしは  ワープロで  ' },
    { t: 'ruby', base: '手紙', kana: 'てがみ' },
    { t: 'text', s: 'を  ' },
    { t: 'ruby', base: '書', kana: 'か' },
    { t: 'text', s: 'きます。' },
  ]);
});

test('沒有標註時回傳單一 text token', () => {
  assert.deepEqual(annotateWithMarks('これは 本です。', []), [{ t: 'text', s: 'これは 本です。' }]);
});

test('標註位置對不上文字時跳過該筆，不拋錯也不錯位', () => {
  const marks = [{ at: 3, base: '手紙', kana: 'てがみ' }]; // at 指到的不是 手紙
  assert.deepEqual(annotateWithMarks('これは 本です。', marks), [{ t: 'text', s: 'これは 本です。' }]);
});

test('標註未依 at 排序時仍正確切詞', () => {
  const marks = [
    { at: 18, base: '書', kana: 'か' },
    { at: 13, base: '手紙', kana: 'てがみ' },
  ];
  const tokens = annotateWithMarks('わたしは  ワープロで  手紙を  書きます。', marks);
  assert.deepEqual(tokens.filter((t) => t.t === 'ruby').map((t) => t.base), ['手紙', '書']);
});

test('空字串與非字串輸入回傳空陣列', () => {
  assert.deepEqual(annotateWithMarks('', []), []);
  assert.deepEqual(annotateWithMarks(null, []), []);
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_ruby.js`
Expected: FAIL，`Cannot find module '../../app/core/ruby.js'`

- [ ] **Step 3: 實作**

建立 `app/core/ruby.js`：

```js
/**
 * 振假名切詞（規格 §9.3、§13 決定 9）。純函式，回傳 token 陣列，不產生 DOM——
 * `<ruby>` 由 ui/html.js 組裝，core 不得碰 document。
 *
 * 兩條路徑共用同一個 token 形狀：
 *   - annotateWithMarks：課本 sentences[].ruby 的精確標註，優先使用
 *   - annotateWithLexicon（Task 2）：練習Ａ／Ｂ 沒有標註，以詞典最長匹配
 */

/**
 * 標註位置對不上時「跳過該筆」而不是拋錯：ruby 是輔助資訊，語料重抽而位移
 * 不該讓整個題目渲染失敗。真正的把關在 Task 3 的漂移測試——那裡對不上就紅燈。
 */
export function annotateWithMarks(text, marks) {
  if (typeof text !== 'string' || text.length === 0) return [];
  const valid = (marks || [])
    .filter((m) => m && typeof m.at === 'number' && typeof m.base === 'string'
      && text.slice(m.at, m.at + m.base.length) === m.base)
    .sort((a, b) => a.at - b.at);

  const out = [];
  let cursor = 0;
  for (const m of valid) {
    if (m.at < cursor) continue; // 重疊標註：保留先出現者
    if (m.at > cursor) out.push({ t: 'text', s: text.slice(cursor, m.at) });
    out.push({ t: 'ruby', base: m.base, kana: m.kana });
    cursor = m.at + m.base.length;
  }
  if (cursor < text.length) out.push({ t: 'text', s: text.slice(cursor) });
  return out;
}
```

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test tests/app/test_ruby.js`
Expected: PASS（5 個測試）

- [ ] **Step 5: 提交**

```bash
git add app/core/ruby.js tests/app/test_ruby.js
git commit -m "feat(core): 振假名依課本標註切詞"
```

---

### Task 2: `core/ruby.js` — 詞典最長匹配

練習Ａ 的 template／slots 與練習Ｂ 的句子課本都沒附 ruby。這些文字要加注只能靠詞典（規格 §13 決定 9）。只在**漢字連續段**上做最長匹配，不碰假名與標點。

**Files:**
- Modify: `app/core/ruby.js`
- Test: `tests/app/test_ruby.js`

**Interfaces:**
- Consumes: Task 1 的 `Token` 形狀
- Produces:
  - `buildLexicon(json)` → `Map<string, string>`，`json` 為 `{ auto: {...}, manual: {...} }`，`manual` 覆蓋 `auto`
  - `annotateWithLexicon(text, lex)` → `Token[]`，`lex` 為上者回傳的 Map

- [ ] **Step 1: 寫失敗的測試**

加到 `tests/app/test_ruby.js` 末尾：

```js
import { buildLexicon, annotateWithLexicon } from '../../app/core/ruby.js';

test('buildLexicon 以 manual 覆蓋 auto', () => {
  const lex = buildLexicon({ auto: { 何: 'なに', 手紙: 'てがみ' }, manual: { 何: 'なん' } });
  assert.equal(lex.get('何'), 'なん');
  assert.equal(lex.get('手紙'), 'てがみ');
});

test('buildLexicon 容忍缺少 auto／manual 區', () => {
  assert.equal(buildLexicon({}).size, 0);
  assert.equal(buildLexicon(null).size, 0);
});

test('最長匹配優先：日本人 不可被切成 日本 ＋ 人', () => {
  const lex = buildLexicon({ auto: { 日本: 'にほん', 日本人: 'にほんじん' } });
  const tokens = annotateWithLexicon('日本人は はしで 食べます。', lex);
  assert.deepEqual(tokens[0], { t: 'ruby', base: '日本人', kana: 'にほんじん' });
});

test('詞典沒有的漢字原樣留在 text token，不加注', () => {
  const lex = buildLexicon({ auto: { 手紙: 'てがみ' } });
  assert.deepEqual(annotateWithLexicon('電気を 消します。', lex), [
    { t: 'text', s: '電気を 消します。' },
  ]);
});

test('只在漢字段上匹配，假名與標點不動', () => {
  const lex = buildLexicon({ auto: { 書: 'か' } });
  assert.deepEqual(annotateWithLexicon('手紙を 書きます。', lex), [
    { t: 'text', s: '手紙を ' },
    { t: 'ruby', base: '書', kana: 'か' },
    { t: 'text', s: 'きます。' },
  ]);
});

test('同一段漢字中匹配不到的字不會吞掉後面匹配得到的字', () => {
  const lex = buildLexicon({ auto: { 紙: 'かみ' } });
  assert.deepEqual(annotateWithLexicon('手紙', lex), [
    { t: 'text', s: '手' },
    { t: 'ruby', base: '紙', kana: 'かみ' },
  ]);
});

test('相鄰的 text token 會被合併，不產生碎片', () => {
  const lex = buildLexicon({ auto: {} });
  assert.deepEqual(annotateWithLexicon('あ亜い', lex), [{ t: 'text', s: 'あ亜い' }]);
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_ruby.js`
Expected: FAIL，`buildLexicon is not a function`

- [ ] **Step 3: 實作**

加到 `app/core/ruby.js` 末尾：

```js
const KANJI_RUN = /[一-鿿]+/g;

/**
 * manual 覆蓋 auto：auto 區是從語料機械產生的，重跑會被整區覆寫；人工補的
 * 判讀必須活得比重跑久，因此分成兩區而不是混在同一個物件裡。
 */
export function buildLexicon(json) {
  const lex = new Map();
  for (const [base, kana] of Object.entries((json && json.auto) || {})) lex.set(base, kana);
  for (const [base, kana] of Object.entries((json && json.manual) || {})) lex.set(base, kana);
  return lex;
}

/** 相鄰 text token 合併，讓輸出與「沒加注」時完全一致，測試才好寫也好讀。 */
function pushText(out, s) {
  if (!s) return;
  const last = out[out.length - 1];
  if (last && last.t === 'text') last.s += s;
  else out.push({ t: 'text', s });
}

/**
 * 只在漢字連續段上做最長匹配。匹配不到就退一個字元繼續試，因此
 * 「手紙」在詞典只有「紙」時會切成 text('手') ＋ ruby('紙')，而不是整段放棄。
 */
export function annotateWithLexicon(text, lex) {
  if (typeof text !== 'string' || text.length === 0) return [];
  const out = [];
  let cursor = 0;
  KANJI_RUN.lastIndex = 0;
  for (const m of text.matchAll(KANJI_RUN)) {
    pushText(out, text.slice(cursor, m.index));
    const run = m[0];
    let i = 0;
    while (i < run.length) {
      let hit = null;
      for (let len = run.length - i; len > 0; len--) {
        const cand = run.slice(i, i + len);
        if (lex.has(cand)) { hit = cand; break; }
      }
      if (hit) {
        out.push({ t: 'ruby', base: hit, kana: lex.get(hit) });
        i += hit.length;
      } else {
        pushText(out, run[i]);
        i += 1;
      }
    }
    cursor = m.index + run.length;
  }
  pushText(out, text.slice(cursor));
  return out;
}
```

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test tests/app/test_ruby.js`
Expected: PASS（12 個測試）

- [ ] **Step 5: 提交**

```bash
git add app/core/ruby.js tests/app/test_ruby.js
git commit -m "feat(core): 振假名詞典最長匹配"
```

---

### Task 3: `data/ruby-lexicon.json` 的 `auto` 區與漂移測試

詞典的來源必須是**這本課本自己的標註**（規格 §13 決定 9）：課本對同一個詞標 なん 或 なに 是教學上的既定答案，通用字典未必一致，而這些字會直接印在題目上被使用者記下來。

**Files:**
- Create: `tools/draft/ruby_lexicon.py`
- Create: `data/ruby-lexicon.json`
- Test: `tests/app/test_ruby_lexicon.js`

**Interfaces:**
- Produces: `data/ruby-lexicon.json`，形狀 `{ "auto": { base: kana }, "manual": { base: kana }, "ambiguous": { base: [kana, ...] } }`。`ambiguous` 只是說明文件，程式不讀——列出刻意不加注的多讀音字，讓後續維護者知道那不是遺漏。

- [ ] **Step 1: 寫產生腳本**

建立 `tools/draft/ruby_lexicon.py`：

```python
"""從課本自身的 ruby 標註產生振假名詞典的 auto 區（規格 §13 決定 9）。

多讀音字（同一個 base 在不同句子標了不同假名）一律排除，列入 ambiguous
區備查——寧可不加注，也不要在題目上印出錯的讀音。

用法：python3 tools/draft/ruby_lexicon.py
直接改寫 data/ruby-lexicon.json 的 auto 與 ambiguous 區，manual 區原樣保留。
"""
import json
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/ruby-lexicon.json"


def collect():
    readings = defaultdict(Counter)
    for n in range(1, 16):
        data = json.loads((ROOT / f"data/lessons/{n:02d}.json").read_text(encoding="utf-8"))
        for s in data.get("sentences", []):
            for r in s.get("ruby", []):
                base, kana = r.get("base"), r.get("kana")
                if base and kana:
                    readings[base][kana] += 1
    auto, ambiguous = {}, {}
    for base, counter in sorted(readings.items()):
        if len(counter) == 1:
            auto[base] = next(iter(counter))
        else:
            ambiguous[base] = sorted(counter)
    return auto, ambiguous


def main():
    auto, ambiguous = collect()
    existing = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    out = {
        "auto": auto,
        "manual": existing.get("manual", {}),
        "ambiguous": ambiguous,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=False) + "\n",
                   encoding="utf-8")
    print(f"auto={len(auto)} manual={len(out['manual'])} ambiguous={len(ambiguous)}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 執行腳本產生詞典**

Run: `python3 tools/draft/ruby_lexicon.py`
Expected: 印出 `auto=380 manual=0 ambiguous=7`（若數字有出入，以實際為準並記於驗收報告；`ambiguous` 應為 人／何／月／上／父／母／少）

- [ ] **Step 3: 寫漂移測試**

建立 `tests/app/test_ruby_lexicon.js`：

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { buildLexicon, annotateWithLexicon } from '../../app/core/ruby.js';

const lexJson = JSON.parse(readFileSync(new URL('../../data/ruby-lexicon.json', import.meta.url)));

function allLessons() {
  const out = [];
  for (let n = 1; n <= 15; n++) {
    out.push(JSON.parse(readFileSync(
      new URL(`../../data/lessons/${String(n).padStart(2, '0')}.json`, import.meta.url))));
  }
  return out;
}

test('auto 區的每一條都能從當前語料的標註回推得到（語料重抽即紅燈）', () => {
  const fromCorpus = new Map();
  for (const d of allLessons()) {
    for (const s of d.sentences || []) {
      for (const r of s.ruby || []) {
        if (!fromCorpus.has(r.base)) fromCorpus.set(r.base, new Set());
        fromCorpus.get(r.base).add(r.kana);
      }
    }
  }
  for (const [base, kana] of Object.entries(lexJson.auto)) {
    const readings = fromCorpus.get(base);
    assert.ok(readings, `詞典的 ${base} 已不存在於語料標註中`);
    assert.ok(readings.has(kana), `${base} 的讀音 ${kana} 已不存在於語料標註中`);
    assert.equal(readings.size, 1, `${base} 在語料中已出現多種讀音，應移出 auto 區`);
  }
});

test('多讀音字不得出現在 auto 區（會在題目上印出錯的讀音）', () => {
  for (const base of Object.keys(lexJson.ambiguous || {})) {
    assert.equal(lexJson.auto[base], undefined, `多讀音字 ${base} 不得自動加注`);
  }
});

test('詞典的 kana 全為假名，base 全含漢字', () => {
  const lex = buildLexicon(lexJson);
  for (const [base, kana] of lex) {
    assert.match(base, /[一-鿿]/, `${base} 不含漢字，不該進詞典`);
    assert.match(kana, /^[぀-ゟ゠-ヿー]+$/, `${base} 的讀音 ${kana} 不是純假名`);
  }
});

test('加注後移除 rt 必須還原成原文（絕不改動句子本身）', () => {
  const lex = buildLexicon(lexJson);
  for (const d of allLessons()) {
    for (const p of d.patterns || []) {
      const text = p.template || '';
      const back = annotateWithLexicon(text, lex)
        .map((t) => (t.t === 'ruby' ? t.base : t.s)).join('');
      assert.equal(back, text, `${p.id} 加注後無法還原`);
    }
  }
});
```

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test tests/app/test_ruby_lexicon.js`
Expected: PASS（4 個測試）

- [ ] **Step 5: 提交**

```bash
git add tools/draft/ruby_lexicon.py data/ruby-lexicon.json tests/app/test_ruby_lexicon.js
git commit -m "feat(data): 振假名詞典自課本標註產生，含漂移偵測"
```

---

### Task 4: 人工補足 `manual` 區到接近全覆蓋

`auto` 區只覆蓋練習Ａ／Ｂ 文字中 89% 的漢字。缺口是**課本從未在標註句中出現過的詞**（電気、部屋、先週、涼しい、手伝います 等），不是歧義——逐條補進 `manual` 即可。7 個多讀音字維持不加注。

**Files:**
- Modify: `data/ruby-lexicon.json`
- Test: `tests/app/test_ruby_lexicon.js`

**Interfaces:**
- Consumes: Task 3 的 `data/ruby-lexicon.json`
- Produces: 同一檔案的 `manual` 區補滿，覆蓋率 ≥ 97%

- [ ] **Step 1: 寫失敗的覆蓋率測試**

加到 `tests/app/test_ruby_lexicon.js` 末尾：

```js
const KANJI_RUN = /[一-鿿]+/g;

function pdTexts() {
  const texts = [];
  for (const d of allLessons()) {
    for (const p of d.patterns || []) {
      texts.push(p.template || '');
      for (const vals of Object.values(p.slots || {})) {
        for (const v of vals) if (typeof v === 'string') texts.push(v);
      }
    }
    for (const dr of d.drills || []) {
      texts.push(dr.model_answer || '', dr.model_cue || '');
      for (const it of dr.items || []) if (typeof it === 'string') texts.push(it);
    }
  }
  return texts;
}

test('練習Ａ／Ｂ 文字的漢字覆蓋率達 97% 以上', () => {
  const lex = buildLexicon(lexJson);
  const ambiguous = new Set(Object.keys(lexJson.ambiguous || {}));
  let covered = 0, total = 0;
  const missing = new Map();
  for (const text of pdTexts()) {
    for (const token of annotateWithLexicon(text, lex)) {
      if (token.t === 'ruby') { covered += token.base.length; total += token.base.length; continue; }
      for (const run of token.s.match(KANJI_RUN) || []) {
        total += run.length;
        for (const ch of run) {
          // 多讀音字是「刻意不加注」，不算進缺口（規格 §13 決定 9）
          if (ambiguous.has(ch)) covered += 1;
          else missing.set(ch, (missing.get(ch) || 0) + 1);
        }
      }
    }
  }
  const rate = covered / total;
  const worst = [...missing.entries()].sort((a, b) => b[1] - a[1]).slice(0, 20);
  assert.ok(rate >= 0.97,
    `覆蓋率 ${(rate * 100).toFixed(1)}% 未達 97%，待補：${JSON.stringify(worst)}`);
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_ruby_lexicon.js`
Expected: FAIL，訊息列出覆蓋率約 89% 與待補字清單（電、気、部、先、涼、手、伝、広、週、黒 等）

- [ ] **Step 3: 人工補 `manual` 區**

依測試訊息列出的待補字，逐條補進 `data/ruby-lexicon.json` 的 `manual`。**以詞為單位補，不以單字為單位**——單字進詞典會在別的詞裡被誤匹配（補「気」→ き，「天気」就會被切成 天＋気）。範例（實際內容依測試訊息為準）：

```json
"manual": {
  "電気": "でんき",
  "部屋": "へや",
  "先週": "せんしゅう",
  "先月": "せんげつ",
  "涼": "すず",
  "手伝": "てつだ",
  "広": "ひろ",
  "黒": "くろ",
  "階段": "かいだん",
  "牛乳": "ぎゅうにゅう"
}
```

補完後重跑測試，依新的待補清單再補一輪，直到通過。**補的來源必須是課本**：該詞若在某課 `vocab` 有 `kanji`／`kana` 欄位，以那組為準（`grep` 該漢字於 `data/lessons/*.json` 的 vocab 即可查到），不得憑記憶填寫。

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test "tests/app/*.js"`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add data/ruby-lexicon.json tests/app/test_ruby_lexicon.js
git commit -m "feat(data): 人工補足振假名詞典，覆蓋率達 97% 以上"
```

---

### Task 5: `ui/html.js` — token 組成 `<ruby>` HTML

`session.js` 目前自帶一份 `escapeHtml`。引擎分層後多個檔都要用，抽出共用，順便加上 ruby 的 HTML 組裝。**這裡是純字串處理**，仍不碰 DOM。

**Files:**
- Create: `app/ui/html.js`
- Modify: `app/ui/session.js`（移除本地 `escapeHtml`，改 import）
- Test: `tests/app/test_html.js`

**Interfaces:**
- Consumes: `Token[]`（Task 1、2）
- Produces:
  - `escapeHtml(s)` → `string`
  - `rubyHtml(tokens, { hideRt = false } = {})` → `string`；`hideRt` 為真時只輸出 base，**連 `<rt>` 都不產生**（不是用 CSS 藏起來——答案若在 DOM 裡，檢視原始碼或選取文字就看得到）

- [ ] **Step 1: 寫失敗的測試**

建立 `tests/app/test_html.js`：

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { escapeHtml, rubyHtml } from '../../app/ui/html.js';

test('escapeHtml 轉義五個危險字元', () => {
  assert.equal(escapeHtml(`<a href="x">&'</a>`),
    '&lt;a href=&quot;x&quot;&gt;&amp;&#39;&lt;/a&gt;');
});

test('rubyHtml 組出 ruby 標籤', () => {
  const tokens = [
    { t: 'ruby', base: '手紙', kana: 'てがみ' },
    { t: 'text', s: 'を 書きます。' },
  ];
  assert.equal(rubyHtml(tokens), '<ruby>手紙<rt>てがみ</rt></ruby>を 書きます。');
});

test('hideRt 時不產生 rt 元素（答案不得存在於 DOM 中）', () => {
  const tokens = [{ t: 'ruby', base: '手紙', kana: 'てがみ' }];
  const html = rubyHtml(tokens, { hideRt: true });
  assert.equal(html, '手紙');
  assert.ok(!html.includes('てがみ'), '讀音不得出現在輸出中');
});

test('rubyHtml 一律轉義文字內容', () => {
  const tokens = [{ t: 'text', s: '<script>' }, { t: 'ruby', base: '<b>', kana: '<i>' }];
  const html = rubyHtml(tokens);
  assert.ok(!html.includes('<script>'));
  assert.ok(html.includes('&lt;script&gt;'));
  assert.ok(html.includes('<ruby>&lt;b&gt;<rt>&lt;i&gt;</rt></ruby>'));
});

test('換行轉成 br，讓代入題的多行題幹不擠成一行', () => {
  assert.equal(rubyHtml([{ t: 'text', s: 'a\nb' }]), 'a<br>b');
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_html.js`
Expected: FAIL，`Cannot find module '../../app/ui/html.js'`

- [ ] **Step 3: 實作**

建立 `app/ui/html.js`：

```js
// HTML 字串組裝。純字串處理（不碰 document），供 ui/ 與 engines/ 共用。
const ENTITIES = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' };

export function escapeHtml(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ENTITIES[c]);
}

/**
 * 規格 §9.3：假名置於漢字上方（ruby-position: over，瀏覽器預設值）。
 *
 * hideRt 為真時**不產生 rt 元素**，而不是以 CSS 隱藏——考讀音的題型若把答案
 * 留在 DOM 裡，長按選取或檢視原始碼就看得到，等於沒藏。
 */
export function rubyHtml(tokens, { hideRt = false } = {}) {
  return (tokens || []).map((t) => {
    if (t.t === 'ruby') {
      const base = escapeHtml(t.base);
      return hideRt ? base : `<ruby>${base}<rt>${escapeHtml(t.kana)}</rt></ruby>`;
    }
    return escapeHtml(t.s).replace(/\n/g, '<br>');
  }).join('');
}
```

修改 `app/ui/session.js`：刪除檔尾的 `escapeHtml` 函式，並在檔案開頭加入
`import { escapeHtml } from './html.js';`

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test "tests/app/*.js"`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add app/ui/html.js tests/app/test_html.js app/ui/session.js
git commit -m "refactor(ui): 抽出共用的 HTML 組裝，加上 ruby 渲染"
```

---

### Task 6: `app/engines/` 分層

規格 §13 決定 1 把這層延到 2b，理由是在此之前沒有行為差異可承載。現在 `jp2zh` 是選擇題，分歧出現了。**這一步只搬家，不改行為**——既有測試必須全綠且不需修改。

**Files:**
- Create: `app/engines/text.js`、`app/engines/recall.js`、`app/engines/transform.js`、`app/engines/substitute.js`、`app/engines/cloze.js`、`app/engines/index.js`
- Modify: `app/ui/session.js`
- Test: `tests/app/test_engines.js`

**Interfaces:**
- Produces:
  - 每個引擎：`render(item, host, opts) → { readValue(): string }`。`host` 是引擎專用的容器元素，引擎把**題幹與作答控制項**寫進去；進度、按鈕、結果畫面仍由 `session.js` 負責。`opts` 為 `{ rubyTokens, hideRt, listening, speak }`。
  - `engines/index.js`：`engineFor(item)` → 上述模組；未知 engine 退回 `text`
  - `isImeComposing(e)` 從 `ui/session.js` 移到 `engines/text.js` 並由該處 export（`session.js` 改為 re-export，維持既有測試的 import 路徑不變）

- [ ] **Step 1: 寫失敗的測試**

建立 `tests/app/test_engines.js`：

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { engineFor } from '../../app/engines/index.js';
import * as text from '../../app/engines/text.js';
import * as recall from '../../app/engines/recall.js';

const item = (over = {}) => ({
  id: 'x', engine: 'recall', prompt: { type: 'text', text: '書', hint: '寫出讀音' },
  answer: 'かく', covers: [], skills: [], ...over,
});

test('engineFor 依 item.engine 分派', () => {
  assert.equal(engineFor(item({ engine: 'recall' })), recall);
  assert.equal(engineFor(item({ engine: 'cloze' })).ENGINE, 'cloze');
});

test('engineFor 遇到未知引擎退回打字作答，不拋錯', () => {
  assert.equal(engineFor(item({ engine: 'mystery' })), text);
  assert.equal(engineFor(null), text);
});

test('每個引擎都 export render 與 ENGINE', async () => {
  for (const name of ['text', 'recall', 'transform', 'substitute', 'cloze']) {
    const mod = await import(`../../app/engines/${name}.js`);
    assert.equal(typeof mod.render, 'function', `${name} 缺 render`);
    assert.equal(typeof mod.ENGINE, 'string', `${name} 缺 ENGINE`);
  }
});

test('引擎不得 import 其他引擎（規格 §6.1：引擎彼此不互相依賴）', async () => {
  const { readFileSync, readdirSync } = await import('node:fs');
  for (const f of readdirSync(new URL('../../app/engines/', import.meta.url))) {
    if (f === 'index.js') continue;
    const src = readFileSync(new URL(`../../app/engines/${f}`, import.meta.url), 'utf8');
    const bad = [...src.matchAll(/from '\.\/(\w+)\.js'/g)].map((m) => m[1])
      .filter((n) => n !== 'text');
    assert.deepEqual(bad, [], `${f} 不得 import 其他引擎：${bad}`);
  }
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_engines.js`
Expected: FAIL，`Cannot find module '../../app/engines/index.js'`

- [ ] **Step 3: 實作**

建立 `app/engines/text.js`（題幹與輸入框的渲染，內容搬自 `ui/session.js` 的 `showItem`）：

```js
/**
 * 打字作答的共用渲染。四個引擎裡有三個完全共用這份，recall 只有在選擇題時才分歧
 * ——引擎層的價值在於承載那一處分歧，不是為每個引擎各抄一份 DOM。
 *
 * 判斷邏輯不在這裡：readValue() 只把使用者輸入原樣交出去，對錯一律由
 * core/grading.js 判定（規格 §11 的分層要求）。
 */
import { escapeHtml, rubyHtml } from '../ui/html.js';

export const ENGINE = 'text';

const INPUT_ATTRS = 'lang="ja" autocorrect="off" autocapitalize="off" spellcheck="false" autocomplete="off"';

/**
 * 日文輸入法（IME）組字期間按下的 Enter 是「確定候補字」，不是「送出答案」——
 * 兩者是同一顆實體按鍵，只能靠事件狀態分辨：組字中的 keydown 帶
 * isComposing=true（舊版瀏覽器則是 keyCode 229）。
 *
 * 不分辨的後果不只是提前送出：submit() 會同時把那筆「答錯」寫進事件日誌，
 * 使用者選個字就被記一次答錯，SRS 的熟悉度會被自己的輸入法污染。
 *
 * 只有這兩個欄位都不成立時才視為真的要送出——判斷寫成「有值才擋」而非
 * 「沒值就擋」，否則不帶這些欄位的環境會永遠送不出答案。
 */
export function isImeComposing(e) {
  return e.isComposing === true || e.keyCode === 229;
}

/** 題幹的 HTML：有振假名 token 就用 ruby 渲染，否則純文字。 */
export function promptHtml(item, opts = {}) {
  if (opts.listening) return '<span class="listening">🔊 聽寫：請聽題目作答</span>';
  if (opts.rubyTokens) return rubyHtml(opts.rubyTokens, { hideRt: opts.hideRt });
  return escapeHtml(item.prompt.text).replace(/\n/g, '<br>');
}

export function render(item, host, opts = {}) {
  host.innerHTML = `
    <div class="prompt">${promptHtml(item, opts)}</div>
    <div class="hint">${escapeHtml(item.prompt.hint || '')}</div>
    <input id="ans" type="text" ${INPUT_ATTRS}>`;
  const input = host.querySelector('#ans');
  input.focus();
  input.onkeydown = (e) => {
    if (e.key === 'Enter' && !isImeComposing(e)) opts.onSubmit?.();
  };
  if (opts.listening) opts.speak?.(item.prompt.text);
  return { readValue: () => input.value };
}
```

建立 `app/engines/recall.js`：

```js
/**
 * 對照題。`item.choices` 存在時渲染選擇題（jp2zh），否則與其他引擎一樣是打字作答。
 * 這是引擎層存在的唯一理由（規格 §13 決定 1）。
 */
import { escapeHtml, rubyHtml } from '../ui/html.js';
import * as text from './text.js';

export const ENGINE = 'recall';

export function render(item, host, opts = {}) {
  if (!item.choices || !item.choices.length) return text.render(item, host, opts);

  const promptHtml = opts.rubyTokens
    ? rubyHtml(opts.rubyTokens, { hideRt: opts.hideRt })
    : escapeHtml(item.prompt.text);
  host.innerHTML = `
    <div class="prompt">${opts.listening ? '🔊 聽寫：請聽題目作答' : promptHtml}</div>
    <div class="hint">${escapeHtml(item.prompt.hint || '')}</div>
    <div class="choices">${item.choices.map((c, i) =>
      `<button class="choice" data-i="${i}">${escapeHtml(c)}</button>`).join('')}</div>`;

  let picked = '';
  for (const btn of host.querySelectorAll('.choice')) {
    btn.onclick = () => {
      picked = item.choices[Number(btn.dataset.i)];
      for (const b of host.querySelectorAll('.choice')) b.classList.remove('picked');
      btn.classList.add('picked');
      // 選擇題選完即送出：再要求按一次「送出」只是多一步，沒有修改空間可言。
      opts.onSubmit?.();
    };
  }
  if (opts.listening) opts.speak?.(item.prompt.text);
  return { readValue: () => picked };
}
```

建立 `app/engines/transform.js`、`app/engines/cloze.js`（兩者內容相同，只有 `ENGINE` 不同）：

```js
// 變換題：作答形式與打字作答無異，引擎只是讓分派表完整（規格 §6.1 列四個引擎）。
import * as text from './text.js';

export const ENGINE = 'transform';   // cloze.js 為 'cloze'

export const render = text.render;
```

建立 `app/engines/substitute.js`：

```js
// 代入題。題幹是「例：…／用這些詞造句：…」的多行文字，需要保留換行。
import * as text from './text.js';

export const ENGINE = 'substitute';

export function render(item, host, opts = {}) {
  const handle = text.render(item, host, opts);
  host.querySelector('.prompt')?.classList.add('multiline');
  return handle;
}
```

建立 `app/engines/index.js`：

```js
// 引擎分派。未知的 engine 退回打字作答而不是拋錯——生成器若新增了題型而忘了
// 加引擎，該題仍可作答，不會讓整輪練習中斷。
import * as text from './text.js';
import * as recall from './recall.js';
import * as transform from './transform.js';
import * as substitute from './substitute.js';
import * as cloze from './cloze.js';

const REGISTRY = { recall, transform, substitute, cloze };

export function engineFor(item) {
  return REGISTRY[item && item.engine] || text;
}
```

修改 `app/ui/session.js` 的 `showItem()`，改為委派引擎（其餘函式不動）：

```js
import { engineFor } from '../engines/index.js';
import { escapeHtml } from './html.js';
export { isImeComposing } from '../engines/text.js';

  let handle = null;

  function showItem() {
    if (idx >= items.length) return onDone();
    const it = items[idx];
    usedHint = false;
    host.innerHTML = `
      <div id="question"></div>
      <button id="submit">送出</button>
      <button id="hint">看提示</button>
      <div class="progress">${idx + 1} / ${items.length}</div>`;
    handle = engineFor(it).render(it, host.querySelector('#question'), {
      ...deps.presentOpts?.(it),
      onSubmit: submit,
    });
    shownAt = Date.now();
    host.querySelector('#submit').onclick = submit;
    host.querySelector('#hint').onclick = () => { usedHint = true; revealHint(it); };
  }
```

並把 `submit()` 中取值的那一行由 `host.querySelector('#ans').value` 改為 `handle.readValue()`。

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test "tests/app/*.js"`
Expected: 全部 PASS。**既有的 `test_session.js` 不得修改**——這一步是搬家，行為不變；若它紅了，是搬壞了而不是測試過時。

- [ ] **Step 5: 提交**

```bash
git add app/engines tests/app/test_engines.js app/ui/session.js
git commit -m "refactor(engines): 建立引擎分層，session 退化為驅動器"
```

---

### Task 7: 振假名接進題目呈現

規格 §9.3：預設一律顯示，不需按鈕。**唯一例外是考讀音的題型**——由 `covers` 是否含 `w:*:reading` 判定，不由使用者設定控制（使用者誤開設定就會讓那類題目失效）。

**Files:**
- Modify: `app/main.js`、`app/ui/session.js`、`index.html`
- Create: `app/ui/present.js`
- Test: `tests/app/test_present.js`

**Interfaces:**
- Produces: `app/ui/present.js` 的 `presentOptsFor(item, { lex, sentenceMarks })` → `{ rubyTokens, hideRt }`
  - `sentenceMarks`：`Map<sentenceId, marks[]>`，讓 cloze 題用得到課本的精確標註
  - 判定順序：題目帶得出句子 id 且該句有標註 → `annotateWithMarks`；否則 → `annotateWithLexicon`

- [ ] **Step 1: 寫失敗的測試**

建立 `tests/app/test_present.js`：

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { presentOptsFor } from '../../app/ui/present.js';
import { buildLexicon } from '../../app/core/ruby.js';

const lex = buildLexicon({ auto: { 手紙: 'てがみ', 書: 'か' } });

test('考讀音的題型隱藏讀音（covers 含 :reading）', () => {
  const item = { id: 'recall:かく:kanji2kana', covers: ['w:書きます:reading'], prompt: { text: '書きます' } };
  const opts = presentOptsFor(item, { lex, sentenceMarks: new Map() });
  assert.equal(opts.hideRt, true);
});

test('其他題型一律顯示讀音', () => {
  const item = { id: 'recall:かく:zh2jp', covers: ['w:書きます'], prompt: { text: '手紙' } };
  const opts = presentOptsFor(item, { lex, sentenceMarks: new Map() });
  assert.equal(opts.hideRt, false);
  assert.deepEqual(opts.rubyTokens, [{ t: 'ruby', base: '手紙', kana: 'てがみ' }]);
});

test('題目對應得到課本句子時，優先用課本的精確標註', () => {
  const marks = new Map([['L07-文型-1', [{ at: 0, base: '手紙', kana: 'おてがみ' }]]]);
  const item = {
    id: 'cloze:L07-文型-1:3', covers: ['p:wo:object'],
    prompt: { text: '手紙を 書きます。' }, source_id: 'L07-文型-1',
  };
  const opts = presentOptsFor(item, { lex, sentenceMarks: marks });
  // 詞典會給 てがみ，課本標註給 おてがみ——必須以課本為準
  assert.equal(opts.rubyTokens[0].kana, 'おてがみ');
});

test('題幹無漢字時回傳單一 text token', () => {
  const item = { id: 'x', covers: [], prompt: { text: 'これは なんですか。' } };
  const opts = presentOptsFor(item, { lex, sentenceMarks: new Map() });
  assert.deepEqual(opts.rubyTokens, [{ t: 'text', s: 'これは なんですか。' }]);
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_present.js`
Expected: FAIL，`Cannot find module '../../app/ui/present.js'`

- [ ] **Step 3: 實作**

建立 `app/ui/present.js`：

```js
/**
 * 呈現修飾的決策點（規格 §9.3）：這一題的題幹要不要加振假名、要不要藏讀音。
 *
 * hideRt 由 covers 判定而非使用者設定——考讀音的題型若顯示 rt，答案就直接
 * 寫在題目上。規格明定此判斷不可由設定控制，避免使用者誤開後題目失效。
 */
import { annotateWithMarks, annotateWithLexicon } from '../core/ruby.js';

export function presentOptsFor(item, { lex, sentenceMarks }) {
  const hideRt = (item.covers || []).some((c) => c.endsWith(':reading'));
  const text = item.prompt?.text || '';
  const marks = item.source_id && sentenceMarks ? sentenceMarks.get(item.source_id) : null;
  const rubyTokens = marks && marks.length
    ? annotateWithMarks(text, marks)
    : annotateWithLexicon(text, lex);
  return { rubyTokens, hideRt };
}
```

修改 `app/main.js`：

1. `fetchJson('data/ruby-lexicon.json')` 加入 `Promise.all`，並 `const lex = buildLexicon(rubyJson);`
2. 建立句子標註索引：
   ```js
   const sentenceMarks = new Map();
   for (const s of idx.sentences) if (s.ruby?.length) sentenceMarks.set(s.id, s.ruby);
   ```
3. 傳給 `renderSession`：`presentOpts: (it) => presentOptsFor(it, { lex, sentenceMarks })`

修改 `app/generators/cloze.js`：`yield` 的物件加上 `source_id: s.id`，讓挖空題用得到課本標註（`substitute` 與 `recall` 無對應句子，不需此欄位）。

修改 `index.html` 的 `<style>`，加入：

```css
  ruby { ruby-position: over; }
  rt { font-size: .5em; color: #666; }
  .prompt.multiline { white-space: pre-line; }
  .choices { display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px; }
  button.choice { background: #fff; color: #1a1a1a; border: 1px solid #ccc; text-align: left;
    font-size: 1.05rem; padding: 12px; margin: 0; }
  button.choice.picked { background: #2d6cdf; color: #fff; }
  .listening { color: #2d6cdf; }
  @media (prefers-color-scheme: dark) {
    rt { color: #aaa; }
    button.choice { background: #1f2229; color: #eee; border-color: #444; }
  }
```

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test "tests/app/*.js"`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add app/ui/present.js tests/app/test_present.js app/main.js app/generators/cloze.js index.html
git commit -m "feat(ui): 題幹顯示振假名，考讀音的題型隱藏 rt"
```

---

### Task 8: `jp2zh` 選擇題生成

規格 §6.1 表列 recall 涵蓋需求 #1；Phase 1 只做了中→日與漢字→假名，日→中延到 2b 做成選擇題。**誘答必須決定性**：同一題每次展開得到同一組選項，否則 id 相同而內容不同。

**Files:**
- Modify: `app/generators/recall.js`
- Test: `tests/app/test_recall.js`

**Interfaces:**
- Produces: 每個有 `zh` 的單字多一道 `recall:<key>:jp2zh`，形狀為既有 Item 再加 `choices: string[]`（4 個中文釋義，含正解，順序決定性）。`answer` 為正解中文。

- [ ] **Step 1: 寫失敗的測試**

加到 `tests/app/test_recall.js` 末尾：

```js
const jpVocab = [
  { kana: 'きります', kanji: '切ります', zh: '剪，切', lesson: 7, no: 1 },
  { kana: 'おくります', kanji: '送ります', zh: '寄送', lesson: 7, no: 2 },
  { kana: 'あげます', kanji: null, zh: '給，送', lesson: 7, no: 3 },
  { kana: 'もらいます', kanji: null, zh: '接受，得到', lesson: 7, no: 4 },
  { kana: 'かします', kanji: '貸します', zh: '借出', lesson: 7, no: 5 },
];

test('jp2zh 產出四選一，含正解', () => {
  const it = [...generate(jpVocab)].find((x) => x.id === 'recall:きります:jp2zh');
  assert.ok(it, '應產生 recall:きります:jp2zh');
  assert.equal(it.engine, 'recall');
  assert.equal(it.prompt.text, '切ります');
  assert.equal(it.answer, '剪，切');
  assert.equal(it.choices.length, 4);
  assert.ok(it.choices.includes('剪，切'));
  assert.equal(new Set(it.choices).size, 4, '選項不得重複');
  assert.deepEqual(it.covers, ['w:切ります']);
  assert.deepEqual(it.skills, ['單字']);
});

test('選項是決定性的：重跑兩次完全一致', () => {
  const a = [...generate(jpVocab)].find((x) => x.id === 'recall:きります:jp2zh');
  const b = [...generate(jpVocab)].find((x) => x.id === 'recall:きります:jp2zh');
  assert.deepEqual(a.choices, b.choices);
});

test('同課可用詞不足四個時不產生選擇題（寧可不出，也不出兩選一）', () => {
  const few = [
    { kana: 'あ', kanji: null, zh: '甲', lesson: 1, no: 1 },
    { kana: 'い', kanji: null, zh: '乙', lesson: 1, no: 2 },
  ];
  assert.equal([...generate(few)].filter((x) => x.id.endsWith(':jp2zh')).length, 0);
});

test('誘答取自同一課，才不會靠課次差異猜答案', () => {
  const mixed = [...jpVocab, { kana: 'ほん', kanji: '本', zh: '書', lesson: 1, no: 9 }];
  const it = [...generate(mixed)].find((x) => x.id === 'recall:きります:jp2zh');
  assert.ok(!it.choices.includes('書'), '第1課的詞不該成為第7課題目的誘答');
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_recall.js`
Expected: FAIL，`應產生 recall:きります:jp2zh`

- [ ] **Step 3: 實作**

在 `app/generators/recall.js` 加入雜湊與誘答挑選，並在 `generate` 的迴圈末尾產出第三種題：

```js
const CHOICE_COUNT = 4;

/**
 * FNV-1a：把 item id 攤成一個整數種子。用途只有一個——讓誘答的挑選與排序
 * 是 id 的函式，而不是呼叫時機的函式。
 *
 * 規格 §5.3 要求 id 決定性，但只有 id 決定性是不夠的：選項若每次不同，
 * 同一個 id 在 SRS 裡記到的就不是同一道題，歷史照樣失效。
 */
function seedOf(s) {
  let h = 0x811c9dc5;
  for (let i = 0; i < s.length; i++) {
    h ^= s.charCodeAt(i);
    h = Math.imul(h, 0x01000193) >>> 0;
  }
  return h;
}

/** 以種子決定性地取 n 個不重複元素（洗牌後取前 n 個）。 */
function pickDeterministic(pool, n, seed) {
  const arr = [...pool];
  let s = seed;
  for (let i = arr.length - 1; i > 0; i--) {
    s = (Math.imul(s, 1103515245) + 12345) >>> 0;
    const j = s % (i + 1);
    [arr[i], arr[j]] = [arr[j], arr[i]];
  }
  return arr.slice(0, n);
}
```

在 `generate` 內、`byKana` 建好之後，先建同課釋義池：

```js
  const zhByLesson = new Map();
  for (const v of usable) {
    if (!zhByLesson.has(v.lesson)) zhByLesson.set(v.lesson, new Set());
    zhByLesson.get(v.lesson).add(v.zh);
  }
```

在每個 `v` 的迴圈末尾加上：

```js
    // 需求 #1 的日→中方向。打字輸入中文對自學者沒有練習價值（會日文的人打得出
    // 中文），改為四選一——分辨近義詞才是這個方向真正要練的能力。
    const pool = [...(zhByLesson.get(v.lesson) || [])].filter((z) => z !== v.zh).sort();
    if (pool.length >= CHOICE_COUNT - 1) {
      const seed = seedOf(`recall:${key}:jp2zh`);
      const distractors = pickDeterministic(pool, CHOICE_COUNT - 1, seed);
      const choices = pickDeterministic([v.zh, ...distractors], CHOICE_COUNT, seed ^ 0x5bf03635);
      const item = makeItem({
        id: `recall:${key}:jp2zh`, v,
        promptText: v.kanji || v.kana, hint: '選出中文意思',
        answer: v.zh, alternatives: [],
        covers: [meaningConcept],
      });
      yield { ...item, choices };
    }
```

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test "tests/app/*.js"`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add app/generators/recall.js tests/app/test_recall.js
git commit -m "feat(generators): 日→中選擇題，誘答取自同課且決定性"
```

---

### Task 9: 選擇題的評分路徑

選擇題的對錯仍走 `core/grading.js`（規格 §11：判斷邏輯不得寫進 ui／engines）。選項文字是中文，`normalizeAnswer` 的假名轉換不影響它，可直接沿用。

**Files:**
- Modify: `app/ui/session.js`
- Test: `tests/app/test_grading.js`

**Interfaces:**
- Consumes: `engineFor(item).render(...).readValue()` 回傳的選項文字
- Produces: 行為契約——沒選任何選項就送出視為答錯（`isCorrect` 對空字串已回 false，不需額外處理）

- [ ] **Step 1: 寫失敗的測試**

加到 `tests/app/test_grading.js` 末尾：

```js
test('選擇題：選到正解判對', () => {
  const item = { answer: '剪，切', alternatives: [], choices: ['剪，切', '寄送', '借出', '給，送'] };
  assert.equal(gradeAnswer('剪，切', item, 1000, 2000, false).correct, true);
});

test('選擇題：沒選就送出判錯，不當成答對', () => {
  const item = { answer: '剪，切', alternatives: [], choices: ['剪，切', '寄送', '借出', '給，送'] };
  const r = gradeAnswer('', item, 1000, 2000, false);
  assert.equal(r.correct, false);
  assert.equal(r.grade, 1);
});

test('選擇題的中文選項不受假名正規化影響', () => {
  const item = { answer: '接受，得到', alternatives: [], choices: [] };
  assert.equal(gradeAnswer('接受，得到', item, 1000, 2000, false).correct, true);
  assert.equal(gradeAnswer('給，送', item, 1000, 2000, false).correct, false);
});
```

- [ ] **Step 2: 執行測試確認通過或失敗**

Run: `node --test tests/app/test_grading.js`
Expected: PASS（`gradeAnswer` 本就與題型無關；這三個測試是把「選擇題也走同一條路」釘住，避免日後有人在引擎裡自行比對）

- [ ] **Step 3: 補上結果畫面對選擇題的處理**

修改 `app/ui/session.js` 的 `showResult()`：選擇題答錯時不顯示「我這樣寫也對」按鈕——那顆按鈕的用途是接住正規化接不住的自由書寫，選擇題選錯就是選錯，沒有誤判空間。

```js
      ${correct || it.choices ? '' : '<button id="also-ok">我這樣寫也對</button>'}
```

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test "tests/app/*.js"`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add app/ui/session.js tests/app/test_grading.js
git commit -m "feat(ui): 選擇題沿用同一條評分路徑，答錯不提供自訂答案"
```

---

### Task 10: `tools/draft/drills.py` — 練習Ｂ 草稿

規格 §13 決定 7：腳本**只做機械拆分**，不猜 template。猜錯的 template 比沒有 template 更糟——後者一眼看得出還沒標，前者要往返測試才抓得到。

**Files:**
- Create: `tools/draft/drills.py`
- Test: 無（產草稿的離線腳本，正確性由 Task 11 的往返測試把關）

**Interfaces:**
- Produces: 印出 JSON 到 stdout，形狀為 `{ "<drill id>": { "model_answer": str, "model_cue": str, "items": [str], "template": "", "slots": {}, "rows": [], "answer_part": null } }`
  - `｜` 分隔的多組範例 → 拆成 `L07-B7#1`、`L07-B7#2`
  - `・` 分隔的複合 cue → `cue_parts` 欄位列出各段
  - `（…）` 括號提示 → 抽成 `cue_paren` 欄位
  - `items` 為空者**不輸出**（規格 §13 決定 8：插畫型，移出 2b 範圍）

- [ ] **Step 1: 寫腳本**

建立 `tools/draft/drills.py`：

```python
"""產生 data/drills.json 的草稿（規格 §13 決定 7）。

只做機械拆分，不猜 template——猜錯的 template 比空的更糟：空的一眼看得出
還沒標，猜錯的要跑往返測試才抓得到。

items 為空的 29 則不輸出：那些練習的提示詞在插畫裡，不在文字層（決定 8），
2b 不處理。

用法：python3 tools/draft/drills.py > /tmp/drills-draft.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAREN = re.compile(r"（\s*(.+?)\s*）")


def split_multi(drill):
    """以 ｜ 拆成多則。cue 與 answer 的段數不一致時原樣保留，留給人工判斷。"""
    cues = (drill.get("model_cue") or "").split("｜")
    answers = (drill.get("model_answer") or "").split("｜")
    if len(cues) != len(answers):
        return [(drill["id"], drill.get("model_cue") or "", drill.get("model_answer") or "")]
    if len(answers) == 1:
        return [(drill["id"], cues[0], answers[0])]
    return [(f"{drill['id']}#{i + 1}", c.strip(), a.strip())
            for i, (c, a) in enumerate(zip(cues, answers))]


def main():
    out = {}
    for n in range(1, 16):
        data = json.loads((ROOT / f"data/lessons/{n:02d}.json").read_text(encoding="utf-8"))
        for drill in data.get("drills", []):
            items = [x for x in drill.get("items", []) if x.strip()]
            if not items:
                continue  # 插畫型，規格 §13 決定 8
            for did, cue, answer in split_multi(drill):
                paren = PAREN.findall(cue)
                out[did] = {
                    "lesson": n,
                    "model_cue": cue,
                    "model_answer": answer,
                    "items": items,
                    "cue_parts": [p.strip() for p in PAREN.sub("", cue).split("・") if p.strip()],
                    "cue_paren": paren,
                    "template": "",
                    "slots": {},
                    "rows": [],
                    "answer_part": None,
                }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print(file=sys.stderr, *[f"輸出 {len(out)} 則"])


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 執行腳本**

Run: `python3 tools/draft/drills.py > /tmp/drills-draft.json && python3 -c "import json;d=json.load(open('/tmp/drills-draft.json'));print(len(d),'則')"`
Expected: 約 77 ~ 97 則（`｜` 拆分會讓則數多於 77，這是預期的——一則多組範例本來就是多道題的素材）

- [ ] **Step 3: 提交腳本**

```bash
git add tools/draft/drills.py
git commit -m "feat(tools): 練習Ｂ 草稿產生器，只做機械拆分"
```

---

### Task 11: 人工標註 `data/drills.json` 與往返測試

規格 §13 決定 7 的核心：承認練習Ｂ 的真實結構與練習Ａ 相同，補標成那個形狀。**把關方式是往返驗證**——第 0 列的槽位值填回 template 必須逐字等於 `model_answer`，標錯即紅燈，不需人工複查。

**Files:**
- Create: `data/drills.json`
- Test: `tests/app/test_drills_data.js`

**Interfaces:**
- Produces: `data/drills.json`，每筆為
  ```json
  {
    "lesson": 7,
    "template": "{A}で {B}。",
    "slots": { "A": ["はし", "ペン"], "B": ["ごはんを 食べます", "手紙を 書きます"] },
    "rows": [[0, 0], [1, 1]],
    "answer_part": null,
    "model_answer": "はしで ごはんを 食べます。",
    "source_ref": "第7課 練習Ｂ-1"
  }
  ```
  - `rows[0]` 必須對應 `model_answer`（往返測試據此把關）
  - `answer_part`：問答對才有，是 `template` 的**後綴子樣板**（使用者只需產出這一段）。測試要求 `fill(template, row)` 以 `fill(answer_part, row)` 結尾。

- [ ] **Step 1: 寫失敗的測試**

建立 `tests/app/test_drills_data.js`：

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const drills = JSON.parse(readFileSync(new URL('../../data/drills.json', import.meta.url)));
const SLOT = /\{([A-Z])\}/g;

function fill(template, slots, row) {
  const keys = Object.keys(slots);
  return template.replace(SLOT, (_, k) => {
    const i = keys.indexOf(k);
    return slots[k][row[i]] ?? '';
  });
}

test('至少標註 70 則（規格 §13 決定 7 預估 77 則有文字者）', () => {
  assert.ok(Object.keys(drills).length >= 70, `只標了 ${Object.keys(drills).length} 則`);
});

test('往返驗證：第 0 列填回 template 必須逐字等於 model_answer', () => {
  for (const [id, d] of Object.entries(drills)) {
    assert.ok(d.rows.length > 0, `${id} 沒有 rows`);
    assert.equal(fill(d.template, d.slots, d.rows[0]), d.model_answer,
      `${id} 的第 0 列填回 template 與 model_answer 不符`);
  }
});

test('每列的槽位索引都在範圍內（越界會產生半句話）', () => {
  for (const [id, d] of Object.entries(drills)) {
    const keys = Object.keys(d.slots);
    for (const [ri, row] of d.rows.entries()) {
      assert.equal(row.length, keys.length, `${id} 第 ${ri} 列的欄數與槽位數不符`);
      for (const [ki, k] of keys.entries()) {
        assert.ok(d.slots[k][row[ki]] !== undefined, `${id} 第 ${ri} 列的 ${k} 索引越界`);
      }
    }
  }
});

test('template 的槽位全部在 slots 中有定義', () => {
  for (const [id, d] of Object.entries(drills)) {
    const used = new Set([...d.template.matchAll(SLOT)].map((m) => m[1]));
    for (const k of used) assert.ok(d.slots[k], `${id} 的 template 用了未定義的槽位 ${k}`);
    for (const k of Object.keys(d.slots)) assert.ok(used.has(k), `${id} 的槽位 ${k} 沒被 template 用到`);
  }
});

test('answer_part 必須是 template 填出來的句子的後綴', () => {
  for (const [id, d] of Object.entries(drills)) {
    if (!d.answer_part) continue;
    for (const row of d.rows) {
      const full = fill(d.template, d.slots, row);
      const part = fill(d.answer_part, d.slots, row);
      assert.ok(full.endsWith(part), `${id} 的 answer_part 不是完整句的後綴：${part} / ${full}`);
      assert.ok(part.length < full.length, `${id} 的 answer_part 等於整句，等於沒有問句`);
    }
  }
});

test('每則都標了課次與出處', () => {
  for (const [id, d] of Object.entries(drills)) {
    assert.ok(d.lesson >= 1 && d.lesson <= 15, `${id} 的課次異常`);
    assert.match(d.source_ref, /^第\d+課 練習Ｂ-/, `${id} 的 source_ref 格式異常`);
  }
});

test('id 對得上課本的練習Ｂ（多組範例以 #n 後綴）', () => {
  const real = new Set();
  for (let n = 1; n <= 15; n++) {
    const d = JSON.parse(readFileSync(
      new URL(`../../data/lessons/${String(n).padStart(2, '0')}.json`, import.meta.url)));
    for (const dr of d.drills || []) real.add(dr.id);
  }
  for (const id of Object.keys(drills)) {
    assert.ok(real.has(id.split('#')[0]), `${id} 不存在於課本資料中`);
  }
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_drills_data.js`
Expected: FAIL，`Cannot find module` 或 `data/drills.json` 不存在

- [ ] **Step 3: 人工標註**

以 `python3 tools/draft/drills.py > /tmp/drills-draft.json` 的草稿為底，逐則標註 `template`／`slots`／`rows`／`answer_part`／`source_ref`，寫入 `data/drills.json`。

標註方法（以 `L07-B1` 為例）：

```
草稿：
  model_cue    = "ごはんを 食べます"
  model_answer = "はしで ごはんを 食べます。"
  items        = ["手紙を 書きます", "レポートを 送ります", "紙を 切ります", "ごはんを 食べます"]

觀察：model_answer 去掉 cue 之後剩「はしで 」與「。」，故 cue 是唯一的變動部分。
但課本此題是「用什麼工具做什麼」，工具欄在 items 裡沒有——items 只給動作。
此時 template 取「はしで {A}。」，slots.A 取 items，rows 為 [[3],[0],[1],[2]]
（第 0 列必須是 model_answer 對應的那一列，即 items 中的「ごはんを 食べます」）。

標註結果：
  "L07-B1": {
    "lesson": 7,
    "template": "はしで {A}。",
    "slots": { "A": ["ごはんを 食べます", "手紙を 書きます", "レポートを 送ります", "紙を 切ります"] },
    "rows": [[0], [1], [2], [3]],
    "answer_part": null,
    "model_answer": "はしで ごはんを 食べます。",
    "source_ref": "第7課 練習Ｂ-1"
  }
```

問答對（14 則）以 `answer_part` 標註，例 `L07-B5`：

```
  model_answer = "だれに 英語を 習いましたか。 ワットさんに 習いました。"

  "L07-B5": {
    "lesson": 7,
    "template": "だれに {A}か。 {B}に {C}。",
    "slots": { "A": ["英語を 習いました"], "B": ["ワットさん"], "C": ["習いました"] },
    "rows": [[0, 0, 0]],
    "answer_part": "{B}に {C}。",
    ...
  }
```

**標註守則**：
- `rows[0]` 一律對應 `model_answer`，其餘列依課本 `items` 的順序接在後面。
- 槽位切在「課本真的讓你換的地方」，不是切在任何可替換的字。切太細會產生課本沒教的組合（規格 §6.1 已為練習Ａ 記過同一個教訓：不做笛卡兒積）。
- 只有一列的則**仍要標**——`substitute.generate` 會自行略過（`rows.length < 2`），但標了才有往返驗證，日後補列時直接可用。
- 標到一半對不上就重跑測試，紅燈訊息會指出是哪一則哪一列。

每標完約 10 則就跑一次 `node --test tests/app/test_drills_data.js`，不要 77 則一次標完才驗。

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test tests/app/test_drills_data.js`
Expected: PASS（7 個測試）

- [ ] **Step 5: 提交**

```bash
git add data/drills.json tests/app/test_drills_data.js
git commit -m "feat(data): 練習Ｂ 標註為練習Ａ 的形狀，往返驗證把關"
```

---

### Task 12: `substitute` 接上練習Ｂ

不寫新引擎、不寫新解析器（規格 §13 決定 7）：練習Ｂ 標成練習Ａ 的形狀之後，直接餵進同一個生成器。只有兩處要加——`answer_part` 的問答對組法，與練習Ｂ 的出處字串。

**Files:**
- Modify: `app/generators/substitute.js`、`app/main.js`、`data/concepts.json`
- Test: `tests/app/test_substitute.js`、`tests/app/test_conceptdefs.js`

**Interfaces:**
- Consumes: `data/drills.json`（Task 11）、`conceptsByPattern`（既有）
- Produces: `generate(patterns, patternConcepts)` 額外接受帶 `answer_part` 的素材；`source_ref` 依 id 判斷是練習Ａ 或練習Ｂ

- [ ] **Step 1: 寫失敗的測試**

加到 `tests/app/test_substitute.js` 末尾：

```js
test('練習Ｂ：出處標成練習Ｂ', () => {
  const drill = {
    id: 'L07-B1', lesson: 7, requires_lesson: 7,
    template: 'はしで {A}。',
    slots: { A: ['ごはんを 食べます', '手紙を 書きます'] },
    rows: [[0], [1]],
  };
  const items = [...generate([drill], new Map())];
  assert.equal(items.length, 2);
  assert.equal(items[0].id, 'subst:L07-B1:0');
  assert.equal(items[0].answer, 'はしで ごはんを 食べます。');
  assert.equal(items[0].source_ref, '第7課 練習Ｂ-1');
});

test('練習Ｂ 問答對：題幹給問句，答案只要求答句', () => {
  const drill = {
    id: 'L07-B5', lesson: 7, requires_lesson: 7,
    template: 'だれに {A}か。 {B}に {C}。',
    slots: { A: ['英語を 習いました', '日本語を 習いました'], B: ['ワットさん', '先生'], C: ['習いました', '習いました'] },
    rows: [[0, 0, 0], [1, 1, 1]],
    answer_part: '{B}に {C}。',
  };
  const it = [...generate([drill], new Map())][0];
  assert.equal(it.answer, 'ワットさんに 習いました。');
  assert.ok(it.prompt.text.includes('だれに 英語を 習いましたか。'),
    '題幹必須包含問句');
  assert.ok(!it.prompt.text.includes('ワットさんに 習いました。'),
    '題幹不得洩漏答句');
});

test('多組範例的 #n 後綴不影響出處', () => {
  const drill = {
    id: 'L07-B7#2', lesson: 7, requires_lesson: 7,
    template: 'もう {A}か。 いいえ、まだです。',
    slots: { A: ['手紙を 書きました', '切符を 買いました'] },
    rows: [[0], [1]],
  };
  const it = [...generate([drill], new Map())][0];
  assert.equal(it.source_ref, '第7課 練習Ｂ-7');
});
```

加到 `tests/app/test_conceptdefs.js` 的「patterns 反查表的每個 pattern id 都真的存在」測試中，把練習Ｂ 也納入真實 id 集合：

```js
  const drills = JSON.parse(readFileSync(new URL('../../data/drills.json', import.meta.url)));
  for (const id of Object.keys(drills)) real.add(id);
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_substitute.js`
Expected: FAIL，`source_ref` 為 `第7課 練習Ａ-`（現行程式以 `-A` 切字串）

- [ ] **Step 3: 實作**

修改 `app/generators/substitute.js`：

新增出處組裝函式（取代 `p.id.split('-A')[1]` 那段）：

```js
/**
 * 出處字串。練習Ａ 是 `L07-A3`，練習Ｂ 是 `L07-B1`，多組範例會多一個 `#2`
 * 後綴——那是我們自己為了拆題加的，課本上沒有這個編號，不能印給使用者看。
 */
function sourceRefOf(p) {
  const m = /^L(\d+)-([AB])(\d+)/.exec(p.id);
  if (!m) return `第${p.lesson}課`;
  return `第${Number(m[1])}課 練習${m[2] === 'A' ? 'Ａ' : 'Ｂ'}-${m[3]}`;
}
```

在 `fillRow` 之後加入答句擷取：

```js
/**
 * 問答對（規格 §13 決定 7 第 4 點）：template 含問句與答句兩半，使用者只需
 * 產出答句。answer_part 是 template 的後綴子樣板，兩者填同一列，相減即得問句。
 *
 * 機制仍是 substitute，不新增引擎——與決定 3 同一原則。
 */
function splitAnswer(pattern, filled, values) {
  if (!pattern.answer_part) return { ask: null, answer: filled };
  const part = pattern.answer_part.replace(SLOT, (_, k) => values[k] ?? '');
  if (!filled.endsWith(part) || part.length >= filled.length) {
    return { ask: null, answer: filled }; // 標註有誤時退回整句，不產生半截題目
  }
  return { ask: filled.slice(0, filled.length - part.length).trim(), answer: part };
}
```

在 `yield` 的部分改為：

```js
      const { ask, answer } = splitAnswer(p, cur.filled, cur.values);
      const exampleText = `例：${example.filled}`;
      yield {
        id: `subst:${p.id}:${i}`,
        engine: ENGINE,
        lesson: p.lesson,
        requires_lesson: p.requires_lesson ?? p.lesson,
        covers,
        skills,
        prompt: {
          type: 'text',
          text: ask
            ? `${exampleText}\n${ask}\n用這些詞回答：${cur.cues.join(' ／ ')}`
            : `${exampleText}\n用這些詞造句：${cur.cues.join(' ／ ')}`,
          hint: ask ? '回答上面的問題' : '照範例的句型造句',
        },
        answer,
        alternatives: [],
        source_ref: sourceRefOf(p),
      };
```

修改 `app/main.js`：載入 `data/drills.json` 並與 patterns 一起餵給 substitute。

```js
      fetchJson('data/drills.json'),
```

```js
    if (settings.engines.includes('substitute')) {
      const byPattern = conceptsByPattern(conceptDefs);
      allItems.push(...substitute.generate(idx.patterns, byPattern));
      // 練習Ｂ 是人工標註的獨立檔，形狀與練習Ａ 相同，故走同一個生成器
      // （規格 §13 決定 7）。
      const drillPatterns = Object.entries(drillsJson).map(([id, d]) => ({ ...d, id }));
      allItems.push(...substitute.generate(drillPatterns, byPattern));
    }
```

修改 `data/concepts.json`：把練習Ｂ 的 id 加進對應概念的 `patterns` 陣列。對不上概念的則會退回 `g:<id>`（既有行為），但那樣儀表板會出現一堆看不懂的概念名，因此**每一則都要歸屬**。判斷依據是該則練的句型，與同課練習Ａ 的歸屬對照即可。

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test "tests/app/*.js"`
Expected: 全部 PASS

驗證題量：

Run: `node -e "import('./app/generators/substitute.js').then(async (s)=>{const fs=await import('node:fs');const d=JSON.parse(fs.readFileSync('data/drills.json'));const ps=Object.entries(d).map(([id,x])=>({...x,id}));console.log('練習Ｂ 題數：',[...s.generate(ps,new Map())].length)})"`
Expected: 200 ~ 300 題（規格 §13 決定 7 的預估）

- [ ] **Step 5: 提交**

```bash
git add app/generators/substitute.js app/main.js data/concepts.json tests/app/test_substitute.js tests/app/test_conceptdefs.js
git commit -m "feat(generators): 練習Ｂ 接上代入題，問答對只要求答句"
```

---

### Task 13: `core/tts.js` 與聽力開關

規格 §6.2：聽力是呈現修飾，不是第五種引擎。規格 §13 決定 10：只做開／關。

**Files:**
- Create: `app/core/tts.js`
- Modify: `app/ui/settings.js`、`app/main.js`
- Test: `tests/app/test_tts.js`

**Interfaces:**
- Produces: `makeSpeaker(synth, UtteranceCtor)` → `{ available(): boolean, speak(text, opts): void, cancel(): void }`
  - `synth` 為 `speechSynthesis`（**注入**，因為 `core/` 不得碰 `window`）
  - `opts`：`{ lang = 'ja-JP', rate = 0.9 }`
  - `available()` 為假時 `speak()` 為 no-op——沒有日文語音的裝置不該卡住整輪練習
- `DEFAULT_SETTINGS` 增加 `listening: false`

- [ ] **Step 1: 寫失敗的測試**

建立 `tests/app/test_tts.js`：

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { makeSpeaker } from '../../app/core/tts.js';

function fakeSynth(voices = [{ lang: 'ja-JP', name: 'Kyoko' }]) {
  return {
    spoken: [], cancelled: 0,
    getVoices: () => voices,
    speak(u) { this.spoken.push(u); },
    cancel() { this.cancelled += 1; },
  };
}
class FakeUtterance {
  constructor(text) { this.text = text; }
}

test('speak 送出日文語音設定', () => {
  const synth = fakeSynth();
  const sp = makeSpeaker(synth, FakeUtterance);
  sp.speak('手紙を 書きます。');
  assert.equal(synth.spoken.length, 1);
  assert.equal(synth.spoken[0].text, '手紙を 書きます。');
  assert.equal(synth.spoken[0].lang, 'ja-JP');
  assert.equal(synth.spoken[0].rate, 0.9);
});

test('speak 前先 cancel，避免上一題的語音疊上來', () => {
  const synth = fakeSynth();
  const sp = makeSpeaker(synth, FakeUtterance);
  sp.speak('あ');
  sp.speak('い');
  assert.equal(synth.cancelled, 2);
});

test('沒有語音合成時 available 為假且 speak 不炸', () => {
  const sp = makeSpeaker(null, FakeUtterance);
  assert.equal(sp.available(), false);
  assert.doesNotThrow(() => sp.speak('あ'));
});

test('沒有日文語音時 available 為假（不以英文語音唸日文）', () => {
  const sp = makeSpeaker(fakeSynth([{ lang: 'en-US', name: 'Alex' }]), FakeUtterance);
  assert.equal(sp.available(), false);
});

test('getVoices 尚未就緒（回空陣列）時仍視為可用', () => {
  // Chrome 首次呼叫 getVoices 常回空陣列，稍後才非同步填入。
  // 此時判為不可用會讓聽力功能在剛開頁時無故消失。
  const sp = makeSpeaker(fakeSynth([]), FakeUtterance);
  assert.equal(sp.available(), true);
});

test('空字串不送出語音', () => {
  const synth = fakeSynth();
  makeSpeaker(synth, FakeUtterance).speak('');
  assert.equal(synth.spoken.length, 0);
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_tts.js`
Expected: FAIL，`Cannot find module '../../app/core/tts.js'`

- [ ] **Step 3: 實作**

建立 `app/core/tts.js`：

```js
/**
 * Web Speech API 的封裝（規格 §6.2：聽力是呈現修飾，不是第五種引擎）。
 *
 * 合成器以參數注入而非直接抓 window.speechSynthesis——core/ 不得出現
 * window／document（規格 §11 的分層要求，Phase 1 已以 grep 驗收）。
 * 注入同時讓這個模組測得到：真的 speechSynthesis 在 Node 裡不存在。
 *
 * 已知限制（規格 §14）：iOS Safari 在鎖屏或切到背景時會暫停 speechSynthesis，
 * 因此循環播放須保持螢幕開啟。UI 明示，不在此處緩解。
 */
export function makeSpeaker(synth, UtteranceCtor) {
  function available() {
    if (!synth || typeof synth.speak !== 'function' || typeof UtteranceCtor !== 'function') {
      return false;
    }
    const voices = typeof synth.getVoices === 'function' ? synth.getVoices() : [];
    // Chrome 首次呼叫 getVoices 常回空陣列，語音清單稍後才非同步填入。
    // 空陣列判為不可用，會讓聽力功能在剛開頁的那幾百毫秒無故消失。
    if (!voices.length) return true;
    return voices.some((v) => (v.lang || '').toLowerCase().startsWith('ja'));
  }

  return {
    available,
    speak(text, { lang = 'ja-JP', rate = 0.9 } = {}) {
      if (!available() || !text) return;
      // 先取消：上一題的語音若還沒唸完，兩段會疊在一起，兩題都聽不清楚。
      synth.cancel();
      const u = new UtteranceCtor(text);
      u.lang = lang;
      u.rate = rate;
      synth.speak(u);
    },
    cancel() {
      if (synth && typeof synth.cancel === 'function') synth.cancel();
    },
  };
}
```

修改 `app/ui/settings.js`：`DEFAULT_SETTINGS` 加入 `listening: false`，並在題型區塊後加入開關：

```js
      <div class="group-title">呈現</div>
      <label><input id="listening" type="checkbox" ${settings.listening ? 'checked' : ''}>
        聽力模式（題幹改為語音播放）</label>
```

以及在 `onChange` 的物件中加入 `listening: host.querySelector('#listening').checked,`。

修改 `app/main.js`：建立 speaker 並接進 `presentOpts`，聽力模式下同時提供重播按鈕。

```js
import { makeSpeaker } from './core/tts.js';

  const speaker = makeSpeaker(win.speechSynthesis, win.SpeechSynthesisUtterance);
```

`presentOpts` 改為：

```js
      presentOpts: (it) => ({
        ...presentOptsFor(it, { lex, sentenceMarks }),
        // 語音不可用時自動退回文字，不讓沒有日文語音的裝置卡在空白題幹。
        listening: settings.listening && speaker.available(),
        speak: (text) => speaker.speak(text),
      }),
```

修改 `app/engines/text.js` 的 `render`：聽力模式時附一顆重播鍵。

```js
  if (opts.listening) {
    host.insertAdjacentHTML('afterbegin', '<button id="replay">🔊 再聽一次</button>');
    host.querySelector('#replay').onclick = () => opts.speak?.(item.prompt.text);
    opts.speak?.(item.prompt.text);
  }
```
（並移除 `render` 結尾原本那行 `if (opts.listening) opts.speak?.(...)`，避免重複播放）

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test "tests/app/*.js"`
Expected: 全部 PASS

Run: `grep -rn "window\.\|document\." app/core/ app/lang/`
Expected: 無輸出（分層未被破壞）

- [ ] **Step 5: 提交**

```bash
git add app/core/tts.js tests/app/test_tts.js app/ui/settings.js app/main.js app/engines/text.js
git commit -m "feat(core): 聽力呈現，語音不可用時自動退回文字"
```

---

### Task 14: `ui/player.js` 單字循環播放

規格 §6.3：播放器不是題目。**不產生複習事件**——純聆聽沒有作答，計入會虛報熟悉度，反而讓排程器少考真正該考的字。選詞權重重用 `scheduler.priority()`，不另寫一套。

**Files:**
- Create: `app/ui/player.js`
- Modify: `app/main.js`、`index.html`
- Test: `tests/app/test_player.js`

**Interfaces:**
- Consumes: `priority(item, itemStates, conceptStates, nowSec)`（既有）
- Produces:
  - `pickForPlayback(items, itemStates, conceptStates, nowSec, alpha, rng)` → 單一 item（純函式，可測）
  - `renderPlayer(host, { items, itemStates, conceptStates, speaker, settings })` → `{ stop() }`

- [ ] **Step 1: 寫失敗的測試**

建立 `tests/app/test_player.js`：

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { pickForPlayback } from '../../app/ui/player.js';

const items = [
  { id: 'a', covers: ['w:A'], answer: 'あ', prompt: { text: '甲' } },
  { id: 'b', covers: ['w:B'], answer: 'い', prompt: { text: '乙' } },
];
// A 全錯（不熟）、B 全對（熟）
const conceptStates = new Map([
  ['w:A', { recent: [1, 1, 1] }],
  ['w:B', { recent: [3, 3, 3] }],
]);

test('不熟的字被抽中的機率明顯較高（規格 §6.3 加權隨機）', () => {
  let a = 0;
  for (let i = 0; i < 1000; i++) {
    const seq = [i / 1000];
    let k = 0;
    const rng = () => seq[k++] ?? 0.5;
    if (pickForPlayback(items, new Map(), conceptStates, 0, 1, rng).id === 'a') a += 1;
  }
  assert.ok(a > 550, `不熟的字只被抽中 ${a}/1000 次，加權沒有作用`);
});

test('alpha 為 0 時退化為平均分布', () => {
  let a = 0;
  for (let i = 0; i < 1000; i++) {
    const seq = [i / 1000];
    let k = 0;
    const rng = () => seq[k++] ?? 0.5;
    if (pickForPlayback(items, new Map(), conceptStates, 0, 0, rng).id === 'a') a += 1;
  }
  assert.ok(a > 400 && a < 600, `平均分布下應約各半，實得 ${a}/1000`);
});

test('題庫為空時回傳 null 而非拋錯', () => {
  assert.equal(pickForPlayback([], new Map(), new Map(), 0, 1, () => 0.5), null);
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_player.js`
Expected: FAIL，`Cannot find module '../../app/ui/player.js'`

- [ ] **Step 3: 實作**

建立 `app/ui/player.js`：

```js
/**
 * 單字循環播放（需求 #15、規格 §6.3）。這是播放器，不是題目。
 *
 * **不產生任何複習事件。** 純聆聽沒有作答，無法評估掌握度；若計入會虛報
 * 熟悉度，反而讓排程器少考真正該考的字。播放器只讀取 SRS 狀態。
 *
 * 權重直接重用 scheduler 的 priority()，不另寫一套——播放器與排程器對
 * 「哪些字該多練」的判斷若不一致，使用者會看到儀表板說不熟、播放器卻很少唸。
 */
import { priority } from '../core/scheduler.js';
import { escapeHtml } from './html.js';

/**
 * alpha 是「偏重生詞」的強度：0 為平均分布，愈大愈集中在不熟的字。
 * 權重取 priority()^alpha，alpha=0 時所有權重同為 1。
 */
export function pickForPlayback(items, itemStates, conceptStates, nowSec, alpha, rng = Math.random) {
  if (!items.length) return null;
  const weights = items.map((it) => {
    const w = priority(it, itemStates, conceptStates, nowSec);
    return Math.max(1e-6, Math.pow(Math.max(0, w), alpha));
  });
  const total = weights.reduce((a, b) => a + b, 0);
  let target = rng() * total;
  for (let i = 0; i < items.length; i++) {
    target -= weights[i];
    if (target <= 0) return items[i];
  }
  return items[items.length - 1];
}

const ALPHA_LABELS = { 0: '平均', 1: '偏重生詞', 2: '大幅偏重生詞' };

export function renderPlayer(host, deps) {
  const { items, itemStates, conceptStates, speaker } = deps;
  let timer = null;
  let running = false;

  host.innerHTML = `
    <h2>單字循環播放</h2>
    <label>偏重程度
      <select id="alpha">${Object.entries(ALPHA_LABELS).map(([v, l]) =>
        `<option value="${v}"${v === '1' ? ' selected' : ''}>${l}</option>`).join('')}</select>
    </label>
    <label>間隔秒數 <input id="gap" type="number" min="1" max="20" value="3"></label>
    <button id="play">開始播放</button>
    <div class="now"></div>
    <p class="note">iOS 鎖屏或切到背景會被系統暫停語音，播放期間請保持螢幕開啟。</p>`;

  const nowEl = host.querySelector('.now');
  const playBtn = host.querySelector('#play');

  function step() {
    const alpha = Number(host.querySelector('#alpha').value);
    const gap = Math.max(1, Number(host.querySelector('#gap').value) || 3) * 1000;
    const it = pickForPlayback(items, itemStates, conceptStates, Math.floor(Date.now() / 1000), alpha);
    if (!it) { stop(); return; }
    // 日→停頓→中（規格 §6.3）。中文不唸，只顯示——日文語音唸中文會亂唸。
    speaker.speak(it.answer);
    nowEl.innerHTML = `<div class="jp">${escapeHtml(it.answer)}</div>
      <div class="zh">${escapeHtml(it.prompt.text)}</div>`;
    timer = setTimeout(step, gap);
  }

  function stop() {
    running = false;
    if (timer) clearTimeout(timer);
    timer = null;
    speaker.cancel();
    playBtn.textContent = '開始播放';
  }

  playBtn.onclick = () => {
    if (running) return stop();
    running = true;
    playBtn.textContent = '停止';
    step();
  };

  return { stop };
}
```

修改 `index.html`：在 `#dashboard` 之前加入 `<section id="player" aria-label="播放器"></section>`，並加樣式：

```css
  .now .jp { font-size: 1.6rem; margin: 10px 0 4px; }
  .now .zh { color: #666; margin-bottom: 8px; }
  .note { color: #999; font-size: .8rem; }
```

修改 `app/main.js`：在 `runSession` 內、`sessionItems` 取得之後，渲染播放器。播放器只用**單字題**當素材（`engine === 'recall'` 且 id 以 `:zh2jp` 結尾，答案為日文假名）：

```js
    const playerHost = doc.querySelector('#player');
    const wordItems = items.filter((it) => it.id.endsWith(':zh2jp'));
    renderPlayer(playerHost, { items: wordItems, itemStates, conceptStates, speaker });
```

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test "tests/app/*.js"`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add app/ui/player.js tests/app/test_player.js app/main.js index.html
git commit -m "feat(ui): 單字循環播放，依熟悉度加權且不寫入事件"
```

---

### Task 15: PWA — 離線可用

規格 §13 Phase 2 驗收：「離線可完成一次完整練習」。快取 app 與資料共約 820KB；插畫 3.6MB 不進快取（2b 用不到）。

**Files:**
- Create: `manifest.json`、`sw.js`、`tools/make_icons.swift`、`icon-192.png`、`icon-512.png`
- Modify: `index.html`、`app/main.js`
- Test: `tests/app/test_sw.js`

**Interfaces:**
- Produces: `sw.js` 內的 `PRECACHE` 陣列（相對路徑），涵蓋 `index.html`、`app/**/*.js`、`data/lessons/*.json`、`data/*.json`、`manifest.json` 與圖示

- [ ] **Step 1: 寫失敗的測試**

建立 `tests/app/test_sw.js`：

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync, readdirSync, existsSync } from 'node:fs';

const root = new URL('../../', import.meta.url);
const sw = readFileSync(new URL('sw.js', root), 'utf8');

function precacheList() {
  const m = /const PRECACHE = (\[[\s\S]*?\]);/.exec(sw);
  assert.ok(m, 'sw.js 找不到 PRECACHE 陣列');
  return JSON.parse(m[1].replace(/'/g, '"').replace(/,(\s*\])/, '$1'));
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

test('15 課資料與四份人工資料都在預快取清單中', () => {
  const listed = new Set(precacheList());
  for (let n = 1; n <= 15; n++) {
    assert.ok(listed.has(`data/lessons/${String(n).padStart(2, '0')}.json`), `第 ${n} 課未列入`);
  }
  for (const f of ['verbs.json', 'adjectives.json', 'concepts.json', 'particles.json',
    'drills.json', 'ruby-lexicon.json']) {
    assert.ok(listed.has(`data/${f}`), `data/${f} 未列入`);
  }
});

test('預快取清單中的每個檔案都真的存在（打錯字會讓整個 install 失敗）', () => {
  for (const p of precacheList()) {
    assert.ok(existsSync(new URL(p, root)), `預快取清單中的 ${p} 不存在`);
  }
});

test('插畫不進預快取（3.6MB，2b 用不到）', () => {
  assert.ok(!precacheList().some((p) => p.startsWith('data/images/')), '插畫不該進快取');
});

test('cache 名稱帶版本，改版才換得掉舊快取', () => {
  assert.match(sw, /const CACHE = '[^']*v\d+'/, 'sw.js 的 CACHE 常數必須帶版本號');
});

test('sw.js 不得使用 import（Service Worker 以 classic script 註冊）', () => {
  assert.ok(!/^\s*import\s/m.test(sw), 'sw.js 不得使用 ES import');
});

test('manifest 欄位齊備', () => {
  const m = JSON.parse(readFileSync(new URL('manifest.json', root), 'utf8'));
  assert.equal(typeof m.name, 'string');
  assert.equal(typeof m.short_name, 'string');
  assert.equal(m.display, 'standalone');
  assert.equal(m.start_url, '.');
  assert.ok(m.icons.length >= 2);
  for (const i of m.icons) assert.ok(existsSync(new URL(i.src, root)), `圖示 ${i.src} 不存在`);
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_sw.js`
Expected: FAIL，`ENOENT ... sw.js`

- [ ] **Step 3: 實作**

建立 `tools/make_icons.swift`（離線執行一次，產出的 PNG 納入版控）：

```swift
// PWA 圖示產生器。執行一次即可，產出的 PNG 納入版控。
// 用法：swift tools/make_icons.swift
import AppKit

for size in [192, 512] {
    let s = CGFloat(size)
    let img = NSImage(size: NSSize(width: s, height: s))
    img.lockFocus()
    NSColor(red: 0.176, green: 0.424, blue: 0.875, alpha: 1).setFill()
    NSRect(x: 0, y: 0, width: s, height: s).fill()
    let attrs: [NSAttributedString.Key: Any] = [
        .font: NSFont.systemFont(ofSize: s * 0.6, weight: .bold),
        .foregroundColor: NSColor.white,
    ]
    let text = "日" as NSString
    let bounds = text.size(withAttributes: attrs)
    text.draw(at: NSPoint(x: (s - bounds.width) / 2, y: (s - bounds.height) / 2),
              withAttributes: attrs)
    img.unlockFocus()
    guard let tiff = img.tiffRepresentation, let rep = NSBitmapImageRep(data: tiff),
          let png = rep.representation(using: .png, properties: [:]) else { continue }
    try? png.write(to: URL(fileURLWithPath: "icon-\(size).png"))
    print("icon-\(size).png")
}
```

Run: `swift tools/make_icons.swift`

建立 `manifest.json`：

```json
{
  "name": "日語練習",
  "short_name": "日語",
  "start_url": ".",
  "display": "standalone",
  "background_color": "#f7f7f5",
  "theme_color": "#2d6cdf",
  "lang": "zh-Hant",
  "icons": [
    { "src": "icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

建立 `sw.js`（**不得使用 import**——Service Worker 以 classic script 註冊）：

```js
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
  'app/main.js',
  'app/core/concepts.js',
  'app/core/conceptdefs.js',
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
  'app/ui/dashboard.js',
  'app/ui/html.js',
  'app/ui/player.js',
  'app/ui/present.js',
  'app/ui/session.js',
  'app/ui/settings.js',
  'data/adjectives.json',
  'data/concepts.json',
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
```

修改 `index.html`：`<head>` 內加入

```html
<link rel="manifest" href="manifest.json">
<meta name="theme-color" content="#2d6cdf">
<link rel="apple-touch-icon" href="icon-192.png">
```

修改 `app/main.js`：`boot()` 末尾加入註冊（**不擋啟動**——註冊失敗只是沒有離線能力，不該讓整個 app 起不來）：

```js
  // PWA：註冊失敗只代表沒有離線能力，不該讓整個 app 起不來，故不 await、不拋錯。
  if (win.navigator && 'serviceWorker' in win.navigator) {
    win.navigator.serviceWorker.register('sw.js').catch((err) => {
      console.warn('Service Worker 註冊失敗，離線功能不可用：', err && err.message);
    });
  }
```

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test "tests/app/*.js"`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add manifest.json sw.js tools/make_icons.swift icon-192.png icon-512.png index.html app/main.js tests/app/test_sw.js
git commit -m "feat(pwa): Service Worker 離線快取與主畫面安裝"
```

---

### Task 16: 驗收

規格 §13 Phase 2 整體驗收：需求 #1 ~ #18 全數可用；離線可完成一次完整練習。

**Files:**
- Create: `docs/superpowers/plans/2026-09-30-phase2b-acceptance-report.md`

- [ ] **Step 1: 跑全部測試**

Run: `node --test "tests/app/*.js" && python3 -m unittest discover -s tests -t .`
Expected: 兩者皆綠，記下題數

- [ ] **Step 2: 驗證分層未被破壞**

Run: `grep -rn "window\.\|document\." app/core/ app/lang/ || echo "分層正確"`
Expected: `分層正確`

Run: `grep -rn "isCorrect\|normalizeAnswer" app/engines/ app/ui/ || echo "判斷邏輯未外洩"`
Expected: `判斷邏輯未外洩`

- [ ] **Step 3: 統計題量**

Run:
```bash
python3 - <<'EOF'
import json, subprocess
d = json.load(open('data/drills.json'))
print('練習Ｂ 標註則數：', len(d))
print('問答對：', sum(1 for x in d.values() if x.get('answer_part')))
lex = json.load(open('data/ruby-lexicon.json'))
print('振假名詞典：auto', len(lex['auto']), '/ manual', len(lex['manual']))
EOF
```
Expected: 練習Ｂ ≥ 70 則、詞典 auto 約 380 條

- [ ] **Step 4: 真實瀏覽器驗證**

啟動 `python3 -m http.server 8000`，以瀏覽器逐項確認並截圖：

1. 題幹的漢字上方出現假名；「漢字→假名」題的題幹**沒有**假名（檢視原始碼確認 `<rt>` 不存在，不只是看不到）
2. 日→中選擇題可點選作答，選錯不出現「我這樣寫也對」
3. 練習Ｂ 的題目出現，出處顯示「第N課 練習Ｂ-n」；問答對題幹有問句、答案只要求答句
4. 打開聽力模式後題幹改為語音，「再聽一次」可重播
5. 單字循環播放可啟動與停止，唸的是日文
6. DevTools → Application → Service Worker 顯示已啟用；切斷網路後重新整理仍可完成一輪練習
7. 手機加入主畫面後可離線開啟

- [ ] **Step 5: 寫驗收報告並提交**

建立 `docs/superpowers/plans/2026-09-30-phase2b-acceptance-report.md`，記錄：各項驗收結果、實際題量與覆蓋率數字、與計畫的偏差及其理由、留給 Phase 2c／4 的項目（29 則插畫型練習Ｂ、7 個多讀音字的振假名）。

```bash
git add docs/superpowers/plans/2026-09-30-phase2b-acceptance-report.md
git commit -m "docs: Phase 2b 驗收報告"
```

---

## Self-Review

**規格覆蓋**：Phase 2b 的六個項目對應 Task 1~7（振假名）、13（聽力）、14（播放器）、8~9（jp2zh 選擇題）、10~12（練習Ｂ）、6（engines 分層）、15（PWA）。決定 8（插畫型排除）落在 Task 10 的腳本過濾；決定 9（詞典策略）落在 Task 3~4；決定 10（聽力開／關）落在 Task 13。

**型別一致性**：`Token` 形狀（Task 1）在 Task 2、5、7 沿用；`render(item, host, opts) → { readValue() }` 在 Task 6、9、13 一致；`fill(template, slots, row)` 的語義在 Task 11（測試）與 Task 12（實作 `fillRow`）一致——實作端沿用既有 `substitute.js` 的 `fillRow`，測試端自帶一份等價實作，這是刻意的：測試若 import 受測程式來驗證資料，資料與程式一起錯時會一起通過。

**已知缺口**：`ui/player.js` 與 `engines/*.js` 的 DOM 行為只以純函式部分覆蓋（`pickForPlayback`、`engineFor`、`promptHtml`），互動本身由 Task 16 的瀏覽器驗證把關，與 Phase 1 對 `session.js` 的做法一致。
