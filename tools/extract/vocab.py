"""單字表（ことば）解析：把 `Section`（Task 6）的 `Line` 序列切成一筆筆
單字紀錄 `{"no", "kana", "kanji", "zh", "usage", "group", "supplementary"}`。

這是整條抽取管線最核心的資料——單字練習、漢字→假名讀音練習、中日對照
全部建立在這裡的輸出上，實測見 `task-7-report.md`。

## 動詞分類記號（group）：課本從第 14 課開始標，動詞變化練習需要它

課本從第 14 課開始，在假名欄後面用羅馬數字標註動詞分類（Ⅰ／Ⅱ／Ⅲ
類，例如「つけます Ⅱ」「けします Ⅰ消します」）。這是變化引擎推導て
形、ない形等變化規則的必要資訊（本題庫使用者需求「動詞變化練習」的
前提），課本既然已經標好，`_extract_group` 把它從假名欄抽成獨立的
`group` 欄位（值為 `"I"`／`"II"`／`"III"`／`None`），不留在 `kana`
裡當雜訊。第 1~13 課沒有這個標記，`group` 一律是 `None`，這是正常的
（見 `task-7-report.md` 的全課統計）。

## 版面：每筆單字一行，欄位依 x 座標由左至右為「編號、假名、漢字（可能
缺席）、中文」，行號標籤格式通常是 `N.`（可能有前導全形/半形空白）。

**欄位 x 座標每一課不同**（07 課 53.4/219.0/384.6、13 課
51.6/210.0/368.4，見任務簡報），不可寫死；本模組先對整個 Section 掃描
一次，用「固定版面欄位的 x 在同一課會被精確重複使用很多次」這個實測
規律（`_learn_layout`）學出這一課的假名欄 x、漢字欄 x、中文欄名目起
點，再對每一行套用**狀態機**（`_split_data_cells`）逐一 Cell 判定歸
屬，而不是單純比對相鄰 Cell 間距。

### 為什麼不能只看相鄰 Cell 的間距（曾經試過、會誤判）

第一版實作用「相鄰 Cell 間距 >= 100pt 視為換欄」，在 07 課（單字幾乎
都很短）看起來正確，但對全 15 課逐課核對後發現會在兩個方向上誤判：

1. **假名/漢字欄本身因標點被 `cells()` 額外切開時，欄內縫隙可能跟真
   正換欄的間距量級重疊**——02 課第 45 筆「［どうも］ ありがとう
   ［ございます］。 （非常）謝謝你。」，假名／中文之間真正的換欄間
   距只有 87pt（比欄內縫隙的上限 92.4pt 還小！），相鄰間距門檻不管
   設多少都無法同時涵蓋兩者。09 課第 3～6、40 筆「好き［な］」「早
   く、速く」這類漢字欄本身有兩個 Cell（`219.0` 與 `258.6`，中間縫
   隙 39.6pt），若只看間距，中文欄的起點（`384.6`）跟漢字欄第二個
   Cell 的間距（126pt）又會被誤判成另一次換欄，導致「な］」「速く」
   被錯誤歸類到中文欄。
2. 04 課「  104電話查號台」——`■会話` 小框裡真正的詞彙「104」（電話
   查號台的號碼）被行號正則誤判成第 104 筆單字（見下方「行號防呆」）。

**改用「絕對位置 + 狀態機」解決第 1 類問題**：先用全 Section 統計學出
這一課的漢字欄 x（`kanji_x`，容差 `_KANJI_TOL`）與中文欄地板
（`zh_floor` = 學出的中文欄名目起點 − `_ZH_MARGIN`，見下方「中文欄
名目起點與抖動」），再對每一行的資料 Cell **依序**維護「目前在哪一
欄」的狀態：從假名欄出發，只有 Cell x 精確貼近 `kanji_x` 才會切換到
漢字欄，只有 Cell x 落在 `zh_floor` 之後才會切換到中文欄；**已經進入
某一欄之後，同一欄內部後續的 Cell（不論間距多大）一律留在同一欄，直
到真的越過下一個欄位邊界**。這樣 09 課「な］」「速く」因為還沒越過
`zh_floor`，正確留在漢字欄；02 課第 45 筆全程沒有 Cell 貼近
`kanji_x`，直到 `370.8`（越過 `zh_floor`）才換欄，正確只切出假名／中
文兩欄。

### 中文欄名目起點與抖動

中文欄名目起點（如 07 課 384.6）在**中文釋義前面剛好接一個全形空白**
時會左移一個全形字寬（07 課第 9、33、34 筆等落在 370.8）。`_learn_
layout` 用「出現次數 >= `_MIN_COLUMN_HITS`」篩出兩個夠遠的高頻叢
集，取較小的當 `zh_ref`（這已經是抖動後的較低值，比名目起點更安全），
再扣掉 `_ZH_MARGIN` 當最終地板，双重保險。

## 行號防呆：只承認「跟預期序號完全銜接」的行號

04 課 `ことば` 頁尾附的「本課會話用語」小框裡有一筆詞彙本身就是「104」
（電話查號台號碼，`■会話` 開頭、不屬於主要單字列表），若行號正則只看
「開頭是數字」，會被誤判成第 104 筆單字（主列表其實只有 50 筆）。單
字表的編號規則是**嚴格從 1 開始、每筆遞增 1**，因此 `parse_vocab`
維護一個 `expected` 計數器，只有行首數字**精確等於**目前預期的下一個
編號才承認是新單字列的開頭；不匹配的一律當成普通內容行處理（可能被
`_is_usage_subline` 收編，否則被忽略）。

**行號句點是可選的**：算繪 10.pdf 第 1 頁核對過，第 15 筆單字原書就印
成「15　スイッチ」（沒有句點，前後 14、16 兩筆都有句點）——這是課本
本身排版不一致，不是抽取管線的缺陷。若句點寫死必要，這一筆會被靜默
漏收，且不會被行號防呆機制擋下（因為它的數字本身仍然正確銜接
14→15→16）。

## 緊排單字（如 07 課第 10 筆「て」/「手」）

同一 Cell 內假名漢字靠字距撐開，沒有觸發任何欄位切換（狀態機全程停在
假名欄）。此時在假名欄文字裡找**第一個 CJK 表意文字**
（`一`-`鿿` / `㐀`-`䶿`）當切點，切點前是假名、切點（含）之後是漢字。
片假名（セロテープ這類）不含表意文字，不會被誤切。

## usage 子行：搭配用法不可遺失

07 課第 9 筆「かけます」單獨沒有意義，課本教的是「電話を　かけます」，
下方印著一行 `［でんわを～］　［電話を～］`（沒有行號、跟上一筆的假名
欄 x 對齊）。判定「是否為前一筆的 usage 子行」需同時滿足：

1. 該行**沒有**行號前綴（不匹配預期序號）。
2. 該行第一個 Cell 的 x 與這一課的假名欄 x 在 `_CONT_ALIGN_TOL` 內對齊。
3. 該行文字含 `［` 或 `〔`。

三者缺一都不算——07 課 ことば 頁尾附有一個「本課會話用語」小框（`■会
話` 開頭），裡面的內容 x 起點不對齊（25.8 vs 假名欄 53.4）、也有一行
含 `〔` 但 x 起點也不對齊（12.0），兩個條件都會擋下它，不會被誤判成
單字的 usage 子行。usage 子行內部改用「相鄰 Cell 最大縫隙」把假名／
漢字兩段切開（`_split_usage_cells`；不是貼近學出來的 `kanji_x`——子行
的漢字用法欄開頭印著「［」，這個前導方括號造成的抖動常常超出
`_KANJI_TOL`，15 課甚至完全學不出 `kanji_x`，兩種情形都會讓「貼近
`kanji_x`」的作法漏判），並把外層 `［］`／`〔〕` 去掉，符合任務簡報
介面說明的 `{"kana": "でんわを～", "kanji": "電話を～"}` 形狀。

### usage 子行對齊容差過嚴（複審修正）

第一版用 `_ALIGN_TOL=3.0` 判斷 usage 子行是否對齊假名欄——但子行開頭的方括號本身會讓整
欄往左抖動，跟中文欄名目起點會抖動是同一種成因（前面剛好接一個全形
空白或方括號時，整段內容的錨點左移一個全形字寬，實測 13.2~13.8pt）。
複審對全 15 課逐課掃描，找到 11.pdf 第 33、35 筆、13.pdf 第 5、6、7、
11 筆、14.pdf 第 8、15、17 筆共 **9 筆** usage 子行因為 3.0pt 容差過
嚴被誤判成「不是子行」而整行遺失（其中 14/8、14/15、14/17 剛好也是
本任務 Task 7 複審修正過 `kanji`/`zh` 欄位的那批單字——同一筆的
`kanji`/`zh` 修好了，`usage` 卻還是漏的，因為兩者是完全不同的程式碼
路徑）。改用 `_CONT_ALIGN_TOL=16.0`（遠大於實測抖動上限 13.8pt、遠
小於假名欄到漢字欄的真正欄距 150pt+）後，這 9 筆全部正確收錄。

## 續行不可遺失：純中文續行與替代讀音／註解續行

usage 子行只涵蓋「方括號搭配用法」這一種續行；複審進一步發現另外兩
種續行也會被完全忽略，導致中文釋義被截斷在句子中間：

1. **純中文續行**——一個長句被 PDF 自動換行成兩個物理行時，續行本身
   沒有任何方括號、也不對齊假名欄，而是整行都落在中文欄地板（`zh_
   floor`）之後（見 `_is_pure_zh_continuation`）。例如 01 課第 14 筆
   「しゃいん」的中文釋義「～公司的職員（和公司的名稱一起使」在下一
   個物理行接續「用，如IMCの　しゃいん）」；04 課第 49 筆、11 課第
   54 筆都是同一種模式（句子在括號說明中途被迫換行）。這種續行**直
   接接在前一筆的 `zh` 尾端，不加分隔符**——它本來就是同一個句子被
   換行切開，不是新的一段。
2. **替代讀音／註解續行**——課本偶爾會在單字下方另起一行給敬語替代
   讀音＋中文說明，用全形圓括號 `（）`（不是搭配用法的 `［］`／
   `〔〕`），甚至完全不用括號（例如 01 課第 32 筆「～から　来まし
   た。」單純給出另一個書寫形式）。這種續行的第一個 Cell 對齊假名欄
   （容差同樣是 `_CONT_ALIGN_TOL`），但**明確不含** `［`／`〔`（見
   `_is_alt_reading_continuation`，這個排除條件避免跟 usage 子行的判
   定重疊）。目前的處理方式是把整行文字（含替代讀音本身）原樣接在
   `zh` 尾端、用一個空白分隔——schema 沒有專門欄位存放「替代讀音」，
   這是為了不遺失資料而選擇的簡化做法，缺點是 `zh` 欄位會混進日文文
   字，不是純中文；若之後需要更精細的結構化，值得為此另闢欄位，但那
   超出本輪修正的範圍。

這兩種續行都可能連續出現多行（例如 01 課第 4、24 筆：先一行替代讀音
續行，再一行純中文續行），`parse_vocab` 的主迴圈逐行判定、沒有行數上
限，天然支援任意長度的續行鏈。

### 續行鏈中斷：遇到不認得的內容必須重設 `last_entry`

實作續行機制的過程中發現一個自己引入的新迴歸：`■会話` 小框裡的對話
常常是長句換行（例如 07 課「ごめんください。對不起。／有人在家嗎？
／我能進來」換行接續「嗎？（去別人家時用）」），對話本文本身的縮排
（x=25.8）不對齊假名欄、不落在中文欄地板，所以正確地被判定成「不認
得」；但換行後的殘句「嗎？（去別人家時用）」單獨一行時，形狀恰好符
合「純中文續行」（整行只有一個 Cell、落在中文欄地板之後）！若不特別
處理，`last_entry` 會停留在單字表最後一筆（例如第 38 筆），這句殘句
就會被誤黏進那一筆的 `zh`，產生一團混亂的假資料——比完全不處理續行
還糟。

修法：主迴圈每處理完一行，若這行**沒有**符合任何已知樣式（不是新單
字、不是 usage 子行、不是純中文續行、不是替代讀音續行），就把
`last_entry` 重設成 `None`。這樣「ごめんください...」這句認不出來的
對話本文出現時，`last_entry` 立刻歸零，緊接在後的「嗎？（去別人家時
用）」即使形狀符合純中文續行，也因為 `last_entry is None` 而不會被
誤併，正確維持在未歸類狀態（`■会話` 小框內容目前的既定行為就是不特
別收錄，見下方「補充單字」的「已知的不完整覆蓋」）。

## 補充單字：無編號的國名／專有名詞不可整批遺失

`ことば` 區段常在編號單字表結束後、「---以下單字請自行練習發音---」
這行標記之後，附上一批**沒有編號**的補充詞彙，例如 01 課的十一個國
名（「アメリカ美國」「中国中國」…）與虛構專有名詞（「さくら大学╱
富士大学」「AKC研究所」）。這批詞彙以行首 `N.` 辨識單字列的主要邏輯
天生就會整批跳過——複審對全 15 課掃描「未被歸入任何單字的行」，找到
96 筆疑似遺漏的補充單字、66 筆疑似遺漏的續行/說明行，全數是這個原
因；相對於編號單字的 628 筆，等於少了約 13% 的詞彙，而且國名是初級
日語最核心的單字之一，直接影響使用者需求「單字練習」。

**判定依據：標記行本身當狀態閘門，不是幾何座標**。第一版曾嘗試用
「詞彙本身從行號原本該印的位置（`label_x`）開始」當幾何判準，但實測
15 課裡這個縮排並不固定——01、04 課是 12.0，03、05~10 課卻是
25.2~25.8（跟同一課「■会話」小框對話內容共用同一個縮排！），沒有一
個放諸全 15 課皆準的固定 x。更嚴重的是：07 課「■会話」小框裡有一句
對話「「～は」いかがですか。」開頭的引號被 `cells()` 併進了行首那一
個 Cell（跟 07 課第 38 筆單字「行號吸附後續文字」是同一種現象），恰
好讓這句對話的 x 精確落在 `label_x`＝12.0，若沿用「幾何對齊 label_x」
當判準，會把這句對話誤判成補充單字，而且因為它變成新的 `last_entry`，
後面好幾行完全無關的對話內容會被連環誤併進它的 `zh` 欄，產生一團混
亂的假資料——這比「完全不收補充單字」更糟，是明確的迴歸。

改用**課本自己印的文字標記**「以下單字請自行練習發音」當狀態閘門
（`_SUPPLEMENTARY_MARKER`）：`parse_vocab` 掃到這一行才把 `past_
marker` 設成 `True`，從此以後（直到這個 Section 結束）**所有**非編號
行都當成補充單字處理，不再檢查編號、usage 子行或續行；閘門開啟之前
的內容（包含「■会話」小框）完全不受影響，維持原有行為。全 15 課裡
只有 02 課完全沒有這個標記行（這一課 ことば 確實沒有額外的補充單
字，`■会話` 小框結束就是整個區段的結尾），閘門永遠不會開啟，行為
跟修正前一致。

**判定「新的一筆補充單字」還是「上一筆的續行」**：閘門開啟後，逐行
判斷該行是不是「純中文續行」（見下方，用 `_is_pure_zh_continuation`：
整行所有 Cell 都落在中文欄地板之後）——是的話併入目前這筆補充單字的
`zh`；不是的話，這行本身就是新一筆補充單字的開頭，重新走一次欄位狀
態機切出「詞彙本身」跟「中文」。這個判準完全不依賴補充單字本身的縮
排是 12.0 還是 25.8——`zh_floor` 是從編號單字學出來的中文欄地板，跟
補充單字共用同一張表格的版面，不受縮排差異影響。

**與編號單字共用欄位狀態機、但不套用緊排單字切點**：`_parse_
supplementary_line` 重用 `_split_data_cells` 切出「詞彙本身」跟「中
文」，但刻意不套用 `_first_ideograph` 的緊排切點——補充單字欄本身就
是一個完整的詞（可能是純假名的外來語國名「アメリカ」，也可能是漢字
寫成的專有名詞「韓国」「さくら大学╱富士大学」，甚至是英文字母
「AKC」「IMC」），不是「假名讀音＋漢字寫法」的配對；套用切點會把
「パワー電気」這種本來就含漢字的複合詞誤切成兩半。改用「詞彙本身含
不含表意文字」決定放在 `kana` 還是 `kanji` 欄，另一欄則是 `None`。

**輸出形狀**：`{"no": None, "kana": ..., "kanji": ..., "zh": ...,
"usage": None, "group": ..., "supplementary": True}`——編號單字的
`supplementary` 一律是 `False`。**注意**：多筆補充單字的 `no` 都是
`None`，若下游程式碼天真地用 `{v["no"]: v for v in vocab}` 建字典，
這些補充單字會互相覆蓋、只剩最後一筆。呼叫端在需要以編號查詢單字時，
應先用 `supplementary` 欄位篩掉補充單字，或改用清單索引／獨立集合處
理它們，不能假設 `no` 在整份清單裡是唯一鍵。

**已知的不完整覆蓋**：「■会話」小框內的對話內容（標記行之前的部
分）刻意不當成補充單字收錄——它們是完整句子的對話練習，不是「詞彙＋
翻譯」格式的單字表，跟補充單字的資料形狀不同，混進同一個 schema 反
而會製造出格式不一致的假資料（且如上述，07 課已經證實這樣做有具體
的誤判風險）。

## 中文欄的角括號 `〔〕` 不可被過濾

07 課第 9 筆中文是「打〔電話〕」——`〔`、`〕`本身是中文釋義的一部分
（強調可替換的部分），過濾規則（`_has_real_content`）只用來判斷「一
個貼近 `kanji_x` 的 Cell 群組是不是真漢字」（防呆極少數場景：`kanji_x`
容差內剛好落了一個純標點 Cell），從不套用在中文欄本身；中文欄一律原
樣拼接、只做首尾空白 `strip()`。

## 已知限制

`_MIN_COLUMN_HITS`、`_MIN_COLUMN_GAP`、`_ZH_MARGIN`、`_KANJI_TOL` 這幾
個常數是用全 15 課（01.pdf ~ 15.pdf）ことば 區段的實測欄位分布校正
的，量測結果見 `task-7-report.md`。若未來課別的版面比例差異更大（例
如中文釋義極長、內部縫隙逼近甚至超過中文欄的抖動容許範圍），這幾個常
數可能需要重新檢視。

14、15 課的動詞群組標記（Ⅰ／Ⅱ／Ⅲ）版面全課從不把假名/漢字切成分開
的 Cell（例如「たちます  Ⅰ           立ちます」整段是一個 Cell，漢字
緊接在假名之後），因此這兩課學不出獨立的 `kanji_x`——這是本模組能正
確處理的情形（靠 `_first_ideograph` 切開、`_extract_group` 把羅馬數字
抽成獨立欄位）。

**這兩課曾經共有 10 筆單字資料損毀（14 課 6 筆、15 課 4 筆：#6、8、
15、16、17、18 與 #2、7、8、9），根因已在 `fragments.py` 修復，不再
是本模組的殘留限制**——課本用巨大字距（`Tc≈14~18.5`）把動詞分類羅馬
數字跟緊接在後的中文釋義第一個字編碼進同一個十六進位字串（例如 14
課第 6 筆的 Fragment 文字原本是 `"Ⅰ等"`，「等」其實是中文釋義「等
待」的第一個字），先前 `fragments.py` 把整串當一個 Fragment、
`layout.py` 用平坦字寬模型估計內部字元位置時完全不知道這個真實間
距，導致「等」被誤判成緊跟在「Ⅰ」後面。修法見 `fragments.py` 模組
說明「Tc 大到造成真實視覺分離時逐字元拆分」：`_emit()` 現在在
`state.tc * state.a` 超過門檻時逐字元展開 Fragment，讓「等」這類字元
帶著正確的真實座標（例如 14 課第 6 筆的「等」現在落在 x=368.4，跟這
一課中文欄名目起點一致），本模組不需要再做任何猜測就能正確分欄。

**已用 shipped 的 `parse_vocab` 重新量測全部 10 筆，全數修正正確**
（14/6 `kanji='待ちます'／zh='等待'`；14/8 `kanji='曲がります'／
zh='轉向〔右邊〕'`；14/15 `kanji='教えます'／zh='告訴〔地址〕'`；14/16
`kanji='始めます'／zh='開始'`；14/17 `kanji='降ります'／zh='下〔雨〕'`；
14/18 `kanji=None／zh='影印'`——`コピーします` 是外來語動詞，先前這個
根因曾誤植出一個根本不存在的假漢字 `'影'`；15/2 `kanji='座ります'／
zh='坐'`，已算繪 15.pdf 第 1 頁核對過視覺位置；15/7 `kanji='知ります'／
zh='得知'`；15/8 `kanji='住みます'／zh='居住'`；15/9
`kanji='研究します'／zh='研究'`。詳細量測與逐筆核對過程見
`task-7-report.md`）。

修復後已對全 15 課做過「原始 Fragment 是否還有任何文字同時包含動詞
分類羅馬數字又長度大於 1」的掃描，確認 ことば 區段裡不再有任何殘留
的這類損毀（頁面上其餘含羅馬數字的多字元 Fragment 都是文法說明頁的
正常連續散文，例如「Ⅰ類動詞」，本來就不該被拆開，也確實沒有觸發拆
分邏輯）。
"""
import re
import unicodedata
from collections import Counter
from typing import Dict, List, Optional, Tuple

