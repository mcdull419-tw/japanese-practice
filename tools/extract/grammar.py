"""文法解說解析：把 `文法` 區段的 `Line` 序列切成一組文法點，每點含標題、
中文說明（`body_zh`）與日中對照例句（`examples`）。

## 原型的缺陷：只取中文字型，日文整批消失

任務簡報記錄的原型輸出：

```
title: '１名詞（工具／手段）動詞'                    ← 「で」不見了
body:  '助詞「」表示手段、方法。用筷子吃。用日語寫報告。'  ← 引號內日文與整句日文例句全失
```

根因是原型只收集中文字型（gb18030）的 fragment，日文字型（cp932）的
fragment 整批被丟棄。這個缺陷已經在上游 `fragments.py`（Task 7 的 Tc
拆分修正）修好，本模組的責任是**不要在解析階段重新弄丟日文**——不對
fragment 依字型過濾，日文與中文 fragment 一律保留，只依座標（x 排序、
縮排層級）決定歸局。

## 標題／內文：直接依 fragment 既有的 x 序串接，不套用 `Line.text()`

`layout.Line._build_line` 已把同一行的 fragment 依 x 由小到大排序
（`line.frags`）。日文夾在中文引號中間（例如「助詞「で」表示手段」）
在這批資料裡，都是**三個各自獨立、彼此不重疊、依 x 遞增排列**的
fragment（「助詞「」」「で」「」表示...」），單純依 `line.frags` 既有
順序串接文字（`_naive_concat`）就能正確還原，不需要 `Line.text()` 的
字元級「插入 vs. 原子性」判定。

**這裡刻意不用 `Line.text()`／`Line.cells()`**：07.pdf 第 5 點標題
「もう〜ました　動詞」的原始 fragment 是 `'もう ました'`（cp932，錨點
x=67.2）＋`'動'`／`'詞'`（gb18030，錨點 x=100.2／110.7）。`char_width`
估計「もう ました」的估計跨距達到 x≈131（半形空白估計成 0.5 倍字級，
但這裡的實際字距比估計值窄），導致 `layout.py` 的插入判定誤判「動」
的錨點（100.2）落在「もう ました」跨距內部，把它插入字串中間，錯誤
產出「もう ま動詞した」——這正是 `patterns.py`「練習Ｂ 絕對不能用
`Line.text()`」教訓的又一個真實案例，同一根因（`char_width` 對字元
間距的估計與實際印刷有落差）在不同區段各自觸發一次。改用
`_naive_concat`（依既有 fragment 順序直接串接，不做任何字元級重排）
後，這一行正確還原成「もう ました動詞」（無重排問題，見下方驗證）。

全 15 課「精確等於某個區段名」以外的 `文法` 內容，均已逐課核對過
`_naive_concat` 與 `Line.text()` 的輸出差異：僅此一處（07.pdf 第 5
點標題）不同，其餘完全一致——`_naive_concat` 在此語料下是安全的選
擇，也避免了 `Line.text()` 的插入誤判風險。

## 版面縮排層級：辨識文法點的四種角色

以行首縮排 x 座標區分，全 15 課逐課驗證過這個層級固定成立（詳見
`task-10-report.md`）：

1. **標題**：行首全形或半形數字＋句點（`１.`／`2.`），x 最小
   （≈25.2~25.8pt）。
2. **內文說明**：句子直接開頭（可能夾雜「1)」「2)」子編號），x 次小
   （每課固定，常見 39.6／51.6／53.4pt）。
3. **例句**：行首圈號數字（①~⑳），x 再大一級（常見 51.6~67.2pt，依
   課別不同，但同一課內固定）。
4. **例句延伸行**（問答對的回答、或例句翻譯另起一行）：比同一則例句
   自己的圈號 x **嚴格更大**（常見比例句 x 多 13.8~14pt）。

判定「延伸行」不能用固定常數（不同課別的例句縮排本身就不同），必須
比較**這一則例句自己的圈號 x**——`_ItemBuilder` 對每個文法點各自記錄
目前作用中例句的圈號 x，之後任何非圈號、非標題的行，x 若嚴格大於這
個值，視為延伸；否則（不大於，含相等——例如內文換行後意外對齊到跟
例句同一個縮排）一律視為內文，緊接著關閉目前作用中的例句。

這個縮排層級全 15 課逐課掃描過（`xbuckets.py`／`xbuckets2.py` 探索
腳本），少數「內文」換行後意外對齊到跟例句同一個 x（例如換行後的句
子剛好也是 67.2pt）都正確落在「不大於」而非「大於」的分支，不會被誤
判成延伸行；詳細案例見 `task-10-report.md`。

## 日中分界：例句／延伸行內「這一行本身最大的座標落差」

同一行日文例句＋中文翻譯相連時（`① はしで  食べます。用筷子吃。`），
兩者之間**一定**存在這一行內部最大的 fragment 間落差——不論這個落
差本身的絕對值多大。全 15 課逐課量測發現這個落差沒有一個放諸四海皆準
的絕對門檻：07.pdf 例句翻譯多半留在固定欄位（x≈357），日文句子短時
落差高達 154.2pt；但 12.pdf 例句⑤「この車はあの車より大きいです。」
因為日文句子本身已經印到接近翻譯欄，落差只剩 9.0pt——比同一課「純日
文、翻譯根本不在這一行」的例句（⑳，最大內部落差 9.6pt）還要小！這證
明**任何固定的絕對或相對門檻都無法同時處理這兩種情形**（詳見
`task-10-report.md` 的量測數據）。

真正可靠的規則不是「門檻」而是**驗證**：取這一行內部落差最大的切點試
切一次，检查切出來的右半段——如果右半段**非空白且不含任何假名**（用
`sentences.py` 相同的假名判準 `_KANA_RE`），就接受這個切點（右半段是
中文翻譯，左半段是日文本體）；否則（右半段仍含假名，代表這個「最大
落差」只是恰好出現在日文句子內部、翻譯根本不在這一行，例如 07.pdf
「…「ありがとう」です。是ありがとう。」的翻譯本身又引述了一次日文
「ありがとう」，導致「です。」→「是」這個真正的分界不是行內數值最
大的落差候選——不，這裡刻意用**整行**最大落差而非「第一個字型轉換
點」，逐一核對後最大落差確實還是落在「です。」→「是」，翻譯內重複出
現的「ありがとう」造成的落差遠小於這裡；若真的遇到「切出來右半段仍
含假名」的情形，不強行切分，改用「整行是否含假名」判斷這一整行該歸
給 `jp` 還是 `zh`（見 `_split_example_line`）。

這個「切了再驗證」的作法刻意**不依賴 `Fragment.font`**：函式介面只
拿得到 `Fragment`（沒有 `PDFDoc`／`Page`，無法呼叫
`fonts.font_encodings` 解析每頁 `/Font` 資源字典），而且font 本身在
這批資料裡也不是無條件可靠的訊號——引號「」、全形空白等裝飾字元經常
借用另一種語言的字型渲染（例如日文句子裡的中文引號「」本身是
gb18030 字型），逐一核對發現**假名內容**（而非字型）才是唯一在全 15
課、376 行例句／延伸行資料裡沒有任何反例的判準。

## `body_zh`：不嘗試依前後位置細分，直接依出現順序串接

07.pdf 第 5 點文法說明在例句 ⑭ 前後都各有一段內文（前段解釋「もう」
的用法、後段補充否定回答的用法）。`body_zh` 是這個文法點**所有**內
文行（不含標題、不含例句／延伸行）依出現順序直接串接的結果，允許內
文出現在例句前、後，甚至前後都有——不嘗試依語意切成「例句前」「例句
後」兩個欄位（介面只定義了單一 `body_zh` 字串）。多行內文直接相鄰串
接、不加分隔符：這批課本的內文換行是版面寬度限制造成的自然斷行（句
子印到一半就換行），不是分段，直接串接才能正確還原完整句子（已用
07.pdf 第 5 點的四行內文＋兩行內文驗證過，見 `task-10-report.md`）。

## 已知限制

- 少數課別的 `文法` 區段包含表格化內容（例如 09.pdf 「程度副詞」對照
  表、12.pdf／14.pdf 動詞變化對照表），這些內容不使用圈號例句格式，
  一律落入 `body_zh`（原樣保留全部文字，不嘗試解析成結構化例句）。這
  跟 `sentences.py`「問題區段的已知簡化」是同一種處理原則：寧可不精
  細切分，也不要遺漏或損毀內容。
- `all_frags` 參數目前未被使用（`Section.lines` 提供的 fragment 已經
  是 `group_lines` 依 `size >= 8.0` 篩選過的正文字級，`文法` 區段的
  標題／內文／例句全部屬於這個字級範圍，不需要另外從 `all_frags` 撈
  振假名或其他資料）。保留這個參數是為了維持跟 Task 7~11 其餘解析器
  一致的介面形狀，供未來若真的需要（例如例句振假名）時擴充，不是遺
  漏或誤用。
"""
import re
from typing import Dict, List, Optional, Tuple

