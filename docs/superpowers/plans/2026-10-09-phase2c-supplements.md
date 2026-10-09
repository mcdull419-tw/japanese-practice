# Phase 2c 補充講義 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把課本附錄的五張表（數字、時間詞、時刻／日期、期間、量詞）人工轉寫成資料檔，用它核對並擴充 `numbers.js`／`counters.js`，並讓新增的量詞與日期讀法可以出題。

**Architecture:** 轉寫結果放 `data/supplements/*.json`，**只當測試的對照基準（oracle）**，執行期不讀取、不 fetch；可執行的讀音規則維持在 `app/lang/` 的明表，題目仍由 `app/generators/quantity.js` 生成（engine 為 `recall`，技能為「數量」，規格 §6.1 不新增引擎）。漂移偵測測試把兩邊逐筆比對：講義有而程式沒有、或兩邊不一致，測試紅燈。

**Tech Stack:** 原生 ES modules、`node --test`、既有的 `app/core/concepts.js` 概念系統。無新依賴。

**Spec:** `docs/superpowers/specs/2026-09-10-japanese-practice-design.md` §4.7（補充講義）、§6.5（語言規則模組）、§13 Phase 2c、決定 6（手維護資料檔須有漂移偵測）

## Global Constraints

- 轉寫來源是 `IMAG0805.jpeg`（數字）、`IMAG0806.jpeg`（時間詞）、`IMAG0807.jpeg`（時刻、日期）、`IMAG0808.jpeg`（期間）、`IMAG0809.jpeg`（量詞）。**`IMAG0810`~`IMAG0824` 是索引、`IMAG0825`／`IMAG0825 1` 是地圖，不在本階段範圍。**
- 照片上的手寫（藍色 △、黃色螢光、粉紅／藍色筆記）一律不收。
- 不憑記憶補日文讀音：每一筆都必須能在照片上讀到。讀不清楚的列進驗收報告，不猜。
- 不得新增第五種引擎；數量題 `engine` 一律 `'recall'`（`app/generators/quantity.js` 檔頭已明定）。
- 唸法題 `prompt.hideRuby: true`（答案就是讀音，不能把振假名印在題幹上；見 `app/ui/present.js`）。
- `app/` 下新增 `.js` 必須列入 `sw.js` 的 `PRECACHE`（`tests/app/test_sw.js` 把關）；改動上線內容後要把 `sw.js` 的 `CACHE` 版本號加一，否則已安裝的手機繼續用舊題庫。
- 測試指令：`node --test "tests/app/*.js"`，全綠才算完成；CI 也跑這一條。
- 題目 id 必須唯一且決定性（重跑得到同一組 id）；既有 id（`qty:hour:4`、`qty:c:hon:3` 等）**不得改名**，改名會讓使用者的作答紀錄與新題對不上。
- git commit 訊息結尾加：`Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`

## Review Focus

照片已經讀過一輪，下列是規格沉默、但最容易出錯或最容易被忽略的：

1. **17 日、27 日**：講義寫じゅうしちにち／にじゅうしちにち，現有 `readDayOfMonth` 用 `readNumber` 會產出じゅうななにち／にじゅうななにち（錯）。——最可能是現有的真實錯誤。對應 Task 3。
2. **「じっ」讀法**：10 分、10 歲、10 本、10 冊、10 匹、10 階、10 週間、10 か月 講義都寫「じゅっ…、じっ…」兩種。使用者打じっぷん不該被判錯。對應 Task 3、5。
3. **數字在量詞前換讀法**：4 時間讀よじかん（不是よんじかん）、9 時間くじかん、4 年よねん、7 年ななねん／しちねん、9 年きゅうねん／くねん。使用者按「ななねん」或「しちねん」都該對。對應 Task 4。
4. **疑問詞的連濁**：何本なんぼん、何匹なんびき、何階なんがい、何軒なんげん、何足なんぞく、何杯なんばい。規則推不出來，必須逐個查表。對應 Task 5。
5. **1 日是 ついたち，但「1 天」是 いちにち**：日期與期間的日數同字不同讀（1 日在日期表是ついたち、在期間表是いちにち）。兩組題的 prompt 必須能讓使用者分辨（「1日」vs「1日間」），否則同題幹有兩個正解。對應 Task 4。

---

## File Structure

| 檔案 | 責任 |
|---|---|
| `data/supplements/numbers.json` | 照片 0805 轉寫：數字 0~90、百、千、萬、億、小數、分數 |
| `data/supplements/timewords.json` | 照片 0806 轉寫：星期、前天~後天、先週~再來週等時間詞 |
| `data/supplements/clock-date.json` | 照片 0807 轉寫：幾點、幾分、1~12 月、1~31 日 |
| `data/supplements/periods.json` | 照片 0808 轉寫：~時間、~分鐘、~天、~週間、~か月、~年 |
| `data/supplements/counters.json` | 照片 0809 轉寫：16 種量詞各 1~10 加疑問詞 |
| `app/lang/numbers.js`（改） | 加 0、萬、億、小數、分數；修 17／27 日；加 alternatives 表 |
| `app/lang/timewords.js`（新） | 時間詞明表（中文 → 假名） |
| `app/lang/counters.js`（改） | 補量詞：つ、番、着、足、軒、個、杯；加疑問詞與 alternatives；加期間類（日數、週間、か月） |
| `app/generators/quantity.js`（改） | 生成新增題目；支援 alternatives |
| `app/core/concepts.js`／`conceptdefs.js`（改） | 新概念的登記 |
| `tests/app/test_supplements_data.js`（新） | 轉寫檔的格式與漂移偵測（oracle 對程式） |
| `docs/superpowers/plans/2026-10-09-phase2c-acceptance-report.md`（新） | 驗收報告 |

