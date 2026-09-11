"""振假名（漢字上方的小字假名）配對。

`pair_ruby(all_frags, line)` 把一行正文裡的每個漢字（CJK 表意文字）跟畫在
它正上方的振假名配對。振假名字級（4.8pt）小於 `layout.group_lines` 的
納入門檻（8.0pt），所以不在 `line.frags` 裡——必須從 `all_frags`（未經
字級篩選的完整片段清單）另行找出。

## 常數是從目前（已修正）座標重新量測的，不是照抄簡報數字

簡報草稿裡的 `RUBY_X_MAX_DIST = 11.0` 是從一個座標計算有嚴重錯誤的原型量
出來的（詳見 Task 3/4 report：TJ 顯示文字未加自然前進寬度、Tm/Tlm 誤合
併、空白字元被當成 0 寬）。那三輪修正讓 x 座標整批改變，y 座標則大致不
受影響。這裡的常數是在座標修好後、用 07~15 課全部資料重新量測得出：

- **`RUBY_Y_OFFSET = 12.0`、`RUBY_Y_TOL = 2.5`**：對全 15 課「每個 CJK
  字元 × 同頁每個振假名字元」做 y 差值直方圖，主峰精準落在 12.0（正文
  y + 12.0 = 振假名 y），次要眾數落在 11.1、11.46（不同正文字級 10.44pt
  /12.6pt 的行）。三個眾數都落在 `12.0 ± 2.5` 內，簡報這兩個數字驗證後
  維持不變。
- **`RUBY_X_MAX_DIST = 12.0`**（簡報原值 11.0，量測後上修）：把候選限制
  在「y 差值符合上述門檻」後，逐一核對「x 差值」分布——真實配對（用
  `tools/render.swift` 算繪比對，例如 04.pdf p.7「6時（に）起きます」的
  時→じ、起→お）最大量到 11.4pt；下一個真實叢集要到 18.8pt（07.pdf p.8
  「語～で　何ですか」的 語→ご，同樣算繪核對為真），中間 11.4~18.8pt 之
  間只有雜訊（例如「動詞」的「動」量到隔壁「回」的假名「かい」偏移
  12.6pt，經算繪確認「動詞」本身沒有振假名，純屬巧合鄰近，不是真配
  對）。11.0 會誤刪 11.4pt 的真配對（時→じ、起→お），因此上修到 12.0：
  緊貼在真實叢集上緣（11.4），同時仍排除下一群雜訊（12.6 起）。18.8pt
  那一組真配對（單一個案，07 課僅一例）不在此門檻內，會被算成「找不到
  配對」而非「配對錯誤」——不影響配對正確性，只小幅拉低配對率，跟簡報
  自陳的「已知邊緣案例」性質相同。

## 配對單位是「振假名 fragment 內的空白分隔區段」，不是逐字元最近點

簡報演算法描述（步驟 2）讀起來像是「每個振假名字元」各自獨立找最近的漢
字。實作後發現這個逐字元最近點策略在**同一個振假名 fragment 涵蓋多個漢
字、且各漢字讀音長度不同**時會配錯——例如「太郎君」的振假名是單一
fragment `'  た  ろう  くん'`（三個空白分隔區段：「た」對應「太」、
「ろう」對應「郎」、「くん」對應「君」）。「太」在 x=273.0，「郎」在
x=286.2（僅相隔 13.2pt，一個全形字寬）；但「た」這個假名字元本身因為只
有一個字、置中後的實際 x 落在 284.4——離「郎」只有 1.8pt，離它真正對應
的「太」反而有 11.4pt。若對每個假名字元獨立找「最近」的漢字，「た」會被
誤配給「郎」，導致合併後的 base 變成「郎君」（漏掉「太」）、kana 變成
「たろうく」（漏掉「ん」）——字串看起來像是「合理的部分結果」，不會讓
任何弱斷言測試失敗，但讀音已經錯位。

修正方式：**先依 fragment 內部空白把文字切成區段（每區段對應一個漢
字），再以「整個 fragment 的原始錨點」（`Fragment.x`，也就是 fragment
文字第一個字元——通常是置中用的前導空白——所在的座標，尚未依字元前進量
推進）去找配對的起始漢字，而不是用區段內已展開的假名字元座標**。同一份
「太郎君」實測：fragment 錨點 x=279.6，離「太」（273.0）只有 6.6pt，離
「郎」（286.2）有 13.2pt——用 fragment 錨點判斷起點，方向就對了。找到起
始漢字後，要求從那裡開始、在該行讀出順序中連續 N 個字元都是 CJK 表意文
字（N = 區段數）——這一步用來排除「起點候選剛好距離相近但接下來湊不出
足夠連續漢字」的假陽性（例如「図書館」的振假名 `'  と  しょ  かん'`錨點
到「図」與「書」的 x 差距剛好相等，只有「図」後面接得出連續 3 個漢字
「図書館」，「書」後面只有「書館」2 個——用這個結構性條件而非距離破
除平手）。

同一個 fragment 找不到滿足門檻與連續漢字數的起點時，整個 fragment 的假
名視為配不到（不落回逐字元最近點那條會配錯的路徑）——只降低配對率，不
產生錯誤配對，符合簡報「測試門檻設 98% 而非 100%」的容忍範圍。
"""
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from tools.extract.fonts import char_width
from tools.extract.fragments import Fragment
from tools.extract.layout import Line, _line_chars

