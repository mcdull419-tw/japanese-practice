// 引擎分派。未知的 engine 退回打字作答而不是拋錯——生成器若新增了題型而忘了
// 加引擎，該題仍可作答，不會讓整輪練習中斷。
import * as text from './text.js';
import * as recall from './recall.js';
import * as transform from './transform.js';
import * as substitute from './substitute.js';
import * as cloze from './cloze.js';

const REGISTRY = { recall, transform, substitute, cloze };

export function engineFor(item) {
  return REGISTRY[item && item.engine] || text;
}
