"""PDF 物件層：把 PDF 位元組解析成頁面物件（內容流 + Resources 字典）。

不依賴任何第三方套件，僅使用標準函式庫（re / zlib）。支援三種在課本 PDF
中實測遇到的結構變體：
  1. 全部物件皆為明文（無壓縮物件流，如 PDF 1.3）。
  2. 全部物件皆封裝在壓縮物件流（ObjStm）中（如 PDF 1.6）。
  3. 明文物件與壓縮物件流混合（如 PDF 1.7）。
"""
import re
import zlib
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class Page:
    number: int        # 1-based
    content: bytes      # 已解壓並串接的內容流
    resources: bytes    # /Resources 字典的原始位元組（含外層 << >>）


# PDF 名稱物件（ISO 32000-1 §7.3.5）的合法字元：除了空白與定界字元
# `( ) < > [ ] { } / %` 之外的任何位元組都合法；`#xx`（兩位十六進位）
# 是逃脫序列，代表單一實際位元組（可能剛好是定界字元或空白本身）。
#
# Task 6 複審時發現的真實臭蟲：`tools/extract/fragments.py` 原本的 `Tf`
# 字型名正則只認 `[A-Za-z0-9]+`，13.pdf 用底線命名的字型資源（`C2_0`、
# `C2_1`）完全匹配不到——正則不匹配時 `Tf` 這個 token 整個被
# `_TOKEN.finditer` 跳過，字型狀態 `state.font` 永遠停留在初始值 `""`，
# 之後查編碼表用 `encodings.get(state.font, _DEFAULT_ENCODING)` 找不到
# 空字串這個 key，靜默退回 `cp1252`，把日文 Shift-JIS 位元組硬讀成西歐
# 字元，整課變亂碼卻不報錯。這裡把「PDF 合法名稱字元」定義成一個共用
# 常數，讓 `fragments.py`（解析 `Tf` 運算子）與 `fonts.py`（列舉
# `/Font` 資源字典的 key）用同一套規則比對，避免兩邊字元類別不一致造成
# 新的、更隱蔽的 key 對不上的臭蟲。
#
# 這裡把 `#` 寫成 `\#`：這個常數會被嵌入 `fragments.py` 用 `re.X`
# （verbose）模式編譯的大型 token 正則裡，verbose 模式下未跳脫的 `#`
# 會被當成註解起始字元，吃掉到行尾的所有內容，把逃脫序列這段規則整個
# 弄壞。跳脫成 `\#` 在 verbose 與非 verbose 模式下都正確比對字面上的
# `#`，兩邊嵌入都安全。
PDF_NAME_TOKEN = rb"(?:\#[0-9A-Fa-f]{2}|[^#\s()<>\[\]{}/%])+"


def decode_pdf_name(raw: bytes) -> bytes:
    """把一個 PDF 名稱物件的原始位元組（不含開頭的 `/`，通常就是用
    `PDF_NAME_TOKEN` 比對出來的那段）解析成實際位元組序列：把 `#xx`
    十六進位逃脫序列還原成它代表的單一位元組，其餘位元組原樣保留。"""
    out = bytearray()
    i = 0
    n = len(raw)
    while i < n:
        if raw[i:i + 1] == b"#" and i + 2 < n:
            hex_part = raw[i + 1:i + 3]
            try:
                out.append(int(hex_part, 16))
                i += 3
                continue
            except ValueError:
                pass
        out.append(raw[i])
        i += 1
    return bytes(out)


def extract_balanced_dict(data: bytes, start: int) -> bytes:
    """從 data[start] 的 '<<' 開始，回傳含外層 << >> 的完整字典位元組。"""
    assert data[start:start + 2] == b"<<"
    depth = 0
    i = start
    while i < len(data) - 1:
        pair = data[i:i + 2]
        if pair == b"<<":
            depth += 1
            i += 2
            continue
        if pair == b">>":
            depth -= 1
            i += 2
            if depth == 0:
                return data[start:i]
            continue
        i += 1
    raise ValueError("unbalanced dictionary")


_OBJ_RE = re.compile(rb"(\d+)\s+0\s+obj(.*?)endobj", re.S)
_REF_RE = re.compile(rb"(\d+)\s+0\s+R")


