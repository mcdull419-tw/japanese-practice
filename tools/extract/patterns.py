"""練習Ａ 代入表與練習Ｂ 變換題解析：把 `Section`（Task 6）的 `Line` 序列
切成句型代入表（`parse_pattern_tables`）與變換練習題（`parse_drills`）。

設計文件把 `練習Ａ` 稱為「計畫價值最高的資產」——課本本身就是「句型模板
＋槽位候選詞」，而且候選詞是課本編者挑選過、語意保證自然的。本模組的
任務就是把這個既有結構原封不動地抽出來，不是自己發明代入內容。

## `練習Ａ` 版面：整句是一個 fragment，欄位靠課本手動排版的空白撐開

07 課練習Ａ-1 課本原文：

```
    1.日本人            は    はし                  で ごはんを 食べます。
        インドネシア人          スプーンと  フォーク
        アメリカ人              ナイフと  フォーク
```

逐 fragment 檢查發現：行號（`    1.`）跟句子本體是兩個各自獨立的
fragment，但**整個句子本體（含中間用來對齊欄位的十幾個半形空白）是單
一個 fragment**——課本排版是用課本編者自己敲的半形空白撐開視覺欄位，
不是用 PDF `TJ` 陣列的位移數字，也不是分成多個 fragment。

這帶來一個關鍵後果：`Line.cells()`（`min_gap=10.0`，Task 4 介面）**無
法**切出這些欄位。`cells()` 判定換欄的依據是「目前字元的 x 減去前一
個字元的可視延伸終點」，而半形空白的可視延伸（`_visual_extent`）定義
為 0——同一個 fragment 內部，後續字元的 x 全部是用 `fonts.char_width`
累加估計出來的（只有 fragment 的第一個字元有 PDF 給的真實錨點），這
表示連續空白之間，每一步的差值固定等於「前一個空白自己的前進寬度」
（半形空白 6.6pt，見 `fonts.char_width`），不管總共排了幾個空白，永
遠不會被單步 10pt 的門檻抓到。

`tests/extract/test_layout.py` 的 `test_substitution_table_columns_
align`——這次任務簡報明確點名「壞掉的測試」——就是踩到這個事實而從
未真正驗證欄位對齊（它只斷言「有 ≥3 行符合關鍵字」，`cells()` 從未被
呼叫來檢查任何 x 座標）。本模組**不能重蹈覆轍**，因此完全不倚賴
`Line.cells()`／`Line.text()` 來抽取代入表欄位，而是實作了自己的、可
獨立驗證的欄位偵測算法（見下方 `_fine_segments`），並且 `tests/
extract/test_patterns.py` 的 `test_two_slot_table_rows_are_paired`
直接斷言「日本人 必須配 はし」這個具體配對，不是「有抽出東西」這種弱
斷言。

## 欄位偵測：混合「同 fragment 內的空白遊程」與「跨 fragment 的真實座標
落差」兩種訊號

單靠「連續空白遊程（`\\s{2,}`）視為換欄」還不夠：行號 fragment（`
"    1."`，只用半形空白填充）跟句子本體 fragment 之間，**兩者的原始
文字之間完全沒有空白字元**（`"    1."` 後面緊接著就是下一個 fragment
的第一個字「日」），純文字遊程偵測會把它們併成 `"1.日本人"`（實測
見 task-9 探索腳本輸出）。但兩者是**不同 fragment**，跨 fragment 時
第二個 fragment 的 x 是 PDF 給的真實錨點，不是估計值——這裡才真的可
以量出「這兩段文字之間視覺上隔了多遠」：量測結果行號 fragment 估計
結束於 x≈51.6，句子本體 fragment 真實錨點 x=67.2，落差 15.6pt；反觀
真正屬於同一段文字、只是被字型切成多個 fragment 的情形（例如 07 課
練習Ａ-3「"謝謝"」被拆成 `ちゅうごくご…"`／`謝謝`／`"` 三個 fragment，
中文引號跟中文字之間沒有視覺間隔），量出的落差是 0.0pt。兩種情形實測
數字相差兩個數量級（15.6 對 0.0，見 `_FRAGMENT_GAP_THRESHOLD` 說明），
用同一個「跨 fragment 落差 > 5pt 視為強制換欄」規則就能同時處理「行號
要跟句子本體分開」跟「引號不能跟中文字分開」，不需要為行號另外寫特例。

`_fine_segments(line)` 因此結合兩種訊號決定換欄點：(1) 同一 fragment
內部文字遊程 `\\s{2,}`（半形/全形空白皆算，Python `re` 的 `\\s` 在
Unicode 字串上本來就涵蓋 `\\u3000`），(2) 跨 fragment 邊界時真實座標
落差 > `_FRAGMENT_GAP_THRESHOLD`。兩者是獨立的訊號來源，同時滿足任何
一種即可切開；文字遊程用來處理同一 fragment 內部的欄位撐版面空白，跨
fragment 落差用來處理「兩個 fragment 之間完全沒有空白字元、但視覺上
真的有落差」的情形（目前資料裡只有行號標籤這一種案例，但規則本身不
限定只能用在行號）。

## 槽位偵測：以基底句欄位為準，用「欄位區間」比對後續列的候選詞

依任務簡報演算法：基底句（行首 `N.` 那一行）的欄位定義了這張表的欄位
骨架；後續無編號的列，其欄位 x 若能對應到基底句的某個欄位，就是該欄
位的替代候選詞。

**比對必須是「欄位區間」，不能是「離哪個欄位最近」**：07 課練習Ａ-1
的「フォーク」（`スプーンと フォーク`／`ナイフと フォーク` 這種雙詞
槽位值的第二個片段）x=304.8，離右邊的固定欄「で ごはんを 食べます。」
（x=370.8，距離 66.0）比離正確欄位 T（`はし` 欄，x=225.6，距離 79.2）
還近——複審時第一版實作用「離哪個欄位最近」，實際跑出來把「フォー
ク」錯誤地跟下一欄的固定文字混在一起，`slots` 因此多算出一個不存在
的第三個槽位（`test_two_slot_table_rows_are_paired` 直接測出這個回
歸：`len(t["slots"])` 量到 3，不是預期的 2）。正確的作法是「一旦進入
某欄，同一欄內接下來的內容不論多寬都留在同一欄，直到真的越過下一欄
的起點」——這跟 `vocab.py` 判斷單字表漢字／中文欄位歸屬時的教訓完全
一致（「不能只看相鄰 Cell 的間距」），這裡是同一類問題的另一次出現。

但區間比對的容差也不能寫死簡報建議的 ±6pt：03 課練習Ａ-6「1,500えん」
／「5,800えん」的欄位 x 是 205.8，但「13,000えん」（多一位數字）的欄
位 x 量出來是 199.2，落後 6.6pt，超過 ±6pt。`_column_index` 改用
`_COLUMN_TOLERANCE = 10.0`（見該常數說明：大於 6.6，涵蓋 03 課這個真
實案例；同時小於本模組看過的資料裡最窄相鄰欄距的一半，不會讓兩個欄
位的管轄範圍重疊）。這裡把 07 課「フォーク」（容差需要夠小，否則會
被錯誤併入下一欄）跟 03 課「13,000えん」（容差需要夠大，否則會被錯
誤併入上一欄）兩個方向相反的真實反例並列記錄，避免又是「只在單一課
別試通就交差」。

## 疑問句變體：整列排除、不進槽位（`question_variant`）

課本用重複的「……」（U+2026 全形省略號，重複多次，不是句點）後接
「か。」表示「這裡跟基底句一樣，只有問號結尾不同」（例如 07 課練習
Ａ-1 第四列「なん                  …………………………か。」代表「{S}は
なんで ごはんを 食べますか。」）。`_QUESTION_VARIANT_RE` 用「一個以上
`…` 後面接 `か`、後面可選一個句點、錨定在整列文字結尾」判定，這一列
會被整列排除、不計入槽位候選詞、也不計入 `rows`，另外存進
`question_variant`（欄位不存在時為 `None`，不是遺漏這個 key）。這是
簡報演算法第 6 點的直接實作，`question_variant` 目前只做「盡力還原」
的重建（見 `_reconstruct_question`），沒有任何驗收測試鎖定其精確內容
（任務簡報給的 7 個測試都沒有斷言 `question_variant`），這裡誠實記錄
這一點，不誇大其精確度。

## `id`：採用課本本身的 `N.` 編號，不是輸出位置

跟 Task 8（`sentences.py`）踩過的臭蟲一樣的教訓：`id` 裡的編號直接來
自基底句行首的 `N.`（`_TABLE_START_RE` 的捕捉群組），不是這個表在輸出
陣列裡的位置。07 課練習Ａ 6 張表剛好是連續的 1~6、練習Ｂ 7 題也剛好是
連續的 1~7，兩者在這一課恰好與位置一致，但這是**資料巧合**、不是規則
本身的保證——往後若有課別的代入表編號跳號（例如課本編者刪掉了一張表
又沒有重新編號），這裡的實作依然只會照課本印出來的號碼走。

## `練習Ｂ` 變換題：絕對不能用 `Line.text()`／`cells()` 的閱讀順序

任務簡報明確點名的第二個陷阱：01 課練習Ｂ-3 的第 1 小題，`Line.text()`
（`layout.py` 的字元級閱讀順序重建，見該模組「插入 vs. 原子性」規則）
會把小題內容重新排成「山田さん・エンジニア      1) →」——**編號「1)」
被排到內容後面**。逐 fragment 核對後找到真正原因：這一列的兩個
fragment 分別是 `"        1)"`（x=12.0，8 個前導半形空白 + `1)`）與
`" 山田さん・エンジニア "`（x=25.8，真實錨點）。`layout.py` 的插入判
定規則是「某 fragment 的錨點嚴格落在另一個 fragment 的 [起點,估計終
點) 跨距內部」——`" 山田さん・エンジニア "` 的錨點 25.8 剛好落在
`"        1)"` 的估計跨距 [12.0, 約78.0) 內部（8 個前導空白＋"1)"兩字
的估計前進寬度撐到約 78pt），因此被 `layout.py` 判定成「插入到行號標
籤內部」，照插入規則重新排列，產生錯亂的閱讀順序。

**這不是 `layout.py` 的臭蟲**——那條插入規則是為了正確處理中文釋義
裡穿插日文替換詞（07 課「打電〔話〕」）這種真實需要精確處理的情境，
在全 15 課的字元級不變量測試（`test_layout.py` 的
`TestCharLevelReadingOrder`）下已充分驗證。這裡只是課本另一種完全不
相關的排版巧合（行號標籤用大量前導空白撐開、實際內容的真實錨點又剛
好落在那段空白的估計跨距內）意外觸發了同一條規則，產生語意上錯誤的
順序。

**解法**：`練習Ｂ` 完全不呼叫 `Line.text()`／`Line.cells()`，改用
`_naive_concat(line)`——單純依 `line.frags`（`layout.py` `_build_line`
已經依 x 由小到大排序，這一步本身不套用任何插入規則）逐一取
`f.text` 直接串接。這樣重建出來的字串固定是
`"        1) 山田さん・エンジニア  →"`——編號、內容、箭頭依原始
fragment 順序排列，跟課本印刷順序一致。

**即使如此，最終小題順序仍然不依賴這個字串的字元順序**：`_parse_
one_drill` 用 `_ITEM_RE` 掃出「每個 `N)` 標籤＋其後到下一個箭頭之間
的內容」，再**依擷取到的整數 `N` 排序**才組成 `items`
清單，不是依掃描到的先後順序。這是任務簡報明確要求的（「必須依 N) 的
編號排序，不可依 x 座標排序」），也是防禦性的雙重保險：即使
`_naive_concat` 在還沒觀察到的其他課別又踩到某種目前未知的錯位，只要
`N)` 標籤本身沒被拆散，排序這一步仍然能救回正確順序。

## `例` 前導區塊：可能有多個範例（`例１：`／`例２：`），簡化為以「／」
串接

07 課練習Ｂ-7、01 課練習Ｂ-4 都是「一題兩個範例＋各自的延續答案」的
格式（`例１：……→……` 換行接「……」延續答案，然後換行又是`例２：`）。
任務介面（`{"model_cue", "model_answer", ...}`）只有單一欄位可以承載
範例，無法無損表達「這一題其實有兩組範例」。這裡選擇用全形「／」把多
組範例的 cue／answer 分別串接成一個字串（保留全部內容，不是丟棄第二
組），並在此明確記錄這是簡化，不是遺漏——跟 `sentences.py`「問題區段
的已知簡化」是同一種處理原則：介面必須維持穩定，資訊改用可見、明確
記錄的方式保留，不是靜默流失。

## `……` 延續行：courseware 排版慣例，不是句子的一部分

例句的答案有時因為版面寬度印不下，換行後在行首印一個「……」（見 07
課練習Ｂ-2「……「パソコン」です。」）。這裡在合併多行前導文字之前，
先把每一行行首的「……」去掉（`_strip_continuation_marker`），視為純
排版標記，不當作句子內容保留——全 15 課目前看到的每一個「……」出現
位置都恰好是「這一行是接續前一行答案」的角色，從未出現在句子中間當
作真正的語意省略號使用（若未來發現反例，這裡的假設需要重新檢視）。
"""
import re
from typing import Dict, List, Optional, Tuple