## Transcription 檔案格式（Task 1~5 共用）

每個檔案是 `{ "source": "IMAG0805.jpeg", "rows": [...] }`。一列：

```json
{ "key": "100", "label": "100", "read": ["ひゃく"], "note": "" }
```

- `key`：唯一識別（數字用數值字串，量詞用 `"<counter>:<n>"`，疑問詞 n 用 `"q"`）。
- `label`：講義上的書寫（`3本`、`17日`、`前天`）。
- `read`：**陣列**。第一個是講義列在最前面的讀法（正解），其餘是講義同格列出的並列讀法（`じゅっぷん、じっぷん` → `["じゅっぷん","じっぷん"]`）。
- `note`：只放講義印刷體上的說明（如「（2週間まえ）」）；沒有就空字串。

---

### Task 1: 數字表（照片 0805）

**Files:**
- Create: `data/supplements/numbers.json`
- Create: `tests/app/test_supplements_data.js`
- Modify: `app/lang/numbers.js`

**Interfaces:**
- Produces: `numbers.json` 格式如上；`numbers.js` 新增 `readZero(): string[]`、`readBig(n): string`（`10000 ≤ n ≤ 999999999`，只支援整萬整億以上的位值：見下）、`readDecimal(str): string`、`readFraction(num, den): string`；`NUMBER_ALTS: { [key]: string[] }`
- Consumes: 既有 `readNumber(n)`

- [ ] **Step 1: 轉寫**

開啟 `IMAG0805.jpeg`，逐列寫進 `data/supplements/numbers.json`。範圍：0~20、30~90、100~900、1,000~9,000、10,000／100,000／1,000,000／10,000,000／100,000,000、17.5、0.83、1/2、3/4。`read` 取左欄或右欄印刷體的假名；並列的（0 ゼロ、れい；4 よん、し；7 なな、しち；9 きゅう、く；14 じゅうよん、じゅうし；17 じゅうなな、じゅうしち；19 じゅうきゅう、じゅうく；70 ななじゅう、しちじゅう）全部收進陣列。

- [ ] **Step 2: 寫失敗測試（格式 + 對照）**

`tests/app/test_supplements_data.js`：

```js
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { readNumber, readBig, readDecimal, readFraction, NUMBER_ALTS } from '../../app/lang/numbers.js';

const load = (name) => JSON.parse(readFileSync(new URL(`../../data/supplements/${name}.json`, import.meta.url), 'utf8'));

export function checkShape(file) {
  assert.ok(file.source.endsWith('.jpeg'));
  const keys = new Set();
  for (const r of file.rows) {
    assert.ok(r.key && r.label, `缺 key/label: ${JSON.stringify(r)}`);
    assert.ok(!keys.has(r.key), `key 重複: ${r.key}`);
    keys.add(r.key);
    assert.ok(Array.isArray(r.read) && r.read.length > 0, `${r.key} 缺 read`);
    for (const k of r.read) assert.match(k, /^[ぁ-ゟー]+$|^ゼロ$/, `${r.key} 的讀音含非假名: ${k}`);
  }
}

test('numbers.json 格式正確', () => checkShape(load('numbers')));

test('numbers.json 與 numbers.js 一致', () => {
  for (const r of load('numbers').rows) {
    const n = Number(r.key);
    let got;
    if (r.key.includes('/')) { const [a, b] = r.key.split('/').map(Number); got = readFraction(a, b); }
    else if (r.key.includes('.')) got = readDecimal(r.key);
    else if (n === 0) got = r.read[0];            // 0 另由 Task 1 Step 4 的 readZero 覆蓋
    else if (n >= 10000) got = readBig(n);
    else got = readNumber(n);
    assert.ok(r.read.includes(got), `${r.key}: 講義 ${r.read.join('/')}，程式 ${got}`);
  }
});

test('並列讀法都被接受（NUMBER_ALTS 涵蓋講義的第二讀法）', () => {
  for (const r of load('numbers').rows) {
    if (r.read.length < 2) continue;
    const alts = NUMBER_ALTS[r.key] || [];
    for (const extra of r.read.slice(1)) {
      assert.ok(alts.includes(extra) || r.read[0] === extra, `${r.key} 的並列讀法 ${extra} 未列入 NUMBER_ALTS`);
    }
  }
});
```

- [ ] **Step 3: 跑測試確認失敗**

