// 組裝入口：把 core/、generators/、ui/ 接起來，成為可在瀏覽器實際使用的應用。
// 這裡是「膠水」層——載入資料、算 SRS 狀態、抽題、渲染三個區塊——本身不做
// 對錯判定／排序／熟悉度計算，那些一律呼叫 core 的對應函式。
import { loadSettings, saveSettings, renderSettings } from './ui/settings.js';
import { renderSession } from './ui/session.js';
import { renderDashboard } from './ui/dashboard.js';
import { loadLessons, buildIndex } from './core/data.js';
import * as recall from './generators/recall.js';
import * as transform from './generators/transform.js';
import * as substitute from './generators/substitute.js';
import * as cloze from './generators/cloze.js';
import * as quantity from './generators/quantity.js';
import * as drillGen from './generators/drills.js';
import { conceptsByPattern } from './core/conceptdefs.js';
import { openStore, makeEvent, makeFlagEvent, userAlternativesFrom, flaggedFrom }
  from './core/store.js';
import { exportFlagged, applyCorrections } from './core/corrections.js';
import { replay } from './core/srs.js';
import { pickItems } from './core/scheduler.js';
import { aggregateSkills } from './core/concepts.js';
import { buildLexicon } from './core/ruby.js';
import { presentOptsFor } from './ui/present.js';

// 舊版把「我這樣寫也對」的寫法存在這個 localStorage 鍵，違反規格 §9.2.1
// （應與事件日誌同一個 Store）。現已改存事件的 `a` 欄位，此鍵只剩遷移用途。
const LEGACY_ALT_KEY = 'jp-practice-user-alternatives';
const DEVICE_KEY = 'jp-practice-device-id';

/**
 * 一次性遷移：把舊版存在 localStorage 的自訂答案補寫成事件，然後刪掉該鍵。
 *
 * 時戳一律取 0：這些寫法的真實認可時間已經遺失，給 0 讓它們排在所有真實作答
 * 之前，不會污染任何一題的 ΔT（§8.1 只看該題最後一次作答的時戳）。grade 給 3
 * 與當初補記的那筆一致。
 *
 * 回傳補寫的事件數，供呼叫端判斷是否需要重讀。
 */
export async function migrateLegacyAlternatives(storageLike, store, deviceId, startSeq) {
  let parsed;
  try {
    const raw = storageLike.getItem(LEGACY_ALT_KEY);
    if (!raw) return 0;
    parsed = JSON.parse(raw);
  } catch {
    return 0;
  }
  const evs = [];
  let seq = startSeq;
  for (const [itemId, alts] of Object.entries(parsed || {})) {
    for (const alt of alts || []) {
      evs.push(makeEvent(deviceId, (seq += 1), itemId, 3, 0, 'text', 0, alt));
    }
  }
  if (evs.length) await store.appendEvents(evs);
  try {
    storageLike.removeItem(LEGACY_ALT_KEY);
  } catch {
    // 移除失敗也無妨：重建 alternatives 一律以事件為準，重跑遷移只會寫入
    // (d, n) 相同的事件，被 mergeEvents 去重，不會產生重複。
  }
  return evs.length;
}

function getDeviceId(storageLike) {
  try {
    let id = storageLike.getItem(DEVICE_KEY);
    if (!id) {
      id = `dev-${Math.random().toString(36).slice(2)}-${Date.now().toString(36)}`;
      storageLike.setItem(DEVICE_KEY, id);
    }
    return id;
  } catch {
    // 無法持久化裝置 id 時退回一次性 id，仍可運作（僅無法跨 session 延續序號）。
    return `dev-ephemeral-${Math.random().toString(36).slice(2)}`;
  }
}

function median(arr) {
  if (!arr.length) return 0;
  const sorted = [...arr].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[mid] : (sorted[mid - 1] + sorted[mid]) / 2;
}

async function fetchLesson(n) {
  const res = await fetch(`data/lessons/${String(n).padStart(2, '0')}.json`);
  if (!res.ok) throw new Error(`第 ${n} 課資料載入失敗：${res.status}`);
  return res.json();
}

async function fetchVerbs() {
  const res = await fetch('data/verbs.json');
  if (!res.ok) throw new Error(`verbs.json 載入失敗：${res.status}`);
  return res.json();
}

async function fetchJson(path) {
  const res = await fetch(path);
  if (!res.ok) throw new Error(`${path} 載入失敗：${res.status}`);
  return res.json();
}

