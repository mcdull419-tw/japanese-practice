"""CLI 入口：把前面各解析模組組裝成一份課次 JSON。

    python3 -m tools.extract.cli 7                  # 產出 data/lessons/07.json
    python3 -m tools.extract.cli 1-15                # 批次
    python3 -m tools.extract.cli 1-15 --validate     # 產出後執行不變式檢查
    python3 -m tools.extract.cli 7 --out <dir>       # 指定輸出目錄
    python3 -m tools.extract.cli 1-15 --images data/images   # 一併抽出插畫

輸出決定性是硬性要求（spec §5.3：題庫重新生成時同一道題必須得到同一
個 ID，否則 SRS 歷史全部失效）——所有解析模組本身都是純函式（無隨機
性、無依賴檔案系統列舉順序的行為），這裡只需要再加上 `sort_keys=True`
確保「dict 鍵序」這唯一還留給呼叫端決定的自由度也是決定性的。

## 補充單字／会話用語缺假名的處理

課本裡有 59 筆（15 課合計，7 課本身佔 4 筆）詞彙只有漢字（或漢字＋
假名混合的短語）沒有假名欄——不是抽取遺漏，是這些詞在課本版面上原
本就沒有獨立的假名欄位（多半是地名、人名、公司名等專有名詞，或
「ことば」頁尾会話用語小框裡的慣用語），但**讀音其實就印在同一頁的
其他地方**：要嘛是同一課「ことば」數字編號詞彙表裡已經有一模一樣的
漢字寫法搭配假名（例如 L04「銀行」／ぎんこう），要嘛是這個詞本身在
課文正文帶著振假名出現過一次（例如 L05「博多」／はかた）。

`validate_lesson` 對每一筆單字都要求非空 `kana`（不分類別），使用者
需求也明確要求「漢字須提供平假名」，所以這裡在序列化前補上：對每一
筆 `kana` 為空的詞彙，把 `kanji` 依「連續漢字／非漢字」切段，非漢字
段落原樣保留（本來就是假名或符號），每一段連續漢字先查「這一課同一
份詞彙表裡有沒有完全相同的漢字寫法且已有假名」（比對全文振假名掃描
更可靠——同一詞在別處的振假名配對可能因排版雜訊而模糊，例如 L04
「銀行」在全文振假名掃描裡同時比對到「ぎんこう」與「きんこう」兩種
讀音，但同一課詞彙表裡「銀行」這個編號詞條本身的假名沒有歧義），查
不到才退而用 `pair_ruby` 對全文（不限「ことば」區段）掃出的
`base→kana` 對照表，且只在該漢字段落只對到**單一**讀音時才採用——
任何一段查無或有歧義都保留原本的 `None`，不用猜的補資料（跟本專案
一貫「查不到就誠實留空」的原則一致）。已對全 15 課實際跑過這個演算
法：59 筆全數消歧成功（無歧義、無需人工介入），人工核對讀音全部正確
（地名／人名的讀音都是常見的日本地理／人名讀法）。
"""
import argparse
import json
import os
from typing import Dict, List, Optional, Tuple

from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments
from tools.extract.layout import group_lines
from tools.extract.sections import split_sections
from tools.extract.vocab import parse_vocab
from tools.extract.sentences import parse_sentences
from tools.extract.patterns import parse_pattern_tables, parse_drills
from tools.extract.grammar import parse_grammar
from tools.extract.images import extract_images
from tools.extract.validate import validate_lesson
from tools.extract.ruby import pair_ruby


def _is_ideograph(ch: str) -> bool:
    return "一" <= ch <= "鿿" or ch in "々〆〇〻"


def _split_runs(text: str) -> List[Tuple[bool, str]]:
    """把字串切成「連續漢字」與「非漢字」交替的段落，保留原順序。"""
    runs: List[Tuple[bool, str]] = []
    cur = ""
    cur_ideo: Optional[bool] = None
    for ch in text:
        ideo = _is_ideograph(ch)
        if cur_ideo is None or ideo == cur_ideo:
            cur += ch
        else:
            runs.append((cur_ideo, cur))
            cur = ch
        cur_ideo = ideo
    if cur:
        runs.append((cur_ideo, cur))
    return runs


