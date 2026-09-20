# Phase 1 驗收報告

日期：2026-09-20
分支：`phase0-extraction`

## 1. 生成的題目總數

以全部 15 課語料（`data/lessons/01.json`~`15.json`）與 `data/verbs.json`（71 筆動詞）即時生成（懶生成，未寫檔）：

| 引擎 | 題數 |
|---|---|
| `recall`（單字，zh→jp／kanji→kana） | 1220 |
| `transform`（動詞變化：て形／ません／ました／ませんでした） | 284 |
| **合計** | **1504** |

實測方式：Node 直接呼叫 `loadLessons` + `buildIndex` + `recall.generate` + `transform.generate`（透過本機 `http.server` 以 `fetch` 取資料，模擬瀏覽器路徑），非憑印象估算。

## 2. 全部自動測試結果

```
node --test "tests/app/*.js"
```

```
tests 70
pass 70
fail 0
cancelled 0
skipped 0
```

70 個既有測試全數維持綠燈，本次新增的 `app/ui/*.js`、`app/main.js`、`index.html` 未新增自動測試（依 Task 13 簡報：ui/ 的驗證方式是本報告的手動／腳本驗收，不用測試框架）。

## 3. Step 2~4 逐項結果

### 3.1 我已實測（本機、非瀏覽器互動）

- **`node --test "tests/app/*.js"`**：70/70 通過（見上）。
- **`app/ui/*.js` 未洩漏核心判斷邏輯**：
  ```
  grep -nE "isCorrect|normalizeAnswer|Math\.pow|retrievability|9 \* " app/ui/*.js
  → ✓ UI 層乾淨
  ```
- **輸入框屬性齊備**（`app/ui/session.js`）：`lang="ja"`、`autocapitalize`、`spellcheck` 各出現 ≥1 次。
- **`app/core/` 與 `app/lang/` 無 DOM 呼叫**：
  ```
  grep -rnE "\bdocument\.|\bwindow\." app/core app/lang
  → ✓ core/lang 無 DOM 呼叫
  ```
- **靜態資源可經 HTTP 載入**（`python3 -m http.server 8000` + `curl`）：
  `index.html`、`app/main.js`、`app/ui/session.js`、`data/lessons/01.json`、`data/lessons/14.json`、`data/verbs.json` 皆回應 `200`。
- **課次範圍過濾（驗收條件 5，逐字腳本實測，非人工點擊）**：
  - 全 15 課：`recall` 1220 題、`transform` 284 題，其中「て形」題 71 題（`requires_lesson` 為 14 或 15）。
  - 設定 `minLesson=1, maxLesson=10` 後，以 `item.lesson >= minLesson && item.requires_lesson <= maxLesson` 過濾：總題數降為 943 題，**て形題數為 0**。
    ```
    ✓ て形題已消失
    ```
- **答錯題後續出現機率提高（驗收條件 4，逐字執行簡報提供的腳本）**：
  ```
  答錯題被選中率 1.000 ；均勻分布基準 0.250
  ✓ 明顯提高
  ```
  （20 題池中，唯一答錯的 i0 在 2000 次抽 5 題的模擬中，被選中率遠高於均勻分布基準，`priority` 公式使其幾乎必被抽中。）
- **匯出／匯入 JSON 不產生重複事件**：涵蓋於既有 70 個測試中的 `test_store.js`「匯出後匯入還原（含去重，不會因重複匯入而膨脹）」，本次未修改 `core/store.js`，維持通過。

### 3.2 待人工確認（我不能做、需要你在真實瀏覽器／手機上操作）

以下規格 Phase 1 驗收條件**我沒有能力實測**，需要你親自確認：

- [ ] 能在**電腦瀏覽器**完成一次含單字題與動詞變化題的真實點擊練習（`http://localhost:8000`）
- [ ] 答對／答錯的畫面回饋是否符合預期、「我這樣寫也對」按鈕實際點擊後行為是否正確
- [ ] 儀表板長條圖在真實畫面上的視覺呈現（我只驗證了資料與 DOM 結構，未渲染截圖確認）
- [ ] **關閉瀏覽器分頁再重新開啟，IndexedDB 進度是否真的保留**——我只讀了 `LocalStore`/`openStore` 的程式碼與既有測試（`MemoryStore` 的行為在 Node 測試中已驗證），Node 環境沒有 IndexedDB，無法端到端驗證瀏覽器裡真的持久化
- [ ] **手機瀏覽器**：版面在手機寬度是否可用、日文輸入法是否未被自動修正干擾（`lang="ja"`／`autocorrect="off"` 等屬性我已確認寫在程式碼裡，但實際 iOS/Android 輸入法行為需要你在真機測試）
- [ ] 用手機連同一 Wi-Fi 存取電腦區網 IP 是否連得上（防火牆、路由器設定我無法測試）

## 4. 已知限制

1. **`app/ui/*.js` 沒有自動測試**——依 Task 13 簡報的設計約束（判斷邏輯都在 core/，ui/ 只做 DOM），本階段用 grep 驗證「沒有邏輯外洩」取代單元測試；DOM 行為本身仍需人工驗收（見 3.2）。
2. **「我這樣寫也對」的資料落地方式**：使用者確認的替代答案存在 `localStorage`（鍵 `jp-practice-user-alternatives`），與唯讀的 `data/corrections.json` 分開，重新載入後會合併回對應題目的 `alternatives`；同時會補記一筆 `grade=3` 的事件到事件日誌，讓 SRS 反映「這題後來確認算對」。這是本任務新增的行為，不在既有 70 個測試涵蓋範圍內，需人工在瀏覽器操作一次「答錯→我這樣寫也對→下一題→回上一頁確認沒有再被判錯」來確認符合預期。
3. **反應時間中位數**採用「目前裝置本機事件」即時計算（每個引擎各自的中位數），初期樣本不足時 `gradeAnswer` 依規格固定給 grade 3，不會誤判——此行為由既有 `test_grading.js` 涵蓋，`main.js` 端未重新測試中位數計算本身（純統計，非核心判斷邏輯，故未擺進 `core/`）。
4. **iOS Safari 私密視窗**：`openStore` 在 IndexedDB 不可用時退回 `MemoryStore`（不會崩潰，但進度不跨頁保留），這是既知風險與既定緩解，Task 14 未新增額外處理。
5. 課次範圍的下界（`minLesson`）目前套用在 `item.lesson`（單字/動詞本身所屬課次），上界（`maxLesson`）套用在 `item.requires_lesson`（規格明訂的過濾依據）；兩者共同生效，預設 `1~15` 時等同不過濾。

## 5. 提交

本報告對應 Task 14 的程式碼提交（`index.html`、`app/main.js`、本檔案），與 Task 13（`app/ui/session.js`、`app/ui/settings.js`、`app/ui/dashboard.js`）分別提交。
