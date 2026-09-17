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

**單一容差常數終究撐不住所有情形，`_parse_one_table` 因此在區間比對
之外，另外加了一條「segment 數對得上就依位置對應」的規則**：08 課練
習Ａ-2「にぎやか です にぎやか じゃ ありません」這一列，第二個
「にぎやか」的真實 x 落後參照欄位 13.8pt——比 03 課的 6.6pt 還大，超
過 `_COLUMN_TOLERANCE`（10.0pt，這個值已經是 07 課「フォーク」跟 03
課「13,000えん」兩個反例拉扯出來的結果，不能再放大，放大會讓 07 課
「フォーク」的兩欄之間開始有歧義）。用區間比對會把它誤併回前一欄，
產生「です にぎやか」這種混雜兩個欄位內容的候選詞。

真正的解法不是再調容差，是換一種歸屬依據：**這一列的 segment 數
（5 個）剛好跟基底句欄位數（5 欄）完全相等，代表這一列每一欄都有給
值、沒有省略任何欄位**——這時候不需要猜 x 落在哪個區間，直接依印刷
順序逐一對應（第 1 個 segment 對應第 1 欄……以此類推）就一定正確，
徹底繞開 x 抖動的問題。這條規則只在 segment 數跟欄位數完全相等時套
用：07 課練習Ａ-1「インドネシア人 スプーンと フォーク」只有 3 個
segment，跟基底句 4 欄對不上（這一列沒有觸碰「は」跟「で ごはんを
食べます。」這兩個固定欄），這種「只碰到部分欄位」的列，逐位置對應
會整個對錯欄，必須繼續用 `_column_index` 的區間判斷。兩種規則搭配之
後，07 課「フォーク」跟 08 課「にぎやか」這兩個方向相反的真實反例都
不再需要靠同一個容差常數硬撐（實作細節見 `_parse_one_table` 呼叫
`_column_index` 前的 `len(cleaned) == len(base_columns)` 判斷）。

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

**誠實記錄這條防禦線目前的驗證狀態**：對全 15 課、107 筆變換題逐一比
對過「依 `_ITEM_RE` 掃描到的先後順序」跟「依擷取到的整數 `N` 排序」
兩者的 `items` 結果，兩者在現有語料裡**從未出現過差異**（複審移除這
行排序、重跑全部測試，142 個測試依然全綠）。換句話說，這個排序步驟
目前是**防禦性**的——現有課本資料裡，`_naive_concat` 依 fragment x
序重建出來的字串，`N)` 標籤本身出現的先後順序恰好一律等於數字大小順
序，`01.pdf` 練習Ｂ-3 那種「編號跟內容錯開」的情形（見上方）目前從未
真的讓兩個以上的 `N)` 標籤本身彼此顛倒。這不代表這行排序是多餘的：
它是規格明文要求的不變量，且只要未來有一課的版面把 `N)` 標籤本身的
掃描順序也弄反，這行排序就會是唯一的救援機制——只是目前的驗證證據
告訴我們「這件事還沒發生過」，不是「這件事不可能發生」，這裡如實記
錄兩者的差別，不誇大這條防禦線目前抓到的真實案例數量（目前是 0）。

## `例` 前導區塊：可能有多個範例（`例１：`／`例２：`），簡化為以
`_MULTI_EXAMPLE_SEP` 串接

07 課練習Ｂ-7、01 課練習Ｂ-4 都是「一題兩個範例＋各自的延續答案」的
格式（`例１：……→……` 換行接「……」延續答案，然後換行又是`例２：`）。
任務介面（`{"model_cue", "model_answer", ...}`）只有單一欄位可以承載
範例，無法無損表達「這一題其實有兩組範例」。這裡選擇把多組範例的
cue／answer 分別串接成一個字串（保留全部內容，不是丟棄第二組），並在
此明確記錄這是簡化，不是遺漏——跟 `sentences.py`「問題區段的已知簡
化」是同一種處理原則：介面必須維持穩定，資訊改用可見、明確記錄的方
式保留，不是靜默流失。

**分隔符不能用全形斜線「／」**（第一版的選擇）——複審修正 cue／answer
分界 bug 之後，額外新增的「cue 是否落在正確欄位」獨立檢查（見下方
「cue／answer 分界」一節與 task-9-report.md）在全 15 課逐課掃描時揪
出：08 課練習Ｂ-5 的 cue **本身**就真的包含全形斜線（課本原文「花を
買いました／きれい」——「做了什麼」跟「什麼樣的」兩個真實片語，用斜
線連接，是課本自己的標點，不是本模組加的分隔符）。若拿同一個字元當
「這裡有幾組範例」的分隔符，`model_cue.split("／")` 會把這種單一 cue
誤切成兩截，下游完全無法正確還原「這一題有幾組範例」——內容沒有損
毀，但**結構**被誤判，跟複審一開始抓到的「內容在不在 vs. 內容在對的
欄位裡」是同一類問題，只是這次是我自己新增的獨立檢查在導入這個修正
的過程中自己抓到的，不是複審報告原文列出的項目。改用
`_MULTI_EXAMPLE_SEP = "｜"`（全形直線，U+FF5C）：全 15 課練習Ｂ 逐字
掃描過，這個字元從未出現在任何課本原文內容裡。

## `……` 延續行：courseware 排版慣例，不是句子的一部分

例句的答案有時因為版面寬度印不下，換行後在行首印一個「……」（見 07
課練習Ｂ-2「……「パソコン」です。」）。這裡在合併多行前導文字之前，
先把每一行行首的「……」去掉（`_line_tokens`），視為純排版標記，不當
作句子內容保留——全 15 課目前看到的每一個「……」出現位置都恰好是
「這一行是接續前一行答案」的角色，從未出現在句子中間當作真正的語意
省略號使用。**這個假設已經用一個真實反例交叉核對過，不是空話**：15
課練習Ｂ-3「すみません。 ちょっと……。」的「……」是句子**中間**真正
的日文語尾委婉省略（口語裡「不太方便」的婉拒），不是續行標記——這個
字串完全沒有出現在任何一行的**行首**，複審用「對照算繪頁面比對語意
完整性」找出這個字串正確保留在 `model_answer` 裡（見下方修正記錄），
證實 `_CONTINUATION_RE`「只吃行首」這個設計沒有誤傷這個真實反例。

## cue／answer 分界：以 fragment 邊界為準，不是「→」字元的字串位置
（複審發現的資料損毀，已修正）