export async function boot(doc = document, win = window) {
  const settingsHost = doc.querySelector('#settings');
  const sessionHost = doc.querySelector('#session');
  const dashboardHost = doc.querySelector('#dashboard');

  const deviceId = getDeviceId(win.localStorage);
  const store = await openStore(win.indexedDB);

  // 舊版的自訂答案存在 localStorage，補寫成事件後刪除該鍵（規格 §9.2.1）。
  const existing = await store.allEvents();
  let maxSeq = -1;
  for (const ev of existing) if (ev.d === deviceId && ev.n > maxSeq) maxSeq = ev.n;
  await migrateLegacyAlternatives(win.localStorage, store, deviceId, maxSeq);

  async function runSession(settings) {
    sessionHost.innerHTML = '<p>載入中…</p>';

    // 課次範圍只需載入到 maxLesson（動詞表本身是全量的 71 筆，不受課次範圍影響，
    // 而 requires_lesson 的過濾才是決定哪些題目可用的關鍵，見下方 filter）。
    const lessonNumbers = [...Array(settings.maxLesson)].map((_, i) => i + 1);
    const [lessonsMap, verbsTable, adjTable, conceptDefs, particleMarks, rubyJson,
      drillsJson, correctionsJson] =
      await Promise.all([
        loadLessons(lessonNumbers, fetchLesson),
        fetchVerbs(),
        fetchJson('data/adjectives.json'),
        fetchJson('data/concepts.json'),
        fetchJson('data/particles.json'),
        fetchJson('data/ruby-lexicon.json'),
        fetchJson('data/drills.json'),
        fetchJson('data/corrections.json').catch(() => ({})),
      ]);
    const idx = buildIndex(lessonsMap);
    const lex = buildLexicon(rubyJson);

    // 規格 §9.3：句子有課本的精確標註時優先使用，練習Ａ／Ｂ 才退回詞典。
    const sentenceMarks = new Map();
    for (const s of idx.sentences) if (s.ruby?.length) sentenceMarks.set(s.id, s.ruby);

    // 懶生成：每次啟動／換設定即時展開題目，不預先寫成檔案（規格 §5.4）。
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
      // 練習Ｂ 的素材結構與練習Ａ 不同（逐列人工書寫，非代入表，見規格 §13
      // 決定 11），故走自己的生成器；作答形式相同，仍是 substitute 引擎。
      allItems.push(...drillGen.generate(drillsJson, byPattern));
    }
    if (settings.engines.includes('cloze')) {
      allItems.push(...cloze.generate(idx.sentences, particleMarks, idx.vocab));
    }

    const itemsById = new Map(allItems.map((it) => [it.id, it]));

    // events 在本輪練習期間持續累積（每答一題 push 一筆），供儀表板即時重算。
    const events = await store.allEvents();

    // 規格 §9.2.1：自訂答案由事件日誌重建，不讀 localStorage。
    const userAlts = userAlternativesFrom(events);
    // 題庫更正先套（靜態檔，記的是題庫本身錯了），使用者的自訂答案後套，
    // 兩者疊加而非互相取代（規格 §9.2.1）。
    const correctedItems = applyCorrections(allItems, correctionsJson);
    const items = correctedItems
      .filter((it) => it.lesson >= settings.minLesson
        && it.requires_lesson <= settings.maxLesson
        && (it.skills || []).some((s) => settings.skills.includes(s)))
      .map((it) => {
        const extra = userAlts.get(it.id);
        if (!extra || !extra.length) return it;
        return { ...it, alternatives: [...new Set([...(it.alternatives || []), ...extra])] };
      });

    const nowSec = Math.floor(Date.now() / 1000);
    // §7 熟悉度模型：概念的 A（近十次答對率）需要知道每個事件對應題目的
    // covers 是什麼，故 replay 多收 itemsById；itemStates 只留 lastSec／reps
    // 供排程器算 ΔT（§8.1）。
    const { itemStates, conceptStates } = replay(events, nowSec, itemsById);

    // 技能熟悉度的分母是「複習範圍內全部概念」，不是「練過的概念」（§7.6 核心
    // bug 修復），因此從目前範圍內的候選題庫蒐集 covers，而不是只看 conceptStates。
    const scopeConceptIds = new Set();
    for (const it of items) for (const c of it.covers || []) scopeConceptIds.add(c);

    /**
     * 規格 §7.6：每答完一題即重畫儀表板。練到一半數字完全不動的話，使用者無從
     * 分辨「數字沒變」與「功能壞了」。
     *
     * 這裡是全量重放，不做增量。實測（本機 Node）：1000 筆 0.5ms、5000 筆 0.9ms、
     * 20000 筆 1.8ms、60000 筆 4.9ms。規格 §10.1 估一年約 2 萬筆，即 1.8ms，
     * 遠低於一個影格，增量的複雜度不值得。
     */
    function refreshDashboard() {
      const { conceptStates: cs } = replay(events, Math.floor(Date.now() / 1000), itemsById);
      const { scores, counts } = aggregateSkills(cs, scopeConceptIds);
      renderDashboard(dashboardHost, scores, counts);
    }
    refreshDashboard();

    const sessionItems = pickItems(items, itemStates, conceptStates, settings.sessionSize, nowSec, Math.random);

    let seqCounter = -1;
    for (const ev of events) if (ev.d === deviceId && ev.n > seqCounter) seqCounter = ev.n;
    const nextSeq = () => (seqCounter += 1);

    const rtByEngine = new Map();
    for (const ev of events) {
      const it = itemsById.get(ev.i);
      if (!it) continue;
      if (!rtByEngine.has(it.engine)) rtByEngine.set(it.engine, []);
      rtByEngine.get(it.engine).push(ev.r);
    }
    const medianRt = (engine) => median(rtByEngine.get(engine) || []);

    /** 練習畫面每記錄一筆事件就回呼，讓儀表板跟上。 */
    function onAnswered(ev) {
      events.push(ev);
      refreshDashboard();
    }

    /**
     * 規格 §9.2.1：補記一筆 g=3 且 a=使用者寫法 的事件。這一筆同時修正 SRS 的
     * 錯誤歸因，並讓該寫法成為此題的 alternative。
     *
     * 必須 await：這個按鈕存在的理由就是「不讓誤判污染排程」，若使用者按完立刻
     * 關閉分頁而寫入還沒落地，這個安全網等於沒作用。
     */
    async function acceptAlternative(itemId, input) {
      if (!input) return;
      const ev = makeEvent(deviceId, nextSeq(), itemId, 3, 0, 'text', Math.floor(Date.now() / 1000), input);
      await store.appendEvents([ev]);
      // 本輪若因 lapse re-drill 再次出到同一題，同樣寫法要立刻算對，不必等下一輪。
      const live = sessionItems.find((it) => it.id === itemId);
      if (live) live.alternatives = [...new Set([...(live.alternatives || []), input])];
      onAnswered(ev);
    }

    /** 「這題怪怪的」：補記一筆 flag 事件。必須 await，理由同 acceptAlternative。 */
    async function flagItem(itemId) {
      const ev = makeFlagEvent(deviceId, nextSeq(), itemId, Math.floor(Date.now() / 1000));
      await store.appendEvents([ev]);
      events.push(ev);
    }

    // 待確認清單掛在 window 上供設定區的匯出鈕取用：題庫是每輪重新展開的，
    // 匯出時需要的是「這一輪的 itemsById」，不是模組載入時的快照。
    win.__jpExportFlagged = () => exportFlagged(flaggedFrom(events), itemsById);

    renderSession(sessionHost, {
      items: sessionItems,
      store,
      settings,
      deviceId,
      nextSeq,
      medianRt,
      acceptAlternative,
      onAnswered,
      presentOpts: (it) => presentOptsFor(it, { lex, sentenceMarks }),
      flagItem,
      onDone: () => runSession(settings),
    });
  }

  const settings = loadSettings(win.localStorage);
  renderSettings(settingsHost, settings, (newSettings) => {
    saveSettings(win.localStorage, newSettings);
    runSession(newSettings);
  }, {
    // 每輪練習會重建題庫，因此這裡取的是「當下那一輪」的匯出函式，
    // 不是模組載入時的快照。
    exportFlagged: () => (win.__jpExportFlagged ? win.__jpExportFlagged() : []),
  });

  await runSession(settings);
}

if (typeof document !== 'undefined' && typeof window !== 'undefined') {
  boot().catch((err) => {
    console.error(err);
    const host = document.querySelector('#session') || document.body;
    host.innerHTML = `<pre style="color:red;white-space:pre-wrap">初始化失敗：${String(err && err.message || err)}</pre>`;
  });
}