from tools.extract.layout import Cell, Line
from tools.extract.sections import Section

# 行首編號：可能有前導全形/半形空白（例如「  10.」），數字後通常接一
# 個半形句點（可選，見模組說明「行號防呆」），其後任何內容（含空白）
# 都留給 group(2)（見模組說明「行號吸附後續文字」的情形，例如某些課
# 別的引號被 `cells()` 併進了標籤 Cell）。
_ENTRY_RE = re.compile(r"^\s*(\d+)\.?(.*)$", re.S)

# 判定一個 x 是不是「固定版面欄位」的最少重複次數；中文續行因標點被
# 切開產生的 x 幾乎每筆都不同，很少剛好重複到這個次數以上（見模組說
# 明「中文欄名目起點與抖動」）。
_MIN_COLUMN_HITS = 3

# 兩個候選欄位 x 之間，被視為「確實是不同欄位」的最小距離（pt）。全
# 15 課實測任兩個真正欄位之間的距離都遠大於這個值。
_MIN_COLUMN_GAP = 100.0

# 中文欄地板 = 學出的中文欄名目起點（抖動後較低的那個叢集） − 這個
# 邊際值，留安全餘裕。
_ZH_MARGIN = 30.0

# 判定一個 Cell 的 x 是否貼近學出來的漢字欄 x 的容差（pt）。漢字欄 x
# 是精確重複的固定版面座標，不需要很寬的容差。
_KANJI_TOL = 5.0

