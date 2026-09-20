# Phase 1：核心引擎與最小可用版本 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 做出第一個能在手機與電腦瀏覽器上實際練習的版本——含單字對照題與動詞變化題、FSRS-lite 熟悉度、概念層排程、六類技能儀表板、IndexedDB 進度保存。

**Architecture:** 純前端、無 build step。資料是 Phase 0 產出的 `data/lessons/*.json`（唯讀）。核心邏輯全部寫成不碰 DOM 的純函式，放在 `app/core/` 與 `app/lang/`，以 Node 內建 `node --test` 測試；UI 層薄到不需要測試框架。儲存的是**複習事件日誌**而非分數快照，熟悉度由日誌重放算出。

**Tech Stack:** Vanilla JavaScript（ES modules，無框架、無打包工具）、IndexedDB、Node v24 內建 `node --test`。

**Spec:** `docs/superpowers/specs/2026-09-10-japanese-practice-design.md`

## Global Constraints

- **無 build step、無 npm 相依。** 不得 `npm install`、不得引入任何第三方函式庫。瀏覽器直接以 `<script type="module">` 載入原始碼。
- **測試用 Node 內建 `node --test`**（Node v24.20.0 已安裝）。從專案根目錄執行：`node --test "tests/app/*.js"`（**必須加引號**——Node 的 `--test` 不接受目錄路徑，且我們的檔名 `test_*.js` 不符合它預設的測試檔樣式）
- **`app/core/` 與 `app/lang/` 下的程式碼不得碰 DOM**（不得出現 `document`、`window`、`localStorage`、`indexedDB` 的直接呼叫）。那些只能出現在 `app/ui/` 與 `app/core/store.js` 的 IndexedDB 實作區段。
- **`data/lessons/*.json` 與 `data/images/` 為唯讀**，Phase 1 不得修改。修改它們等於改動 Phase 0 的驗收產物。
- **item id 必須決定性**：同樣的資料重新生成必須得到同樣的 id。規格 §5.3：「否則 SRS 歷史全部失效」。id 不得含亂數、時間戳、或陣列位置。
- **事件日誌不可變**：已寫入的事件不得修改或刪除，只能追加。合併多裝置資料時取聯集。
- **提交訊息結尾**必須逐字附上：
  ```
  Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01QazTpwM3ApzPa47zWjy26D
  ```

## Phase 0 產出的實際資料 schema（唯讀，全部經過驗收）

```jsonc
// data/lessons/07.json
{
  "lesson": 7,
  "vocab": [                                  // 全 15 課共 749 筆
    {"no": 1, "kana": "きります", "kanji": "切ります", "zh": "剪，切",
     "usage": null, "group": null, "category": "numbered"},
    {"no": 9, "kana": "かけます", "kanji": null, "zh": "打〔電話〕",
     "usage": {"kana": "でんわを～", "kanji": "電話を～"}, "group": null, "category": "numbered"}
    // category ∈ "numbered"(628) | "supplementary"(56) | "conversation"(65)
    // group    ∈ "I" | "II" | "III" | null   ——僅第 14、15 課標註，共 29 筆
  ],
  "sentences": [                              // 全 15 課共 430 句
    {"id": "L07-文型-1", "section": "文型", "no": 1,
     "jp": "わたしは  ワープロで  手紙を  書きます。",
     "ruby": [{"base": "手紙", "kana": "てがみ", "at": 13}],
     "zh": null, "alt": []}
    // section ∈ "文型"(48) | "例文"(99) | "会話"(207) | "問題"(76)
    // ruby[].at 是 base 在 jp 中的字元起始位置，保證 jp[at:at+len(base)] === base
  ],
  "patterns": [                               // 全 15 課共 78 張
    {"id": "L07-A1", "template": "{S}は{T}で ごはんを 食べます。",
     "slots": {"S": ["日本人","インドネシア人","アメリカ人"],
               "T": ["はし","スプーンと フォーク","ナイフと フォーク"]},
     "rows": [[0,0],[1,1],[2,2]], "requires_lesson": 7,
     "table_type": "substitution",            // "substitution"(71) | "conjugation"(7)
     "question_variant": "日本人はなんで ごはんを 食べますか。"}
  ],
  "drills": [                                 // 全 15 課共 107 題
    {"id": "L07-B1", "model_cue": "ごはんを 食べます",
     "model_answer": "はしで ごはんを 食べます。",
     "items": ["手紙を 書きます", "レポートを 送ります"]}
  ],
  "grammar": [                                // 全 15 課共 91 則、例句 213 句
    {"no": 1, "title": "名詞（工具／手段）で  動詞",
     "body_zh": "助詞「で」表示手段、方法。",
     "examples": [{"jp": "はしで  食べます。", "zh": "用筷子吃。"}]}
  ],
  "images": [                                 // 全 15 課共 739 張
    {"file": "data/images/07-p02-01.png", "page": 2, "x": 79.2, "y": 560.0004, "w": 80.0, "h": 1.8}
  ]
}
```

**Phase 1 只用到 `vocab` 與 `sentences`**（recall 與 transform 兩個引擎的素材）。`patterns`／`drills`／`grammar`／`images` 留給 Phase 2。

---

## File Structure

```
index.html                     單一頁面入口
app/
  main.js                      啟動、路由、把各模組接起來
  core/
    data.js       載入 lessons JSON 並建索引（注入式 loader，可在 Node 測試）
    concepts.js   概念 id 生成、概念索引、六類技能聚合
    srs.js        FSRS-lite 純函式（R(t)、S/D 更新、事件重放）
    store.js      Store 介面 + LocalStore（IndexedDB）+ 匯出／匯入
    scheduler.js  依概念熟悉度加權抽樣選題
    normalize.js  日文答案正規化比對
  lang/
    kana.js       假名正規化、平片假名互轉
    conjugation.js 動詞變化（ます形 ↔ て形、時態四變化）
  generators/
    recall.js     對照題生成（中→日、日→中、漢字→假名）
    transform.js  變換題生成（動詞變化）
  ui/
    session.js    練習畫面
    settings.js   範圍與題型設定
    dashboard.js  六類技能熟悉度儀表板
data/
  verbs.json      動詞分類表（Task 3 建立，人工校對）
tests/app/
  test_kana.js  test_conjugation.js  test_normalize.js  test_srs.js
  test_concepts.js  test_recall.js  test_transform.js  test_scheduler.js
  test_data.js
```

**依賴方向單向**：`data → concepts → {srs, scheduler}`；`lang/kana → lang/conjugation`；`generators` 依賴 `data`+`lang`+`concepts`；`ui` 依賴全部；`core/*` 之間只有 `scheduler → {srs, concepts}`。**不得產生循環匯入。**

---

## Task 1: 專案骨架與資料載入

**Files:**
- Create: `app/core/data.js`, `tests/app/test_data.js`

**Interfaces:**
- Consumes: 無
- Produces:
  ```js
  // 載入器注入式：瀏覽器傳 fetch-based，Node 測試傳 fs-based
  export async function loadLessons(lessonNumbers, loader) // → Map<number, LessonData>
  export function buildIndex(lessonsMap)                   // → { vocab: [...], sentences: [...] }
  // buildIndex 回傳的每筆 vocab 多帶 lesson 欄位：{...原欄位, lesson: 7}
  // sentences 同樣多帶 lesson 欄位
  ```

- [ ] **Step 1: 寫失敗的測試**

`tests/app/test_data.js`：

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { loadLessons, buildIndex } from '../../app/core/data.js';

const fsLoader = async (n) =>
  JSON.parse(await readFile(`data/lessons/${String(n).padStart(2, '0')}.json`, 'utf8'));

test('loadLessons 載入指定課次', async () => {
  const m = await loadLessons([7], fsLoader);
  assert.equal(m.size, 1);
  assert.equal(m.get(7).lesson, 7);
  assert.equal(m.get(7).vocab.length, 48);
});

test('buildIndex 攤平並標註課次', async () => {
  const m = await loadLessons([7, 14], fsLoader);
  const idx = buildIndex(m);
  const kiri = idx.vocab.find((v) => v.kana === 'きります');
  assert.equal(kiri.lesson, 7);
  assert.equal(kiri.kanji, '切ります');
  const tsuke = idx.vocab.find((v) => v.kana === 'つけます');
  assert.equal(tsuke.lesson, 14);
  assert.equal(tsuke.group, 'II');
});

test('buildIndex 涵蓋全 15 課的實際總數', async () => {
  const all = await loadLessons([...Array(15)].map((_, i) => i + 1), fsLoader);
  const idx = buildIndex(all);
  assert.equal(idx.vocab.length, 749);
  assert.equal(idx.sentences.length, 430);
});
```

- [ ] **Step 2: 執行確認失敗**

Run: `node --test tests/app/test_data.js`
Expected: FAIL — `Cannot find module '.../app/core/data.js'`

- [ ] **Step 3: 實作 `app/core/data.js`**

```js
/**
 * 載入 Phase 0 產出的課次 JSON 並建立索引。
 * loader 以注入方式提供，讓瀏覽器（fetch）與 Node 測試（fs）共用同一份邏輯。
 */
export async function loadLessons(lessonNumbers, loader) {
  const out = new Map();
  for (const n of lessonNumbers) {
    out.set(n, await loader(n));
  }
  return out;
}

export function buildIndex(lessonsMap) {
  const vocab = [];
  const sentences = [];
  for (const [n, data] of [...lessonsMap.entries()].sort((a, b) => a[0] - b[0])) {
    for (const v of data.vocab || []) vocab.push({ ...v, lesson: n });
    for (const s of data.sentences || []) sentences.push({ ...s, lesson: n });
  }
  return { vocab, sentences };
}
```

- [ ] **Step 4: 執行確認通過**

Run: `node --test tests/app/test_data.js`
Expected: 3 tests PASS

- [ ] **Step 5: 提交**

```bash
git add app/core/data.js tests/app/test_data.js
git commit -m "$(cat <<'EOF'
feat(app): 課次資料載入與索引

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QazTpwM3ApzPa47zWjy26D
EOF
)"
```

---

## Task 2: 假名正規化（`lang/kana.js`）

**Files:**
- Create: `app/lang/kana.js`, `tests/app/test_kana.js`

**Interfaces:**
- Consumes: 無
- Produces:
  ```js
  export function toHiragana(s)   // 片假名 → 平假名，其餘原樣
  export function toKatakana(s)   // 平假名 → 片假名，其餘原樣
  export function isKana(ch)      // 單一字元是否為平或片假名
  export function stripSpaces(s)  // 移除所有空白（半形、全形、tab）
  ```

- [ ] **Step 1: 寫失敗的測試**

`tests/app/test_kana.js`：

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { toHiragana, toKatakana, isKana, stripSpaces } from '../../app/lang/kana.js';

test('片假名轉平假名', () => {
  assert.equal(toHiragana('コーヒー'), 'こーひー');
  assert.equal(toHiragana('きります'), 'きります');
  assert.equal(toHiragana('切ります'), '切ります');   // 漢字不動
});

test('平假名轉片假名', () => {
  assert.equal(toKatakana('きります'), 'キリマス');
  assert.equal(toKatakana('コーヒー'), 'コーヒー');   // 已是片假名，不動
});

test('isKana 判定', () => {
  assert.equal(isKana('あ'), true);
  assert.equal(isKana('ア'), true);
  assert.equal(isKana('切'), false);
  assert.equal(isKana('A'), false);
});

test('stripSpaces 移除半形與全形空白', () => {
  assert.equal(stripSpaces('わたしは  ワープロで'), 'わたしはワープロで');
  assert.equal(stripSpaces('あの　ひと'), 'あのひと');   // 全形空白 U+3000
});
```

