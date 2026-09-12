"""句子解析：把 `文型`／`例文`／`会話`／`問題` 四個區段的 `Line` 序列切成
一筆筆 `{"id", "section", "no", "jp", "ruby", "zh", "alt"}` 句子紀錄。

這四個區段是使用者需求裡幾乎所有題型的素材（句型代入、助詞填空、挖空
題、聽力題），但版面差異很大，因此本模組依「是否有行首編號」把每個
`Section` 分派到兩條不同的切分邏輯：

## 兩條切分邏輯

**編號模式**（`文型`／`例文`／`問題`，全 15 課逐一驗證過每一課三者皆有
行首 `N.` 編號）：以行首 `\\s*\\d+\\.` 開新一組，之後直到下一個 `N.`
之前的所有行全部併入同一組、以 `\\n` 連接——這不只涵蓋 `例文` 的問答對
（`……` 開頭的回答行），也涵蓋 `問題` 每題底下的 `1)`／`2)` 子項（子項
用右括號 `)`，不是句點，不會被行首正規式誤判成新的一組——07 課問題 4
「例：友達に（本を貸します）。」＋ 5 個 `N)` 子項因此正確併成同一筆，
`問題` 因此是以「整題」而非「每個子項」為切分單位，這是本模組已知、
刻意的粗顆粒度簡化（見下方「問題區段的已知簡化」）。

**標點模式**（`会話`——全 15 課掃描過，`会話` 本文從未出現行首編號）：
沒有編號可用，改成掃過整個區段的字元流，遇到 `。`／`？`／`！` 就切一
句；換行不代表換句，一句可能橫跨好幾個實際印刷行（見下方「対話換行與
說話者邊界」）。

## 對話換行與說話者邊界（会話 專用）

対話原文常常一句話印到一半就換行（頁寬限制），也常常把「說話者：」
單獨印一行、內容留到下一行——這兩種情形都必須跨行黏接，否則會產生斷
尾或空殼句子。全 15 課掃描找到的實例：

- 08 課「山田一郎　：マリアさんは　もう　日本の　生活に」+ 下一行
  「慣れましたか。」——同一句被印成兩行，中間沒有句讀，必須直接串接
  （不加任何分隔字元，日文本來就不用空格斷詞）。
- 15 課「木　村：」單獨一行（說話者標籤後面完全沒有內容），內容在
  「3人です。」這一行——同樣需要跨行串接才不會產生一個只有「木　村：」
  的空洞句子和一個少了說話者標籤的孤兒句子。

**但不能無條件跨行黏接**：11 課「郵便局員：500円です」這一行本身沒有
句點（逐 fragment 窮舉這一行 y 座標上的所有片段，只有「郵便局員：」
「500円です」兩個 fragment、沒有任何句點字元——確認是原書內容流本身
沒有這個字元，不是抽取遺漏，見 task-8-report.md），下一行卻是全新說
話者「ワン：どのくらい　かかりますか。」。如果無條件
跨行黏接，會把两個不同說話者的話併成一句「郵便局員：500円です　ワン：
どのくらい　かかりますか。」——错误合併，跟 `ruby.py` 模組說明裡「今
　何」被誤合併是同一類問題。

判別依據：一行如果**以「說話者：」開頭**（`_SPEAKER_RE`：起首
20 字內出現全形或半形冒號，且冒號前沒有句讀符號），代表這是新的一輪
發言，即使前一輪還沒湊到句點，也要強制在此切斷（把前一輪目前累積到
的內容直接輸出成一句，即使沒有句點結尾）。這個判別對「継続句」（08、
15 課的例子）不會誤判，因為那些延續行本身都不是以說話者標籤開頭。

分隔線（`------`）與空白行一樣，是強制斷點：不管前面累積到什麼，遇到
就整段輸出（若有非空白內容）並清空累積，避免跨場景黏接。

## 問題區段的已知簡化：以整題為單位，不切到子項

07 課「問題 4」「問題 5」「問題 6」這類每題底下有 `1)`～`5)` 子項的格
式，全部併成一筆（例如 `問題 4` 整題、含例句與 5 個子項，都在同一個
`jp` 字串裡，用 `\\n` 分隔）。這是刻意的簡化，不是遺漏——`問題` 區段
本身的子格式極不一致（同一課內就有聽力填空、圈詞選擇 `①②③`、
是非題 `( ○ )`／`( × )`、代入填空、閱讀測驗＋是非題五種不同形式，
07~15 課逐一核對後發現沒有一種通用的子項切分規則能同時正確處理全
部），任務簡報給的驗收測試也只鎖定 `文型`／`例文` 的精確內容，`問題`
只要求「不遺漏、不損毀」。這裡選擇「保留整題完整內容、不強行切子項」
是符合模組說明「寧可不配對／不精細切分，也不要產生錯誤或遺漏」這個
一貫原則的做法——後續若真的需要逐子項出題，應該是另一個更聚焦的任務
（依題型分別解析），不是本模組的職責。

## 替代形註記 `alt`：只吃「整行恰好是（詞）」的行，不動 問題 答案括號

`文型` 句尾偶爾有獨立一行、恰好是 `（　から　）`／`（　では　）` 這種
純粹「全形括號包住不含空白的單一詞」的行（01/07/13 課實測都有，01
課『（　では　）』、13 課『（　が　）』），代表這裡的助詞／格式有兩種
說法皆可接受，必須移出句子本體、放進 `alt`。

`問題` 區段的括號用法完全不同——`（　本を　貸します　）`／`（　に（から）　）`
這類括號恰好嵌在句子中間，且括號內是完整詞組（含空白），不是「整行只
有括號」，`_ALT_RE` 要求 `re.fullmatch` 整行，兩者在全 15 課的實測資
料裡從未混淆過（見 task-8-report.md 的全語料掃描：`文型`／`例文` 找到
的純括號整行都只出現在 `文型`，`問題`／`例文` 一次也沒有整行恰好是這
個格式）。`問題` 內嵌的巢狀括號（例如 `に（から）`）目前刻意不處理：
它出現在句子中間、不是句尾，套用「整行匹配」規則不會誤觸發，但也不會
被解析成 alt——這是已知、誠實記錄的限制，不是被藏起來的錯誤。

## 振假名 `at` 偏移

`pair_ruby` 回傳的 `at` 是相對於**單一 `Line.text()`** 的字元位置。本
模組把多行拼成一個句子時（`\\n` 連接或跨行直接串接），必須把每一行的
`at` 平移成「相對於整句 `jp` 字串」的位置——`_build_sentence` 統一處理
這個平移，並在最後對組好的 `jp` 做一次整體 `strip()`，同步平移剩餘
ruby 的 `at`，確保 `jp[at:at+len(base)] == base` 這個不變量在任何裁切
之後都成立（詳見 `ruby.py` 模組說明「已知既有事實」）。

## 過濾一：純答案符號的『問題』條目（審查回合修正）

複審全 15 課後發現：`問題` 100 筆裡有 24 筆根本不是句子，是課本的
「聽力多選圈選欄」（`①②③`）或「是非題答案列」（`( ○ )`／`( × )`）
——例如 `L01-問題-2` 的 `jp` 是 `'例：①②③\n1)①②③\n2)①②③'`，
沒有任何一個字是使用者需要輸入／聽懂的日文句子，若進了題庫，使用者
會被要求「回答」`①②③` 這種東西。

判準：**這一筆的 `jp` 完全不含任何假名（平假名或片假名）**。逐課實測
（見 task-8-report.md 附加段落）這 24 筆的假名數全部是 0，全書其餘
369 筆真正的句子（`文型`／`例文`／`会話`／`問題` 裡有實質內容的條目）
假名數最低是 19——0 跟 19 之間有巨大的斷層、沒有任何一筆落在中間，這
不是湊出來剛好卡在門檻上的巧合，是這個資料集裡「純符號答案列」跟「真
正的句子」在結構上天生不同（真正的日文句子一定有假名——至少也會有
「です」「ます」這類語尾），可以放心用「零假名」當判準，不需要更複雜
的啟發式。`_looks_like_real_sentence` 實作、驗證細節見
`test_sentences.py` 的 `TestProblemMarkerEntriesExcluded`／
`TestNoRealSentenceHasZeroKana`（後者是否證面：反過來確認`文型`／
`例文`／`会話`這三個「已知全部是真句子」的區段沒有一筆被這個判準誤
殺）。

這個過濾套用在**所有**區段（不只 `問題`），不是寫死「問題第 2、3 筆一
定砍掉」——03／06／09／12／13／15 課的『問題』沒有 ①②③ 選擇題（只有
是非題答案列），只會篩掉 1 筆而不是 2 筆，因為判準是逐筆看內容，不是
看位置。`文型`／`例文`／`会話` 目前全部通過這個判準（沒有任何一筆被
篩掉），純粹是因為這三個區段本來就沒有這種純符號條目——過濾器本身沒
有排除任何一個區段。

## 過濾二：`会話` 標題不是台詞（審查回合修正）

`会話` 每篇對話開頭都有一行純標題（例如 07 課「ごめんください」、
15 課「ご家族は？」），全 15 課實測：這一行一定是整個區段第一個非空
白行、一定不是「說話者：」開頭（`_SPEAKER_RE` 判不到）、後面一定緊接
一個空白行才是真正的對話開始（`_has_dialogue_title` 用這個結構驗證，
不是單純「丟掉第一筆」）。修正前這行會被當成一句台詞輸出
（`L07-会話-1`），修正後整段捨棄，不計入輸出、也不佔用編號。

**為什麼選擇整段捨棄，不是存成 metadata**：任務介面固定是
`parse_sentences(...) -> List[Dict]`，改成回傳 tuple 或在清單裡塞一
個 schema 不同的特殊項目，都會破壞這個已經被其他測試／未來 Task 9~11
依賴的簡單回傳型別。標題本身如果真的有下游需求，直接從
`section.lines[0].text()` 取得即可（不需要經過句子解析器），不需要為
了一個標題改變整個函式的回傳介面。
"""
import re
from typing import Dict, List, Optional, Tuple