RUBY_MAX_SIZE = 6.0      # 振假名字級 4.8pt；正文 10pt 以上
RUBY_Y_OFFSET = 12.0     # 振假名 y 比漢字高 12.0pt（PDF 座標 y 軸向上 = 視覺在上方）
RUBY_Y_TOL = 2.5
RUBY_X_MAX_DIST = 12.0


@dataclass
class RubyPair:
    base: str      # 漢字
    kana: str      # 讀音
    at: int        # base 在該行文字中的字元位置


def _is_cjk_ideograph(ch: str) -> bool:
    try:
        name = unicodedata.name(ch)
    except ValueError:
        return False
    return "CJK UNIFIED" in name or "CJK COMPATIBILITY" in name


def _ruby_groups(frags: List[Fragment]) -> List[Tuple[float, float, List[str]]]:
    """把每個振假名 fragment 依內部空白切成區段，回傳
    `(錨點x, 錨點y, [區段文字, ...])` 的清單——一個 fragment 一組，錨點是
    `Fragment.x`／`Fragment.y` 本身（見模組說明：不能用區段內展開後的假
    名字元座標，短區段會系統性偏向下一個漢字）。"""
    groups = []
    for f in frags:
        x = f.x
        segments: List[str] = []
        current = ""
        for ch in f.text:
            if ch.strip():
                current += ch
            elif current:
                segments.append(current)
                current = ""
            x += char_width(ch, f.size)
        if current:
            segments.append(current)
        if segments:
            groups.append((f.x, f.y, segments))
    return groups


_MAX_NORMAL_GAP_RATIO = 2.0   # 見 `_has_normal_spacing` 說明


def _has_normal_spacing(reading: List[Tuple[str, float, Fragment]], start: int, n: int) -> bool:
    """檢查 `reading[start : start+n]` 這 n 個字元彼此的 x 間距都「正
    常」（同一個詞內相鄰字元的間距，約等於字級），排除橫跨欄位/儲存格邊
    界的情形。

    07 課單字表常見「日文欄＋中文欄同一列、中間沒有任何分隔字元」的排
    版（例如「旅行」headword 緊接著右欄解說「旅行（～を...）」、
    「お土産」緊接著右欄「土產，記念品」）——`Line.text()`／`_line_chars`
    純粹依 x 排序＋內容流順序重建閱讀順序，兩欄之間沒有分隔符，光看字
    元是否相鄰無法分辨換欄。改看幾何 x 間距：同一個詞內相鄰漢字的間距
    等於字級（實測 10.4~13.2pt）；換欄的間距實測高達 332.4~345.6pt，兩
    者差距懸殊，用「正文字級的 2 倍」當上限就能可靠分開。"""
    for k in range(n - 1):
        _prev_ch, prev_x, prev_f = reading[start + k]
        _next_ch, next_x, _next_f = reading[start + k + 1]
        if next_x - prev_x > _MAX_NORMAL_GAP_RATIO * prev_f.size:
            return False
    return True


