"""不變式檢查：對已產出的課次 JSON（Task 13 CLI 組出的字典）做靜態驗
證，把靜默的資料損毀變成大聲的失敗。

**本模組刻意不 import 任何解析模組**（`fragments.py`／`layout.py`／
`vocab.py`……）——它的輸入是最終產出的 JSON 字典，不是中介表示，這樣
才能獨立驗證任何一份課次 JSON（包含未來人工修訂過、或用其他管線重新
產生的檔案），不綁死於本專案目前的抽取實作。呼叫端（Task 13 CLI）才
負責把解析模組的回傳值組成這裡吃的字典形狀。

`validate_lesson` 的設計原則是「回報所有能查到的問題，不因為第一個問
題就中斷」——單一次呼叫應該讓使用者一次看到整份課次資料裡所有已知類
型的損毀，不必逐一修一個、重跑一次才看到下一個。因此本模組**不拋
例外**（除了呼叫端傳入型別完全不對，例如 `data` 不是 dict 這種明顯誤
用），任何欄位缺漏或型別不符，一律轉成一則問題描述，讓 `List[str]`
維持「非空即失敗」這個單純的介面。

各檢查的鍵一律用 `data.get(key, [])` 取得，不假設存在——上游不同階段
的產出可能缺某些鍵（例如尚未跑到文法解析階段的中介產物）。

## 兩個非顯而易見的設計決策，特別記錄

**1. 誤解碼指紋涵蓋兩種變體**：專案六次「測試全綠但資料是壞的」事故
之一是第 13 課整課日文被誤讀成 cp1252（Shift-JIS 的兩位元組全形字前
導位元組 0x82／0x83，被 cp1252 這種單位元組編碼表誤讀成 `‚`
（U+201A）／`ƒ`（U+0192），後面接的第二個位元組落在 cp1252 的
0xA0-0xFF 區段時會直接映成同碼位的 Latin-1 補充字元）。`_CP1252_
MOJIBAKE_RE` 抓的正是這個位元組層級的因果關係，不是硬記某幾個具體字
串：只要「前導誤讀字元」後面緊跟著一個 Latin-1 補充字元，就是這種誤
解碼的指紋，不論實際課本內容是哪個假名／漢字。已用範例字串
`‚±‚Æ‚Î`（Shift-JIS「こと」「ば」誤讀後的結果）驗證比對得上。另一種
「Shift-JIS 誤讀為 GB18030」用的是任務簡報既有的 `MISDECODE_
FINGERPRINT` 字元集合（複審全案時全 15 課逐字掃描標出的罕見漢字
區間），兩者是不同誤讀路徑、不同字元範圍，缺一都會漏掉一種真實發生
過的損毀。

**2. 代入表「代入後是否為完整句子」的判準是結構性的，不是詞彙表比對**
：不能只看「句尾有沒有。」（`L15-A3` 的模板本身就沒有句號，但代入結
果是完整句子），也不能只看「有沒有空槽位」（`L13-A4`／`L15-A3` 的空
槽位是課本原本的排版——名詞可以直接接固定尾綴，例如「買い物」直接接
「に行きます。」；`L01-A4`／`L04-A6` 的空槽位則是真的缺述語）。真正
能區分兩者的訊號是模板的**結構**：把模板最後一個佔位符之後的固定字
面文字（`trailing_literal`）取出來——如果它非空（例如 L13-A4 的
「に行きます。」、L15-A3 的「います」），代表不論任何槽位是否留空，
這個模板都保證會印出一個述語，代入結果一定完整；如果它是空的（L01-A4
的模板整句就是「{S}{T}」，L04-A6 是「わたしは{S}{T}」，佔位符之後什
麼都沒有），完整與否就完全取決於最後一個佔位符本身有沒有值——這正是
`_row_forms_complete_sentence` 的判準，用全 15 課僅有的 4 處真實空槽
位（2 好 2 壞）逐一驗算過（見 `tests/extract/test_validate.py`
`TestPatternSubstitutionCompleteness`），不是憑空設計的規則。

## 已知但本模組無法檢查的風險（誠實記錄，不是遺漏）

`_TJ_ITEM`（`tools/extract/fragments.py`，Task 3）目前不匹配 PDF `TJ`
陣列裡的 `(...)` 字面字串，只影響頁尾頁碼，但擴至 16~50 課時若正文使
用字面字串會靜默遺失整段內容。這是**抽取階段**的風險，`validate_
lesson` 吃的是抽取完成後的 JSON——如果內容在抽取當下就沒被寫進
JSON，這裡的任何不變式檢查都無從得知「本來還應該有更多內容」（不變
式檢查只能驗證「已存在的資料是否自洽」，無法驗證「資料是否完整」）。
真正的防線是 `tools/render.swift` 視覺比對（spec §13 Phase 0 驗收明
文要求，理由同樣寫在那裡：遺失整行子項目這類缺陷會通過所有不變式檢
查）。
"""
import re
import unicodedata
from typing import Dict, List


