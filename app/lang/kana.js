const HIRA_START = 0x3041, HIRA_END = 0x3096;
const KATA_START = 0x30a1, KATA_END = 0x30f6;
const GAP = KATA_START - HIRA_START;

export function toHiragana(s) {
  let out = '';
  for (const ch of s) {
    const c = ch.codePointAt(0);
    out += (c >= KATA_START && c <= KATA_END) ? String.fromCodePoint(c - GAP) : ch;
  }
  return out;
}

export function toKatakana(s) {
  let out = '';
  for (const ch of s) {
    const c = ch.codePointAt(0);
    out += (c >= HIRA_START && c <= HIRA_END) ? String.fromCodePoint(c + GAP) : ch;
  }
  return out;
}

export function isKana(ch) {
  const c = ch.codePointAt(0);
  return (c >= HIRA_START && c <= HIRA_END) || (c >= KATA_START && c <= KATA_END);
}

export function stripSpaces(s) {
  return s.replace(/[\s　]+/g, '');
}