from tools.extract.fragments import Fragment
from tools.extract.layout import Line
from tools.extract.ruby import RubyPair, pair_ruby
from tools.extract.sections import Section

# 行首編號：`    1.`、`   12.` 這類。刻意只認句點，不認右括號 `)`——問題
# 區段的子項用 `1)`／`2)`，不應該被誤判成新的一組（見模組說明）。
_NUM_START_RE = re.compile(r"^\s*\d+\.\s*")

# 純粹「（詞）」整行——alt 替代形註記。`\S+` 不含空白，故 `（本を貸します）`
# 這類多詞括號不會被 `fullmatch` 到（見模組說明）。同時接受全形／半形括號。
_ALT_RE = re.compile(r"^[（(]\s*(\S+)\s*[）)]$")

# 対話說話者標籤：起首 20 字內出現冒號，且冒號前沒有句讀——用來判斷
# 「這是新的一輪發言」，強制切斷上一輪還沒湊到句點的殘句（見模組說明
# 「対話換行與說話者邊界」，11 課「郵便局員：500円です」是實測案例）。
_SPEAKER_RE = re.compile(r"^[^。？！：:]{0,20}[：:]")

# 純分隔線（------）。
_DASH_RE = re.compile(r"^-+$")

_TERMINATORS = "。？！"