第一版實作把整段前導文字（跨行）先串成一個字串，再用
`str.partition("→")` 找箭頭切 cue／answer。複審用「對照算繪頁面比對
cue／answer 語意完整性」這個跟 Task 9 原本「逐字回查」完全不同的角
度，在全 15 課、107 筆變換題裡揪出 8 筆受害：`str.partition` 假設
「→」的字串位置就是語意上 cue 跟 answer 的分界，但至少兩種課本排版
變體會讓這個假設不成立（06 課練習Ｂ-7「沒有箭頭」、10／11／13／14
課多筆「箭頭印在示範問句之後、不是 cue 跟示範問句之間」）。詳細根因
與修正後的規則見 `_split_cue_answer` 的 docstring。**這個 bug 之所以
穿過原本「逐字回查」的檢查**：合併錯誤並不會讓內容從原始文字裡消
失——cue 跟 answer 的內容都還在，只是被分進了錯的欄位；逐字回查只驗
證「內容在不在」，不驗證「內容在對的欄位裡」，因此回報「0 個問
題」。修正後新增的檢查（見 `parse_drills` 的批次驗證腳本，摘要見
task-9-report.md）改為同時驗證兩者。
"""
import re
from collections import Counter
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

# 尾端純省略號（沒有接「か」）——課本另一種用法：省略號不一定是「這裡
# 開始都跟基底句一樣、改成疑問形」的結尾標記（`_QUESTION_VARIANT_RE`
# 專門處理那一種，一定帶「か」），也可能只是單純「這一欄（或這一欄的
# 尾巴）不變，用點代替重印一次基底句原文」的視覺速記，不接「か」：
#
# - 04 課練習Ａ-5「あなたは …… なんじ ………………か。」：「……」自成一
#   個欄位（欄位裡只有點，沒有其他字），落在「毎朝」的欄位，代表這欄
#   沿用基底句原文；真正的結尾標記是後面帶「か。」的那一段。
# - 13 課練習Ａ-4「あなたは…… なにを し …………か。」：「……」沒有自
#   成一欄，是**緊接在「あなたは」後面、同一個欄位**裡的尾巴（這一欄
#   跟基底句排版時中間沒有留白，兩段文字被存成同一個 fragment）——
#   若不處理，「……」會原封不動跟著「あなたは」一起被當成這一欄的候
#   選詞內容，重建出「あなたは……なにをしに行きますか。」這種殘留裝
#   飾符號的錯誤句子。
#
# 兩種情形的共通處理：只要一個欄位的文字**尾端**是一段沒有接「か」的
# 省略號，一律把這段尾端省略號去掉，剩下的文字（可能是空字串，也可能
# 像「あなたは」這樣還有實質內容）才是這一欄真正的候選詞。全 15 課逐
# 課掃描過，這種「尾端純省略號、沒有か」的情形只出現在 04、11、13 三
# 課，共 4 處，這裡明確記錄樣本數不大，但已對每一處都核對過語意（見
# `_parse_one_table` 呼叫處）。
_TRAILING_BARE_ELLIPSIS_RE = re.compile(r"…+$")

# 整列以省略號開頭、但不是疑問句變體（不符合 `_QUESTION_VARIANT_RE`，
# 即結尾沒有「か」）——複審後額外發現的第三種課本用法：12 課練習Ａ-5
# 「……  サッカー の ほうが おもしろいです。」是「示範答案」（呼應
# `練習Ｂ` 的「……延續行」慣例，只是這次出現在 `練習Ａ` 的代入表裡），
# 不是這張表的替代候選詞。若不排除，這一整列會被當成普通候選列處理，
# 「……」跟示範答案本身的文字會原封不動混進槽位候選詞清單（複審實測
# L12-A5 因此把 `slots["S"]` 污染成
# `["サッカー","ほん","しごと","…… サッカー","ほん","しごと"]`，
# `rows` 的配對也完全錯亂）。這一整列直接排除、不計入 `variant_rows`
# 也不計入 `rows`——跟疑問句變體被整列排除、另存 `question_variant`
# 是類似的處理精神，但這裡沒有對應的介面欄位可以承接（任務介面
# `parse_pattern_tables` 只定義了 `question_variant`，沒有「範例答
# 案」欄位），所以只排除，不另外保留內容。全 15 課逐課掃描過，這種
# 「整列以省略號開頭、結尾沒有か」的情形只出現在 12 課這一處。
_SAMPLE_ANSWER_ROW_RE = re.compile(r"^\s*…+")

# 欄位歸屬容差（pt）。見模組說明「槽位偵測」：欄位歸屬必須是「這個 x
# 落在哪個欄位的管轄範圍內」（區間式），不能單純「離哪個欄位最近」
# ——07 課練習Ａ-1 的「フォーク」（多字詞槽位值的第二個片段，x=304.8）
# 離右邊的固定欄「で ごはんを 食べます。」（x=370.8，距離 66.0）其實
# 比離正確欄位「T」（はし欄，x=225.6，距離 79.2）更近，若改用最近欄位
# 會把它誤判成下一欄，錯誤地把兩個獨立欄位的內容混在一起（複審時实際
# 測出這個回歸，見下方 `_column_index`）。
#
# 但區間式比對也不能用固定的絕對容差（pt）——這是複審第二輪抓到的更
# 深層問題：欄位 x 的漂移幅度本身沒有一個安全的固定上限。已經實測到的
# 反例（全部是「候選詞真實 x 比參照欄位更靠左」的漂移）：
#   - 03 課「13,000えん」：漂移 6.6pt
#   - 08 課練習Ａ-1「おもしろい」：漂移 13.2pt
#   - 13 課練習Ａ-4「かいもの」：漂移 13.2pt
#   - 08 課練習Ａ-2「にぎやか」：漂移 13.8pt（這筆現在改用位置對應，
#     見 `_parse_one_table` 的 `len(cleaned) == len(base_columns)` 分
#     支，不再依賴這裡）
# 這些漂移幅度已經逼近、甚至超過本模組看過的最窄相鄰欄距（07 課練習
# Ａ-2「で」到「レポートを」26.4pt）的一半（13.2pt）——用固定容差
# （不論設多少）不可能同時滿足「大到能接住 13.8pt 的漂移」跟「小到不
# 會在 26.4pt 窄欄距裡誤跨欄」這兩個互斥的要求，第一輪選的 10.0pt 正
# 是卡在這兩者中間、遲早會被更大的反例打破的妥協值。
#
# 改用**相對於欄距本身的比例**決定何時跨欄，不是絕對 pt 數：欄位 i 到
# i+1 的欄距是 `gap = base_xs[i+1] - base_xs[目前欄位]`，只有當 x 大於
# 等於 `base_xs[i+1] - _COLUMN_CROSS_FRACTION * gap` 才跨欄。欄距窄時
# 允許的漂移量自動跟著變小，欄距寬時自動跟著變大——這正是「漂移量會不
# 會誤觸下一欄」這個問題本身的形狀，比任何固定常數都更貼近實際情況。
#
# 這個比例值必須同時滿足 5 個真實反例（4 個「必須跨欄」＋1 個「必須不
# 跨欄」，逐一代入 `base_xs[i+1] - f * gap` 這條公式反推 f 的上下限）：
#   - 08 課練習Ａ-1「おもしろい」必須跨欄：f >= 0.1386
#   - 13 課練習Ａ-4「かいもの」必須跨欄：f >= 0.0513
#   - 03 課練習Ａ-6「13,000えん」必須跨欄：f >= 0.0667
#   - 07 課練習Ａ-1「フォーク」必須**不**跨欄：f < 0.4545
#   - 10 課練習Ａ-4「エレベーターの まえ」的「まえ」必須**不**跨欄
#     （這一列的「まえ」若跨進下一欄，會把「エレベーターの まえ」這
#     個複合詞拆成兩截，跟基底句原本只是單一虛欄「に」的候選詞混在一
#     起，見 `_parse_one_table` 呼叫處的具體案例）：f < 0.2727
# 交集是 `0.1386 <= f < 0.2727`，取中段的 `0.2`（20%），兩側都留有安
# 全邊際（詳見 task-9-report.md 複審回合二的完整計算過程與逐一代入驗
# 算）。
_COLUMN_CROSS_FRACTION = 0.2

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


def _column_index(x: float, base_xs: List[float], fraction: float = None) -> int:
    """回傳 `x` 所屬的欄位索引。這是區間式歸屬（一旦進入某欄，同一欄
    內接下來的內容不論多寬都留在同一欄，直到真的越過下一欄的起點），
    不是單純的「離哪個欄位最近」（見模組說明「槽位偵測」）；但「要越
    過多遠才算真的跨欄」不是固定 pt 數，是相對於「目前欄位到下一欄」
    這段欄距本身的比例（見 `_COLUMN_CROSS_FRACTION` 說明）。

    `fraction` 預設用模組級的 `_COLUMN_CROSS_FRACTION`（給一般代入
    表、必須同時相容全部欄位間距差異懸殊的表格用）；
    `_parse_ms_te_reference_table` 這種已經是專用解析、只需要相容自己
    這一張表 4 個欄位間距的呼叫情境，可以傳入自己校準過的比例，不受
    全域常數的跨表相容性限制。"""
    f = _COLUMN_CROSS_FRACTION if fraction is None else fraction
    idx = 0
    for i in range(1, len(base_xs)):
        gap = base_xs[i] - base_xs[idx]
        threshold = base_xs[i] - f * gap if gap > 0 else base_xs[i]
        if x >= threshold:
            idx = i
    return idx


def _collapse_group(segs: List[Tuple[float, str]]) -> str:
    """把一個欄位收集到的 (x, 文字) 片段清單合併成一個字串（依原始
    x 序，用單一半形空白連接），見 `_redistribute_missing_slots` 與
    `_parse_one_table` 呼叫處。"""
    return _collapse_ws(" ".join(t for _x, t in segs))


def _redistribute_missing_slots(
    variant_rows: List[Dict[int, List[Tuple[float, str]]]],
    slot_idxs: List[int],
    base_xs: List[float],
) -> None:
    """複審第四輪抓到的回歸：單靠 `_column_index` 這種「只看單一欄位
    跨欄比例」的判斷，天生無法同時滿足所有真實反例——複審反推 13 課
    練習Ａ-2「はたらき」需要跨欄比例 >= 0.2857、14 課練習Ａ-5
    「べんきょうして」需要 >= 0.381、15 課練習Ａ-3「けっこんして」需
    要 >= 0.3，這三個下限全部超過 10 課練習Ａ-4「まえ」「必須不跨欄」
    的上限 < 0.2727——**不存在任何一個全域比例常數能同時滿足這批反
    例**，這不是校準不夠精，是單一比例常數的設計本身在這份語料上不
    完備。

    這幾個反例的共通點：句子讀起來剛好通順（`{S}{T}` 前後相接，其中
    一欄為空時句子恰好還讀得通），但欄位歸屬本身是錯的——用課本自己
    的網底框顏色核對過，`はたらき`／`べんきょうして`／`けっこんして`
    這三個詞真正屬於的欄位，都是**這張表已經由其他列證實存在、但這
    一列偵測不到值**的那個槽位，而不是它們被 `_column_index` 分到的
    那一欄。

    複審建議的修法：改用「表格整體結構」這個比單一列的 x 座標更強的
    訊號——若某欄已經透過**其他列**證實有自己的候選詞集合
    （`slot_idxs`，在呼叫這個函式之前就已經算好），但**這一列**偵測
    不到這個欄位的值，優先把這一列排在它前面、內容比較多的欄位裡的
    殘餘文字，重新分給這個缺值的欄位，而不是繼續相信 `_column_index`
    當初的判斷：

    - **這一列前面的欄位收了 2 個以上的片段**（13 課「外国で
      はたらき」、14 課「日本語を べんきょうして」都是這種情形）：
      把最後一個片段整個移到缺值的欄位，前面的欄位留下其餘片段。這是
      單欄裡「其實塞了兩欄內容」最直接的訊號——真正只有一欄內容的
      列，`_column_index` 不會意外多切出一個片段。
    - **這一列前面的欄位只有 1 個片段**（15 課「けっこんして」單獨一
      個片段，`_column_index` 誤判成 S）：改成比較這個片段的 x 到底
      離哪個欄位的基底句參照 x 更近——`_column_index` 判斷「是否跨
      欄」時只看與目前欄位的相對比例，沒有拿缺值欄位的參照位置直接
      比較距離；這裡改成直接比距離，離缺值欄位更近就整個移過去。

    這個函式**原地修改** `variant_rows`（每一列的 dict），不回傳新
    值——呼叫方在算完 `slot_idxs`之後、建立 `slots`／`rows` 之前呼
    叫一次即可。"""
    for row_groups in variant_rows:
        present = sorted(row_groups)
        for missing in slot_idxs:
            if missing in row_groups and row_groups[missing]:
                continue
            # 找這一列裡，排在缺值欄位「之前」、有內容的最近欄位。
            candidates = [i for i in present if i < missing and row_groups.get(i)]
            if not candidates:
                continue
            src = max(candidates)
            segs = row_groups[src]
            if len(segs) >= 2:
                row_groups[missing] = [segs[-1]]
                row_groups[src] = segs[:-1]
            else:
                (x, _text) = segs[0]
                if abs(x - base_xs[missing]) < abs(x - base_xs[src]):
                    row_groups[missing] = segs
                    row_groups[src] = []
            present = sorted(i for i in row_groups if row_groups.get(i))


def _reconstruct_question(
    base_texts: List[str],
    row_values: Dict[int, str],
    ellipsis_start_idx: Optional[int],
    slot_idxs: List[int],
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

    ## 一個疑問詞可能整體取代好幾個槽位（複審發現的第二個回歸，已修正）

    10 課練習Ａ-5 是兩個槽位：`S`（`えきの`／`ぎんこうの`／`はなやと`）
    緊接著 `T`（`ちかく`／`となり`／`スーパーの あいだ`），基底句是
    「本屋は{S}{T}に あります。」。疑問句變體整列只有「どこ」一個詞
    （落在 `S` 的欄位 x）＋省略號（落在 `に` 的欄位 x，`T` 欄本身完全
    沒有出現在這一列裡）。第一版實作對「沒有拿到候選詞的欄位」一律
    fallback 回基底句原文，`T` 欄因此照抄基底值「ちかく」，重建出
    「本屋はどこちかくにありますか。」——文法錯誤，`どこ` 後面多黏了
    一個不該存在的「ちかく」。

    真正的語意是：「どこ」不是只取代 `S`，而是取代「`S` 加 `T` 這整個
    複合片語」（「えきの ちかく」＝「車站附近」整組被問成「どこ」＝
    「哪裡」），`T` 欄根本不該再輸出任何文字。修正後的規則：**從第一
    個真的拿到候選詞的欄位開始，之後任何屬於槽位（`slot_idxs`）但這一
    列沒有提供候選詞的欄位，直接跳過、不印任何文字**（不是 fallback
    回基底值）——只有非槽位的固定欄位才會 fallback 回基底句原文（固
    定文字本來就不是被問的對象，理當照印）。用這個修正後的規則重算
    10 課練習Ａ-5，得到「本屋はどこにありますか。」——文法通順、語意
    正確。

    沒有任何驗收測試鎖定這個字串的精確內容（見模組說明），這裡誠實記
    錄：這個函式追求「語意正確」，已用多個實例（07 課 A1/A4/A5、10 課
    A5）交叉核對過，但沒有對全 15 課逐一驗證過每一種疑問句變體的排版
    變體。
    """
    if ellipsis_start_idx is None:
        return None
    slot_idx_set = set(slot_idxs)
    pieces: List[str] = []
    replacing = False
    for idx in range(ellipsis_start_idx):
        if idx in row_values:
            pieces.append(row_values[idx])
            replacing = True
        elif replacing and idx in slot_idx_set:
            continue  # 被前面的疑問詞整體取代，見上方說明，不印任何文字
        else:
            pieces.append(base_texts[idx])
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

    variant_rows: List[Dict[int, List[Tuple[float, str]]]] = []
    question_variant: Optional[str] = None
    question_ellipsis_idx: Optional[int] = None
    question_row_values: Dict[int, str] = {}

    in_sample_answer_block = False
    for line in lines[1:]:
        raw = "".join(f.text for f in line.frags)
        segments = _fine_segments(line)
        if not segments:
            continue

        if _SAMPLE_ANSWER_ROW_RE.match(raw) and not _QUESTION_VARIANT_RE.search(raw):
            # 見 `_SAMPLE_ANSWER_ROW_RE` 說明：示範答案列，整列排除，
            # 不計入槽位候選詞也不計入 `rows`。12 課練習Ａ-5 實測這個
            # 示範答案本身可能橫跨好幾列（第一列印「……サッカーの
            # ほうがおもしろいです。」，後面接著只印「ほん」「しごと」
            # ——沿用 `練習Ａ` 一貫的「只印有改變的部分」慣例，這次改
            # 的是示範答案，不是基底句），全部屬於同一個示範答案區
            # 塊。一旦看到這個標記，這張表接下來的所有列都視為這個區
            # 塊的延續，全部排除——全 15 課逐課掃描過，示範答案區塊
            # 一定出現在表格最後（真正的候選詞列一定先印完），還沒遇
            # 過這個區塊後面又接著真正候選詞列的反例。
            in_sample_answer_block = True
            continue
        if in_sample_answer_block:
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
                    # 見 `_TRAILING_BARE_ELLIPSIS_RE` 說明：先去掉這個
                    # 欄位文字尾端「沒有接か」的省略號（純裝飾，代表
                    # 「這一欄／這一欄的尾巴沿用基底句原文」），剩下的
                    # 才是真正的候選詞內容；若去掉後整段變空字串（欄位
                    # 裡原本就只有省略號），略過、不寫入 row_values，
                    # 讓 `_reconstruct_question` 自然 fallback 回基底句。
                    stripped = _TRAILING_BARE_ELLIPSIS_RE.sub("", text).strip()
                    if stripped:
                        row_values[idx] = _collapse_ws(
                            (row_values.get(idx, "") + " " + stripped).strip()
                        )
            question_row_values = row_values
            question_ellipsis_idx = ellipsis_idx
            continue

        # 「→」是課本在變化對照表（見 `_CONJUGATION_MARKER_TEXT`／
        # `table_type`）裡，對其中一列額外加印的裝飾用轉換箭頭（例如
        # 「たべます →たべましょう」），純粹是排版上的視覺提示，不是
        # 候選詞內容本身的一部分——全 15 課逐課掃描過，這個字元從未真
        # 正屬於任何一個候選詞（前後不是空白就是另一個候選詞邊界）。
        # 不濾掉的話，這個字元會原封不動混進候選詞字串。這裡的表都是
        # 一般代入表（變化對照表已在 `parse_pattern_tables` 分流到
        # `_parse_conjugation_table`，不會走到這裡），但字元清理規則
        # 沿用同一套、無條件套用不影響正確性。
        cleaned = [(x, text.replace("→", "").strip()) for x, text in segments]
        cleaned = [(x, text) for x, text in cleaned if text]

        # 一律依 x 座標區間歸屬（見 `_column_index`／`_COLUMN_CROSS_
        # FRACTION`），不再依「segment 數是否等於欄位數」切換成逐位置
        # 對應。複審第三輪發現：14 課練習Ａ-4「迎えに いき」（2 個
        # segment，跟這張表基底句的欄位數 2 剛好相等）曾經因為這個
        #「數量相符就依位置對應」的規則，被誤判成「這一列兩欄都各自
        # 給了新值」，把「いき」錯塞進「ましょうか。」那個其實從未被
        # 任何一列真正替換過的固定欄，產生「迎えにいき」這種丟掉語尾
        # 的殘句。這條規則原本是為了解決 08 課練習Ａ-2「にぎやか」欄
        # 位漂移 13.8pt 超出 `_COLUMN_CROSS_FRACTION` 涵蓋範圍的問
        # 題——但那張表本身就是變化對照表，已經改用 `_parse_
        # conjugation_table` 的獨立邏輯處理（不受這裡的容差限制），
        # 這裡不再需要這條特例，兩個真實反例（14 課「迎えに いき」該
        # 合併、08 課「にぎやか」該正確分流到別的函式）因此都不必再
        # 靠同一條規則硬撐。
        row_groups: Dict[int, List[Tuple[float, str]]] = {}
        for x, text in cleaned:
            idx = _column_index(x, base_xs) if base_xs else 0
            row_groups.setdefault(idx, []).append((x, text))
        variant_rows.append(row_groups)

    # 只有「真的出現過跟基底句不同的候選詞」的欄位才算槽位——07 課練
    # 習Ａ-6 每一列都重印了完全相同的「ました。」在同一欄（idx3），這
    # 欄位確實「被後續列碰到」了，但三列的值全部相同，不是真正的可替
    # 換槽位。若只憑「有沒有被任何列碰到」判定槽位，會產生一個候選詞
    # 清單裡三個值都一樣的假槽位，`template` 因此少展現這欄本來是固
    # 定文字的事實。改成「該欄位至少有一列的值跟基底句不同」才算數。
    #
    # 這一步必須在 `_reconstruct_question` 之前算好：疑問句變體重建需
    # 要知道哪些欄位是槽位（見該函式說明「一個疑問詞可能整體取代好幾
    # 個槽位」），才能正確判斷「這個沒拿到候選詞的欄位，是該印基底句
    # 原文的固定文字，還是該整個跳過的槽位」。
    slot_idxs = sorted({
        idx
        for row in variant_rows
        for idx in row
        if _collapse_group(row[idx]) != base_texts[idx]
    })
    if not slot_idxs and base_columns:
        # 防禦性後備：目前 15 課驗證過的資料裡，每張代入表至少都有一個
        # 真正的槽位（見模組說明），這個分支目前沒有真實案例觸發，只
        # 是避免「這張表萬一真的沒有替代候選詞」時 template 整個沒有
        # 任何 "{" 佔位符（會讓 test_template_has_placeholders 這類不
        # 變量失守，且下游代入練習完全無法使用）。退而求其次，把第一
        # 欄當成只有一個候選詞的槽位。
        slot_idxs = [0]

    _redistribute_missing_slots(variant_rows, slot_idxs, base_xs)

    if question_row_values or question_ellipsis_idx is not None:
        question_variant = _reconstruct_question(
            base_texts, question_row_values, question_ellipsis_idx, slot_idxs
        )

    slot_letters = {idx: _slot_letter(i) for i, idx in enumerate(slot_idxs)}
    slots: Dict[str, List[str]] = {slot_letters[idx]: [base_texts[idx]] for idx in slot_idxs}
    rows: List[List[int]] = [[0] * len(slot_idxs)]

    for row_groups in variant_rows:
        if not any(idx in row_groups and row_groups[idx] for idx in slot_idxs):
            continue
        row_indices = []
        for idx in slot_idxs:
            letter = slot_letters[idx]
            if idx in row_groups and row_groups[idx]:
                slots[letter].append(_collapse_group(row_groups[idx]))
                row_indices.append(len(slots[letter]) - 1)
            else:
                # 這一列沒有提供這個槽位的新候選詞（`_redistribute_
                # missing_slots` 已經先嘗試把前面欄位的殘餘文字重新分
                # 配過，這裡走到 else 分支代表真的沒有可分配的來源）
                # ——用空字串當這一列的值，不是沿用前一列的索引。
                #
                # 複審第二輪抓到的真實反例（13 課練習Ａ-4）：課本這一
                # 列本身只印了「かいもの」一個詞，用課本頁面算繪核對
                # 過，這一列在 S 欄（神戸へ／ロシア料理を）對應的位置
                # 是**空白網底框**，「かいもの」整個落在 T 欄——這一列
                # 的 S 本來就沒有替代詞，不是「沿用上一列的 S」。第一
                # 版的「沿用前一列索引」fallback 會把上一列的
                # 「ロシア料理を」誤接到這一列的「かいもの」前面，產生
                # 「わたしはロシア料理をかいものに行きます。」這種混
                # 合兩列內容的病句；改成空字串後正確產生
                # 「わたしはかいものに行きます。」。
                #
                # 這裡優先重用已存在的空字串候選（避免每次都新增一個
                # 內容相同的候選詞），不存在才新增。
                if "" in slots[letter]:
                    row_indices.append(slots[letter].index(""))
                else:
                    slots[letter].append("")
                    row_indices.append(len(slots[letter]) - 1)
        rows.append(row_indices)

    template = "".join(
        "{%s}" % slot_letters[idx] if idx in slot_letters else base_texts[idx]
        for idx in range(len(base_texts))
    )

    result: Dict = {
        "id": "L%02d-A%d" % (lesson, table_no),
        "table_type": "substitution",
        "template": template,
        "slots": slots,
        "rows": rows,
        "requires_lesson": lesson,
        "question_variant": question_variant,
    }
    return result


