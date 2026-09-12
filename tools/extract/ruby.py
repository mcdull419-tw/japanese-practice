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
- **`RUBY_X_MAX_DIST = 12.0`**（簡報原值 11.0；審查回合重新量測，數值不
  變但敘述改寫——見下方「這個常數的敘述曾經引用錯誤的距離」）：對全 15
  課資料掃 `RUBY_X_MAX_DIST ∈ {5,6,6.6,7,...,22}`，量出全書配對字元總
  數，7.0~13.0 這個區間全部給出相同結果（11750，逐一相同，這個區間內
  任何一個值行為都等價，不是巧合湊出來的單一數字），12.0 落在這個區間
  正中偏左，維持不變。往下量：6.6→7.0 之間有一個真實跳躍
  （11543→11750）；往上量：13.0→14.05 之間有另一個真實跳躍
  （11750→11765，對應 07.pdf p.8「語～で　何ですか」的 語→ご，算繪核
  對為真，見下方精確距離）；14.05~18 又是一段平台，20 附近再跳一次。
  12.0 安全落在第一段平台內，跟兩側的真實跳躍點都留有餘裕。

  **這個常數的敘述曾經引用錯誤的距離，這裡記錄更正過程**：Task 5 第一
  輪報告曾主張「時→じ、起→お 最大量到 11.4pt」「語→ご 量到 18.8pt」，
  這兩個數字是用**逐字元展開後的假名座標**算出來的；但演算法後來改成
  一律用 **fragment 原始錨點**（`Fragment.x`）當候選座標（見上一節「配
  對單位是振假名 fragment 內的空白分隔區段」），沒有回頭用新的座標定義
  重新量測這兩個例子，導致敘述跟實際跑的程式碼不符——這個落差是審查回
  合抓出來的，程式碼本身沒有問題（`RUBY_X_MAX_DIST` 在 7.0~13.0 區間本
  來就是 inert，不管敘述對不對，實際行為都一樣），但敘述寫進了 commit
  history、可能誤導後續維護者，這裡用**目前演算法實際跑出來的距離**重
  新記錄：
  - 時→じ、起→お（04.pdf p.7「6時（に）起きます」）：用 fragment 錨點
    算出來的距離是 **6.6pt**（`ruby ' じ' 193.8` vs `時 x=187.2`），不
    是 11.4pt。
  - 語→ご（07.pdf p.8「語～で　何ですか」）：用 fragment 錨點算出來的
    距離是 **14.04pt**（`ruby '  ご' 152.4` vs `語 x=138.361`），不是
    18.8pt。這個距離剛好落在 13.0~14.05 那個跳躍點之後，12.0 目前抓不
    到（會算成「找不到配對」，不影響配對正確性，只小幅拉低配對率，跟
    簡報自陳的「已知邊緣案例」性質相同）。
  - 「動詞」的「動」量到隔壁「回」的假名「かい」：距離 12.6pt（算繪確
    認「動詞」本身沒有振假名，純屬巧合鄰近，不是真配對）——這個數字沒
    有變，維持原本的結論：12.0 緊貼在 7.0~13.0 這段真實叢集的中段，同
    時排除 12.6 這個雜訊。

## 配對單位是「振假名 fragment 內的空白分隔區段」，不是逐字元最近點

簡報演算法描述（步驟 2）讀起來像是「每個振假名字元」各自獨立找最近的漢
字。實作後發現這個逐字元最近點策略在**同一個振假名 fragment 涵蓋多個漢
字、且各漢字讀音長度不同**時會配錯——例如「太郎君」的振假名是單一
fragment `'  た  ろう  くん'`（三個空白分隔區段：「た」對應「太」、
「ろう」對應「郎」、「くん」對應「君」）。「た」這個假名字元本身因為只
有一個字，置中後展開的實際 x（用目前實際跑的演算法算出來是 284.4）離
「郎」（x≈286.2）只有 1.8pt，離它真正對應的「太」（x≈273.0）反而有
11.4pt。若對每個假名字元獨立找「最近」的漢字，「た」會被誤配給「郎」，
導致合併後的 base 變成「郎君」（漏掉「太」）、kana 變成「たろうく」
（漏掉「ん」）——字串看起來像是「合理的部分結果」，不會讓任何弱斷言測
試失敗，但讀音已經錯位。

修正方式：**先依 fragment 內部空白把文字切成區段（每區段對應一個漢
字），再以「整個 fragment 的原始錨點」（`Fragment.x`，也就是 fragment
文字第一個字元——通常是置中用的前導空白——所在的座標，尚未依字元前進量
推進）去找配對的起始漢字，而不是用區段內已展開的假名字元座標**。找到起
始漢字後，要求從那裡開始能湊出 N 個底字（N = 區段數，見 `_find_run`）
——這一步不只是「找最近」，是真正決定這個候選能不能撐起整組讀音。