# Shift-JIS 誤讀為 GB18030 會產生的罕見漢字區間（模組層級常數，介面
# 由任務簡報指定）。
MISDECODE_FINGERPRINT = set(
    "偁偄偆偊偍偐偑偒偓偔偕偖偗偘偙偠偡偣偤偦偨偩偪偭偮偯偰偱偲偵偼傑傒傓"
)

# Shift-JIS 誤讀為 cp1252 的指紋：兩位元組全形字的前導位元組
# 0x82（ひらがな）／0x83（カタカナ）被 cp1252 誤讀成 U+201A（‚）／
# U+0192（ƒ），後面接的第二個位元組（0xA0-0xFF）在 cp1252 裡直接映成
# 同碼位的 Latin-1 補充字元。見模組說明。
_CP1252_MOJIBAKE_RE = re.compile("[‚ƒ][ -ÿ]")

# 句子／例句允許的結尾符號：句號／問號／驚嘆號，或代換練習用的箭頭。
_TERMINATORS = "。？！"

# 課本圈號標記（①～⑳，U+2460-U+2473）——那是課本的編號，不是句子內
# 容，殘留代表抽取時忘了剝除。
_CIRCLED_MARK_RE = re.compile("[①-⑳]")

# `sentences.py` 的區段名稱之一：`問題`（選擇題／代換題參考素材）。控
# 制端已裁決該區段維持「整題」粗顆粒度（不拆子項），見模組說明「`問
# 題` 區段的兩個誤判」——句尾終止符檢查與圈號殘留檢查都不適用於這個
# 區段，其餘區段（`文型`／`例文`／`会話`）不受影響。
_PROBLEM_SECTION = "問題"

# 文法內文不得出現的空引號。
_EMPTY_QUOTE_RE = re.compile("「」")

# 代入表模板裡的佔位符，例如 "{S}"、"{T}"。
_PLACEHOLDER_RE = re.compile(r"\{(\w+)\}")

_PUNCT_CATEGORIES = ("Pc", "Pd", "Pe", "Pf", "Pi", "Po", "Ps")


def _is_pure_punctuation(text: str) -> bool:
    """整段文字扣掉空白後，是否每個字元都屬於 Unicode 標點類別。空
    字串（或只有空白）不算「純標點」——那是另一種缺漏，由呼叫端的空值
    檢查負責，避免同一個缺陷被兩條規則重複計數又互相掩蓋語意。"""
    stripped = text.strip()
    if not stripped:
        return False
    for ch in stripped:
        if ch.isspace():
            continue
        if unicodedata.category(ch) not in _PUNCT_CATEGORIES:
            return False
    return True


def _walk_strings(value):
    """遞迴走訪任意巢狀 dict／list 結構，依序 yield 所有字串葉節點。
    用於誤解碼指紋這種「全檔任何欄位都可能中招」的檢查——不能只挑幾
    個已知欄位看，複審踩過的教訓是誤解碼可能出現在任何被誤判編碼的
    整段文字裡，欄位名稱不會告訴你哪裡壞了。"""
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for v in value.values():
            for s in _walk_strings(v):
                yield s
    elif isinstance(value, list):
        for v in value:
            for s in _walk_strings(v):
                yield s


