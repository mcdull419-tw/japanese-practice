"""從課本自身的 ruby 標註產生振假名詞典的 auto 區（規格 §13 決定 9）。

多讀音字（同一個 base 在不同句子標了不同假名）一律排除，列入 ambiguous
區備查——寧可不加注，也不要在題目上印出錯的讀音。

用法：python3 tools/draft/ruby_lexicon.py
直接改寫 data/ruby-lexicon.json 的 auto 與 ambiguous 區，manual 區原樣保留。
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "data/ruby-lexicon.json"


KANJI = re.compile(r"[\u4e00-\u9fff]")


def collect():
    readings = defaultdict(Counter)
    for n in range(1, 16):
        data = json.loads((ROOT / f"data/lessons/{n:02d}.json").read_text(encoding="utf-8"))
        for s in data.get("sentences", []):
            for r in s.get("ruby", []):
                base, kana = r.get("base"), r.get("kana")
                # 課本也替數字標讀音（「3つ」標 みっ）。這些不進詞典，兩個理由：
                # 一是 annotateWithLexicon 只掃漢字段，數字永遠匹配不到，收了也是死條目；
                # 二是數字讀音高度依賴後接的量詞（3つ みっつ／3人 さんにん／3階 さんがい），
                # 用詞典硬套必錯。數量的讀音由 lang/numbers.js 與 counters.js 負責。
                if base and kana and KANJI.search(base):
                    readings[base][kana] += 1
    auto, ambiguous = {}, {}
    for base, counter in sorted(readings.items()):
        if len(counter) == 1:
            auto[base] = next(iter(counter))
        else:
            ambiguous[base] = sorted(counter)
    return auto, ambiguous


def main():
    auto, ambiguous = collect()
    existing = json.loads(OUT.read_text(encoding="utf-8")) if OUT.exists() else {}
    out = {
        "auto": auto,
        "manual": existing.get("manual", {}),
        "ambiguous": ambiguous,
    }
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1, sort_keys=False) + "\n",
                   encoding="utf-8")
    print(f"auto={len(auto)} manual={len(out['manual'])} ambiguous={len(ambiguous)}")


if __name__ == "__main__":
    main()