from tools.extract.fonts import char_width
from tools.extract.fragments import Fragment
from tools.extract.sections import Section

# 例句／延伸行的圈號數字。全 15 課 `文法` 區段掃描過，例句最多用到 ⑳
# （20），沒有超出這個範圍的案例。
_CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭⑮⑯⑰⑱⑲⑳"

# 文法點標題：行首全形或半形數字＋句點（見模組說明「版面縮排層級」）。
# `\s*` 吸收句點後可能的空白——這批資料實測句點後沒有空白字元（見
# 模組說明），但保留這個彈性不影響任何已知案例。
_TITLE_RE = re.compile(r"^([0-9０-９]+)[.．]\s*")

_FULLWIDTH_DIGITS = str.maketrans("０１２３４５６７８９", "0123456789")

# 假名（平假名 U+3040-309F／片假名 U+30A0-30FF）——跟 `sentences.py`
# 判斷「這是不是真正的日文」用同一個字元類別範圍，見模組說明「日中分
# 界」：這是唯一在全 15 課、376 行例句／延伸行資料裡沒有反例的判準。
_KANA_RE = re.compile(r"[぀-ゟ゠-ヿ]")

# 獨立一行、整行恰好是「（詞）」的替代形註記（跟 `sentences.py`
# `_ALT_RE` 同樣的課本排版慣例，例如 07.pdf「(へ)」、01.pdf／08.pdf／
# 13.pdf「（では）」「（が）」）。這種註記有時縮排比同一文法點的例句
# 縮排還深（07.pdf「(へ)」x=108.6，比例句⑧的 x=67.2 深），若只靠
# 「縮排是否大於例句自身」判斷延伸行，會被誤判成例句⑧的延伸內容、再
# 被日中分界邏輯錯誤拆成兩半（見 `task-10-report.md` 複審記錄的具體
# 案例）。這裡在判斷延伸行之前優先攔截，一律歸給內文，不受縮排影響。
_ALT_ANNOTATION_RE = re.compile(r"^[（(]\S+[）)]$")