def _row_forms_complete_sentence(template: str, vals: Dict[str, str], sentence: str) -> bool:
    """判斷代入表某一列代入後是否為完整句子。見模組說明「代入表『代
    入後是否為完整句子』的判準是結構性的，不是詞彙表比對」。"""
    text = sentence.rstrip()
    if text and text[-1] in _TERMINATORS:
        return True
    matches = list(_PLACEHOLDER_RE.finditer(template))
    if not matches:
        # 模板本身沒有佔位符（理論上不會發生於代入表，但防禦性地視為
        # 完整——沒有任何槽位可以「留空」）。
        return True
    last = matches[-1]
    last_name = last.group(1)
    trailing_literal = template[last.end():]
    if trailing_literal.strip():
        # 最後一個佔位符之後還有固定文字，不論任何槽位是否留空，這段
        # 固定文字都保證會印出來——代入結果的句尾結構是確定的。
        return True
    if (vals.get(last_name) or "") != "":
        # 沒有固定尾綴，但最後一個佔位符本身有值。
        return True
    return False


def _check_vocab(vocab: List[Dict], problems: List[str]) -> None:
    numbered_nos = [v.get("no") for v in vocab if v.get("no") is not None]
    if numbered_nos and sorted(numbered_nos) != list(range(1, len(numbered_nos) + 1)):
        problems.append("單字編號不連續或有缺漏（1..N）：%r" % (numbered_nos,))

    for v in vocab:
        label = v.get("kanji") or v.get("kana") or "no=%r" % v.get("no")
        if not (v.get("kana") or "").strip():
            problems.append("單字「%s」缺少假名" % label)
        if not (v.get("zh") or "").strip():
            problems.append("單字「%s」缺少中文" % label)
        kanji = v.get("kanji")
        if kanji and _is_pure_punctuation(kanji):
            problems.append("單字「%s」漢字欄為純標點：%r" % (label, kanji))
        usage = v.get("usage")
        if usage is not None:
            usage_kana = (usage.get("kana") or "").strip()
            usage_kanji = (usage.get("kanji") or "").strip()
            if not usage_kana and not usage_kanji:
                # 兩側都空才是缺陷（真的什麼都沒抽到）。只有一側非空是
                # 合法狀態：課本印刷的搭配用法本來就常常只給假名（例如
                # 第 6 課「吸います」的「［たばこを～］」只印假名，
                # `tabako`〔煙草〕這個漢字寫法課本原文根本沒印——已用
                # `tools/render.swift` 算繪第 1 頁核對，同頁鄰近詞條
                # 「撮ります」「会います」的 usage 才兩側都有），或詞
                # 彙本身就沒有漢字寫法（第 12 課「いい」`kanji` 欄本身
                # 就是 `None`，其 usage 沒有漢字是同一個原因的自然結
                # 果，不該用更嚴格的標準要求 usage 比詞彙本身還完整）。
                problems.append(
                    "單字「%s」的搭配用法（usage）假名與漢字皆缺漏：%r" % (label, usage)
                )


def _check_sentences(sentences: List[Dict], problems: List[str]) -> None:
    for s in sentences:
        sid = s.get("id", "?")
        jp = s.get("jp") or ""
        section = s.get("section")
        if section != _PROBLEM_SECTION:
            # `問題` 區段的句尾終止符檢查與圈號殘留檢查都不適用（見模組
            # 說明「`問題` 區段的兩個誤判」）：`sentences.py` 對 `問題`
            # 刻意採「整題」而非「每個子項」的粗顆粒度（控制端已裁決維
            # 持，見模組說明），整題內容合法地以「（②）」這類選擇題答
            # 案代號結尾，也合法地含有課本印的 `①②③` 選擇題選項本身
            # ——那些不是抽取時忘了剝除的標記殘留，是題目原文的一部
            # 分。全 15 課實測：含圈號的句子共 6 句，全部落在 `問題`
            # 區段，其餘區段 0 句。
            text = jp.rstrip()
            if text and text[-1] not in _TERMINATORS and not text.endswith("→"):
                problems.append("句子 %s 結尾不是「。？！」或「→」：%r" % (sid, jp))
            if _CIRCLED_MARK_RE.search(jp):
                problems.append("句子 %s 的 jp 殘留課本圈號標記：%r" % (sid, jp))
        for ruby in s.get("ruby") or []:
            base = ruby.get("base", "")
            at = ruby.get("at")
            ok = isinstance(at, int) and at >= 0 and jp[at:at + len(base)] == base
            if not ok:
                problems.append(
                    "句子 %s 振假名 base=%r 未出現在 jp 宣告的位置 at=%r：%r"
                    % (sid, base, at, jp)
                )