from tools.extract.fonts import char_width
from tools.extract.layout import Line
from tools.extract.sections import Section

# 行首「N.」——代入表／變換題的表號／題號來自這裡（課本本身印出的編
# 號），不是輸出陣列裡的位置（見模組說明「id：採用課本本身的 N. 編
# 號」）。
_TABLE_START_RE = re.compile(r"^\s*(\d+)\.")

# 跨 fragment 邊界的真實座標落差門檻（pt）。實測：07 課「行號 fragment
# →句子本體 fragment」的落差固定是 15.6pt；同一課「中文引號→中文字」
# 這種真正該連續的跨 fragment 邊界落差固定是 0.0pt（見模組說明「欄位
# 偵測」，兩者相差兩個數量級，5.0 這個門檻兩側都留有充裕的安全邊界）。
_FRAGMENT_GAP_THRESHOLD = 5.0

# 疑問句變體：一個以上全形省略號（U+2026，可能重複很多次）後面接
# 「か」，可選再接一個句點，且必須錨定在整列文字的結尾（見模組說明
# 「疑問句變體」）。
_QUESTION_VARIANT_RE = re.compile(r"…+か。?\s*$")

# 欄位歸屬容差（pt）。見模組說明「槽位偵測」：欄位歸屬必須是「這個 x
# 落在哪個欄位的管轄範圍內」（區間式），不能單純「離哪個欄位最近」
# ——07 課練習Ａ-1 的「フォーク」（多字詞槽位值的第二個片段，x=304.8）
# 離右邊的固定欄「で ごはんを 食べます。」（x=370.8，距離 66.0）其實
# 比離正確欄位「T」（はし欄，x=225.6，距離 79.2）更近，若改用最近欄位
# 會把它誤判成下一欄，錯誤地把兩個獨立欄位的內容混在一起（複審時实際
# 測出這個回歸，見下方 `_column_index`）。
#
# 但區間式比對也不能寫死 ±6pt（簡報建議值）：03 課「13,000えん」量出
# 來的欄位 x 是 199.2，比同一欄其他列（1,500えん／5,800えん，x=205.8）
# 落後 6.6pt，超過 ±6pt。這裡取 10.0pt——大於 6.6（涵蓋 03 課這個真實
# 案例），且小於本模組目前看過的全部資料裡「最窄的相鄰欄位間距」的一
# 半（07 課練習Ａ-2「で」（238.8）到「レポートを」（265.2）間距
# 26.4pt，一半是 13.2pt，10.0 留有安全邊際，不會讓兩個相鄰欄位的管轄
# 範圍重疊）。
_COLUMN_TOLERANCE = 10.0