- [ ] **Step 2: 執行確認失敗**

Run: `node --test tests/app/test_kana.js`
Expected: FAIL — 模組不存在

- [ ] **Step 3: 實作 `app/lang/kana.js`**

```js
const HIRA_START = 0x3041, HIRA_END = 0x3096;
const KATA_START = 0x30a1, KATA_END = 0x30f6;
const GAP = KATA_START - HIRA_START;

export function toHiragana(s) {
  let out = '';
  for (const ch of s) {
    const c = ch.codePointAt(0);
    out += (c >= KATA_START && c <= KATA_END) ? String.fromCodePoint(c - GAP) : ch;
  }
  return out;
}

export function toKatakana(s) {
  let out = '';
  for (const ch of s) {
    const c = ch.codePointAt(0);
    out += (c >= HIRA_START && c <= HIRA_END) ? String.fromCodePoint(c + GAP) : ch;
  }
  return out;
}

export function isKana(ch) {
  const c = ch.codePointAt(0);
  return (c >= HIRA_START && c <= HIRA_END) || (c >= KATA_START && c <= KATA_END);
}

export function stripSpaces(s) {
  return s.replace(/[\s　]+/g, '');
}
```

- [ ] **Step 4: 執行確認通過**

Run: `node --test tests/app/test_kana.js`
Expected: 4 tests PASS

- [ ] **Step 5: 提交**

```bash
git add app/lang/kana.js tests/app/test_kana.js
git commit -m "$(cat <<'EOF'
feat(app): 假名正規化與平片假名互轉

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QazTpwM3ApzPa47zWjy26D
EOF
)"
```

---

## Task 3: 動詞分類表（`data/verbs.json`）

**Files:**
- Create: `data/verbs.json`, `tests/app/test_verbs_data.js`

**Interfaces:**
- Consumes: `data/lessons/*.json` 的 `vocab`
- Produces: `data/verbs.json` —
  ```jsonc
  {
    "切ります":   {"group": "I",   "dict": "切る",   "kana": "きります",  "lesson": 7},
    "食べます":   {"group": "II",  "dict": "食べる", "kana": "たべます",  "lesson": 6},
    "勉強します": {"group": "III", "dict": "勉強する", "kana": "べんきょうします", "lesson": 4},
    "あげます":   {"group": "II",  "dict": "あげる", "kana": "あげます",  "lesson": 7}
  }
  // 鍵為**引用形** = kanji || kana（有漢字用漢字，沒有的用假名）
  // kana 欄位保留ます形的假名，變化引擎用它產生題目答案
  ```

### 為什麼需要這張表（實測證據，不要跳過這段）

語料中 `ます` 結尾的動詞共 **72 個**，但課本只在第 14、15 課標註 `group`（29 筆）。**純靠語尾推導會錯**，實測反例：

| 假名 | 漢字 | 語尾推導 | 課本標記 | 正確 |
|---|---|---|---|---|
| かします | 貸します | III（以します結尾） | **I** | 貸す 是 I 類 |
| けします | 消します | III | **I** | 消す |
| はなします | 話します | III | **I** | 話す |
| かえります | 帰ります | I（り是 i 段） | — | 帰る 是 I 類，但**外形像 II 類** |
| かります | 借ります | I（り是 i 段） | — | 借りる 是 **II 類** |

**i 段結尾的動詞有 46 個，語尾完全無法區分 I 類與 II 類**（書きます→書く 是 I，起きます→起きる 是 II）。這正是課本要標註的原因。

### 分類規則（實作 Task 4 時依此）

1. **III 類**：`する` 複合動詞與 `来ます`。判準是「**する 複合**」，不是「以します結尾」——`勉強します`／`コピーします`／`結婚します`／`散歩します`／`食事します`／`買い物します`／`研究します` 是 III；`貸します`／`消します`／`話します`／`出します`／`思い出します` 是 I。
2. **II 類**：ます 前為 **e 段**（えけせてねへめれげぜでべぺ）一律 II 類，無例外。
3. **i 段**：無法推導，**一律查表**。

- [ ] **Step 1: 寫失敗的測試**

`tests/app/test_verbs_data.js`：

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const verbs = JSON.parse(await readFile('data/verbs.json', 'utf8'));
const lessons = await Promise.all(
  [...Array(15)].map((_, i) =>
    readFile(`data/lessons/${String(i + 1).padStart(2, '0')}.json`, 'utf8').then(JSON.parse))
);

test('涵蓋語料中所有 ます 結尾的單字（排除非單一動詞者）', () => {
  const EXCLUDE = new Set(['しって  います', 'すんで  います', 'いらっしゃいます います']);
  const missing = [];
  for (const d of lessons) {
    for (const v of d.vocab) {
      const form = v.kanji || v.kana || '';
      if (!form.endsWith('ます')) continue;
      if (EXCLUDE.has(v.kana)) continue;
      if (!verbs[v.kana]) missing.push(`L${d.lesson} ${v.kana}`);
    }
  }
  assert.deepEqual(missing, [], `未收錄: ${missing.join(', ')}`);
});

test('與課本自身的 group 標記完全一致', () => {
  const conflicts = [];
  for (const d of lessons) {
    for (const v of d.vocab) {
      if (!v.group || !verbs[v.kana]) continue;
      if (verbs[v.kana].group !== v.group) {
        conflicts.push(`${v.kana}: 表=${verbs[v.kana].group} 課本=${v.group}`);
      }
    }
  }
  assert.deepEqual(conflicts, [], conflicts.join('; '));
});

test('課本未標註但已知的關鍵分類正確', () => {
  assert.equal(verbs['かします'].group, 'I');      // 貸す：非 する 複合
  assert.equal(verbs['かえります'].group, 'I');    // 帰る：外形像 II 類的 I 類
  assert.equal(verbs['かります'].group, 'II');     // 借りる：i 段但為 II 類
  assert.equal(verbs['きります'].group, 'I');      // 切る
  assert.equal(verbs['はいります'].group, 'I');    // 入る：同 帰る
  assert.equal(verbs['おきます'].group, 'II');     // 起きる
  assert.equal(verbs['たべます'].group, 'II');     // 食べる
  assert.equal(verbs['べんきょうします'].group, 'III');
  assert.equal(verbs['きます'].group, 'III');      // 来る
  assert.equal(verbs['します'].group, 'III');      // する
});

test('鍵不含空白（否則 conjugate 會切錯語幹並靜默產生錯誤答案）', () => {
  for (const k of Object.keys(verbs)) {
    assert.equal(/[\s　]/.test(k), false, `鍵含空白: ${JSON.stringify(k)}`);
  }
});

test('每筆都有 group 與 dict，group 值合法', () => {
  for (const [k, v] of Object.entries(verbs)) {
    assert.ok(['I', 'II', 'III'].includes(v.group), `${k} group 非法: ${v.group}`);
    assert.ok(typeof v.dict === 'string' && v.dict.length > 0, `${k} 缺 dict`);
  }
});
```

- [ ] **Step 2: 執行確認失敗**

Run: `node --test tests/app/test_verbs_data.js`
Expected: FAIL — `ENOENT: data/verbs.json`

- [ ] **Step 3: 建立 `data/verbs.json`**

**課本已標註者（29 筆）直接採用其 `group`**，不得更動——那是課本的權威宣告。

**課本未標註者，以下為正確分類**（已逐一核對辭書形）：

```
I 類：おわります(終わる) はたらきます(働く) やすみます(休む) いきます(行く)
      かえります(帰る) あいます(会う) かいます(買う) かきます(書く) ききます(聞く)
      すいます(吸う) とります(撮る) のみます(飲む) よみます(読む) おくります(送る)
      かします(貸す) きります(切る) ならいます(習う) もらいます(もらう)
      あります(ある) わかります(わかる) かかります(かかる) あそびます(遊ぶ)
      およぎます(泳ぐ) だします(出す) はいります(入る)

II 類：おきます(起きる) ねます(寝る) たべます(食べる) みます(見る) あげます(あげる)
      おしえます(教える) かけます(かける) かります(借りる) います(いる)
      つかれます(疲れる) でます(出る) むかえます(迎える)

III 類：べんきょうします(勉強する) きます(来る) します(する) かいものします(買い物する)
      けっこんします(結婚する) さんぽします(散歩する) しょくじします(食事する)
```

**排除這三筆**（`kana` 含空白，不是單一動詞詞條）：`しって  います`、`すんで  います`、`いらっしゃいます います`

**為什麼必須排除**：`conjugate()` 以 `masuForm.slice(0, -2)` 取語幹。`'いらっしゃいます います'` 雖以 `ます` 結尾，語幹會被切成 `'いらっしゃいます い'`——**產生錯誤答案而非拋錯**。這正是本專案 Phase 0 一路在防的靜默損毀。`data/verbs.json` 的鍵一律不得含空白。

- [ ] **Step 4: 執行確認通過**

Run: `node --test tests/app/test_verbs_data.js`
Expected: 5 tests PASS

- [ ] **Step 5: 提交**

```bash
git add data/verbs.json tests/app/test_verbs_data.js
git commit -m "$(cat <<'EOF'
feat(app): 動詞分類表，涵蓋語料全部 ます 形動詞

