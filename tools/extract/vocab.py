"""單字表（ことば）解析：把 `Section`（Task 6）的 `Line` 序列切成一筆筆
單字紀錄 `{"no", "kana", "kanji", "zh", "usage", "group"}`。

這是整條抽取管線最核心的資料——單字練習、漢字→假名讀音練習、中日對照
全部建立在這裡的輸出上，實測見 `task-7-report.md`。

## 動詞分類記號（group）：課本從第 14 課開始標，動詞變化練習需要它

課本從第 14 課開始，在假名欄後面用羅馬數字標註動詞分類（Ⅰ／Ⅱ／Ⅲ
類，例如「つけます Ⅱ」「けします Ⅰ消します」）。這是變化引擎推導て
形、ない形等變化規則的必要資訊（本題庫使用者需求「動詞變化練習」的
前提），課本既然已經標好，`_extract_group` 把它從假名欄抽成獨立的
`group` 欄位（值為 `"I"`／`"II"`／`"III"`／`None`），不留在 `kana`
裡當雜訊。第 1~13 課沒有這個標記，`group` 一律是 `None`，這是正常的
（見 `task-7-report.md` 的全課統計）。

## 版面：每筆單字一行，欄位依 x 座標由左至右為「編號、假名、漢字（可能
缺席）、中文」，行號標籤格式通常是 `N.`（可能有前導全形/半形空白）。

**欄位 x 座標每一課不同**（07 課 53.4/219.0/384.6、13 課
51.6/210.0/368.4，見任務簡報），不可寫死；本模組先對整個 Section 掃描
一次，用「固定版面欄位的 x 在同一課會被精確重複使用很多次」這個實測
規律（`_learn_columns`）學出這一課的假名欄 x、漢字欄 x、中文欄名目起
點，再對每一行套用**狀態機**（`_split_data_cells`）逐一 Cell 判定歸
屬，而不是單純比對相鄰 Cell 間距。

### 為什麼不能只看相鄰 Cell 的間距（曾經試過、會誤判）

第一版實作用「相鄰 Cell 間距 >= 100pt 視為換欄」，在 07 課（單字幾乎
都很短）看起來正確，但對全 15 課逐課核對後發現會在兩個方向上誤判：

1. **假名/漢字欄本身因標點被 `cells()` 額外切開時，欄內縫隙可能跟真
   正換欄的間距量級重疊**——02 課第 45 筆「［どうも］ ありがとう
   ［ございます］。 （非常）謝謝你。」，假名／中文之間真正的換欄間
   距只有 87pt（比欄內縫隙的上限 92.4pt 還小！），相鄰間距門檻不管
   設多少都無法同時涵蓋兩者。09 課第 3～6、40 筆「好き［な］」「早
   く、速く」這類漢字欄本身有兩個 Cell（`219.0` 與 `258.6`，中間縫
   隙 39.6pt），若只看間距，中文欄的起點（`384.6`）跟漢字欄第二個
   Cell 的間距（126pt）又會被誤判成另一次換欄，導致「な］」「速く」
   被錯誤歸類到中文欄。
2. 04 課「  104電話查號台」——`■会話` 小框裡真正的詞彙「104」（電話
   查號台的號碼）被行號正則誤判成第 104 筆單字（見下方「行號防呆」）。

**改用「絕對位置 + 狀態機」解決第 1 類問題**：先用全 Section 統計學出
這一課的漢字欄 x（`kanji_x`，容差 `_KANJI_TOL`）與中文欄地板
（`zh_floor` = 學出的中文欄名目起點 − `_ZH_MARGIN`，見下方「中文欄
名目起點與抖動」），再對每一行的資料 Cell **依序**維護「目前在哪一
欄」的狀態：從假名欄出發，只有 Cell x 精確貼近 `kanji_x` 才會切換到
漢字欄，只有 Cell x 落在 `zh_floor` 之後才會切換到中文欄；**已經進入
某一欄之後，同一欄內部後續的 Cell（不論間距多大）一律留在同一欄，直
到真的越過下一個欄位邊界**。這樣 09 課「な］」「速く」因為還沒越過
`zh_floor`，正確留在漢字欄；02 課第 45 筆全程沒有 Cell 貼近
`kanji_x`，直到 `370.8`（越過 `zh_floor`）才換欄，正確只切出假名／中
文兩欄。

### 中文欄名目起點與抖動

中文欄名目起點（如 07 課 384.6）在**中文釋義前面剛好接一個全形空白**
時會左移一個全形字寬（07 課第 9、33、34 筆等落在 370.8）。`_learn_
columns` 用「出現次數 >= `_MIN_COLUMN_HITS`」篩出兩個夠遠的高頻叢
集，取較小的當 `zh_ref`（這已經是抖動後的較低值，比名目起點更安全），
再扣掉 `_ZH_MARGIN` 當最終地板，双重保險。

## 行號防呆：只承認「跟預期序號完全銜接」的行號

04 課 `ことば` 頁尾附的「本課會話用語」小框裡有一筆詞彙本身就是「104」
（電話查號台號碼，`■会話` 開頭、不屬於主要單字列表），若行號正則只看
「開頭是數字」，會被誤判成第 104 筆單字（主列表其實只有 50 筆）。單
字表的編號規則是**嚴格從 1 開始、每筆遞增 1**，因此 `parse_vocab`
維護一個 `expected` 計數器，只有行首數字**精確等於**目前預期的下一個
編號才承認是新單字列的開頭；不匹配的一律當成普通內容行處理（可能被
`_is_usage_subline` 收編，否則被忽略）。

**行號句點是可選的**：算繪 10.pdf 第 1 頁核對過，第 15 筆單字原書就印
成「15　スイッチ」（沒有句點，前後 14、16 兩筆都有句點）——這是課本
本身排版不一致，不是抽取管線的缺陷。若句點寫死必要，這一筆會被靜默
漏收，且不會被行號防呆機制擋下（因為它的數字本身仍然正確銜接
14→15→16）。

## 緊排單字（如 07 課第 10 筆「て」/「手」）

同一 Cell 內假名漢字靠字距撐開，沒有觸發任何欄位切換（狀態機全程停在
假名欄）。此時在假名欄文字裡找**第一個 CJK 表意文字**
（`一`-`鿿` / `㐀`-`䶿`）當切點，切點前是假名、切點（含）之後是漢字。
片假名（セロテープ這類）不含表意文字，不會被誤切。

## usage 子行：搭配用法不可遺失

07 課第 9 筆「かけます」單獨沒有意義，課本教的是「電話を　かけます」，
下方印著一行 `［でんわを～］　［電話を～］`（沒有行號、跟上一筆的假名
欄 x 對齊）。判定「是否為前一筆的 usage 子行」需同時滿足：

1. 該行**沒有**行號前綴（不匹配預期序號）。
2. 該行第一個 Cell 的 x 與這一課的假名欄 x 在 `_ALIGN_TOL` 內對齊。
3. 該行文字含 `［` 或 `〔`。

三者缺一都不算——07 課 ことば 頁尾附有一個「本課會話用語」小框（`■会
話` 開頭），裡面的內容 x 起點不對齊（25.8 vs 假名欄 53.4）、也有一行
含 `〔` 但 x 起點也不對齊（12.0），兩個條件都會擋下它，不會被誤判成
單字的 usage 子行。usage 子行內部改用「相鄰 Cell 最大縫隙」把假名／
漢字兩段切開（`_split_usage_cells`；不是貼近學出來的 `kanji_x`——子行
的漢字用法欄開頭印著「［」，這個前導方括號造成的抖動常常超出
`_KANJI_TOL`，15 課甚至完全學不出 `kanji_x`，兩種情形都會讓「貼近
`kanji_x`」的作法漏判），並把外層 `［］`／`〔〕` 去掉，符合任務簡報
介面說明的 `{"kana": "でんわを～", "kanji": "電話を～"}` 形狀。

## 中文欄的角括號 `〔〕` 不可被過濾

07 課第 9 筆中文是「打〔電話〕」——`〔`、`〕`本身是中文釋義的一部分
（強調可替換的部分），過濾規則（`_has_real_content`）只用來判斷「一
個貼近 `kanji_x` 的 Cell 群組是不是真漢字」（防呆極少數場景：`kanji_x`
容差內剛好落了一個純標點 Cell），從不套用在中文欄本身；中文欄一律原
樣拼接、只做首尾空白 `strip()`。

## 已知限制

`_MIN_COLUMN_HITS`、`_MIN_COLUMN_GAP`、`_ZH_MARGIN`、`_KANJI_TOL` 這幾
個常數是用全 15 課（01.pdf ~ 15.pdf）ことば 區段的實測欄位分布校正
的，量測結果見 `task-7-report.md`。若未來課別的版面比例差異更大（例
如中文釋義極長、內部縫隙逼近甚至超過中文欄的抖動容許範圍），這幾個常
數可能需要重新檢視。

14、15 課的動詞群組標記（Ⅰ／Ⅱ／Ⅲ）版面全課從不把假名/漢字切成分開
的 Cell（例如「たちます  Ⅰ           立ちます」整段是一個 Cell，漢字
緊接在假名之後），因此這兩課學不出獨立的 `kanji_x`——這是本模組能正
確處理的情形（靠 `_first_ideograph` 切開、`_extract_group` 把羅馬數字
抽成獨立欄位）。

**但這兩課共 10 筆單字是已知、已逐一核對過原始 Fragment 座標（15 課
第 2 筆並算繪 15.pdf 第 1 頁核對過視覺位置）的資料損毀，本模組無法修
復**：`fragments.py` 把「動詞分類羅馬數字」跟「中文釋義的第一個字」
解碼成同一個 Fragment（例如 14 課第 6 筆的 Fragment 文字是 `"Ⅰ等"`
——「等」其實是中文釋義「等待」的第一個字；15 課第 2 筆是 `"Ⅰ坐"`），
`layout.py` 用 `fonts.char_width` 估計 Fragment 內部個別字元位置時，
這個真實課本用巨大字距（`Tc`）撐到中文欄的字，估計位置遠低於它真實
的版面位置（`Fragment` 資料結構不攜帶 `Tc`，這是複審在 Task 4 就已
經明確裁決延後、屬於本任務才會咬到的已知殘留限制），導致這個字被錯
誤地黏在動詞分類羅馬數字後面、緊接在漢字讀音前面，而不是留在遠在右
側的中文欄。

用 shipped 的 `parse_vocab` 重新量測，全 15 課 628 筆單字裡，這個根因
共影響以下 **10 筆**（14 課 6 筆、15 課 4 筆；此前只記錄了 15 課第 2
筆，複審後發現範圍更廣，這裡更正）：

| 課/編號 | kana（正確） | 目前輸出 kanji | 目前輸出 zh | 推測正確 kanji／zh |
|---|---|---|---|---|
| 14/6 | まちます | `等待ちます` | `待` | `待ちます` ／ `等待` |
| 14/8 | まがります | `轉曲がります` | `向〔右邊〕` | `曲がります` ／ `向〔右邊〕轉` |
| 14/15 | おしえます | `告教えます` | `訴〔地址〕` | `教えます` ／ `告訴〔地址〕` |
| 14/16 | はじめます | `開始めます` | `始` | `始めます` ／ `開始` |
| 14/17 | ふります | `下降ります` | `〔雨〕` | `降ります` ／ `下〔雨〕` |
| 14/18 | コピーします | `影`（誤植，此詞無漢字） | `印` | `None` ／ `影印` |
| 15/2 | すわります | `座ります坐` | `` | `座ります` ／ `坐` |
| 15/7 | しります | `知ります得` | `知` | `知ります` ／ `得知` |
| 15/8 | すみます | `住みます居` | `住` | `住みます` ／ `居住` |
| 15/9 | けんきゅうします | `研究します研` | `究` | `研究します` ／ `研究` |

（「推測正確」欄是人工比對日文動詞常見中文翻譯得出，不是本模組自動修
正的結果，只用於說明損毀的性質；14 課第 18 筆更嚴重——`コピーします`
是外來語動詞、本來就沒有漢字讀音，卻因為這個根因被誤植出一個假的
`kanji="影"`。）

`parse_vocab` 沒有嘗試用文字內容猜測修補（例如「連續兩個表意文字中間
隔著假名就在第二個表意文字處二次切分」這類規則），因為這類規則對合
法的複合動詞讀音（例如「書き込みます」，漢字讀音本身就含兩個被假名
隔開的表意文字）會造成新的誤判。根因在 `fragments.py`／`layout.py`
（`Fragment` 不攜帶 `Tc`），不是本模組的欄位判定邏輯；選擇誠實回報、
如實輸出，而不是用未驗證的啟發式掩蓋。
"""
import re
import unicodedata
from collections import Counter
from typing import Dict, List, Optional, Tuple