# 假名（平假名 U+3040-309F／片假名 U+30A0-30FF）——用來過濾『問題』區段
# 裡純答案符號（①②③、( ○ )/( × )）的條目（見模組說明「過濾一」）。
_KANA_RE = re.compile(r"[぀-ゟ゠-ヿ]")

Piece = Tuple[Line, int, int]   # (line, 起, 迄)：line.text()[起:迄]


def parse_sentences(section: Section, all_frags: List[Fragment], lesson: int) -> List[Dict]:
    lines = section.lines
    numbered = any(_NUM_START_RE.match(l.text()) for l in lines if l.text().strip())

    ruby_cache: Dict[int, List[RubyPair]] = {}

    if numbered:
        raw_groups = _split_numbered(lines)
        sep = "\n"
        group_alts = []
        kept_groups = []
        for pieces in raw_groups:
            kept, alt = _extract_alt(pieces)
            kept_groups.append(kept)
            group_alts.append(alt)
    else:
        kept_groups = _split_by_punctuation(lines)
        if kept_groups and _has_dialogue_title(lines):
            kept_groups = kept_groups[1:]   # 見模組說明「過濾二」
        sep = ""
        group_alts = [[] for _ in kept_groups]

    results: List[Dict] = []
    no = 0
    for pieces, alt in zip(kept_groups, group_alts):
        if not pieces:
            continue
        jp, ruby_list = _build_sentence(pieces, sep, all_frags, ruby_cache)
        jp, ruby_list = _trim(jp, ruby_list)
        if not jp:
            continue
        if not _KANA_RE.search(jp):
            continue   # 見模組說明「過濾一」：純答案符號，不是句子
        no += 1
        results.append({
            "id": "L%02d-%s-%d" % (lesson, section.name, no),
            "section": section.name,
            "no": no,
            "jp": jp,
            "ruby": ruby_list,
            "zh": None,
            "alt": alt,
        })
    return results