課本僅第 14、15 課標註 group（29/72），其餘由辭書形人工核對。
語尾推導不可行：i 段結尾 46 個動詞無法區分 I 類與 II 類，
且「以します結尾」不等於 III 類（貸す／消す／話す 皆為 I 類）。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QazTpwM3ApzPa47zWjy26D
EOF
)"
```

---

## Task 4: 動詞變化引擎（`lang/conjugation.js`）

**Files:**
- Create: `app/lang/conjugation.js`, `tests/app/test_conjugation.js`

**Interfaces:**
- Consumes: `data/verbs.json`（由呼叫端載入後注入）
- Produces:
  ```js
  export const FORMS = ['masu', 'masen', 'mashita', 'masendeshita', 'te'];
  export const FORM_LESSON = { masu: 4, masen: 4, mashita: 4, masendeshita: 4, te: 14 };
  export function conjugate(masuForm, group, form)  // → string
  // masuForm 為ます形（如 'かきます'），group ∈ 'I'|'II'|'III'，form ∈ FORMS
  // 無法變化時丟 Error（不得回傳 null 或原樣——靜默失敗會讓錯誤答案進題庫）
  ```

### て形變化規則（I 類依語幹末音）

| ます形語幹末音 | て形 | 例 |
|---|---|---|
| い・ち・り | って | かいます→かって、まちます→まって、とります→とって |
| に・び・み | んで | のみます→のんで、あそびます→あそんで、よびます→よんで |
| き | いて | かきます→かいて |
| ぎ | いで | いそぎます→いそいで |
| し | して | はなします→はなして |

**唯一不規則**：`いきます` → `いって`（不是 `いいて`）。規格 §6.4 已載明，課本第 14 課也以 `＊` 標記。

II 類：去 `ます` 加 `て`（たべます→たべて）。
III 類：`します`→`して`、`きます`→`きて`（勉強します→勉強して）。

- [ ] **Step 1: 寫失敗的測試**

`tests/app/test_conjugation.js`：

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { conjugate, FORMS, FORM_LESSON } from '../../app/lang/conjugation.js';

test('時態四變化（與類別無關）', () => {
  assert.equal(conjugate('かきます', 'I', 'masu'), 'かきます');
  assert.equal(conjugate('かきます', 'I', 'masen'), 'かきません');
  assert.equal(conjugate('かきます', 'I', 'mashita'), 'かきました');
  assert.equal(conjugate('かきます', 'I', 'masendeshita'), 'かきませんでした');
  assert.equal(conjugate('たべます', 'II', 'masen'), 'たべません');
});

test('I 類て形：依語幹末音', () => {
  assert.equal(conjugate('かいます', 'I', 'te'), 'かって');   // い→って
  assert.equal(conjugate('まちます', 'I', 'te'), 'まって');   // ち→って
  assert.equal(conjugate('とります', 'I', 'te'), 'とって');   // り→って
  assert.equal(conjugate('のみます', 'I', 'te'), 'のんで');   // み→んで
  assert.equal(conjugate('あそびます', 'I', 'te'), 'あそんで'); // び→んで
  assert.equal(conjugate('かきます', 'I', 'te'), 'かいて');   // き→いて
  assert.equal(conjugate('いそぎます', 'I', 'te'), 'いそいで'); // ぎ→いで
  assert.equal(conjugate('はなします', 'I', 'te'), 'はなして'); // し→して
});

test('いきます 是唯一的 I 類て形不規則', () => {
  assert.equal(conjugate('いきます', 'I', 'te'), 'いって');
  assert.notEqual(conjugate('いきます', 'I', 'te'), 'いいて');
});

test('II 類與 III 類て形', () => {
  assert.equal(conjugate('たべます', 'II', 'te'), 'たべて');
  assert.equal(conjugate('おきます', 'II', 'te'), 'おきて');
  assert.equal(conjugate('します', 'III', 'te'), 'して');
  assert.equal(conjugate('きます', 'III', 'te'), 'きて');
  assert.equal(conjugate('べんきょうします', 'III', 'te'), 'べんきょうして');
});

test('外形像 II 類的 I 類動詞，依傳入的 group 變化', () => {
  // 帰ります 是 I 類：て形為 かえって，不是 かえて
  assert.equal(conjugate('かえります', 'I', 'te'), 'かえって');
  // 借ります 是 II 類：て形為 かりて，不是 かって
  assert.equal(conjugate('かります', 'II', 'te'), 'かりて');
});

test('無效輸入丟 Error，不得靜默回傳', () => {
  assert.throws(() => conjugate('たべる', 'II', 'te'), /ます/);
  assert.throws(() => conjugate('たべます', 'IV', 'te'), /group/);
  assert.throws(() => conjugate('たべます', 'II', 'nai'), /form/);
});

test('FORM_LESSON 標示各形態的解鎖課次', () => {
  assert.equal(FORM_LESSON.masu, 4);
  assert.equal(FORM_LESSON.te, 14);
  assert.ok(FORMS.includes('te'));
});
```

- [ ] **Step 2: 執行確認失敗**

Run: `node --test tests/app/test_conjugation.js`
Expected: FAIL — 模組不存在

- [ ] **Step 3: 實作 `app/lang/conjugation.js`**

```js
export const FORMS = ['masu', 'masen', 'mashita', 'masendeshita', 'te'];

/** 各形態在課本中首次出現的課次，用於範圍過濾（規格 §5.3 requires_lesson）。 */
export const FORM_LESSON = { masu: 4, masen: 4, mashita: 4, masendeshita: 4, te: 14 };

const TENSE_SUFFIX = {
  masu: 'ます', masen: 'ません', mashita: 'ました', masendeshita: 'ませんでした',
};

/** I 類：ます形語幹末音 → て形語尾。 */
const I_TE = new Map([
  ['い', 'って'], ['ち', 'って'], ['り', 'って'],
  ['に', 'んで'], ['び', 'んで'], ['み', 'んで'],
  ['き', 'いて'], ['ぎ', 'いで'], ['し', 'して'],
]);

/** 唯一的 I 類て形不規則（規格 §6.4）。 */
const I_TE_IRREGULAR = new Map([['いきます', 'いって']]);

export function conjugate(masuForm, group, form) {
  if (typeof masuForm !== 'string' || !masuForm.endsWith('ます')) {
    throw new Error(`conjugate: 需要ます形，收到 ${JSON.stringify(masuForm)}`);
  }
  if (!['I', 'II', 'III'].includes(group)) {
    throw new Error(`conjugate: 未知的 group ${JSON.stringify(group)}`);
  }
  if (!FORMS.includes(form)) {
    throw new Error(`conjugate: 未知的 form ${JSON.stringify(form)}`);
  }

  const stem = masuForm.slice(0, -2);
  if (form !== 'te') return stem + TENSE_SUFFIX[form];

  if (I_TE_IRREGULAR.has(masuForm)) return I_TE_IRREGULAR.get(masuForm);
  if (group === 'II') return stem + 'て';
  if (group === 'III') {
    if (masuForm.endsWith('きます')) return masuForm.slice(0, -3) + 'きて';
    return stem + 'して'.slice(1); // します→して：stem 已含「し」前的部分
  }

  const last = stem.slice(-1);
  const ending = I_TE.get(last);
  if (!ending) throw new Error(`conjugate: I 類語幹末音 ${last} 無對應て形（${masuForm}）`);
  return stem.slice(0, -1) + ending;
}
```

**注意 III 類那兩行容易寫錯**，請以測試為準：
- `します` → stem 是 `し`，結果應為 `して`
- `べんきょうします` → stem 是 `べんきょうし`，結果應為 `べんきょうして`
- `きます`（来ます）→ 結果應為 `きて`

若上面的寫法過不了測試，請改用更直接的形式（例如對 III 類直接 `stem + 'て'`，因為 stem 已以 `し` 或 `き` 結尾）。**以測試通過為準，不要改測試。**

- [ ] **Step 4: 執行確認通過**

Run: `node --test tests/app/test_conjugation.js`
Expected: 7 tests PASS

- [ ] **Step 5: 全語料驗證**

```bash
node -e "
const fs=require('fs');
const verbs=JSON.parse(fs.readFileSync('data/verbs.json','utf8'));
import('./app/lang/conjugation.js').then(({conjugate,FORMS})=>{
  let n=0, err=[];
  for(const [kana,info] of Object.entries(verbs)){
    for(const f of FORMS){
      try{ conjugate(kana, info.group, f); n++; }
      catch(e){ err.push(kana+'/'+f+': '+e.message); }
    }
  }
  console.log('成功變化', n, '組；失敗', err.length);
  err.slice(0,10).forEach(x=>console.log('  ',x));
});
"
```
Expected: 失敗數為 0

- [ ] **Step 6: 提交**

```bash
git add app/lang/conjugation.js tests/app/test_conjugation.js
git commit -m "$(cat <<'EOF'
feat(app): 動詞變化引擎，ます形與て形

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QazTpwM3ApzPa47zWjy26D
EOF
)"
```

---

## Task 5: 答案正規化比對（`core/normalize.js`）

**Files:** Create `app/core/normalize.js`, `tests/app/test_normalize.js`

**Interfaces:**
- Consumes: `app/lang/kana.js` 的 `toHiragana`、`stripSpaces`
- Produces:
  ```js
  export function normalizeAnswer(s)                  // → 正規化字串
  export function isCorrect(input, answer, alternatives = [])  // → boolean
  ```

**原則（規格 §9.1）**：格式差異一律寬鬆，語言本身的差異一律嚴格。

| 情況 | 處理 |
|---|---|
| 空白（課本用全形空格分詞） | 全部移除 |
| 片假名 vs 平假名 | 統一為平假名後比對 |
| 句號 `。`／`.`／未輸入 | 皆正確 |
| 全形／半形數字、英文 | 統一為半形 |
| **長音、促音、濁音** | **必須正確**，這是考點不是格式 |

- [ ] **Step 1: 寫失敗的測試**

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { normalizeAnswer, isCorrect } from '../../app/core/normalize.js';

test('格式差異一律寬鬆', () => {
  assert.ok(isCorrect('わたしはワープロで手紙を書きます', 'わたしは  ワープロで  手紙を  書きます。'));
  assert.ok(isCorrect('コーヒー', 'こーひー'));          // 片假名↔平假名
  assert.ok(isCorrect('たべます。', 'たべます'));         // 句號可有可無
  assert.ok(isCorrect('たべます.', 'たべます'));          // 半形句點
  assert.ok(isCorrect('１４にち', '14にち'));             // 全形數字
});

test('語言本身的差異一律嚴格', () => {
  assert.equal(isCorrect('きて', 'きって'), false);       // 促音
  assert.equal(isCorrect('ビル', 'ビール'), false);       // 長音
  assert.equal(isCorrect('かいて', 'かいで'), false);     // 濁音
});

test('alternatives 任一相符即正確', () => {
  assert.ok(isCorrect('から', 'に', ['から']));
  assert.equal(isCorrect('へ', 'に', ['から']), false);
});

test('normalizeAnswer 冪等', () => {
  const once = normalizeAnswer('わたしは  コーヒーを  飲みます。');
  assert.equal(normalizeAnswer(once), once);
});
```

- [ ] **Step 2: 執行確認失敗** — `node --test tests/app/test_normalize.js`

- [ ] **Step 3: 實作**

```js
import { toHiragana, stripSpaces } from '../lang/kana.js';

const FULLWIDTH_OFFSET = 0xfee0; // 全形 ！～～ 對應半形

function toHalfWidth(s) {
  return s.replace(/[！-～]/g, (ch) =>
    String.fromCharCode(ch.charCodeAt(0) - FULLWIDTH_OFFSET));
}

export function normalizeAnswer(s) {
  if (typeof s !== 'string') return '';
  let out = toHalfWidth(s);
  out = toHiragana(out);
  out = stripSpaces(out);
  out = out.replace(/[。.．]+$/u, '');   // 只移除結尾的句號
  return out;
}