# usage 子行／續行 x 對齊容差（pt）：見模組說明「usage 子行對齊容差過
# 嚴」——子行開頭的方括號／圓括號本身會讓整欄往左抖動（實測抖動量
# 13.2~13.8pt，量級跟中文欄抖動一致，見模組說明「中文欄名目起點與抖
# 動」），複審全 15 課掃描找到 9 筆 usage 子行因為原本的 3.0pt 容差被
# 誤判成非子行而遺失。16.0pt 留有安全邊界（遠大於實測抖動上限
# 13.8pt、遠小於假名欄到漢字欄的真正欄距 150pt+）。
_CONT_ALIGN_TOL = 16.0


def _is_ideograph(ch: str) -> bool:
    return ("一" <= ch <= "鿿") or ("㐀" <= ch <= "䶿")


def _first_ideograph(text: str) -> Optional[int]:
    for i, ch in enumerate(text):
        if _is_ideograph(ch):
            return i
    return None


# 課本從第 14 課開始，在假名欄後面用羅馬數字標註動詞分類（Ⅰ／Ⅱ／Ⅲ
# 類，動詞變化練習需要這個資訊才能推導て形、ない形等），見模組說明
# 「動詞分類記號（group）」。
_GROUP_MARKS = {"Ⅰ": "I", "Ⅱ": "II", "Ⅲ": "III"}