「太郎君」用目前實際跑的演算法重新量測：fragment 錨點 x=279.6，離
「太」的距離是 6.60036000000008pt，離「郎」的距離是 6.5996399999999085
pt——兩者幾乎相等（差約 0.00072pt，這個差距本身跟「排版設計」無關，是
`char_width` 對不同字元的離散寬度模型累加多次後的正常次像素效應，不能
拿來當作「太比較近」的證據）。真正讓「太」中選、「郎」出局的不是距離，
是 `_find_run` 的結構驗證：從「太」出發能找到 `[太,郎,君]` 三個連續底
字（合法）；從「郎」出發只能找到 `[郎,君]`，第三個底字需要先跳過「と」
（1 個非空白字元）、再跳過緊接著的空白（第 2 個跳過字元，超過
`_find_run` 「只放行剛好 1 個非空白跳過」的上限），判定無效——實測
`_find_run(reading, 郎的索引, 3)` 回傳 `None`。也就是說，即使兩個候選
的距離幾乎打平，「郎」根本沒有資格進入比較，`_TIE_EPS` 在這個案例裡不
是決定性因素（把 `_TIE_EPS` 設為 0 重跑，這個案例依然正確——已驗證，
見 `tests/extract/test_ruby.py`）。

同一個 fragment 找不到滿足門檻與連續底字數的起點時，整個 fragment 的假
名視為配不到（不落回逐字元最近點那條會配錯的路徑）——只降低配對率，不
產生錯誤配對，符合簡報「測試門檻設 98% 而非 100%」的容忍範圍。

## 底字不只是漢字：々、數字

第一版只認 CJK 表意文字當底字，審查後補上兩類：
`々`（U+3005 IDEOGRAPHIC ITERATION MARK，「時々」「別々」這類疊字詞需要
自己的讀音）與阿拉伯數字（「7つ」「3か月」「10分」這類量詞/時間表達，
振假名標在數字本身上面）。詳見 `_is_base_char`。

## 兩種錨點交叉驗證：純數字起點必須跟「展開後首字元」的結果一致

`_find_start` 預設用 `Fragment.x`（原始錨點，尚未依字元前進量展開）找
起點。改用「展開後第一個假名字元的實際座標」**全面取代**原始錨點試過
一次（拿掉數字判定、無條件改用展開座標，全 15 課重新跑一次比對輸出），
結果讓好幾個原本正確的案例壞掉：`時計→とけい` 變成 `計→とけい`（漏掉
「時」）、`一人→ひとり` 變成 `人→ひとり`（漏掉「一」）、
`土産→みやげ` 變成 `産→みやげ`（漏掉「土」）、`紅葉→もみじ` 變成
`葉→もみじ`（漏掉「紅」）——這些都是「一個未分段區段涵蓋多個漢字」的
熟字訓讀音（跟「時計」「誕生日」同一類，見前面「配對單位」一節），展開
後的座標系統性往「最後一個」底字偏移，而正確答案通常是「第一個」底
字。這證實原始錨點（不展開）才是這類情形的正確預設。

但原始錨點對「底字前面還有好幾個不需要讀音的字元」的情形會系統性選
錯——例如 13.pdf「980円」，振假名只有一個區段「えん」（對應「円」），
但 fragment 本身有 9 個前導半形空白（用來把「えん」推到「円」正上
方），這些空白的寬度剛好讓 `Fragment.x` 數值跟「9」（980 的第一位數
字）的 x 座標幾乎重合（實測差 1.1368683772161603e-13pt，雙精度浮點運
算的正常捨入誤差量級），而展開後第一個假名字元「え」的實際座標離
「円」只有 1.8pt、離「9」卻有 21.6pt——這裡展開後座標才是對的。

兩種情形無法用同一套規則同時處理對，所以採取交叉驗證：**只有在原始錨
點選到的起點是數字時**，才額外用展開後首字元的座標重找一次；如果這次
找到的起點是漢字，改採這個結果。這個條件只在「原始選到數字」時觸發，
不會影響「時計」「一人」「土産」這類原始錨點選到漢字、本來就正確的案
例（`tests/extract/test_ruby.py` 的迴歸測試逐一鎖住兩邊的案例）。

（「太郎君」不受這個交叉驗證機制影響——不管用原始錨點還是展開後座標
搜尋，「郎」都會因為 `_find_run` 的結構驗證失敗而出局，「太」在兩種算
法下都正確中選，已個別驗證過，見上一節。）
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


def _is_base_char(ch: str) -> bool:
    """判斷一個字元能不能當振假名的「底字」——不只是漢字。

    第一版實作只認 CJK 表意文字，審查後發現至少兩類真實存在、有振假名
    的底字被排除在外：

    - **々（U+3005 IDEOGRAPHIC ITERATION MARK）**：`unicodedata.name` 回
      傳 `IDEOGRAPHIC ITERATION MARK`，不含 `CJK UNIFIED`/`CJK
      COMPATIBILITY`，但它在「時々」「別々」這類疊字詞裡跟前一個漢字一
      樣需要自己的讀音（時々→ときどき、別々→べつべつ），不能被當成標
      點跳過。
    - **阿拉伯數字**：「7つ」「3か月」「10分」這類量詞/時間表達，振假名
      標在數字本身上面（7→なな、3→さん、10→じゅう），底字不是漢字。
      這是第 11 課（量詞、數字課，直接對應使用者 must-have 需求）配對率
      偏低的主因。

    `ch.isdigit()` 同時涵蓋半形與全形數字。"""
    if ch == "々":
        return True
    if ch.isdigit():
        return True
    return _is_cjk_ideograph(ch)