# 變化對照表判定用的助詞白名單——這些字元本來就常常在正常句子裡合法
# 重複兩次以上（「AとBとどちらが」比較句型、「XからYまで」範圍句
# 型），出現在基底句欄位裡不代表這張表是變化對照表（見
# `_find_conjugation_marker` 說明；12 課練習Ａ-5「サッカーとやきゅう
# と」就是這樣的真實反例，`と` 重複但這張表是正常代入表）。
#
# **複審第四輪抓到的臭蟲**：這個清單原本也排除「か」「の」，理由是
# 「常見助詞」，但沒有實測驗證——14 課練習Ａ-1（動詞ます形／て形總
# 表）裡，「か」是「書きます／書いて」的動詞語幹、「の」是「飲みます
# ／飲んで」的動詞語幹，不是助詞。把它們排除會讓 `_find_conjugation_
# marker` 對這些列的重複語幹視而不見，導致這些列在「同一個 segment
# 數多數決」的分界演算法裡完全解析不出分界，整列從 `forms` 消失（複審
# 實測：11 個資料列裡至少 5 列因此被靜默丟棄）。這裡拿掉「か」「の」
# ——這張表現在改用專門的 `_parse_ms_te_reference_table`（見該函式說
# 明）處理，不再依賴這份清單，但清單本身也不該包含沒有實測依據、還會
# 誤傷合法語幹的項目，一併修正。
_CONJUGATION_EXCLUDED_REPEATS = frozenset(
    ["は", "が", "を", "に", "で", "と", "も", "へ", "から", "まで", "や", "、"]
)