def _extract_group(kana: str) -> Tuple[str, Optional[str]]:
    """從假名欄文字裡找動詞分類羅馬數字，抽成獨立的 `group` 值並從假名
    欄移除。見模組說明「動詞分類記號（group）」。"""
    for mark, name in _GROUP_MARKS.items():
        if mark in kana:
            return kana.replace(mark, ""), name
    return kana, None


def _has_real_content(text: str) -> bool:
    """判斷一段文字是不是「純標點/空白的偽欄位」——見模組說明「中文欄
    的角括號不可被過濾」：這個判斷只用在疑似漢字欄，從不套用在中文欄
    本身。Unicode 類別開頭 P（標點）或 Z（空白分隔）的字元視為不算實
    質內容；假名、漢字、片假名等（類別 Lo）都算。"""
    return any(unicodedata.category(ch)[0] not in ("P", "Z") for ch in text)


def _join(cells: List[Cell]) -> str:
    return "".join(c.text for c in cells).strip()


def _strip_brackets(s: str) -> str:
    s = s.strip()
    if s[:1] in ("［", "〔"):
        s = s[1:]
    if s[-1:] in ("］", "〕"):
        s = s[:-1]
    return s


def _match_entry(line: Line) -> Optional[Tuple[int, List[Cell]]]:
    """若這一行是單字列（行首有編號），回傳 (編號, 資料 Cell 列表)；
    資料 Cell 已去掉行號標籤本身，且把標籤吸附的殘留文字（見模組說明）
    併回最前面。不是單字列則回傳 None（不做行號防呆——呼叫端自行比對
    預期序號，見 `parse_vocab`/`_learn_layout`）。"""
    m = _ENTRY_RE.match(line.text())
    if not m:
        return None
    no = int(m.group(1))

    cells = line.cells()
    lm = _ENTRY_RE.match(cells[0].text)
    leftover = lm.group(2) if lm else ""
    data: List[Cell] = list(cells[1:])
    if leftover.strip():
        data = [Cell(x=cells[0].x, text=leftover, frags=[])] + data
    return no, data


