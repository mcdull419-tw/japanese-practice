"""內容流轉為帶座標的 Fragment。

逐一掃描內容流中的文字繪製運算子，維護目前的字型、文字矩陣（位置、字級），
每遇到一個十六進位字串（`<hex> Tj` 或 `TJ` 陣列中的元素）就產生一個
`Fragment`。刻意不合併相鄰片段——細粒度的 x 座標是後續模組（振假名配對、
欄位切分、日中交錯合併）唯一的依據。

## Tm 與 Tlm 是兩個矩陣，不能合併成一個 x/y

`_TextState` 依 PDF 規格分別追蹤 Tm（目前畫筆位置，Tj/TJ 顯示文字時用來
定位並推進）與 Tlm（文字行矩陣，Td/TD/T* 的基準）。`Tj`/`TJ` 顯示文字時
只會推進 Tm（依字元自然前進寬度，見 `fonts.text_width`；TJ 陣列中的數字
另外疊加字距調整，單位為 1/1000 文字空間），完全不動 Tlm；`Td`/`TD`/`T*`
只操作 Tlm，操作完會把 Tm 重設為新的 Tlm，捨棄先前顯示文字造成的畫筆漂移。

若誤把兩者合併成同一個 x/y，`TJ` 陣列顯示文字造成的畫筆漂移會被下一個
`Td`/`TD` 誤當成行首疊加位移，座標可能暴衝到頁面外——中文釋義常見於
「同一個 TJ 陣列顯示＋稍後用 Td/TD 換行」的組合，因此最容易踩到這個坑。

## 字型名解析失敗必須大聲失敗，不能靜默退回預設編碼

Task 6 複審（`task-6-report.md` 附加段落）發現：`Tf` 字型名正則原本只
認 `[A-Za-z0-9]+`，13.pdf 用底線命名的字型資源（`/C2_0`、`/C2_1`）完
全匹配不到——正則不匹配時整個 `Tf` token 被 `_TOKEN.finditer` 跳過，
`state.font` 永遠停留在初始值 `""`；之後每個 `Tj`/`TJ` 顯示文字時，
`encodings.get(state.font, _DEFAULT_ENCODING)` 找不到 `""` 這個 key，
靜默退回 `cp1252`，把 Shift-JIS 位元組硬讀成西歐字元。13.pdf 第 1 頁
（`ことば` 標題與大部分單字表所在頁）因此整頁變成亂碼（`'ことば'` 變
成 `'‚±‚Æ‚Î'`），但沒有任何例外或錯誤訊息——15 課全綠的測試套件完全
沒發現這一課壞掉，這是這條管線第四次出現「測試全綠但資料是壞的」。

兩處修正：

1. **字型名正則改用 `pdfobj.PDF_NAME_TOKEN`**（依 ISO 32000-1 §7.3.5
   定義的合法名稱字元，含底線、`+`、`-`、`.`、`#xx` 逃脫序列等），不
   是簡報字面上「補一個底線」這種頭痛醫頭的修法——正則的疏漏只是這次
   觸發靜默失敗的其中一個原因，這裡把名稱字元集合一次做對，減少日後
   再被別的合法字元踩到同一種洞的機會。`fonts.py` 列舉 `/Font` 資源
   字典 key 的正則也改用同一個常數並套用 `decode_pdf_name`，確保兩邊
   對同一個字型名稱有完全一致的解讀，不會因為字元類別不一致而彼此對
   不上（見 `pdfobj.PDF_NAME_TOKEN` 說明）。
2. **`_emit()` 查不到字型的編碼時，直接丟 `UnresolvedFontError`**，不
   再 `encodings.get(state.font, _DEFAULT_ENCODING)` 靜默回退。理由：
   `encodings` 這個字典是 `font_encodings()` 對「這一頁 `/Font` 資源
   字典裡真實宣告的每一個字型」各自決定編碼後產生的（決策不到的字型
   會在 `font_encodings()` 那一層就有自己的 fallback 邏輯，見
   `fonts.py`），所以只要 `state.font` 是這一頁真的宣告過的字型，就一
   定找得到對應的編碼；找不到，代表 `state.font` 本身有問題——可能是
   字型名解析失敗（這次的根因）、可能是內容流引用了未宣告的字型資
   源、也可能是 `Tj`/`TJ` 出現在任何 `Tf` 之前（`state.font` 還停在初
   始值）。這三種情形都是「不知道該用什麼編碼解碼」，猜一個預設值產
   出來的文字沒有任何正確性保證，必須讓呼叫方立刻知道，而不是悄悄產
   出一個看起來像 `Fragment`、實際上文字是亂碼的物件。選擇「立刻丟例
   外」而非「記錄後由驗證層事後攔截」，是因為 `extract_fragments()`
   幾乎是所有下游模組與測試共同的進入點——例外會讓對應那一課的萃取立
   刻整個失敗、無法被忽略；若改成收集錯誤清單、事後才檢查，還是要靠
   額外寫的驗證測試才會被看到，等於把「這個模組本來就該保證的不變量」
   外包給呼叫方，跟這次的問題（不變量被默默違反卻沒人檢查）是同一種
   結構性風險。
"""
import re
from dataclasses import dataclass
from typing import List