# 槽位命名：依簡報範例從 S 開始（S、T、U……），不是 A、B、C。最多命名
# 到 Z（26-83=... 這批課本資料實測最多只有 2 個槽位，遠低於這個上
# 限；超過上限時退回 "S%d" 這種數字後綴，避免真的撞到才崩潰）。
_SLOT_LETTERS = [chr(ord("S") + i) for i in range(ord("Z") - ord("S") + 1)]


def _slot_letter(idx: int) -> str:
    if idx < len(_SLOT_LETTERS):
        return _SLOT_LETTERS[idx]
    return "S%d" % idx


def _collapse_ws(text: str) -> str:
    """把任意長度的空白遊程（含全形空白）壓成一個半形空白，首尾空白去
    掉。用於清理課本編者手動排版用的撐版面空白，不用於欄位偵測本身
    （欄位偵測見 `_fine_segments`，需要保留原始空白遊程的位置資訊）。"""
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# 練習Ａ：代入表
# ---------------------------------------------------------------------------


def _combined_chars(line: Line) -> List[Tuple[str, float, bool]]:
    """把一行的所有 fragment 依 `line.frags` 既有順序（`layout.py`
    `_build_line` 已依 x 由小到大排序，這裡不套用任何插入規則）串接成
    逐字元序列 `(字元, x, 是否為強制換欄點)`。

    每個 fragment 的第一個字元使用其真實錨點 `f.x`；同一 fragment 內
    後續字元用 `fonts.char_width` 累加估計（跟 `layout.py` 對單一
    fragment 內部字元位置的處理方式一致）。fragment 邊界處若真實座標
    落差超過 `_FRAGMENT_GAP_THRESHOLD`，標記為強制換欄點（見模組說明
    「欄位偵測」）。
    """
    out: List[Tuple[str, float, bool]] = []
    prev_end: Optional[float] = None
    for f in line.frags:
        force = prev_end is not None and (f.x - prev_end) > _FRAGMENT_GAP_THRESHOLD
        x = f.x
        for i, ch in enumerate(f.text):
            out.append((ch, x, force and i == 0))
            x += char_width(ch, f.size)
        prev_end = x
    return out


