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

const ALPHA_LABELS = [
  ['0', '平均分布'],
  ['1', '偏重生詞'],
  ['2', '大幅偏重生詞'],
];

export function renderPlayer(host, deps) {
  const { items, itemStates, conceptStates, speaker } = deps;
  let timer = null;
  let running = false;

  if (!items.length) {
    host.innerHTML = '<h2>單字循環播放</h2><p class="note">目前的範圍內沒有單字題。</p>';
    return { stop() {} };
  }

  host.innerHTML = `
    <h2>單字循環播放</h2>
    <label>偏重程度
      <select id="alpha">${ALPHA_LABELS.map(([v, l]) =>
        `<option value="${v}"${v === '1' ? ' selected' : ''}>${l}</option>`).join('')}</select>
    </label>
    <label>間隔秒數 <input id="gap" type="number" min="1" max="20" value="4"></label>
    <button id="play">開始播放</button>
    <div class="now"></div>
    <p class="note">播放不計入成績。iOS 鎖屏或切到背景時系統會暫停語音，
      播放期間請保持螢幕開啟。</p>`;

  const nowEl = host.querySelector('.now');
  const playBtn = host.querySelector('#play');

  function step() {
    const alpha = Number(host.querySelector('#alpha').value);
    const gap = Math.max(1, Number(host.querySelector('#gap').value) || 4) * 1000;
    const it = pickForPlayback(items, itemStates, conceptStates, Math.floor(Date.now() / 1000), alpha);
    if (!it) return stop();
    // 日→停頓→中（規格 §6.3）。中文只顯示不朗讀——日文語音唸中文會亂唸。
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