Run: `node --test tests/app/test_supplements_data.js`
Expected: FAIL（`readBig` 等未匯出）

- [ ] **Step 4: 實作**

在 `app/lang/numbers.js` 末尾加（`readNumber` 不改）：

```js
/** 0 有兩種讀法，講義第一個是ゼロ。 */
export function readZero() { return ['ゼロ', 'れい']; }

/**
 * 一萬以上。位值只有「萬」「億」兩個，其餘用 readNumber（<10000）接上去：
 * 10000 いちまん（萬位的 1 要唸出來，不像百、千可省）、100000 じゅうまん、
 * 1000000 ひゃくまん、10000000 せんまん、100000000 いちおく。
 * 本函式不處理「億」之下的混合數（如 12345678），講義沒有，也不需要。
 */
export function readBig(n) {
  need(n, 10000, 999999999, 'readBig');
  if (n >= 100000000) {
    const o = Math.floor(n / 100000000);
    const rest = n % 100000000;
    return readNumber(o) + 'おく' + (rest ? readBig(rest) : '');
  }
  const m = Math.floor(n / 10000);
  const rest = n % 10000;
  return readNumber(m) + 'まん' + (rest ? readNumber(rest) : '');
}

const DIGIT_KANA = ['れい', 'いち', 'に', 'さん', 'よん', 'ご', 'ろく', 'なな', 'はち', 'きゅう'];

/** 小數：整數部 + てん + 逐位數字（17.5 → じゅうななてんご）。整數部為 0 讀れい。 */
export function readDecimal(str) {
  const [i, f] = String(str).split('.');
  if (!/^\d+$/.test(i) || !/^\d+$/.test(f || '')) throw new Error(`readDecimal: 不是小數 ${JSON.stringify(str)}`);
  const head = Number(i) === 0 ? 'れい' : readNumber(Number(i));
  return head + 'てん' + [...f].map((c) => DIGIT_KANA[Number(c)]).join('');
}

/** 分數：分母＋ぶんの＋分子（1/2 → にぶんのいち）。 */
export function readFraction(num, den) {
  need(num, 1, 99, 'readFraction'); need(den, 2, 99, 'readFraction');
  return readNumber(den) + 'ぶんの' + readNumber(num);
}

/** 講義列出的並列讀法（key 同 numbers.json）。第一讀法由函式產生，這裡只放其餘的。 */
export const NUMBER_ALTS = {
  4: ['し'], 7: ['しち'], 9: ['く'],
  14: ['じゅうし'], 17: ['じゅうしち'], 19: ['じゅうく'], 70: ['しちじゅう'],
};
```

此步的 `NUMBER_ALTS` 先依 Step 1 轉寫出的實際並列讀法填；**若轉寫與上表不同，以照片為準並修正此表**。

- [ ] **Step 5: 跑測試確認通過**

Run: `node --test tests/app/test_supplements_data.js tests/app/test_numbers.js`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add data/supplements/numbers.json tests/app/test_supplements_data.js app/lang/numbers.js
git commit -m "feat(data): 補充講義數字表轉寫，加萬、億、小數、分數"
```

---

### Task 2: 時間詞（照片 0806）

**Files:**
- Create: `data/supplements/timewords.json`
- Create: `app/lang/timewords.js`
- Modify: `tests/app/test_supplements_data.js`

**Interfaces:**
- Produces: `timewords.js` 匯出 `TIMEWORDS: Array<{ key, zh, kana, alts: string[], group }>`；`group` 為 `'weekday' | 'day' | 'morning' | 'evening' | 'week' | 'month' | 'year'`
- Consumes: Task 1 的 `checkShape`

- [ ] **Step 1: 轉寫**

開啟 `IMAG0806.jpeg`。範圍：七個曜日加何曜日；日子（おととい／きのう／きょう／あした／あさって／まいにち）；早上（おとといのあさ…けさ…まいあさ）；晚上（…こんばん、ゆうべ…まいばん）；週（せんせんしゅう…まいしゅう）；月（せんせんげつ…まいつき）；年（おととし／きょねん／ことし／らいねん／さらいねん／まいとし、まいねん）。`label` 用講義上的漢字寫法，`zh` 欄位放講義印的中文（前天、昨天…），都放進 `note`（`label` 是日文漢字、`note` 是中文）。同一格有兩種寫法（`あさ`／`朝`）只收一列。**不收**「2週間まえ」之類括號內的補充說明列。

- [ ] **Step 2: 寫失敗測試**

在 `tests/app/test_supplements_data.js` 末尾加：

```js
import { TIMEWORDS } from '../../app/lang/timewords.js';

test('timewords.json 格式正確', () => checkShape(load('timewords')));

