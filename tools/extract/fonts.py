import re
from typing import Dict

_ENCODING_RULES = (
    (("RKSJ", "90MS", "90MSP"), "cp932"),
    (("GBK", "GB-", "GBPC", "GBKP"), "gb18030"),
    (("WINANSI",), "cp1252"),
)

_CHINESE_FONTS = ("SIMSUN", "SIMHEI", "STSONG", "FANGSONG", "KAITI")


def _encoding_from_name(name: str) -> str:
    upper = name.upper()
    for needles, enc in _ENCODING_RULES:
        for needle in needles:
            if needle in upper:
                return enc
    return "cp1252"


def _encoding_from_basefont(name: str) -> str:
    """由 /BaseFont 推導編碼，用於缺少 /Encoding 的情況。"""
    upper = name.upper()
    if "GOTHIC" in upper or "MINCHO" in upper:
        return "cp932"
    for font in _CHINESE_FONTS:
        if font in upper:
            return "gb18030"
    return "cp1252"


def font_encodings(doc, page) -> Dict[str, str]:
    """回傳 {字型資源名(去掉斜線): python 編碼名}。"""
    result = {}
    block = re.search(rb"/Font\s*(<<.*?>>)", page.resources, re.S)
    if not block:
        return result
    for m in re.finditer(rb"/(\w+)\s+(\d+)\s+0\s+R", block.group(1)):
        res_name = m.group(1).decode("latin-1")
        body = doc.get_object(int(m.group(2)))
        enc = re.search(rb"/Encoding\s*/([\w-]+)", body)
        if enc:
            result[res_name] = _encoding_from_name(enc.group(1).decode("latin-1"))
        else:
            base = re.search(rb"/BaseFont\s*/([^\s/>\]]+)", body)
            name = base.group(1).decode("latin-1") if base else ""
            result[res_name] = _encoding_from_basefont(name)
    return result


def decode_hex(hex_str: str, encoding: str) -> str:
    if len(hex_str) % 2:
        hex_str += "0"
    return bytes.fromhex(hex_str).decode(encoding, errors="replace")


# ----------------------------------------------------------------------
# 字寬估計（見 tools/extract/layout.py 模組說明的完整依據）
# ----------------------------------------------------------------------
#
# 依課本內嵌 CIDFont 實測：全形字元（假名、漢字、全形標點）走 /DW 預設
# 1000（1.0 倍字級）；半形字元（ASCII/Latin-1，課本用於行號標籤如「  1.」）
# 走 TT2 descendant font 的 /W 覆寫 500（0.5 倍字級）；空白不佔可視墨水，
# 估計寬度為 0。這三類寬度由實際檢視內嵌字型物件的 /DW、/W 得出，不是
# 憑空猜測的折衷係數。
#
# 這裡是唯一實作：`fragments.py`（TJ 陣列內字串的自然前進寬度、供下個
# 字距調整數字疊加）與 `layout.py`（欄位切分的右端估算）都呼叫這裡，
# 避免兩份重複、可能各自漂移的字寬邏輯。

def char_width(ch: str, size: float) -> float:
    """單一（已解碼）字元的估計前進寬度。"""
    if ch.isspace():
        return 0.0
    if ord(ch) < 0x100:
        return 0.5 * size
    return 1.0 * size


def text_width(text: str, size: float) -> float:
    """已解碼文字的估計前進寬度總和。"""
    return sum(char_width(c, size) for c in text)