def _fine_segments(line: Line) -> List[Tuple[float, str]]:
    """把一行切成欄位候選清單 `(欄位起點 x, 文字)`。換欄依兩種訊號（見
    模組說明「欄位偵測」）：同一 fragment 內部 `\\s{2,}` 空白遊程，或
    跨 fragment 邊界的真實座標落差。純空白的欄位（沒有任何非空白字
    元）不輸出。"""
    chars = _combined_chars(line)
    text = "".join(c[0] for c in chars)

    cut_points = {0, len(text)}
    for m in re.finditer(r"\s{2,}", text):
        cut_points.add(m.start())
        cut_points.add(m.end())
    for i, (_ch, _x, force) in enumerate(chars):
        if force:
            cut_points.add(i)

    bounds = sorted(cut_points)
    segments: List[Tuple[float, str]] = []
    for lo, hi in zip(bounds, bounds[1:]):
        seg_text = text[lo:hi]
        if seg_text.strip():
            segments.append((chars[lo][1], seg_text.strip()))
    return segments


def _column_index(x: float, base_xs: List[float]) -> int:
    """回傳 `x` 所屬的欄位索引：`base_xs` 中，滿足
    `base_xs[i] <= x + _COLUMN_TOLERANCE` 的最後一個索引（見模組說明
    「槽位偵測」與 `_COLUMN_TOLERANCE`）。這是區間式歸屬（一旦進入某
    欄，同一欄內後續內容不論多寬都留在同一欄，直到真的越過下一欄的起
    點），不是單純的「離哪個欄位最近」。"""
    idx = 0
    for i, bx in enumerate(base_xs):
        if bx <= x + _COLUMN_TOLERANCE:
            idx = i
        else:
            break
    return idx


