// 規格 §7.4：grade 的自動判定。使用者不需手動評分（自評卡已從設計移除）。
//
// | 條件                                   | grade |
// |-----------------------------------------|-------|
// | 答對，反應時間 < 該題型中位數 × 0.6      | 4 簡單 |
// | 答對                                     | 3 普通 |
// | 答對，但反應時間偏長（> 中位數 × 2）或用過提示 | 2 困難 |
// | 答錯                                     | 1 重來 |

import { isCorrect } from './normalize.js';

const FAST = 0.6;   // 中位數的倍率，低於此視為「簡單」
const SLOW = 2.0;   // 高於此視為「困難」

export function gradeAnswer(input, item, rtMs, medianRtMs, usedHint) {
  const correct = isCorrect(input, item.answer, item.alternatives || []);
  if (!correct) return { correct: false, grade: 1 };
  if (usedHint) return { correct: true, grade: 2 };
  if (!medianRtMs || medianRtMs <= 0) return { correct: true, grade: 3 };
  if (rtMs < medianRtMs * FAST) return { correct: true, grade: 4 };
  if (rtMs > medianRtMs * SLOW) return { correct: true, grade: 2 };
  return { correct: true, grade: 3 };
}