test('timewords.json 與 timewords.js 逐筆一致', () => {
  const byKey = new Map(TIMEWORDS.map((t) => [t.key, t]));
  for (const r of load('timewords').rows) {
    const t = byKey.get(r.key);
    assert.ok(t, `timewords.js 缺 ${r.key}（${r.label}）`);
    assert.equal(t.kana, r.read[0], `${r.key}: 第一讀法不符`);
    assert.deepEqual(t.alts, r.read.slice(1), `${r.key}: 並列讀法不符`);
  }
  assert.equal(TIMEWORDS.length, load('timewords').rows.length, 'timewords.js 多出講義沒有的條目');
});
```

- [ ] **Step 3: 跑測試確認失敗**

Run: `node --test tests/app/test_supplements_data.js`
Expected: FAIL（找不到 `timewords.js`）

- [ ] **Step 4: 實作**

`app/lang/timewords.js` 的內容**由 `timewords.json` 逐列手抄成 JS 陣列**（不在執行期讀 JSON）。形狀：

```js
/**
 * 時間詞明表（補充講義第 II 節）。不寫成規則：おととい／あさって／ゆうべ 這類沒有可推的規律。
 * 與 data/supplements/timewords.json 的一致性由 tests/app/test_supplements_data.js 把關。
 */
export const TIMEWORDS = [
  { key: 'day:-2', zh: '前天', kana: 'おととい', alts: [], group: 'day' },
  // …其餘列由 timewords.json 逐列抄入，key 命名：<group>:<序>，與 JSON 的 key 完全相同
];
```

- [ ] **Step 5: 跑測試確認通過**

Run: `node --test tests/app/test_supplements_data.js`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add data/supplements/timewords.json app/lang/timewords.js tests/app/test_supplements_data.js
git commit -m "feat(data): 補充講義時間詞轉寫與明表"
```

---

### Task 3: 時刻與日期（照片 0807）——含 17／27 日修正

**Files:**
- Create: `data/supplements/clock-date.json`
- Modify: `app/lang/numbers.js`
- Modify: `tests/app/test_supplements_data.js`

**Interfaces:**
- Produces: `numbers.js` 新增 `CLOCK_ALTS: { [key]: string[] }`（key 如 `minute:10`、`minute:7`、`minute:30`）；`readDayOfMonth(17)` 回 `じゅうしちにち`、`readDayOfMonth(27)` 回 `にじゅうしちにち`
- Consumes: Task 1 的 `checkShape`、`load`

- [ ] **Step 1: 轉寫**

開啟 `IMAG0807.jpeg`。key 命名：`hour:1`~`hour:12`、`hour:q`（なんじ）；`minute:1`~`minute:10`、`minute:15`、`minute:30`、`minute:q`；`month:1`~`month:12`、`month:q`；`day:1`~`day:31`、`day:q`。30 分除 `さんじゅっぷん`／`さんじっぷん` 外，講義另列「はん（半）」，key 用 `minute:half`，label `半`。

- [ ] **Step 2: 寫失敗測試**

```js
import { readHour, readMinute, readDayOfMonth, readMonth, CLOCK_ALTS } from '../../app/lang/numbers.js';

test('clock-date.json 格式正確', () => checkShape(load('clock-date')));

test('clock-date.json 與 numbers.js 一致', () => {
  const fn = { hour: readHour, minute: readMinute, month: readMonth, day: readDayOfMonth };
  for (const r of load('clock-date').rows) {
    const [kind, v] = r.key.split(':');
    if (v === 'q' || v === 'half') continue;          // 疑問詞與「半」另由 Task 5 的 Q 表／下方獨立測試覆蓋
    const got = fn[kind](Number(v));
    assert.equal(got, r.read[0], `${r.key}: 講義 ${r.read[0]}，程式 ${got}`);
    const alts = CLOCK_ALTS[r.key] || [];
    for (const extra of r.read.slice(1)) assert.ok(alts.includes(extra), `${r.key} 的並列讀法 ${extra} 未列入 CLOCK_ALTS`);
  }
});

test('17日、27日 唸 しち（不是なな）', () => {
  assert.equal(readDayOfMonth(17), 'じゅうしちにち');
  assert.equal(readDayOfMonth(27), 'にじゅうしちにち');
});
```

- [ ] **Step 3: 跑測試確認失敗**

Run: `node --test tests/app/test_supplements_data.js`
Expected: FAIL（17日／27日 與 `CLOCK_ALTS` 未匯出）

- [ ] **Step 4: 實作**

`app/lang/numbers.js`：在 `DAY_IRREGULAR` 補 `17: 'じゅうしちにち', 27: 'にじゅうしちにち'`；加：

```js
/** 講義同格列出的並列讀法。第一讀法由 readHour/readMinute/... 產生。key 同 clock-date.json。 */
export const CLOCK_ALTS = {
  'minute:7': ['しちふん'],
  'minute:10': ['じっぷん'],
  'minute:30': ['さんじっぷん'],
};
```

**若轉寫發現其他不一致（如 14 日、19 日、24 日的讀法與現有表不同），以照片為準，修表並在驗收報告記錄。** 測試會逐筆揪出，不必靠記憶。

- [ ] **Step 5: 跑測試確認通過**