from tools.extract.layout import Cell, Line
from tools.extract.sections import Section

# 行首編號：可能有前導全形/半形空白（例如「  10.」），數字後通常接一
# 個半形句點（可選，見模組說明「行號防呆」），其後任何內容（含空白）
# 都留給 group(2)（見模組說明「行號吸附後續文字」的情形，例如某些課
# 別的引號被 `cells()` 併進了標籤 Cell）。
_ENTRY_RE = re.compile(r"^\s*(\d+)\.?(.*)$", re.S)

# 判定一個 x 是不是「固定版面欄位」的最少重複次數；中文續行因標點被
# 切開產生的 x 幾乎每筆都不同，很少剛好重複到這個次數以上（見模組說
# 明「中文欄名目起點與抖動」）。
_MIN_COLUMN_HITS = 3

# 兩個候選欄位 x 之間，被視為「確實是不同欄位」的最小距離（pt）。全
# 15 課實測任兩個真正欄位之間的距離都遠大於這個值。
_MIN_COLUMN_GAP = 100.0

# 中文欄地板 = 學出的中文欄名目起點（抖動後較低的那個叢集） − 這個
# 邊際值，留安全餘裕。
_ZH_MARGIN = 30.0

# 判定一個 Cell 的 x 是否貼近學出來的漢字欄 x 的容差（pt）。漢字欄 x
# 是精確重複的固定版面座標，不需要很寬的容差。
_KANJI_TOL = 5.0