def _ruby_groups(frags: List[Fragment]) -> List[Tuple[float, float, List[str], float]]:
    """把每個振假名 fragment 依內部空白切成區段，回傳
    `(錨點x, 錨點y, [區段文字, ...], 首個假名字元的展開後 x)` 的清單——
    一個 fragment 一組，錨點是 `Fragment.x`／`Fragment.y` 本身（見模組說
    明「兩種錨點」：`Fragment.x` 用來找「起始底字」，展開後的首字元 x
    只在起始候選是數字時用來做交叉驗證，見 `pair_ruby`）。"""
    groups = []
    for f in frags:
        x = f.x
        first_kana_x: Optional[float] = None
        segments: List[str] = []
        current = ""
        for ch in f.text:
            if ch.strip():
                if first_kana_x is None:
                    first_kana_x = x
                current += ch
            elif current:
                segments.append(current)
                current = ""
            x += char_width(ch, f.size)
        if current:
            segments.append(current)
        if segments:
            groups.append((f.x, f.y, segments, first_kana_x))
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
    者差距懸殊，用「正文字級的 2 倍」當上限就能可靠分開。

    **間距也不能是零或負的**：11.pdf 單字表換算列（例如「－時間小
    時」：假名欄「時間」跟中文欄「小時」剛好都從同一個左邊界 x=66.6
    起排、假名欄字級較窄（12.6pt）先印完，中文欄「小」的錨點因此落在
    假名欄「間」（x=79.2）的**左邊**——`next_x - prev_x = 66.6 - 79.2 =
    -12.6`，這種「往回跳」只可能是換到另一個獨立定位的文字區塊，不可
    能是同一個詞內字元真的往左移動。另一種變形是兩欄剛好**完全重
    合**——「－年年數」的假名欄單字「年」跟中文欄「年數」的「年」都落
    在 x=66.6（兩欄都從同一個左邊界起排、剛好都是第一個字），
    `next_x - prev_x = 0`，同一個詞內真正相鄰的兩個字元不可能有 0 的前
    進量（最窄的半形字元在最小字級下前進量也有數 pt）。原本只檢查上限
    （`next_x - prev_x > 門檻`），沒有同時排除「零或負值」，會誤判成
    「間距正常」，讓「時間」被錯誤延伸到中文欄「小時」、「年」被錯誤延
    伸到中文欄的另一個「年」（見 `pair_ruby` 呼叫這個函式的兩個擴張段
    落）。同一種列表格式另外還有「日天數」「週間星期」「か月月數」「分
    分鐘」等好幾個實例，都是同一根因（審查回合全語料庫掃描找出，不是
    這次新增的擴張邏輯造成的——沿用既有的熟字訓擴張機制，只是這道間距
    檢查原本就有這個漏洞）。下限設在 `0.5pt`（而非嚴格要求 `> 0`）純粹
    是安全邊界，容忍字元位置估計本身的次像素誤差，不是要放行真正的零
    間距。"""
    for k in range(n - 1):
        _prev_ch, prev_x, prev_f = reading[start + k]
        _next_ch, next_x, _next_f = reading[start + k + 1]
        gap = next_x - prev_x
        if gap < 0.5 or gap > _MAX_NORMAL_GAP_RATIO * prev_f.size:
            return False
    return True


_TIE_EPS = 1.0   # 見 `_find_start` 說明：兩個候選幾何距離「理論上相等」
                 # （例如 13.pdf「週末」的「週」「末」離振假名錨點
                 # `'しゅうまつ'`（單一未分段區段，anchor x=302.4）在視
                 # 覺上都恰好是半個字寬，理應平手），但用目前實際跑的演
                 # 算法（`_line_chars` 累加 `char_width` 算出來的 x）量
                 # 兩者的距離：週=6.60000000000008、末=6.599999999999909
                 # ——差了約 1.7e-13，屬於雙精度浮點連加幾十次後的正常捨
                 # 入誤差量級，不具備「兩個候選誰真的比較近」的意義，不
                 # 該拿來決定選哪個當起點。這個差值本身通常沒有影響（大
                 # 部分情況下就算選錯起點，`_find_run` 的「起點必須自己
                 # 就是底字、且能湊齊 n 個底字」驗證會直接判定該候選無
                 # 效，回頭選到正確答案）——但如果錯的那個候選剛好也能透
                 # 過「跳過剛好一個非空白字元」湊出合法的 n 個底字（週末
                 # 這裡 n=1，任何單一候選都天生合法，沒有這道保護），就
                 # 會真的選錯：13.pdf「(×) サントスさんの家族は週末公園
                 # へ...」這一處，`_TIE_EPS=0` 會讓「末」而非「週」中選，
                 # 產生 `base='末'、kana='しゅうまつ'`（「末」不讀
                 # しゅうまつ，那是「週末」的讀音，跟「太郎君」「980円」
                 # 同一類「base 被截短、kana 卻是完整讀音」的錯誤）。
                 # `tests/extract/test_ruby.py` 的
                 # `test_tie_break_not_swayed_by_subpixel_float_noise`
                 # 鎖住這個具體案例，驗收方式是把 `_TIE_EPS` 設回 0 重
                 # 跑，確認測試會變紅。1.0pt 遠大於這類次像素噪音，也遠
                 # 小於任何字元間有意義的距離差（相鄰字元間距至少 6.6pt
                 # 起跳），可以安全地把「視覺上同樣近」的候選視為平手，
                 # 改依讀出順序（x 較小者優先）決定。

def _find_run(
    reading: List[Tuple[str, float, Fragment]],
    start: int,
    n: int,
) -> Optional[List[int]]:
    """從 `reading[start]`（必須本身是底字）開始，找出依序出現的
    `n` 個底字字元索引，回傳這 `n` 個索引；找不到齊全就回傳 `None`。

    這裡允許在兩個相鄰底字之間**跳過剛好一個「連接用」的假名字元**
    （例如「店の人」中間的助詞「の」），不要求嚴格的索引相鄰——第一版
    實作要求 `reading[i+k]` 全部緊鄰、都是底字，這在「假名連接的複合
    詞」這種真實排版下會讓整組振假名配不到（審查發現，13 課「店の人」
    實例：店＝みせ、人＝ひと，中間的「の」是本來就在正文裡的助詞，不需
    要自己的振假名，振假名 `' みせ       ひと'` 是兩區段，但「店」後面
    接的是「の」（假名，非漢字），嚴格相鄰的舊判定直接判不到）。

    **刻意不允許跳過純空白字元，即使數量剛好符合對話人名字距排版的樣
    式**（審查曾建議修這個，實測後發現行不通，記錄在這裡避免重蹈覆
    轍）：對話人名字距排版（「山　田：」「佐　藤：」）確實會用 2~4 個
    半形空白把姓跟名拉開，一開始的修正版本允許跳過任意數量的純空白，也
    確實修好了這幾個人名。但這個放行條件跟本書排版裡「兩個獨立單字之間
    的間隔」用的是**同一種視覺慣例**——全書內文任何兩個詞之間幾乎都用
    兩個半形空白隔開（例如「わたしは␣␣木村さんに␣␣花を␣␣あげま
    す」），跟「山␣␣田」的姓名字距在幾何上無法區分。13.pdf 的「今␣␣
    何」（今天／什麼，兩個完全獨立的詞）剛好在某一個出現處被 PDF 原始
    內容流編碼成單一個振假名 fragment `' いま␣␣␣␣␣␣␣なに'`，允許跳過
    純空白後，這兩個無關的詞被錯誤合併成一個 `RubyPair`（base='今␣␣
    何'、kana='いまなに'）——「来年␣␣結婚」「毎日␣␣忙」是同一課的另外
    兩個實例。這種合併雖然沒有讓個別漢字的讀音本身錯誤（「今」跟「何」
    各自的假名還是對的），但破壞了讀音練習題型需要的「查得到獨立單字」
    這個前提，risk 高於「幾個人名配不到振假名」這個涵蓋率缺口。兩害相
    權，這裡選擇**不修**人名字距排版（見 task-5-report.md「否證驗證」
    小節有一個對照測試，鎖住這個決定，避免未來重新引入純空白跳過）。

    這裡逐步檢查的每一段間距（沿用 `_has_normal_spacing` 的比例）也用來
    排除真正的換頁/換欄跳躍：07.pdf 單字表裡「お土産土產，記念品」這一
    列，振假名 `'  み や げ'`（3 個空白分隔區段）錨點在第一個「土」正上
    方，若不檢查逐步間距，會依序找到「土（x=39.0）→産（x=52.2）→土
    （x=384.6）」這 3 個字元組成一個（看似合法的）3-底字候選——但最後
    一步的間距是 332.4pt（=384.6-52.2），是換到中文釋義欄位的巨大跳
    躍，不是同一個詞內的正常字距。逐步間距檢查會在「産→土」這一步就擋
    下來，讓這組振假名正確地判定為配不到（不會產生 base='土産土'這種橫
    跨欄位的錯誤合併）——已用「拿掉這道檢查、全 15 課重新跑一次、比對
    輸出差異」驗證過，這是全書唯一一個實際依賴這道檢查的案例。"""
    if not _is_base_char(reading[start][0]):
        return None
    run = [start]
    cur = start
    while len(run) < n:
        nxt = cur + 1
        non_space_skips = 0
        total_skips = 0
        while nxt < len(reading) and not _is_base_char(reading[nxt][0]):
            if reading[nxt][0].strip():
                non_space_skips += 1
            total_skips += 1
            if total_skips > 1:
                return None
            nxt += 1
        if nxt >= len(reading):
            return None
        if total_skips == 1 and non_space_skips == 0:
            return None   # 唯一跳過的字元是空白——見上方說明，不放行
        for k in range(cur, nxt):
            if not _has_normal_spacing(reading, k, 2):
                return None
        run.append(nxt)
        cur = nxt
    return run


def _find_start(
    reading: List[Tuple[str, float, Fragment]],
    base_indices: List[int],
    anchor_x: float,
    anchor_y: float,
    n_segments: int,
) -> Optional[List[int]]:
    """找出這組振假名區段最佳的起始底字索引，回傳完整的 `n_segments`
    個索引（見 `_find_run`）。候選須通過 y/x 門檻，且從候選起能找到齊全
    的底字序列。多個候選時取離 `anchor_x` 最近的；距離在浮點誤差範圍內
    視為相等時，取讀出順序較前面（x 較小）的候選（見 `_TIE_EPS` 說明）。
    """
    best_run: Optional[List[int]] = None
    best_dist: Optional[float] = None
    for i in base_indices:
        _ch, bx, bf = reading[i]
        if abs(anchor_y - (bf.y + RUBY_Y_OFFSET)) > RUBY_Y_TOL:
            continue
        xdist = abs(anchor_x - bx)
        if xdist > RUBY_X_MAX_DIST:
            continue
        run = _find_run(reading, i, n_segments)
        if run is None:
            continue
        if best_dist is None or xdist < best_dist - _TIE_EPS:
            best_dist = xdist
            best_run = run
    return best_run


_JUKUJIKUN_EXTEND_CAP = 2   # 見模組說明「未分段複合詞讀音」，避免無界擴張

_COUNTER_BRIDGE_KANJI = {"月", "時"}   # 見 pair_ruby 內「鏡像情況」段落說明：
                                       # 全語料庫掃描確認唯二需要「漢字＋
                                       # 數字＋漢字」橋接的計量單位漢字
                                       # （月＋N＋日、時＋N＋分），刻意排
                                       # 除「今」「毎日」「朝」等獨立時間
                                       # 副詞，避免誤把兩個獨立詞併成一個

_REGULAR_TARGET_READING = {"日": "にち"}   # 見 pair_ruby 內「鏡像情況」段落的
                                           # 「規則讀音日期」說明：判斷 target
                                           # 是否已經獨立配到一個「本身完整、
                                           # 不需要再吸收數字」的讀音，若是就
                                           # 不該被鏡像橋接吞掉。「日」是唯一
                                           # 需要這道判斷的 target——「分」
                                           # （時橋接的 target）不管數字規不
                                           # 規則、時態如何，自己的讀音永遠是
                                           # ふん／ぷん，橋接永遠正確，不需要
                                           # 排除；「日」則不同，見下方詳細
                                           # 說明。


def pair_ruby(all_frags: List[Fragment], line: Line) -> List[RubyPair]:
    ruby_groups = _ruby_groups([
        f for f in all_frags
        if f.size <= RUBY_MAX_SIZE and f.page == line.page and f.text.strip()
    ])

    # reading-order 字元序列，索引跟 line.text() 逐字元對應（見
    # layout.Line.text() 的實作——兩者共用同一個 `_line_chars` 來源）。
    reading = _line_chars(line.frags)
    base_indices = [i for i, (ch, _x, _f) in enumerate(reading) if _is_base_char(ch)]
    # 熟字訓擴張（見下方）只認漢字／々，不含數字——見該處說明。
    extendable_index_set = {
        i for i, (ch, _x, _f) in enumerate(reading)
        if _is_cjk_ideograph(ch) or ch == "々"
    }

    kana_by_index: Dict[int, str] = {}
    for anchor_x, anchor_y, segments, first_kana_x in ruby_groups:
        run = _find_start(reading, base_indices, anchor_x, anchor_y, len(segments))
        # 數字起點的交叉驗證（見模組說明「兩種錨點交叉驗證」）：原始錨點
        # 選到的起點如果是數字，改用「展開後首個假名字元的 x」重新找一
        # 次；如果這次選到的是漢字，改採這個結果。
        if (run is None or reading[run[0]][0].isdigit()) and first_kana_x is not None:
            alt_run = _find_start(reading, base_indices, first_kana_x, anchor_y, len(segments))
            if alt_run is not None and _is_cjk_ideograph(reading[alt_run[0]][0]):
                run = alt_run
        if run is None:
            continue
        for k, seg_text in enumerate(segments):
            idx = run[k]
            if idx not in kana_by_index:
                kana_by_index[idx] = seg_text
        # `_find_run` 允許跳過底字之間的非底字字元（見該函式說明），這裡
        # 把被跳過的位置也補上空字串——`_merge_blocks` 只認得「索引連續
        # 遞增 1」的區塊，被跳過的位置（例如「山　田」中間的兩個空白）
        # 若留空隙，會被拆成兩個各自獨立的 RubyPair，base 就只剩「山」
        # 跟「田」各自一個字。
        for a, b in zip(run, run[1:]):
            for gap_idx in range(a + 1, b):
                kana_by_index.setdefault(gap_idx, "")

    # 未分段複合詞讀音（見模組說明）：把緊接在一個已配對區塊後面、完全
    # 沒被任何振假名群組配到的漢字併入該區塊（假名留空——讀音字元已經
    # 完整包含在前面的區段裡，只是區段數少於實際涵蓋的漢字數）。最多往
    # 後併 `_JUKUJIKUN_EXTEND_CAP` 個字，避免吃進真正獨立、沒有振假名的
    # 漢字。
    #
    # 只認漢字／々，刻意不含數字：數字廣泛用於清單編號、例句題號（例1、
    # 例2、1)、2)……），緊接在有振假名的漢字後面、自己沒有振假名是常
    # 態（數字本身不需要讀音），若跟漢字一樣可以被這個機制吃掉，
    # 「例」的讀音「れい」會把緊接著的題號「1」「2」一起併入 base，變成
    # 錯誤的 base='例1'／'例2'（06.pdf 實測案例；審查回合把數字納入底
    # 字集合後才會暴露這個交互作用——數字要能單獨被找到（見 `_is_base_
    # char`），但不該被這個「假設緊鄰字元屬於同一個詞」的擴張機制牽連）。
    for block_end in [end for _start, end in _merge_blocks(sorted(kana_by_index))]:
        nxt = block_end + 1
        extended = 0
        while nxt in extendable_index_set and nxt not in kana_by_index and extended < _JUKUJIKUN_EXTEND_CAP:
            # 只在「字距正常」（同一個詞的相鄰漢字，不是換欄）時才擴張——
            # 見 `_has_normal_spacing` 說明（07 課單字表日文欄／中文欄同
            # 一列、彼此沒有文字間隔的排版，例如「旅行」headword 緊接著
            # 右欄解說文字重複出現的「旅行（～を...）」）。
            if not _has_normal_spacing(reading, nxt - 1, 2):
                break
            kana_by_index[nxt] = ""
            nxt += 1
            extended += 1

    # 多位數日期/計數複合詞（見模組說明「數字延續與量詞銜接」）：一個已
    # 配對區塊如果以數字結尾，代表這個數字本身已經被判定為某個振假名區
    # 段的底字（例如「14日」的「1」配到「じゅうよっ」）——但如果讀音其
    # 實涵蓋整個多位數（14）甚至連著後面的量詞/日期漢字（14日→
    # じゅうよっか），只配到「1」會產生 base='1'、kana='じゅうよっ' 這
    # 種錯誤宣稱（審查發現：14 不讀 じゅうよっ，24 不讀 にじゅうよっ
    # か，那是「14日」「24日」的讀音，不是數字本身的）。這裡把區塊向後
    # 延伸：先吃掉緊鄰、屬於同一個多位數的後續數字（不需要跳過任何字
    # 元，兩個數字寫在一起就是同一個號碼，沒有模稜兩可的空間），再視需
    # 要跨過剛好一個非底字字元（通常是排版用的空白）銜接後面的量詞/日期
    # 漢字。跟前面的清單編號排除邏輯不衝突：只有「區塊本身以數字結尾」
    # 才會觸發，「例」這類以漢字結尾的區塊不會被這裡影響。
    for block_end in [end for _start, end in _merge_blocks(sorted(kana_by_index))]:
        if not reading[block_end][0].isdigit():
            continue
        cur = block_end
        extended = 0
        while extended < _JUKUJIKUN_EXTEND_CAP:
            nxt = cur + 1
            if (nxt < len(reading) and reading[nxt][0].isdigit()
                    and nxt not in kana_by_index
                    and _has_normal_spacing(reading, cur, 2)):
                kana_by_index[nxt] = ""
                cur = nxt
                extended += 1
                continue
            # 「target」（通常是量詞/日期漢字，如「日」）可能已經有自己
            # 獨立的振假名（例如 05.pdf「14 日」的「日」有自己的
            # `'  か'` fragment），也可能完全沒有、讀音已經包含在數字自
            # 己的區段裡（例如 15.pdf「24 日」的「日」沒有獨立 fragment，
            # 讀音「か」在主要配對階段就已經跟著「4」一起收下）。兩種情
            # 形都要能把中間的空白橋接起來，差別只在於「target」已有讀
            # 音時不覆寫它。
            skip = cur + 1
            target = skip + 1
            if (skip < len(reading) and target < len(reading)
                    and not _is_base_char(reading[skip][0])
                    and _is_cjk_ideograph(reading[target][0])
                    and skip not in kana_by_index
                    and _has_normal_spacing(reading, cur, 3)):
                kana_by_index[skip] = ""
                kana_by_index.setdefault(target, "")
                cur = target
                extended += 2
                continue
            break

    # 鏡像情況（複審全語料庫稽核找出的殘留缺陷）：上面那段擴張只處理
    # 「已配對區塊本身以數字結尾」（14→日、24→日）；沒有處理鏡像方
    # 向——區塊以**漢字**結尾，後面緊接著「還沒被配到的數字」再接漢字
    # （「月」+「6」+「日」、「月」+「1」+「日」）。05.pdf「4月6日」
    # 「9月1日」正是這個形狀：「月」的振假名是單一未分段區段
    # （'がつむい'／'がつついたち'），實際涵蓋整個「月N日」，但「6」／
    # 「1」這個數字夾在中間、自己沒有振假名，前面的擴張邏輯不會處理
    # （它只在區塊「以數字結尾」時觸發），導致 base='月' 卻帶著整個
    # 「月N日」的讀音——跟已修好的「980円」「14日」是同一個缺陷類別，
    # 只是方向相反。
    #
    # 這裡採「先確認整條路徑合法、再一次提交」而非逐步貪婪擴張：只有在
    # 緊接著至少 1 個數字、且這個數字（或多位數字）之後（直接相鄰或跳
    # 過剛好 1 個非底字字元）能接上一個漢字時，才把「數字＋（可能的跳
    # 過字元）＋漢字」一次全部併入。**刻意要求「後面必須接得上漢字」這
    # 個條件**——單純「後面是數字」不足以觸發，數字後面接不上漢字（例
    # 如「例1：」的「1」後面是「：」，再後面是「（」，都不是漢字）就不
    # 會誤觸發，維持「例1」「例2」原本的正確排除；也因為要求「先看得到
    # 完整路徑才提交」，不會像貪婪擴張那樣半途留下不完整的殘餘標記。
    #
    # **`block_end` 的字元被刻意限制在 `_COUNTER_BRIDGE_KANJI` 這個白名
    # 單，不是任何漢字都放行**：全語料庫掃描發現，如果不限制，這個機制
    # 會誤觸發在「今9時半」（今→いま，緊接著「9」再接「時」——但「今」
    # 是「現在」的意思，跟後面的「9時」是兩個獨立詞，不是像「月」那樣真
    # 的屬於同一個複合詞）、「毎日9時」（毎日＝每天，同樣是獨立的時間副
    # 詞）——這些案例會產生 base='今9時半'、kana='いまじはん'，「9」既
    # 沒有自己的讀音，也不屬於「いまじはん」這個宣稱的一部分，是跟
    # 「980円」同一類的假配對。「月」（月＋N＋日）與「時」（時＋N＋分，
    # 例如「4時5分」）是全語料庫裡唯二真正需要這個橋接的漢字——量詞/日
    # 期用語裡，數字前後的漢字本身就是那個數字的「計量單位」，跟「今」
    # 「毎日」「朝」這類獨立語意的時間副詞在語法上完全不同，但沒有找到
    # 純幾何/結構的訊號可以自動分辨兩者，只能用白名單限制範圍——這是刻
    # 意的保守選擇，寧可讓白名單外的漢字＋數字＋漢字案例維持配不到（安
    # 全），也不要冒錯配的風險。
    for block_end in [end for _start, end in _merge_blocks(sorted(kana_by_index))]:
        if reading[block_end][0] not in _COUNTER_BRIDGE_KANJI:
            continue
        digit_run: List[int] = []
        probe = block_end + 1
        while (probe < len(reading) and reading[probe][0].isdigit()
                and probe not in kana_by_index):
            digit_run.append(probe)
            probe += 1
        if not digit_run:
            continue
        skip_idx = None
        target = probe
        if not (target < len(reading) and _is_cjk_ideograph(reading[target][0])):
            skip_idx = probe
            target = probe + 1
            if not (skip_idx < len(reading) and target < len(reading)
                    and not _is_base_char(reading[skip_idx][0])
                    and _is_cjk_ideograph(reading[target][0])):
                continue
        # 規則讀音日期不橋接（複審全語料庫稽核找出的假配對，跟「鏡像情
        # 況」是同一段程式碼但需要額外排除的反例）：上面「鏡像情況」的
        # 出發點是「月」的振假名有時會直接把後面數字的讀音吃掉一部分
        # （「がつむい」「がつついたち」），這時候「日」要嘛完全沒有自
        # 己的振假名（がつついたち已經含完，9月1日），要嘛只剩讀音尾巴
        # （「か」，4月6日──單獨看「日」讀「か」是錯的，「か」只有跟前
        # 面湊起來才是完整讀音），兩種情形都必須橋接才不會產生錯誤或不
        # 完整的宣稱。
        #
        # 但全語料庫稽核發現「月」＋規則讀音日期（13、17、20、21、25、
        # 30 日……這些不需要死背、跟著數字本身讀音走的日子）也會落入同
        # 一段程式碼：這種情形「日」本身早就在主配對階段獨立配到一組完
        # 整、正確、可以自己成立的讀音——標準讀音「にち」（例如
        # 05.pdf「3月25日」：「月」自己的振假名只有「がつ」，「日」自
        # 己的振假名是獨立的一個 fragment『にち』，中間的「25」本來就沒
        # 有振假名，因為規則讀音不需要標）。這種情形如果照樣橋接，會把
        # 兩個各自正確、各自完整的讀音（月→がつ、日→にち）硬併成一個
        # 錯誤宣稱 base='月25日'、kana='がつにち'——「25」的讀音完全消
        # 失不見，而「がつにち」本身根本不是任何人會唸的音。這正是簡報
        # 「寧可不配對，也不要產生錯誤配對」的核心案例：不橋接，維持兩
        # 個獨立、各自正確的 RubyPair（月→がつ、日→にち），遠比橋接出
        # 一個消音又唸不出來的假讀音安全。
        #
        # 判別依據：**「日」已經獨立配到的讀音本身是不是一個完整、正確
        # 的『日』單獨讀音**——にち（規則讀音日期唯一會出現的獨立日讀
        # 音；不規則讀音絕不會單獨產生「にち」這個尾音，みっか、むい
        # か、よっか、いつか、はつか、ついたち、とおか、なのか、ここの
        # か、ようか、にじゅうよっか──沒有一個以「にち」結尾）。這是內
        # 容判定，不是幾何判定：「がつ」（月自己的讀音，25 日這個案例）
        # 跟「がつむい」（月自己的讀音，6 日這個案例）在 fragment 的錨
        # 點/座標結構上完全一樣（都是單一未分段區段，錨點就在「月」本
        # 身正上方），純幾何找不出任何能區分兩者的訊號——已實測驗證：兩
        # 種情形下振假名 group 的錨點/y 座標/字級模式无法區分，唯一的差
        # 別是實際印出來的假名內容本身，因此這裡選擇用內容判定，不是幾
        # 何判定。
        #
        # 全語料庫掃描交叉驗證：11月16日（じゅうろくにち，規則讀音）的
        # 「日」也獨立配到「にち」，這裡的判定同樣會擋下橋接，維持兩個
        # 獨立正確的配對（月→がつ、日→にち）——這個案例剛好也被既有的
        # 「安全閥」（比較數字錨點距離）意外擋下來過，兩道判斷在這裡結
        # 果一致，但安全閥本身不可靠（06.pdf 系列的規則讀音案例，數字跟
        # 「月」自己讀音錨點的距離超過 RUBY_X_MAX_DIST，安全閥完全不會
        # 檢查到，這裡的內容判定才是真正擋下錯誤橋接的機制）。
        target_ch = reading[target][0]
        if (target_ch in _REGULAR_TARGET_READING
                and kana_by_index.get(target) == _REGULAR_TARGET_READING[target_ch]):
            continue
        # 安全閥：如果被吸收的數字自己旁邊就有一個振假名 fragment 的錨
        # 點、而且那個錨點離這個數字比離 target 更近，代表這個數字本來
        # 就該有自己的讀音（fragment 明顯是衝著它來的），只是配對邏輯
        # 目前解不出來——這種情況下不要用空字串默默吞掉它，寧可讓這個
        # 區塊維持原狀（不擴張）。實測案例：04.pdf「７月２日」，「２
        # 日」的振假名是單一 fragment `'  ふ つ か'`（3 個區段，錨點在
        # 「２」正上方），但只有「２」「日」兩個底字可用，區段數（3）多
        # 於底字數（2）這種「過度分段」目前的 `_find_run` 解不出來，整
        # 組配不到；如果沒有這道安全閥，鏡像擴張會誤把「月」的區塊延伸
        # 到「月２日」、卻只帶著「がつ」，等於宣稱「月２日」整體讀
        # 「がつ」——這比「月」單獨讀「がつ」（配不到「２日」但沒有錯誤
        # 宣稱）更糟。**跟 target 比較距離**這一步很重要：05.pdf「4月6
        # 日」的「日」自己的 `'  か'` fragment 錨點剛好也落在「6」的門
        # 檻範圍內（只差 6.6pt），但那個錨點離「日」本身的距離是 0——比
        # 較距離後看得出這個 fragment 其實是衝著「日」（target）來的、
        # 已經成功配對，不是「6」的孤兒讀音，不該觸發安全閥。
        if any(
            abs(anchor_y - (reading[d][2].y + RUBY_Y_OFFSET)) <= RUBY_Y_TOL
            and abs(anchor_x - reading[d][1]) <= RUBY_X_MAX_DIST
            and abs(anchor_x - reading[d][1]) <= abs(anchor_x - reading[target][1])
            for d in digit_run
            for anchor_x, anchor_y, _segments, _first_kana_x in ruby_groups
        ):
            continue
        path = digit_run + ([skip_idx] if skip_idx is not None else []) + [target]
        prev = block_end
        normal = True
        for idx in path:
            if not _has_normal_spacing(reading, prev, 2):
                normal = False
                break
            prev = idx
        if not normal:
            continue
        for idx in digit_run:
            kana_by_index[idx] = ""
        if skip_idx is not None:
            kana_by_index[skip_idx] = ""
        kana_by_index.setdefault(target, "")

    matched_indices = sorted(kana_by_index)

    pairs: List[RubyPair] = []
    text = line.text()
    for start, end in _merge_blocks(matched_indices):
        for s, e in _split_by_geometry(reading, start, end):
            kana = "".join(kana_by_index[idx] for idx in range(s, e + 1))
            pairs.append(RubyPair(base=text[s:e + 1], kana=kana, at=s))

    return pairs


def _split_by_geometry(
    reading: List[Tuple[str, float, Fragment]], start: int, end: int
) -> List[Tuple[int, int]]:
    """把一個「索引連續」的區塊（`_merge_blocks` 的輸出）依照實際幾何間
    距進一步拆開，回傳可能不只一段的 (start, end) 清單。

    `_merge_blocks` 只看索引是不是連續整數，不看版面上的實際距離——這
    在**兩個各自獨立配對成功、彼此都正確**的字元剛好在讀出順序上相鄰
    （索引連續）時會出問題：08.pdf 代入練習「1)大阪城静か」，「大阪
    城」（おおさかじょう，正確）跟後面代換用的形容詞「静」（しず，也正
    確，是同一列代入練習的另一個獨立欄位，兩者之間版面上其實相隔
    84pt，遠超過同一個詞內字元間距的量級）剛好落在讀出順序上緊鄰的索
    引，`_merge_blocks` 因此把兩個本來正確、各自獨立的讀音硬拼成一個
    `RubyPair`（base='大阪城静'、kana='おおさかじょうしず'）——雖然拼起
    來的 kana 沒有任何一個字元是錯的，但把兩個無關欄位的內容黏在一起，
    等於讓查詢「大阪城」或「静」個別讀音的下游用途查不到獨立條目，跟
    「今　何」被誤合併是同一類問題。

    這裡在建構最終 `RubyPair` 之前，對每個索引連續的區塊，逐步比對相鄰
    位置的幾何間距（沿用 `_has_normal_spacing` 的比例），間距不正常就
    切開——前面的擴張機制（`_JUKUJIKUN_EXTEND_CAP` 等）在「填入」空白/
    跳過字元時已經各自檢查過幾何間距，這裡的切分不會影響那些已經驗證
    過的合法擴張，只會把「原本就沒有經過任何擴張檢查、純粹因為索引相鄰
    而被 `_merge_blocks` 誤連在一起」的情形分開。"""
    boundaries = [start]
    for idx in range(start, end):
        if not _has_normal_spacing(reading, idx, 2):
            boundaries.append(idx + 1)
    boundaries.append(end + 1)
    return [(boundaries[i], boundaries[i + 1] - 1) for i in range(len(boundaries) - 1)]


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