def _find_conjugation_marker(base_texts: List[str]) -> Optional[str]:
    """判定這張表是不是「變化對照表」（見模組說明「變化對照表：跟代
    入表版面相同、語意結構完全不同」）：回傳基底句欄位裡第一個「重複
    出現、且不是純助詞」的文字，找不到則回傳 `None`。

    這個文字若存在，就是這張表每一列的「起始標記」——變化對照表的基
    底句本身就是好幾組「詞幹＋語尾」黏在一起（例如 07 課「たべます
    たべましょう」：`たべ` 沒有重複、但很多其他變化對照表的詞幹會直
    接重複兩次以上，見下方函式呼叫處的具體案例），不是一個真正的句
    子。全 15 課、78 張表逐一用「基底句欄位裡是否有重複且非助詞的文
    字」掃描過，精確找出 7 張這種表（`L04-A7`／`L06-A5`／`L08-A2`／
    `L12-A2`／`L12-A3`／`L13-A3`／`L14-A1`），沒有誤判任何一張正常代
    入表（`L12-A5` 的基底句雖然也有重複文字「と」，但那是比較句型的
    助詞，已經用 `_CONJUGATION_EXCLUDED_REPEATS` 排除）。

    **重複必須間隔至少 2 個欄位才算數**（`i - seen[t] >= 2`）：08 課
    練習Ａ-2 有一列本身是「い い です よ くない です」（形容詞
    「いい」本身兩個字重複，不是「正／負形態各自的起始標記」重複）
    ——「い」緊接著自己重複一次，這是這個形容詞單字本身的拼寫，不是
    形態組的分界，若不排除，會把「い」誤判成這一列的分界標記，切出
    「いですよくない」「です」這種錯誤分組。要求間隔至少 2 欄，能正
    確跳過這種「同一個詞自己疊字」的情形，繼續找到真正代表「正／負形
    態」分界的重複（這一列本身其實找不到——「いい／よくない」是不規
    則形容詞，兩個形態沒有共用字根，見 `_parse_conjugation_table` 說
    明「同一個 segment 數的所有列用多數決決定分界」如何處理這個殘留
    案例）。
    """
    seen_at: Dict[str, int] = {}
    for i, t in enumerate(base_texts):
        if t in _CONJUGATION_EXCLUDED_REPEATS:
            continue
        if t in seen_at and i - seen_at[t] >= 2:
            return t
        seen_at[t] = i
    return None