from tools.extract.fonts import font_encodings, decode_hex, text_width
from tools.extract.pdfobj import Page, PDFDoc, PDF_NAME_TOKEN, decode_pdf_name


class UnresolvedFontError(RuntimeError):
    """`Tf` 選用的字型名，在這一頁 `/Font` 資源字典解析出的編碼表裡找
    不到對應項目——這是錯誤狀態（字型名解析失敗、內容流引用未宣告的字
    型資源、或文字顯示運算子出現在任何 `Tf` 之前），不可以靜默退回預
    設編碼產出亂碼。見模組說明「字型名解析失敗必須大聲失敗」。"""


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
    /(?P<font>""" + PDF_NAME_TOKEN + rb""")\s+""" + _NUM + rb"""\s+Tf
  | (?P<tm>""" + _NUM + (rb"\s+" + _NUM) * 5 + rb""")\s+Tm
  | (?P<td>""" + _NUM + rb"\s+" + _NUM + rb""")\s+(?P<tdop>TD|Td)
  | <(?P<tj>[0-9A-Fa-f]*)>\s*Tj
  | \[(?P<tjarr>[^\]]*)\]\s*TJ
  | (?P<bt>BT)
  | (?P<tstar>T\*)
  | (?P<tl>""" + _NUM + rb""")\s+TL
  | (?P<tc>""" + _NUM + rb""")\s+Tc
  | (?P<tw>""" + _NUM + rb""")\s+Tw
