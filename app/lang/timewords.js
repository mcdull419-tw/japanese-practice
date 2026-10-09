/**
 * 時間詞明表（補充講義第 II 節，IMAG0806）。不寫成規則：おととい／あさって／ゆうべ
 * 這類詞沒有可推的規律。與 data/supplements/timewords.json 的一致性由
 * tests/app/test_supplements_data.js 把關。
 *
 * label 是講義上的日文書寫、zh 是講義印的中文、kana 是第一讀法（正解）、
 * alts 是同格並列的其他讀法。
 */
export const TIMEWORDS = [
  { key: 'weekday:0', label: '日曜日', zh: '星期日（天）', kana: 'にちようび', alts: [], group: 'weekday' },
  { key: 'weekday:1', label: '月曜日', zh: '星期一', kana: 'げつようび', alts: [], group: 'weekday' },
  { key: 'weekday:2', label: '火曜日', zh: '星期二', kana: 'かようび', alts: [], group: 'weekday' },
  { key: 'weekday:3', label: '水曜日', zh: '星期三', kana: 'すいようび', alts: [], group: 'weekday' },
  { key: 'weekday:4', label: '木曜日', zh: '星期四', kana: 'もくようび', alts: [], group: 'weekday' },
  { key: 'weekday:5', label: '金曜日', zh: '星期五', kana: 'きんようび', alts: [], group: 'weekday' },
  { key: 'weekday:6', label: '土曜日', zh: '星期六', kana: 'どようび', alts: [], group: 'weekday' },
  { key: 'weekday:q', label: '何曜日', zh: '星期幾', kana: 'なんようび', alts: [], group: 'weekday' },
  { key: 'day:-2', label: 'おととい', zh: '前天', kana: 'おととい', alts: [], group: 'day' },
  { key: 'day:-1', label: 'きのう', zh: '昨天', kana: 'きのう', alts: [], group: 'day' },
  { key: 'day:0', label: 'きょう', zh: '今天', kana: 'きょう', alts: [], group: 'day' },
  { key: 'day:1', label: 'あした', zh: '明天', kana: 'あした', alts: [], group: 'day' },
  { key: 'day:2', label: 'あさって', zh: '後天', kana: 'あさって', alts: [], group: 'day' },
  { key: 'day:every', label: 'まいにち', zh: '每天', kana: 'まいにち', alts: [], group: 'day' },
  { key: 'morning:-2', label: 'おとといの朝', zh: '前天早上', kana: 'おとといのあさ', alts: [], group: 'morning' },
  { key: 'morning:-1', label: 'きのうの朝', zh: '昨天早上', kana: 'きのうのあさ', alts: [], group: 'morning' },
  { key: 'morning:0', label: 'けさ', zh: '今天早上', kana: 'けさ', alts: [], group: 'morning' },
  { key: 'morning:1', label: 'あしたの朝', zh: '明天早上', kana: 'あしたのあさ', alts: [], group: 'morning' },
  { key: 'morning:2', label: 'あさっての朝', zh: '後天早上', kana: 'あさってのあさ', alts: [], group: 'morning' },
  { key: 'morning:every', label: 'まいあさ', zh: '每天早上', kana: 'まいあさ', alts: [], group: 'morning' },
  { key: 'evening:-2', label: 'おとといの晩', zh: '前天晚上', kana: 'おとといのばん', alts: [], group: 'evening' },
  { key: 'evening:-1', label: 'きのうの晩', zh: '昨天晚上，昨晚', kana: 'きのうのばん', alts: ['ゆうべ'], group: 'evening' },
  { key: 'evening:0', label: 'こんばん', zh: '今天晚上，今晚', kana: 'こんばん', alts: [], group: 'evening' },
  { key: 'evening:1', label: 'あしたの晩', zh: '明天晚上，明晚', kana: 'あしたのばん', alts: [], group: 'evening' },
  { key: 'evening:2', label: 'あさっての晩', zh: '後天晚上', kana: 'あさってのばん', alts: [], group: 'evening' },
  { key: 'evening:every', label: 'まいばん', zh: '每天晚上，每晚', kana: 'まいばん', alts: [], group: 'evening' },
  { key: 'week:-2', label: '先々週', zh: '上上星期', kana: 'せんせんしゅう', alts: [], group: 'week' },
  { key: 'week:-1', label: '先週', zh: '上星期，上週', kana: 'せんしゅう', alts: [], group: 'week' },
  { key: 'week:0', label: '今週', zh: '本星期，本週', kana: 'こんしゅう', alts: [], group: 'week' },
  { key: 'week:1', label: '来週', zh: '下星期，下週', kana: 'らいしゅう', alts: [], group: 'week' },
  { key: 'week:2', label: 'さ来週', zh: '下下星期', kana: 'さらいしゅう', alts: [], group: 'week' },
  { key: 'week:every', label: '毎週', zh: '每星期，每週', kana: 'まいしゅう', alts: [], group: 'week' },
  { key: 'month:-2', label: '先々月', zh: '上上個月', kana: 'せんせんげつ', alts: [], group: 'month' },
  { key: 'month:-1', label: '先月', zh: '上個月', kana: 'せんげつ', alts: [], group: 'month' },
  { key: 'month:0', label: '今月', zh: '本月', kana: 'こんげつ', alts: [], group: 'month' },
  { key: 'month:1', label: '来月', zh: '下個月', kana: 'らいげつ', alts: [], group: 'month' },
  { key: 'month:2', label: 'さ来月', zh: '下下個月', kana: 'さらいげつ', alts: [], group: 'month' },
  { key: 'month:every', label: '毎月', zh: '每個月', kana: 'まいつき', alts: [], group: 'month' },
  { key: 'year:-2', label: 'おととし', zh: '前年', kana: 'おととし', alts: [], group: 'year' },
  { key: 'year:-1', label: '去年', zh: '去年', kana: 'きょねん', alts: [], group: 'year' },
  { key: 'year:0', label: '今年', zh: '今年', kana: 'ことし', alts: [], group: 'year' },
  { key: 'year:1', label: '来年', zh: '明年', kana: 'らいねん', alts: [], group: 'year' },
  { key: 'year:2', label: 'さ来年', zh: '後年', kana: 'さらいねん', alts: [], group: 'year' },
  { key: 'year:every', label: '毎年', zh: '每年', kana: 'まいとし', alts: ['まいねん'], group: 'year' },
];
