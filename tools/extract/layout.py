"""版面分組：把帶座標的 Fragment 組成「行」，再把行切成「欄」。

`group_lines` 依 (page, y) 把 fragment 分群成 Line（同群 y 差距在 y_tol
內視為同一行），只納入正文字級（size >= 8.0）；振假名（4.8pt）由 ruby.py
另行處理。

## 閱讀順序重建在「字元」粒度，不是「fragment」粒度

課本會把日文詞彙插進中文說明的字元之間（反之亦然）——同一視覺列裡，後
畫的 fragment 座標可能落在先畫的 fragment 內部（例如中文釋義「打電話」
被拆成「打電」「〔」「話」「〕」四個 fragment，「〔」的 x 落在「打電」
內部）。若依 fragment 起點 x 排序、逐 fragment 串接文字，會把這類穿插
的 fragment 整批插在錯誤位置（見 Task 4 report 的「打電〔話〕」對比
「打〔電話〕」）。

`Line.text()`／`Line.cells()` 因此不是單純「展開成逐字元、全域依 x 排
序」，而是先在 fragment 層級判定「誰穿插進誰」，只有真正被穿插的
fragment 才會被拆進宿主內部；沒有被任何 fragment 穿插的 fragment，一律
維持自身文字**連續、不被拆開**的一個區塊。

### 插入 vs. 原子性：兩種必須分開處理的情形

穿插只有一種嚴謹定義：**外來 fragment 的錨點 x 嚴格大於某 fragment 的
錨點、且嚴格小於它的估計結束位置**（`fonts.char_width` 累加得出）。滿
足這個條件，外來 fragment 才會被拆進宿主字元之間；不滿足——包括「兩個
fragment 的錨點 x 完全相等」——兩個 fragment 都各自維持完整連續的一個
區塊，區塊之間的先後依內容流出現順序決定。

- **07 課「打電」與「〔」**（真正的穿插）：`〔` 的錨點 397.8 嚴格介於
  `打電` 的錨點 384.6 與估計結束位置 411.0 之間（`384.6 < 397.8 <
  411.0`）——`〔` 真的畫在 `打` 與 `電` 之間，必須拆進去，得到
  「打〔電話〕」。
- **14 課「ます」與「視」、01 課「だれ」列「是」/「“だれ”」**（曾經
  誤判為需要 tie-break 的打平，見下方「打平的真正根因」）：兩者錨點 x
  一度被算成完全相等，但這不是文件本身刻意讓兩段獨立文字共用同一個
  錨點——是座標算錯了。修好座標後兩者根本不再打平，單純依 x 排序即可
  正確還原成「視ます」「“どなた”是“だれ”」。原子性規則（下方）依然
  保留作為「兩個 fragment 錨點確實剛好相等」時的 fallback，只是這兩個
  案例已經不再需要靠它。

判定「誰是誰的宿主」：對每個 fragment，找出所有滿足「錨點嚴格落在自己
跨距內部」的其他 fragment 當作候選宿主；若有多個候選（巢狀穿插，目前
15 課資料並沒有實際案例，但演算法一般化處理），取跨距最短（最貼近）的
一個。沒有任何候選宿主的 fragment 是「頂層區塊」。

**頂層區塊之間**依 `(x, 內容流原始順序)` 排序——x 不同時直接依 x；x
相同時依 fragment 在內容流中出現的先後。修好下方的座標臭蟲後，全 15
課只剩 9 處 fragment 錨點打平（原本 55 處，見 Task 4 report 第三輪修正
的量化結果），逐一核對過都是「兩個各自獨立、真的沒有前後關係的
fragment 剛好共用同一個版面對齊點」（例如 05/10 課「1)」/「①」、多課
「→」箭頭跟後面例句對齊用的清單/表格排版慣例），不是座標算錯的症狀，
原子性 + 內容流順序排放皆已逐一核對正確。

**同一個宿主底下的插入字元，遇到宿主自身衍生字元 x 相同時，錨點優先於
衍生字元**：例如「打電」被拆開後，「電」是「打電」自身的衍生字元
（x 用 `char_width` 累加估計、不是文件錨點），插入的外來 fragment
「〔」剛好也落在同一個 x（397.8）——這是 `打電` 套用了 `1 Tc` 字元間距
（每個字元多前進 `1 Tc` 個未縮放文字空間單位），但 `Fragment` 不攜帶
`Tc` 資訊，`char_width` 估計因此系統性偏小，才讓「電」的估計位置跟
「〔」的真實錨點重合，插入的錨點字元排在衍生字元之前，得到正確的
「打〔電話〕」。

### 打平的真正根因：`char_width` 把空白算成 0 寬

14 課「ます」/「視」、01 課「だれ」列的打平，第三輪修正追查發現根因不
是版面設計、也不需要任何 tie-break 規則——是 `fonts.char_width` 先前
把空白字元的前進寬度算成 0（理由是「空白不佔可視墨水」，這個理由本身
沒錯，但這個函式同時被 `fragments.py` 拿去計算 TJ 陣列內文字顯示後畫筆
真正的前進量，PDF 渲染器不會因為某個字元「看不見」就不讓畫筆前進）。
用 `tools/render.swift` 算繪課本頁面、逐像素量測 14 課 p.8 與 01 課
p.1 的實際墨水位置後確認：把空白前進寬度改成跟其他半形字元一致的
0.5 倍字級（全形空白 U+3000 併入一般全形分支的 1.0 倍字級）後，兩個
案例的座標都不再打平，而且都跟算繪出來的真實版面完全吻合，見
`fonts.char_width` 的說明與 Task 4 report 第三輪修正。

**這個修正推翻了前兩輪對這兩個案例的結論**：第一輪（開頭標點啟發式，
只有 01 課一個案例佐證）判 01 課「“どなた”是“だれ”」——這個答案剛好
是對的，但推論方式（n=1 啟發式）本身站不住腳；第二輪（原子性＋內容流
順序）判 01 課「“どなた”“だれ”是」、14 課「ます視」——兩個答案都是
錯的，因為那兩個案例根本不是「原子性」情形，是座標算錯造成的假打平。
真正的正確答案（用算繪頁面核對）是「視ます」「“どなた”是“だれ”」，
現在座標修好後，不靠任何 tie-break、單純依 x 排序就會自然得到。

**已知殘留限制**：巢狀穿插（一個被插入的 fragment 自己又被別的 fragment
插入）目前 15 課資料沒有實際案例，演算法雖已一般化處理，但缺乏實測驗
證。剩下 9 處 fragment 錨點打平雖然都已逐一核對為「原子性、非座標臭蟲」
（見上方），樣本仍然不大，若未來課別出現更多、方向跟目前不一致的打平
案例，這裡假設的「內容流順序＝閱讀順序」可能需要重新檢視——這條規則
目前是用「05/10 課清單標記」「多課『→』例句」等獨立案例交叉驗證出來
的，樣本數比第二輪的 n=1 好得多，但仍不是從 PDF 規格直接推導出的定理。
"""
import unicodedata
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from tools.extract.fonts import char_width
from tools.extract.fragments import Fragment