""", re.X)

# 元素於 TJ 陣列內：十六進位字串或字距調整數字。
_TJ_ITEM = re.compile(rb"<(?P<hex>[0-9A-Fa-f]*)>|(?P<num>[-\d.]+)")


class _TextState:
    """追蹤目前字型，以及兩個各自獨立的矩陣：Tm（目前畫筆位置）與 Tlm
    （文字行矩陣，換行基準）。

    ISO 32000-1 §9.4.2–9.4.3 明確區分兩者：`Td`/`TD`/`T*` 只讀寫 Tlm，
    寫完後把 Tm 重設為新的 Tlm；`Tj`/`TJ` 顯示文字時只推進 Tm（依字元
    自然前進寬度、TJ 的字距調整數字），完全不碰 Tlm。若誤把兩者合併成
    同一個 x/y（本模組先前版本即是如此），TJ 陣列顯示文字造成的畫筆
    漂移會被「下一個 Td/TD 以為是行首而疊加位移」誤用，座標可能暴衝到
    頁面外——中文釋義常見於「同一個 TJ 陣列顯示＋稍後用 Td/TD 換行」的
    組合，因此最容易踩到這個坑（實測：07.pdf 第 9 筆單字「打電話」的
    中文欄位曾因此被算到 x≈1020，遠超頁寬 595）。
    """

    def __init__(self):
        self.font = ""
        self.x = 0.0        # Tm.e：目前畫筆位置，Fragment 的座標來源
        self.y = 0.0        # Tm.f
        self.line_x = 0.0   # Tlm.e：Td/TD/T* 的基準與寫入對象
        self.line_y = 0.0   # Tlm.f
        self.size = 1.0
        self.a = 1.0    # 文字矩陣水平縮放（一般等於 size）
        self.d = 1.0    # 文字矩陣垂直縮放（一般等於 size）
        self.leading = 0.0
        self.tc = 0.0   # 字元間距 Tc：每個顯示字元額外前進，未縮放文字空間
        self.tw = 0.0   # 字間距 Tw：僅套用於解碼後為 ASCII 空白（U+0020）的字元

    def reset_matrix(self) -> None:
        """BT：Tm 與 Tlm 皆重設為單位矩陣。

        `Tc`/`Tw`（連同 `Tz`/`TL`/`Tr`/`Trise`）屬於文字狀態參數，是圖形
        狀態的一部分，依規格不會被 `BT` 重設，因此這裡刻意不動。
        """
        self.x = self.y = 0.0
        self.line_x = self.line_y = 0.0
        self.a = 1.0
        self.d = 1.0
        self.size = 1.0

    def set_tm(self, a: float, b: float, c: float, d: float, e: float, f: float) -> None:
        """`a b c d e f Tm`：依規格同時設定 Tm 與 Tlm 為同一個值。"""
        self.a = a
        self.d = d
        self.x = self.line_x = e
        self.y = self.line_y = f
        self.size = d

    def move_td(self, tx: float, ty: float) -> None:
        """Td/TD：Tlm 依 (tx, ty)（未縮放文字空間）平移；Tm 重設為新 Tlm。"""
        self.line_x += tx * self.a
        self.line_y += ty * self.d
        self.x = self.line_x
        self.y = self.line_y

    def next_line(self) -> None:
        """T*：等同於 `0 -leading Td`。"""
        self.move_td(0.0, -self.leading)

    def advance(self, dx: float) -> None:
        """Tj/TJ 顯示文字（自然前進寬度或 TJ 字距調整）後，Tm 前進；Tlm 不受影響。"""
        self.x += dx


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
            # latin-1（不是 ascii）：`decode_pdf_name` 還原 `#xx` 逃脫序
            # 列後可能產生 0x80~0xFF 的位元組，跟 `fonts.py` 列舉
            # `/Font` 資源字典 key 時的解碼方式一致（見該模組），確保兩
            # 邊對同一個字型名稱得到完全相同的字串，查表時 key 對得上。
            state.font = decode_pdf_name(m.group("font")).decode("latin-1")
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
        elif m.group("tc") is not None:
            state.tc = float(m.group("tc"))
        elif m.group("tw") is not None:
            state.tw = float(m.group("tw"))

    return frags


def _emit(frags: List[Fragment], state: _TextState, encodings, hex_bytes: bytes, page_number: int) -> None:
    """解碼一個十六進位字串、產生一個 Fragment，並依 ISO 32000-1 §9.4.3
    讓目前 x 前進該字串顯示後的位移總和。

    這一步是 Tj/TJ 都必須做的一半：畫出文字後，筆的位置本來就會移動到
    文字結束處，接下來（若在 TJ 陣列中）才疊加字距調整數字；若漏掉這一步，
    同一個 TJ 陣列裡的後續字串會疊在同一個 x，順序錯亂（尤其是中文字串，
    因為中文釋義多半整段包在同一個 TJ 陣列裡、字串之間又常常沒有調整數字）。

    位移總和有三個來源，缺一都會讓少數（但實測確實存在的）片段座標算錯：
    - 自然前進寬度（`fonts.text_width`，依全形/半形分類）；
    - 字元間距 `Tc`：每個顯示字元都加一次，單位為未縮放文字空間；
    - 字間距 `Tw`：只加在解碼後為 ASCII 空白（U+0020）的字元上——這批課本
      字型的空白字元在原始位元組中恆為單一位元組 0x20（cp932/gb18030 皆
      未把 0x20 納入任何雙位元組序列），符合規格「Tw 只套用於單位元組
      code 32」的條件。
    某些裝飾性內容（例如語法分類標籤的粗體疊字效果）會同時設定很大的
    `Tc` 與很大的 TJ 字距調整數字，兩者互相抵銷、視覺上幾乎疊在同一點；
    若沒有把 `Tc` 一併算進來，只看到 TJ 調整數字的那一半，會讓筆座標暴衝
    到頁面外（實測：01.pdf 第 7 頁一段裝飾文字曾因此算出 x<0）。
    """
    hex_str = hex_bytes.decode("ascii", errors="replace")
    if state.font not in encodings:
        raise UnresolvedFontError(
            "page %d: current font %r has no resolvable encoding in this "
            "page's /Font resource dict (known fonts: %r) — a Tf name "
            "may have failed to parse, referenced an undeclared font "
            "resource, or no Tf appeared before this text-showing "
            "operator. Refusing to guess an encoding and silently "
            "produce mis-decoded text (see module docstring)."
            % (page_number, state.font, sorted(encodings))
        )
    encoding = encodings[state.font]
    text = decode_hex(hex_str, encoding)
    frags.append(Fragment(
        text=text,
        x=state.x,
        y=state.y,
        size=state.size,
        font=state.font,
        page=page_number,
    ))
    extra = len(text) * state.tc * state.a
    extra += text.count(" ") * state.tw * state.a
    state.advance(text_width(text, state.size) + extra)


def _emit_tj_array(frags: List[Fragment], state: _TextState, encodings, arr_bytes: bytes, page_number: int) -> None:
    for item in _TJ_ITEM.finditer(arr_bytes):
        if item.group("hex") is not None:
            _emit(frags, state, encodings, item.group("hex"), page_number)
        else:
            adjustment = float(item.group("num"))
            state.advance(-adjustment / 1000.0 * state.size)


def extract_fragments(doc: PDFDoc) -> List[Fragment]:
    frags: List[Fragment] = []
    for page in doc.pages:
        frags.extend(page_fragments(doc, page))
    return frags
