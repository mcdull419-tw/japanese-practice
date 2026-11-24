// 規格 §7.4：grade 的自動判定。使用者不需手動評分（自評卡已從設計移除）。
//
// | 條件                                   | grade |
// |-----------------------------------------|-------|
// | 答對，反應時間 < 該題型中位數 × 0.6      | 4 簡單 |
// | 答對                                     | 3 普通 |
// | 答對，但反應時間偏長（> 中位數 × 2）或用過提示 | 2 困難 |
// | 答錯                                     | 1 重來 |

import { isCorrect } from './normalize.js';
import { matchesReading } from './reading.js';

const FAST = 0.6;   // 中位數的倍率，低於此視為「簡單」
const SLOW = 2.0;   // 高於此視為「困難」

/**
 * 課本用［ ］或〔 〕標可省略的部分（しずか［な］、［お］くに、〔どうも〕すみません），
 * 開頭的「…」「～」是「接在別的詞後面」的記號（…にん、～くん）。兩者都不必打出來，
 * 也可以照打：每個［ ］各自展開成「有」與「沒有」兩種寫法。
 */
export function expandOptional(s) {
  if (typeof s !== 'string') return [];
  let out = [s.replace(/^[…～〜]+/u, '')];
  const parts = s.match(/［[^］]*］|〔[^〕]*〕/gu) || [];
  for (const p of parts.slice(0, 4)) {
    const inner = p.slice(1, -1);
    out = out.flatMap((x) => [x.replace(p, inner), x.replace(p, '')]);
  }
  return [...new Set([s, ...out])];
}

/**
 * 寫漢字或寫假名都算對（可混寫），見 core/reading.js。
 * 例外是 strictKana 的題目：問的就是讀音（看漢字寫讀音、數字唸法），
 * 收漢字等於把題幹照抄就算對。
 */
function correctAnswer(input, item, { lex, inputLex } = {}) {
  const targets = [item.answer, ...(item.alternatives || [])].flatMap(expandOptional);
  if (isCorrect(input, targets[0], targets.slice(1))) return true;
  if (item.strictKana) return false;
  return targets.some((t) => matchesReading(input, t, lex, inputLex || lex));
}

// dicts：{ lex（振假名詞典）, inputLex（輸入端詞典，見 core/reading.js） }，可省略。
export function gradeAnswer(input, item, rtMs, medianRtMs, usedHint, dicts) {
  const correct = correctAnswer(input, item, dicts);
  if (!correct) return { correct: false, grade: 1 };
  if (usedHint) return { correct: true, grade: 2 };
  if (!medianRtMs || medianRtMs <= 0) return { correct: true, grade: 3 };
  if (rtMs < medianRtMs * FAST) return { correct: true, grade: 4 };
  if (rtMs > medianRtMs * SLOW) return { correct: true, grade: 2 };
  return { correct: true, grade: 3 };
}
