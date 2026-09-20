"""插畫影像抽取：把頁面內容流裡 `cm ... Do` 放置的點陣圖影像寫成檔案，
並回傳每張影像的頁碼與頁面座標。

不依賴任何第三方套件，僅使用標準函式庫（re / zlib / struct / os）。

## 抽取流程

1. 對每一頁的內容流找出 `a 0 0 d e f cm` 緊接著 `/Name Do` 的樣式（依
   簡報指示；實測全 15 課、908 個影像 Do 呼叫，每一個都緊接在恰好一個
   6 參數 `cm` 之後、`b`、`c` 兩個剪切/旋轉分量恆為 0——這裡不嘗試維護
   完整的圖形狀態堆疊（`q`/`Q`、巢狀 `cm` 相乘），只認這個已驗證涵蓋全
   corpus 的樣式；不符合這個樣式的 `Do` 會被略過且不計入 index，寧可
   漏掉也不要算出錯的座標）。
2. 依 `/Name` 查頁面 `/Resources /XObject` 字典解析出物件編號，取得該
   物件字典＋串流位元組。非 `/Subtype /Image`（例如 Form XObject）或帶
   `/ImageMask true`（模板遮罩，沒有自己的色彩，需要當時的填色狀態才能
   還原，這裡不追蹤）一律跳過。
3. 依 `/Filter` 分派：
   - `DCTDecode`：串流本身就是 JPEG，原樣寫成 `.jpg`。
   - `FlateDecode`：解壓後為原始樣本，依 `/ColorSpace` 解析出調色盤
     （`/Indexed`）或灰階／RGB（直接色彩空間或 `/ICCBased`），手工封裝
     成 `.png`（IHDR/PLTE?/IDAT/IEND）。
   - 其他過濾器（`CCITTFaxDecode` 等）或無法辨識的色彩空間、多重過濾器
     鏈：記錄並跳過，不視為錯誤、不計入 index。
4. 檔名 `{lesson:02d}-p{page:02d}-{index:02d}.{ext}`，index 只對「實際
   寫出檔案」的影像計數（跳過的不佔位，同一頁的檔名連號不留缺口），保
   證重跑時逐位元組相同。
"""
import os
import re
import struct
import zlib
from typing import Dict, List, Optional, Tuple

from tools.extract.pdfobj import PDFDoc, Page, PDF_NAME_TOKEN, decode_pdf_name

_NUM = rb"[+-]?\d*\.?\d+"
_CM_DO_RE = re.compile(
    rb"(" + _NUM + rb")\s+(" + _NUM + rb")\s+(" + _NUM + rb")\s+(" + _NUM +
    rb")\s+(" + _NUM + rb")\s+(" + _NUM + rb")\s+cm\s*/(" + PDF_NAME_TOKEN +
    rb")\s+Do"
)


def extract_images(doc: PDFDoc, lesson: int, out_dir: str) -> List[Dict]:
    """抽取 `doc` 全部頁面的插畫影像，寫到 `out_dir`，回傳
    `[{"file", "page", "x", "y", "w", "h"}, ...]`（依頁碼、頁內出現順序）。
    """
    os.makedirs(out_dir, exist_ok=True)
    results: List[Dict] = []
    for page in doc.pages:
        xobjects = _page_xobjects(page)
        if not xobjects:
            continue
        index = 0
        for name, x, y, w, h in _find_placements(page.content):
            obj_num = xobjects.get(name)
            if obj_num is None:
                continue
            body = doc.get_object(obj_num)
            written = _write_image(doc, body, lesson, page.number, index + 1, out_dir)
            if written is None:
                continue
            filename, _ext = written
            index += 1
            results.append({
                "file": filename,
                "page": page.number,
                "x": x, "y": y, "w": w, "h": h,
            })
    return results


# --------------------------------------------------------------------------
# 內容流：找出 `cm ... Do` 影像放置
# --------------------------------------------------------------------------