def _learn_layout(lines: List[Line]) -> Tuple[float, Optional[float], Optional[float]]:
    """學出這一課的 (假名欄 x, 漢字欄 x 或 None, 中文欄地板 x 或
    None)。見模組說明「為什麼不能只看相鄰 Cell 的間距」與「中文欄名
    目起點與抖動」。只採用「行號跟預期序號精確銜接」的行（見模組說明
    「行號防呆」），避免非單字內容（例如課文附錄的號碼）污染統計。"""
    kana_counts: Counter = Counter()
    other_counts: Counter = Counter()
    expected = 1

    for line in lines:
        matched = _match_entry(line)
        if matched is None:
            continue
        no, data = matched
        if no != expected:
            continue
        expected += 1
        if not data:
            continue
        kana_counts[round(data[0].x, 1)] += 1
        for c in data[1:]:
            other_counts[round(c.x, 1)] += 1

    kana_x = kana_counts.most_common(1)[0][0] if kana_counts else 0.0

    candidates = sorted(
        x for x, cnt in other_counts.items()
        if cnt >= _MIN_COLUMN_HITS and x - kana_x >= _MIN_COLUMN_GAP
    )

    if not candidates:
        return kana_x, None, None

    kanji_x: Optional[float] = None
    zh_ref: Optional[float] = None
    for x in candidates:
        if zh_ref is None and kanji_x is None:
            kanji_x = x
            continue
        if x - kanji_x >= _MIN_COLUMN_GAP:
            zh_ref = x
            break

    if zh_ref is None:
        # 只有一個夠遠的高頻叢集：這一課沒有另外的漢字欄，這個叢集本
        # 身就是中文欄名目起點。
        zh_ref = kanji_x
        kanji_x = None

    zh_floor = zh_ref - _ZH_MARGIN
    return kana_x, kanji_x, zh_floor