_MIN_BODY_SIZE = 8.0


@dataclass
class Cell:
    x: float
    text: str
    frags: List[Fragment]      # 對這個欄位有貢獻（哪怕只貢獻部分字元）的來源 fragment，依出現順序、不重複


@dataclass
class Line:
    y: float
    page: int
    frags: List[Fragment]          # 已依 fragment 起點 x 排序；實際閱讀順序見 text()/cells()

    def text(self) -> str:
        return "".join(ch for ch, _x, _f in _line_chars(self.frags))

    def cells(self, min_gap: float = 10.0) -> List[Cell]:
        chars = _line_chars(self.frags)
        out: List[Cell] = []
        cur_chars: List[Tuple[str, float]] = []
        cur_frags: List[Fragment] = []
        prev_right = None
        for ch, x, f in chars:
            if prev_right is not None and x - prev_right > min_gap and cur_chars:
                out.append(_make_cell(cur_chars, cur_frags))
                cur_chars = []
                cur_frags = []
            cur_chars.append((ch, x))
            if not cur_frags or cur_frags[-1] is not f:
                cur_frags.append(f)
            prev_right = x + _visual_extent(ch, f.size)
        if cur_chars:
            out.append(_make_cell(cur_chars, cur_frags))
        return out


def _make_cell(cur_chars: List[Tuple[str, float]], cur_frags: List[Fragment]) -> Cell:
    return Cell(
        x=cur_chars[0][1],
        text="".join(ch for ch, _x in cur_chars),
        frags=list(cur_frags),
    )


def _visual_extent(ch: str, size: float) -> float:
    """`cells()` 專用：估計單一字元對「這裡看起來延伸到哪裡」的貢獻，
    跟 `fonts.char_width`（PDF 真實前進寬度，供座標推進用）是兩個不同
    的量，不能混用。

    真實前進寬度是「筆尖移動了多遠」，不是「墨水畫到哪裡」——這在任何
    字元都成立，但對空白與標點特別明顯：07 課單字表行號標籤「   1.」
    的句點「.」，前進寬度是半形的 0.5 倍字級（6.6pt，供下一個內容正確
    定位），但用課本實際頁面算繪後逐像素量測，句點本身的墨水只佔約
    1pt，其餘 5.6pt 是空白（見 Task 4 report 第三輪修正）。`cells()`
    只在乎「這個欄位的可見內容看起來延伸到哪裡，好跟下一個字比較有沒有
    明顯空隙」，因此空白與標點（Unicode 類別 Z*／P*）一律視為不貢獻
    可見延伸；字母、數字、假名、漢字等「有實體筆畫」的字元則沿用真實
    前進寬度（那些字元的墨水普遍接近甚至填滿自己的前進寬度，兩者當
    估計值用差異不大）。

    這個函式只用在 `cells()` 的間距判定；`_fragment_chars`／
    `_find_host`／`_fragment_end` 需要的是「文件真實座標會落在哪裡」
    （用來判斷字元錨點、fragment 跨距是否真的穿插），必須用
    `fonts.char_width` 的真實前進寬度，不能套用這裡的視覺裁切。
    """
    category = unicodedata.category(ch)
    if category[0] in ("Z", "P"):
        return 0.0
    return char_width(ch, size)