# usage 子行 x 對齊容差（pt）：實測同一欄位 x 是精確浮點值，留一點餘裕
# 防浮點誤差，不需要很寬。
_ALIGN_TOL = 3.0


def _is_ideograph(ch: str) -> bool:
    return ("一" <= ch <= "鿿") or ("㐀" <= ch <= "䶿")


def _first_ideograph(text: str) -> Optional[int]:
    for i, ch in enumerate(text):
        if _is_ideograph(ch):
            return i
    return None


# 課本從第 14 課開始，在假名欄後面用羅馬數字標註動詞分類（Ⅰ／Ⅱ／Ⅲ
# 類，動詞變化練習需要這個資訊才能推導て形、ない形等），見模組說明
# 「動詞分類記號（group）」。
_GROUP_MARKS = {"Ⅰ": "I", "Ⅱ": "II", "Ⅲ": "III"}


def _extract_group(kana: str) -> Tuple[str, Optional[str]]:
    """從假名欄文字裡找動詞分類羅馬數字，抽成獨立的 `group` 值並從假名
    欄移除。見模組說明「動詞分類記號（group）」。"""
    for mark, name in _GROUP_MARKS.items():
        if mark in kana:
            return kana.replace(mark, ""), name
    return kana, None


def _has_real_content(text: str) -> bool:
    """判斷一段文字是不是「純標點/空白的偽欄位」——見模組說明「中文欄
    的角括號不可被過濾」：這個判斷只用在疑似漢字欄，從不套用在中文欄
    本身。Unicode 類別開頭 P（標點）或 Z（空白分隔）的字元視為不算實
    質內容；假名、漢字、片假名等（類別 Lo）都算。"""
    return any(unicodedata.category(ch)[0] not in ("P", "Z") for ch in text)