def _find_placements(content: bytes) -> List[Tuple[str, float, float, float, float]]:
    """回傳依內容流出現順序排列的 `(名稱, x, y, w, h)` 清單。

    `a 0 0 d e f cm` 之後 `/Name Do`：`e`、`f` 是左下角座標，`a`、`d` 是
    寬高（見模組說明：全 15 課實測 `b`、`c` 恆為 0，`a`、`d` 恆為正）。
    """
    out = []
    for m in _CM_DO_RE.finditer(content):
        a, b, c, d, e, f, raw_name = m.groups()
        name = decode_pdf_name(raw_name).decode("latin-1")
        out.append((name, float(e), float(f), float(a), float(d)))
    return out


def _page_xobjects(page: Page) -> Dict[str, int]:
    """`/Resources /XObject` 字典：`{資源名(不含斜線): 物件編號}`。"""
    result: Dict[str, int] = {}
    m = re.search(rb"/XObject\s*(<<.*?>>)", page.resources, re.S)
    if not m:
        return result
    for mm in re.finditer(rb"/(" + PDF_NAME_TOKEN + rb")\s+(\d+)\s+0\s+R", m.group(1)):
        result[decode_pdf_name(mm.group(1)).decode("latin-1")] = int(mm.group(2))
    return result


# --------------------------------------------------------------------------
# 影像物件本體：分派 / 寫檔
# --------------------------------------------------------------------------

def _write_image(doc: PDFDoc, body: bytes, lesson: int, page: int, index: int,
                  out_dir: str) -> Optional[Tuple[str, str]]:
    if not re.search(rb"/Subtype\s*/Image", body):
        return None
    if re.search(rb"/ImageMask\s+true", body):
        return None
    filt = _single_filter(body)
    if filt is None:
        return None
    stream = _stream_bytes(body)

    if filt == b"DCTDecode":
        ext = "jpg"
        data = stream
    elif filt == b"FlateDecode":
        try:
            raw = zlib.decompress(stream)
        except zlib.error:
            return None
        png = _build_png(doc, body, raw)
        if png is None:
            return None
        ext = "png"
        data = png
    else:
        return None

    filename = os.path.join(out_dir, "%02d-p%02d-%02d.%s" % (lesson, page, index, ext))
    with open(filename, "wb") as fh:
        fh.write(data)
    return filename, ext


def _single_filter(body: bytes) -> Optional[bytes]:
    """回傳單一 `/Filter` 名稱；找不到、或多重過濾器鏈（陣列超過一個
    元素）一律回傳 None（呼叫端視為不支援，跳過）。"""
    m = re.search(rb"/Filter\s*/(" + PDF_NAME_TOKEN + rb")", body)
    if m:
        return m.group(1)
    arr_m = re.search(rb"/Filter\s*\[(.*?)\]", body, re.S)
    if arr_m:
        names = re.findall(rb"/(" + PDF_NAME_TOKEN + rb")", arr_m.group(1))
        if len(names) == 1:
            return names[0]
    return None


def _stream_bytes(body: bytes) -> bytes:
    """物件字典後 `stream`～`endstream` 之間的原始位元組。優先用
    `/Length`（本語料庫全部 290 個影像物件皆為直接整數，非間接參照）取
    精確長度；`/Length` 缺失或為間接參照時，退回搜尋 `endstream` 並剝除
    其前的行尾標記。"""
    start_m = re.search(rb"stream\r?\n", body)
    if not start_m:
        return b""
    start = start_m.end()
    len_m = re.search(rb"/Length\s+(\d+)", body)
    if len_m:
        tail = body[len_m.end():len_m.end() + 16]
        if not re.match(rb"\s+0\s+R", tail):
            return body[start:start + int(len_m.group(1))]
    end = body.find(b"endstream", start)
    if end == -1:
        end = len(body)
    raw = body[start:end]
    if raw.endswith(b"\r\n"):
        raw = raw[:-2]
    elif raw.endswith(b"\n") or raw.endswith(b"\r"):
        raw = raw[:-1]
    return raw


# --------------------------------------------------------------------------
# 色彩空間解析
# --------------------------------------------------------------------------

