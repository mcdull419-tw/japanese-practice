// 組裝入口：把 core/、generators/、ui/ 接起來，成為可在瀏覽器實際使用的應用。
// 這裡是「膠水」層——載入資料、算 SRS 狀態、抽題、渲染三個區塊——本身不做
// 對錯判定／排序／熟悉度計算，那些一律呼叫 core 的對應函式。
import { loadSettings, saveSettings, renderSettings } from './ui/settings.js';
import { renderSession } from './ui/session.js';
import { renderDashboard } from './ui/dashboard.js';
import { loadLessons, buildIndex } from './core/data.js';
import * as recall from './generators/recall.js';
import * as transform from './generators/transform.js';
import { openStore, makeEvent } from './core/store.js';
import { replay } from './core/srs.js';
import { pickItems } from './core/scheduler.js';
import { aggregateSkills } from './core/concepts.js';

const ALT_KEY = 'jp-practice-user-alternatives'; // 使用者「我這樣寫也對」，與 data/corrections.json 分開
const DEVICE_KEY = 'jp-practice-device-id';

function loadUserAlternatives(storageLike) {
  try {
    const raw = storageLike.getItem(ALT_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

function saveUserAlternatives(storageLike, data) {
  try {
    storageLike.setItem(ALT_KEY, JSON.stringify(data));
  } catch {
    // 私密視窗或容量已滿時忽略，僅本次 session 有效。
  }
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

export async function boot(doc = document, win = window) {
  const settingsHost = doc.querySelector('#settings');
  const sessionHost = doc.querySelector('#session');
  const dashboardHost = doc.querySelector('#dashboard');

  const deviceId = getDeviceId(win.localStorage);
  const store = await openStore(win.indexedDB);

  async function runSession(settings) {
    sessionHost.innerHTML = '<p>載入中…</p>';

    // 課次範圍只需載入到 maxLesson（動詞表本身是全量的 71 筆，不受課次範圍影響，
    // 而 requires_lesson 的過濾才是決定哪些題目可用的關鍵，見下方 filter）。
    const lessonNumbers = [...Array(settings.maxLesson)].map((_, i) => i + 1);
    const [lessonsMap, verbsTable] = await Promise.all([
      loadLessons(lessonNumbers, fetchLesson),
      fetchVerbs(),
    ]);
    const idx = buildIndex(lessonsMap);

    // 懶生成：每次啟動／換設定即時展開題目，不預先寫成檔案（規格 §5.4）。
    const allItems = [];
    if (settings.engines.includes('recall')) allItems.push(...recall.generate(idx.vocab));
    if (settings.engines.includes('transform')) allItems.push(...transform.generate(idx.vocab, verbsTable));

    const itemsById = new Map(allItems.map((it) => [it.id, it]));

    const userAlts = loadUserAlternatives(win.localStorage);
    const items = allItems
      .filter((it) => it.lesson >= settings.minLesson && it.requires_lesson <= settings.maxLesson)
      .map((it) => {
        const extra = userAlts[it.id];
        if (!extra || !extra.length) return it;
        return { ...it, alternatives: [...new Set([...(it.alternatives || []), ...extra])] };
      });

    const events = await store.allEvents();
    const nowSec = Math.floor(Date.now() / 1000);
    // §7 熟悉度模型：概念的 A（近十次答對率）需要知道每個事件對應題目的
    // covers 是什麼，故 replay 多收 itemsById；itemStates 只留 lastSec／reps
    // 供排程器算 ΔT（§8.1）。
    const { itemStates, conceptStates } = replay(events, nowSec, itemsById);

    // 技能熟悉度的分母是「複習範圍內全部概念」，不是「練過的概念」（§7.6 核心
    // bug 修復），因此從目前範圍內的候選題庫蒐集 covers，而不是只看 conceptStates。
    const scopeConceptIds = new Set();
    for (const it of items) for (const c of it.covers || []) scopeConceptIds.add(c);
    const { scores: skillScores, counts: skillCounts } = aggregateSkills(conceptStates, scopeConceptIds);
    renderDashboard(dashboardHost, skillScores, skillCounts);

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

    function acceptAlternative(itemId, input) {
      if (!input) return;
      const list = userAlts[itemId] || (userAlts[itemId] = []);
      if (!list.includes(input)) list.push(input);
      saveUserAlternatives(win.localStorage, userAlts);
      // 這次作答已在 submit() 記為答錯；使用者確認可接受後，補記一筆正確事件，
      // 讓 SRS／排程反映「這題其實答對了」，而不是重新實作一套判斷邏輯。
      store.appendEvents([
        makeEvent(deviceId, nextSeq(), itemId, 3, 0, 'text', Math.floor(Date.now() / 1000)),
      ]);
    }

    renderSession(sessionHost, {
      items: sessionItems,
      store,
      settings,
      deviceId,
      nextSeq,
      medianRt,
      acceptAlternative,
      onDone: () => runSession(settings),
    });
  }

  const settings = loadSettings(win.localStorage);
  renderSettings(settingsHost, settings, (newSettings) => {
    saveSettings(win.localStorage, newSettings);
    runSession(newSettings);
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