def _row_group_starts(texts: List[str]) -> Optional[List[int]]:
    """對單一列（已清乾淨的欄位文字清單）用 `_find_conjugation_marker`
    找出形態組的起始欄位索引清單（恆以 0 開頭）。找不到重複標記則回
    傳 `None`（見 `_parse_conjugation_table` 說明「同一個 segment 數的
    所有列用多數決決定分界」，這種情形交給呼叫方處理，不在這裡猜
    測）。"""
    marker = _find_conjugation_marker(texts)
    if marker is None:
        return None
    starts = [i for i, t in enumerate(texts) if t == marker]
    if not starts or starts[0] != 0:
        starts = [0] + starts
    return starts


def _parse_conjugation_table(lesson: int, table_no: int, lines: List[Line], marker: str) -> Dict:
    """解析變化對照表（見模組說明「變化對照表」）。

    每一列本身就是好幾組「詞幹＋語尾」黏在一起，不是單一句子加槽位。
    每一列各自用 `_row_group_starts`（`_find_conjugation_marker` 的邏
    輯）找出「這一列自己的形態組從哪裡開始」——這是位置對應（不是
    `_column_index` 的 x 座標區間比對），因為變化對照表每一列本來就
    是「每一欄都對應著印」，不會有「只替換部分欄位」的情形（跟一般代
    入表的核心差異）。

    ## 同一個 segment 數的所有列用多數決決定分界，不是各自為政

    08 課練習Ａ-2「い い です よ くない です」（形容詞「いい」＝
    「好」，不規則形容詞，正／負形態「いい」／「よくない」沒有共用字
    根）——這一列自己用 `_row_group_starts` 解析，剛好會湊巧選到
    「です」當分界標記（`です` 在這一列裡出現兩次、間隔剛好 >= 2，滿
    足 `_find_conjugation_marker` 的條件），切出「いいです」「よくな
    い」「です」三段——**這個自我解析的結果本身是錯的**（正確應該是
    兩段：「いいです」「よくないです」），因為這一列的兩個形態本來就
    沒有共用字根可以正確標記分界，任何找到的「重複文字」都只是巧合。

    但這一列的 segment 數（6 個）跟同一張表另外兩列（「たか い です
    たか くない です」「おいし い です おいし くない です」，兩者都
    正確解析出「正／負形態各 3 欄」）完全相同——**同一張表裡 segment
    數相同的列，形態組的欄位切法理應相同**（都是「い形容詞肯定形／
    否定形」這個固定版面，只是詞幹不同）。因此不採用「每一列各自的解
    析結果」，改成**同一個 segment 數的所有列一起多數決**：這裡
    `[0, 3]`（たか／おいし 兩票）勝過「いい」這一列自己解析出的
    `[0, 2, 5]`（一票），全部 3 列統一套用多數決選出的 `[0, 3]`，「い
    い」這一列因此也能正確切成兩段。

    若某個 segment 數在整張表裡完全沒有任何一列能解析出分界（目前 15
    課資料沒有這種案例），這一列會被跳過、不計入 `forms`——寧可少一
    列資料，也不要瞎猜一個可能錯誤的切法。

    回傳 `{"id", "table_type": "conjugation", "requires_lesson",
    "forms"}`——`forms` 是每一列一組的形態清單（例如 06 課練習Ａ-5
    第一列是 `["やすみます", "やすみましょう"]`）。沒有
    `template`／`slots`／`rows`／`question_variant`：這些欄位對變化
    對照表沒有意義，刻意留白（設為 `None`），避免下游把它當一般代入
    表呼叫 `template.format(**slots)`。
    """
    base_line = lines[0]
    base_texts = [t for _, t in _fine_segments(base_line)[1:]]

    all_rows_texts: List[List[str]] = [base_texts]
    for line in lines[1:]:
        raw = "".join(f.text for f in line.frags)
        cleaned_texts = [t.replace("→", "").strip() for _x, t in _fine_segments(line)]
        cleaned_texts = [t for t in cleaned_texts if t]
        if not cleaned_texts:
            continue
        if _QUESTION_VARIANT_RE.search(raw) or _SAMPLE_ANSWER_ROW_RE.match(raw):
            # 變化對照表目前 15 課實測從未出現疑問句變體或示範答案區
            # 塊（這兩種都是一般代入表的慣例），這裡防禦性排除、不計
            # 入 `forms`，避免萬一真的出現時混入垃圾資料。
            continue
        all_rows_texts.append(cleaned_texts)

    # 第一輪：每一列各自嘗試解析分界。同一個 segment 數的所有列，理應
    # 共用同一種切法（同一種版面，只是詞幹不同）——用**多數決**選出
    # 每個 segment 數最常見的分界（不是「誰先解析出來就用誰」）：08
    # 課練習Ａ-2「いい／よくない」那一列自己解析出的分界（`です` 兩次
    # 出現，湊巧間隔也 >= 2）剛好是錯的（`いい`／`よくない` 是不規則
    # 形容詞，正負形態不共用字根，見 `_find_conjugation_marker` 說
    # 明），但跟它 segment 數相同的另外兩列（`たか`／`おいし`）都正確
    # 解析出「各 3 欄」的分界，多數決會蓋掉這一列自己的錯誤答案，改用
    # 兩票對一票勝出的正確分界。
    resolved = [_row_group_starts(texts) for texts in all_rows_texts]
    votes_by_count: Dict[int, Counter] = {}
    for texts, starts in zip(all_rows_texts, resolved):
        if starts is not None:
            votes_by_count.setdefault(len(texts), Counter())[tuple(starts)] += 1
    majority_by_count = {
        count: max(votes.items(), key=lambda kv: kv[1])[0]
        for count, votes in votes_by_count.items()
    }

    forms: List[List[str]] = []
    for texts in all_rows_texts:
        starts = majority_by_count.get(len(texts))
        if starts is None:
            continue  # 見模組說明：整個 segment 數都解析不出分界，跳過
        forms.append([
            "".join(texts[s:(starts[i + 1] if i + 1 < len(starts) else len(texts))])
            for i, s in enumerate(starts)
        ])

    return {
        "id": "L%02d-A%d" % (lesson, table_no),
        "table_type": "conjugation",
        "requires_lesson": lesson,
        "template": None,
        "slots": None,
        "rows": None,
        "question_variant": None,
        "forms": forms,
    }


