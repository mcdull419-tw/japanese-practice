/**
 * 課本部分詞條在同一欄位裡用分隔符列出多個寫法（例：漢字欄「作ります、造ります」、
 * 「暑い、熱い」），分隔符可能是 、，／,/ 這幾種（規格外觀察，修正 B／C）。
 * 這裡統一拆開，供 recall.js（每個寫法都要能被判對）與 transform.js
 * （取第一個寫法作引用形查 verbsTable、其餘寫法的變化也算 alternatives）共用，
 * 避免兩處各自維護一份分隔符正規式而漂移。
 */
const DELIMS = /[、，,／/]/;

export function splitForms(s) {
  if (typeof s !== 'string' || s.length === 0) return [];
  return s.split(DELIMS).map((x) => x.trim()).filter(Boolean);
}