def _reconstruct_question(
    base_texts: List[str], row_values: Dict[int, str], ellipsis_start_idx: Optional[int]
) -> Optional[str]:
    """盡力還原疑問句變體的完整句子（見模組說明「疑問句變體」）。

    省略號代表「從這個欄位開始、一路到句尾，跟基底句一樣，只是改成疑
    問形」——**不是只取代它自己落在的那一欄**。07 課練習Ａ-4「あなたは
    だれ         …………………………か。」複審時第一版實作只把省略號自己
    歸屬到的那一欄（「に」欄）換成「にか。」，其餘欄位（「電話を」
    「かけます。」）各自沿用基底句原文，串接後產生「あなたはだれにか。
    電話をかけます。」——文法錯誤的殘句。真正原因是：省略號那一串點沒
    有被空白斷開、橫跨了好幾個基底欄位的視覺寬度，但它落腳的 x 只對齊
    到「這一段被省略的內容」的**起點**（緊接在被替換詞之後的那一欄），
    不是這句話真正的最後一欄。

    修正後的作法：省略號欄位視為「從它自己起，到最後一欄為止，這一段
    全部原樣沿用基底句、整段一起接上疑問語尾」——`ellipsis_start_idx`
    到 `len(base_texts)-1` 之間的基底欄位文字直接串接（不套用任何這幾
    欄各自的候選詞替換，因為省略號本來就代表「這裡沒有换的，跟基底句
    一樣」），只在這一整段的結尾把句點換成「か。」。用這個修正過的邏
    輯重算 07 課練習Ａ-4／5，分別得到「あなたはだれに電話をかけます
    か。」「あなたはだれに 本を借りましたか。」——文法通順、語意正確。

    沒有任何驗收測試鎖定這個字串的精確內容（見模組說明），這裡誠實記
    錄：這個函式追求「語意正確」，已用上述兩個實例交叉核對過，但沒有
    對全 15 課逐一驗證過每一種疑問句變體的排版變體。
    """
    if ellipsis_start_idx is None:
        return None
    pieces = [row_values.get(idx, base_texts[idx]) for idx in range(ellipsis_start_idx)]
    tail_texts = list(base_texts[ellipsis_start_idx + 1:])
    head = row_values.get(ellipsis_start_idx, base_texts[ellipsis_start_idx])
    suffix = "".join([head] + tail_texts)
    if suffix.endswith("。"):
        suffix = suffix[:-1] + "か。"
    else:
        suffix = suffix + "か。"
    pieces.append(suffix)
    return "".join(pieces)


