/**
 * 打字作答的共用渲染。四個引擎裡有三個完全共用這份，recall 只有在選擇題時才分歧
 * ——引擎層的價值在於承載那一處分歧，不是為每個引擎各抄一份 DOM。
 *
 * 判斷邏輯不在這裡：readValue() 只把使用者輸入原樣交出去，對錯一律由
 * core/grading.js 判定（規格 §11 的分層要求）。
 */
import { escapeHtml, rubyHtml } from '../ui/html.js';

export const ENGINE = 'text';

const INPUT_ATTRS = 'lang="ja" autocorrect="off" autocapitalize="off" spellcheck="false" autocomplete="off"';

/**
 * 日文輸入法（IME）組字期間按下的 Enter 是「確定候補字」，不是「送出答案」——
 * 兩者是同一顆實體按鍵，只能靠事件狀態分辨：組字中的 keydown 帶
 * isComposing=true（舊版瀏覽器則是 keyCode 229）。
 *
 * 不分辨的後果不只是提前送出：submit() 會同時把那筆「答錯」寫進事件日誌，
 * 使用者選個字就被記一次答錯，SRS 的熟悉度會被自己的輸入法污染。
 *
 * 只有這兩個欄位都不成立時才視為真的要送出——判斷寫成「有值才擋」而非
 * 「沒值就擋」，否則不帶這些欄位的環境會永遠送不出答案。
 */
export function isImeComposing(e) {
  return e.isComposing === true || e.keyCode === 229;
}

/** 題幹的 HTML：有振假名 token 就用 ruby 渲染，否則純文字。 */
export function promptHtml(item, opts = {}) {
  if (opts.listening) return '<span class="listening">🔊 聽寫：請聽題目作答</span>';
  if (opts.rubyTokens) return rubyHtml(opts.rubyTokens, { hideRt: opts.hideRt });
  return escapeHtml(item.prompt.text).replace(/\n/g, '<br>');
}

export function render(item, host, opts = {}) {
  host.innerHTML = `
    <div class="prompt">${promptHtml(item, opts)}</div>
    <div class="hint">${escapeHtml(item.prompt.hint || '')}</div>
    <input id="ans" type="text" ${INPUT_ATTRS}>`;

  if (opts.listening) {
    // 聽力模式的題幹沒有文字可看，重播鍵是唯一能再取得題目的途徑，不可省。
    host.insertAdjacentHTML('afterbegin', '<button id="replay">🔊 再聽一次</button>');
    host.querySelector('#replay').onclick = () => opts.speak?.(item.prompt.text);
    opts.speak?.(item.prompt.text);
  }

  const input = host.querySelector('#ans');
  input.focus();
  input.onkeydown = (e) => {
    if (e.key === 'Enter' && !isImeComposing(e)) opts.onSubmit?.();
  };
  return { readValue: () => input.value };
}