def _split_data_cells(
    data: List[Cell], kanji_x: Optional[float], zh_floor: Optional[float]
) -> Tuple[List[Cell], List[Cell], List[Cell]]:
    """狀態機：依序掃描一筆單字的資料 Cell，決定「假名／漢字／中文」
    三欄的歸屬。見模組說明「改用『絕對位置 + 狀態機』解決第 1 類問
    題」——已經進入某一欄之後，同一欄內部後續的 Cell 一律留在同一欄，
    只有 Cell x 真正貼近下一個欄位邊界才會換欄。"""
    kana_cells: List[Cell] = []
    kanji_cells: List[Cell] = []
    zh_cells: List[Cell] = []
    state = "kana"

    for c in data:
        if state == "kana":
            if kanji_x is not None and abs(c.x - kanji_x) <= _KANJI_TOL:
                state = "kanji"
            elif zh_floor is not None and c.x >= zh_floor:
                state = "zh"
        elif state == "kanji":
            if zh_floor is not None and c.x >= zh_floor:
                state = "zh"
        # state == "zh"：不再切換。

        if state == "kana":
            kana_cells.append(c)
        elif state == "kanji":
            kanji_cells.append(c)
        else:
            zh_cells.append(c)

    return kana_cells, kanji_cells, zh_cells


def _parse_entry_line(
    no: int, data: List[Cell], kanji_x: Optional[float], zh_floor: Optional[float]
) -> Dict:
    kana_cells, kanji_cells, zh_cells = _split_data_cells(data, kanji_x, zh_floor)

    kana = _join(kana_cells)
    kanji = _join(kanji_cells)
    zh = _join(zh_cells)

    if kanji and not _has_real_content(kanji):
        # 疑似漢字欄其實是純標點造成的偽欄位——併回中文欄開頭（見模組
        # 說明「中文欄的角括號不可被過濾」：這個過濾只用在這裡）。
        zh = _join(kanji_cells + zh_cells)
        kanji = ""

    if not kanji:
        idx = _first_ideograph(kana)
        if idx is not None:
            # 緊排單字：假名／漢字擠在同一個 Cell 內，見模組說明。
            kanji = kana[idx:]
            kana = kana[:idx]

    kana, group = _extract_group(kana)

    kana = kana.strip()
    kanji = kanji.strip()
    zh = zh.strip()

    return {
        "no": no,
        "kana": kana,
        "kanji": kanji if kanji else None,
        "zh": zh,
        "usage": None,
        "group": group,
        "supplementary": False,
    }


