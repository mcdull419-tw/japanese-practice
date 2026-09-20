// 設定畫面：課次範圍、題型開關、每次題數。純 DOM／localStorage 存取，不含判斷邏輯。

export const DEFAULT_SETTINGS = { minLesson: 1, maxLesson: 15, engines: ['recall', 'transform'], sessionSize: 20 };

const STORAGE_KEY = 'jp-practice-settings';

export function loadSettings(storageLike) {
  try {
    const raw = storageLike.getItem(STORAGE_KEY);
    if (!raw) return { ...DEFAULT_SETTINGS };
    const parsed = JSON.parse(raw);
    return { ...DEFAULT_SETTINGS, ...parsed };
  } catch {
    // 私密視窗或儲存被封鎖時 getItem/JSON.parse 可能拋錯，回預設值。
    return { ...DEFAULT_SETTINGS };
  }
}

export function saveSettings(storageLike, s) {
  try {
    storageLike.setItem(STORAGE_KEY, JSON.stringify(s));
  } catch {
    // 寫入失敗（私密視窗、容量已滿）時忽略，設定僅本次有效。
  }
}

function clampLesson(v, fallback) {
  const n = parseInt(v, 10);
  if (Number.isNaN(n)) return fallback;
  return Math.min(15, Math.max(1, n));
}

export function renderSettings(host, settings, onChange) {
  host.innerHTML = `
    <div class="settings">
      <h2>設定</h2>
      <label>起始課次
        <input id="minLesson" type="number" min="1" max="15" value="${settings.minLesson}">
      </label>
      <label>結束課次
        <input id="maxLesson" type="number" min="1" max="15" value="${settings.maxLesson}">
      </label>
      <label><input id="eng-recall" type="checkbox" ${settings.engines.includes('recall') ? 'checked' : ''}> 單字題</label>
      <label><input id="eng-transform" type="checkbox" ${settings.engines.includes('transform') ? 'checked' : ''}> 動詞變化題</label>
      <label>每次題數
        <input id="sessionSize" type="number" min="1" max="100" value="${settings.sessionSize}">
      </label>
      <button id="apply">套用並開始新的一組</button>
    </div>`;

  host.querySelector('#apply').onclick = () => {
    const min = clampLesson(host.querySelector('#minLesson').value, DEFAULT_SETTINGS.minLesson);
    const max = clampLesson(host.querySelector('#maxLesson').value, DEFAULT_SETTINGS.maxLesson);
    const engines = [];
    if (host.querySelector('#eng-recall').checked) engines.push('recall');
    if (host.querySelector('#eng-transform').checked) engines.push('transform');
    const sizeRaw = parseInt(host.querySelector('#sessionSize').value, 10);
    const sessionSize = Number.isFinite(sizeRaw) && sizeRaw > 0 ? sizeRaw : DEFAULT_SETTINGS.sessionSize;
    onChange({
      minLesson: Math.min(min, max),
      maxLesson: Math.max(min, max),
      engines: engines.length ? engines : DEFAULT_SETTINGS.engines,
      sessionSize,
    });
  };
}
