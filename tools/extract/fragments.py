"""內容流轉為帶座標的 Fragment。

逐一掃描內容流中的文字繪製運算子，維護目前的字型、文字矩陣（位置、字級），
每遇到一個十六進位字串（`<hex> Tj` 或 `TJ` 陣列中的元素）就產生一個
`Fragment`。刻意不合併相鄰片段——細粒度的 x 座標是後續模組（振假名配對、
欄位切分、日中交錯合併）唯一的依據。
"""
import re
from dataclasses import dataclass
from typing import List

from tools.extract.fonts import font_encodings, decode_hex
from tools.extract.pdfobj import Page, PDFDoc


@dataclass
class Fragment:
    text: str
    x: float
    y: float
    size: float
    font: str     # 資源名，如 'TT2'
    page: int     # 1-based


_NUM = rb"[-\d.]+"

_TOKEN = re.compile(rb"""
    /(?P<font>[A-Za-z0-9]+)\s+""" + _NUM + rb"""\s+Tf
  | (?P<tm>""" + _NUM + (rb"\s+" + _NUM) * 5 + rb""")\s+Tm
  | (?P<td>""" + _NUM + rb"\s+" + _NUM + rb""")\s+(?P<tdop>TD|Td)
  | <(?P<tj>[0-9A-Fa-f]*)>\s*Tj
  | \[(?P<tjarr>[^\]]*)\]\s*TJ
  | (?P<bt>BT)
  | (?P<tstar>T\*)
  | (?P<tl>""" + _NUM + rb""")\s+TL
""", re.X)

# 元素於 TJ 陣列內：十六進位字串或字距調整數字。
_TJ_ITEM = re.compile(rb"<(?P<hex>[0-9A-Fa-f]*)>|(?P<num>[-\d.]+)")

_DEFAULT_ENCODING = "cp1252"


class _TextState:
    """追蹤目前字型與文字矩陣（位置、字級）。"""

    def __init__(self):
        self.font = ""
        self.x = 0.0
        self.y = 0.0
        self.size = 1.0
        self.a = 1.0    # 文字矩陣水平縮放（一般等於 size）
        self.d = 1.0    # 文字矩陣垂直縮放（一般等於 size）
        self.leading = 0.0

    def reset_matrix(self) -> None:
        """BT：重設文字矩陣為單位矩陣。"""
        self.x = 0.0
        self.y = 0.0
        self.a = 1.0
        self.d = 1.0
        self.size = 1.0

    def set_tm(self, a: float, b: float, c: float, d: float, e: float, f: float) -> None:
        self.a = a
        self.d = d
        self.x = e
        self.y = f
        self.size = d

    def move_td(self, tx: float, ty: float) -> None:
        """Td/TD：於目前文字行矩陣下平移 (tx, ty)（單位為未縮放文字空間）。"""
        self.x += tx * self.a
        self.y += ty * self.d

    def next_line(self) -> None:
        """T*：等同於 `0 -leading Td`。"""
        self.move_td(0.0, -self.leading)


def page_fragments(doc: PDFDoc, page: Page) -> List[Fragment]:
    encodings = font_encodings(doc, page)
    state = _TextState()
    frags: List[Fragment] = []

    for m in _TOKEN.finditer(page.content):
        # NOTE: `m.lastgroup` is unreliable here — the Td/TD branch matches
        # two named groups (`td` and `tdop`) in one alternative, and
        # `lastgroup` returns whichever of them is rightmost in the pattern
        # (always "tdop"), not "whichever branch matched". Check each named
        # group explicitly (with `is not None`, since `tj`/`tjarr` can
        # legitimately capture an empty string, which is falsy).
        if m.group("font") is not None:
            state.font = m.group("font").decode("ascii")
        elif m.group("tdop") is not None:
            tx_str, ty_str = m.group("td").split()
            tx, ty = float(tx_str), float(ty_str)
            if m.group("tdop") == b"TD":
                state.leading = -ty
            state.move_td(tx, ty)
        elif m.group("tm") is not None:
            nums = [float(n) for n in m.group("tm").split()]
            state.set_tm(*nums)
        elif m.group("tj") is not None:
            _emit(frags, state, encodings, m.group("tj"), page.number)
        elif m.group("tjarr") is not None:
            _emit_tj_array(frags, state, encodings, m.group("tjarr"), page.number)
        elif m.group("bt") is not None:
            state.reset_matrix()
        elif m.group("tstar") is not None:
            state.next_line()
        elif m.group("tl") is not None:
            state.leading = float(m.group("tl"))

    return frags


def _emit(frags: List[Fragment], state: _TextState, encodings, hex_bytes: bytes, page_number: int) -> None:
    hex_str = hex_bytes.decode("ascii", errors="replace")
    encoding = encodings.get(state.font, _DEFAULT_ENCODING)
    text = decode_hex(hex_str, encoding)
    frags.append(Fragment(
        text=text,
        x=state.x,
        y=state.y,
        size=state.size,
        font=state.font,
        page=page_number,
    ))


def _emit_tj_array(frags: List[Fragment], state: _TextState, encodings, arr_bytes: bytes, page_number: int) -> None:
    for item in _TJ_ITEM.finditer(arr_bytes):
        if item.group("hex") is not None:
            _emit(frags, state, encodings, item.group("hex"), page_number)
        else:
            adjustment = float(item.group("num"))
            state.x -= adjustment / 1000.0 * state.size


def extract_fragments(doc: PDFDoc) -> List[Fragment]:
    frags: List[Fragment] = []
    for page in doc.pages:
        frags.extend(page_fragments(doc, page))
    return frags
