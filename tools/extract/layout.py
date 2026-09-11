"""版面分組：把帶座標的 Fragment 組成「行」，再把行切成「欄」。

`group_lines` 依 (page, y) 把 fragment 分群成 Line（同群 y 差距在 y_tol
內視為同一行），只納入正文字級（size >= 8.0）；振假名（4.8pt）由 ruby.py
另行處理。

## 閱讀順序重建在「字元」粒度，不是「fragment」粒度

課本會把日文詞彙插進中文說明的字元之間（反之亦然）——同一視覺列裡，後
畫的 fragment 座標可能落在先畫的 fragment 內部（例如中文釋義「打電話」
被拆成「打電」「〔」「話」「〕」四個 fragment，「〔」的 x 落在「打電」
內部）。若依 fragment 起點 x 排序、逐 fragment 串接文字，會把這類穿插
的 fragment 整批插在錯誤位置（見 Task 4 report 的「打電〔話〕」對比
「打〔電話〕」）。

`Line.text()`／`Line.cells()` 因此把每個 fragment 依
`tools.extract.fonts.char_width` 展開成逐字元的 `(字元, x)`，所有字元
（跨 fragment）依 x 全域排序後才組成行文字／欄位。這樣「〔」自然落在
「打」與「電」之間，不需要特別處理。

### 排序同分時的判斷（tie-break）

字元展開後，同一行內偶爾會有兩個字元的估計 x 完全相同：

1. **fragment 起點字元 vs. fragment 內部（衍生）字元**：fragment 起點
   的 x 是文件本身寫死的錨點（來自 Tm/Td/TD 或 TJ 字距調整數字），
   fragment 內部第 2 個字起的 x 則是本模組依 `char_width` 累加推算出來
   的估計值。實測發現：當 fragment 內文字有 `Tc`（字元間距，Fragment
   目前不攜帶這項資訊）時，這個估計值會系統性偏小（例如「打電」的
   「電」字實際套用 `1 Tc` 後的真實前進位置比純 `char_width` 推算多
   13.2pt，但 `Fragment` 沒有 Tc 資訊可用）。因此當兩者打平，優先採信
   「真正的錨點」——這在偏差存在時也是比較保守、比較可能正確的選擇。
2. **兩個都是 fragment 起點字元**（兩個各自獨立、都是文件錨點的
   fragment 剛好落在同一 x）：這種情況下無法用上述規則區分。實測到
   的唯一案例（07 課「だれ」列，`“どなた”是“だれ”` 的「是」與
   「“だれ”」的開引號打平）中，正確讀法要求非開頭標點的字元（「是」）
   排在前面，開頭標點（左引號／左括號，Unicode 類別 `Ps`/`Pi`）排在
   後面——開頭標點在語意上是「接住後面的內容」，跟不相干的前文平手時
   應該讓前文先讀完。這條規則只在極少數兩個 fragment 起點字元剛好完全
   同 x 時才會用到（見 Task 4 report 的量化統計）。

三層排序鍵（由粗到細）：`(x, tier, 進場順序)`，其中 `tier`：
`0`＝fragment 起點且非開頭標點；`1`＝fragment 起點且是開頭標點；
`2`＝fragment 內部（非起點）的衍生字元。「進場順序」只是避免 Python
排序在極端情況下不穩定，不帶語意。

**已知殘留限制**：這個 tie-break 是依實際檢視 07/01 課內容流歸納出的
啟發式，不是從規格推導出的通用規則；若未來課別出現更多、方向不同的
打平案例，可能需要修正。真正一勞永逸的解法是讓 `Fragment` 攜帶 `Tc`
（本模組驗收所需的兩個具體案例皆已確認不受 `Tc`/`Tw` 影響，屬於乾淨的
座標打平，但一般情況下 `Tc` 造成的「衍生字元位置被低估」仍是潛在成因，
詳見 Task 4 report 判斷題）。
"""
import unicodedata
from dataclasses import dataclass
from typing import List, Tuple

from tools.extract.fonts import char_width
from tools.extract.fragments import Fragment

_MIN_BODY_SIZE = 8.0

# tie-break 的 tier 常數（見模組說明）。
_TIER_ANCHOR_PLAIN = 0      # fragment 起點，非開頭標點
_TIER_ANCHOR_OPEN_PUNCT = 1  # fragment 起點，是開頭標點（“「〔（…）
_TIER_DERIVED = 2           # fragment 內部衍生字元