def _find_start(
    reading: List[Tuple[str, float, Fragment]],
    cjk_indices: List[int],
    anchor_x: float,
    anchor_y: float,
    n_segments: int,
) -> Optional[int]:
    """找出這組振假名區段的起始漢字索引：候選須通過 y/x 門檻，且從候選
    起、讀出順序上連續 `n_segments` 個字元都必須是 CJK 表意文字（見模組
    說明的「連續漢字數」平手判定）。多個候選時取離 `anchor_x` 最近的。"""
    cjk_set = set(cjk_indices)
    best_i: Optional[int] = None
    best_dist: Optional[float] = None
    for i in cjk_indices:
        _ch, bx, bf = reading[i]
        if abs(anchor_y - (bf.y + RUBY_Y_OFFSET)) > RUBY_Y_TOL:
            continue
        xdist = abs(anchor_x - bx)
        if xdist > RUBY_X_MAX_DIST:
            continue
        if not all((i + k) in cjk_set and i + k < len(reading) for k in range(n_segments)):
            continue
        if not _has_normal_spacing(reading, i, n_segments):
            continue
        if best_dist is None or xdist < best_dist:
            best_dist = xdist
            best_i = i
    return best_i


_JUKUJIKUN_EXTEND_CAP = 2   # 見模組說明「未分段複合詞讀音」，避免無界擴張


def pair_ruby(all_frags: List[Fragment], line: Line) -> List[RubyPair]:
    ruby_groups = _ruby_groups([
        f for f in all_frags
        if f.size <= RUBY_MAX_SIZE and f.page == line.page and f.text.strip()
    ])

    # reading-order 字元序列，索引跟 line.text() 逐字元對應（見
    # layout.Line.text() 的實作——兩者共用同一個 `_line_chars` 來源）。
    reading = _line_chars(line.frags)
    cjk_indices = [i for i, (ch, _x, _f) in enumerate(reading) if _is_cjk_ideograph(ch)]
    cjk_index_set = set(cjk_indices)

    kana_by_index: Dict[int, str] = {}
    for anchor_x, anchor_y, segments in ruby_groups:
        start = _find_start(reading, cjk_indices, anchor_x, anchor_y, len(segments))
        if start is None:
            continue
        for k, seg_text in enumerate(segments):
            idx = start + k
            if idx not in kana_by_index:
                kana_by_index[idx] = seg_text

    # 未分段複合詞讀音（見模組說明）：把緊接在一個已配對區塊後面、完全
    # 沒被任何振假名群組配到的漢字併入該區塊（假名留空——讀音字元已經
    # 完整包含在前面的區段裡，只是區段數少於實際涵蓋的漢字數）。最多往
    # 後併 `_JUKUJIKUN_EXTEND_CAP` 個字，避免吃進真正獨立、沒有振假名的
    # 漢字。
    for block_end in [end for _start, end in _merge_blocks(sorted(kana_by_index))]:
        nxt = block_end + 1
        extended = 0
        while nxt in cjk_index_set and nxt not in kana_by_index and extended < _JUKUJIKUN_EXTEND_CAP:
            # 只在「字距正常」（同一個詞的相鄰漢字，不是換欄）時才擴張——
            # 見 `_has_normal_spacing` 說明（07 課單字表日文欄／中文欄同
            # 一列、彼此沒有文字間隔的排版，例如「旅行」headword 緊接著
            # 右欄解說文字重複出現的「旅行（～を...）」）。
            if not _has_normal_spacing(reading, nxt - 1, 2):
                break
            kana_by_index[nxt] = ""
            nxt += 1
            extended += 1

    matched_indices = sorted(kana_by_index)

    pairs: List[RubyPair] = []
    text = line.text()
    for start, end in _merge_blocks(matched_indices):
        kana = "".join(kana_by_index[idx] for idx in range(start, end + 1))
        pairs.append(RubyPair(base=text[start:end + 1], kana=kana, at=start))

    return pairs


def _merge_blocks(sorted_indices: List[int]) -> List[Tuple[int, int]]:
    """把已排序、遞增的索引清單切成「連續執行」的 (start, end) 區間清單。"""
    blocks = []
    i = 0
    while i < len(sorted_indices):
        start = sorted_indices[i]
        j = i
        while j + 1 < len(sorted_indices) and sorted_indices[j + 1] == sorted_indices[j] + 1:
            j += 1
        blocks.append((start, sorted_indices[j]))
        i = j + 1
    return blocks