Run: `node --test tests/app/test_supplements_data.js tests/app/test_numbers.js`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add data/supplements/clock-date.json app/lang/numbers.js tests/app/test_supplements_data.js
git commit -m "fix(lang): 17日27日唸しち，並列讀法列表，對照補充講義"
```

---

### Task 4: 期間（照片 0808）

**Files:**
- Create: `data/supplements/periods.json`
- Modify: `app/lang/counters.js`
- Modify: `tests/app/test_supplements_data.js`

**Interfaces:**
- Produces: `COUNTERS` 新增 `nichi_span`（～日間，label `日`）、`shuukan`（～週間）、`kagetsu`（～か月）；每個量詞新增選用欄位 `alts: { [n]: string[] }` 與 `q: string`（疑問詞讀法，如 `なんじかん`）；`readCounterAlts(n, key): string[]`、`readCounterQ(key): string`
- Consumes: 既有 `withNumberOverrides`、`readCounter`

- [ ] **Step 1: 轉寫**

開啟 `IMAG0808.jpeg`。key：`jikan:1`~`jikan:10`／`jikan:q`、`fun:1`~`fun:10`／`fun:q`（分鐘，內容與 `minute` 同）、`nichi:1`~`nichi:10`／`nichi:q`、`shuukan:1`~`10`／`q`、`kagetsu:1`~`10`／`q`、`nen:1`~`10`／`q`。`kagetsu:6` 另收「半年」（はんとし，key `kagetsu:6`、`read` 並列）。

- [ ] **Step 2: 寫失敗測試**

```js
import { readCounter, readCounterAlts, readCounterQ } from '../../app/lang/counters.js';

test('periods.json 格式正確', () => checkShape(load('periods')));

test('periods.json 與 counters.js 一致', () => {
  const map = { jikan: 'jikan', nen: 'nen', shuukan: 'shuukan', kagetsu: 'kagetsu', nichi: 'nichi_span' };
  for (const r of load('periods').rows) {
    const [kind, v] = r.key.split(':');
    if (kind === 'fun') continue;                     // 分鐘與 minute 同表，已由 Task 3 覆蓋
    const key = map[kind];
    const got = v === 'q' ? readCounterQ(key) : readCounter(Number(v), key);
    assert.equal(got, r.read[0], `${r.key}: 講義 ${r.read[0]}，程式 ${got}`);
    if (v !== 'q') {
      const alts = readCounterAlts(Number(v), key);
      for (const extra of r.read.slice(1)) assert.ok(alts.includes(extra), `${r.key} 並列讀法 ${extra} 未列入 alts`);
    }
  }
});

test('4時間是よじかん、不是よんじかん', () => {
  assert.equal(readCounter(4, 'jikan'), 'よじかん');
});

test('1天（期間）是いちにち，與日期的ついたち不同', () => {
  assert.equal(readCounter(1, 'nichi_span'), 'いちにち');
  assert.equal(readCounter(2, 'nichi_span'), 'ふつか');
});
```

- [ ] **Step 3: 跑測試確認失敗**

Run: `node --test tests/app/test_supplements_data.js`
Expected: FAIL

- [ ] **Step 4: 實作**

`app/lang/counters.js`：`COUNTERS` 條目加選用欄位，`readCounterAlts`／`readCounterQ` 讀它們：

```js
export function readCounterAlts(n, key) {
  const c = COUNTERS[key];
  if (!c) throw new Error(`readCounterAlts: 未知的量詞 ${JSON.stringify(key)}`);
  return (c.alts && c.alts[n]) || [];
}

export function readCounterQ(key) {
  const c = COUNTERS[key];
  if (!c || !c.q) throw new Error(`readCounterQ: ${JSON.stringify(key)} 沒有疑問詞`);
  return c.q;
}
```

並在 `COUNTERS` 新增（`table` 一律明表，從 `periods.json` 抄入；下為已知結構，具體值以轉寫結果為準）：

```js
nichi_span: { kana: 'にち', label: '日間', lesson: 5,
  table: { 1: 'いちにち', 2: 'ふつか', 3: 'みっか', 4: 'よっか', 5: 'いつか',
           6: 'むいか', 7: 'なのか', 8: 'ようか', 9: 'ここのか', 10: 'とおか' },
  q: 'なんにち' },
shuukan: { kana: 'しゅうかん', label: '週間', lesson: 11, table: /* 10 項，由 periods.json 抄入 */, alts: { /* 7:['しちしゅうかん'], 10:['じっしゅうかん'] 等，依轉寫 */ }, q: 'なんしゅうかん' },
kagetsu: { kana: 'かげつ', label: 'か月', lesson: 11, table: /* 同上 */, alts: { /* 依轉寫 */ }, q: 'なんかげつ' },
```

既有的 `jikan`、`nen` 加 `q`（`なんじかん`、`なんねん`）與 `alts`（`jikan` 7 的 `ななじかん`；`nen` 7 的 `ななねん`、9 的 `くねん`；**以轉寫的第一讀法為正解，其餘進 alts**，若轉寫的第一讀法與現有 `withNumberOverrides` 不同，以照片為準修 overrides）。
`ほか`：`nichi_span` 的 label 用 `日間`（prompt 顯示 `3日間`）以與日期題的 `3日` 區分（Review Focus #5）。

- [ ] **Step 5: 跑測試確認通過**

Run: `node --test tests/app/test_supplements_data.js tests/app/test_counters.js`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add data/supplements/periods.json app/lang/counters.js tests/app/test_supplements_data.js
git commit -m "feat(lang): 期間表達（日間、週間、か月）與疑問詞、並列讀法"
```