def _text_width(text: str, size: float) -> float:
    return sum(char_width(ch, size) for ch in text)


def _naive_concat(frags: List[Fragment]) -> str:
    """依 fragment 既有（已依 x 排序）順序直接串接文字，不套用
    `layout.Line.text()` 的字元級插入判定——見模組說明「標題／內文：
    直接依 fragment 既有的 x 序串接」。"""
    return "".join(f.text for f in frags)


def _split_example_line(frags: List[Fragment], strip_marker: bool) -> Tuple[str, str]:
    """把一行例句／延伸行的 fragment 切成 (日文片段, 中文片段)。

    `strip_marker` 為真時，去除第一個 fragment 開頭的圈號數字字元
    （例句起始行專用；延伸行沒有圈號，不需要去除）。

    切分演算法見模組說明「日中分界」：**先確認整行含假名，才嘗試切
    分**——完全不含假名的行（例如純中文延伸行「我向卡莉娜小姐借了
    ＣＤ」）直接整行判定為中文，不嘗試在裡面找切點（這種行任何位置都
    可能出現座標落差，若不先排除，會被誤判成「日文＋中文」兩段，見
    `task-10-report.md` 複審記錄的 07.pdf 第 4 點例句⑩案例）。

    含假名的行，取這一行內部 fragment 間座標落差**最大**的位置試切
    一次，驗證右半段非空白且不含假名才接受；不接受時整行歸為日文，
    不再嘗試次大的落差——次大落差在少數案例（07.pdf 第 2 點例句④的
    延伸行「…「ありがとう」です。是ありがとう。」，中文翻譯本身又引
    述了一次日文「ありがとう」）會找到只切出結尾句點這種退化切法，寧
    可整行判給日文（不遺漏任何字，只是這一則例句的中文欄位留空），也
    不要產生這種切錯位置的結果，見模組說明「已知限制」。"""
    if not frags:
        return "", ""

    texts = [f.text for f in frags]
    if strip_marker and texts[0] and texts[0][0] in _CIRCLED:
        texts[0] = texts[0][1:]

    whole = "".join(texts)
    if not _KANA_RE.search(whole):
        return "", whole
    if len(frags) == 1:
        return whole, ""

    gaps = []
    for i in range(len(frags) - 1):
        end = frags[i].x + _text_width(frags[i].text, frags[i].size)
        gaps.append(frags[i + 1].x - end)
    split_at = max(range(len(gaps)), key=lambda i: gaps[i])  # 切在 split_at 之後

    jp_text = "".join(texts[: split_at + 1])
    zh_text = "".join(texts[split_at + 1:])
    if zh_text.strip() and not _KANA_RE.search(zh_text):
        return jp_text, zh_text
    return whole, ""