def _is_usage_subline(line: Line, kana_x: float) -> bool:
    cells = line.cells()
    if not cells:
        return False
    if abs(cells[0].x - kana_x) > _CONT_ALIGN_TOL:
        return False
    text = line.text()
    return ("［" in text) or ("〔" in text)


# usage 子行「假名用法／漢字用法」兩欄之間，視為真正換欄的最小間距
# （pt）。見 `_split_usage_cells` 說明：欄內縫隙（同一括號片語內部）
# 實測 <=19.8pt，真正換欄的縫隙實測 >=66pt，50pt 留有安全邊界。
_USAGE_SPLIT_GAP = 50.0


def _split_usage_cells(cells: List[Cell]) -> Tuple[List[Cell], List[Cell]]:
    """usage 子行只有假名／漢字兩欄（沒有中文欄），用「相鄰 Cell 間最
    大縫隙」切成兩組，而不是比對學出來的 `kanji_x`：子行的漢字用法欄
    開頭印著「［」，這個前導方括號會讓整欄往左抖動（06 課實測抖動量
    13.8pt，跟中文欄的抖動量級相同，見模組說明「中文欄名目起點與抖
    動」），若沿用貼近 `kanji_x` 的精確容差比對會漏判、整行被誤判成只
    有假名沒有漢字（06 課第 9、11 筆、11 課第 4 筆都是這個模式）。15
    課更進一步：這一課的單字本身從不把假名/漢字切成分開的 Cell（見模
    組說明「已知限制」），完全學不出 `kanji_x`，貼近 `kanji_x` 的作法
    對這一課的 usage 子行必然失效。

    改用相鄰 Cell 的最大間距來找換欄點：全 15 課實測，同一欄位內部（括
    號片語自身）的縫隙全部 <=19.8pt，真正的假名／漢字換欄縫隙全部
    >=66pt，`_USAGE_SPLIT_GAP`（50pt）介於兩者之間。只有一個 Cell、或
    最大縫隙小於門檻（只有單一括號、沒有對應的漢字用法，例如 12 課
    「［コーヒーが～］」）時，回傳全部歸假名、漢字為 `None`。"""
    if len(cells) < 2:
        return list(cells), []
    gaps = [(cells[i + 1].x - cells[i].x, i) for i in range(len(cells) - 1)]
    max_gap, split_at = max(gaps)
    if max_gap < _USAGE_SPLIT_GAP:
        return list(cells), []
    return cells[:split_at + 1], cells[split_at + 1:]


def _parse_usage_line(line: Line) -> Dict:
    kana_cells, kanji_cells = _split_usage_cells(line.cells())
    kana = _strip_brackets(_join(kana_cells))
    kanji = _strip_brackets(_join(kanji_cells)) if kanji_cells else None
    return {"kana": kana, "kanji": kanji}


# 「以下單字請自行練習發音」這類標記行——底下是沒有編號的補充詞彙／
# 專有名詞，標記本身不是詞彙內容。見模組說明「補充單字」：這行本身當
# 狀態閘門用，不是幾何座標判準（補充單字的縮排在不同課別並不固定）。
_SUPPLEMENTARY_MARKER = "以下單字"


def _parse_supplementary_line(
    line: Line, kanji_x: Optional[float], zh_floor: Optional[float]
) -> Dict:
    """解析一筆補充單字（見模組說明「補充單字」）。跟編號單字共用同一
    套欄位狀態機（`_split_data_cells`）切出「詞彙本身」跟「中文」，但
    **不**套用 `_first_ideograph` 緊排單字切點——補充單字欄本身就是一
    個完整的詞（可能是純假名的外來語國名，也可能是漢字寫成的專有名詞
    或複合詞，例如「さくら大学╱富士大学」），不是「假名讀音 + 漢字寫
    法」的配對，套用切點會把「パワー電気」這種本來就含漢字的複合詞
    誤切成兩半。改用「詞彙本身含不含表意文字」決定放在 `kana` 還是
    `kanji` 欄：純假名/片假名/其他非表意文字（外來語國名）放 `kana`，
    含表意文字（漢字專有名詞）放 `kanji`，另一欄則是 `None`。"""
    cells = line.cells()
    kana_cells, kanji_cells, zh_cells = _split_data_cells(cells, kanji_x, zh_floor)
    term = _join(kana_cells + kanji_cells)
    zh = _join(zh_cells)

    term, group = _extract_group(term)
    term = term.strip()

    if _first_ideograph(term) is not None:
        kana, kanji = None, term
    else:
        kana, kanji = (term if term else None), None

    return {
        "no": None,
        "kana": kana,
        "kanji": kanji,
        "zh": zh.strip(),
        "usage": None,
        "group": group,
        "supplementary": True,
    }