---

### Task 5: 量詞表（照片 0809）

**Files:**
- Create: `data/supplements/counters.json`
- Modify: `app/lang/counters.js`
- Modify: `tests/app/test_supplements_data.js`

**Interfaces:**
- Produces: `COUNTERS` 新增 `tsu`（つ）、`ban`（番）、`chaku`（着）、`soku`（足）、`ken`（軒）、`ko`（個）、`hai`（杯）；既有 `hon／hiki／satsu／sai／kai_floor／kai_times／nin／mai／dai` 補 `q` 與 `alts`
- Consumes: Task 4 的 `readCounterAlts`、`readCounterQ`

- [ ] **Step 1: 轉寫**

開啟 `IMAG0809.jpeg`，一個量詞一個群組。key：`tsu:1`~`tsu:10`／`tsu:q`（ひとつ…とお／いくつ）、`nin`、`ban`、`mai`、`dai`、`sai`、`satsu`、`chaku`、`kai_times`（講義的「…回」）、`ko`、`soku`、`ken`、`kai_floor`（講義的「…階」）、`hon`、`hai`、`hiki`，各 `1`~`10` 加 `q`。照片右半部量詞表是斜拍，個別列字小：看不清的一律先標進 `note: "?"` 並列入驗收報告，**不得猜**。

- [ ] **Step 2: 寫失敗測試**

```js
test('counters.json 格式正確', () => checkShape(load('counters')));

test('counters.json 與 counters.js 逐筆一致，且 alts 涵蓋講義並列讀法', () => {
  for (const r of load('counters').rows) {
    const [key, v] = r.key.split(':');
    const got = v === 'q' ? readCounterQ(key) : readCounter(Number(v), key);
    assert.equal(got, r.read[0], `${r.key}: 講義 ${r.read[0]}，程式 ${got}`);
    if (v !== 'q') {
      const alts = readCounterAlts(Number(v), key);
      for (const extra of r.read.slice(1)) assert.ok(alts.includes(extra), `${r.key} 並列讀法 ${extra} 未列入 alts`);
    }
  }
});

test('講義上每種量詞在程式裡都有（不會漏收）', () => {
  const inJson = new Set(load('counters').rows.map((r) => r.key.split(':')[0]));
  for (const k of inJson) assert.ok(COUNTERS[k], `COUNTERS 缺 ${k}`);
});

test('疑問詞連濁：なんぼん／なんびき／なんがい', () => {
  assert.equal(readCounterQ('hon'), 'なんぼん');
  assert.equal(readCounterQ('hiki'), 'なんびき');
  assert.equal(readCounterQ('kai_floor'), 'なんがい');
});
```

`COUNTERS` 需在測試檔頂端另行 `import { COUNTERS }`。

- [ ] **Step 3: 跑測試確認失敗**

Run: `node --test tests/app/test_supplements_data.js`
Expected: FAIL

- [ ] **Step 4: 實作**

在 `app/lang/counters.js` 加入七個新量詞，並為既有量詞補 `q`／`alts`。**全部 `table` 一律明表、值由 `counters.json` 抄入**。已讀到的結構：

- `tsu`：1~10 不是「數字＋つ」，是ひとつ、ふたつ、みっつ、よっつ、いつつ、むっつ、ななつ、やっつ、ここのつ、とお；`q: 'いくつ'`。
- `ban`、`chaku`、`soku`、`ken`、`ko`、`hai`：音變型態不同，逐表抄；10 的並列 `じゅっ／じっ` 進 `alts`。
- `q` 一律依照片：`なんばん`、`なんちゃく`、`なんぞく`、`なんげん`、`なんこ`、`なんばい`。

`lesson`（解鎖課次）的決定方式：**在 `data/lessons/01.json`~`15.json` 的詞彙／本文中搜尋該量詞的假名或漢字，取第一個出現的課次**；15 課內都搜不到者（預期有 着、軒、匹）填 `15`，並在驗收報告列出「本階段暫排 15 課，待確認課本實際教到哪一課」。不要憑記憶填課次。

- [ ] **Step 5: 跑測試確認通過**