def _split_numbered(lines: List[Line]) -> List[List[Piece]]:
    """編號模式分組：行首 `N.` 開新一組，之後的行（含空白行以外的所有
    行）全部併入目前這一組，直到下一個 `N.` 出現。空白行整行捨棄（既不
    開新組也不併入任何一組——`例文` 每組之間的空白間隔行就是這種情
    形）。"""
    groups: List[List[Piece]] = []
    current: Optional[List[Piece]] = None
    for line in lines:
        text = line.text()
        if not text.strip():
            continue
        m = _NUM_START_RE.match(text)
        if m:
            current = []
            groups.append(current)
            lo = len(m.group(0))
            hi = len(text.rstrip())
            if lo < hi:
                current.append((line, lo, hi))
            continue
        if current is None:
            continue   # 第一個編號之前的行，沒有可歸屬的組，捨棄
        lo = len(text) - len(text.lstrip())
        hi = len(text.rstrip())
        if lo < hi:
            current.append((line, lo, hi))
    return groups


def _extract_alt(pieces: List[Piece]) -> Tuple[List[Piece], List[str]]:
    """把一組 piece 裡「整段恰好是（詞）」的獨立條目移出，回傳
    (保留的 piece 清單, 抽出的替代詞清單)。"""
    kept: List[Piece] = []
    alt: List[str] = []
    for line, lo, hi in pieces:
        text = line.text()[lo:hi]
        m = _ALT_RE.fullmatch(text)
        if m:
            alt.append(m.group(1))
        else:
            kept.append((line, lo, hi))
    return kept, alt


def _has_dialogue_title(lines: List[Line]) -> bool:
    """判斷這個區段（会話）開頭是不是一行純標題（見模組說明「過濾
    二」）：區段第一個非空白行本身不是「說話者：」開頭。全 15 課實測
    這個條件下、第一組（`_split_by_punctuation` 產生的第一個 group）
    恰好就是這一整行標題本身——因為標題後面一定緊接空白行，
    `_split_by_punctuation` 的 `flush()` 已經會在那個空白行把標題單
    獨切成一組，不會混進後面的對話內容。"""
    for line in lines:
        text = line.text()
        if text.strip():
            return not _SPEAKER_RE.match(text.lstrip())
    return False


def _split_by_punctuation(lines: List[Line]) -> List[List[Piece]]:
    """標點模式分組（会話 專用，見模組說明「対話換行與說話者邊界」）。"""
    groups: List[List[Piece]] = []
    pending: List[Piece] = []

    def flush():
        nonlocal pending
        if pending and any(line.text()[lo:hi].strip() for line, lo, hi in pending):
            groups.append(pending)
        pending = []

    for line in lines:
        text = line.text()
        stripped = text.strip()
        if not stripped or _DASH_RE.match(stripped):
            flush()
            continue
        if pending and _SPEAKER_RE.match(text.lstrip()):
            flush()
        pos = 0
        n = len(text)
        for i, ch in enumerate(text):
            if ch in _TERMINATORS:
                pending.append((line, pos, i + 1))
                flush()
                pos = i + 1
        if pos < n:
            pending.append((line, pos, n))
    flush()
    return groups


def _build_sentence(
    pieces: List[Piece], sep: str, all_frags: List[Fragment], ruby_cache: Dict[int, List[RubyPair]],
) -> Tuple[str, List[Dict]]:
    """把一組 piece 依 `sep` 接成一個句子字串，並把每個 piece 內的振假名
    `at` 平移成相對於整句字串的位置（見模組說明「振假名 at 偏移」）。"""
    text_parts: List[str] = []
    ruby_out: List[Dict] = []
    cum = 0
    for i, (line, lo, hi) in enumerate(pieces):
        if i > 0:
            cum += len(sep)
        pairs = ruby_cache.get(id(line))
        if pairs is None:
            pairs = pair_ruby(all_frags, line)
            ruby_cache[id(line)] = pairs
        piece_text = line.text()[lo:hi]
        for p in pairs:
            if lo <= p.at and p.at + len(p.base) <= hi:
                ruby_out.append({"base": p.base, "kana": p.kana, "at": cum + (p.at - lo)})
        text_parts.append(piece_text)
        cum += len(piece_text)
    return sep.join(text_parts), ruby_out


def _trim(jp: str, ruby_list: List[Dict]) -> Tuple[str, List[Dict]]:
    """整句組好之後，去除頭尾空白，同步平移 ruby 的 `at`，並丟掉因裁切
    而落到範圍外的 ruby（理論上不應發生——裁掉的只有頭尾空白，任何
    base 都不可能是空白——這裡的過濾純粹是防禦）。"""
    lead = len(jp) - len(jp.lstrip())
    trimmed = jp.strip()
    out = []
    for r in ruby_list:
        at = r["at"] - lead
        if 0 <= at and at + len(r["base"]) <= len(trimmed):
            out.append({"base": r["base"], "kana": r["kana"], "at": at})
    return trimmed, out
