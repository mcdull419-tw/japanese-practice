"""產生 data/drills.json 的草稿（規格 §13 決定 7）。

只做機械拆分，不猜 template——猜錯的 template 比空的更糟：空的一眼看得出
還沒標，猜錯的要跑往返測試才抓得到。

items 為空的 29 則不輸出：那些練習的提示詞在插畫裡，不在文字層（決定 8），
2b 不處理。

用法：python3 tools/draft/drills.py > /tmp/drills-draft.json
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PAREN = re.compile(r"[（(]\s*(.+?)\s*[）)]")


def split_multi(drill):
    """以 ｜ 拆成多則。cue 與 answer 的段數不一致時原樣保留，留給人工判斷。"""
    cues = (drill.get("model_cue") or "").split("｜")
    answers = (drill.get("model_answer") or "").split("｜")
    if len(cues) != len(answers):
        return [(drill["id"], drill.get("model_cue") or "", drill.get("model_answer") or "")]
    if len(answers) == 1:
        return [(drill["id"], cues[0], answers[0])]
    return [(f"{drill['id']}#{i + 1}", c.strip(), a.strip())
            for i, (c, a) in enumerate(zip(cues, answers))]


def main():
    out = {}
    for n in range(1, 16):
        data = json.loads((ROOT / f"data/lessons/{n:02d}.json").read_text(encoding="utf-8"))
        for drill in data.get("drills", []):
            items = [x for x in drill.get("items", []) if x.strip()]
            if not items:
                continue  # 插畫型，規格 §13 決定 8
            for did, cue, answer in split_multi(drill):
                out[did] = {
                    "lesson": n,
                    "model_cue": cue,
                    "model_answer": answer,
                    "items": items,
                    "cue_parts": [p.strip() for p in PAREN.sub("", cue).split("・") if p.strip()],
                    "cue_paren": PAREN.findall(cue),
                    "template": "",
                    "slots": {},
                    "rows": [],
                    "answer_part": None,
                    "source_ref": f"第{n}課 練習Ｂ-{did.split('-B')[1].split('#')[0]}",
                }
    json.dump(out, sys.stdout, ensure_ascii=False, indent=1)
    print(f"輸出 {len(out)} 則", file=sys.stderr)


if __name__ == "__main__":
    main()