def _fill_missing_vocab_kana(vocab: List[Dict], all_lines, all_frags) -> None:
    """就地補上缺假名的詞彙條目（見模組 docstring）。查不到或有歧義
    的段落一律保留 `None`，不猜測。"""
    local_map = {
        v["kanji"]: v["kana"]
        for v in vocab
        if v.get("kanji") and (v.get("kana") or "").strip()
    }
    global_map: Dict[str, set] = {}
    for line in all_lines:
        for pair in pair_ruby(all_frags, line):
            global_map.setdefault(pair.base, set()).add(pair.kana)

    for entry in vocab:
        if (entry.get("kana") or "").strip():
            continue
        kanji = entry.get("kanji")
        if not kanji:
            continue
        pieces: List[str] = []
        resolved = True
        for is_ideo, run in _split_runs(kanji):
            if not is_ideo:
                pieces.append(run)
                continue
            if run in local_map:
                pieces.append(local_map[run])
            elif run in global_map and len(global_map[run]) == 1:
                pieces.append(next(iter(global_map[run])))
            else:
                resolved = False
                break
        if resolved:
            entry["kana"] = "".join(pieces)


def extract_lesson(lesson: int, image_dir: Optional[str] = None) -> Dict:
    doc = PDFDoc.from_path("%02d.pdf" % lesson)
    frags = extract_fragments(doc)
    lines = group_lines(frags)
    sections = {s.name: s for s in split_sections(lines)}
    data: Dict = {
        "lesson": lesson,
        "vocab": [],
        "sentences": [],
        "patterns": [],
        "drills": [],
        "grammar": [],
        "images": [],
    }
    if "ことば" in sections:
        data["vocab"] = parse_vocab(sections["ことば"])
        _fill_missing_vocab_kana(data["vocab"], lines, frags)
    for name in ("文型", "例文", "会話", "問題"):
        if name in sections:
            data["sentences"].extend(parse_sentences(sections[name], frags, lesson))
    if "練習Ａ" in sections:
        data["patterns"] = parse_pattern_tables(sections["練習Ａ"], lesson)
    if "練習Ｂ" in sections:
        data["drills"] = parse_drills(sections["練習Ｂ"], lesson)
    if "文法" in sections:
        data["grammar"] = parse_grammar(sections["文法"], frags)
    if image_dir:
        images = extract_images(doc, lesson, image_dir)
        for img in images:
            # `images.py` 回傳的 `file` 是實際寫檔用的路徑，字面等於呼叫
            # 端傳入的 `--images` 目錄——同樣條件下重跑位元組相同，但換
            # 一個 `--images` 目錄，這個欄位就變，使得 JSON 內容取決於執
            # 行時的參數，違反「重跑管線必須能重現已提交的資料」（spec
            # §5.3）。這裡改存規範化的相對識別碼：固定為
            # `data/images/<檔名>`（符合 spec §4.5 範例、目錄結構
            # §6.4 的既定慣例），與實際物理寫檔位置解耦——物理檔案仍照
            # `--images` 指定的目錄寫出（供人工核對／算繪比對使用），但
            # JSON 內容本身不再受呼叫參數影響。
            img["file"] = "data/images/%s" % os.path.basename(img["file"])
        data["images"] = images
    return data


def parse_range(spec: str) -> List[int]:
    if "-" in spec:
        lo, hi = spec.split("-", 1)
        return list(range(int(lo), int(hi) + 1))
    return [int(spec)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("lessons", help="課次，例如 7 或 1-15")
    ap.add_argument("--out", default="data/lessons")
    ap.add_argument("--images", default=None)
    ap.add_argument("--validate", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    failures = 0
    for n in parse_range(args.lessons):
        data = extract_lesson(n, args.images)
        path = os.path.join(args.out, "%02d.json" % n)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1, sort_keys=True)
        msg = "%s  單字=%d 句子=%d 代入表=%d 練習Ｂ=%d 文法=%d" % (
            path,
            len(data["vocab"]),
            len(data["sentences"]),
            len(data["patterns"]),
            len(data["drills"]),
            len(data["grammar"]),
        )
        if args.validate:
            problems = validate_lesson(data)
            if problems:
                failures += 1
                msg += "\n  ✗ " + "\n  ✗ ".join(problems)
            else:
                msg += "  ✓"
        print(msg)
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
