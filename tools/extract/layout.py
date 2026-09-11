"""版面分組：把帶座標的 Fragment 組成「行」，再把行切成「欄」。

`group_lines` 依 (page, y) 把 fragment 分群成 Line（同群 y 差距在 y_tol
內視為同一行），只納入正文字級（size >= 8.0）；振假名（4.8pt）由 ruby.py
另行處理。

`Line.cells` 依欄位 x 間距把一行內已排序的 fragment 切成 Cell。切分依據
「前一個 fragment 估計的右端」與「目前 fragment 的左端」之間的距離：超過
min_gap 即視為換欄。

## 右端估算：為何不是單一係數

右端估算需要「這段文字大概畫到哪裡」，用的是 `tools.extract.fonts.text_width`
（全形 1.0 倍字級、半形 0.5 倍字級、空白 0——依課本內嵌 CIDFont 的 `/DW`、
`/W` 度量分類，完整依據見該函式旁的說明）。`fragments.py` 抽 TJ 陣列內字串
的自然前進寬度也是同一份邏輯，避免兩處各自維護、可能漂移的字寬常數。

**已知殘留限制**（詳見 Task 4 report）：本估算法仍是「標稱前進寬度」
（advance width），不是字形實際墨水外框（ink extent）。在少數欄位緊貼
的列（例如單字表第 2 筆「おくります」與其行號標籤之間，真實留白小於
一個假名字寬），仍可能因估計右端超出行號標籤起點而誤判為同一欄。這是
任何不解析內嵌字型 glyph outline 的前進寬度估算法的固有限制；本模組驗
收所依賴的兩筆單字（第 1、3 筆）與代入表測試不受此限制影響。
"""
from dataclasses import dataclass
from typing import List

from tools.extract.fonts import text_width
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
            prev_right = f.x + text_width(f.text, f.size)
        if cur:
            out.append(Cell(x=cur[0].x, text="".join(g.text for g in cur), frags=cur))
        return out


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