export function isCorrect(input, answer, alternatives = []) {
  const got = normalizeAnswer(input);
  if (got.length === 0) return false;
  return [answer, ...alternatives].some((a) => normalizeAnswer(a) === got);
}
```

- [ ] **Step 4: 執行確認通過** — 4 tests PASS

- [ ] **Step 5: 提交** — `feat(app): 答案正規化比對`

---

## Task 6: FSRS-lite 熟悉度（`core/srs.js`）

**Files:** Create `app/core/srs.js`, `tests/app/test_srs.js`

**Interfaces:**
- Consumes: 無
- Produces:
  ```js
  export const SRS_CONST = { W: 1.0, S_MIN: 0.4, D_MIN: 1.0, D_MAX: 10.0,
    S_INIT: {1:0.4, 2:1.2, 3:3.2, 4:9.0}, D_INIT: {1:7.0, 2:6.0, 3:5.0, 4:4.0},
    LAPSE_S_FACTOR: 0.4, LAPSE_D_DELTA: 1.0, SUCCESS_D_DELTA: 0.1 };
  export function retrievability(S, elapsedDays)      // → 0..1
  export function initialState(grade)                 // → {S, D}
  export function updateState(state, grade, elapsedDays) // → {S, D}
  export function replay(events, nowSec)              // → Map<itemId, {S, D, lastSec, reps, lapses, R}>
  // events: [{i: itemId, t: unixSeconds, g: 1..4}, ...]，必須依 t 排序後重放
  ```

**衰減公式（規格 §7.2）**：`R(t) = (1 + t / (9·S))^-1`

- [ ] **Step 1: 寫失敗的測試**

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { retrievability, initialState, updateState, replay, SRS_CONST } from '../../app/core/srs.js';

const near = (a, b, tol = 0.01) => assert.ok(Math.abs(a - b) < tol, `${a} vs ${b}`);

test('衰減曲線符合規格 §7.2 的表', () => {
  near(retrievability(3, 3), 0.90);     // S=3 天，3 天後 90%
  near(retrievability(3, 7), 0.79);
  near(retrievability(3, 30), 0.47);
  near(retrievability(30, 30), 0.90);   // S=30 天，30 天後才 90%
  near(retrievability(30, 90), 0.75);
  near(retrievability(3, 0), 1.00);     // 剛複習完
});

test('練得越熟，同樣天數衰減越慢', () => {
  assert.ok(retrievability(30, 7) > retrievability(3, 7));
});

test('首次作答依 grade 給初始狀態', () => {
  assert.equal(initialState(1).S, 0.4);
  assert.equal(initialState(4).S, 9.0);
  assert.ok(initialState(1).D > initialState(4).D);  // 答錯者難度較高
});

test('答對時 S 增加；在快遺忘時答對增益最大（規格 §7.3）', () => {
  const s = { S: 3, D: 5 };
  // R=1 時 (e^(1-R) - 1) 精確為 0，增益必為 0——同日重複複習不給穩定度增益。
  // 這是長期記憶模型的正確行為：兩分鐘後再答對一次，不代表記得更久。
  assert.equal(updateState(s, 3, 0).S, 3, 'elapsed=0 時 S 不變（增益精確為 0）');

  const lateWin = updateState(s, 3, 20).S;   // R≈0.31，快忘掉才答對
  const earlyWin = updateState(s, 3, 1).S;   // R≈0.96
  assert.ok(lateWin > earlyWin, `晚答對應增益更大: ${lateWin} vs ${earlyWin}`);
  assert.ok(earlyWin > 3, '有經過時間就該有增益');
});

test('S 越大增幅越小（邊際遞減）', () => {
  const gain = (S) => updateState({ S, D: 5 }, 3, S).S / S;
  assert.ok(gain(3) > gain(30), '高 S 的相對增幅應較小');
});

test('難題（D 高）的 S 增幅較小', () => {
  const easy = updateState({ S: 3, D: 2 }, 3, 3).S;
  const hard = updateState({ S: 3, D: 9 }, 3, 3).S;
  assert.ok(easy > hard);
});

test('答錯時 S 縮水但不歸零，D 上調', () => {
  const next = updateState({ S: 10, D: 5 }, 1, 5);
  assert.ok(next.S < 10 && next.S >= SRS_CONST.S_MIN, `S=${next.S}`);
  assert.ok(next.D > 5);
});

test('D 夾在 1..10', () => {
  let st = { S: 3, D: 9.8 };
  for (let i = 0; i < 10; i++) st = updateState(st, 1, 1);
  assert.ok(st.D <= 10);
  st = { S: 3, D: 1.2 };
  for (let i = 0; i < 10; i++) st = updateState(st, 4, 1);
  assert.ok(st.D >= 1);
});

test('replay 從事件日誌重建狀態，且與事件順序無關（會先排序）', () => {
  const day = 86400;
  const now = 1000 * day;
  const evs = [
    { i: 'a', t: now - 10 * day, g: 3 },
    { i: 'a', t: now - 3 * day, g: 3 },
    { i: 'b', t: now - 1 * day, g: 1 },
  ];
  const m1 = replay(evs, now);
  const m2 = replay([...evs].reverse(), now);
  assert.equal(m1.get('a').reps, 2);
  assert.equal(m1.get('b').lapses, 1);
  assert.deepEqual(m1.get('a'), m2.get('a'), 'replay 必須先排序，與輸入順序無關');
  assert.ok(m1.get('a').R > 0 && m1.get('a').R <= 1);
});
```

- [ ] **Step 2: 執行確認失敗** — `node --test tests/app/test_srs.js`

- [ ] **Step 3: 實作**

```js
export const SRS_CONST = {
  W: 1.0, S_MIN: 0.4, D_MIN: 1.0, D_MAX: 10.0,
  S_INIT: { 1: 0.4, 2: 1.2, 3: 3.2, 4: 9.0 },
  D_INIT: { 1: 7.0, 2: 6.0, 3: 5.0, 4: 4.0 },
  LAPSE_S_FACTOR: 0.4, LAPSE_D_DELTA: 1.0, SUCCESS_D_DELTA: 0.1,
};

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

/** 規格 §7.2：R(t) = (1 + t/(9S))^-1。純函式，每次讀取時即時計算，不需背景排程。 */
export function retrievability(S, elapsedDays) {
  const s = Math.max(S, SRS_CONST.S_MIN);
  return 1 / (1 + Math.max(0, elapsedDays) / (9 * s));
}

export function initialState(grade) {
  return { S: SRS_CONST.S_INIT[grade], D: SRS_CONST.D_INIT[grade] };
}

export function updateState(state, grade, elapsedDays) {
  const { W, S_MIN, D_MIN, D_MAX, LAPSE_S_FACTOR, LAPSE_D_DELTA, SUCCESS_D_DELTA } = SRS_CONST;
  const S = Math.max(state.S, S_MIN);
  const D = clamp(state.D, D_MIN, D_MAX);
  const R = retrievability(S, elapsedDays);

  if (grade === 1) {
    return { S: Math.max(S_MIN, S * LAPSE_S_FACTOR), D: clamp(D + LAPSE_D_DELTA, D_MIN, D_MAX) };
  }
  // 規格 §7.3：(e^(1-R) - 1) 使「快遺忘時答對」增益最大；
  // S^-0.5 造成邊際遞減；(11 - D) 使難題的間隔不被衝高。
  //
  // 【設計後果，不要「修好」它】elapsedDays=0 時 R 精確為 1，本式增益精確為 0。
  // 這代表規格 §8 的 lapse re-drill（答錯後 3~5 題重新插入）即使答對，S 也不會增加。
  // 那是正確的：兩分鐘後記得不代表兩天後記得。同日重複複習需要另一套短期模型，
  // 不在這個 lite 版的範圍。
  const gain = Math.exp(W) * (11 - D) * Math.pow(S, -0.5) * (Math.exp(1 - R) - 1);
  return {
    S: Math.max(S_MIN, S * (1 + gain)),
    D: clamp(D - SUCCESS_D_DELTA * (grade - 3), D_MIN, D_MAX),
  };
}

const SEC_PER_DAY = 86400;

/** 事件日誌 → 每題的目前狀態。事件不可變，重放即可，故演算法調整後可重算歷史。 */
export function replay(events, nowSec) {
  const sorted = [...events].sort((a, b) => a.t - b.t || (a.n ?? 0) - (b.n ?? 0));
  const out = new Map();
  for (const ev of sorted) {
    const prev = out.get(ev.i);
    if (!prev) {
      const { S, D } = initialState(ev.g);
      out.set(ev.i, { S, D, lastSec: ev.t, reps: 1, lapses: ev.g === 1 ? 1 : 0 });
      continue;
    }
    const elapsed = (ev.t - prev.lastSec) / SEC_PER_DAY;
    const next = updateState(prev, ev.g, elapsed);
    out.set(ev.i, {
      ...next, lastSec: ev.t, reps: prev.reps + 1,
      lapses: prev.lapses + (ev.g === 1 ? 1 : 0),
    });
  }
  for (const [id, st] of out) {
    out.set(id, { ...st, R: retrievability(st.S, (nowSec - st.lastSec) / SEC_PER_DAY) });
  }
  return out;
}
```

- [ ] **Step 4: 執行確認通過** — 9 tests PASS

- [ ] **Step 5: 提交** — `feat(app): FSRS-lite 熟悉度與事件重放`

---

## Task 7: 概念層與技能聚合（`core/concepts.js`）

**Files:** Create `app/core/concepts.js`, `tests/app/test_concepts.js`

**Interfaces:**
- Consumes: 無（只吃資料物件）
- Produces:
  ```js
  export const SKILLS = ['單字', '讀音', '變化', '助詞', '句型', '數量'];
  export function skillOf(conceptId)                 // → SKILLS 之一，未知回 null
  export function conceptsForVocab(v)                // → string[]  （v 為 vocab 物件）
  export function conceptsForConjugation(kana, group, form) // → string[]
  export function aggregateSkills(conceptR)          // → { 單字: 0.78, ... }
  // conceptR: Map<conceptId, {R, reps}>；權重為 log(1+reps)，避免只練過一次的概念左右大局
  ```

**概念 id 格式（規格 §5.2）**：`w:<kana>` 單字字義、`w:<kana>:reading` 漢字讀音、`w:<kana>:group` 動詞分類、`r:<form>:group<I|II|III>` 變化規則、`p:` 助詞、`g:` 句型、`c:`／`n:` 量詞數字。

**技能歸屬（規格 §7.6）**：`w:X` → 單字；`w:X:reading` → 讀音；`w:X:group` 與 `r:*` → 變化；`p:*` → 助詞；`g:*` → 句型；`c:*`／`n:*` → 數量。

**注意**：`w:X:reading` 與 `w:X:group` 都以 `w:` 開頭，**判斷順序必須先檢查後綴再檢查前綴**，否則全部會被歸成「單字」。

- [ ] **Step 1: 寫失敗的測試**

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { SKILLS, skillOf, conceptsForVocab, conceptsForConjugation, aggregateSkills }
  from '../../app/core/concepts.js';

test('技能歸屬：後綴優先於前綴', () => {
  assert.equal(skillOf('w:きります'), '單字');
  assert.equal(skillOf('w:てがみ:reading'), '讀音');
  assert.equal(skillOf('w:きります:group'), '變化');
  assert.equal(skillOf('r:te:groupI'), '變化');
  assert.equal(skillOf('p:に:recipient'), '助詞');
  assert.equal(skillOf('g:mou_mashita'), '句型');
  assert.equal(skillOf('c:hon'), '數量');
  assert.equal(skillOf('n:time:hour'), '數量');
  assert.equal(skillOf('zzz:unknown'), null);
});

test('有漢字的單字產生字義與讀音兩個概念（以引用形為 lemma）', () => {
  const ids = conceptsForVocab({ kana: 'きります', kanji: '切ります', zh: '剪，切' });
  assert.deepEqual(ids.sort(), ['w:切ります', 'w:切ります:reading'].sort());
});

test('概念用引用形：同假名不同詞分開，同詞跨課共用', () => {
  const oki = conceptsForVocab({ kana: 'おきます', kanji: '起きます' });
  const oku = conceptsForVocab({ kana: 'おきます', kanji: '置きます' });
  assert.notDeepEqual(oki, oku, '起きる 與 置く 是不同概念');

  const y4 = conceptsForVocab({ kana: 'やすみます', kanji: '休みます' });
  const y11 = conceptsForVocab({ kana: 'やすみます', kanji: '休みます' });
  assert.deepEqual(y4, y11, '同一個詞跨課次應共用概念');
});