# (kind, components, palette)：kind 為 "gray"/"rgb"/"cmyk"/"indexed"；
# indexed 的 components 恆為 1（樣本值即調色盤索引），palette 為攤平的
# RGB 三元組位元組（PNG PLTE 格式）。
_ColorSpace = Tuple[str, int, Optional[bytes]]

_DEVICE_NAME_KIND = {
    "DeviceGray": ("gray", 1),
    "CalGray": ("gray", 1),
    "DeviceRGB": ("rgb", 3),
    "CalRGB": ("rgb", 3),
    "DeviceCMYK": ("cmyk", 4),
}


def _resolve_colorspace(doc: PDFDoc, image_body: bytes) -> Optional[_ColorSpace]:
    m = re.search(rb"/ColorSpace\s+(\d+)\s+0\s+R", image_body)
    if m:
        cs_body = doc.get_object(int(m.group(1)))
    else:
        m2 = re.search(rb"/ColorSpace\s*(/" + PDF_NAME_TOKEN + rb")", image_body)
        if not m2:
            return None
        cs_body = m2.group(1)
    return _classify_colorspace(doc, cs_body)


def _classify_colorspace(doc: PDFDoc, cs_body: bytes) -> Optional[_ColorSpace]:
    cs_body = cs_body.strip()
    if cs_body.startswith(b"/"):
        name = decode_pdf_name(cs_body[1:]).decode("latin-1")
        kind = _DEVICE_NAME_KIND.get(name)
        return (kind[0], kind[1], None) if kind else None
    if not cs_body.startswith(b"["):
        return None
    inner = cs_body[1:-1] if cs_body.endswith(b"]") else cs_body[1:]
    inner = inner.strip()
    if inner.startswith(b"/Indexed"):
        return _classify_indexed(doc, inner)
    if inner.startswith(b"/ICCBased"):
        ref = re.search(rb"/ICCBased\s+(\d+)\s+0\s+R", inner)
        if not ref:
            return None
        icc_body = doc.get_object(int(ref.group(1)))
        n = re.search(rb"/N\s+(\d+)", icc_body)
        comps = int(n.group(1)) if n else 3
        kind = {1: "gray", 3: "rgb", 4: "cmyk"}.get(comps)
        return (kind, comps, None) if kind else None
    for name, (kind, comps) in _DEVICE_NAME_KIND.items():
        if inner.startswith(b"/" + name.encode("ascii")):
            return (kind, comps, None)
    return None


def _classify_indexed(doc: PDFDoc, inner: bytes) -> Optional[_ColorSpace]:
    """`inner` 形如 `/Indexed base hival lookup`。`base` 可以是間接參照
    或直接色彩空間名稱；`lookup` 可以是間接串流參照，或 PDF literal
    string `(...)`（本語料庫實測全部 238 個 Indexed 影像的 `base` 都是
    間接參照（解到 `/ICCBased`，N=3）、`lookup` 都是串流間接參照——
    以下 `base` 為直接名稱、`lookup` 為 literal string 這兩個分支未被
    真實語料觸發，只由合成測試涵蓋，見 test_images.py）。"""
    m = re.match(
        rb"/Indexed\s+(?:(\d+)\s+0\s+R|(/" + PDF_NAME_TOKEN + rb"))\s+(\d+)\s+(.+)",
        inner, re.S,
    )
    if not m:
        return None
    ref_num, name_base, hival_s, rest = m.groups()
    if ref_num is not None:
        base = _classify_colorspace(doc, doc.get_object(int(ref_num)))
    else:
        base = _classify_colorspace(doc, name_base)
    if base is None or base[0] == "cmyk":
        return None
    base_kind, base_comps, _ = base
    hival = int(hival_s)
    rest = rest.strip()

    lookup_ref_m = re.match(rb"(\d+)\s+0\s+R", rest)
    if lookup_ref_m:
        lookup_body = doc.get_object(int(lookup_ref_m.group(1)))
        palette_raw = _stream_bytes(lookup_body)
        if b"/FlateDecode" in lookup_body:
            try:
                palette_raw = zlib.decompress(palette_raw)
            except zlib.error:
                return None
    else:
        lit_m = re.match(rb"\(", rest)
        if not lit_m:
            return None
        palette_raw = _extract_literal_string(rest, 0)

    expected = (hival + 1) * base_comps
    if len(palette_raw) < expected:
        return None
    palette_raw = palette_raw[:expected]

    if base_kind == "gray":
        palette_rgb = bytearray()
        for byte in palette_raw:
            palette_rgb += bytes([byte, byte, byte])
        palette_raw = bytes(palette_rgb)
    elif base_kind != "rgb":
        return None
    return "indexed", 1, palette_raw


