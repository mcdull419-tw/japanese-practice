# Phase 2a 題型核心 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 補齊 substitute（代入）、cloze（挖空）、quantity（數量）三類題目與其所需的語言規則模組與人工標註資料，使需求 #3 #4 #5 #7 #11 #12 #13 可用。

**Architecture:** 沿用 Phase 1 既有分層——`lang/` 放純函式語言規則，`generators/` 把素材展開成 Item，`core/` 負責索引、排程、評分，`ui/` 只做 DOM。**不新增 `app/engines/` 層**（規格 §13 決定 1）：2a 的新題型仍是打字作答，塞得進現有的 `prompt`／`answer`／`alternatives` 形狀。三份新的人工維護資料檔（`concepts.json`／`particles.json`／`adjectives.json`）一律先以 `tools/draft/` 的腳本產草稿再人工校對，並各自配一組漂移偵測測試。

**Tech Stack:** Vanilla JS ES modules（無 build step）、`node --test`（Node 內建）、Python 3 標準函式庫（僅用於 `tools/draft/` 的離線草稿產生，不部署）。

**Spec:** `docs/superpowers/specs/2026-09-10-japanese-practice-design.md`（Phase 2a 範圍與六項實作決定見 §13）

## Global Constraints

- **無 build step、無第三方依賴。** 瀏覽器端一律 ES modules 直接載入；測試一律 `node --test`，不得引入測試框架。
- **`tools/` 只用 Python 3 標準函式庫**，且不部署到網站（規格 §11）。
- **Item `id` 必須決定性**（規格 §5.3）：由「生成器名 : 素材鍵 : 參數」組成，禁止亂數與時間戳。同一份語料重新生成必須得到同一組 id，否則 SRS 歷史全部失效。
- **`requires_lesson` = max(素材課次, 形態／句型解鎖課次)**（規格 §5.3），這是範圍過濾的依據。
- **概念技能由 ID 前綴推導**，`core/concepts.js` 的 `skillOf()` 是唯一真相來源；資料檔不得自帶 `skills` 欄位（規格 §13 決定 2）。
- **判斷邏輯不得寫進 `ui/`。** 對錯比對走 `core/normalize.js`，評分走 `core/grading.js`。
- **`app/core/` 與 `app/lang/` 不得出現 `document.` 或 `window.`**（Phase 1 已以 grep 驗收，須維持）。
- **純函式模組必須有測試**（規格 §11）：`adjective.js`、`numbers.js`、`counters.js` 的測試必須涵蓋不規則形。
- **全部註解與提交訊息使用繁體中文**，與既有程式碼一致。
- 提交訊息結尾附：
  ```
  Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
  ```

## 檔案結構

| 檔案 | 責任 |
|---|---|
| `app/lang/adjective.js` | い／な 形容詞變化（純函式） |
| `app/lang/numbers.js` | 數字、時刻、分、日期、月份讀音（純函式） |
| `app/lang/counters.js` | 量詞音變（純函式） |
| `app/generators/quantity.js` | 數量題（`engine: 'recall'`、`skills: ['數量']`） |
| `app/generators/cloze.js` | 助詞挖空與詞組挖空 |
| `app/generators/substitute.js` | 練習Ａ代入表與練習Ｂ變換 |
| `app/core/conceptdefs.js` | 載入並查詢 `concepts.json`，含 pattern→概念反查 |
| `data/concepts.json` | 文法／助詞概念定義（人工維護） |
| `data/particles.json` | 助詞用法標註（人工維護） |
| `data/adjectives.json` | 形容詞い／な 分類（人工維護） |
| `tools/draft/` | 三份資料檔的草稿產生腳本（離線、不部署） |

修改：`app/core/data.js`（暴露 patterns／drills）、`app/generators/transform.js`（擴充形容詞）、`app/main.js`、`app/ui/settings.js`（接線與技能過濾）。

---

### Task 1: `buildIndex` 暴露 patterns 與 drills

`core/data.js` 目前只把 `vocab` 與 `sentences` 攤平（Phase 1 只用得到這兩者）。substitute 需要 `patterns` 與 `drills`，且兩者都必須帶上課次。

**Files:**
- Modify: `app/core/data.js:13-21`
- Test: `tests/app/test_data.js`

**Interfaces:**
- Produces: `buildIndex(lessonsMap)` → `{ vocab, sentences, patterns, drills }`，其中 `patterns[]` 與 `drills[]` 的每個元素都多一個 `lesson` 欄位（數字），其餘欄位原樣保留。

- [ ] **Step 1: 寫失敗的測試**

加到 `tests/app/test_data.js` 末尾：

```js
test('buildIndex 攤平 patterns 與 drills 並帶上課次', () => {
  const lessons = new Map([
    [7, {
      vocab: [], sentences: [],
      patterns: [{ id: 'L07-A1', template: '{S}は{T}で ごはんを 食べます。', slots: { S: ['日本人'], T: ['はし'] }, rows: [[0, 0]], requires_lesson: 7 }],
      drills: [{ id: 'L07-B1', items: ['手紙を 書きます'], model_answer: 'はしで ごはんを 食べます。', model_cue: 'ごはんを 食べます' }],
    }],
  ]);
  const idx = buildIndex(lessons);
  assert.equal(idx.patterns.length, 1);
  assert.equal(idx.patterns[0].id, 'L07-A1');
  assert.equal(idx.patterns[0].lesson, 7);
  assert.equal(idx.patterns[0].template, '{S}は{T}で ごはんを 食べます。');
  assert.equal(idx.drills.length, 1);
  assert.equal(idx.drills[0].lesson, 7);
  assert.equal(idx.drills[0].model_answer, 'はしで ごはんを 食べます。');
});

test('buildIndex 對缺少 patterns／drills 的課次不炸', () => {
  const idx = buildIndex(new Map([[1, { vocab: [], sentences: [] }]]));
  assert.deepEqual(idx.patterns, []);
  assert.deepEqual(idx.drills, []);
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_data.js`
Expected: FAIL，`idx.patterns` 為 `undefined`（`Cannot read properties of undefined (reading 'length')`）

- [ ] **Step 3: 實作**

把 `app/core/data.js` 的 `buildIndex` 改成：

```js
export function buildIndex(lessonsMap) {
  const vocab = [];
  const sentences = [];
  const patterns = [];
  const drills = [];
  for (const [n, data] of [...lessonsMap.entries()].sort((a, b) => a[0] - b[0])) {
    for (const v of data.vocab || []) vocab.push({ ...v, lesson: n });
    for (const s of data.sentences || []) sentences.push({ ...s, lesson: n });
    for (const p of data.patterns || []) patterns.push({ ...p, lesson: n });
    for (const d of data.drills || []) drills.push({ ...d, lesson: n });
  }
  return { vocab, sentences, patterns, drills };
}
```

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test "tests/app/*.js"`
Expected: 全部 PASS（既有 70 個 ＋ 新增 2 個）

- [ ] **Step 5: 提交**

```bash
git add app/core/data.js tests/app/test_data.js
git commit -m "feat(data): buildIndex 攤平 patterns 與 drills，供代入題使用

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 2: `lang/adjective.js` 形容詞變化

鏡射 `lang/conjugation.js` 的形狀（`FORMS`／`FORM_LESSON`／單一變化函式）。課本第 8 課教形容詞現在式、第 12 課教過去式（已核對 `data/lessons/08.json` 與 `12.json` 的 `grammar[].title`）；て形與副詞形第 16 課才教，一併寫完但以 `requires_lesson` 擋在 1~15 範圍之外——與 `conjugation.js` 收錄可能形、意向形的作法一致。

回傳**完整的禮貌形**（含 です／じゃありません），因為那才是課本操練、也是使用者要打的字串；這與 `conjugate()` 回傳完整ます形一致。

**Files:**
- Create: `app/lang/adjective.js`
- Test: `tests/app/test_adjective.js`

**Interfaces:**
- Produces:
  - `FORMS: string[]` = `['plain','neg','past','pastneg','te','adverb']`
  - `FORM_LESSON: Record<string, number>` = `{ plain:8, neg:8, past:12, pastneg:12, te:16, adverb:16 }`
  - `conjugateAdj(citation: string, type: 'i'|'na', form: string) → string`（主要答案）
  - `conjugateAdjAlts(citation: string, type: 'i'|'na', form: string) → string[]`（其他可接受寫法，不含主要答案）
  - 參數不合法時 `throw`（與 `conjugate()` 同慣例）

- [ ] **Step 1: 寫失敗的測試**

Create `tests/app/test_adjective.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { conjugateAdj, conjugateAdjAlts, FORMS, FORM_LESSON } from '../../app/lang/adjective.js';

test('い形容詞四變化', () => {
  assert.equal(conjugateAdj('大きい', 'i', 'plain'), '大きいです');
  assert.equal(conjugateAdj('大きい', 'i', 'neg'), '大きくないです');
  assert.equal(conjugateAdj('大きい', 'i', 'past'), '大きかったです');
  assert.equal(conjugateAdj('大きい', 'i', 'pastneg'), '大きくなかったです');
});

test('い形容詞て形與副詞形', () => {
  assert.equal(conjugateAdj('大きい', 'i', 'te'), '大きくて');
  assert.equal(conjugateAdj('大きい', 'i', 'adverb'), '大きく');
});

test('いい 是不規則：語幹改用 よ', () => {
  assert.equal(conjugateAdj('いい', 'i', 'plain'), 'いいです');
  assert.equal(conjugateAdj('いい', 'i', 'neg'), 'よくないです');
  assert.equal(conjugateAdj('いい', 'i', 'past'), 'よかったです');
  assert.equal(conjugateAdj('いい', 'i', 'pastneg'), 'よくなかったです');
  assert.equal(conjugateAdj('いい', 'i', 'te'), 'よくて');
  assert.equal(conjugateAdj('いい', 'i', 'adverb'), 'よく');
  assert.notEqual(conjugateAdj('いい', 'i', 'past'), 'いかったです');
});

test('複合形容詞含 いい 時只有語尾變（かっこいい）', () => {
  assert.equal(conjugateAdj('かっこいい', 'i', 'past'), 'かっこよかったです');
});

test('な形容詞四變化', () => {
  assert.equal(conjugateAdj('きれい', 'na', 'plain'), 'きれいです');
  assert.equal(conjugateAdj('きれい', 'na', 'neg'), 'きれいじゃありません');
  assert.equal(conjugateAdj('きれい', 'na', 'past'), 'きれいでした');
  assert.equal(conjugateAdj('きれい', 'na', 'pastneg'), 'きれいじゃありませんでした');
});

test('な形容詞て形與副詞形', () => {
  assert.equal(conjugateAdj('静か', 'na', 'te'), '静かで');
  assert.equal(conjugateAdj('静か', 'na', 'adverb'), '静かに');
});

test('な形容詞的 では 寫法列為可接受', () => {
  assert.deepEqual(conjugateAdjAlts('きれい', 'na', 'neg'), ['きれいではありません']);
  assert.deepEqual(conjugateAdjAlts('きれい', 'na', 'pastneg'), ['きれいではありませんでした']);
});

test('い形容詞的 ありません 寫法列為可接受', () => {
  assert.deepEqual(conjugateAdjAlts('大きい', 'i', 'neg'), ['大きくありません']);
  assert.deepEqual(conjugateAdjAlts('大きい', 'i', 'pastneg'), ['大きくありませんでした']);
});

test('無其他寫法時回傳空陣列', () => {
  assert.deepEqual(conjugateAdjAlts('大きい', 'i', 'past'), []);
  assert.deepEqual(conjugateAdjAlts('静か', 'na', 'te'), []);
});

test('參數不合法時拋錯', () => {
  assert.throws(() => conjugateAdj('大きい', 'i', 'nope'));
  assert.throws(() => conjugateAdj('大きい', 'x', 'past'));
  assert.throws(() => conjugateAdj('大き', 'i', 'past'));  // い形容詞必須以い結尾
});

test('FORM_LESSON 覆蓋全部 FORMS，過去式為第12課', () => {
  for (const f of FORMS) assert.equal(typeof FORM_LESSON[f], 'number');
  assert.equal(FORM_LESSON.plain, 8);
  assert.equal(FORM_LESSON.past, 12);
  assert.equal(FORM_LESSON.te, 16);
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_adjective.js`
Expected: FAIL，`Cannot find module '../../app/lang/adjective.js'`

- [ ] **Step 3: 實作**

Create `app/lang/adjective.js`:

```js
/**
 * い／な 形容詞變化。鏡射 lang/conjugation.js 的形狀（FORMS／FORM_LESSON／單一變化函式）。
 *
 * 回傳完整的禮貌形（含です／じゃありません），不是語幹——課本操練的是
 * 「大きくないです」這個完整形式，使用者要打的也是它，與 conjugate() 回傳
 * 完整ます形一致。
 *
 * て形與副詞形課本第16課才教，超出本專案1~15課的範圍。仍然寫完整，由
 * FORM_LESSON 的 16 擋在範圍之外（同 conjugation.js 收錄可能形的作法）：
 * 日後擴充課次範圍時不需要改程式。
 */
export const FORMS = ['plain', 'neg', 'past', 'pastneg', 'te', 'adverb'];

/** 各形態在課本中首次出現的課次（已核對 L08／L12 的 grammar 標題）。 */
export const FORM_LESSON = { plain: 8, neg: 8, past: 12, pastneg: 12, te: 16, adverb: 16 };

const I_SUFFIX = { plain: 'いです', neg: 'くないです', past: 'かったです',
  pastneg: 'くなかったです', te: 'くて', adverb: 'く' };

const NA_SUFFIX = { plain: 'です', neg: 'じゃありません', past: 'でした',
  pastneg: 'じゃありませんでした', te: 'で', adverb: 'に' };

const I_ALT = { neg: 'くありません', pastneg: 'くありませんでした' };
const NA_ALT = { neg: 'ではありません', pastneg: 'ではありませんでした' };

/**
 * いい 的不規則：除了 plain 之外一律改用 よ 語幹（よかった／よくない）。
 * かっこいい、きもちいい 這類複合詞同樣只有末尾的いい 變化，因此比對的是
 * 「以いい結尾」而非「等於いい」。
 */
function iStem(citation) {
  if (citation.endsWith('いい')) return citation.slice(0, -2) + 'よ';
  return citation.slice(0, -1);
}

function check(citation, type, form) {
  if (typeof citation !== 'string' || citation.length === 0) {
    throw new Error(`adjective: 需要非空字串，收到 ${JSON.stringify(citation)}`);
  }
  if (type !== 'i' && type !== 'na') {
    throw new Error(`adjective: 未知的 type ${JSON.stringify(type)}`);
  }
  if (!FORMS.includes(form)) {
    throw new Error(`adjective: 未知的 form ${JSON.stringify(form)}`);
  }
  if (type === 'i' && !citation.endsWith('い')) {
    throw new Error(`adjective: い形容詞須以い結尾，收到 ${JSON.stringify(citation)}`);
  }
}

export function conjugateAdj(citation, type, form) {
  check(citation, type, form);
  if (type === 'na') return citation + NA_SUFFIX[form];
  // plain 不套 よ 語幹：いい 的現在肯定就是「いいです」，不是「よいです」。
  if (form === 'plain') return citation + 'です';
  return iStem(citation) + I_SUFFIX[form];
}

export function conjugateAdjAlts(citation, type, form) {
  check(citation, type, form);
  const table = type === 'na' ? NA_ALT : I_ALT;
  const suffix = table[form];
  if (!suffix) return [];
  if (type === 'na') return [citation + suffix];
  return [iStem(citation) + suffix];
}
```

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test tests/app/test_adjective.js`
Expected: 12 tests PASS

- [ ] **Step 5: 確認無 DOM 依賴**

Run: `grep -nE "\bdocument\.|\bwindow\." app/lang/adjective.js; echo "exit=$?"`
Expected: 無輸出，`exit=1`（grep 找不到即回 1）

- [ ] **Step 6: 提交**

```bash
git add app/lang/adjective.js tests/app/test_adjective.js
git commit -m "feat(lang): 形容詞變化模組，含 いい 不規則與 16 課形態

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 3: `data/adjectives.json` 與其漂移測試