test('無漢字的單字只產生字義概念', () => {
  const ids = conceptsForVocab({ kana: 'あげます', kanji: null, zh: '給，送' });
  assert.deepEqual(ids, ['w:あげます']);
});

test('變化題涵蓋規則與該動詞的分類', () => {
  const ids = conceptsForConjugation('かきます', 'I', 'te');
  assert.ok(ids.includes('r:te:groupI'));
  assert.ok(ids.includes('w:かきます:group'));
});

test('技能聚合以 log(1+reps) 加權', () => {
  const m = new Map([
    ['w:a', { R: 1.0, reps: 1 }],    // 只練過一次
    ['w:b', { R: 0.0, reps: 100 }],  // 練過很多次但很生疏
  ]);
  const agg = aggregateSkills(m);
  assert.ok(agg['單字'] < 0.3, `練得多的生疏概念應主導: ${agg['單字']}`);
});

test('無資料的技能回傳 null 而非 0（尚未練過 ≠ 熟悉度 0）', () => {
  const agg = aggregateSkills(new Map([['w:a', { R: 0.8, reps: 3 }]]));
  assert.ok(agg['單字'] > 0);
  assert.equal(agg['助詞'], null);
});
```

- [ ] **Step 2: 執行確認失敗** — `node --test tests/app/test_concepts.js`

- [ ] **Step 3: 實作**

```js
export const SKILLS = ['單字', '讀音', '變化', '助詞', '句型', '數量'];

export function skillOf(conceptId) {
  if (typeof conceptId !== 'string') return null;
  // 後綴必須先判斷：w:X:reading 與 w:X:group 都以 w: 開頭
  if (conceptId.endsWith(':reading')) return '讀音';
  if (conceptId.endsWith(':group')) return '變化';
  if (conceptId.startsWith('r:')) return '變化';
  if (conceptId.startsWith('w:')) return '單字';
  if (conceptId.startsWith('p:')) return '助詞';
  if (conceptId.startsWith('g:')) return '句型';
  if (conceptId.startsWith('c:') || conceptId.startsWith('n:')) return '數量';
  return null;
}

export function conceptsForVocab(v) {
  // 引用形（kanji || kana）作為 lemma，與 verbs.json 的鍵及 transform 的概念一致。
  // 粒度剛好正確：起きます／置きます 分開（不同動詞），
  // 休みます L4「休息」與 L11「請假」共用（同一個詞）。
  const cite = v.kanji || v.kana;
  const ids = [`w:${cite}`];
  if (v.kanji) ids.push(`w:${cite}:reading`);
  return ids;
}

export function conceptsForConjugation(kana, group, form) {
  return [`r:${form}:group${group}`, `w:${kana}:group`];
}

/** 規格 §7.6：權重取 log(1+複習次數)，避免只練過一次的概念左右大局。 */
export function aggregateSkills(conceptR) {
  const acc = Object.fromEntries(SKILLS.map((s) => [s, { sum: 0, w: 0 }]));
  for (const [id, st] of conceptR) {
    const skill = skillOf(id);
    if (!skill) continue;
    const w = Math.log(1 + (st.reps ?? 0));
    if (w <= 0) continue;
    acc[skill].sum += st.R * w;
    acc[skill].w += w;
  }
  return Object.fromEntries(
    SKILLS.map((s) => [s, acc[s].w > 0 ? acc[s].sum / acc[s].w : null]));
}
```

- [ ] **Step 4: 執行確認通過** — 6 tests PASS

- [ ] **Step 5: 提交** — `feat(app): 概念層與六類技能聚合`

---

## Task 8: 對照題生成器（`generators/recall.js`）

**Files:** Create `app/generators/recall.js`, `tests/app/test_recall.js`

**Interfaces:**
- Consumes: `app/core/concepts.js`
- Produces:
  ```js
  export const ENGINE = 'recall';
  export function* generate(vocabList)   // yield Item
  // Item: {id, engine, lesson, requires_lesson, covers, skills, prompt, answer, alternatives, source_ref}
  // prompt: {type: 'text', text, hint}
  ```

**Phase 1 產生兩種題型**（皆可由打字客觀評分）：
- `zh2jp`：給中文釋義，答日文（假名）。`alternatives` 含漢字形。
- `kanji2kana`：給漢字，答假名。僅限有 `kanji` 的單字。

**不做 `jp2zh`**（給日文答中文）：中文自由作答的評分需要選擇題 UI，排入 Phase 2。這是刻意縮小的範圍，不是遺漏。

**id 格式**：`recall:<kana>:<variant>`，決定性、不含亂數。**真實語料中有 11 組假名會撞鍵**（如 `おきます` = 起きます／置きます），碰撞時才附加課本既定的 `L<課次>-<編號>` 後綴消歧——那些值取自課本欄位，不是陣列位置。

**概念 id 與 item id 是不同的命名空間**：概念用引用形（`w:起きます`），item id 用假名加消歧後綴。不需要統一，也不要為了對稱而改。

- [ ] **Step 1: 寫失敗的測試**

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generate, ENGINE } from '../../app/generators/recall.js';

const V = [
  { kana: 'きります', kanji: '切ります', zh: '剪，切', lesson: 7, category: 'numbered', group: null },
  { kana: 'あげます', kanji: null, zh: '給，送', lesson: 7, category: 'numbered', group: null },
];

test('有漢字者產生兩題，無漢字者只產生一題', () => {
  const items = [...generate(V)];
  const ids = items.map((i) => i.id);
  assert.ok(ids.includes('recall:きります:zh2jp'));
  assert.ok(ids.includes('recall:きります:kanji2kana'));
  assert.ok(ids.includes('recall:あげます:zh2jp'));
  assert.equal(ids.includes('recall:あげます:kanji2kana'), false);
  assert.equal(items.length, 3);
});

test('zh2jp：題幹為中文，答案為假名，漢字列入 alternatives', () => {
  const it = [...generate(V)].find((i) => i.id === 'recall:きります:zh2jp');
  assert.equal(it.prompt.text, '剪，切');
  assert.equal(it.answer, 'きります');
  assert.ok(it.alternatives.includes('切ります'));
  assert.equal(it.engine, ENGINE);
});

test('kanji2kana：考讀音，covers 含 reading 概念', () => {
  const it = [...generate(V)].find((i) => i.id === 'recall:きります:kanji2kana');
  assert.equal(it.prompt.text, '切ります');
  assert.equal(it.answer, 'きります');
  assert.ok(it.covers.includes('w:きります:reading'));
  assert.ok(it.skills.includes('讀音'));
  assert.deepEqual(it.alternatives, [], '考讀音時不接受漢字作答');
});

test('requires_lesson 等於單字所在課次，source_ref 可讀', () => {
  const it = [...generate(V)][0];
  assert.equal(it.requires_lesson, 7);
  assert.ok(it.source_ref.includes('第7課'));
});

test('重新生成得到相同 id（決定性）', () => {
  const a = [...generate(V)].map((i) => i.id);
  const b = [...generate(V)].map((i) => i.id);
  assert.deepEqual(a, b);
});
```

- [ ] **Step 2: 執行確認失敗** — `node --test tests/app/test_recall.js`

- [ ] **Step 3: 實作**

```js
import { conceptsForVocab, skillOf } from '../core/concepts.js';

export const ENGINE = 'recall';

function makeItem({ id, v, promptText, hint, answer, alternatives, covers }) {
  return {
    id, engine: ENGINE, lesson: v.lesson, requires_lesson: v.lesson,
    covers, skills: [...new Set(covers.map(skillOf).filter(Boolean))],
    prompt: { type: 'text', text: promptText, hint },
    answer, alternatives,
    source_ref: `第${v.lesson}課 ことば${v.no ? ` ${v.no}` : ''}`,
  };
}

export function* generate(vocabList) {
  for (const v of vocabList) {
    if (!v.kana || !v.zh) continue;
    const base = conceptsForVocab(v);
    yield makeItem({
      id: `recall:${v.kana}:zh2jp`, v,
      promptText: v.zh, hint: '寫出日文',
      answer: v.kana,
      alternatives: v.kanji ? [v.kanji] : [],
      covers: [`w:${v.kanji || v.kana}`],
    });
    if (v.kanji) {
      yield makeItem({
        id: `recall:${v.kana}:kanji2kana`, v,
        promptText: v.kanji, hint: '寫出讀音（平假名）',
        answer: v.kana, alternatives: [],
        covers: [`w:${v.kanji}:reading`],
      });
    }
  }
}
```

- [ ] **Step 4: 執行確認通過** — 5 tests PASS

- [ ] **Step 5: 全語料驗證**

```bash
node -e "
const fs=require('fs');
(async()=>{
  const {buildIndex,loadLessons}=await import('./app/core/data.js');
  const {generate}=await import('./app/generators/recall.js');
  const load=async n=>JSON.parse(fs.readFileSync('data/lessons/'+String(n).padStart(2,'0')+'.json','utf8'));
  const idx=buildIndex(await loadLessons([...Array(15)].map((_,i)=>i+1),load));
  const items=[...generate(idx.vocab)];
  const ids=new Set(items.map(i=>i.id));
  console.log('對照題', items.length, '個；id 唯一:', ids.size===items.length);
})();
"
```
Expected: 題數 > 1000，id 唯一為 true

- [ ] **Step 6: 提交** — `feat(app): 對照題生成器`

---

## Task 9: 變換題生成器（`generators/transform.js`）

**Files:** Create `app/generators/transform.js`, `tests/app/test_transform.js`

**Interfaces:**
- Consumes: `app/lang/conjugation.js`、`app/core/concepts.js`
- Produces:
  ```js
  export const ENGINE = 'transform';
  export function* generate(vocabList, verbsTable)  // yield Item（schema 同 recall）
  ```

**Phase 1 產生的變換**：`masu → te`、`masu → masen`、`masu → mashita`、`masu → masendeshita`。

**`requires_lesson` = max(單字課次, `FORM_LESSON[目標形態]`)**——`送ります` 是第 7 課單字，但て形第 14 課才教，所以該題的 `requires_lesson` 為 14。這是規格 §5.3 的範圍過濾依據：使用者把範圍設 1~10 時這題不該出現。

**id 格式**：`conj:<引用形>:masu2<form>`（不使用 `→`，避免 URL 與檔名問題）。

**為什麼用引用形而非假名**：語料中 `おきます` 同時對應 `起きます`(II 類) 與 `置きます`(I 類)——以假名為鍵會讓其中一個覆蓋另一個，使第 4 課的基礎動詞 `起きます` 的て形算成 `おいて` 而非 `おきて`。**那是教錯。** 引用形（`kanji || kana`）在全語料庫 74 個鍵中分類衝突為 0。

- [ ] **Step 1: 寫失敗的測試**

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generate } from '../../app/generators/transform.js';

const V = [
  { kana: 'おくります', kanji: '送ります', zh: '寄送', lesson: 7, no: 2 },
  { kana: 'たべます', kanji: '食べます', zh: '吃', lesson: 6, no: 1 },
  { kana: 'きります', kanji: '切ります', zh: '剪，切', lesson: 7, no: 1 },
];
const VERBS = {
  '送ります': { group: 'I',  dict: '送る',  kana: 'おくります' },
  '食べます': { group: 'II', dict: '食べる', kana: 'たべます' },
  '切ります': { group: 'I',  dict: '切る',  kana: 'きります' },
};