def _parse_ms_te_reference_table(lesson: int, table_no: int, lines: List[Line]) -> Dict:
    """14 課練習Ａ-1 專用解析：動詞ます形／て形總表（Ⅰ／Ⅱ／Ⅲ類全
    表）。複審第四輪指出這張表根本不是「一列一組形態」的版面，是
    **一列同時橫跨兩個動詞**（左半一個動詞的 ます形／て形、右半另一
    個動詞的 ます形／て形，並排省版面），套用 `_find_conjugation_
    marker` 那種「同一個 segment 數多數決切兩段」的邏輯，會把兩個不
    相干動詞的形態接在一起（例如「いき ます」跟「＊いっ てね ます
    ねて」黏成一段），或因為動詞語幹（「か」「の」）被舊版的助詞白名
    單誤判排除而整列消失。

    這裡改用基底句（表頭列）自己印出的欄位 x 座標當四個欄位的參照位
    置——表頭列文字是「ます形　て形　ます形　て形」（左半動詞的
    ます形／て形標籤，右半另一個動詞的 ます形／て形標籤），共 4 個
    概念欄位（「て形」因表頭本身的字距排版，可能被 `_fine_segments`
    拆成 `て`／`形` 兩個 segment，這裡只取每個標籤的第一個 segment 當
    參照 x，足夠定義四個欄位的邊界）。每個資料列先濾掉「Ⅰ」「Ⅱ」
    「Ⅲ」這種純動詞分類標籤（不是形態內容本身，見
    `_GROUP_LABEL_MARKERS`），再用 `_column_index`（跟一般代入表共用
    同一套「相對欄距比例」判斷）把剩下的 segment 分進四個欄位，左半
    兩欄湊成一組「(ます形, て形)」、右半兩欄湊成另一組，兩組都非空才
    算數（有些列只有右半有內容——這是課本真實排版：左邊 Ⅰ 類動詞的
    例子比右邊少，列到後面左半自然空白，不是資料遺漏）。"""
    header_segments = _fine_segments(lines[0])[1:]
    # 表頭「て形」有時（本身排版用字距撐開)被 `_fine_segments` 拆成
    # 「て」／「形」兩個 segment（見上方模組說明），逐一併相鄰 segment
    # 湊字看是否構成「ます形」或「て形」，取這個標籤第一個 segment 的
    # x 當這一欄的參照位置。
    col_xs: List[float] = []
    i = 0
    while i < len(header_segments) and len(col_xs) < 4:
        x, t = header_segments[i]
        stripped = t.replace(" ", "")
        if stripped in ("ます形", "て形"):
            col_xs.append(x)
            i += 1
            continue
        if i + 1 < len(header_segments):
            x2, t2 = header_segments[i + 1]
            if (stripped + t2.replace(" ", "")) in ("ます形", "て形"):
                col_xs.append(x)
                i += 2
                continue
        i += 1

    forms: List[List[str]] = []
    if len(col_xs) == 4:
        for line in lines[1:]:
            cleaned = [
                (x, t) for x, t in _fine_segments(line) if t not in _GROUP_LABEL_MARKERS
            ]
            if not cleaned:
                continue
            groups: Dict[int, List[str]] = {}
            for x, t in cleaned:
                # 這張表左右兩欄組（colA/colB、colC/colD）之間的欄距
                # 105.6~118.8pt，遠比其中一欄內部（詞幹 segment 到
                # 「ます」／「て」語尾 segment 之間）常見的間距寬鬆很
                # 多；但個別動詞語幹（單一假名，例如「い」「かえ」）
                # 偶爾會印在欄位邊界附近，用跟一般代入表共用的
                # `_COLUMN_CROSS_FRACTION`（為了同時相容 07 課「フォー
                # ク」等窄欄距表格而校準得比較保守）會讓這些語幹跨欄失
                # 敗，把左欄的「て形」語幹誤留在「ます形」欄裡（複審實
                # 測「＊い」「いそ」「かえ」都曾經卡在這個門檻差幾 pt
                # 跨不過去）。這裡改用 0.25——只需要相容這張表自己 4
                # 個欄位間的距離，不必兼顧其他表格，用實際量出的邊界
                # 案例（差 5.28pt 沒跨過）反推得出。
                groups.setdefault(_column_index(x, col_xs, fraction=0.25), []).append(t)

            def _joined(idx: int) -> str:
                return "".join(tok.replace(" ", "") for tok in groups.get(idx, []))

            left = (_joined(0), _joined(1))
            right = (_joined(2), _joined(3))
            # 表格中途重印一次表頭列本身（「ます形」／「て形」字面重
            # 複出現在資料列的右半，見模組說明）——這是裝飾用的分隔提
            # 示，不是真正的動詞形態，過濾掉不計入 `forms`。
            if left[0] and left[1] and left not in (("ます形", "て形"),):
                forms.append([left[0], left[1]])
            if right[0] and right[1] and right not in (("ます形", "て形"),):
                forms.append([right[0], right[1]])

    return {
        "id": "L%02d-A%d" % (lesson, table_no),
        "table_type": "conjugation",
        "requires_lesson": lesson,
        "template": None,
        "slots": None,
        "rows": None,
        "question_variant": None,
        "forms": forms,
    }


