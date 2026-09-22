"""產生 data/particles.json 的草稿。

只處理 文型 與 例文 兩個段落：会話 多為對話殘句，問題 的條目是含題號與
括號答案的多行混合體，都不是乾淨單句。

規則只猜得出「助詞在哪裡」，猜不準「是哪種用法」——後者由人工校對填入。
腳本把能高度確定的情形先填好（例如 を 只有一種用法），其餘留空字串，
讓校對者一眼看出哪些還沒決定。

用法：python3 tools/draft/particles.py > /tmp/particles-draft.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SECTIONS = {"文型", "例文"}
PARTICLES = ["から", "まで", "は", "が", "を", "に", "で", "と", "へ", "も", "や"]

# 只有單一用法的助詞可以直接定案，其餘一律留空給人工判斷。
UNAMBIGUOUS = {"を": "p:wo:object", "は": "p:wa:topic", "も": "p:mo:also"}


def main():
    out = {}
    for n in range(1, 16):
        data = json.loads((ROOT / f"data/lessons/{n:02d}.json").read_text(encoding="utf-8"))
        for s in data.get("sentences", []):
            if s.get("section") not in SECTIONS:
                continue
            jp = s.get("jp") or ""
            if not re.search(r"[　 ]", jp):
                continue  # 無課本分詞空格者無法可靠切分，跳過
            marks = []
            pos = 0
            for chunk in re.split(r"([　 ]+)", jp):
                if not chunk.strip():
                    pos += len(chunk)
                    continue
                body = re.sub(r"[。？！]+$", "", chunk)
                for p in PARTICLES:
                    if body.endswith(p) and len(body) > len(p):
                        marks.append({"at": pos + len(body) - len(p), "p": p,
                                      "c": UNAMBIGUOUS.get(p, "")})
                        break
                pos += len(chunk)
            if marks:
                out[s["id"]] = marks
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
