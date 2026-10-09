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
import {
  readHour, readMinute, readDayOfMonth, readMonth, readNumber, readBig, readDecimal, readFraction,
  readZero, NUMBER_ALTS, CLOCK_ALTS, CLOCK_Q,
} from '../lang/numbers.js';
import { readCounter, readCounterAlts, readCounterQ, COUNTERS } from '../lang/counters.js';
import { TIMEWORDS } from '../lang/timewords.js';
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

function makeItem({ id, lesson, covers, promptText, hint, answer, alternatives = [], sourceRef }) {
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
    alternatives,
    source_ref: sourceRef,
  };
}

const SUPP = '補充講義';

/** 音變集中、值得單獨問的數字：4／7／9 的並列讀法，百、千的音變。 */
const IRREGULAR_NUMBERS = [4, 7, 9, 14, 17, 19, 70, 100, 300, 600, 800, 1000, 3000, 8000];
const BIG_NUMBERS = [10000, 100000, 1000000, 10000000, 100000000];
const DECIMALS = ['17.5', '0.83'];
const FRACTIONS = [[1, 2], [3, 4]];

/** 時間詞的解鎖課次：第4課教曜日與今天／每天，第5課教先月／今月／來月。 */
const TIMEWORD_LESSON = { weekday: 4, day: 4, morning: 4, evening: 4, week: 5, month: 5, year: 5 };

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
        alternatives: CLOCK_ALTS[`${g.kind}:${n}`] || [],
        sourceRef: `第${g.lesson}課 ことば`,
      });
    }
    // 疑問詞（何時、何分、何月、何日）：連濁は規則では導けないので明表（CLOCK_Q）。
    yield makeItem({
      id: `qty:${g.kind}:q`,
      lesson: g.lesson,
      covers,
      promptText: g.label('何'),
      hint: g.hint,
      answer: CLOCK_Q[g.kind],
      sourceRef: SUPP,
    });
  }

  yield makeItem({
    id: 'qty:minute:half',
    lesson: 4,
    covers: conceptsForNumber('time', 'minute'),
    promptText: '半',
    hint: '30分の言い方',
    answer: CLOCK_Q.half,
    sourceRef: SUPP,
  });

  yield makeItem({
    id: 'qty:zero',
    lesson: 1,
    covers: conceptsForNumber('num', 'zero'),
    promptText: '0',
    hint: '數字的唸法',
    answer: readZero()[0],
    alternatives: readZero().slice(1),
    sourceRef: SUPP,
  });

  for (const n of IRREGULAR_NUMBERS) {
    yield makeItem({
      id: `qty:num:${n}`,
      lesson: 3,
      covers: conceptsForNumber('num', n >= 100 ? 'place' : 'variant'),
      promptText: String(n),
      hint: '數字的唸法',
      answer: readNumber(n),
      alternatives: NUMBER_ALTS[n] || [],
      sourceRef: SUPP,
    });
  }

  for (const n of BIG_NUMBERS) {
    yield makeItem({
      id: `qty:big:${n}`,
      lesson: 3,
      covers: conceptsForNumber('num', 'big'),
      promptText: n.toLocaleString('en-US'),
      hint: '萬、億的唸法',
      answer: readBig(n),
      sourceRef: SUPP,
    });
  }

  for (const d of DECIMALS) {
    yield makeItem({
      id: `qty:dec:${d}`,
      lesson: 15,
      covers: conceptsForNumber('num', 'decimal'),
      promptText: d,
      hint: '小數的唸法',
      answer: readDecimal(d),
      sourceRef: SUPP,
    });
  }

  for (const [a, b] of FRACTIONS) {
    yield makeItem({
      id: `qty:frac:${a}/${b}`,
      lesson: 15,
      covers: conceptsForNumber('num', 'fraction'),
      promptText: `${a}/${b}`,
      hint: '分數的唸法',
      answer: readFraction(a, b),
      sourceRef: SUPP,
    });
  }

  for (const t of TIMEWORDS) {
    yield makeItem({
      id: `qty:tw:${t.key}`,
      lesson: TIMEWORD_LESSON[t.group],
      covers: conceptsForNumber('time', 'word'),
      promptText: t.zh,
      hint: '時間詞的唸法',
      answer: t.kana,
      // 講義上的日文寫法（先週、毎年）也算對；與假名相同的不重複放。
      alternatives: [...new Set([...t.alts, t.label])].filter((x) => x !== t.kana),
      sourceRef: SUPP,
    });
  }

  for (const [key, c] of Object.entries(COUNTERS)) {
    const covers = conceptsForCounter(key);
    for (let n = 1; n <= 10; n++) {
      yield makeItem({
        id: `qty:c:${key}:${n}`,
        lesson: c.lesson,
        covers,
        promptText: (c.prompts && c.prompts[n]) || `${n}${c.label}${c.promptNote || ''}`,
        hint: `量詞 ${c.label} 的唸法`,
        answer: readCounter(n, key),
        alternatives: readCounterAlts(n, key),
        sourceRef: `第${c.lesson}課 ことば`,
      });
    }
    // 「つ」的疑問詞是いくつ，題幹與答案同形，不出題。
    if (c.q && key !== 'tsu') {
      yield makeItem({
        id: `qty:c:${key}:q`,
        lesson: c.lesson,
        covers,
        promptText: `何${c.label}${c.promptNote || ''}`,
        hint: `量詞 ${c.label} 的疑問詞`,
        answer: readCounterQ(key),
        sourceRef: SUPP,
      });
    }
  }
}