def _join(cells: List[Cell]) -> str:
    return "".join(c.text for c in cells).strip()


def _strip_brackets(s: str) -> str:
    s = s.strip()
    if s[:1] in ("［", "〔"):
        s = s[1:]
    if s[-1:] in ("］", "〕"):
        s = s[:-1]
    return s


def _match_entry(line: Line) -> Optional[Tuple[int, List[Cell]]]:
    """若這一行是單字列（行首有編號），回傳 (編號, 資料 Cell 列表)；
    資料 Cell 已去掉行號標籤本身，且把標籤吸附的殘留文字（見模組說明）
    併回最前面。不是單字列則回傳 None（不做行號防呆——呼叫端自行比對
    預期序號，見 `parse_vocab`/`_learn_columns`）。"""
    m = _ENTRY_RE.match(line.text())
    if not m:
        return None
    no = int(m.group(1))

    cells = line.cells()
    lm = _ENTRY_RE.match(cells[0].text)
    leftover = lm.group(2) if lm else ""
    data: List[Cell] = list(cells[1:])
    if leftover.strip():
        data = [Cell(x=cells[0].x, text=leftover, frags=[])] + data
    return no, data


def _learn_columns(lines: List[Line]) -> Tuple[float, Optional[float], Optional[float]]:
    """學出這一課的 (假名欄 x, 漢字欄 x 或 None, 中文欄地板 x 或
    None)。見模組說明「為什麼不能只看相鄰 Cell 的間距」與「中文欄名
    目起點與抖動」。只採用「行號跟預期序號精確銜接」的行（見模組說明
    「行號防呆」），避免非單字內容（例如課文附錄的號碼）污染統計。"""
    kana_counts: Counter = Counter()
    other_counts: Counter = Counter()
    expected = 1

    for line in lines:
        matched = _match_entry(line)
        if matched is None:
            continue
        no, data = matched
        if no != expected:
            continue
        expected += 1
        if not data:
            continue
        kana_counts[round(data[0].x, 1)] += 1
        for c in data[1:]:
            other_counts[round(c.x, 1)] += 1

    kana_x = kana_counts.most_common(1)[0][0] if kana_counts else 0.0

    candidates = sorted(
        x for x, cnt in other_counts.items()
        if cnt >= _MIN_COLUMN_HITS and x - kana_x >= _MIN_COLUMN_GAP
    )

    if not candidates:
        return kana_x, None, None

    kanji_x: Optional[float] = None
    zh_ref: Optional[float] = None
    for x in candidates:
        if zh_ref is None and kanji_x is None:
            kanji_x = x
            continue
        if x - kanji_x >= _MIN_COLUMN_GAP:
            zh_ref = x
            break

    if zh_ref is None:
        # 只有一個夠遠的高頻叢集：這一課沒有另外的漢字欄，這個叢集本
        # 身就是中文欄名目起點。
        zh_ref = kanji_x
        kanji_x = None

    zh_floor = zh_ref - _ZH_MARGIN
    return kana_x, kanji_x, zh_floor