課本把な形容詞明確標為 `［な］`（`ハンサム［な］`、`静か［な］`），這個標記是可靠的自動判據。い形容詞無標記，且「以い結尾」會誤收名詞（`先生`、`時計`、`花`、`宿題`），必須人工確認。全語料共 64 個候選。

**Files:**
- Create: `tools/draft/adjectives.py`
- Create: `data/adjectives.json`
- Test: `tests/app/test_adjectives_data.js`

**Interfaces:**
- Produces: `data/adjectives.json`，以引用形（`kanji || kana`，去掉 `［な］`）為鍵，鏡射 `data/verbs.json` 的結構：
  ```json
  { "大きい": { "type": "i", "kana": "おおきい", "lesson": 8 },
    "静か":   { "type": "na", "kana": "しずか", "lesson": 8 } }
  ```

- [ ] **Step 1: 寫草稿產生腳本**

Create `tools/draft/adjectives.py`:

```python
"""從課次 JSON 產生 data/adjectives.json 的草稿。

な形容詞由課本的［な］標記自動判定，可靠。
い形容詞只能列為「候選」——以い結尾的名詞（先生、時計、花）數量不少，
必須人工確認。腳本把兩者分開輸出，草稿只收な形，い形留給人工勾選。

用法：python3 tools/draft/adjectives.py > /tmp/adjectives-draft.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NA_MARK = "［な］"


def strip_mark(s):
    return s.replace(NA_MARK, "").strip() if s else s


def main():
    na, i_candidates = {}, {}
    for n in range(1, 16):
        data = json.loads((ROOT / f"data/lessons/{n:02d}.json").read_text(encoding="utf-8"))
        for v in data.get("vocab", []):
            kana, kanji = v.get("kana") or "", v.get("kanji")
            cite = strip_mark(kanji) or strip_mark(kana)
            if not cite:
                continue
            if NA_MARK in kana or (kanji and NA_MARK in kanji):
                na.setdefault(cite, {"type": "na", "kana": strip_mark(kana), "lesson": n})
            elif kana.endswith("い") and not re.search(r"[…～]", kana):
                i_candidates.setdefault(cite, {"type": "i", "kana": kana, "lesson": n, "zh": v.get("zh")})

    print(json.dumps({"na": na, "i_candidates": i_candidates},
                     ensure_ascii=False, indent=2), file=sys.stdout)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 執行腳本產生草稿**

Run: `python3 tools/draft/adjectives.py > /tmp/adjectives-draft.json && python3 -c "import json;d=json.load(open('/tmp/adjectives-draft.json'));print('na',len(d['na']),'i候選',len(d['i_candidates']))"`
Expected: 印出兩個數字；`na` 約 10 餘筆，`i候選` 約 50 餘筆

- [ ] **Step 3: 人工校對並寫出 `data/adjectives.json`**

逐筆檢查 `i_candidates`：看 `zh` 欄位判斷是不是形容詞。**必須剔除**以下這類以い結尾但不是形容詞的名詞（已知會混進來）：`先生`、`学生`、`時計`、`花`、`魚`、`野菜`、`宿題`、`おととい`、`はい`、`何階`、`何歳`。

保留的項目去掉 `zh` 欄位（那只是校對用的參考），與 `na` 合併成單一物件寫入 `data/adjectives.json`，鍵排序固定（依課次再依鍵），格式為 2 空格縮排、`ensure_ascii=False`，與 `data/verbs.json` 一致。

`いい （よい）` 這筆的 `kana` 含括號異寫，**鍵與 `kana` 都取 `いい`**，`よい` 不另立條目（課本教的是いい，且 `conjugateAdj` 的不規則以いい 為準）。

- [ ] **Step 4: 寫漂移偵測測試**

Create `tests/app/test_adjectives_data.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { conjugateAdj } from '../../app/lang/adjective.js';

const adjectives = JSON.parse(readFileSync(new URL('../../data/adjectives.json', import.meta.url)));

function allVocab() {
  const out = [];
  for (let n = 1; n <= 15; n++) {
    const d = JSON.parse(readFileSync(new URL(`../../data/lessons/${String(n).padStart(2, '0')}.json`, import.meta.url)));
    for (const v of d.vocab || []) out.push({ ...v, lesson: n });
  }
  return out;
}

test('每個鍵都在課本單字表中找得到（去掉［な］後比對）', () => {
  const cites = new Set();
  for (const v of allVocab()) {
    // 課本有兩種會讓字面比對落空的寫法，都要一併收進可接受的引用形：
    //   ［な］ 標記（静か［な］）與括號異寫（いい  （よい））。
    const strip = (s) => (s || '').replace('［な］', '').trim();
    for (const raw of [v.kanji, v.kana]) {
      const t = strip(raw);
      if (!t) continue;
      cites.add(t);
      cites.add(t.split('（')[0].trim());
    }
  }
  for (const key of Object.keys(adjectives)) {
    assert.ok(cites.has(key), `adjectives.json 的「${key}」在課本單字表中不存在`);
  }
});

test('每筆欄位齊備且 type 合法', () => {
  for (const [key, info] of Object.entries(adjectives)) {
    assert.ok(['i', 'na'].includes(info.type), `${key} 的 type 非法：${info.type}`);
    assert.equal(typeof info.kana, 'string', `${key} 缺 kana`);
    assert.ok(info.kana.length > 0, `${key} 的 kana 為空`);
    assert.equal(typeof info.lesson, 'number', `${key} 缺 lesson`);
    assert.ok(info.lesson >= 1 && info.lesson <= 15, `${key} 的 lesson 超出 1~15：${info.lesson}`);
    assert.ok(!key.includes('［'), `${key} 的鍵未去除［な］標記`);
  }
});

test('每筆都能實際變化，不拋錯', () => {
  for (const [key, info] of Object.entries(adjectives)) {
    for (const form of ['plain', 'neg', 'past', 'pastneg']) {
      assert.doesNotThrow(() => conjugateAdj(key, info.type, form), `${key} 的 ${form} 變化失敗`);
      assert.doesNotThrow(() => conjugateAdj(info.kana, info.type, form), `${key} 的假名形 ${form} 變化失敗`);
    }
  }
});

test('形容詞數量在合理範圍（1~15課約 40~60 筆）', () => {
  const n = Object.keys(adjectives).length;
  assert.ok(n >= 35 && n <= 70, `形容詞筆數 ${n} 不在預期範圍，檢查是否漏收或誤收`);
});
```

- [ ] **Step 5: 執行測試確認通過**

Run: `node --test tests/app/test_adjectives_data.js`
Expected: 4 tests PASS。若「每個鍵都在課本單字表中找得到」失敗，代表校對時打錯字；若「每筆都能實際變化」失敗，代表某筆い形容詞的引用形不以い結尾（多半是誤收的名詞）。

- [ ] **Step 6: 提交**

```bash
git add tools/draft/adjectives.py data/adjectives.json tests/app/test_adjectives_data.js
git commit -m "feat(data): 形容詞い／な 分類表，含漂移偵測測試

な形由課本［な］標記自動判定，い形人工校對剔除以い結尾的名詞
（先生、時計、花、宿題）。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 4: `transform` 生成器擴充形容詞變化

需求 #3。沿用既有的 `generators/transform.js`，不另開生成器——機制相同（給一形態求另一形態），只是素材從動詞換成形容詞。

**Files:**
- Modify: `app/generators/transform.js`
- Modify: `app/core/concepts.js`（新增 `conceptsForAdjective`）
- Test: `tests/app/test_transform.js`、`tests/app/test_concepts.js`

**Interfaces:**
- Consumes: `conjugateAdj`／`conjugateAdjAlts`／`FORM_LESSON`（Task 2）、`data/adjectives.json`（Task 3）
- Produces:
  - `conceptsForAdjective(citation: string, type: 'i'|'na', form: string) → string[]` = `['r:<form>:<type>adj', 'w:<citation>:group']`
  - `generate(vocabList, verbsTable, adjTable)` — 第三個參數選用；未提供時行為與現在完全相同（只產動詞題）

- [ ] **Step 1: 寫失敗的測試**

先把 `tests/app/test_concepts.js` 的 import 行改為（既有的具名匯入清單是固定的，不加新名字會 `ReferenceError`）：

```js
import { SKILLS, skillOf, conceptsForVocab, conceptsForConjugation, conceptsForAdjective, aggregateSkills }
  from '../../app/core/concepts.js';
```

再把測試加到檔案末尾：

```js
test('形容詞概念：變化規則 ＋ 該詞的類別歸屬', () => {
  assert.deepEqual(conceptsForAdjective('大きい', 'i', 'past'), ['r:past:iadj', 'w:大きい:group']);
  assert.deepEqual(conceptsForAdjective('静か', 'na', 'neg'), ['r:neg:naadj', 'w:静か:group']);
});

test('形容詞概念歸入「變化」技能', () => {
  assert.equal(skillOf('r:past:iadj'), '變化');
  assert.equal(skillOf('w:大きい:group'), '變化');
});
```

加到 `tests/app/test_transform.js`：

```js
test('形容詞變化題：い形', () => {
  const vocab = [{ kana: 'おおきい', kanji: '大きい', zh: '大', lesson: 8, no: 11 }];
  const adjTable = { '大きい': { type: 'i', kana: 'おおきい', lesson: 8 } };
  const items = [...generate(vocab, {}, adjTable)];
  const past = items.find((it) => it.id === 'adj:大きい:past');
  assert.ok(past, '應產生過去形題目');
  assert.equal(past.engine, 'transform');
  assert.equal(past.prompt.text, '大きい');
  assert.equal(past.prompt.hint, '過去形');
  assert.equal(past.answer, '大きかったです');
  assert.ok(past.alternatives.includes('おおきかったです'), '假名形應算對');
  assert.deepEqual(past.covers, ['r:past:iadj', 'w:大きい:group']);
  // 素材第8課、過去式第12課解鎖 → 取較大者
  assert.equal(past.requires_lesson, 12);
  assert.equal(past.lesson, 8);
});

test('形容詞變化題：な形的 では 寫法也算對', () => {
  const vocab = [{ kana: 'きれい［な］', kanji: null, zh: '美麗', lesson: 8, no: 2 }];
  const adjTable = { 'きれい': { type: 'na', kana: 'きれい', lesson: 8 } };
  const items = [...generate(vocab, {}, adjTable)];
  const neg = items.find((it) => it.id === 'adj:きれい:neg');
  assert.ok(neg, '應產生否定形題目');
  assert.equal(neg.answer, 'きれいじゃありません');
  assert.ok(neg.alternatives.includes('きれいではありません'));
});

test('て形與副詞形的 requires_lesson 為 16（1~15 範圍內不會出現）', () => {
  const vocab = [{ kana: 'おおきい', kanji: '大きい', zh: '大', lesson: 8, no: 11 }];
  const adjTable = { '大きい': { type: 'i', kana: 'おおきい', lesson: 8 } };
  const items = [...generate(vocab, {}, adjTable)];
  const te = items.find((it) => it.id === 'adj:大きい:te');
  assert.ok(te);
  assert.equal(te.requires_lesson, 16);
});

test('未提供 adjTable 時行為不變（只產動詞題）', () => {
  const vocab = [{ kana: 'おおきい', kanji: '大きい', zh: '大', lesson: 8, no: 11 }];
  const items = [...generate(vocab, {})];
  assert.equal(items.length, 0);
});

test('同一引用形只產生一組形容詞題，不重複', () => {
  const vocab = [
    { kana: 'おおきい', kanji: '大きい', zh: '大', lesson: 8, no: 11 },
    { kana: 'おおきい', kanji: '大きい', zh: '大的', lesson: 12, no: 3 },
  ];
  const adjTable = { '大きい': { type: 'i', kana: 'おおきい', lesson: 8 } };
  const ids = [...generate(vocab, {}, adjTable)].map((it) => it.id);
  assert.equal(new Set(ids).size, ids.length, '不得有重複 id');
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_transform.js tests/app/test_concepts.js`
Expected: FAIL，`conceptsForAdjective is not defined` 以及 `應產生過去形題目`

- [ ] **Step 3: 實作概念函式**

加到 `app/core/concepts.js`（放在 `conceptsForConjugation` 之後）：

```js
/**
 * 形容詞的概念與動詞同構：變化規則本身，加上「這個詞屬於哪一類」。
 * 類別用 iadj／naadj 而非 I／II／III，才不會與動詞的 r:te:groupI 撞名——
 * 兩者都是「變化」技能底下的概念，命名空間必須分得開。
 */
export function conceptsForAdjective(citation, type, form) {
  return [`r:${form}:${type}adj`, `w:${citation}:group`];
}
```

- [ ] **Step 4: 實作生成器擴充**

在 `app/generators/transform.js` 頂部加入 import：

```js
import { conjugateAdj, conjugateAdjAlts, FORM_LESSON as ADJ_FORM_LESSON } from '../lang/adjective.js';
import { conceptsForConjugation, conceptsForAdjective, skillOf } from '../core/concepts.js';
```

在 `TARGETS` 之後加入：