class PDFDoc:
    def __init__(self, data: bytes):
        self._data = data
        self._objects: Dict[int, bytes] = {}
        self._parse_objects()
        self._parse_objstms()
        self._pages: Optional[List[Page]] = None

    @classmethod
    def from_path(cls, path: str) -> "PDFDoc":
        with open(path, "rb") as f:
            return cls(f.read())

    def get_object(self, num: int) -> bytes:
        """物件本體位元組（不含 "N 0 obj"/"endobj"）。"""
        return self._objects[num]

    # ------------------------------------------------------------------
    # 建立物件表
    # ------------------------------------------------------------------

    def _parse_objects(self) -> None:
        for m in _OBJ_RE.finditer(self._data):
            num = int(m.group(1))
            self._objects[num] = m.group(2)

    def _parse_objstms(self) -> None:
        # 對一份既有物件的快照做迭代：合併壓縮物件流不應影響本次掃描對象。
        for body in list(self._objects.values()):
            if not re.search(rb"/Type\s*/ObjStm", body):
                continue
            stream = self._extract_stream_from_body(body)
            if stream is None:
                continue
            self._parse_objstm(body, stream)

    def _extract_stream_from_body(self, body: bytes) -> Optional[bytes]:
        m = re.search(rb"stream\r?\n", body)
        if not m:
            return None
        start = m.end()
        end = body.find(b"endstream", start)
        if end == -1:
            end = len(body)
        raw = body[start:end]
        try:
            return zlib.decompress(raw)
        except zlib.error:
            return raw

    def _parse_objstm(self, body: bytes, stream: bytes) -> None:
        n = int(re.search(rb"/N\s+(\d+)", body).group(1))
        first = int(re.search(rb"/First\s+(\d+)", body).group(1))
        header = stream[:first].split()
        for k in range(n):
            num = int(header[2 * k])
            off = int(header[2 * k + 1])
            end = int(header[2 * k + 3]) + first if k + 1 < n else len(stream)
            if num not in self._objects:          # 明文物件優先，不覆蓋
                self._objects[num] = stream[first + off:end]

    # ------------------------------------------------------------------
    # 頁面樹
    # ------------------------------------------------------------------

    @property
    def pages(self) -> List[Page]:
        if self._pages is None:
            self._pages = self._build_pages()
        return self._pages

    def _find_catalog(self) -> Optional[int]:
        for num, body in self._objects.items():
            if re.search(rb"/Type\s*/Catalog", body):
                return num
        return None

    def _build_pages(self) -> List[Page]:
        page_nums = self._collect_page_object_numbers()
        pages = []
        for i, num in enumerate(page_nums, start=1):
            body = self._objects[num]
            content = self._get_page_content(body)
            resources = self._get_page_resources(num)
            pages.append(Page(number=i, content=content, resources=resources))
        return pages

    def _collect_page_object_numbers(self) -> List[int]:
        catalog_num = self._find_catalog()
        if catalog_num is not None:
            catalog_body = self._objects[catalog_num]
            m = re.search(rb"/Pages\s+(\d+)\s+0\s+R", catalog_body)
            if m:
                nums: List[int] = []
                self._collect_kids(int(m.group(1)), nums)
                if nums:
                    return nums
        # 找不到 Catalog（或找不到有效頁面）：退回掃描所有 /Type /Page 物件，
        # 依物件編號排序。
        nums = [
            num for num, body in self._objects.items()
            if re.search(rb"/Type\s*/Page(?!s)", body)
        ]
        nums.sort()
        return nums

    def _collect_kids(self, num: int, out: List[int]) -> None:
        body = self._objects.get(num)
        if body is None:
            return
        kids_array = self._resolve_kids_array(body)
        if kids_array is not None:
            for ref in _REF_RE.finditer(kids_array):
                self._collect_kids(int(ref.group(1)), out)
        else:
            out.append(num)

    def _resolve_kids_array(self, body: bytes) -> Optional[bytes]:
        """回傳 /Kids 陣列內容（不含中括號），若此節點無 /Kids 則回傳 None。

        /Kids 的值可以是內嵌陣列（`/Kids [ 1 0 R 2 0 R ]`），也可以是指向
        陣列物件的間接參照（`/Kids 9 0 R`）——兩者皆為合法 PDF 語法，
        後者常見於頁數多、由不同工具產生的檔案。
        """
        m = re.search(rb"/Kids\s*\[(.*?)\]", body, re.S)
        if m:
            return m.group(1)
        ref_m = re.search(rb"/Kids\s+(\d+)\s+0\s+R", body)
        if ref_m:
            arr_body = self._objects.get(int(ref_m.group(1)))
            if arr_body is None:
                return None
            arr_m = re.search(rb"\[(.*?)\]", arr_body, re.S)
            if arr_m:
                return arr_m.group(1)
            return None
        return None

    # ------------------------------------------------------------------
    # 內容流
    # ------------------------------------------------------------------

    def _get_page_content(self, body: bytes) -> bytes:
        content_nums = self._resolve_content_numbers(body)
        parts = []
        for num in content_nums:
            obj_body = self._objects.get(num)
            if obj_body is None:
                continue
            stream = self._extract_stream_from_body(obj_body)
            if stream is not None:
                parts.append(stream)
        return b"\n".join(parts)

    def _resolve_content_numbers(self, body: bytes) -> List[int]:
        m = re.search(rb"/Contents\s+(\d+)\s+0\s+R", body)
        if m:
            return [int(m.group(1))]
        arr_m = re.search(rb"/Contents\s*\[(.*?)\]", body, re.S)
        if arr_m:
            return [int(r.group(1)) for r in _REF_RE.finditer(arr_m.group(1))]
        return []

    # ------------------------------------------------------------------
    # Resources（含向上繼承）
    # ------------------------------------------------------------------

    def _get_page_resources(self, num: int) -> bytes:
        cur: Optional[int] = num
        seen = set()
        while cur is not None and cur not in seen:
            seen.add(cur)
            body = self._objects.get(cur)
            if body is None:
                break
            res = self._extract_resources(body)
            if res is not None:
                return res
            parent_m = re.search(rb"/Parent\s+(\d+)\s+0\s+R", body)
            cur = int(parent_m.group(1)) if parent_m else None
        return b"<< >>"

    def _extract_resources(self, body: bytes) -> Optional[bytes]:
        # 間接參照：/Resources 12 0 R
        m = re.search(rb"/Resources\s+(\d+)\s+0\s+R", body)
        if m:
            ref_body = self._objects.get(int(m.group(1)))
            if ref_body is None:
                return None
            dict_m = re.search(rb"<<", ref_body)
            if dict_m is None:
                return None
            return extract_balanced_dict(ref_body, dict_m.start())
        # 直接內嵌字典：/Resources << ... >>
        m2 = re.search(rb"/Resources\s*(<<)", body)
        if m2:
            return extract_balanced_dict(body, m2.start(1))
        return None
