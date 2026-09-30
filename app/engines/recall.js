/**
 * 對照題。`item.choices` 存在時渲染選擇題（jp2zh），否則與其他引擎一樣是打字作答。
 * 這是引擎層存在的唯一理由（規格 §13 決定 1）。
 */
import { escapeHtml, rubyHtml } from '../ui/html.js';
import * as text from './text.js';

export const ENGINE = 'recall';

export function render(item, host, opts = {}) {
  if (!item.choices || !item.choices.length) return text.render(item, host, opts);

  const prompt = opts.rubyTokens
    ? rubyHtml(opts.rubyTokens, { hideRt: opts.hideRt })
    : escapeHtml(item.prompt.text);
  host.innerHTML = `
    <div class="prompt">${opts.listening ? '<span class="listening">🔊 聽寫：請聽題目作答</span>' : prompt}</div>
    <div class="hint">${escapeHtml(item.prompt.hint || '')}</div>
    <div class="choices">${item.choices.map((c, i) =>
      `<button class="choice" data-i="${i}">${escapeHtml(c)}</button>`).join('')}</div>`;

  if (opts.listening) {
    host.insertAdjacentHTML('afterbegin', '<button id="replay">🔊 再聽一次</button>');
    host.querySelector('#replay').onclick = () => opts.speak?.(item.prompt.text);
    opts.speak?.(item.prompt.text);
  }

  let picked = '';
  for (const btn of host.querySelectorAll('.choice')) {
    btn.onclick = () => {
      picked = item.choices[Number(btn.dataset.i)];
      for (const b of host.querySelectorAll('.choice')) b.classList.remove('picked');
      btn.classList.add('picked');
      // 選擇題選完即送出：再要求按一次「送出」只是多一步，沒有修改空間可言。
      opts.onSubmit?.();
    };
  }
  return { readValue: () => picked };
}