```js
// 形容詞只操練四個時態。て形與副詞形第16課才教，本專案範圍外；
// 產出來也會被 requires_lesson=16 擋掉，但仍然生成，讓日後擴充課次不必改這裡。
const ADJ_TARGETS = [
  { form: 'neg', hint: '否定形' },
  { form: 'past', hint: '過去形' },
  { form: 'pastneg', hint: '過去否定形' },
  { form: 'te', hint: 'て形' },
  { form: 'adverb', hint: '副詞形' },
];

const NA_MARK = '［な］';

/**
 * 形容詞題與動詞題共用 transform 引擎（機制相同：給一形態求另一形態），
 * 但 id 前綴用 adj: 而非 conj:，因為兩者的素材表不同、變化規則也不同，
 * 混在同一個前綴下日後難以分辨來源。
 */
function* generateAdjectives(vocabList, adjTable) {
  const seen = new Set();
  for (const v of vocabList) {
    const strip = (s) => (s || '').replace(NA_MARK, '').trim();
    const cite = strip(v.kanji) || strip(v.kana);
    if (!cite || seen.has(cite)) continue;
    const info = adjTable[cite];
    if (!info) continue; // 未收錄者不猜類別，直接跳過
    seen.add(cite);

    for (const { form, hint } of ADJ_TARGETS) {
      let answer, kanaAnswer;
      try {
        answer = conjugateAdj(cite, info.type, form);
        kanaAnswer = conjugateAdj(info.kana, info.type, form);
      } catch {
        continue;
      }
      const alternatives = new Set(conjugateAdjAlts(cite, info.type, form));
      if (kanaAnswer !== answer) {
        alternatives.add(kanaAnswer);
        for (const alt of conjugateAdjAlts(info.kana, info.type, form)) alternatives.add(alt);
      }

      const covers = conceptsForAdjective(cite, info.type, form);
      yield {
        id: `adj:${cite}:${form}`,
        engine: ENGINE,
        lesson: v.lesson,
        requires_lesson: Math.max(v.lesson, ADJ_FORM_LESSON[form]),
        covers,
        skills: [...new Set(covers.map(skillOf).filter(Boolean))],
        prompt: { type: 'text', text: cite, hint },
        answer,
        alternatives: [...alternatives],
        source_ref: `第${v.lesson}課 ことば${v.no ? ` ${v.no}` : ''}`,
      };
    }
  }
}
```

把 `generate` 的簽章改為 `export function* generate(vocabList, verbsTable, adjTable)`，並在既有動詞迴圈**結束後**加上：

```js
  if (adjTable) yield* generateAdjectives(vocabList, adjTable);
```

- [ ] **Step 5: 執行測試確認通過**

Run: `node --test "tests/app/*.js"`
Expected: 全部 PASS

- [ ] **Step 6: 提交**

```bash
git add app/generators/transform.js app/core/concepts.js tests/app/test_transform.js tests/app/test_concepts.js
git commit -m "feat(generators): 變換題擴充形容詞，涵蓋需求 #3

形容詞與動詞共用 transform 引擎（機制相同），但 id 前綴用 adj:
且概念類別用 iadj／naadj，與動詞的 groupI/II/III 分開命名空間。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 5: `lang/numbers.js` 數字與時間讀音

需求 #4。不規則是本模組的全部重點：`よじ` 非 `しじ`、`はつか` 非 `にじゅうよっか`、`ついたち`、`ようか`、`いっぷん`／`さんぷん`。

**Files:**
- Create: `app/lang/numbers.js`
- Test: `tests/app/test_numbers.js`

**Interfaces:**
- Produces:
  - `readNumber(n: number) → string`（1 ~ 9999）
  - `readHour(h: number) → string`（1 ~ 12）
  - `readMinute(m: number) → string`（1 ~ 59）
  - `readDayOfMonth(d: number) → string`（1 ~ 31）
  - `readMonth(m: number) → string`（1 ~ 12）
  - 超出範圍時 `throw`

- [ ] **Step 1: 寫失敗的測試**

Create `tests/app/test_numbers.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readNumber, readHour, readMinute, readDayOfMonth, readMonth } from '../../app/lang/numbers.js';

test('基本數字 1~10', () => {
  const want = ['いち', 'に', 'さん', 'よん', 'ご', 'ろく', 'なな', 'はち', 'きゅう', 'じゅう'];
  want.forEach((w, i) => assert.equal(readNumber(i + 1), w));
});

test('十位與百位', () => {
  assert.equal(readNumber(11), 'じゅういち');
  assert.equal(readNumber(20), 'にじゅう');
  assert.equal(readNumber(35), 'さんじゅうご');
  assert.equal(readNumber(99), 'きゅうじゅうきゅう');
  assert.equal(readNumber(100), 'ひゃく');
  assert.equal(readNumber(300), 'さんびゃく');
  assert.equal(readNumber(600), 'ろっぴゃく');
  assert.equal(readNumber(800), 'はっぴゃく');
  assert.equal(readNumber(1000), 'せん');
  assert.equal(readNumber(3000), 'さんぜん');
  assert.equal(readNumber(8000), 'はっせん');
});

test('時刻：4時 7時 9時 為不規則', () => {
  assert.equal(readHour(4), 'よじ');
  assert.notEqual(readHour(4), 'しじ');
  assert.equal(readHour(7), 'しちじ');
  assert.equal(readHour(9), 'くじ');
  assert.equal(readHour(1), 'いちじ');
  assert.equal(readHour(12), 'じゅうにじ');
});

test('分：1 3 4 6 8 10 有音變', () => {
  assert.equal(readMinute(1), 'いっぷん');
  assert.equal(readMinute(2), 'にふん');
  assert.equal(readMinute(3), 'さんぷん');
  assert.equal(readMinute(4), 'よんぷん');
  assert.equal(readMinute(5), 'ごふん');
  assert.equal(readMinute(6), 'ろっぷん');
  assert.equal(readMinute(8), 'はっぷん');
  assert.equal(readMinute(10), 'じゅっぷん');
  assert.equal(readMinute(30), 'さんじゅっぷん');
  assert.equal(readMinute(15), 'じゅうごふん');
});

test('日期：1~10、14、20、24 為不規則', () => {
  assert.equal(readDayOfMonth(1), 'ついたち');
  assert.equal(readDayOfMonth(2), 'ふつか');
  assert.equal(readDayOfMonth(3), 'みっか');
  assert.equal(readDayOfMonth(4), 'よっか');
  assert.equal(readDayOfMonth(5), 'いつか');
  assert.equal(readDayOfMonth(6), 'むいか');
  assert.equal(readDayOfMonth(7), 'なのか');
  assert.equal(readDayOfMonth(8), 'ようか');
  assert.equal(readDayOfMonth(9), 'ここのか');
  assert.equal(readDayOfMonth(10), 'とおか');
  assert.equal(readDayOfMonth(14), 'じゅうよっか');
  assert.equal(readDayOfMonth(20), 'はつか');
  assert.notEqual(readDayOfMonth(20), 'にじゅうにち');
  assert.equal(readDayOfMonth(24), 'にじゅうよっか');
});

test('日期：規則部分', () => {
  assert.equal(readDayOfMonth(11), 'じゅういちにち');
  assert.equal(readDayOfMonth(31), 'さんじゅういちにち');
});

test('月份：4月 7月 9月 為不規則', () => {
  assert.equal(readMonth(4), 'しがつ');
  assert.notEqual(readMonth(4), 'よんがつ');
  assert.equal(readMonth(7), 'しちがつ');
  assert.equal(readMonth(9), 'くがつ');
  assert.equal(readMonth(1), 'いちがつ');
  assert.equal(readMonth(12), 'じゅうにがつ');
});