test('每個動詞產生四種變化題', () => {
  const items = [...generate(V, VERBS)];
  const ids = items.filter((i) => i.id.startsWith('conj:送ります')).map((i) => i.id);
  assert.deepEqual(ids.sort(), [
    'conj:送ります:masu2masen', 'conj:送ります:masu2masendeshita',
    'conj:送ります:masu2mashita', 'conj:送ります:masu2te',
  ]);
});

test('て形題的答案正確，且 requires_lesson 取形態的解鎖課次', () => {
  const it = [...generate(V, VERBS)].find((i) => i.id === 'conj:送ります:masu2te');
  assert.equal(it.prompt.text, 'おくります');
  assert.equal(it.prompt.hint, 'て形');
  assert.equal(it.answer, 'おくって');
  assert.equal(it.lesson, 7, '單字出自第 7 課');
  assert.equal(it.requires_lesson, 14, 'て形第 14 課才教');
});

test('時態題的 requires_lesson 為單字課次（ます形第 4 課已教）', () => {
  const it = [...generate(V, VERBS)].find((i) => i.id === 'conj:食べます:masu2mashita');
  assert.equal(it.answer, 'たべました');
  assert.equal(it.requires_lesson, 6);
});

test('covers 含變化規則與該動詞的分類，skills 為「變化」', () => {
  const it = [...generate(V, VERBS)].find((i) => i.id === 'conj:切ります:masu2te');
  assert.equal(it.answer, 'きって');
  assert.ok(it.covers.includes('r:te:groupI'));
  assert.ok(it.covers.includes('w:きります:group'));
  assert.deepEqual(it.skills, ['變化']);
});

test('不在 verbsTable 中的單字直接跳過，不得猜分類', () => {
  const items = [...generate([{ kana: 'ぜんぜんない', zh: 'x', lesson: 1 }], VERBS)];
  assert.equal(items.length, 0);
});
```

- [ ] **Step 2: 執行確認失敗** — `node --test tests/app/test_transform.js`

- [ ] **Step 3: 實作**

```js
import { conjugate, FORM_LESSON } from '../lang/conjugation.js';
import { conceptsForConjugation, skillOf } from '../core/concepts.js';

export const ENGINE = 'transform';

const TARGETS = [
  { form: 'te', hint: 'て形' },
  { form: 'masen', hint: '否定形（ません）' },
  { form: 'mashita', hint: '過去形（ました）' },
  { form: 'masendeshita', hint: '過去否定形（ませんでした）' },
];

export function* generate(vocabList, verbsTable) {
  // 同一個動詞會在多課重複出現（休みます L4「休息」／L11「請假」等），
  // 逐筆生成會產生重複 id。以引用形去重，並**取最早出現的課次**——
  // 使用者在第 4 課就學過這個詞，ます形題不該等到第 11 課才解鎖。
  const seen = new Map();
  for (const v of vocabList) {
    const cite = v.kanji || v.kana;
    if (!seen.has(cite) || v.lesson < seen.get(cite).lesson) seen.set(cite, v);
  }
  for (const v of seen.values()) {
    const cite = v.kanji || v.kana;            // 引用形：與 verbs.json 的鍵一致
    const info = verbsTable[cite];
    if (!info) continue;                       // 未收錄的動詞不猜分類
    for (const { form, hint } of TARGETS) {
      let answer;
      try {
        answer = conjugate(info.kana, info.group, form);
      } catch {
        continue;                              // 無法變化者略過，不產生錯誤題目
      }
      const covers = conceptsForConjugation(cite, info.group, form);
      yield {
        id: `conj:${cite}:masu2${form}`, engine: ENGINE,
        lesson: v.lesson,
        requires_lesson: Math.max(v.lesson, FORM_LESSON[form]),
        covers, skills: [...new Set(covers.map(skillOf).filter(Boolean))],
        prompt: { type: 'text', text: info.kana, hint },
        answer, alternatives: [],
        source_ref: `第${v.lesson}課 ことば${v.no ? ` ${v.no}` : ''}`,
      };
    }
  }
}
```

- [ ] **Step 4: 執行確認通過** — 5 tests PASS

- [ ] **Step 5: 提交** — `feat(app): 變換題生成器`

---

## Task 10: 事件日誌儲存（`core/store.js`）

**Files:** Create `app/core/store.js`, `tests/app/test_store.js`

**Interfaces:**
- Consumes: 無
- Produces:
  ```js
  export function makeEvent(deviceId, seq, itemId, grade, rtMs, mode, nowSec) // → Event
  // Event: {d, n, i, t, g, r, m}  —— 短鍵節省空間（規格 §10.1）
  export function mergeEvents(a, b)   // → Event[]  以 (d,n) 去重、依 t 排序
  export class MemoryStore { appendEvents(evs); allEvents(); exportJSON(); importJSON(s) }
  export class LocalStore  { /* 同介面，IndexedDB 實作 */ }
  export async function openStore(indexedDBFactory) // 有 IDB 回 LocalStore，否則回 MemoryStore
  ```

**規格 §10.1 的硬性要求**：事件的全域唯一鍵是 **`(d, n)`**（裝置 id + 該裝置的單調遞增序號），**不得用 `(i, t)`**——時戳只到秒會碰撞，且無法區分「同一題連續作答兩次」與「重複的同一筆事件」。

**儲存事件而非分數**的三個理由（規格 §10.1）：演算法調整後可重放歷史；多裝置合併只是取聯集、永不衝突；支援學習分析。

- [ ] **Step 1: 寫失敗的測試**

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { makeEvent, mergeEvents, MemoryStore } from '../../app/core/store.js';

test('事件使用短鍵，含裝置 id 與序號', () => {
  const e = makeEvent('a3f9', 1482, 'conj:かきます:masu2te', 3, 2400, 'text', 1757500000);
  assert.deepEqual(e, { d: 'a3f9', n: 1482, i: 'conj:かきます:masu2te',
                        t: 1757500000, g: 3, r: 2400, m: 'text' });
});

test('合併以 (d,n) 去重，而非 (i,t)', () => {
  const same = { d: 'a', n: 1, i: 'x', t: 100, g: 3, r: 0, m: 'text' };
  const dupe = { ...same };
  assert.equal(mergeEvents([same], [dupe]).length, 1, '同一 (d,n) 應去重');

  // 同一題、同一秒、不同裝置 → 兩筆都必須保留
  const devA = { d: 'a', n: 1, i: 'x', t: 100, g: 3, r: 0, m: 'text' };
  const devB = { d: 'b', n: 1, i: 'x', t: 100, g: 1, r: 0, m: 'text' };
  assert.equal(mergeEvents([devA], [devB]).length, 2);

  // 同一裝置、同一題、同一秒、不同序號 → 連續作答兩次，都必須保留
  const n1 = { d: 'a', n: 1, i: 'x', t: 100, g: 1, r: 0, m: 'text' };
  const n2 = { d: 'a', n: 2, i: 'x', t: 100, g: 3, r: 0, m: 'text' };
  assert.equal(mergeEvents([n1], [n2]).length, 2);
});

test('合併結果依時間排序', () => {
  const out = mergeEvents(
    [{ d: 'a', n: 2, i: 'x', t: 200, g: 3, r: 0, m: 'text' }],
    [{ d: 'a', n: 1, i: 'x', t: 100, g: 3, r: 0, m: 'text' }]);
  assert.deepEqual(out.map((e) => e.t), [100, 200]);
});

test('MemoryStore 追加與讀取', async () => {
  const s = new MemoryStore();
  await s.appendEvents([makeEvent('a', 1, 'x', 3, 100, 'text', 1000)]);
  await s.appendEvents([makeEvent('a', 2, 'y', 1, 200, 'text', 2000)]);
  const all = await s.allEvents();
  assert.equal(all.length, 2);
});

test('匯出後匯入還原（含去重，不會因重複匯入而膨脹）', async () => {
  const s = new MemoryStore();
  await s.appendEvents([makeEvent('a', 1, 'x', 3, 100, 'text', 1000)]);
  const json = await s.exportJSON();
  await s.importJSON(json);
  await s.importJSON(json);
  assert.equal((await s.allEvents()).length, 1, '重複匯入不得產生重複事件');
});
```

- [ ] **Step 2: 執行確認失敗** — `node --test tests/app/test_store.js`

- [ ] **Step 3: 實作**

```js
export function makeEvent(deviceId, seq, itemId, grade, rtMs, mode, nowSec) {
  return { d: deviceId, n: seq, i: itemId, t: nowSec, g: grade, r: rtMs, m: mode };
}

/** 規格 §10.1：全域唯一鍵為 (d,n)。事件不可變，合併即取聯集，永不衝突。 */
export function mergeEvents(a, b) {
  const seen = new Map();
  for (const e of [...a, ...b]) seen.set(`${e.d}#${e.n}`, e);
  return [...seen.values()].sort((x, y) => x.t - y.t || x.n - y.n);
}

export class MemoryStore {
  constructor() { this._events = []; }
  async appendEvents(evs) { this._events = mergeEvents(this._events, evs); }
  async allEvents() { return [...this._events]; }
  async exportJSON() { return JSON.stringify({ version: 1, events: this._events }); }
  async importJSON(s) {
    const parsed = JSON.parse(s);
    await this.appendEvents(parsed.events || []);
  }
}

const DB_NAME = 'japanese-practice';
const STORE = 'events';

export class LocalStore {
  constructor(db) { this._db = db; }

