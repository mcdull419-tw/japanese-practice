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
序」（那個做法在第一輪修正時，把 14 課「Ⅰ類動詞ます形」誤重建成
「Ⅰ類動詞ま視す形」——見下方「插入 vs. 原子性」），而是先在 fragment
層級判定「誰穿插進誰」，只有真正被穿插的 fragment 才會被拆進宿主內部；
沒有被任何 fragment 穿插的 fragment，一律維持自身文字**連續、不被拆
開**的一個區塊。

### 插入 vs. 原子性：兩種必須分開處理的情形

穿插只有一種嚴謹定義：**外來 fragment 的錨點 x 嚴格大於某 fragment 的
錨點、且嚴格小於它的估計結束位置**（`fonts.char_width` 累加得出）。滿
足這個條件，外來 fragment 才會被拆進宿主字元之間；不滿足——包括「兩個
fragment 的錨點 x 完全相等」——兩個 fragment 都各自維持完整連續的一個
區塊，區塊之間的先後依內容流出現順序決定。

兩個實測案例正好落在條件的兩側：

- **07 課「打電」與「〔」**：`〔` 的錨點 397.8 嚴格介於 `打電` 的錨點
  384.6 與估計結束位置 411.0 之間（`384.6 < 397.8 < 411.0`）——`〔` 真
  的畫在 `打` 與 `電` 之間，必須拆進去，得到「打〔電話〕」。
- **14 課「ます」與「視」**：兩者錨點 x 完全相等（150.6，不是「嚴格
  介於」，是「相等」）。這不是穿插——是兩段獨立文字剛好從同一個 x 開
  始各自畫自己的內容（一段是動詞變化說明的日文範例「ます」，另一段是
  中文說明「視……形」），彼此在視覺上互相靠齊，不代表其中一段的字元
  要被拆進另一段中間。第一輪修正把「錨點相等」也當成一種需要排序
  tie-break 的穿插來處理（見下方「已修正的錯誤」），結果把「視」硬插
  進「ます」與「す」中間，重建成「ま視す」——這是一個真實的回歸，已用
  第 14 課這一列的個案測試鎖住。

判定「誰是誰的宿主」：對每個 fragment，找出所有滿足「錨點嚴格落在自己
跨距內部」的其他 fragment 當作候選宿主；若有多個候選（巢狀穿插，目前
15 課資料並沒有實際案例，但演算法一般化處理），取跨距最短（最貼近）的
一個。沒有任何候選宿主的 fragment 是「頂層區塊」。

**頂層區塊之間**（包含前述的原子性情形）依 `(x, 內容流原始順序)` 排
序——x 不同時直接依 x；x 相同時依 fragment 在內容流中出現的先後。

**同一個宿主底下的插入字元，遇到宿主自身衍生字元 x 相同時，錨點優先於
衍生字元**：例如「打電」被拆開後，「電」是「打電」自身的衍生字元
（x 用 `char_width` 累加估計、不是文件錨點），若插入的外來 fragment
剛好也落在同一個 x（如「〔」與「電」都是 397.8——這是 `打電` 套用了
`1 Tc` 字元間距、但 `Fragment` 不攜帶 `Tc` 資訊，`char_width` 估計因此
系統性偏小才造成的巧合，不是文件本身的巧合，見下方殘留限制），插入的
錨點字元排在衍生字元之前——這是第一輪修正裡唯一保留下來的 tier 規則。

### 已修正的錯誤：`n=1` 的「開頭標點」啟發式不是通用規則

第一輪修正曾經用「開頭標點在錨點對錨點打平時排後面」這條啟發式處理
01 課「だれ」列的打平（見 Task 4 report）。複審抽樣檢視同類打平案例時
發現，同一條規則會把 14 課「ます」/「視」、05/10 課「1)」/「①」這些
**不該穿插**的錨點對錨點打平也判成需要排序，進而把外來 fragment 的字
元硬插進另一個 fragment 中間，造成真實的輸出損毀（見上方）。原本這裡
寫「進場順序不帶語意」——這句話已被證偽：對錨點對錨點打平而言，「保持
兩個 fragment 各自完整連續、依內容流順序排放」才是唯一有根據的規則；
啟發式挑一種標點類別優先，是在沒有第二個案例佐證的情況下硬套的模式，
套用到不同的打平案例上就會出錯。

01 課「だれ」列的打平（中文「是」與日文引號詞「“だれ”」的開引號，都
是錨點、x 完全相等）在新規則下屬於「原子性」情形：兩個 fragment 各自
保持完整連續，依內容流順序排放。實測內容流順序是「“だれ”」（與
「“どなた”」同一個 TT2 TJ 陣列，先畫）先於「是」（後面另一個 BT 區塊
的 TT4 TJ 陣列，後畫）——所以「“だれ”」整塊排在「是」整塊之前，得到
「“どなた”“だれ”是」，**跟第一輪修正的結論不同**（第一輪用開頭標點
啟發式排出「“どなた”是“だれ”」）。第一輪那個結論當時只靠中文語法直
覺佐證（「Ａ是Ｂ的禮貌形」句型），沒有拿內容流順序這個更直接的證據
核對過；14/05/10 課這三個新案例的內容流順序，皆與各自已知正確的讀法
一致（見上方），三個獨立案例都指向同一條規則，比起單一案例的語法直覺
更可信，因此這裡採用新規則重新推出的結果，判定第一輪的語法直覺推論
很可能是錯的。

**已知殘留限制**：巢狀穿插（一個被插入的 fragment 自己又被別的 fragment
插入）目前 15 課資料沒有實際案例，演算法雖已一般化處理，但缺乏實測驗
證。真正能一勞永逸消除「打電/電 與 〔 之間那類巧合打平」的解法，是讓
`Fragment` 攜帶 `Tc`，讓衍生字元的估計位置不再系統性偏小；但這對「ます
/視」這類兩者皆為真錨點的打平沒有幫助——原子性規則本來就是為這類打平
設計的，不是 `Tc` 能解的問題（詳見 Task 4 report 第二輪修正的判斷）。
"""
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
            prev_right = x + char_width(ch, f.size)
        if cur_chars:
            out.append(_make_cell(cur_chars, cur_frags))
        return out


def _make_cell(cur_chars: List[Tuple[str, float]], cur_frags: List[Fragment]) -> Cell:
    return Cell(
        x=cur_chars[0][1],
        text="".join(ch for ch, _x in cur_chars),
        frags=list(cur_frags),
    )


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
