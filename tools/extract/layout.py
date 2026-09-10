"""版面分組：把帶座標的 Fragment 組成「行」，再把行切成「欄」。

`group_lines` 依 (page, y) 把 fragment 分群成 Line（同群 y 差距在 y_tol
內視為同一行），只納入正文字級（size >= 8.0）；振假名（4.8pt）由 ruby.py
另行處理。

`Line.cells` 依欄位 x 間距把一行內已排序的 fragment 切成 Cell。切分依據
「前一個 fragment 估計的右端」與「目前 fragment 的左端」之間的距離：超過
min_gap 即視為換欄。

## 右端估算：為何不是單一係數

右端估算需要「這段文字大概畫到哪裡」。逐字元檢視發現寬度並非單一比例：

- 全形字元（假名、漢字、全形標點如「，」「〔」）：實測本課字型的內嵌
  CIDFont 皆宣告 `/DW 1000`（預設字寬 = 100% 字級）——例如 TT2
  （MSGothic, `90ms-RKSJ-H`）的 descendant font 物件與 TT4（SimSun,
  `GBK-EUC-H`）皆是 `/DW 1000`。
- 半形字元（ASCII 字母、數字、標點）：TT2 的 descendant font 另外宣告了
  `/W` 陣列，明確把一批 CID（涵蓋單字表中「   1.」「  10.」這類半形數字
  標籤所用的字碼）覆寫為寬度 500（= 50% 字級）。這正是課本裡「單字表
  行號標籤與假名/漢字之間留白很窄」的成因——若誤用全形寬度估計，行號
  標籤的右端會被高估，導致無法切開。
- 空白字元不佔可視墨水，切欄只在乎「看得到的內容延伸到哪裡」，因此空白
  一律計為零寬——這對行號標籤（如「   1.」有 3 個前導空白）尤其關鍵：
  若比照半形字元給 0.5 倍字級，前導空白仍會把估計右端推得過遠，導致
  01 行的「   1.」與「切ります」無法正確切開。

以上三類寬度（全形 1.0、半形 0.5、空白 0）皆可由內嵌字型物件（`/DW`、
`/W`）與「空白無墨水」的物理事實佐證，而非「調到測試變綠」的單一
折衷係數。

**已知殘留限制**（詳見 Task 4 report）：本估算法仍是「標稱前進寬度」
（advance width），不是字形實際墨水外框（ink extent）。在少數欄位緊貼
的列（例如單字表第 2 筆「おくります」與其行號標籤之間，真實留白小於
一個假名字寬），仍可能因估計右端超出行號標籤起點而誤判為同一欄。這是
任何不解析內嵌字型 glyph outline 的前進寬度估算法的固有限制；本模組驗
收所依賴的兩筆單字（第 1、3 筆）與代入表測試不受此限制影響。
"""
from dataclasses import dataclass
from typing import List

from tools.extract.fragments import Fragment

_MIN_BODY_SIZE = 8.0


@dataclass
class Cell:
    x: float
    text: str
    frags: List[Fragment]


@dataclass
class Line:
    y: float
    page: int
    frags: List[Fragment]          # 已依 x 排序

    def text(self) -> str:
        return "".join(f.text for f in self.frags)

    def cells(self, min_gap: float = 10.0) -> List[Cell]:
        out: List[Cell] = []
        cur: List[Fragment] = []
        prev_right = None
        for f in self.frags:
            left = f.x
            if prev_right is not None and left - prev_right > min_gap and cur:
                out.append(Cell(x=cur[0].x, text="".join(g.text for g in cur), frags=cur))
                cur = []
            cur.append(f)
            prev_right = f.x + _text_width(f.text, f.size)
        if cur:
            out.append(Cell(x=cur[0].x, text="".join(g.text for g in cur), frags=cur))
        return out


def _char_width(ch: str, size: float) -> float:
    """單一字元的估計前進寬度（見模組說明的三類寬度依據）。"""
    if ch.isspace():
        return 0.0
    if ord(ch) < 0x100:
        # 半形（ASCII / Latin-1）：課本內嵌字型 /W 覆寫為 500（0.5 倍字級）。
        return 0.5 * size
    # 全形（假名、漢字、全形標點）：內嵌字型 /DW 1000（1.0 倍字級）。
    return 1.0 * size


def _text_width(text: str, size: float) -> float:
    return sum(_char_width(c, size) for c in text)


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