def _is_pure_zh_continuation(line: Line, zh_floor: Optional[float]) -> bool:
    """判定一行是不是「純中文續行」——見模組說明「續行不可遺失」：一
    個長句被 PDF 自動換行成兩個物理行時，續行的全部 Cell 都落在中文
    欄地板之後（沒有任何內容退回假名欄或行號欄的位置），這是跟「usage
    子行」「補充單字開頭」（兩者的第一個 Cell 都遠在中文欄地板之前）
    的關鍵區別。"""
    if zh_floor is None:
        return False
    cells = line.cells()
    if not cells:
        return False
    return all(c.x >= zh_floor for c in cells)


def _is_alt_reading_continuation(line: Line, kana_x: float) -> bool:
    """判定一行是不是「替代讀音／註解續行」——見模組說明「續行不可遺
    失」：課本偶爾會在單字下方另起一行給敬語替代讀音＋中文註解（例如
    01 課「（ あの かた ）（ あの 方 ）（"あのかた"是"あのひと"的禮」），
    版面上跟 usage 子行一樣對齊假名欄（同樣的前導括號抖動，套用同一個
    `_CONT_ALIGN_TOL`），但內容不是 `［ ］`／`〔 〕` 搭配用法方括號
    （用全形圓括號 `（）`，或甚至完全沒有括號，例如「～から　来まし
    た。」給另一個寫法）。**明確排除含 `［`／`〔` 的行**：那種情況一
    定是 usage 子行，應該交給 `_is_usage_subline` 處理，不能兩邊都收
    一次（`usage` 已設定時才會落到這裡，此時若又是方括號子行，代表是
    這筆單字的第二則搭配用法，目前選擇忽略而不是覆蓋或誤併入中文欄，
    見模組說明「已知限制」）。"""
    cells = line.cells()
    if not cells:
        return False
    if abs(cells[0].x - kana_x) > _CONT_ALIGN_TOL:
        return False
    text = line.text()
    return not (("［" in text) or ("〔" in text))


def parse_vocab(section: Section) -> List[Dict]:
    """把 `ことば` Section 解析成單字紀錄列表，見模組說明。"""
    kana_x, kanji_x, zh_floor = _learn_layout(section.lines)

    entries: List[Dict] = []
    last_entry: Optional[Dict] = None
    expected = 1
    past_marker = False  # 見模組說明「補充單字」：碰到標記行後永久開啟

    for line in section.lines:
        if _SUPPLEMENTARY_MARKER in line.text():
            past_marker = True
            continue

        if past_marker:
            # 標記行之後，這個 Section 剩下的每一行都是補充單字或它的
            # 續行，不再檢查編號／usage 子行——那些機制只適用於編號單
            # 字表本體（見模組說明「補充單字」）。
            if not line.cells():
                continue
            if (last_entry is not None and last_entry["supplementary"]
                    and _is_pure_zh_continuation(line, zh_floor)):
                cont_text = line.text().strip()
                if cont_text:
                    last_entry["zh"] = (last_entry["zh"] + cont_text).strip()
                continue
            entry = _parse_supplementary_line(line, kanji_x, zh_floor)
            entries.append(entry)
            last_entry = entry
            continue

        matched = _match_entry(line)
        if matched is not None and matched[0] == expected:
            no, data = matched
            entry = _parse_entry_line(no, data, kanji_x, zh_floor)
            entries.append(entry)
            last_entry = entry
            expected += 1
            continue

        if (last_entry is not None and last_entry["usage"] is None
                and _is_usage_subline(line, kana_x)):
            last_entry["usage"] = _parse_usage_line(line)
            continue

        if last_entry is not None and _is_pure_zh_continuation(line, zh_floor):
            cont_text = line.text().strip()
            if cont_text:
                last_entry["zh"] = (last_entry["zh"] + cont_text).strip()
            continue

        if last_entry is not None and _is_alt_reading_continuation(line, kana_x):
            cont_text = line.text().strip()
            if cont_text:
                last_entry["zh"] = (last_entry["zh"] + " " + cont_text).strip()
            continue

        # 這行不符合任何已知樣式——見模組說明「續行鏈中斷」：一旦遇到無
        # 法辨識的內容（典型例子是「■会話」小框的對話本文），視為離開
        # 了目前這筆單字的續行鏈，重設 `last_entry`。不重設的話，後面
        # 剛好長得像純中文續行（單一 Cell 落在中文欄地板之後）的無關對
        # 話內容會被誤併入這筆舊單字——07 課「■会話」小框裡有好幾句對
        # 話換行後的殘句（例如「嗎？（去別人家時用）」），複審修正 usage
        # 容差之前沒有這個重設機制時，這些殘句全部被誤黏進第 38 筆單字
        # 的 `zh`，變成一團混亂的假資料，是比「完全不收」更糟的迴歸。
        if line.cells() and line.text().strip():
            last_entry = None

    return entries
