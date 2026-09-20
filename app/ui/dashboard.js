// 儀表板：顯示規格 §7.6 的六類技能熟悉度長條。
// skillScores 與 counts 皆由呼叫端（core 的 replay + aggregateSkills）事先算好傳入，
// 這裡只負責畫圖，不做任何熟悉度計算。
import { SKILLS } from '../core/concepts.js';

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) =>
    ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
}

export function renderDashboard(host, skillScores, counts) {
  const rows = SKILLS.map((skill) => {
    const score = skillScores ? skillScores[skill] : null;
    const count = counts && counts[skill] ? counts[skill] : 0;
    if (score == null) {
      return `
        <div class="skill-row">
          <div class="skill-name">${escapeHtml(skill)}</div>
          <div class="skill-bar unseen">尚未練習</div>
          <div class="skill-count">${count} 題</div>
        </div>`;
    }
    const pct = Math.round(Math.min(1, Math.max(0, score)) * 100);
    return `
      <div class="skill-row">
        <div class="skill-name">${escapeHtml(skill)}</div>
        <div class="skill-bar">
          <div class="skill-fill" style="width:${pct}%"></div>
          <span class="skill-pct">${pct}%</span>
        </div>
        <div class="skill-count">${count} 題</div>
      </div>`;
  }).join('');

  host.innerHTML = `<div class="dashboard"><h2>技能熟悉度</h2>${rows}</div>`;
}