def _parse_one_table(lesson: int, table_no: int, lines: List[Line]) -> Dict:
    base_line = lines[0]
    base_segments = _fine_segments(base_line)
    # base_segments[0] 是行首 "N." 標籤本身（見模組說明「欄位偵測」的
    # 跨 fragment 落差機制——行號 fragment 跟句子本體 fragment 之間的
    # 15.6pt 落差會被切成獨立的第一個 segment）。
    base_columns = base_segments[1:]
    base_xs = [x for x, _ in base_columns]
    base_texts = [t for _, t in base_columns]

    variant_rows: List[Dict[int, str]] = []
    question_variant: Optional[str] = None
    question_ellipsis_idx: Optional[int] = None
    question_row_values: Dict[int, str] = {}

    for line in lines[1:]:
        raw = "".join(f.text for f in line.frags)
        segments = _fine_segments(line)
        if not segments:
            continue

        if _QUESTION_VARIANT_RE.search(raw):
            row_values: Dict[int, str] = {}
            ellipsis_idx = None
            for x, text in segments:
                idx = _column_index(x, base_xs) if base_xs else 0
                m = _QUESTION_VARIANT_RE.search(text)
                if m:
                    ellipsis_idx = idx
                    prefix = text[: m.start()].strip()
                    if prefix:
                        row_values[idx] = _collapse_ws(
                            (row_values.get(idx, "") + " " + prefix).strip()
                        )
                else:
                    row_values[idx] = _collapse_ws(
                        (row_values.get(idx, "") + " " + text).strip()
                    )
            question_row_values = row_values
            question_ellipsis_idx = ellipsis_idx
            continue

        row_values = {}
        for x, text in segments:
            idx = _column_index(x, base_xs) if base_xs else 0
            row_values[idx] = _collapse_ws((row_values.get(idx, "") + " " + text).strip())
        variant_rows.append(row_values)

    if question_row_values or question_ellipsis_idx is not None:
        question_variant = _reconstruct_question(
            base_texts, question_row_values, question_ellipsis_idx
        )

    # 只有「真的出現過跟基底句不同的候選詞」的欄位才算槽位——07 課練
    # 習Ａ-6 每一列都重印了完全相同的「ました。」在同一欄（idx3），這
    # 欄位確實「被後續列碰到」了，但三列的值全部相同，不是真正的可替
    # 換槽位。若只憑「有沒有被任何列碰到」判定槽位，會產生一個候選詞
    # 清單裡三個值都一樣的假槽位，`template` 因此少展現這欄本來是固
    # 定文字的事實。改成「該欄位至少有一列的值跟基底句不同」才算數。
    slot_idxs = sorted({
        idx
        for row in variant_rows
        for idx in row
        if row[idx] != base_texts[idx]
    })
    if not slot_idxs and base_columns:
        # 防禦性後備：目前 15 課驗證過的資料裡，每張代入表至少都有一個
        # 真正的槽位（見模組說明），這個分支目前沒有真實案例觸發，只
        # 是避免「這張表萬一真的沒有替代候選詞」時 template 整個沒有
        # 任何 "{" 佔位符（會讓 test_template_has_placeholders 這類不
        # 變量失守，且下游代入練習完全無法使用）。退而求其次，把第一
        # 欄當成只有一個候選詞的槽位。
        slot_idxs = [0]

    slot_letters = {idx: _slot_letter(i) for i, idx in enumerate(slot_idxs)}
    slots: Dict[str, List[str]] = {slot_letters[idx]: [base_texts[idx]] for idx in slot_idxs}
    rows: List[List[int]] = [[0] * len(slot_idxs)]

    for row_values in variant_rows:
        if not any(idx in row_values for idx in slot_idxs):
            continue
        row_indices = []
        for idx in slot_idxs:
            letter = slot_letters[idx]
            if idx in row_values:
                slots[letter].append(row_values[idx])
                row_indices.append(len(slots[letter]) - 1)
            else:
                # 這一列沒有提供這個槽位的新候選詞——沿用前一列的索引
                # （見模組說明「槽位偵測」，目前資料沒有實際案例觸發這
                # 個分支，是防禦性設計，不是憑空猜測的行為）。
                row_indices.append(rows[-1][slot_idxs.index(idx)] if rows else 0)
        rows.append(row_indices)

    template = "".join(
        "{%s}" % slot_letters[idx] if idx in slot_letters else base_texts[idx]
        for idx in range(len(base_texts))
    )

    result: Dict = {
        "id": "L%02d-A%d" % (lesson, table_no),
        "template": template,
        "slots": slots,
        "rows": rows,
        "requires_lesson": lesson,
        "question_variant": question_variant,
    }
    return result


