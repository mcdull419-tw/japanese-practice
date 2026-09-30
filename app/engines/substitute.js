// 代入題。題幹是「例：…／用這些詞造句：…」的多行文字，需要保留換行。
import * as text from './text.js';

export const ENGINE = 'substitute';

export function render(item, host, opts = {}) {
  const handle = text.render(item, host, opts);
  host.querySelector('.prompt')?.classList.add('multiline');
  return handle;
}