def _split_data_cells(
    data: List[Cell], kanji_x: Optional[float], zh_floor: Optional[float]
) -> Tuple[List[Cell], List[Cell], List[Cell]]:
    """狀態機：依序掃描一筆單字的資料 Cell，決定「假名／漢字／中文」
    三欄的歸屬。見模組說明「改用『絕對位置 + 狀態機』解決第 1 類問
    題」——已經進入某一欄之後，同一欄內部後續的 Cell 一律留在同一欄，
    只有 Cell x 真正貼近下一個欄位邊界才會換欄。"""
    kana_cells: List[Cell] = []
    kanji_cells: List[Cell] = []
    zh_cells: List[Cell] = []
    state = "kana"

    for c in data:
        if state == "kana":
            if kanji_x is not None and abs(c.x - kanji_x) <= _KANJI_TOL:
                state = "kanji"
            elif zh_floor is not None and c.x >= zh_floor:
                state = "zh"
        elif state == "kanji":
            if zh_floor is not None and c.x >= zh_floor:
                state = "zh"
        # state == "zh"：不再切換。

        if state == "kana":
            kana_cells.append(c)
        elif state == "kanji":
            kanji_cells.append(c)
        else:
            zh_cells.append(c)

    return kana_cells, kanji_cells, zh_cells