def _fragment_chars(f: Fragment) -> List[Tuple[str, float, bool]]:
    """把一個 fragment 展開成逐字元的 (字元, x, 是否為 fragment 起點字元)。

    第一個字元的 x 固定等於 `f.x`（文件本身的錨點）；後續字元的 x 是依
    `fonts.char_width` 累加的估計值（見模組說明的殘留限制）。
    """
    out: List[Tuple[str, float, bool]] = []
    x = f.x
    for i, ch in enumerate(f.text):
        out.append((ch, x, i == 0))
        x += char_width(ch, f.size)
    return out


def _fragment_end(f: Fragment) -> float:
    """fragment 的估計結束位置：錨點 + 全部字元的估計前進寬度總和。"""
    x = f.x
    for ch in f.text:
        x += char_width(ch, f.size)
    return x


def _find_host(f: Fragment, frags: List[Fragment]) -> Optional[Fragment]:
    """回傳 f 的宿主：f 的錨點嚴格落在某個 fragment 的 [起點, 結束) 跨距
    內部（見模組說明「插入 vs. 原子性」）。錨點 x 完全相等**不算**——那是
    原子性情形，不是穿插，回傳 None（f 是頂層區塊）。

    若有多個候選宿主（巢狀穿插；目前 15 課資料沒有實際案例，這裡一併
    處理以求一般化），取跨距最短（最貼近 f 的）一個。
    """
    candidates = [h for h in frags if h is not f and h.x < f.x < _fragment_end(h)]
    if not candidates:
        return None
    return min(candidates, key=lambda h: _fragment_end(h) - h.x)


def _line_chars(frags: List[Fragment]) -> List[Tuple[str, float, Fragment]]:
    """把一行內所有 fragment 依「插入 vs. 原子性」規則展開、重組成正確
    閱讀順序（見模組說明）。

    回傳 (字元, x, 來源 fragment) 序列——這是 `Line.text()` 與
    `Line.cells()` 唯一的真實來源，兩者必須一致。
    """
    order = {id(f): i for i, f in enumerate(frags)}
    host_of = {id(f): _find_host(f, frags) for f in frags}

    children_of: Dict[int, List[Fragment]] = {}
    for f in frags:
        host = host_of[id(f)]
        if host is not None:
            children_of.setdefault(id(host), []).append(f)

    def render(f: Fragment) -> List[Tuple[str, float, Fragment]]:
        """遞迴展開 f 自身的字元，把插入它的子 fragment（已各自遞迴展開
        成一個連續區塊）拼進正確的字元縫隙。"""
        own_chars = _fragment_chars(f)
        kids = sorted(
            children_of.get(id(f), []),
            key=lambda c: (c.x, order[id(c)]),
        )
        out: List[Tuple[str, float, Fragment]] = []
        ki = 0
        for i, (ch, x, _is_initial) in enumerate(own_chars):
            # 插入所有應該排在「目前這個自身字元」之前的子區塊：子區塊
            # 錨點嚴格小於目前字元的 x；或剛好相等時——目前字元必須是
            # f 自身的衍生字元（i > 0，第 0 個是 f 自己的錨點，子 fragment
            # 依 _find_host 的定義不可能與它相等）——錨點優先於衍生字元。
            while ki < len(kids) and (kids[ki].x < x or (kids[ki].x == x and i > 0)):
                out.extend(render(kids[ki]))
                ki += 1
            out.append((ch, x, f))
        while ki < len(kids):
            out.extend(render(kids[ki]))
            ki += 1
        return out

    # 頂層區塊（沒有宿主的 fragment）依 (x, 內容流原始順序) 排序、各自
    # 保持完整連續——這正是「原子性」規則的體現：x 相同時不穿插，只看
    # 內容流順序。
    top_level = [f for f in frags if host_of[id(f)] is None]
    top_level.sort(key=lambda f: (f.x, order[id(f)]))

    result: List[Tuple[str, float, Fragment]] = []
    for f in top_level:
        result.extend(render(f))
    return result


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