@dataclass
class Cell:
    x: float
    text: str
    frags: List[Fragment]      # 對這個欄位有貢獻（哪怕只貢獻部分字元）的來源 fragment，依出現順序、不重複


@dataclass
class Line:
    y: float
    page: int
    frags: List[Fragment]          # 已依 fragment 起點 x 排序；實際閱讀順序見 text()/cells()

    def text(self) -> str:
        return "".join(ch for ch, _x, _f in _line_chars(self.frags))

    def cells(self, min_gap: float = 10.0) -> List[Cell]:
        chars = _line_chars(self.frags)
        out: List[Cell] = []
        cur_chars: List[Tuple[str, float]] = []
        cur_frags: List[Fragment] = []
        prev_right = None
        for ch, x, f in chars:
            if prev_right is not None and x - prev_right > min_gap and cur_chars:
                out.append(_make_cell(cur_chars, cur_frags))
                cur_chars = []
                cur_frags = []
            cur_chars.append((ch, x))
            if not cur_frags or cur_frags[-1] is not f:
                cur_frags.append(f)
            prev_right = x + char_width(ch, f.size)
        if cur_chars:
            out.append(_make_cell(cur_chars, cur_frags))
        return out


def _make_cell(cur_chars: List[Tuple[str, float]], cur_frags: List[Fragment]) -> Cell:
    return Cell(
        x=cur_chars[0][1],
        text="".join(ch for ch, _x in cur_chars),
        frags=list(cur_frags),
    )


def _is_opening_punct(ch: str) -> bool:
    """Unicode 類別 Ps（開放標點，如 （〔「『【）或 Pi（起始引號，如 “）。"""
    return unicodedata.category(ch) in ("Ps", "Pi")


def _fragment_chars(f: Fragment) -> List[Tuple[str, float, bool]]:
    """把一個 fragment 展開成逐字元的 (字元, x, 是否為 fragment 起點字元)。

    第一個字元的 x 固定等於 `f.x`（文件本身的錨點）；後續字元的 x 是依
    `fonts.char_width` 累加的估計值（見模組說明的殘留限制）。
    """
    out: List[Tuple[str, float, bool]] = []
    x = f.x
    for i, ch in enumerate(f.text):
        out.append((ch, x, i == 0))
        x += char_width(ch, f.size)
    return out


def _sort_key(x: float, is_initial: bool, ch: str, order: int) -> Tuple[float, int, int]:
    if not is_initial:
        tier = _TIER_DERIVED
    elif _is_opening_punct(ch):
        tier = _TIER_ANCHOR_OPEN_PUNCT
    else:
        tier = _TIER_ANCHOR_PLAIN
    return (x, tier, order)


def _line_chars(frags: List[Fragment]) -> List[Tuple[str, float, Fragment]]:
    """把一行內所有 fragment 展開、依全域 x（含 tie-break）排序。

    回傳 (字元, x, 來源 fragment) 序列，即這一行的正確閱讀順序——這是
    `Line.text()` 與 `Line.cells()` 唯一的真實來源，兩者必須一致。
    """
    entries = []
    order = 0
    for f in frags:
        for ch, x, is_initial in _fragment_chars(f):
            entries.append((ch, x, is_initial, f, order))
            order += 1
    entries.sort(key=lambda e: _sort_key(e[1], e[2], e[0], e[4]))
    return [(ch, x, f) for ch, x, _is_initial, f, _order in entries]


def group_lines(frags: List[Fragment], y_tol: float = 2.0) -> List[Line]:
    """把 fragment 依 (page, y) 分群成 Line，回傳依 (page, -y) 排序（閱讀順序）。

    只納入正文字級（size >= 8.0）；振假名由 ruby.py 處理。
    """
    body = [f for f in frags if f.size >= _MIN_BODY_SIZE]
    body.sort(key=lambda f: (f.page, -f.y))

    lines: List[Line] = []
    bucket: List[Fragment] = []
    anchor_page = None
    anchor_y = None

    for f in body:
        if bucket and f.page == anchor_page and abs(f.y - anchor_y) <= y_tol:
            bucket.append(f)
        else:
            if bucket:
                lines.append(_build_line(anchor_page, anchor_y, bucket))
            bucket = [f]
            anchor_page = f.page
            anchor_y = f.y

    if bucket:
        lines.append(_build_line(anchor_page, anchor_y, bucket))

    return lines


def _build_line(page: int, y: float, frags: List[Fragment]) -> Line:
    return Line(y=y, page=page, frags=sorted(frags, key=lambda f: f.x))