  static async open(idbFactory) {
    const db = await new Promise((resolve, reject) => {
      const req = idbFactory.open(DB_NAME, 1);
      req.onupgradeneeded = () => {
        // 主鍵為 [d, n]，直接由 IndexedDB 保證唯一，不需應用層去重
        req.result.createObjectStore(STORE, { keyPath: ['d', 'n'] });
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    return new LocalStore(db);
  }

  _tx(mode) { return this._db.transaction(STORE, mode).objectStore(STORE); }

  async appendEvents(evs) {
    await new Promise((resolve, reject) => {
      const tx = this._db.transaction(STORE, 'readwrite');
      const os = tx.objectStore(STORE);
      for (const e of evs) os.put(e);   // put 而非 add：重複 (d,n) 覆寫而非拋錯
      tx.oncomplete = resolve;
      tx.onerror = () => reject(tx.error);
    });
  }

  async allEvents() {
    const rows = await new Promise((resolve, reject) => {
      const req = this._tx('readonly').getAll();
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
    return rows.sort((a, b) => a.t - b.t || a.n - b.n);
  }

  async exportJSON() { return JSON.stringify({ version: 1, events: await this.allEvents() }); }
  async importJSON(s) { await this.appendEvents(JSON.parse(s).events || []); }
}

export async function openStore(indexedDBFactory) {
  if (indexedDBFactory) {
    try { return await LocalStore.open(indexedDBFactory); }
    catch { /* 私密視窗或封鎖站台資料時會失敗，退回記憶體 */ }
  }
  return new MemoryStore();
}
```

**`LocalStore` 無法在 Node 測試**（沒有 IndexedDB），由 Task 14 的手動驗收涵蓋。`MemoryStore` 與 `mergeEvents` 承擔全部可自動測試的邏輯，這是刻意的切分。

- [ ] **Step 4: 執行確認通過** — 5 tests PASS

- [ ] **Step 5: 提交** — `feat(app): 事件日誌儲存與多裝置合併`

---

## Task 11: 排程器（`core/scheduler.js`）

**Files:** Create `app/core/scheduler.js`, `tests/app/test_scheduler.js`

**Interfaces:**
- Consumes: `app/core/srs.js`、`app/core/concepts.js`
- Produces:
  ```js
  export function buildConceptStates(itemStates, items) // → Map<conceptId, {R, reps}>
  export function priority(item, itemStates, conceptStates)  // → number
  export function pickItems(items, itemStates, conceptStates, count, rng) // → Item[]
  // rng 為 () => [0,1) 的函式，測試時注入固定序列以取得決定性結果
  ```

**規格 §8 的優先度公式**：
```
priority = (1 - R_item) × max over c∈covers (1 - R_concept) × freshness
```
- **加權隨機抽樣**（權重 `priority^2`），**不是排序取前 N**——純排序會讓每次練習都是同幾題，使用者會背下順序而非內容。
- 未練過的題目 `R = 0`（最高優先），但**新題比例上限 30%／session**——這條必須實作，否則首次使用時新題會無上限湧入，使用者一次面對上千道沒見過的題目。

- [ ] **Step 1: 寫失敗的測試**

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { buildConceptStates, priority, pickItems } from '../../app/core/scheduler.js';

const mkItem = (id, covers) => ({ id, covers, requires_lesson: 1, engine: 'recall' });

test('概念狀態由涵蓋它的題目聚合而來', () => {
  const items = [mkItem('i1', ['w:a']), mkItem('i2', ['w:a', 'w:b'])];
  const st = new Map([['i1', { R: 0.2, reps: 3 }], ['i2', { R: 0.8, reps: 1 }]]);
  const cs = buildConceptStates(st, items);
  assert.ok(cs.has('w:a') && cs.has('w:b'));
  assert.ok(cs.get('w:a').R > 0.2 && cs.get('w:a').R < 0.8);
});

test('生疏的題目優先度較高', () => {
  const items = [mkItem('i1', ['w:a'])];
  const cs = new Map([['w:a', { R: 0.5, reps: 2 }]]);
  const weak = priority(items[0], new Map([['i1', { R: 0.1, reps: 5 }]]), cs);
  const strong = priority(items[0], new Map([['i1', { R: 0.95, reps: 5 }]]), cs);
  assert.ok(weak > strong);
});

test('概念生疏會拉高所有涵蓋它的題目（跨題型傳導）', () => {
  const it = mkItem('i1', ['g:X']);
  const st = new Map([['i1', { R: 0.5, reps: 2 }]]);
  const weakConcept = priority(it, st, new Map([['g:X', { R: 0.1, reps: 9 }]]));
  const strongConcept = priority(it, st, new Map([['g:X', { R: 0.9, reps: 9 }]]));
  assert.ok(weakConcept > strongConcept);
});

test('未練過的題目優先度最高', () => {
  const it = mkItem('new', ['w:z']);
  assert.ok(priority(it, new Map(), new Map()) > 0);
});

test('pickItems 為加權隨機而非排序取前 N', () => {
  const items = [mkItem('a', ['w:a']), mkItem('b', ['w:b']), mkItem('c', ['w:c'])];
  const st = new Map([
    ['a', { R: 0.1, reps: 5 }], ['b', { R: 0.5, reps: 5 }], ['c', { R: 0.9, reps: 5 }]]);
  const cs = buildConceptStates(st, items);
  // rng 回傳接近 1 → 抽到權重較低者，證明不是單純排序
  const late = pickItems(items, st, cs, 1, () => 0.999);
  const early = pickItems(items, st, cs, 1, () => 0.001);
  assert.notEqual(late[0].id, early[0].id, '不同亂數應抽到不同題目');
});

test('不重複抽到同一題', () => {
  const items = [mkItem('a', ['w:a']), mkItem('b', ['w:b'])];
  const picked = pickItems(items, new Map(), new Map(), 2, () => 0.5);
  assert.equal(new Set(picked.map((i) => i.id)).size, 2);
});

test('要求數量超過可用題數時回傳全部，不無限迴圈', () => {
  const items = [mkItem('a', ['w:a'])];
  assert.equal(pickItems(items, new Map(), new Map(), 10, () => 0.5).length, 1);
});
```

- [ ] **Step 2: 執行確認失敗** — `node --test tests/app/test_scheduler.js`

- [ ] **Step 3: 實作**

```js
const ALPHA = 2;          // 權重指數：priority^ALPHA
const UNSEEN_R = 0;       // 未練過視為完全生疏

export function buildConceptStates(itemStates, items) {
  const acc = new Map();
  for (const it of items) {
    const st = itemStates.get(it.id);
    if (!st) continue;
    const w = Math.log(1 + (st.reps ?? 0)) || 0.0001;
    for (const c of it.covers || []) {
      const cur = acc.get(c) || { sum: 0, w: 0, reps: 0 };
      cur.sum += st.R * w; cur.w += w; cur.reps += st.reps ?? 0;
      acc.set(c, cur);
    }
  }
  const out = new Map();
  for (const [c, v] of acc) out.set(c, { R: v.w > 0 ? v.sum / v.w : UNSEEN_R, reps: v.reps });
  return out;
}

/** 規格 §8：(1-R_item) × max(1-R_concept) × freshness */
export function priority(item, itemStates, conceptStates, seenThisSession = new Set()) {
  const itemR = itemStates.get(item.id)?.R ?? UNSEEN_R;
  // 初始值必須是 0：(1-R) 的值域上界就是 1，若初始化為 1 則 max 恆等於 1，
  // 概念熟悉度對優先度的影響會完全歸零——規格 §8 的「跨題型傳導」會靜默失能。
  let conceptGap = 0;
  for (const c of item.covers || []) {
    const r = conceptStates.get(c)?.R ?? UNSEEN_R;
    conceptGap = Math.max(conceptGap, 1 - r);
  }
  if (!(item.covers || []).length) conceptGap = 1;   // 無概念標註者不因此被壓到 0
  const freshness = seenThisSession.has(item.id) ? 0.05 : 1;
  return Math.max(1e-6, (1 - itemR)) * conceptGap * freshness;
}

export function pickItems(items, itemStates, conceptStates, count, rng = Math.random) {
  const pool = [...items];
  const picked = [];
  const seen = new Set();
  while (picked.length < count && pool.length > 0) {
    const weights = pool.map((it) =>
      Math.pow(priority(it, itemStates, conceptStates, seen), ALPHA));
    const total = weights.reduce((a, b) => a + b, 0);
    let target = rng() * total;
    let idx = pool.length - 1;
    for (let k = 0; k < pool.length; k++) {
      target -= weights[k];
      if (target <= 0) { idx = k; break; }
    }
    const [chosen] = pool.splice(idx, 1);
    picked.push(chosen);
    seen.add(chosen.id);
  }
  return picked;
}
```

- [ ] **Step 4: 執行確認通過** — 7 tests PASS

- [ ] **Step 5: 提交** — `feat(app): 概念層加權抽樣排程器`

---

## Task 12: 作答評分與 grade 判定（`core/grading.js`）

**Files:** Create `app/core/grading.js`, `tests/app/test_grading.js`

**Interfaces:**
- Consumes: `app/core/normalize.js`
- Produces:
  ```js
  export function gradeAnswer(input, item, rtMs, medianRtMs, usedHint) // → {correct, grade}
  ```

**規格 §7.4 的自動判定**（使用者不需手動評分，自評卡已從設計移除）：

| 條件 | grade |
|---|---|
| 答對，反應時間 < 中位數 × 0.6 | 4 簡單 |
| 答對 | 3 普通 |
| 答對，但反應時間偏長（> 中位數 × 2）或用過提示 | 2 困難 |
| 答錯 | 1 重來 |

- [ ] **Step 1: 寫失敗的測試**

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { gradeAnswer } from '../../app/core/grading.js';

const item = { answer: 'きります', alternatives: ['切ります'] };

test('答錯一律 grade 1', () => {
  const r = gradeAnswer('たべます', item, 1000, 3000, false);
  assert.equal(r.correct, false);
  assert.equal(r.grade, 1);
});

test('答對且很快 → grade 4', () => {
  assert.equal(gradeAnswer('きります', item, 1000, 3000, false).grade, 4);
});

test('答對、速度普通 → grade 3', () => {
  assert.equal(gradeAnswer('きります', item, 3000, 3000, false).grade, 3);
});

test('答對但很慢 → grade 2', () => {
  assert.equal(gradeAnswer('きります', item, 9000, 3000, false).grade, 2);
});

test('用過提示即使答對也只給 grade 2', () => {
  assert.equal(gradeAnswer('きります', item, 500, 3000, true).grade, 2);
});

test('alternatives 亦視為答對', () => {
  assert.equal(gradeAnswer('切ります', item, 3000, 3000, false).correct, true);
});

test('沒有中位數可參考時（首次練該題型）給 grade 3', () => {
  assert.equal(gradeAnswer('きります', item, 1000, null, false).grade, 3);
});
```

- [ ] **Step 2: 執行確認失敗** — `node --test tests/app/test_grading.js`

- [ ] **Step 3: 實作**

```js
import { isCorrect } from './normalize.js';

const FAST = 0.6;   // 中位數的倍率，低於此視為「簡單」
const SLOW = 2.0;   // 高於此視為「困難」

export function gradeAnswer(input, item, rtMs, medianRtMs, usedHint) {
  const correct = isCorrect(input, item.answer, item.alternatives || []);
  if (!correct) return { correct: false, grade: 1 };
  if (usedHint) return { correct: true, grade: 2 };
  if (!medianRtMs || medianRtMs <= 0) return { correct: true, grade: 3 };
  if (rtMs < medianRtMs * FAST) return { correct: true, grade: 4 };
  if (rtMs > medianRtMs * SLOW) return { correct: true, grade: 2 };
  return { correct: true, grade: 3 };
}
```

- [ ] **Step 4: 執行確認通過** — 7 tests PASS

- [ ] **Step 5: 提交** — `feat(app): 作答評分與 grade 自動判定`

---

## Task 13: 練習畫面、設定與儀表板（`ui/`）

**Files:** Create `app/ui/session.js`, `app/ui/settings.js`, `app/ui/dashboard.js`

**Interfaces:**
- Consumes: 全部 `core/`、`generators/`
- Produces:
  ```js
  // session.js
  export function renderSession(host, deps)   // deps: {items, store, itemStates, conceptStates, settings, onDone}
  // settings.js
  export function renderSettings(host, settings, onChange)
  export const DEFAULT_SETTINGS = { minLesson: 1, maxLesson: 15, engines: ['recall','transform'], sessionSize: 20 };
  export function loadSettings(storageLike)   // 讀 localStorage，失敗回預設
  export function saveSettings(storageLike, s)
  // dashboard.js
  export function renderDashboard(host, skillScores, counts)
  ```

**UI 層的設計約束**：所有判斷邏輯都在 `core/`，`ui/` 只做 DOM 與事件。這讓 `ui/` 不需要測試框架——Task 14 的手動驗收涵蓋它。

**練習畫面必須有的行為**：
- 顯示 `item.prompt.text` 與 `item.prompt.hint`
- 輸入框設 `lang="ja"`、`autocorrect="off"`、`autocapitalize="off"`、`spellcheck="false"`（規格 §9，避免 iOS 幫倒忙）
- 送出後顯示對錯與正解、`item.source_ref`（規格 §17 要求每題提供課本出處）
- 答錯時提供「**我這樣寫也對**」按鈕（規格 §9.2.1 的安全網）：按下後本次改判答對，並把使用者的答案寫入該題的 `alternatives`（存於使用者層資料，與 `data/corrections.json` 分開）
- 記錄反應時間（從題目顯示到送出）
- 每題作答後呼叫 `store.appendEvents([...])`

**設定畫面**：課次範圍（1~15 的起迄）、題型開關（recall／transform）、每次題數。存於 `localStorage`，讀取失敗時回預設值（私密視窗會拋錯）。

**儀表板**：六類技能的熟悉度長條（規格 §7.6），未練過的技能顯示「尚未練習」而非 0%，並顯示各類的題數。

- [ ] **Step 1: 實作 `app/ui/session.js`**

以下是必須遵守的骨架（DOM 細節可自行調整，但**結構與呼叫關係不得改**）：

```js
import { gradeAnswer } from '../core/grading.js';
import { makeEvent } from '../core/store.js';

const INPUT_ATTRS = 'lang="ja" autocorrect="off" autocapitalize="off" spellcheck="false" autocomplete="off"';

export function renderSession(host, deps) {
  const { items, store, settings, deviceId, nextSeq, medianRt, onDone } = deps;
  let idx = 0, shownAt = 0, usedHint = false;

  function showItem() {
    if (idx >= items.length) return onDone();
    const it = items[idx];
    usedHint = false;
    host.innerHTML = `
      <div class="prompt">${escapeHtml(it.prompt.text)}</div>
      <div class="hint">${escapeHtml(it.prompt.hint || '')}</div>
      <input id="ans" type="text" ${INPUT_ATTRS}>
      <button id="submit">送出</button>
      <button id="hint">看提示</button>
      <div class="progress">${idx + 1} / ${items.length}</div>`;
    shownAt = Date.now();
    host.querySelector('#ans').focus();
    host.querySelector('#submit').onclick = submit;
    host.querySelector('#hint').onclick = () => { usedHint = true; revealHint(it); };
    host.querySelector('#ans').onkeydown = (e) => { if (e.key === 'Enter') submit(); };
  }

  async function submit() {
    const it = items[idx];
    const input = host.querySelector('#ans').value;
    const rt = Date.now() - shownAt;
    // 判定一律交給 core，ui 不得自行比對字串
    const { correct, grade } = gradeAnswer(input, it, rt, medianRt(it.engine), usedHint);
    await store.appendEvents([
      makeEvent(deviceId, nextSeq(), it.id, grade, rt, 'text', Math.floor(Date.now() / 1000)),
    ]);
    showResult(it, input, correct);
  }

  function showResult(it, input, correct) {
    host.innerHTML = `
      <div class="verdict">${correct ? '正確' : '再看一次'}</div>
      <div class="answer">正解：${escapeHtml(it.answer)}</div>
      <div class="source">出處：${escapeHtml(it.source_ref)}</div>
      ${correct ? '' : '<button id="also-ok">我這樣寫也對</button>'}
      <button id="next">下一題</button>`;
    host.querySelector('#next').onclick = () => { idx += 1; showItem(); };
    const alsoOk = host.querySelector('#also-ok');
    if (alsoOk) alsoOk.onclick = () => deps.acceptAlternative(it.id, input);
  }

  function revealHint(it) {
    host.querySelector('.hint').textContent = `${it.prompt.hint || ''}（開頭：${it.answer.slice(0, 1)}）`;
  }

  showItem();
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}
```

**注意 `escapeHtml`**：`item.prompt.text` 來自課本資料，雖然不太可能含 HTML，但用 `innerHTML` 組字串時一律轉義是正確做法。

- [ ] **Step 1b: 實作 `app/ui/settings.js` 與 `app/ui/dashboard.js`**

依上述行為需求撰寫。**關鍵是 `ui/` 內不得有任何判斷邏輯**——對錯判定呼叫 `gradeAnswer`、選題呼叫 `pickItems`、熟悉度呼叫 `replay` + `aggregateSkills`。

- [ ] **Step 2: 驗證 `ui/` 沒有洩漏邏輯**

```bash
grep -nE "isCorrect|normalizeAnswer|Math\.pow|retrievability|9 \* " app/ui/*.js && echo "✗ UI 層出現核心邏輯" || echo "✓ UI 層乾淨"
```
Expected: `✓ UI 層乾淨`

- [ ] **Step 3: 驗證輸入框屬性齊備**

```bash
grep -c 'lang="ja"' app/ui/session.js
grep -c 'autocapitalize' app/ui/session.js
grep -c 'spellcheck' app/ui/session.js
```
Expected: 每項至少 1

- [ ] **Step 4: 提交** — `feat(app): 練習畫面、範圍設定與技能儀表板`

---

## Task 14: 組裝、入口頁與端到端驗收

**Files:** Create `index.html`, `app/main.js`, `docs/superpowers/plans/2026-09-20-phase1-acceptance-report.md`

**Interfaces:**
- Consumes: 全部模組
- Produces: 可在瀏覽器開啟的完整應用

- [ ] **Step 1: 建立 `index.html` 與 `app/main.js`**

`index.html` 需求：
- `<meta name="viewport" content="width=device-width, initial-scale=1">`（手機可用）
- `<script type="module" src="app/main.js"></script>`
- 三個容器：`#settings`、`#session`、`#dashboard`

`app/main.js` 的啟動流程：
1. `loadSettings(localStorage)` 取得課次範圍與題型
2. 以 `fetch` 載入該範圍的 `data/lessons/NN.json` 與 `data/verbs.json`
3. `buildIndex` → 以 `recall.generate` 與 `transform.generate` 展開題目（**懶生成，不預先寫成檔案**，規格 §5.4）
4. 依 `requires_lesson <= settings.maxLesson` 過濾
5. `openStore(window.indexedDB)` → `allEvents()` → `replay()` 取得 `itemStates`
6. `buildConceptStates()` → `pickItems()` 取本次題目
7. 渲染三個區塊

- [ ] **Step 2: 啟動本機伺服器並在電腦瀏覽器驗收**

```bash
python3 -m http.server 8000
```

開 `http://localhost:8000`，逐項確認：
- [ ] 能完成一次含**單字題與動詞變化題**的練習（規格 Phase 1 驗收條件）
- [ ] 答對／答錯都有正確回饋，並顯示正解與 `source_ref`
- [ ] 儀表板顯示**六類技能**的熟悉度
- [ ] **關閉瀏覽器再開，進度仍在**（IndexedDB 生效）
- [ ] 設定課次範圍為 1~10 後，**て形題目不再出現**（`requires_lesson=14` 被正確過濾）

- [ ] **Step 3: 手機驗收**

用手機連同一 Wi-Fi 開 `http://<電腦區域網路IP>:8000`：
- [ ] 版面在手機寬度可用
- [ ] 日文輸入法可正常輸入，輸入框未被自動修正干擾

- [ ] **Step 4: 驗證「答錯的題目在後續 session 出現機率明顯提高」**

這是規格 Phase 1 的驗收條件之一，需要實測而非推論：

```bash
node -e "
(async()=>{
  const {pickItems,buildConceptStates}=await import('./app/core/scheduler.js');
  const {replay}=await import('./app/core/srs.js');
  const now=Math.floor(Date.now()/1000);
  const items=[...Array(20)].map((_,i)=>({id:'i'+i,covers:['w:'+i],requires_lesson:1}));
  // i0 答錯三次，其餘答對三次
  const evs=[];
  let n=0;
  for(const it of items){
    for(let k=0;k<3;k++) evs.push({d:'a',n:n++,i:it.id,t:now-86400*(3-k),g:it.id==='i0'?1:3,r:0,m:'text'});
  }
  const st=replay(evs,now);
  const cs=buildConceptStates(st,items);
  let hit=0; const TRIALS=2000;
  for(let t=0;t<TRIALS;t++){ if(pickItems(items,st,cs,5,Math.random).some(x=>x.id==='i0')) hit++; }
  const rate=hit/TRIALS, baseline=5/20;
  console.log('答錯題被選中率', rate.toFixed(3), '；均勻分布基準', baseline.toFixed(3));
  console.log(rate > baseline*1.5 ? '✓ 明顯提高' : '✗ 未達預期');
})();
"
```
Expected: `✓ 明顯提高`

- [ ] **Step 5: 撰寫驗收報告**

`docs/superpowers/plans/2026-09-20-phase1-acceptance-report.md`，內容：
- 生成的題目總數（對照題／變換題各幾題）
- 全部自動測試結果
- Step 2~4 每一項的實際結果，**誠實列出不如預期之處**
- 已知限制與其影響範圍

- [ ] **Step 6: 提交**

```bash
git add index.html app/ docs/superpowers/plans/2026-09-20-phase1-acceptance-report.md
git commit -m "$(cat <<'EOF'
feat(app): Phase 1 組裝、入口頁與驗收報告

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QazTpwM3ApzPa47zWjy26D
EOF
)"
```

---

## Phase 1 完成定義

全部達成才算完成：

- [ ] `node --test "tests/app/*.js"` 全數通過
- [ ] 能在**電腦與手機**瀏覽器完成一次含單字題與動詞變化題的練習
- [ ] 儀表板顯示規格 §7.6 的**六類技能**熟悉度
- [ ] 關閉瀏覽器後進度保留（IndexedDB）
- [ ] 答錯的題目在後續 session 出現機率明顯提高（Task 14 Step 4 實測通過）
- [ ] 課次範圍設定能正確過濾 `requires_lesson` 超出範圍的題目
- [ ] 匯出／匯入 JSON 可還原進度，且重複匯入不會產生重複事件
- [ ] `app/core/` 與 `app/lang/` 無任何 DOM 呼叫
- [ ] 無 npm 相依、無 build step

## 不屬於 Phase 1 的工作

- `substitute`（代入題）與 `cloze`（挖空題）引擎 → Phase 2
- `data/concepts.json`（約 70 個文法／助詞概念的人工定義）→ Phase 2
- 聽力呈現修飾、單字循環播放器、振假名顯示、PWA → Phase 2
- Gitea 同步（`GiteaStore`）→ Phase 3
- 插畫關聯 → Phase 4
- `jp2zh` 對照題（給日文答中文）→ Phase 2，需選擇題 UI

## 已知風險

| 風險 | 影響 | 緩解 |
|---|---|---|
| `data/verbs.json` 分類錯誤 | 變化題答案錯誤，教錯使用者 | Task 3 的測試與課本 29 筆標記交叉驗證；i 段動詞逐一人工核對 |
| iOS Safari 的 IndexedDB 在私密視窗不可用 | 進度不保存 | `openStore` 退回 `MemoryStore`，Task 14 手動確認不會崩潰 |
| 反應時間中位數在初期樣本不足 | grade 判定偏保守 | `gradeAnswer` 在無中位數時固定給 3，不猜 |
| FSRS 預設權重未必貼合個人 | 間隔略偏 | 事件日誌保留原始資料，日後可重放重算 |