Run: `node --test tests/app/test_supplements_data.js tests/app/test_counters.js`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add data/supplements/counters.json app/lang/counters.js tests/app/test_supplements_data.js
git commit -m "feat(lang): 補充講義量詞表，新增つ、番、着、足、軒、個、杯與疑問詞"
```

---

### Task 6: 出題與概念登記

**Files:**
- Modify: `app/generators/quantity.js`
- Modify: `app/core/concepts.js`、`app/core/conceptdefs.js`
- Modify: `tests/app/test_quantity.js`、`tests/app/test_conceptdefs.js`

**Interfaces:**
- Consumes: Task 1~5 的 `readBig`、`readDecimal`、`readFraction`、`readZero`、`NUMBER_ALTS`、`CLOCK_ALTS`、`TIMEWORDS`、`readCounterAlts`、`readCounterQ`、新 `COUNTERS`
- Produces: 新題目 id：`qty:big:<n>`、`qty:dec:<str>`、`qty:frac:<a>/<b>`、`qty:zero`、`qty:tw:<key>`、`qty:c:<counter>:<n>`（新量詞沿用既有格式）、`qty:c:<counter>:q`、`qty:hour:q` 等疑問詞題

- [ ] **Step 1: 先讀既有概念登記**

Run: `grep -n "n:time\|n:date\|c:hon" app/core/conceptdefs.js app/core/concepts.js tests/app/test_conceptdefs.js`
照既有 `n:time:hour`、`c:hon` 的形狀，為新增概念各補一筆：`n:num:big`、`n:num:decimal`、`n:num:fraction`、`n:time:word`、`n:date:span`，以及每個新量詞的 `c:<key>`（`c:tsu`、`c:ban`、`c:chaku`、`c:soku`、`c:ken`、`c:ko`、`c:hai`、`c:nichi_span`、`c:shuukan`、`c:kagetsu`）。

- [ ] **Step 2: 寫失敗測試**

在 `tests/app/test_quantity.js` 加：

```js
test('新增量詞出題：3個、ひとつ', () => {
  assert.equal(byId.get('qty:c:tsu:1').answer, 'ひとつ');
  assert.equal(byId.get('qty:c:tsu:1').prompt.text, '1つ');
  assert.ok(byId.get('qty:c:ko:3'));
});

test('17日、27日 出題且唸しち', () => {
  assert.equal(byId.get('qty:day:17').answer, 'じゅうしちにち');
  assert.equal(byId.get('qty:day:27').answer, 'にじゅうしちにち');
});

test('期間題與日期題的題幹可分辨：1日（ついたち）vs 1日間（いちにち）', () => {
  assert.equal(byId.get('qty:day:1').prompt.text, '1日');
  assert.equal(byId.get('qty:c:nichi_span:1').prompt.text, '1日間');
  assert.equal(byId.get('qty:c:nichi_span:1').answer, 'いちにち');
});

test('並列讀法進 alternatives：10分 じっぷん 也算對', () => {
  const it = byId.get('qty:minute:10');
  assert.equal(it.answer, 'じゅっぷん');
  assert.ok(it.alternatives.includes('じっぷん'));
});

test('疑問詞題：何本 → なんぼん', () => {
  const it = byId.get('qty:c:hon:q');
  assert.equal(it.prompt.text, '何本');
  assert.equal(it.answer, 'なんぼん');
});

test('萬、億、小數、分數題', () => {
  assert.equal(byId.get('qty:big:10000').answer, 'いちまん');
  assert.equal(byId.get('qty:big:100000000').answer, 'いちおく');
  assert.equal(byId.get('qty:dec:17.5').answer, 'じゅうななてんご');
  assert.equal(byId.get('qty:frac:1/2').answer, 'にぶんのいち');
});

test('時間詞題：前天 → おととい，且歸入數量技能', () => {
  const it = [...byId.values()].find((x) => x.prompt.text === '前天');
  assert.ok(it);
  assert.equal(it.answer, 'おととい');
  assert.deepEqual(it.skills, ['數量']);
});