class _ItemBuilder:
    """累積單一文法點（標題已知）的內文／例句，直到遇到下一個標題或
    區段結尾。"""

    def __init__(self, no: int, title: str):
        self.no = no
        self.title = title.strip()
        self._body_parts: List[str] = []
        self._examples: List[Dict[str, str]] = []
        self._cur_example: Optional[Dict[str, str]] = None
        self._example_x: Optional[float] = None

    def add_body(self, text: str) -> None:
        self._close_example()
        self._body_parts.append(text)

    def start_example(self, x0: float, frags: List[Fragment]) -> None:
        self._close_example()
        self._example_x = x0
        jp, zh = _split_example_line(frags, strip_marker=True)
        self._cur_example = {"jp": jp, "zh": zh}

    def continue_example(self, frags: List[Fragment]) -> None:
        jp, zh = _split_example_line(frags, strip_marker=False)
        self._cur_example["jp"] += jp
        self._cur_example["zh"] += zh

    def is_continuation_x(self, x0: float) -> bool:
        return (
            self._cur_example is not None
            and self._example_x is not None
            and x0 > self._example_x
        )

    def _close_example(self) -> None:
        ex = self._cur_example
        if ex is not None:
            jp = ex["jp"].strip()
            zh = ex["zh"].strip()
            if jp or zh:
                self._examples.append({"jp": jp, "zh": zh})
        self._cur_example = None

    def finalize(self) -> Dict:
        self._close_example()
        return {
            "no": self.no,
            "title": self.title,
            "body_zh": "".join(self._body_parts).strip(),
            "examples": self._examples,
        }


def parse_grammar(section: Section, all_frags: List[Fragment]) -> List[Dict]:
    """解析 `文法` 區段，回傳每個文法點的
    `{"no", "title", "body_zh", "examples"}`（見模組說明）。

    `all_frags` 目前未被使用——見模組說明「已知限制」。"""
    items: List[Dict] = []
    cur: Optional[_ItemBuilder] = None

    for line in section.lines:
        frags = line.frags
        if not frags:
            continue
        text = _naive_concat(frags)
        stripped = text.strip()
        if not stripped:
            continue

        m = _TITLE_RE.match(stripped)
        if m:
            if cur is not None:
                items.append(cur.finalize())
            no = int(m.group(1).translate(_FULLWIDTH_DIGITS))
            title = stripped[m.end():]
            cur = _ItemBuilder(no, title)
            continue

        if cur is None:
            continue  # 第一個標題之前的行，沒有可歸屬的文法點，捨棄

        x0 = frags[0].x
        if stripped[0] in _CIRCLED:
            cur.start_example(x0, frags)
            continue

        if _ALT_ANNOTATION_RE.match(stripped):
            cur.add_body(text)
            continue

        if cur.is_continuation_x(x0):
            cur.continue_example(frags)
            continue

        cur.add_body(text)

    if cur is not None:
        items.append(cur.finalize())

    return items