def _extract_literal_string(data: bytes, start: int) -> bytes:
    """解析 PDF literal string `(...)`（ISO 32000-1 §7.3.4.2）：處理
    `\\n \\r \\t \\b \\f \\( \\) \\\\`、最多三位數 8 進位逃脫，以及平衡但
    未逃脫的內層括號。回傳還原後的原始位元組（不含外層括號）。"""
    assert data[start:start + 1] == b"("
    i = start + 1
    depth = 1
    out = bytearray()
    escapes = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f"}
    n = len(data)
    while i < n:
        c = data[i:i + 1]
        if c == b"\\":
            nxt = data[i + 1:i + 2]
            if nxt in escapes:
                out += escapes[nxt]
                i += 2
                continue
            if nxt in (b"(", b")", b"\\"):
                out += nxt
                i += 2
                continue
            if nxt.isdigit():
                m = re.match(rb"[0-7]{1,3}", data[i + 1:i + 4])
                digits = m.group(0)
                out.append(int(digits, 8) & 0xFF)
                i += 1 + len(digits)
                continue
            out += nxt
            i += 2
            continue
        if c == b"(":
            depth += 1
            out += c
            i += 1
            continue
        if c == b")":
            depth -= 1
            i += 1
            if depth == 0:
                return bytes(out)
            out += c
            continue
        out += c
        i += 1
    return bytes(out)


# --------------------------------------------------------------------------
# PNG 封裝（IHDR / PLTE? / IDAT / IEND）
# --------------------------------------------------------------------------

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_COLOR_TYPE = {"gray": 0, "rgb": 2, "indexed": 3}


def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return (struct.pack(">I", len(data)) + tag + data +
            struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))


def _build_png(doc: PDFDoc, image_body: bytes, raw_samples: bytes) -> Optional[bytes]:
    w_m = re.search(rb"/Width\s+(\d+)", image_body)
    h_m = re.search(rb"/Height\s+(\d+)", image_body)
    bpc_m = re.search(rb"/BitsPerComponent\s+(\d+)", image_body)
    if not (w_m and h_m and bpc_m):
        return None
    width = int(w_m.group(1))
    height = int(h_m.group(1))
    bpc = int(bpc_m.group(1))
    if bpc != 8:
        return None  # 本語料庫恆為 8；其他位元深度未經驗證，寧可跳過

    cs = _resolve_colorspace(doc, image_body)
    if cs is None:
        return None
    kind, comps, palette = cs
    color_type = _COLOR_TYPE.get(kind)
    if color_type is None:
        return None

    row_bytes = width * comps
    expected = row_bytes * height
    if len(raw_samples) < expected:
        return None
    raw_samples = raw_samples[:expected]

    out = bytearray()
    for y in range(height):
        out.append(0)  # PNG per-scanline filter type：None
        out += raw_samples[y * row_bytes:(y + 1) * row_bytes]
    compressed = zlib.compress(bytes(out), 9)

    ihdr = struct.pack(">IIBBBBB", width, height, bpc, color_type, 0, 0, 0)
    chunks = [_PNG_SIGNATURE, _png_chunk(b"IHDR", ihdr)]
    if color_type == 3:
        if palette is None:
            return None
        chunks.append(_png_chunk(b"PLTE", palette))
    chunks.append(_png_chunk(b"IDAT", compressed))
    chunks.append(_png_chunk(b"IEND", b""))
    return b"".join(chunks)
