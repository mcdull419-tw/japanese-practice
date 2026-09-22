"""從課次 JSON 產生 data/adjectives.json 的草稿。

な形容詞由課本的［な］標記自動判定，可靠。
い形容詞只能列為「候選」——以い結尾的名詞（先生、時計、花）數量不少，
必須人工確認。腳本把兩者分開輸出，草稿只收な形，い形留給人工勾選。

用法：python3 tools/draft/adjectives.py > /tmp/adjectives-draft.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NA_MARK = "［な］"


def strip_mark(s):
    return s.replace(NA_MARK, "").strip() if s else s


def main():
    na, i_candidates = {}, {}
    for n in range(1, 16):
        data = json.loads((ROOT / f"data/lessons/{n:02d}.json").read_text(encoding="utf-8"))
        for v in data.get("vocab", []):
            kana, kanji = v.get("kana") or "", v.get("kanji")
            cite = strip_mark(kanji) or strip_mark(kana)
            if not cite:
                continue
            if NA_MARK in kana or (kanji and NA_MARK in kanji):
                na.setdefault(cite, {"type": "na", "kana": strip_mark(kana), "lesson": n})
            elif kana.endswith("い") and not re.search(r"[…～]", kana):
                i_candidates.setdefault(cite, {"type": "i", "kana": kana, "lesson": n, "zh": v.get("zh")})

    print(json.dumps({"na": na, "i_candidates": i_candidates},
                     ensure_ascii=False, indent=2), file=sys.stdout)


if __name__ == "__main__":
    main()