def _check_patterns(patterns: List[Dict], problems: List[str]) -> None:
    for t in patterns:
        tid = t.get("id", "?")
        slots = t.get("slots")
        rows = t.get("rows")
        template = t.get("template")
        if slots is None or rows is None:
            # 變化表（table_type == "conjugation"）沒有槽位結構，不適
            # 用本檢查（見 patterns.py `parse_pattern_tables` 介面）。
            continue
        names = sorted(slots.keys())
        for i, row in enumerate(rows):
            if len(row) != len(names):
                problems.append(
                    "代入表 %s 第 %d 列長度 %d 與槽位數 %d 不符"
                    % (tid, i, len(row), len(names))
                )
                continue
            vals = {}
            row_ok = True
            for name, idx in zip(names, row):
                candidates = slots[name]
                if not isinstance(idx, int) or idx < 0 or idx >= len(candidates):
                    problems.append(
                        "代入表 %s 第 %d 列索引 %r 超出槽位 %s 的範圍（0..%d）"
                        % (tid, i, idx, name, len(candidates) - 1)
                    )
                    row_ok = False
                    continue
                vals[name] = candidates[idx]
            if not row_ok or template is None:
                continue
            sentence = template.format(**vals)
            if not _row_forms_complete_sentence(template, vals, sentence):
                problems.append(
                    "代入表 %s 第 %d 列代入後缺少述語，句子不完整：%r"
                    % (tid, i, sentence)
                )


def _check_grammar(grammar: List[Dict], problems: List[str]) -> None:
    for g in grammar:
        title = g.get("title", "?")
        examples = g.get("examples") or []
        has_japanese_example = any((ex.get("jp") or "").strip() for ex in examples)
        for ex in examples:
            jp = ex.get("jp") or ""
            if _CIRCLED_MARK_RE.search(jp):
                problems.append("文法「%s」例句殘留課本圈號標記：%r" % (title, jp))
        body_zh = g.get("body_zh") or ""
        if _EMPTY_QUOTE_RE.search(body_zh):
            problems.append("文法「%s」內文出現空引號「」：%r" % (title, body_zh))
        if not has_japanese_example and _CIRCLED_MARK_RE.search(body_zh):
            # 「缺少日文例句」本身不是缺陷——全 15 課 91 則文法點裡有 9
            # 則課本原文就沒有圈號例句（Task 10 已對照課本核對，內容都
            # 在 `body_zh` 裡）。但若 `body_zh` 殘留圈號標記字元，代表
            # 這一則原本有例句標記，卻沒有任何一句被解析成功抽出
            # ——那才是真正需要攔的情形（標記存在但抽取失敗），比單純
            # 「examples 是空的」精確：全 15 課實測那 9 則的 `body_zh`
            # 均不含圈號殘留，這個檢查對它們不會誤報。
            problems.append(
                "文法「%s」有圈號例句標記卻未抽出任何例句：%r" % (title, body_zh)
            )


def _check_misdecoding(data: Dict, problems: List[str]) -> None:
    seen_gb18030 = set()
    seen_cp1252 = set()
    for text in _walk_strings(data):
        hit_chars = set(text) & MISDECODE_FINGERPRINT
        if hit_chars and text not in seen_gb18030:
            seen_gb18030.add(text)
            problems.append(
                "誤解碼指紋字元（Shift-JIS 誤讀為 GB18030）出現於：%r（字元：%r）"
                % (text, sorted(hit_chars))
            )
        if _CP1252_MOJIBAKE_RE.search(text) and text not in seen_cp1252:
            seen_cp1252.add(text)
            problems.append(
                "誤解碼指紋字元（Shift-JIS 誤讀為 cp1252）出現於：%r" % (text,)
            )


def validate_lesson(data: Dict) -> List[str]:
    """驗證一份課次 JSON 字典是否符合 spec §13 Phase 0 全部驗收不變
    式。回傳問題描述清單，空清單代表通過。不修改 `data`、不拋例外
    （型別完全不符的欄位一律轉成問題描述），不 import 任何解析模組。
    """
    problems: List[str] = []

    _check_vocab(data.get("vocab") or [], problems)
    _check_sentences(data.get("sentences") or [], problems)
    _check_patterns(data.get("patterns") or [], problems)
    _check_grammar(data.get("grammar") or [], problems)
    _check_misdecoding(data, problems)

    return problems
