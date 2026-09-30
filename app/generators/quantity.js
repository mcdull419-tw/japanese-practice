/**
 * 數量題（需求 #4 數字時間日期、#7 量詞）。
 *
 * engine 是 'recall'——機制就是對照題「給 X 求 Y」，規格 §6.1 明定只有四個引擎，
 * 不為這類題目新增第五個。使用者要單獨開關數量題時，靠的是 skills: ['數量']
 * 配合排程器既有的技能過濾（規格 §8 的候選條件），不是靠引擎名稱。
 *
 * 題目完全由 lang/ 的規則生成，不讀課次素材——數字與量詞的讀法是規則，
 * 不是課本逐條列出的內容。課次只用來決定 requires_lesson（何時解鎖）。
 */
import { readHour, readMinute, readDayOfMonth, readMonth } from '../lang/numbers.js';
import { readCounter, COUNTERS } from '../lang/counters.js';
import { conceptsForNumber, conceptsForCounter, skillOf } from '../core/concepts.js';

/** 分只取有教學價值的值：音變全落在個位，加上整十與常用的15、45。 */
const MINUTES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 15, 20, 30, 45];

const NUMBER_GROUPS = [
  { kind: 'hour', type: 'time', sub: 'hour', lesson: 4, values: range(1, 12),
    label: (n) => `${n}時`, read: readHour, hint: '時刻的唸法' },
  { kind: 'minute', type: 'time', sub: 'minute', lesson: 4, values: MINUTES,
    label: (n) => `${n}分`, read: readMinute, hint: '分的唸法' },
  { kind: 'day', type: 'date', sub: 'day', lesson: 5, values: range(1, 31),
    label: (n) => `${n}日`, read: readDayOfMonth, hint: '日期的唸法' },
  { kind: 'month', type: 'date', sub: 'month', lesson: 5, values: range(1, 12),
    label: (n) => `${n}月`, read: readMonth, hint: '月份的唸法' },
];

function range(lo, hi) {
  return [...Array(hi - lo + 1)].map((_, i) => lo + i);
}

function makeItem({ id, lesson, covers, promptText, hint, answer, sourceRef }) {
  return {
    id,
    engine: 'recall',
    lesson,
    requires_lesson: lesson,
    covers,
    skills: [...new Set(covers.map(skillOf).filter(Boolean))],
    // 這裡每一題問的都是唸法，答案就是讀音：振假名照常顯示等於把答案印在題幹上
    // （「4時」標著「時→じ」）。見 ui/present.js 的 hideRt。
    prompt: { type: 'text', text: promptText, hint, hideRuby: true },
    answer,
    alternatives: [],
    source_ref: sourceRef,
  };
}

export function* generate() {
  for (const g of NUMBER_GROUPS) {
    const covers = conceptsForNumber(g.type, g.sub);
    for (const n of g.values) {
      yield makeItem({
        id: `qty:${g.kind}:${n}`,
        lesson: g.lesson,
        covers,
        promptText: g.label(n),
        hint: g.hint,
        answer: g.read(n),
        sourceRef: `第${g.lesson}課 ことば`,
      });
    }
  }

  for (const [key, c] of Object.entries(COUNTERS)) {
    const covers = conceptsForCounter(key);
    for (let n = 1; n <= 10; n++) {
      yield makeItem({
        id: `qty:c:${key}:${n}`,
        lesson: c.lesson,
        covers,
        promptText: `${n}${c.label}`,
        hint: `量詞 ${c.label} 的唸法`,
        answer: readCounter(n, key),
        sourceRef: `第${c.lesson}課 ことば`,
      });
    }
  }
}