test('既有 id 不變（作答紀錄靠 id 對應）', () => {
  for (const id of ['qty:hour:4', 'qty:minute:10', 'qty:day:20', 'qty:month:4', 'qty:c:hon:3', 'qty:c:kai_floor:3']) {
    assert.ok(byId.has(id), `既有題目 ${id} 不見了`);
  }
});
```

- [ ] **Step 3: 跑測試確認失敗**

Run: `node --test tests/app/test_quantity.js`
Expected: FAIL

- [ ] **Step 4: 實作**

`app/generators/quantity.js`：

1. `makeItem` 加參數 `alternatives = []` 並寫入題目。
2. `NUMBER_GROUPS` 的值域不動；每題 `alternatives` 取 `CLOCK_ALTS[`${g.kind}:${n}`] || []`；加疑問詞題 `qty:<kind>:q`（`何時` → なんじ，`何分` → なんぷん，`何月` → なんがつ，`何日` → なんにち），答案取自 `clock-date.json` 對應列的第一讀法，**抄成常數放 `numbers.js` 的 `CLOCK_Q`**，由 Task 3 的測試擴充一條比對。
3. 量詞迴圈：`for n` 1~10 後多產一題疑問詞（`何${label}`，id `qty:c:<key>:q`，答案 `readCounterQ`），`alternatives` 取 `readCounterAlts`。
4. 新增生成區塊：`BIG_VALUES = [10000, 100000, 1000000, 10000000, 100000000]`、`DECIMALS = ['17.5', '0.83']`、`FRACTIONS = [[1,2],[3,4]]`、`qty:zero`（答案 `ゼロ`，alternatives `['れい']`）、`百`位音變 `[100,300,600,800]`、`千`位音變 `[1000,3000,8000]`（用 `readNumber`，id `qty:num:<n>`，概念 `n:num:big`）。
5. `TIMEWORDS` 迴圈：`id: qty:tw:<key>`，`prompt.text` 為講義的中文（`zh`），`answer` 為 `kana`，`alternatives` 為 `alts`，概念 `n:time:word`，`lesson` 4（依 Task 5 同樣的搜尋規則決定；搜不到填 15 並記入報告）。

`lesson`／`requires_lesson` 沿用 Task 5 的取得規則，不憑記憶。

- [ ] **Step 5: 跑全套測試**

Run: `node --test "tests/app/*.js"`
Expected: PASS（含 `test_conceptdefs.js`、`test_sw.js`）

- [ ] **Step 6: Commit**

```bash
git add app tests
git commit -m "feat(generators): 補充講義題目——新量詞、期間、疑問詞、萬億小數分數、時間詞"
```

---

### Task 7: 離線快取、驗收報告

**Files:**
- Modify: `sw.js`（`PRECACHE` 加 `app/lang/timewords.js`；`CACHE` 由 `jp-practice-v1` 改為 `jp-practice-v2`）
- Create: `docs/superpowers/plans/2026-10-09-phase2c-acceptance-report.md`

- [ ] **Step 1: 更新 sw.js**

在 `PRECACHE` 的 `app/lang/numbers.js` 前（照字母序）加 `'app/lang/timewords.js',`；`const CACHE = 'jp-practice-v2';`。

- [ ] **Step 2: 跑全套測試**

Run: `node --test "tests/app/*.js"`
Expected: PASS（`test_sw.js` 會在漏列時紅燈）

- [ ] **Step 3: 逐題讀過再驗收（本專案的鐵律）**

```bash
node -e "import('./app/generators/quantity.js').then(m=>{for(const it of m.generate()){const s=it.id;if(/^qty:(c:(tsu|ban|chaku|soku|ken|ko|hai|nichi_span|shuukan|kagetsu)|tw|big|dec|frac|zero|num)|:q$|^qty:day:(17|27)$/.test(s))console.log(it.id,'|',it.prompt.text,'→',it.answer,it.alternatives.length?'('+it.alternatives.join('/')+')':'')}})"
```

把輸出**逐行對照 `IMAG0805`~`IMAG0809` 的照片**讀過（不是看結構對不對、不是看測試綠燈）。重點：新量詞十個值、疑問詞連濁、期間的 1 天、10 的じっ。發現與照片不符：先修 `data/supplements/*.json`（若轉寫錯）或 `app/lang/*`（若程式錯），再重跑。

- [ ] **Step 4: 寫驗收報告**

`docs/superpowers/plans/2026-10-09-phase2c-acceptance-report.md` 必含：新增題數（依題型）、17／27 日修正的記錄、照片上讀不清而未收的列、暫排 15 課的量詞清單與原因、`IMAG0810`~`IMAG0825` 未處理的範圍說明（索引與地圖，使用者決定地圖暫不收）、留給後續階段的項目。

- [ ] **Step 5: 手動瀏覽器驗收（Node 測不到的部分）**

Run: `python3 -m http.server 8000`，開 `http://localhost:8000`，設定只勾「數量」技能、課次範圍 1~15：確認新量詞題、疑問詞題、期間題有出現；輸入並列讀法（如じっぷん）判對；離線（DevTools → Offline）重新整理仍可用，且 Application → Cache Storage 只剩 `jp-practice-v2`。

- [ ] **Step 6: Commit**

```bash
git add sw.js docs/superpowers/plans/2026-10-09-phase2c-acceptance-report.md
git commit -m "docs: Phase 2c 驗收報告，快取版本升為 v2"
```

---

## Self-Review

- **規格覆蓋**：§13 Phase 2c 兩項——「21 張轉寫」（實為前 5 張，其餘範圍已與使用者確認排除）→ Task 1~5；「核對並擴充 `numbers.js`／`counters.js`」→ Task 1、3、4、5 的漂移偵測與擴充；使用者追加的「新量詞、日期讀法可以出題」→ Task 6。
- **佔位檢查**：`timewords.js`、`shuukan`／`kagetsu` 的 `table`、`NUMBER_ALTS` 的完整內容刻意寫成「由轉寫結果抄入」——這些值的唯一來源是照片，計劃書寫死等於憑記憶填，違反 Global Constraints。每處都附有結構、驗證測試與「以照片為準」的規則。
- **型別一致**：`readCounterAlts(n, key)`、`readCounterQ(key)`、`CLOCK_ALTS`、`NUMBER_ALTS` 在 Task 3~6 名稱一致；題目 id 格式在 Task 6 統一列出。
- **Review Focus**：#1 → Task 3 測試；#2 → Task 3、4、5 的 alts 測試與 Task 6「10分 じっぷん」；#3 → Task 4「4時間」測試；#4 → Task 5「疑問詞連濁」測試；#5 → Task 4、6 的「1日 vs 1日間」測試。
