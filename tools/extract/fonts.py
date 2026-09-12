import re
from typing import Dict

from tools.extract.pdfobj import PDF_NAME_TOKEN, decode_pdf_name

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
    """回傳 {字型資源名(去掉斜線): python 編碼名}。

    列舉 `/Font` 資源字典 key 用 `pdfobj.PDF_NAME_TOKEN`（依規格定義的
    合法 PDF 名稱字元，含底線、`+`、`-`、`.`、`#xx` 逃脫序列），不是只
    認英數字加底線的 `\\w+`——這裡跟 `fragments.py` 解析 `Tf` 運算子字
    型名用同一個字元類別、同一個 `decode_pdf_name` 還原 `#xx` 逃脫序
    列，兩邊對同一個字型資源名稱保證得到完全相同的字串，`Tf` 設定的
    `state.font` 才查得到這裡建出來的編碼表（見 `fragments.py` 模組說
    明「字型名解析失敗必須大聲失敗」；Task 6 複審發現的真實案例是
    13.pdf 的 `/C2_0`、`/C2_1`——這兩個字型名本身用 `\\w+` 就已經能完
    整比對到，這裡改用更寬的字元類別是為了避免兩邊字元類別不一致，未
    來換成別的合法字元時再次出現同一種 key 對不上的臭蟲）。"""
    result = {}
    block = re.search(rb"/Font\s*(<<.*?>>)", page.resources, re.S)
    if not block:
        return result
    for m in re.finditer(rb"/(" + PDF_NAME_TOKEN + rb")\s+(\d+)\s+0\s+R", block.group(1)):
        res_name = decode_pdf_name(m.group(1)).decode("latin-1")
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
# 依課本內嵌 CIDFont 實測：全形字元（假名、漢字、全形標點、全形空白
# U+3000）走 /DW 預設 1000（1.0 倍字級）；半形字元（ASCII/Latin-1，含
# 半形空白 0x20）走 TT2 descendant font 的 /W 覆寫 500（0.5 倍字級）。
# 這兩類寬度由實際檢視內嵌字型物件的 /DW、/W 得出，不是憑空猜測的折衷
# 係數。
#
# 這裡是唯一實作：`fragments.py`（TJ 陣列內字串的自然前進寬度，用來推
# 進畫筆、決定下一個字距調整數字/字串疊加的基準）與 `layout.py`（欄位
# 切分的右端估算、fragment 插入判定）都呼叫這裡，避免兩份重複、可能各
# 自漂移的字寬邏輯。
#
# **半形空白不能特殊處理成 0**：Task 4 第三輪修正查出，先前這裡把空白
# 字元估計寬度寫死為 0（理由是「空白不佔可視墨水」），這對 layout.py
# 自己的欄位右端估算或許還算合理的簡化，但 `fragments.py` 拿同一個函式
# 計算 TJ 陣列裡文字顯示後畫筆真正的前進量——PDF 渲染器並不會因為某個
# 字元「看不見」就不讓畫筆前進，半形空白跟其他半形字元一樣，前進量是
# 字型宣告的 500/1000（0.5 倍字級），不是 0。把空白視為 0 寬，會讓
# `fragments.py` 算出的座標系統性少走「空白數 × 0.5 倍字級」，14 課
# p.8「ます」被少算了整整一個字寬（兩個半形空白），因此跟後面完全獨立
# 算出的「視」的錨點意外重合，兩個各自獨立的 fragment 因此被誤判成
# 「錨點剛好相等」；01 課「だれ」列的「是」／「“だれ”」平手也是同一
# 根因的另一種表現形式（見 Task 4 report 第三輪修正）。改成套用跟其他
# 半形字元一致的 0.5 倍字級（全形空白 U+3000 一樣併入一般全形分支的
# 1.0 倍字級，不再需要特殊判斷）後，這兩個案例的座標不再打平，全 15 課
# 的 fragment 錨點打平數從 55 降到 9（量化方法與逐一核對見 Task 4
# report 第三輪修正）。

def char_width(ch: str, size: float) -> float:
    """單一（已解碼）字元的估計前進寬度（依 CIDFont /DW、/W 度量；空白
    字元套用跟同類全形/半形字元一致的寬度，不特殊處理成 0——見上方
    模組層級說明）。"""
    if ord(ch) < 0x100:
        return 0.5 * size
    return 1.0 * size


def text_width(text: str, size: float) -> float:
    """已解碼文字的估計前進寬度總和。"""
    return sum(char_width(c, size) for c in text)