def parse_pattern_tables(section: Section, lesson: int) -> List[Dict]:
    """把 `練習Ａ` 的 `Line` 序列切成代入表清單（見模組說明）。"""
    lines = section.lines
    starts: List[int] = []
    for i, line in enumerate(lines):
        raw = "".join(f.text for f in line.frags)
        if _TABLE_START_RE.match(raw):
            starts.append(i)

    tables: List[Dict] = []
    for si, start in enumerate(starts):
        end = starts[si + 1] if si + 1 < len(starts) else len(lines)
        raw = "".join(f.text for f in lines[start].frags)
        table_no = int(_TABLE_START_RE.match(raw).group(1))
        tables.append(_parse_one_table(lesson, table_no, lines[start:end]))
    return tables


# ---------------------------------------------------------------------------
# 練習Ｂ：變換題
# ---------------------------------------------------------------------------

# 例句範例標籤：「例：」「例１：」「例 ：」等（見模組說明「例 前導區
# 塊」），全形／半形冒號皆接受，數字與冒號前後容許空白。
_EXAMPLE_RE = re.compile(r"例\s*\d*\s*[:：]")

# 小題編號：「N)」，捕捉數字本身、以及到下一個「→」（或字串結尾）之前
# 的內容。不會跟 `_TABLE_START_RE`／drill 開頭的「N.」搞混，因為這裡
# 認的是右括號，不是句點。
#
# 右括號同時接受半形「)」與全形「）」：05 課練習Ｂ-2 小題 4 逐 fragment
# 核對過，課本原文本身就印成全形「4）」（其餘三個小題都是半形
# 「1)」「2)」「3)」，同一列裡混用），是課本排版的不一致，不是抽取
# 或解碼造成的損毀（`ord('）')==0xff09`，`FULLWIDTH RIGHT PARENTHESIS`，
# 逐 fragment 檢查跟其他頁面的全形符號一致）。只認半形會讓這個小題整
# 個從 `items` 消失（複審批次跑全 15 課時發現：`L05-B2` 只抽到 3 個
# 小題，缺第 4 個），因此兩種括號都要接受。
_ITEM_RE = re.compile(r"(\d+)[)）]([^→]*)(?:→|$)")

