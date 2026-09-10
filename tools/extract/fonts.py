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
