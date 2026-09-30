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

export function renderSettings(host, settings, onChange, deps = {}) {
  const engineBoxes = Object.entries(ENGINE_LABELS).map(([id, label]) =>
    `<label><input id="eng-${id}" type="checkbox" ${settings.engines.includes(id) ? 'checked' : ''}> ${label}</label>`
  ).join('');
  const skillBoxes = SKILLS.map((s, i) =>
    `<label><input id="skill-${i}" type="checkbox" data-skill="${s}" ${settings.skills.includes(s) ? 'checked' : ''}> ${s}</label>`
  ).join('');

  host.innerHTML = `
    <div class="settings">
      <h2>設定</h2>
      <label>起始課次
        <input id="minLesson" type="number" min="1" max="15" value="${settings.minLesson}">
      </label>
      <label>結束課次
        <input id="maxLesson" type="number" min="1" max="15" value="${settings.maxLesson}">
      </label>
      <div class="group-title">題型</div>
      ${engineBoxes}
      <div class="group-title">練習技能</div>
      ${skillBoxes}
      <label>每次題數
        <input id="sessionSize" type="number" min="1" max="100" value="${settings.sessionSize}">
      </label>
      <button id="apply">套用並開始新的一組</button>
      <button id="export-flagged">匯出待確認題目</button>
      <textarea id="flagged-out" rows="8" hidden readonly></textarea>
    </div>`;

  /**
   * 匯出「這題怪怪的」標記過的題目。輸出到 textarea 而不是觸發下載：
   * 這個網站要能離線用（PWA），而沙箱環境對程式觸發的下載限制不一，
   * 顯示出來讓使用者自行複製最可靠，也方便直接貼給別的工具查證。
   */
  const exportBtn = host.querySelector('#export-flagged');
  if (exportBtn) {
    exportBtn.onclick = () => {
      const out = host.querySelector('#flagged-out');
      const rows = typeof deps.exportFlagged === 'function' ? deps.exportFlagged() : [];
      out.value = rows.length
        ? JSON.stringify(rows, null, 1)
        : '目前沒有標記為待確認的題目。';
      out.hidden = false;
      out.select?.();
    };
  }

  host.querySelector('#apply').onclick = () => {
    const min = clampLesson(host.querySelector('#minLesson').value, DEFAULT_SETTINGS.minLesson);
    const max = clampLesson(host.querySelector('#maxLesson').value, DEFAULT_SETTINGS.maxLesson);
    const engines = Object.keys(ENGINE_LABELS).filter((id) => host.querySelector(`#eng-${id}`).checked);
    const skills = SKILLS.filter((_, i) => host.querySelector(`#skill-${i}`).checked);
    const sizeRaw = parseInt(host.querySelector('#sessionSize').value, 10);
    const sessionSize = Number.isFinite(sizeRaw) && sizeRaw > 0 ? sizeRaw : DEFAULT_SETTINGS.sessionSize;
    onChange({
      minLesson: Math.min(min, max),
      maxLesson: Math.max(min, max),
      // 全部取消勾選等於一題都不出，那是使用者操作失誤而非意圖，退回預設值。
      engines: engines.length ? engines : DEFAULT_SETTINGS.engines,
      skills: skills.length ? skills : DEFAULT_SETTINGS.skills,
      sessionSize,
    });
  };
}