# 14 課練習Ａ-1 表頭列的動詞分類標籤——不是形態內容本身，見
# `_parse_ms_te_reference_table` 說明，解析資料列時要先濾掉。
_GROUP_LABEL_MARKERS = frozenset(["Ⅰ", "Ⅱ", "Ⅲ"])


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
        table_lines = lines[start:end]
        if lesson == 14 and table_no == 1:
            # 見 `_parse_ms_te_reference_table` 說明：這張表是「一列橫
            # 跨兩個動詞」的特殊版面，一般的「同一個 segment 數多數決」
            # 分界演算法（`_parse_conjugation_table`）對它結構性地不適
            # 用，改用專用解析。
            tables.append(_parse_ms_te_reference_table(lesson, table_no, table_lines))
            continue
        base_texts = [t for _, t in _fine_segments(table_lines[0])[1:]]
        marker = _find_conjugation_marker(base_texts)
        if marker is not None:
            tables.append(_parse_conjugation_table(lesson, table_no, table_lines, marker))
        else:
            tables.append(_parse_one_table(lesson, table_no, table_lines))
    return tables


# ---------------------------------------------------------------------------
# 練習Ｂ：變換題
# ---------------------------------------------------------------------------

# 例句範例標籤：「例：」「例１：」「例 ：」等（見模組說明「例 前導區
# 塊」），全形／半形冒號皆接受，數字與冒號前後容許空白。
_EXAMPLE_RE = re.compile(r"例\s*\d*\s*[:：]")