# 續行標記「……」（全形省略號，一個以上）——課本用來表示「這一行接續
# 上一行沒印完的答案」，見模組說明「…… 延續行」。只吃行首（可能有
# 前導空白）的這個標記，不動句子中間的內容。
_CONTINUATION_RE = re.compile(r"^\s*…+\s*")


def _naive_concat(line: Line) -> str:
    """依 `line.frags` 既有順序（已依 x 排序，未套用任何插入規則）直
    接串接每個 fragment 的原始文字。見模組說明「練習Ｂ 變換題」：
    `Line.text()`／`cells()` 的插入規則會在特定巧合下把行號標籤跟後面
    的內容錯誤地交錯在一起，`練習Ｂ` 一律改用這個更簡單、更可預期的
    串接方式。"""
    return "".join(f.text for f in line.frags)


def _strip_continuation_marker(text: str) -> str:
    return _CONTINUATION_RE.sub("", text)


def _parse_one_drill(lesson: int, drill_no: int, lines: List[Line]) -> Dict:
    item_start = None
    for i, line in enumerate(lines):
        if re.search(r"\d+\)", _naive_concat(line)):
            item_start = i
            break
    if item_start is None:
        item_start = len(lines)

    preamble_lines = lines[:item_start]
    item_lines = lines[item_start:]

    preamble_text = " ".join(
        _strip_continuation_marker(_naive_concat(ln)) for ln in preamble_lines
    )
    examples = _EXAMPLE_RE.split(preamble_text)[1:]  # [0] 是題號本身，丟棄

    cues: List[str] = []
    answers: List[str] = []
    for chunk in examples:
        cue_raw, _, answer_raw = chunk.partition("→")
        cues.append(_collapse_ws(cue_raw))
        answers.append(_collapse_ws(answer_raw))

    model_cue = "／".join(cues) if cues else ""
    model_answer = "／".join(answers) if answers else ""

    item_text = " ".join(_naive_concat(ln) for ln in item_lines)
    found = [(int(n), _collapse_ws(content)) for n, content in _ITEM_RE.findall(item_text)]
    found.sort(key=lambda pair: pair[0])
    items = [content for _n, content in found]

    return {
        "id": "L%02d-B%d" % (lesson, drill_no),
        "model_cue": model_cue,
        "model_answer": model_answer,
        "items": items,
    }


def parse_drills(section: Section, lesson: int) -> List[Dict]:
    """把 `練習Ｂ` 的 `Line` 序列切成變換題清單（見模組說明）。"""
    lines = section.lines
    starts: List[int] = []
    for i, line in enumerate(lines):
        raw = _naive_concat(line)
        if _TABLE_START_RE.match(raw):
            starts.append(i)

    drills: List[Dict] = []
    for si, start in enumerate(starts):
        end = starts[si + 1] if si + 1 < len(starts) else len(lines)
        raw = _naive_concat(lines[start])
        drill_no = int(_TABLE_START_RE.match(raw).group(1))
        drills.append(_parse_one_drill(lesson, drill_no, lines[start:end]))
    return drills