def _parse_entry_line(
    no: int, data: List[Cell], kanji_x: Optional[float], zh_floor: Optional[float]
) -> Dict:
    kana_cells, kanji_cells, zh_cells = _split_data_cells(data, kanji_x, zh_floor)

    kana = _join(kana_cells)
    kanji = _join(kanji_cells)
    zh = _join(zh_cells)

    if kanji and not _has_real_content(kanji):
        # 疑似漢字欄其實是純標點造成的偽欄位——併回中文欄開頭（見模組
        # 說明「中文欄的角括號不可被過濾」：這個過濾只用在這裡）。
        zh = _join(kanji_cells + zh_cells)
        kanji = ""

    if not kanji:
        idx = _first_ideograph(kana)
        if idx is not None:
            # 緊排單字：假名／漢字擠在同一個 Cell 內，見模組說明。
            kanji = kana[idx:]
            kana = kana[:idx]

    kana, group = _extract_group(kana)

    kana = kana.strip()
    kanji = kanji.strip()
    zh = zh.strip()

    return {
        "no": no,
        "kana": kana,
        "kanji": kanji if kanji else None,
        "zh": zh,
        "usage": None,
        "group": group,
    }


def _is_usage_subline(line: Line, kana_x: float) -> bool:
    cells = line.cells()
    if not cells:
        return False
    if abs(cells[0].x - kana_x) > _ALIGN_TOL:
        return False
    text = line.text()
    return ("［" in text) or ("〔" in text)


# usage 子行「假名用法／漢字用法」兩欄之間，視為真正換欄的最小間距
# （pt）。見 `_split_usage_cells` 說明：欄內縫隙（同一括號片語內部）
# 實測 <=19.8pt，真正換欄的縫隙實測 >=66pt，50pt 留有安全邊界。
_USAGE_SPLIT_GAP = 50.0


def _split_usage_cells(cells: List[Cell]) -> Tuple[List[Cell], List[Cell]]:
    """usage 子行只有假名／漢字兩欄（沒有中文欄），用「相鄰 Cell 間最
    大縫隙」切成兩組，而不是比對學出來的 `kanji_x`：子行的漢字用法欄
    開頭印著「［」，這個前導方括號會讓整欄往左抖動（06 課實測抖動量
    13.8pt，跟中文欄的抖動量級相同，見模組說明「中文欄名目起點與抖
    動」），若沿用貼近 `kanji_x` 的精確容差比對會漏判、整行被誤判成只
    有假名沒有漢字（06 課第 9、11 筆、11 課第 4 筆都是這個模式）。15
    課更進一步：這一課的單字本身從不把假名/漢字切成分開的 Cell（見模
    組說明「已知限制」），完全學不出 `kanji_x`，貼近 `kanji_x` 的作法
    對這一課的 usage 子行必然失效。

    改用相鄰 Cell 的最大間距來找換欄點：全 15 課實測，同一欄位內部（括
    號片語自身）的縫隙全部 <=19.8pt，真正的假名／漢字換欄縫隙全部
    >=66pt，`_USAGE_SPLIT_GAP`（50pt）介於兩者之間。只有一個 Cell、或
    最大縫隙小於門檻（只有單一括號、沒有對應的漢字用法，例如 12 課
    「［コーヒーが～］」）時，回傳全部歸假名、漢字為 `None`。"""
    if len(cells) < 2:
        return list(cells), []
    gaps = [(cells[i + 1].x - cells[i].x, i) for i in range(len(cells) - 1)]
    max_gap, split_at = max(gaps)
    if max_gap < _USAGE_SPLIT_GAP:
        return list(cells), []
    return cells[:split_at + 1], cells[split_at + 1:]


def _parse_usage_line(line: Line) -> Dict:
    kana_cells, kanji_cells = _split_usage_cells(line.cells())
    kana = _strip_brackets(_join(kana_cells))
    kanji = _strip_brackets(_join(kanji_cells)) if kanji_cells else None
    return {"kana": kana, "kanji": kanji}


def parse_vocab(section: Section) -> List[Dict]:
    """把 `ことば` Section 解析成單字紀錄列表，見模組說明。"""
    kana_x, kanji_x, zh_floor = _learn_columns(section.lines)

    entries: List[Dict] = []
    last_entry: Optional[Dict] = None
    expected = 1

    for line in section.lines:
        matched = _match_entry(line)
        if matched is not None and matched[0] == expected:
            no, data = matched
            entry = _parse_entry_line(no, data, kanji_x, zh_floor)
            entries.append(entry)
            last_entry = entry
            expected += 1
            continue

        if (last_entry is not None and last_entry["usage"] is None
                and _is_usage_subline(line, kana_x)):
            last_entry["usage"] = _parse_usage_line(line)

    return entries