# 多範例（例１／例２）串接分隔符（見模組說明「例 前導區塊」）。**不能
# 用全形斜線「／」**——複審後新增的獨立檢查（比對「cue 是否落在正確欄
# 位」，見 task-9-report.md）發現 08 課練習Ｂ-5 的 cue 本身就真的包含
# 全形斜線（課本原文「花を 買いました／きれい」，斜線是課本用來連接
# 「做了什麼」跟「什麼樣的」兩個真實片語的標點，不是本模組加的分隔
# 符）——如果拿同一個字元當多範例分隔符，`model_cue.split("／")` 會把
# 這種單一 cue 誤切成兩截，讓下游完全無法正確還原「這一題有幾組範
# 例」。改用「｜」（全形直線，U+FF5C）：全 15 課練習Ｂ 逐字掃描過，這
# 個字元從未出現在任何課本原文內容裡，不會跟真實 cue／answer 內容衝
# 突。
_MULTI_EXAMPLE_SEP = "｜"

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


# fragment 邊界標記，插在每個 fragment 的原始文字之間（見 `_line_
# tokens`／`_parse_one_drill` 說明「cue／answer 分界：以 fragment 邊界
# 為準，不是以「→」字元在字串裡的位置為準」）。選 `\x00`：不是任何合
# 法字元編碼會解碼出來的字元（`fonts.decode_hex` 的目標字元集不含
# NUL），不會跟課本真實內容混淆，之後也一定會在比對／輸出前整個移除。
_FRAGMENT_SENTINEL = "\x00"


def _line_tokens(line: Line) -> List[str]:
    """把一行拆成逐 fragment 的原始文字清單（依 `line.frags` 既有 x
    序，不套用任何插入規則，跟 `_naive_concat` 用同一套資料來源）。若
    這一行整行文字（見模組說明「…… 延續行」）以「……」開頭，把這個續
    行標記從**跨 fragment 的前綴**移除。

    標記不保證落在第一個 fragment：10 課練習Ｂ-3 的續行是兩個
    fragment `'   '`（純空白，courseware 排版留白）與
    `'……かばんが  あります。'`（標記跟真正內容融合在同一個 fragment
    裡）——標記其實在**第二個** fragment 的開頭。複審抓到這個案例：
    第一版只檢查、移除第一個 fragment 的前導標記，這一行的空白
    fragment 沒有標記可移除，真正帶標記的第二個 fragment完全沒被處
    理，導致「……」原封不動留在 `model_answer` 裡（`L10-B3`／
    `L11-B2` 皆受影響）。

    修正：用 `_CONTINUATION_RE.match` 量出整行文字開頭要移除幾個字
    元，再依序從每個 fragment 的開頭扣掉這個長度（可能跨過好幾個
    fragment，例如這裡先扣光第一個純空白 fragment，再繼續扣進第二個
    fragment 內部），確保不論標記落在第幾個 fragment，或是不是跟純空
    白 fragment 混在一起，都能正確移除。"""
    tokens = [f.text for f in line.frags]
    match = _CONTINUATION_RE.match(_naive_concat(line))
    if not match:
        return tokens
    remaining = match.end()
    out: List[str] = []
    for t in tokens:
        if remaining <= 0:
            out.append(t)
        elif remaining >= len(t):
            remaining -= len(t)
            out.append("")
        else:
            out.append(t[remaining:])
            remaining = 0
    return out


def _split_cue_answer(chunk: str) -> Tuple[str, str]:
    """把一個「例」範例的內容（`_FRAGMENT_SENTINEL` 分隔的逐 fragment
    片段）切成 `(cue, answer)`。

    **cue／answer 分界：以 fragment 邊界為準，不是以「→」字元在字串
    裡的位置為準**——複審抓到的臭蟲根因：原本的實作把整段前導文字先
    串成一個字串，再用 `str.partition("→")` 找箭頭切 cue／answer。這
    在課本排版把箭頭放在 cue 跟 answer 之間時（例如 07 課練習Ｂ-1
    「ごはんを 食べます → はしで ごはんを 食べます。」）碰巧是對的，
    但至少兩種排版變體會讓它失效：

    1. **答案完全沒有箭頭**（06 課練習Ｂ-7「いっしょに 京都へ 行きま
       せんか。」下一行「……ええ、行きましょう。」，這裡沒有任何
       「→」）——`partition` 找不到分隔符，整段文字全部落入 cue，
       answer 變空字串。
    2. **箭頭印在 cue 與「示範問句」都結束之後，而不是兩者之間**（14
       課練習Ｂ-7「カリナさんは 何を かいて いますか。」跟「花を か
       いて います。」是**兩個各自獨立的 fragment**，「→」是緊接在
       第二個 fragment 後面的**第三個** fragment，不是夾在兩者中
       間；10 課練習Ｂ-3、11 課練習Ｂ-2、13 課練習Ｂ-4、14 課練習
       Ｂ-4 都是同一種版面）——用字串位置切，會把「示範問句」整段
       併入 cue，answer 只剩箭頭後面的殘餘空白，變成空字串。

    這兩種情形的共通點：**cue 永遠就是「例：」標籤後面那一個
    fragment 自己的內容**（課本排版上，cue 詞／片語跟緊接在後的示範
    句／答案句一定是不同的 fragment，即使兩者之間完全沒有箭頭、或箭
    頭被印到後面去了）。因此改成：先依 fragment 邊界（用
    `_FRAGMENT_SENTINEL` 保留下來）取得「例：」後的第一個 fragment
    當 cue；「→」字元本身只當作視覺雜訊整個移除，不再用它的字串位置
    做任何切分。

    **完全沒有箭頭時，cue 視為空字串，整段內容都算 answer**——跟課本
    排版習慣一致（沒有可代換的「cue 詞」時，這一題本來就是「示範問句
    ＋示範答案」的完整組合，例如 07 課練習Ｂ-2「例：→ これは 日本語
    で 何ですか。」原本就已經是 cue="" 的處理方式，這裡只是把它推廣
    到「連箭頭都沒有」的情形）。"""
    tokens = chunk.split(_FRAGMENT_SENTINEL)
    if "→" not in chunk:
        return "", _collapse_ws(" ".join(tokens))
    head = tokens[0]
    if "→" in head:
        # 防禦性分支：全 15 課實測「→」從未跟其他非空白文字融合在同一
        # 個 fragment 裡（只跟裝飾用的全形/半形空白融合過），這裡沒有
        # 真實案例觸發，只是避免萬一真的發生時，cue 被誤含箭頭字元。
        cue_part, _, remainder = head.partition("→")
        rest = [remainder] + tokens[1:]
    else:
        cue_part = head
        rest = tokens[1:]
    answer = _collapse_ws(" ".join(rest).replace("→", ""))
    return _collapse_ws(cue_part), answer


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

    preamble_tokens: List[str] = []
    for ln in preamble_lines:
        preamble_tokens.extend(_line_tokens(ln))
    preamble_text = _FRAGMENT_SENTINEL.join(preamble_tokens)
    examples = _EXAMPLE_RE.split(preamble_text)[1:]  # [0] 是題號本身，丟棄

    cues: List[str] = []
    answers: List[str] = []
    for chunk in examples:
        cue, answer = _split_cue_answer(chunk)
        cues.append(cue)
        answers.append(answer)

    model_cue = _MULTI_EXAMPLE_SEP.join(cues) if cues else ""
    model_answer = _MULTI_EXAMPLE_SEP.join(answers) if answers else ""

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