test('超出範圍時拋錯', () => {
  assert.throws(() => readHour(13));
  assert.throws(() => readHour(0));
  assert.throws(() => readMinute(60));
  assert.throws(() => readDayOfMonth(32));
  assert.throws(() => readMonth(13));
  assert.throws(() => readNumber(0));
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_numbers.js`
Expected: FAIL，`Cannot find module '../../app/lang/numbers.js'`

- [ ] **Step 3: 實作**

Create `app/lang/numbers.js`:

```js
/**
 * 數字、時刻、日期、月份的讀音（規格 §6.5）。
 *
 * 本模組的價值全在不規則：よじ 不是しじ、はつか 不是にじゅうよっか、
 * ついたち、ようか、いっぷん／さんぷん。規則部分反而是陪襯。
 * 因此不規則一律以明表列出，不試圖用「規則加例外修補」的寫法表達——
 * 那種寫法在這個領域裡每次擴充都會漏。
 */
const ONES = ['', 'いち', 'に', 'さん', 'よん', 'ご', 'ろく', 'なな', 'はち', 'きゅう'];
const HUNDREDS = ['', 'ひゃく', 'にひゃく', 'さんびゃく', 'よんひゃく', 'ごひゃく',
  'ろっぴゃく', 'ななひゃく', 'はっぴゃく', 'きゅうひゃく'];
const THOUSANDS = ['', 'せん', 'にせん', 'さんぜん', 'よんせん', 'ごせん',
  'ろくせん', 'ななせん', 'はっせん', 'きゅうせん'];

function need(n, lo, hi, what) {
  if (!Number.isInteger(n) || n < lo || n > hi) {
    throw new Error(`${what}: 需要 ${lo}~${hi} 的整數，收到 ${JSON.stringify(n)}`);
  }
}

export function readNumber(n) {
  need(n, 1, 9999, 'readNumber');
  const th = Math.floor(n / 1000);
  const hu = Math.floor((n % 1000) / 100);
  const te = Math.floor((n % 100) / 10);
  const on = n % 10;
  let out = THOUSANDS[th] + HUNDREDS[hu];
  if (te === 1) out += 'じゅう';
  else if (te > 1) out += ONES[te] + 'じゅう';
  out += ONES[on];
  return out;
}

const HOUR_IRREGULAR = { 4: 'よじ', 7: 'しちじ', 9: 'くじ' };

export function readHour(h) {
  need(h, 1, 12, 'readHour');
  return HOUR_IRREGULAR[h] || readNumber(h) + 'じ';
}

/** 分的音變只由個位決定（30分＝さんじゅっぷん，跟10分同型）。 */
const MINUTE_ONES = {
  1: 'いっぷん', 2: 'にふん', 3: 'さんぷん', 4: 'よんぷん', 5: 'ごふん',
  6: 'ろっぷん', 7: 'ななふん', 8: 'はっぷん', 9: 'きゅうふん', 0: 'じゅっぷん',
};

export function readMinute(m) {
  need(m, 1, 59, 'readMinute');
  const te = Math.floor(m / 10);
  const on = m % 10;
  const tens = te === 0 ? '' : (te === 1 ? 'じゅう' : ONES[te] + 'じゅう');
  if (on === 0) {
    // 10、20…50：音變落在「じゅっぷん」上，十位單獨讀
    return (te === 1 ? '' : ONES[te]) + MINUTE_ONES[0];
  }
  return tens + MINUTE_ONES[on];
}

const DAY_IRREGULAR = {
  1: 'ついたち', 2: 'ふつか', 3: 'みっか', 4: 'よっか', 5: 'いつか',
  6: 'むいか', 7: 'なのか', 8: 'ようか', 9: 'ここのか', 10: 'とおか',
  14: 'じゅうよっか', 20: 'はつか', 24: 'にじゅうよっか',
};

export function readDayOfMonth(d) {
  need(d, 1, 31, 'readDayOfMonth');
  return DAY_IRREGULAR[d] || readNumber(d) + 'にち';
}

const MONTH_IRREGULAR = { 4: 'しがつ', 7: 'しちがつ', 9: 'くがつ' };

export function readMonth(m) {
  need(m, 1, 12, 'readMonth');
  return MONTH_IRREGULAR[m] || readNumber(m) + 'がつ';
}
```

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test tests/app/test_numbers.js`
Expected: 8 tests PASS

- [ ] **Step 5: 提交**

```bash
git add app/lang/numbers.js tests/app/test_numbers.js
git commit -m "feat(lang): 數字、時刻、日期、月份讀音，不規則以明表列出

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 6: `lang/counters.js` 量詞音變

需求 #7。課本第 1、3、4、5、11 課陸續introduce量詞，各自的解鎖課次不同，必須記在量詞表裡供 `requires_lesson` 使用。

**Files:**
- Create: `app/lang/counters.js`
- Test: `tests/app/test_counters.js`

**Interfaces:**
- Consumes: `readNumber`（Task 5）
- Produces:
  - `COUNTERS: Record<string, { kana: string, label: string, lesson: number }>` — 鍵為羅馬字量詞名（`hon`、`satsu`、`nin`…），`label` 為題目要顯示的漢字寫法（`本`、`冊`、`人`）
  - `readCounter(n: number, key: string) → string`（1 ~ 10）
  - 未知量詞或超出範圍時 `throw`

- [ ] **Step 1: 寫失敗的測試**

Create `tests/app/test_counters.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readCounter, COUNTERS } from '../../app/lang/counters.js';

test('ほん：1 3 6 8 10 音變', () => {
  assert.equal(readCounter(1, 'hon'), 'いっぽん');
  assert.equal(readCounter(2, 'hon'), 'にほん');
  assert.equal(readCounter(3, 'hon'), 'さんぼん');
  assert.equal(readCounter(4, 'hon'), 'よんほん');
  assert.equal(readCounter(6, 'hon'), 'ろっぽん');
  assert.equal(readCounter(8, 'hon'), 'はっぽん');
  assert.equal(readCounter(10, 'hon'), 'じゅっぽん');
});

test('さつ：1 8 10 促音', () => {
  assert.equal(readCounter(1, 'satsu'), 'いっさつ');
  assert.equal(readCounter(3, 'satsu'), 'さんさつ');
  assert.equal(readCounter(8, 'satsu'), 'はっさつ');
  assert.equal(readCounter(10, 'satsu'), 'じゅっさつ');
});

test('ひき：1 3 6 8 10 音變', () => {
  assert.equal(readCounter(1, 'hiki'), 'いっぴき');
  assert.equal(readCounter(3, 'hiki'), 'さんびき');
  assert.equal(readCounter(6, 'hiki'), 'ろっぴき');
  assert.equal(readCounter(8, 'hiki'), 'はっぴき');
});

test('にん：1 2 4 為不規則', () => {
  assert.equal(readCounter(1, 'nin'), 'ひとり');
  assert.equal(readCounter(2, 'nin'), 'ふたり');
  assert.equal(readCounter(3, 'nin'), 'さんにん');
  assert.equal(readCounter(4, 'nin'), 'よにん');
  assert.notEqual(readCounter(4, 'nin'), 'よんにん');
});

test('さい：1 8 10 促音、20 為はたち', () => {
  assert.equal(readCounter(1, 'sai'), 'いっさい');
  assert.equal(readCounter(8, 'sai'), 'はっさい');
  assert.equal(readCounter(10, 'sai'), 'じゅっさい');
});

test('まい、だい 無音變', () => {
  assert.equal(readCounter(1, 'mai'), 'いちまい');
  assert.equal(readCounter(3, 'mai'), 'さんまい');
  assert.equal(readCounter(1, 'dai'), 'いちだい');
  assert.equal(readCounter(8, 'dai'), 'はちだい');
});

test('かい（樓層）：1 3 6 8 10 音變', () => {
  assert.equal(readCounter(1, 'kai_floor'), 'いっかい');
  assert.equal(readCounter(3, 'kai_floor'), 'さんがい');
  assert.equal(readCounter(6, 'kai_floor'), 'ろっかい');
  assert.equal(readCounter(10, 'kai_floor'), 'じゅっかい');
});

test('COUNTERS 每筆欄位齊備，課次在 1~15', () => {
  for (const [key, c] of Object.entries(COUNTERS)) {
    assert.equal(typeof c.kana, 'string', `${key} 缺 kana`);
    assert.equal(typeof c.label, 'string', `${key} 缺 label`);
    assert.ok(c.lesson >= 1 && c.lesson <= 15, `${key} 的 lesson 超出範圍：${c.lesson}`);
  }
});

test('每個量詞 1~10 都算得出來，不拋錯', () => {
  for (const key of Object.keys(COUNTERS)) {
    for (let n = 1; n <= 10; n++) {
      assert.doesNotThrow(() => readCounter(n, key), `${key} 的 ${n} 失敗`);
      assert.ok(readCounter(n, key).length > 0);
    }
  }
});

test('未知量詞與超出範圍時拋錯', () => {
  assert.throws(() => readCounter(1, 'nope'));
  assert.throws(() => readCounter(0, 'hon'));
  assert.throws(() => readCounter(11, 'hon'));
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_counters.js`
Expected: FAIL，`Cannot find module '../../app/lang/counters.js'`

- [ ] **Step 3: 實作**

Create `app/lang/counters.js`:

```js
/**
 * 量詞音變（規格 §6.5）。課本第1、3、4、5、11課陸續教到，各自的解鎖課次
 * 記在 COUNTERS[].lesson，供生成器算 requires_lesson。
 *
 * 音變一律以 1~10 的明表列出，不寫成「規則＋例外」：日語量詞的音變
 * 由數字與量詞首音共同決定（ほん→ぽん／ぼん、ひき→ぴき／びき、
 * かい→がい），交互作用多，明表才不會漏。每個量詞只有10個值，成本很低。
 */
import { readNumber } from './numbers.js';

const H_SERIES = (base, p, b) => ({
  1: `いっ${p}`, 2: `に${base}`, 3: `さん${b}`, 4: `よん${base}`, 5: `ご${base}`,
  6: `ろっ${p}`, 7: `なな${base}`, 8: `はっ${p}`, 9: `きゅう${base}`, 10: `じゅっ${p}`,
});

const K_SERIES = (base, g) => ({
  1: `いっ${base}`, 2: `に${base}`, 3: `さん${g}`, 4: `よん${base}`, 5: `ご${base}`,
  6: `ろっ${base}`, 7: `なな${base}`, 8: `はっ${base}`, 9: `きゅう${base}`, 10: `じゅっ${base}`,
});

const S_SERIES = (base) => ({
  1: `いっ${base}`, 2: `に${base}`, 3: `さん${base}`, 4: `よん${base}`, 5: `ご${base}`,
  6: `ろく${base}`, 7: `なな${base}`, 8: `はっ${base}`, 9: `きゅう${base}`, 10: `じゅっ${base}`,
});

/** 無音變者：直接用 readNumber 接上量詞。 */
const PLAIN = null;

export const COUNTERS = {
  hon:       { kana: 'ほん', label: '本', lesson: 11, table: H_SERIES('ほん', 'ぽん', 'ぼん') },
  hiki:      { kana: 'ひき', label: '匹', lesson: 11, table: H_SERIES('ひき', 'ぴき', 'びき') },
  satsu:     { kana: 'さつ', label: '冊', lesson: 11, table: S_SERIES('さつ') },
  sai:       { kana: 'さい', label: '歳', lesson: 1,  table: S_SERIES('さい') },
  kai_floor: { kana: 'かい', label: '階', lesson: 3,  table: K_SERIES('かい', 'がい') },
  kai_times: { kana: 'かい', label: '回', lesson: 11, table: S_SERIES('かい') },
  nin:       { kana: 'にん', label: '人', lesson: 11,
               table: { 1: 'ひとり', 2: 'ふたり', 3: 'さんにん', 4: 'よにん', 5: 'ごにん',
                        6: 'ろくにん', 7: 'ななにん', 8: 'はちにん', 9: 'きゅうにん', 10: 'じゅうにん' } },
  mai:       { kana: 'まい', label: '枚', lesson: 11, table: PLAIN },
  dai:       { kana: 'だい', label: '台', lesson: 11, table: PLAIN },
  en:        { kana: 'えん', label: '円', lesson: 3,  table: PLAIN },
  jikan:     { kana: 'じかん', label: '時間', lesson: 11, table: PLAIN },
  nen:       { kana: 'ねん', label: '年', lesson: 11, table: PLAIN },
};

export function readCounter(n, key) {
  const c = COUNTERS[key];
  if (!c) throw new Error(`readCounter: 未知的量詞 ${JSON.stringify(key)}`);
  if (!Number.isInteger(n) || n < 1 || n > 10) {
    throw new Error(`readCounter: 需要 1~10 的整數，收到 ${JSON.stringify(n)}`);
  }
  if (!c.table) return readNumber(n) + c.kana;
  return c.table[n];
}
```

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test tests/app/test_counters.js`
Expected: 10 tests PASS

- [ ] **Step 5: 提交**

```bash
git add app/lang/counters.js tests/app/test_counters.js
git commit -m "feat(lang): 量詞音變表，含 ひとり／ふたり／さんがい 等不規則

音變以 1~10 明表列出而非規則加例外修補——音變由數字與量詞首音
交互決定，明表才不會漏，且每個量詞只有十個值。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 7: `generators/quantity.js` 數量題

需求 #4 與 #7。產出 `engine: 'recall'`（機制就是對照題，規格 §6.1 不新增第五個引擎）但 `skills: ['數量']` 的題目，靠技能過濾讓使用者能單獨開關（規格 §13 決定 3）。

**Files:**
- Create: `app/generators/quantity.js`
- Modify: `app/core/concepts.js`（新增 `conceptsForQuantity`）
- Test: `tests/app/test_quantity.js`

**Interfaces:**
- Consumes: `readHour`／`readMinute`／`readDayOfMonth`／`readMonth`（Task 5）、`readCounter`／`COUNTERS`（Task 6）
- Produces: `generate() → Iterable<Item>`（無參數：題目完全由規則生成，不依賴課次素材）

- [ ] **Step 1: 寫失敗的測試**

Create `tests/app/test_quantity.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generate } from '../../app/generators/quantity.js';

const items = [...generate()];
const byId = new Map(items.map((it) => [it.id, it]));

test('時刻題：4時 → よじ', () => {
  const it = byId.get('qty:hour:4');
  assert.ok(it, '應有 qty:hour:4');
  assert.equal(it.engine, 'recall');
  assert.equal(it.prompt.text, '4時');
  assert.equal(it.answer, 'よじ');
  assert.deepEqual(it.covers, ['n:time:hour']);
  assert.deepEqual(it.skills, ['數量']);
  assert.equal(it.requires_lesson, 4);
});

test('日期題：20日 → はつか', () => {
  const it = byId.get('qty:day:20');
  assert.ok(it);
  assert.equal(it.answer, 'はつか');
  assert.deepEqual(it.covers, ['n:date:day']);
  assert.equal(it.requires_lesson, 5);
});

test('量詞題：3本 → さんぼん', () => {
  const it = byId.get('qty:c:hon:3');
  assert.ok(it);
  assert.equal(it.prompt.text, '3本');
  assert.equal(it.answer, 'さんぼん');
  assert.deepEqual(it.covers, ['c:hon']);
  assert.equal(it.requires_lesson, 11);
});

test('樓層與次數雖同為かい，但各自獨立成題', () => {
  assert.equal(byId.get('qty:c:kai_floor:3').answer, 'さんがい');
  assert.equal(byId.get('qty:c:kai_times:3').answer, 'さんかい');
  assert.notEqual(byId.get('qty:c:kai_floor:3').covers[0], byId.get('qty:c:kai_times:3').covers[0]);
});

test('全部 id 唯一且決定性（重跑兩次結果相同）', () => {
  const ids = items.map((it) => it.id);
  assert.equal(new Set(ids).size, ids.length, '不得有重複 id');
  const again = [...generate()].map((it) => it.id);
  assert.deepEqual(again, ids, '同一份規則重跑必須得到同一組 id');
});

test('每題欄位齊備', () => {
  for (const it of items) {
    assert.equal(typeof it.id, 'string');
    assert.equal(it.engine, 'recall');
    assert.ok(Array.isArray(it.covers) && it.covers.length > 0, `${it.id} 缺 covers`);
    assert.ok(it.answer.length > 0, `${it.id} 缺答案`);
    assert.ok(it.source_ref.length > 0, `${it.id} 缺出處`);
    assert.ok(it.requires_lesson >= 1 && it.requires_lesson <= 15, `${it.id} 的 requires_lesson 異常`);
    assert.ok(it.lesson >= 1 && it.lesson <= 15, `${it.id} 的 lesson 異常`);
  }
});

test('題數在預期範圍', () => {
  // 時12 ＋ 分14 ＋ 日31 ＋ 月12 ＝ 69，量詞 12 種 × 10 ＝ 120
  assert.ok(items.length >= 150 && items.length <= 220, `題數 ${items.length} 不如預期`);
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_quantity.js`
Expected: FAIL，`Cannot find module '../../app/generators/quantity.js'`

- [ ] **Step 3: 新增概念函式**

加到 `app/core/concepts.js`：

```js
/**
 * 數量概念：`n:<type>:<sub>` 為數字規則、`c:<counter>` 為量詞（規格 §5.2）。
 * 兩者都由 skillOf 歸入「數量」技能。
 */
export function conceptsForNumber(type, sub) {
  return [`n:${type}:${sub}`];
}

export function conceptsForCounter(key) {
  return [`c:${key}`];
}
```

- [ ] **Step 4: 實作生成器**

Create `app/generators/quantity.js`:

```js
/**
 * 數量題（需求 #4 數字時間日期、#7 量詞）。
 *
 * engine 是 'recall'——機制就是對照題「給 X 求 Y」，規格 §6.1 明定只有四個引擎，
 * 不為這類題目新增第五個。使用者要單獨開關數量題時，靠的是 skills: ['數量']
 * 配合排程器既有的技能過濾（規格 §8 的候選條件），不是靠引擎名稱。
 *
 * 題目完全由 lang/ 的規則生成，不讀課次素材——數字與量詞的讀法是規則，
 * 不是課本逐條列出的內容。課次只用來決定 requires_lesson（何時解鎖）。
 */
import { readHour, readMinute, readDayOfMonth, readMonth } from '../lang/numbers.js';
import { readCounter, COUNTERS } from '../lang/counters.js';
import { conceptsForNumber, conceptsForCounter, skillOf } from '../core/concepts.js';

/** 分只取有教學價值的值：音變全落在個位，加上整十與常用的15、45。 */
const MINUTES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 30, 45];

const NUMBER_GROUPS = [
  { kind: 'hour', type: 'time', sub: 'hour', lesson: 4, values: range(1, 12),
    label: (n) => `${n}時`, read: readHour, hint: '時刻的唸法' },
  { kind: 'minute', type: 'time', sub: 'minute', lesson: 4, values: MINUTES,
    label: (n) => `${n}分`, read: readMinute, hint: '分的唸法' },
  { kind: 'day', type: 'date', sub: 'day', lesson: 5, values: range(1, 31),
    label: (n) => `${n}日`, read: readDayOfMonth, hint: '日期的唸法' },
  { kind: 'month', type: 'date', sub: 'month', lesson: 5, values: range(1, 12),
    label: (n) => `${n}月`, read: readMonth, hint: '月份的唸法' },
];

function range(lo, hi) {
  return [...Array(hi - lo + 1)].map((_, i) => lo + i);
}

function makeItem({ id, lesson, covers, promptText, hint, answer, sourceRef }) {
  return {
    id,
    engine: 'recall',
    lesson,
    requires_lesson: lesson,
    covers,
    skills: [...new Set(covers.map(skillOf).filter(Boolean))],
    prompt: { type: 'text', text: promptText, hint },
    answer,
    alternatives: [],
    source_ref: sourceRef,
  };
}

export function* generate() {
  for (const g of NUMBER_GROUPS) {
    const covers = conceptsForNumber(g.type, g.sub);
    for (const n of g.values) {
      yield makeItem({
        id: `qty:${g.kind}:${n}`,
        lesson: g.lesson,
        covers,
        promptText: g.label(n),
        hint: g.hint,
        answer: g.read(n),
        sourceRef: `第${g.lesson}課 ことば`,
      });
    }
  }

  for (const [key, c] of Object.entries(COUNTERS)) {
    const covers = conceptsForCounter(key);
    for (let n = 1; n <= 10; n++) {
      yield makeItem({
        id: `qty:c:${key}:${n}`,
        lesson: c.lesson,
        covers,
        promptText: `${n}${c.label}`,
        hint: `量詞 ${c.label} 的唸法`,
        answer: readCounter(n, key),
        sourceRef: `第${c.lesson}課 ことば`,
      });
    }
  }
}
```

- [ ] **Step 5: 執行測試確認通過**

Run: `node --test "tests/app/*.js"`
Expected: 全部 PASS

- [ ] **Step 6: 提交**

```bash
git add app/generators/quantity.js app/core/concepts.js tests/app/test_quantity.js
git commit -m "feat(generators): 數量題生成器，涵蓋需求 #4 與 #7

engine 仍為 recall（機制就是對照題，不新增第五個引擎），
單獨開關靠 skills: ['數量'] 配合排程器既有的技能過濾。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 8: `data/concepts.json` 與 `core/conceptdefs.js`

91 則 `grammar[]` 是草稿來源——`title` 幾乎就是概念名（第7課-3「名詞（人）に あげます，等」→ `p:ni:recipient`），`no` 直接給出 `source_ref`。

`patterns` 反查表（規格 §13 決定 4）記在概念定義裡：哪些練習Ａ代入表考這個概念。substitute 的 `covers` 別無來源。

**Files:**
- Create: `tools/draft/concepts.py`
- Create: `data/concepts.json`
- Create: `app/core/conceptdefs.js`
- Test: `tests/app/test_conceptdefs.js`

**Interfaces:**
- Produces:
  - `data/concepts.json`：
    ```json
    { "p:ni:recipient": { "label": "助詞 に（動作對象）", "requires_lesson": 7, "source_ref": "第7課 文法3" },
      "g:de_means": { "label": "で（工具／手段）", "requires_lesson": 7, "source_ref": "第7課 文法1",
                      "patterns": ["L07-A1", "L07-A2"] } }
    ```
  - `app/core/conceptdefs.js`：
    - `conceptLabel(defs, id) → string`（查無時回傳 `id` 本身，不拋錯）
    - `conceptsByPattern(defs) → Map<patternId, string[]>`（反查：pattern id → 概念 id 陣列）
    - `requiresLessonOf(defs, id) → number`（查無時回傳 `1`）

- [ ] **Step 1: 寫草稿產生腳本**

Create `tools/draft/concepts.py`:

```python
"""從課次 JSON 的 grammar[] 產生 data/concepts.json 的草稿。

grammar[].title 幾乎就是概念名稱，grammar[].no 直接給出 source_ref。
概念 id 無法自動產生（要人為決定 p:ni:recipient 這種命名），因此草稿
輸出的是「待命名清單」：每則文法一列，附標題、課次、例句，供人工填 id。

用法：python3 tools/draft/concepts.py > /tmp/concepts-draft.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    out = []
    for n in range(1, 16):
        data = json.loads((ROOT / f"data/lessons/{n:02d}.json").read_text(encoding="utf-8"))
        patterns = [p["id"] for p in data.get("patterns", [])]
        for g in data.get("grammar", []):
            out.append({
                "id": "",  # 待人工填寫，例如 p:ni:recipient
                "label": g.get("title", ""),
                "requires_lesson": n,
                "source_ref": f"第{n}課 文法{g.get('no', '')}",
                "body_zh": g.get("body_zh", "")[:120],
                "examples": [e.get("jp", "") for e in g.get("examples", [])[:2]],
                "lesson_patterns": patterns,  # 供人工挑選哪幾張表屬於這個概念
            })
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 產生草稿**

Run: `python3 tools/draft/concepts.py > /tmp/concepts-draft.json && python3 -c "import json;print(len(json.load(open('/tmp/concepts-draft.json'))),'則文法待命名')"`
Expected: `91 則文法待命名`

- [ ] **Step 3: 人工命名並寫出 `data/concepts.json`**

逐則決定概念 id，規則（規格 §5.2）：

- 助詞用法 → `p:<助詞羅馬字>:<用法>`，例：`p:ni:recipient`、`p:de:means`、`p:de:place`、`p:ni:time`、`p:e:direction`、`p:to:together`
- 句型 → `g:<句型slug>`，例：`g:mou_mashita`、`g:arimasu_imasu`、`g:hoshii`、`g:tai`、`g:yori_nohou`
- 一則文法可能對應多個概念（第7課-3 同時教 `p:ni:recipient` 與 `g:ageru_morau`），拆成多筆
- 純詞彙性質的條目（「どれ」「何」）**不建概念**——那是單字，由 `w:` 概念涵蓋，重複建會讓同一個知識點的熟悉度分散在兩個概念上

把 78 張練習Ａ代入表逐張歸到概念下，填入該概念的 `patterns` 陣列。**每張表最多屬於一個概念**（重複歸屬會讓同一次作答對同一概念記兩次）。歸不出來的表先不填，Task 12 會以 fallback 處理。

輸出檔只保留 `label`／`requires_lesson`／`source_ref`／`patterns` 四個欄位——**不得寫入 `skills`**（規格 §13 決定 2：技能由 `skillOf()` 依 ID 前綴推導，寫進檔案會變成第二個真相來源）。`body_zh` 與 `examples` 是校對用的參考，不進最終檔案。

- [ ] **Step 4: 寫查詢模組的失敗測試**

Create `tests/app/test_conceptdefs.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { conceptLabel, conceptsByPattern, requiresLessonOf } from '../../app/core/conceptdefs.js';
import { skillOf } from '../../app/core/concepts.js';

const defs = JSON.parse(readFileSync(new URL('../../data/concepts.json', import.meta.url)));

test('conceptLabel 查得到就回標籤，查不到回 id 本身', () => {
  const someId = Object.keys(defs)[0];
  assert.equal(conceptLabel(defs, someId), defs[someId].label);
  assert.equal(conceptLabel(defs, 'p:nonexistent:x'), 'p:nonexistent:x');
});

test('requiresLessonOf 查不到時回 1（不擋任何範圍）', () => {
  assert.equal(requiresLessonOf(defs, 'p:nonexistent:x'), 1);
});

test('conceptsByPattern 建出 pattern → 概念的反查表', () => {
  const map = conceptsByPattern(defs);
  assert.ok(map instanceof Map);
  for (const [pid, ids] of map) {
    assert.match(pid, /^L\d{2}-[AB]\d+$/, `pattern id 格式異常：${pid}`);
    assert.ok(ids.length > 0);
  }
});

// ── 以下為漂移偵測（規格 §13 決定 6）────────────────────────────

test('每個概念 id 都能被 skillOf 歸類（不得落入任何長條圖之外）', () => {
  for (const id of Object.keys(defs)) {
    assert.ok(skillOf(id) !== null, `概念 ${id} 無法歸入六類技能，檢查前綴`);
  }
});

test('每筆定義欄位齊備且無 skills 欄位', () => {
  for (const [id, d] of Object.entries(defs)) {
    assert.equal(typeof d.label, 'string', `${id} 缺 label`);
    assert.ok(d.label.length > 0, `${id} 的 label 為空`);
    assert.equal(typeof d.requires_lesson, 'number', `${id} 缺 requires_lesson`);
    assert.ok(d.requires_lesson >= 1 && d.requires_lesson <= 15, `${id} 的課次超出範圍`);
    assert.equal(typeof d.source_ref, 'string', `${id} 缺 source_ref`);
    assert.equal(d.skills, undefined, `${id} 不得自帶 skills 欄位（技能由 skillOf 推導）`);
  }
});

test('patterns 反查表的每個 pattern id 都真的存在於課本資料中', () => {
  const real = new Set();
  for (let n = 1; n <= 15; n++) {
    const d = JSON.parse(readFileSync(new URL(`../../data/lessons/${String(n).padStart(2, '0')}.json`, import.meta.url)));
    for (const p of d.patterns || []) real.add(p.id);
  }
  for (const [id, d] of Object.entries(defs)) {
    for (const pid of d.patterns || []) {
      assert.ok(real.has(pid), `概念 ${id} 引用了不存在的代入表 ${pid}`);
    }
  }
});

test('同一張代入表不得歸屬到兩個概念', () => {
  const owner = new Map();
  for (const [id, d] of Object.entries(defs)) {
    for (const pid of d.patterns || []) {
      assert.ok(!owner.has(pid), `代入表 ${pid} 同時屬於 ${owner.get(pid)} 與 ${id}`);
      owner.set(pid, id);
    }
  }
});

test('概念數量在合理範圍', () => {
  const n = Object.keys(defs).length;
  assert.ok(n >= 50 && n <= 130, `概念數 ${n} 不如預期（91則文法，預估 70~90 個概念）`);
});
```

- [ ] **Step 5: 執行測試確認失敗**

Run: `node --test tests/app/test_conceptdefs.js`
Expected: FAIL，`Cannot find module '../../app/core/conceptdefs.js'`

- [ ] **Step 6: 實作查詢模組**

Create `app/core/conceptdefs.js`:

```js
/**
 * data/concepts.json 的查詢層（規格 §5.2）。
 *
 * 這個檔只放「人工定義的文法／助詞概念」，單字概念仍由 concepts.js 的
 * conceptsForVocab 即時生成——約900個單字概念沒有手寫定義的價值。
 *
 * 定義檔刻意不收 skills 欄位（規格 §13 決定 2）：技能一律由 concepts.js 的
 * skillOf() 依 ID 前綴推導，維持單一真相來源。
 *
 * 查不到的概念一律降級而不拋錯——概念定義是輔助資料，缺一筆不該讓整個
 * 題庫載入失敗。label 退回 id 本身（儀表板仍看得出是哪個概念），
 * requires_lesson 退回 1（不擋任何範圍，寧可多出題也不要靜默少出題）。
 */
export function conceptLabel(defs, id) {
  const d = defs && defs[id];
  return d && d.label ? d.label : id;
}

export function requiresLessonOf(defs, id) {
  const d = defs && defs[id];
  return d && typeof d.requires_lesson === 'number' ? d.requires_lesson : 1;
}

export function conceptsByPattern(defs) {
  const map = new Map();
  for (const [id, d] of Object.entries(defs || {})) {
    for (const pid of d.patterns || []) {
      if (!map.has(pid)) map.set(pid, []);
      map.get(pid).push(id);
    }
  }
  return map;
}
```

- [ ] **Step 7: 執行測試確認通過**

Run: `node --test tests/app/test_conceptdefs.js`
Expected: 8 tests PASS

- [ ] **Step 8: 提交**

```bash
git add tools/draft/concepts.py data/concepts.json app/core/conceptdefs.js tests/app/test_conceptdefs.js
git commit -m "feat(data): 文法與助詞概念定義檔，含 pattern 反查表與漂移偵測

91則 grammar[] 為草稿來源，人工命名概念 id 並把 78 張代入表歸屬到概念。
定義檔不收 skills 欄位——技能由 skillOf() 依前綴推導，維持單一真相來源。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 9: `data/particles.json` 助詞用法標註

cloze 的 `covers` 需要知道「這個 に 是哪種用法」，而課本語料只有純字串，沒有任何詞性或語意標註。規則猜測產草稿，人工校對定案（規格 §13，與 `verbs.json` 的「抽取初判＋人工校對」同一套作法）。

**素材限定 `文型` 與 `例文` 兩個段落**：147 句、**296 個句末助詞**。`会話` 多為對話殘句，`問題` 的 76 筆是多行混合體（含題號與括號內答案，例如 `1) わたしは はし（ で ） ごはんを 食べます。`），都不是乾淨單句，納入只會製造雜訊。問題段落的拆解屬 Phase 0 抽取工作，不在 2a。

**Files:**
- Create: `tools/draft/particles.py`
- Create: `data/particles.json`
- Test: `tests/app/test_particles_data.js`

**Interfaces:**
- Produces: `data/particles.json`，鍵為句子 id，值為該句的助詞標註陣列。`at` 為 `jp` 字串的字元索引，沿用 `sentence.ruby[].at` 的既有慣例：
  ```json
  { "L07-文型-2": [ { "at": 10, "p": "に", "c": "p:ni:recipient" } ] }
  ```

- [ ] **Step 1: 寫草稿產生腳本**

Create `tools/draft/particles.py`:

```python
"""產生 data/particles.json 的草稿。

只處理 文型 與 例文 兩個段落：会話 多為對話殘句，問題 的條目是含題號與
括號答案的多行混合體，都不是乾淨單句。

規則只猜得出「助詞在哪裡」，猜不準「是哪種用法」——後者由人工校對填入。
腳本把能高度確定的情形先填好（例如 を 只有一種用法），其餘留空字串，
讓校對者一眼看出哪些還沒決定。

用法：python3 tools/draft/particles.py > /tmp/particles-draft.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SECTIONS = {"文型", "例文"}
PARTICLES = ["から", "まで", "は", "が", "を", "に", "で", "と", "へ", "も", "や"]

# 只有單一用法的助詞可以直接定案，其餘一律留空給人工判斷。
UNAMBIGUOUS = {"を": "p:wo:object", "は": "p:wa:topic", "も": "p:mo:also"}


def main():
    out = {}
    for n in range(1, 16):
        data = json.loads((ROOT / f"data/lessons/{n:02d}.json").read_text(encoding="utf-8"))
        for s in data.get("sentences", []):
            if s.get("section") not in SECTIONS:
                continue
            jp = s.get("jp") or ""
            if not re.search(r"[　 ]", jp):
                continue  # 無課本分詞空格者無法可靠切分，跳過
            marks = []
            pos = 0
            for chunk in re.split(r"([　 ]+)", jp):
                if not chunk.strip():
                    pos += len(chunk)
                    continue
                body = re.sub(r"[。？！]+$", "", chunk)
                for p in PARTICLES:
                    if body.endswith(p) and len(body) > len(p):
                        marks.append({"at": pos + len(body) - len(p), "p": p,
                                      "c": UNAMBIGUOUS.get(p, "")})
                        break
                pos += len(chunk)
            if marks:
                out[s["id"]] = marks
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: 產生草稿並確認規模**

Run:
```bash
python3 tools/draft/particles.py > /tmp/particles-draft.json
python3 -c "
import json
d=json.load(open('/tmp/particles-draft.json'))
n=sum(len(v) for v in d.values())
todo=sum(1 for v in d.values() for m in v if not m['c'])
print(f'{len(d)} 句、{n} 個標註，其中 {todo} 個待人工判斷用法')
"
```
Expected: 約 140 句、290 個上下的標註，待判斷者約 150 個

- [ ] **Step 3: 人工校對並寫出 `data/particles.json`**

逐筆填入空的 `c` 欄位。常見用法（概念 id 須與 Task 3 的 `data/concepts.json` 一致，若草稿中出現定義檔沒有的用法，回頭補進 `concepts.json`）：

| 助詞 | 用法判準 | 概念 id |
|---|---|---|
| に | 動作的對象（人）＋ あげます／もらいます／かします／おしえます | `p:ni:recipient` |
| に | 時間點（前面是時刻、日期、星期） | `p:ni:time` |
| に | 歸著點（前面是場所）＋ いきます／きます／かえります／はいります | `p:ni:destination` |
| に | 存在的場所 ＋ あります／います | `p:ni:existence` |
| で | 工具、手段、語言 | `p:de:means` |
| で | 動作發生的場所 | `p:de:place` |
| へ | 方向 | `p:e:direction` |
| と | 共同動作的對象（いっしょに） | `p:to:together` |
| と | 並列（名詞と名詞） | `p:to:and` |
| から | 起點（時間或場所） | `p:kara:from` |
| から | 授受的來源（＋ もらいます） | `p:kara:source` |
| が | 主格（あります／います／すきです／わかります 的對象） | `p:ga:subject` |
| まで | 終點 | `p:made:to` |
| や | 舉例並列 | `p:ya:examples` |

**校對時同時驗證 `at`**：腳本算出的位置若有偏差，Step 4 的測試會抓到，不需人工逐字數。

- [ ] **Step 4: 寫漂移偵測測試**

Create `tests/app/test_particles_data.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const marks = JSON.parse(readFileSync(new URL('../../data/particles.json', import.meta.url)));
const defs = JSON.parse(readFileSync(new URL('../../data/concepts.json', import.meta.url)));

function allSentences() {
  const out = new Map();
  for (let n = 1; n <= 15; n++) {
    const d = JSON.parse(readFileSync(new URL(`../../data/lessons/${String(n).padStart(2, '0')}.json`, import.meta.url)));
    for (const s of d.sentences || []) out.set(s.id, { ...s, lesson: n });
  }
  return out;
}

const sentences = allSentences();

test('每個標註的句子 id 都存在', () => {
  for (const sid of Object.keys(marks)) {
    assert.ok(sentences.has(sid), `particles.json 引用了不存在的句子 ${sid}`);
  }
});

// 這是本檔最重要的一項：課本語料若被重新抽取而位移，必須紅燈而非靜默錯位。
test('每個 at 位置在句子中確實是所標的助詞', () => {
  for (const [sid, list] of Object.entries(marks)) {
    const jp = sentences.get(sid).jp;
    for (const m of list) {
      const got = jp.slice(m.at, m.at + m.p.length);
      assert.equal(got, m.p,
        `${sid} 的 at=${m.at} 應為「${m.p}」，實際是「${got}」——課本語料可能已位移`);
    }
  }
});

test('每個概念引用都存在於 concepts.json，不得懸空', () => {
  for (const [sid, list] of Object.entries(marks)) {
    for (const m of list) {
      assert.ok(m.c && m.c.length > 0, `${sid} 的 at=${m.at} 尚未填入概念 id`);
      assert.ok(Object.hasOwn(defs, m.c), `${sid} 引用了 concepts.json 沒有的概念 ${m.c}`);
    }
  }
});

test('同一句中的標註位置不重複且遞增', () => {
  for (const [sid, list] of Object.entries(marks)) {
    const ats = list.map((m) => m.at);
    assert.deepEqual([...ats].sort((a, b) => a - b), ats, `${sid} 的標註未依位置排序`);
    assert.equal(new Set(ats).size, ats.length, `${sid} 有重複的標註位置`);
  }
});

test('只標註 文型 與 例文 段落', () => {
  for (const sid of Object.keys(marks)) {
    const sec = sentences.get(sid).section;
    assert.ok(['文型', '例文'].includes(sec), `${sid} 屬於 ${sec} 段落，不應納入`);
  }
});

test('標註總數在預期範圍', () => {
  const n = Object.values(marks).reduce((a, l) => a + l.length, 0);
  assert.ok(n >= 200 && n <= 350, `標註數 ${n} 不如預期（文型＋例文 約 296 個句末助詞）`);
});
```

- [ ] **Step 5: 執行測試確認通過**

Run: `node --test tests/app/test_particles_data.js`
Expected: 6 tests PASS。若「at 位置確實是所標的助詞」失敗，訊息會直接指出哪一句哪個位置對不上。

- [ ] **Step 6: 提交**

```bash
git add tools/draft/particles.py data/particles.json tests/app/test_particles_data.js
git commit -m "feat(data): 助詞用法標註，涵蓋文型與例文段落

素材限定文型與例文（147句、296個句末助詞）：会話 多為對話殘句，
問題 的條目是含題號與括號答案的多行混合體，拆解屬 Phase 0 工作。

最關鍵的測試是 at 位置驗證——課本語料若重新抽取而位移，必須紅燈
而非靜默錯位到別的字上。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 10: `generators/cloze.js` 助詞挖空

需求 #5。單一考點題，歸因明確（規格 §7.5 第 1 點）。

**Files:**
- Create: `app/generators/cloze.js`
- Test: `tests/app/test_cloze.js`

**Interfaces:**
- Consumes: `data/particles.json`（Task 9）、`idx.sentences`（`core/data.js`）
- Produces: `generate(sentences, particleMarks) → Iterable<Item>`
  - `sentences`: `buildIndex().sentences`
  - `particleMarks`: `data/particles.json` 解析後的物件

- [ ] **Step 1: 寫失敗的測試**

Create `tests/app/test_cloze.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generate } from '../../app/generators/cloze.js';

const sentences = [
  { id: 'L07-文型-2', jp: 'わたしは  木村さんに  花を  あげます。', section: '文型', no: 2, lesson: 7, alt: [] },
  { id: 'L07-文型-3', jp: 'わたしは  カリナさんに  チョコレートを  もらいました。', section: '文型', no: 3, lesson: 7, alt: ['から'] },
];
const marks = {
  'L07-文型-2': [{ at: 10, p: 'に', c: 'p:ni:recipient' }],
  'L07-文型-3': [{ at: 11, p: 'に', c: 'p:ni:recipient' }],
};

test('挖掉助詞，題幹留下底線', () => {
  const it = [...generate(sentences, marks)].find((x) => x.id === 'cloze:L07-文型-2:10');
  assert.ok(it, '應產生 cloze:L07-文型-2:10');
  assert.equal(it.engine, 'cloze');
  assert.equal(it.prompt.text, 'わたしは  木村さん＿  花を  あげます。');
  assert.equal(it.answer, 'に');
  assert.deepEqual(it.covers, ['p:ni:recipient']);
  assert.deepEqual(it.skills, ['助詞']);
  assert.equal(it.lesson, 7);
  assert.equal(it.requires_lesson, 7);
  assert.equal(it.source_ref, '第7課 文型-2');
});

test('課本標註的替代形納入 alternatives（規格 §9.2 第一類）', () => {
  const it = [...generate(sentences, marks)].find((x) => x.id === 'cloze:L07-文型-3:11');
  assert.ok(it);
  assert.equal(it.answer, 'に');
  assert.ok(it.alternatives.includes('から'), '課本標的から 應算對');
});

test('方向助詞 へ↔に 互為替代（規格 §9.2 第二類）', () => {
  const s = [{ id: 'L05-文型-1', jp: 'わたしは  京都へ  行きます。', section: '文型', no: 1, lesson: 5, alt: [] }];
  const m = { 'L05-文型-1': [{ at: 8, p: 'へ', c: 'p:e:direction' }] };
  const it = [...generate(s, m)][0];
  assert.equal(it.answer, 'へ');
  assert.ok(it.alternatives.includes('に'), '方向的に 應算對');
});

test('沒有標註的句子不產題（不猜）', () => {
  const s = [{ id: 'L01-文型-1', jp: 'わたしは  マイク・ミラーです。', section: '文型', no: 1, lesson: 1, alt: [] }];
  assert.equal([...generate(s, {})].length, 0);
});

test('標註指向不存在的句子時略過，不拋錯', () => {
  const items = [...generate(sentences, { 'L99-文型-1': [{ at: 0, p: 'に', c: 'p:ni:time' }] })];
  assert.equal(items.length, 0);
});

test('一句多個助詞各自成題，id 不撞', () => {
  const s = [{ id: 'L07-例文-1', jp: 'きのう  友達に  手紙を  書きました。', section: '例文', no: 1, lesson: 7, alt: [] }];
  const m = { 'L07-例文-1': [
    { at: 7, p: 'に', c: 'p:ni:recipient' },
    { at: 12, p: 'を', c: 'p:wo:object' },
  ] };
  const items = [...generate(s, m)];
  assert.equal(items.length, 2);
  assert.equal(new Set(items.map((x) => x.id)).size, 2);
  assert.equal(items[0].answer, 'に');
  assert.equal(items[1].answer, 'を');
  // 各題只挖自己那一個，另一個助詞要留在題幹裡
  assert.ok(items[0].prompt.text.includes('を'));
  assert.ok(items[1].prompt.text.includes('に'));
});

test('id 決定性：同一份輸入重跑結果相同', () => {
  const a = [...generate(sentences, marks)].map((x) => x.id);
  const b = [...generate(sentences, marks)].map((x) => x.id);
  assert.deepEqual(a, b);
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_cloze.js`
Expected: FAIL，`Cannot find module '../../app/generators/cloze.js'`

- [ ] **Step 3: 實作**

Create `app/generators/cloze.js`:

```js
/**
 * 挖空題（需求 #5 助詞填空）。
 *
 * 素材是 data/particles.json 的人工標註，不是規則猜測——規則找得到助詞在哪，
 * 但分不出「に 表對象」與「に 表時間」是兩個不同的知識點（規格 §5.2）。
 * 沒有標註的句子一律不產題：寧可少出題，也不要把錯的歸因寫進 SRS。
 *
 * 單一考點題，covers 只有一個概念，答錯的歸因明確（規格 §7.5 第1點）。
 */
import { skillOf } from '../core/concepts.js';

export const ENGINE = 'cloze';

const BLANK = '＿';

/**
 * 規格 §9.2 第二類：助詞的合法替代，生成時依規則列舉。
 * 只收課本範圍內確實兩者皆可的配對——過度列舉會讓真正的錯誤也被判對。
 */
const EQUIVALENT = {
  'p:e:direction': ['に'],       // 日本へ 行きます／日本に 行きます
  'p:ni:destination': ['へ'],
};

export function* generate(sentences, particleMarks) {
  const byId = new Map(sentences.map((s) => [s.id, s]));

  for (const [sid, list] of Object.entries(particleMarks || {})) {
    const s = byId.get(sid);
    if (!s) continue; // 標註指向已不存在的句子（課次範圍未載入或語料變動），略過

    for (const m of list) {
      // 位置對不上就不出題。測試會在 CI 抓到這種漂移，這裡是執行期的第二道防線：
      // 錯位的題目會把答案挖在別的字上，比不出題有害得多。
      if (s.jp.slice(m.at, m.at + m.p.length) !== m.p) continue;

      const prompt = s.jp.slice(0, m.at) + BLANK + s.jp.slice(m.at + m.p.length);
      const alternatives = new Set([
        ...(s.alt || []),
        ...(EQUIVALENT[m.c] || []),
      ]);
      alternatives.delete(m.p); // 主答案不重複列進 alternatives

      const covers = [m.c];
      yield {
        id: `cloze:${sid}:${m.at}`,
        engine: ENGINE,
        lesson: s.lesson,
        // 助詞用法的解鎖課次就是它所在句子的課次——課本在哪一課用這個句型，
        // 該用法就是那一課教的。
        requires_lesson: s.lesson,
        covers,
        skills: [...new Set(covers.map(skillOf).filter(Boolean))],
        prompt: { type: 'text', text: prompt, hint: '填入助詞' },
        answer: m.p,
        alternatives: [...alternatives],
        source_ref: `第${s.lesson}課 ${s.section}-${s.no}`,
      };
    }
  }
}
```

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test tests/app/test_cloze.js`
Expected: 7 tests PASS

- [ ] **Step 5: 以全語料實測產題量**

Run:
```bash
node --input-type=module -e "
import { readFileSync } from 'node:fs';
const { generate } = await import('./app/generators/cloze.js');
const { buildIndex } = await import('./app/core/data.js');
const map = new Map();
for (let n = 1; n <= 15; n++) map.set(n, JSON.parse(readFileSync(\`data/lessons/\${String(n).padStart(2,'0')}.json\`)));
const idx = buildIndex(map);
const marks = JSON.parse(readFileSync('data/particles.json'));
const items = [...generate(idx.sentences, marks)];
console.log('助詞挖空題數:', items.length);
console.log('概念數:', new Set(items.flatMap(i => i.covers)).size);
"
```
Expected: 題數接近 `particles.json` 的標註總數（約 296），概念數約 15 ~ 25

- [ ] **Step 6: 提交**

```bash
git add app/generators/cloze.js tests/app/test_cloze.js
git commit -m "feat(generators): 助詞挖空題，涵蓋需求 #5

素材為人工標註而非規則猜測——規則找得到助詞在哪，但分不出
「に 表對象」與「に 表時間」是兩個知識點。沒有標註的句子不產題。

執行期另有位置驗證：標註與句子對不上就不出題，錯位的題目會把答案
挖在別的字上，比不出題有害得多。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 11: cloze 詞組挖空

需求 #12「填空練習（挖任意成分）」。挖掉一整個課本分詞詞組，**只在該詞組的內容詞能對上 vocab 條目時才出題**——對不上就沒有明確的 `w:` 概念可掛，歸因會落空。

**Files:**
- Modify: `app/generators/cloze.js`
- Test: `tests/app/test_cloze.js`

**Interfaces:**
- Produces: `generate(sentences, particleMarks, vocabList)` — 第三個參數選用；未提供時只產助詞題（行為與 Task 10 相同）

- [ ] **Step 1: 寫失敗的測試**

加到 `tests/app/test_cloze.js`：

```js
test('詞組挖空：內容詞對得上 vocab 時才出題', () => {
  const s = [{ id: 'L07-文型-1', jp: 'わたしは  ワープロで  手紙を  書きます。', section: '文型', no: 1, lesson: 7, alt: [] }];
  const vocab = [{ kana: 'てがみ', kanji: '手紙', zh: '信', lesson: 7, no: 5 }];
  const items = [...generate(s, {}, vocab)];
  const it = items.find((x) => x.id === 'cloze:L07-文型-1:13:phrase');
  assert.ok(it, '手紙を 這個詞組應可出題');
  assert.equal(it.prompt.text, 'わたしは  ワープロで  ＿を  書きます。');
  assert.equal(it.answer, '手紙');
  assert.ok(it.alternatives.includes('てがみ'), '假名寫法應算對');
  assert.deepEqual(it.covers, ['w:手紙']);
  assert.deepEqual(it.skills, ['單字']);
  assert.equal(it.prompt.hint, '信');
});

test('詞組挖空：對不上 vocab 的詞組不出題', () => {
  const s = [{ id: 'L07-文型-1', jp: 'わたしは  ワープロで  手紙を  書きます。', section: '文型', no: 1, lesson: 7, alt: [] }];
  const items = [...generate(s, {}, [])];
  assert.equal(items.length, 0, 'vocab 空的時候不該產出任何詞組題');
});

test('詞組挖空與助詞挖空並存，id 不撞', () => {
  const s = [{ id: 'L07-文型-1', jp: 'わたしは  ワープロで  手紙を  書きます。', section: '文型', no: 1, lesson: 7, alt: [] }];
  const m = { 'L07-文型-1': [{ at: 15, p: 'を', c: 'p:wo:object' }] };
  const vocab = [{ kana: 'てがみ', kanji: '手紙', zh: '信', lesson: 7, no: 5 }];
  const ids = [...generate(s, m, vocab)].map((x) => x.id);
  assert.equal(new Set(ids).size, ids.length);
  assert.ok(ids.includes('cloze:L07-文型-1:15'));
  assert.ok(ids.includes('cloze:L07-文型-1:13:phrase'));
});

test('未提供 vocab 時只產助詞題（行為不變）', () => {
  const items = [...generate(sentences, marks)];
  assert.ok(items.every((x) => !x.id.endsWith(':phrase')));
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_cloze.js`
Expected: FAIL，`手紙を 這個詞組應可出題`

- [ ] **Step 3: 實作**

在 `app/generators/cloze.js` 的 import 加入 `conceptsForVocab`：

```js
import { skillOf, conceptsForVocab } from '../core/concepts.js';
import { splitForms, splitKanaForms } from '../lang/altforms.js';
```

在檔案末尾加入詞組挖空，並把 `generate` 改為同時產出兩種：

```js
/** 課本以全形空格分詞，切出來的每一塊就是一個詞組。 */
const SPACE = /[　 ]+/;

/**
 * 詞組挖空（需求 #12）。挖掉整個詞組的內容詞，保留其後的助詞——
 * 助詞留著，題目才問得出「這裡該填哪個詞」而不是「這裡該填什麼都行」。
 *
 * 只在內容詞對得上 vocab 條目時才出題。對不上就沒有明確的 w: 概念可掛，
 * 答對答錯都無處歸因，那種題目對 SRS 沒有價值（規格 §7.5）。
 */
function* generatePhrases(sentences, vocabList) {
  // 引用形與假名兩種寫法都建索引：課本句子裡可能寫漢字也可能寫假名。
  const byForm = new Map();
  for (const v of vocabList) {
    if (!v.zh) continue;
    for (const form of [...(v.kanji ? splitForms(v.kanji) : []), ...splitKanaForms(v.kana || '')]) {
      if (form && !byForm.has(form)) byForm.set(form, v);
    }
  }

  for (const s of sentences) {
    let pos = 0;
    for (const chunk of s.jp.split(/([　 ]+)/)) {
      if (!chunk.trim()) { pos += chunk.length; continue; }
      const body = chunk.replace(/[。？！]+$/u, '');
      // 由長到短試切點：詞組可能是「手紙を」「手紙」或「手紙が」，
      // 取最長的成功比對，避免把「手」當成內容詞。
      for (let cut = body.length; cut >= 1; cut--) {
        const head = body.slice(0, cut);
        const v = byForm.get(head);
        if (!v) continue;
        const covers = [conceptsForVocab(v)[0]];
        yield {
          id: `cloze:${s.id}:${pos}:phrase`,
          engine: ENGINE,
          lesson: s.lesson,
          requires_lesson: Math.max(s.lesson, v.lesson),
          covers,
          skills: [...new Set(covers.map(skillOf).filter(Boolean))],
          prompt: {
            type: 'text',
            text: s.jp.slice(0, pos) + BLANK + s.jp.slice(pos + cut),
            hint: v.zh,
          },
          answer: head,
          alternatives: [...new Set([
            ...(v.kanji ? splitForms(v.kanji) : []),
            ...splitKanaForms(v.kana || ''),
          ])].filter((x) => x !== head),
          source_ref: `第${s.lesson}課 ${s.section}-${s.no}`,
        };
        break; // 一個詞組只出一題
      }
      pos += chunk.length;
    }
  }
}
```

把 `generate` 的簽章改為 `export function* generate(sentences, particleMarks, vocabList)`，並在既有助詞迴圈**結束後**加上：

```js
  if (vocabList) yield* generatePhrases(sentences, vocabList);
```

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test "tests/app/*.js"`
Expected: 全部 PASS

- [ ] **Step 5: 提交**

```bash
git add app/generators/cloze.js tests/app/test_cloze.js
git commit -m "feat(generators): 詞組挖空，涵蓋需求 #12

只在內容詞對得上 vocab 時才出題——對不上就沒有 w: 概念可掛，
答對答錯都無處歸因，那種題目對 SRS 沒有價值。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 12: `generators/substitute.js` 代入題（練習Ａ）

需求 #11 #13，並隨素材自動涵蓋 #6 #8 #9 #10。78 張代入表的 `rows` 已經給出合法的槽位組合，逐列展開即可。

**Files:**
- Create: `app/generators/substitute.js`
- Test: `tests/app/test_substitute.js`

**Interfaces:**
- Consumes: `idx.patterns`（Task 1）、`conceptsByPattern(defs)`（Task 8）
- Produces: `generate(patterns, patternConcepts) → Iterable<Item>`
  - `patternConcepts`: `Map<patternId, string[]>`

- [ ] **Step 1: 寫失敗的測試**

Create `tests/app/test_substitute.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { generate } from '../../app/generators/substitute.js';

const patterns = [{
  id: 'L07-A1',
  lesson: 7,
  requires_lesson: 7,
  template: '{S}は{T}で ごはんを 食べます。',
  slots: { S: ['日本人', 'インドネシア人', 'アメリカ人'], T: ['はし', 'スプーンと フォーク', 'ナイフと フォーク'] },
  rows: [[0, 0], [1, 1], [2, 2]],
  question_variant: '日本人はなんで ごはんを 食べますか。',
}];
const concepts = new Map([['L07-A1', ['g:de_means']]]);

test('逐列展開代入表', () => {
  const items = [...generate(patterns, concepts)];
  assert.equal(items.length, 3);
  const it = items.find((x) => x.id === 'subst:L07-A1:1');
  assert.ok(it);
  assert.equal(it.engine, 'substitute');
  assert.equal(it.answer, 'インドネシア人はスプーンと フォークで ごはんを 食べます。');
  assert.equal(it.lesson, 7);
  assert.equal(it.requires_lesson, 7);
  assert.equal(it.source_ref, '第7課 練習Ａ-1');
});

test('題幹給出範例句與本題的提示詞', () => {
  const it = [...generate(patterns, concepts)].find((x) => x.id === 'subst:L07-A1:1');
  // 範例取第0列，讓使用者知道要造什麼樣的句子
  assert.ok(it.prompt.text.includes('日本人ははしで ごはんを 食べます。'), '應含第0列範例');
  assert.ok(it.prompt.text.includes('インドネシア人'), '應含本題提示詞');
  assert.ok(it.prompt.text.includes('スプーンと フォーク'), '應含本題提示詞');
});

test('第 0 列本身也出題，但題幹改用第 1 列當範例', () => {
  const it = [...generate(patterns, concepts)].find((x) => x.id === 'subst:L07-A1:0');
  assert.ok(it, '第0列也該出題');
  assert.equal(it.answer, '日本人ははしで ごはんを 食べます。');
  assert.ok(it.prompt.text.includes('インドネシア人はスプーンと フォークで'), '範例應改用第1列');
  assert.ok(!it.prompt.text.includes('日本人ははしで ごはんを 食べます。'), '範例不得等於答案');
});

test('covers 含句型概念與各槽位填充詞', () => {
  const it = [...generate(patterns, concepts)].find((x) => x.id === 'subst:L07-A1:1');
  assert.ok(it.covers.includes('g:de_means'), '應含句型概念');
  assert.ok(it.skills.includes('句型'));
});

test('沒有對應概念的代入表仍出題，以表 id 當概念（不靜默丟棄素材）', () => {
  const it = [...generate(patterns, new Map())][0];
  assert.ok(it, '無概念對應時仍應出題');
  assert.deepEqual(it.covers, ['g:L07-A1']);
});

test('只有一列的表不出題（沒有代入的變化可練）', () => {
  const single = [{ ...patterns[0], id: 'L07-A9', rows: [[0, 0]] }];
  assert.equal([...generate(single, new Map())].length, 0);
});

test('槽位索引越界時略過該列，不產生壞題目', () => {
  const bad = [{ ...patterns[0], id: 'L07-A8', rows: [[0, 0], [9, 9]] }];
  const items = [...generate(bad, new Map())];
  assert.equal(items.length, 1);
  assert.ok(!items[0].answer.includes('undefined'));
});

test('id 決定性且唯一', () => {
  const a = [...generate(patterns, concepts)].map((x) => x.id);
  const b = [...generate(patterns, concepts)].map((x) => x.id);
  assert.deepEqual(a, b);
  assert.equal(new Set(a).size, a.length);
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_substitute.js`
Expected: FAIL，`Cannot find module '../../app/generators/substitute.js'`

- [ ] **Step 3: 實作**

Create `app/generators/substitute.js`:

```js
/**
 * 代入題（需求 #11 句型代入、#13 句型練習）。
 *
 * 素材是課本練習Ａ的代入表：template 帶槽位、slots 給各槽位的候選詞、
 * rows 給出哪些組合是課本列出的合法搭配。逐列展開即可，不自行做笛卡兒積
 * ——課本的 rows 是有意義的配對（日本人配はし、アメリカ人配ナイフ），
 * 全組合會造出「日本人はナイフで」這種課本沒教、也未必自然的句子。
 *
 * 複合題：covers 含句型概念與各槽位填充詞，答錯時全部計入（規格 §7.5 第2點
 * 的已知過度歸因，token 級精準歸因屬 Phase 4）。
 *
 * 語序自由度無法窮舉（規格 §9.2 第四類），由「我這樣寫也對」承接。
 */
import { skillOf } from '../core/concepts.js';

export const ENGINE = 'substitute';

const SLOT = /\{([A-Z])\}/g;

function fillRow(pattern, row) {
  const keys = Object.keys(pattern.slots);
  const values = {};
  for (let i = 0; i < keys.length; i++) {
    const v = pattern.slots[keys[i]][row[i]];
    if (v == null) return null; // 索引越界：課本資料有缺，略過該列而非產生壞題
    values[keys[i]] = v;
  }
  const filled = pattern.template.replace(SLOT, (_, k) => values[k] ?? '');
  return { filled, values, cues: keys.map((k) => values[k]) };
}

export function* generate(patterns, patternConcepts) {
  for (const p of patterns) {
    const rows = p.rows || [];
    // 只有一列的表沒有「代入」可練——那是一個例句，不是代入練習。
    if (rows.length < 2 || !p.template || !p.slots) continue;

    const filledRows = rows.map((r) => fillRow(p, r));
    // 概念對應不到時退回以表 id 當概念，讓這張表的練習仍然累積熟悉度。
    // 靜默丟棄素材才是更糟的結果：使用者會發現某些課本練習從來沒出現過。
    const covers = patternConcepts.get(p.id) || [`g:${p.id}`];
    const skills = [...new Set(covers.map(skillOf).filter(Boolean))];

    for (let i = 0; i < rows.length; i++) {
      const cur = filledRows[i];
      if (!cur) continue;
      // 範例取另一列（通常是第0列；輪到第0列時改用第1列），
      // 範例等於答案的話這題就沒得練了。
      const exampleIdx = i === 0 ? 1 : 0;
      const example = filledRows[exampleIdx];
      if (!example) continue;

      yield {
        id: `subst:${p.id}:${i}`,
        engine: ENGINE,
        lesson: p.lesson,
        requires_lesson: p.requires_lesson ?? p.lesson,
        covers,
        skills,
        prompt: {
          type: 'text',
          text: `例：${example.filled}\n用這些詞造句：${cur.cues.join(' ／ ')}`,
          hint: '照範例的句型造句',
        },
        answer: cur.filled,
        alternatives: [],
        source_ref: `第${p.lesson}課 練習Ａ-${p.id.split('-A')[1] || ''}`,
      };
    }
  }
}
```

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test tests/app/test_substitute.js`
Expected: 8 tests PASS

- [ ] **Step 5: 以全語料實測產題量與抽樣檢視**

Run:
```bash
node --input-type=module -e "
import { readFileSync } from 'node:fs';
const { generate } = await import('./app/generators/substitute.js');
const { buildIndex } = await import('./app/core/data.js');
const { conceptsByPattern } = await import('./app/core/conceptdefs.js');
const map = new Map();
for (let n = 1; n <= 15; n++) map.set(n, JSON.parse(readFileSync(\`data/lessons/\${String(n).padStart(2,'0')}.json\`)));
const idx = buildIndex(map);
const defs = JSON.parse(readFileSync('data/concepts.json'));
const items = [...generate(idx.patterns, conceptsByPattern(defs))];
console.log('代入題數:', items.length);
const fallback = items.filter(i => i.covers[0].startsWith('g:L'));
console.log('無概念對應而用 fallback 的題數:', fallback.length);
for (const it of items.slice(0, 3)) console.log('---\n' + it.prompt.text + '\n→ ' + it.answer);
"
```
Expected: 題數約 200 ~ 300；fallback 題數應為 0（Task 8 已把 78 張表全部歸屬）。若 fallback 不為 0，回頭補 `concepts.json` 的 `patterns` 陣列。人工檢視印出的三題，確認句子通順、範例不等於答案。

- [ ] **Step 6: 提交**

```bash
git add app/generators/substitute.js tests/app/test_substitute.js
git commit -m "feat(generators): 代入題（練習Ａ），涵蓋需求 #11 #13

逐列展開課本 rows，不自行做笛卡兒積——課本的配對是有意義的
（日本人配はし），全組合會造出課本沒教也未必自然的句子。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 13: substitute 納入練習Ｂ（drills）

107 則 `drills[]` 中 72%（77 則）完整可用（`items`、`model_answer`、`model_cue` 齊備）。不可用的 29 則集中在第 1 ~ 3 課且 `items` 為空，屬 Phase 0 抽取缺口（規格 §13 決定 5），此處自然不產題。

練習Ｂ 的結構與練習Ａ不同：`model_cue` 是範例的提示詞、`model_answer` 是範例的完整答句，`items[]` 是要代入的其他提示詞。由 cue → answer 的對應推出替換規則，套到每個 item 上。

**Files:**
- Modify: `app/generators/substitute.js`
- Test: `tests/app/test_substitute.js`

**Interfaces:**
- Produces: `generateDrills(drills, lessonConcepts) → Iterable<Item>`，由 `generate` 於同一模組內匯出並在 `main.js` 各自呼叫
  - `lessonConcepts: Map<number, string[]>` — 課次 → 該課概念 id 陣列（練習Ｂ無表 id 可對應，只能歸到課次層級）

- [ ] **Step 1: 寫失敗的測試**

先把 `tests/app/test_substitute.js` **既有的** import 行改為（再寫一行 `import` 同一個模組會是重複宣告，直接 SyntaxError）：

```js
import { generate, generateDrills } from '../../app/generators/substitute.js';
```

再把測試加到檔案末尾：

```js
const drills = [{
  id: 'L07-B1',
  lesson: 7,
  items: ['手紙を 書きます', 'レポートを 送ります', '紙を 切ります', 'ごはんを 食べます'],
  model_answer: 'はしで ごはんを 食べます。',
  model_cue: 'ごはんを 食べます',
}];

test('練習Ｂ：把 cue 換成各 item，其餘保持不變', () => {
  const items = [...generateDrills(drills, new Map([[7, ['g:de_means']]]))];
  const it = items.find((x) => x.id === 'subst:L07-B1:0');
  assert.ok(it, '應產生 subst:L07-B1:0');
  assert.equal(it.engine, 'substitute');
  assert.equal(it.answer, 'はしで 手紙を 書きます。');
  assert.equal(it.lesson, 7);
  assert.equal(it.source_ref, '第7課 練習Ｂ-1');
  assert.ok(it.prompt.text.includes('はしで ごはんを 食べます。'), '應含範例答句');
  assert.ok(it.prompt.text.includes('手紙を 書きます'), '應含本題提示詞');
});

test('練習Ｂ：與範例相同的 item 不重複出題', () => {
  const items = [...generateDrills(drills, new Map())];
  assert.ok(!items.some((x) => x.answer === 'はしで ごはんを 食べます。'),
    '等於範例答句的那題沒有練習價值');
});

test('練習Ｂ：items 為空者不產題（第1~3課的抽取缺口）', () => {
  const empty = [{ id: 'L01-B1', lesson: 1, items: ['', '', ''], model_answer: 'ミラーさんです。', model_cue: '' }];
  assert.equal([...generateDrills(empty, new Map())].length, 0);
});

test('練習Ｂ：cue 不在 model_answer 中時不產題（推不出替換規則）', () => {
  const broken = [{ id: 'L07-B9', lesson: 7, items: ['手紙を 書きます'],
    model_answer: 'これは 日本語で 何ですか。', model_cue: 'ごはんを 食べます' }];
  assert.equal([...generateDrills(broken, new Map())].length, 0);
});

test('練習Ｂ的 id 與練習Ａ不撞', () => {
  const a = [...generate(patterns, concepts)].map((x) => x.id);
  const b = [...generateDrills(drills, new Map())].map((x) => x.id);
  assert.equal(new Set([...a, ...b]).size, a.length + b.length);
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_substitute.js`
Expected: FAIL，`generateDrills is not a function`

- [ ] **Step 3: 實作**

加到 `app/generators/substitute.js` 末尾：

```js
/**
 * 練習Ｂ（需求 #11 #13 的第二素材來源）。
 *
 * 結構與練習Ａ不同：model_cue 是範例的提示詞、model_answer 是範例的完整答句，
 * items[] 是其他要代入的提示詞。由 cue → answer 推出替換規則
 * （cue 在 answer 中的位置），再把每個 item 套上去。
 *
 * 全語料實測 107 則中 77 則完整可用；不可用的 29 則集中在第1~3課且 items 為空
 * （Phase 0 抽取缺口，規格 §13 決定 5），在這裡自然不產題，不特別處理。
 *
 * cue 不在 answer 裡就不產題：推不出替換規則時硬湊只會造出錯句。
 */
export function* generateDrills(drills, lessonConcepts) {
  for (const d of drills || []) {
    const cue = (d.model_cue || '').trim();
    const answer = (d.model_answer || '').trim();
    if (!cue || !answer) continue;

    const at = answer.indexOf(cue);
    if (at < 0) continue; // 推不出替換規則

    const covers = lessonConcepts.get(d.lesson) || [`g:${d.id}`];
    const skills = [...new Set(covers.map(skillOf).filter(Boolean))];
    const head = answer.slice(0, at);
    const tail = answer.slice(at + cue.length);

    let n = 0;
    for (const raw of d.items || []) {
      const item = (raw || '').trim();
      if (!item) continue;
      // 與範例相同者沒有練習價值——答案會一字不差等於題幹給的範例。
      if (item === cue) continue;

      yield {
        id: `subst:${d.id}:${n}`,
        engine: ENGINE,
        lesson: d.lesson,
        requires_lesson: d.lesson,
        covers,
        skills,
        prompt: {
          type: 'text',
          text: `例：${answer}\n用這個詞造句：${item}`,
          hint: '照範例的句型造句',
        },
        answer: head + item + tail,
        alternatives: [],
        source_ref: `第${d.lesson}課 練習Ｂ-${d.id.split('-B')[1] || ''}`,
      };
      n++;
    }
  }
}
```

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test tests/app/test_substitute.js`
Expected: 13 tests PASS

- [ ] **Step 5: 以全語料實測可用率**

Run:
```bash
node --input-type=module -e "
import { readFileSync } from 'node:fs';
const { generateDrills } = await import('./app/generators/substitute.js');
const { buildIndex } = await import('./app/core/data.js');
const map = new Map();
for (let n = 1; n <= 15; n++) map.set(n, JSON.parse(readFileSync(\`data/lessons/\${String(n).padStart(2,'0')}.json\`)));
const idx = buildIndex(map);
const items = [...generateDrills(idx.drills, new Map())];
const used = new Set(items.map(i => i.id.split(':')[1]));
console.log(\`練習Ｂ題數: \${items.length}，實際產題的表: \${used.size} / \${idx.drills.length}\`);
for (const it of items.slice(0, 3)) console.log('---\n' + it.prompt.text + '\n→ ' + it.answer);
"
```
Expected: 產題的表數應接近 77（實測可用數）。人工檢視印出的三題，確認替換後的句子通順。若明顯低於 70，停下來回報——代表 `model_cue` 的抽取品質比預期差，不要硬推進。

- [ ] **Step 6: 提交**

```bash
git add app/generators/substitute.js tests/app/test_substitute.js
git commit -m "feat(generators): 代入題納入練習Ｂ 為第二素材來源

由 model_cue 在 model_answer 中的位置推出替換規則。cue 不在 answer
裡就不產題——推不出規則時硬湊只會造出錯句。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 14: 接線與技能過濾

把三個新生成器接進 `main.js`，並在設定畫面加入題型與技能開關。規格 §8 的候選條件同時含 `engine ∈ scope.enabledEngines` 與 `skills ∩ scope.skills ≠ ∅`，Phase 1 只實作了前者。

**Files:**
- Modify: `app/main.js:8-13`（import）、`app/main.js:108-118`（載入與生成）
- Modify: `app/ui/settings.js`
- Test: `tests/app/test_settings.js`

**Interfaces:**
- Produces: `DEFAULT_SETTINGS` 擴充為
  ```js
  { minLesson: 1, maxLesson: 15,
    engines: ['recall', 'transform', 'substitute', 'cloze'],
    skills: ['單字', '讀音', '變化', '助詞', '句型', '數量'],
    sessionSize: 20 }
  ```

- [ ] **Step 1: 寫失敗的測試**

Create `tests/app/test_settings.js`:

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { DEFAULT_SETTINGS, loadSettings } from '../../app/ui/settings.js';
import { SKILLS } from '../../app/core/concepts.js';

test('預設開啟四個引擎與六類技能', () => {
  assert.deepEqual(DEFAULT_SETTINGS.engines, ['recall', 'transform', 'substitute', 'cloze']);
  assert.deepEqual(DEFAULT_SETTINGS.skills, SKILLS);
});

test('舊版設定沒有 skills 欄位時補上預設值（不讓既有使用者的題目消失）', () => {
  const storage = { getItem: () => JSON.stringify({ minLesson: 1, maxLesson: 15, engines: ['recall'], sessionSize: 20 }) };
  const s = loadSettings(storage);
  assert.deepEqual(s.skills, SKILLS);
  assert.deepEqual(s.engines, ['recall'], '既有欄位不得被預設值蓋掉');
});

test('儲存被封鎖時回預設值', () => {
  const storage = { getItem: () => { throw new Error('blocked'); } };
  assert.deepEqual(loadSettings(storage), DEFAULT_SETTINGS);
});
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `node --test tests/app/test_settings.js`
Expected: FAIL，`DEFAULT_SETTINGS.engines` 只有兩個引擎

- [ ] **Step 3: 修改設定模組**

`app/ui/settings.js` 頂部改為：

```js
// 設定畫面：課次範圍、題型開關、技能過濾、每次題數。純 DOM／localStorage 存取，不含判斷邏輯。
import { SKILLS } from '../core/concepts.js';

const ENGINE_LABELS = {
  recall: '單字題',
  transform: '變化題',
  substitute: '代入題',
  cloze: '挖空題',
};

export const DEFAULT_SETTINGS = {
  minLesson: 1,
  maxLesson: 15,
  engines: Object.keys(ENGINE_LABELS),
  skills: [...SKILLS],
  sessionSize: 20,
};
```

`renderSettings` 的引擎與技能兩組 checkbox 改為由清單生成：

```js
  const engineBoxes = Object.entries(ENGINE_LABELS).map(([id, label]) =>
    `<label><input id="eng-${id}" type="checkbox" ${settings.engines.includes(id) ? 'checked' : ''}> ${label}</label>`
  ).join('');
  const skillBoxes = SKILLS.map((s, i) =>
    `<label><input id="skill-${i}" type="checkbox" data-skill="${s}" ${settings.skills.includes(s) ? 'checked' : ''}> ${s}</label>`
  ).join('');
```

把這兩段插進 `host.innerHTML` 的題型區塊（取代原本寫死的兩個 checkbox），技能區塊加上小標題 `<div class="group-title">練習技能</div>`。

`#apply` 的 handler 改為：

```js
    const engines = Object.keys(ENGINE_LABELS).filter((id) => host.querySelector(`#eng-${id}`).checked);
    const skills = SKILLS.filter((_, i) => host.querySelector(`#skill-${i}`).checked);
    // 全部取消勾選等於一題都不出，那是使用者操作失誤而非意圖，退回預設值。
    onChange({
      minLesson: Math.min(min, max),
      maxLesson: Math.max(min, max),
      engines: engines.length ? engines : DEFAULT_SETTINGS.engines,
      skills: skills.length ? skills : DEFAULT_SETTINGS.skills,
      sessionSize,
    });
```

- [ ] **Step 4: 執行測試確認通過**

Run: `node --test tests/app/test_settings.js`
Expected: 3 tests PASS（`loadSettings` 既有的 `{ ...DEFAULT_SETTINGS, ...parsed }` 展開已自動補上缺少的 `skills`）

- [ ] **Step 5: 接線 main.js**

`app/main.js` 的 import 區加入：

```js
import * as substitute from './generators/substitute.js';
import * as cloze from './generators/cloze.js';
import * as quantity from './generators/quantity.js';
import { conceptsByPattern } from './core/conceptdefs.js';
```

新增三個 fetch 函式（緊接 `fetchVerbs` 之後）：

```js
async function fetchJson(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} 載入失敗：${res.status}`);
  return res.json();
}
```

把 `runSession` 中的載入改為：

```js
    const [lessonsMap, verbsTable, adjTable, conceptDefs, particleMarks] = await Promise.all([
      loadLessons(lessonNumbers, fetchLesson),
      fetchVerbs(),
      fetchJson('data/adjectives.json'),
      fetchJson('data/concepts.json'),
      fetchJson('data/particles.json'),
    ]);
```

生成區改為：

```js
    const allItems = [];
    if (settings.engines.includes('recall')) {
      allItems.push(...recall.generate(idx.vocab));
      // 數量題的機制就是對照題，跟著 recall 開關走；要單獨關掉請用技能過濾
      // （規格 §13 決定 3）。
      allItems.push(...quantity.generate());
    }
    if (settings.engines.includes('transform')) {
      allItems.push(...transform.generate(idx.vocab, verbsTable, adjTable));
    }
    if (settings.engines.includes('substitute')) {
      const byPattern = conceptsByPattern(conceptDefs);
      allItems.push(...substitute.generate(idx.patterns, byPattern));
      allItems.push(...substitute.generateDrills(idx.drills, lessonConceptsOf(conceptDefs)));
    }
    if (settings.engines.includes('cloze')) {
      allItems.push(...cloze.generate(idx.sentences, particleMarks, idx.vocab));
    }
```

在 `main.js` 的模組層加入輔助函式（練習Ｂ無表 id 可對應，只能歸到課次層級）：

```js
/** 練習Ｂ 沒有表 id 可對應概念，只能歸到課次層級：該課所有句型概念一併計入。 */
function lessonConceptsOf(defs) {
  const map = new Map();
  for (const [id, d] of Object.entries(defs)) {
    if (!id.startsWith('g:')) continue;
    const n = d.requires_lesson;
    if (!map.has(n)) map.set(n, []);
    map.get(n).push(id);
  }
  return map;
}
```

範圍過濾加上技能條件（規格 §8）：

```js
    const items = allItems
      .filter((it) => it.lesson >= settings.minLesson
        && it.requires_lesson <= settings.maxLesson
        && (it.skills || []).some((s) => settings.skills.includes(s)))
```

- [ ] **Step 6: 以 HTTP 實測端到端載入**

Run:
```bash
python3 -m http.server 8000 &
sleep 1
for f in index.html app/main.js app/generators/substitute.js app/generators/cloze.js app/generators/quantity.js \
         app/lang/adjective.js app/lang/numbers.js app/lang/counters.js app/core/conceptdefs.js \
         data/concepts.json data/particles.json data/adjectives.json; do
  printf '%s %s\n' "$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:8000/$f")" "$f"
done
kill %1
```
Expected: 全部 `200`

- [ ] **Step 7: 全語料題數實測**

Run:
```bash
node --input-type=module -e "
import { readFileSync } from 'node:fs';
const { buildIndex } = await import('./app/core/data.js');
const recall = await import('./app/generators/recall.js');
const transform = await import('./app/generators/transform.js');
const substitute = await import('./app/generators/substitute.js');
const cloze = await import('./app/generators/cloze.js');
const quantity = await import('./app/generators/quantity.js');
const { conceptsByPattern } = await import('./app/core/conceptdefs.js');
const map = new Map();
for (let n = 1; n <= 15; n++) map.set(n, JSON.parse(readFileSync(\`data/lessons/\${String(n).padStart(2,'0')}.json\`)));
const idx = buildIndex(map);
const verbs = JSON.parse(readFileSync('data/verbs.json'));
const adjs = JSON.parse(readFileSync('data/adjectives.json'));
const defs = JSON.parse(readFileSync('data/concepts.json'));
const marks = JSON.parse(readFileSync('data/particles.json'));
const all = [
  ...recall.generate(idx.vocab), ...quantity.generate(),
  ...transform.generate(idx.vocab, verbs, adjs),
  ...substitute.generate(idx.patterns, conceptsByPattern(defs)),
  ...cloze.generate(idx.sentences, marks, idx.vocab),
];
const byEngine = {};
for (const it of all) byEngine[it.engine] = (byEngine[it.engine] || 0) + 1;
console.log('題數 by engine:', byEngine, '合計', all.length);
const bySkill = {};
for (const it of all) for (const s of it.skills) bySkill[s] = (bySkill[s] || 0) + 1;
console.log('題數 by skill:', bySkill);
const ids = all.map(i => i.id);
console.log('id 唯一:', new Set(ids).size === ids.length);
const noCovers = all.filter(i => !i.covers || i.covers.length === 0);
console.log('缺 covers 的題數:', noCovers.length);
"
```
Expected: `id 唯一: true`、`缺 covers 的題數: 0`、六類技能**每一類都有非零題數**（這是 2a 驗收條件之一）。若某類為 0，回頭檢查該類概念是否漏定義。

- [ ] **Step 8: 提交**

```bash
git add app/main.js app/ui/settings.js tests/app/test_settings.js
git commit -m "feat(app): 接上代入、挖空、數量三個生成器，設定加入技能過濾

規格 §8 的候選條件同時含引擎與技能兩個維度，Phase 1 只實作了引擎。
數量題跟著 recall 開關走，要單獨關掉用技能過濾。

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```

---

### Task 15: 驗收報告

比照 `docs/superpowers/plans/2026-09-20-phase1-acceptance-report.md` 的格式：**實測數據與人工待確認項目分開列，不把讀過程式碼當成驗證過**。

**Files:**
- Create: `docs/superpowers/plans/2026-09-23-phase2a-acceptance-report.md`

- [ ] **Step 1: 跑完整測試套件並記錄**

Run: `node --test "tests/app/*.js" 2>&1 | tail -20`
Expected: 全部 PASS，記下 `tests`／`pass`／`fail` 三個數字寫進報告

- [ ] **Step 2: 確認核心判斷邏輯未洩漏到 ui/**

Run:
```bash
grep -nE "isCorrect|normalizeAnswer|conjugateAdj|readCounter|readHour" app/ui/*.js && echo "✗ 有洩漏" || echo "✓ ui 層乾淨"
grep -rnE "\bdocument\.|\bwindow\." app/core app/lang app/generators && echo "✗ 有 DOM 呼叫" || echo "✓ core/lang/generators 無 DOM 呼叫"
```
Expected: 兩行都是 `✓`

- [ ] **Step 3: 重跑 Task 14 Step 7 的題數統計，寫進報告**

把 by engine、by skill 兩張表與 id 唯一性結果填入報告第 1 節。

- [ ] **Step 4: 撰寫報告**

必須包含：

1. **生成的題目總數**（by engine、by skill 兩張表），並註明是以全語料即時生成實測、非估算
2. **全部自動測試結果**（實際輸出的 tests/pass/fail 數字）
3. **2a 驗收條件逐項結果**：需求 #3 #4 #5 #7 #11 #12 #13 各由哪個生成器涵蓋、實際題數各多少；六類技能分母皆非零的實測輸出
4. **三份人工資料檔的規模與校對範圍**：`concepts.json` 幾個概念、`particles.json` 幾筆標註（涵蓋哪些段落、為何排除 会話 與 問題）、`adjectives.json` 幾筆
5. **待人工確認**（我不能做的）：真實瀏覽器裡代入題的長句輸入體驗、挖空題的底線在手機上是否看得清楚、代入題答案的語序自由度實際有多常誤判（這會決定「我這樣寫也對」的按下頻率）
6. **已知限制**：substitute 的複合題過度歸因（規格 §7.5 第 2 點，Phase 4 才做 token diff）；練習Ｂ 第 1 ~ 3 課因抽取缺口不產題；`会話` 與 `問題` 段落未納入 cloze 素材

- [ ] **Step 5: 提交**

```bash
git add docs/superpowers/plans/2026-09-23-phase2a-acceptance-report.md
git commit -m "docs: Phase 2a 驗收報告

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>"
```
