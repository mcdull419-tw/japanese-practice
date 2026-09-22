"""從課次 JSON 的 grammar[] 產生 data/concepts.json 的草稿。

grammar[].title 幾乎就是概念名稱，grammar[].no 直接給出 source_ref。
概念 id 無法自動產生（要人為決定 p:ni:recipient 這種命名），因此草稿
輸出的是「待命名清單」：每則文法一列，附標題、課次、例句，供人工填 id。

用法：python3 tools/draft/concepts.py > /tmp/concepts-draft.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main():
    out = []
    for n in range(1, 16):
        data = json.loads((ROOT / f"data/lessons/{n:02d}.json").read_text(encoding="utf-8"))
        patterns = [p["id"] for p in data.get("patterns", [])]
        for g in data.get("grammar", []):
            out.append({
                "id": "",  # 待人工填寫，例如 p:ni:recipient
                "label": g.get("title", ""),
                "requires_lesson": n,
                "source_ref": f"第{n}課 文法{g.get('no', '')}",
                "body_zh": g.get("body_zh", "")[:120],
                "examples": [e.get("jp", "") for e in g.get("examples", [])[:2]],
                "lesson_patterns": patterns,  # 供人工挑選哪幾張表屬於這個概念
            })
    print(json.dumps(out, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
