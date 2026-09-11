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

## 底字不只是漢字：々、數字

第一版只認 CJK 表意文字當底字，審查後補上兩類：
`々`（U+3005 IDEOGRAPHIC ITERATION MARK，「時々」「別々」這類疊字詞需要
自己的讀音）與阿拉伯數字（「7つ」「3か月」「10分」這類量詞/時間表達，
振假名標在數字本身上面）。詳見 `_is_base_char`。

## 兩種錨點交叉驗證：純數字起點必須跟「展開後首字元」的結果一致

`Fragment.x`（原始錨點，`_find_start` 預設用來找起點）對「短讀音、寬底
字」的情形是對的（見上面「太郎君」的推導），但對「底字前面還有好幾個不
需要讀音的字元」的情形會系統性選錯——例如 13.pdf「980円」，振假名只有
一個區段「えん」（對應「円」），但 fragment 本身有 9 個前導半形空白
（用來把「えん」推到「円」正上方），這些空白的寬度剛好讓 `Fragment.x`
數值跟「9」（980 的第一位數字）的 x 座標幾乎重合（差 0.0006pt），而展
開後第一個假名字元「え」的實際座標離「円」只有 1.8pt、離「9」卻有
21.6pt——兩種算法在這裡給出完全相反的答案，跟「太郎君」的「た」離「郎」
比離「太」近的情形是同一種「短讀音被前導空白推移」的現象，只是這次移動
的方向、幅度不同（太郎君是被推向「下一個」底字，980円是被推向「前面」
一整串不需要讀音的數字）。

兩種情形無法用同一套規則同時處理對（實測驗證：改用展開後座標會讓「太郎
君」重新配錯；固定用原始錨點會讓「980円」配錯），所以採取交叉驗證：
**只有在原始錨點選到的起點是數字時**，才額外用展開後首字元的座標重找一
次；如果這次找到的起點是漢字，改採這個結果。這個條件只在「原始選到數
字」時觸發，不會影響「10日」「1週間」這類數字本身就是正確起點的案例
（展開後座標在這些案例上跟原始錨點指向同一個起點，不會被覆蓋——見
`tests/extract/test_ruby.py` 的迴歸測試逐一鎖住兩邊的案例）。
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
    者差距懸殊，用「正文字級的 2 倍」當上限就能可靠分開。"""
    for k in range(n - 1):
        _prev_ch, prev_x, prev_f = reading[start + k]
        _next_ch, next_x, _next_f = reading[start + k + 1]
        if next_x - prev_x > _MAX_NORMAL_GAP_RATIO * prev_f.size:
            return False
    return True


_TIE_EPS = 1.0   # 見 `_find_start` 說明：兩個候選幾何距離「理論上相等」
                 # （例如「毎朝」的「毎」「朝」離振假名錨點在視覺上都恰
                 # 好是半個字寬，理應平手），但實測兩者算出來的 x 差距
                 # 分別是 6.600360 與 6.599640——差了 0.00072pt，遠超過
                 # 純浮點捨入誤差（雙精度連加幾十次的量級是 1e-11 以
                 # 下），推測是 `char_width` 對不同字元四捨五入到
                 # 0.5/1.0 倍字級這種離散模型，在長行裡累加多次後產生的
                 # 系統性次像素偏移——這種偏移本身就不具備「兩個候選誰
                 # 真的比較近」的意義，不該拿來決定選哪個當起點。06.pdf
                 # 「毎朝　7時半」「毎朝　英語」都曾因此選到「朝」而非
                 # 「毎」當起點，讓允許跳過空白的 `_find_run` 沿著空白一
                 # 路跳到不相干的下一個詞（審查回合新增的跳過機制才會暴
                 # 露這個問題——舊版嚴格相鄰判定即使選錯起點也會直接判
                 # 定無效，沒有這道安全網就會暴露出來）。1.0pt 遠大於這
                 # 類次像素噪音，也遠小於任何字元間有意義的距離差（相鄰
                 # 字元間距至少 6.6pt 起跳），可以安全地把「視覺上同樣
                 # 近」的候選視為平手，改依讀出順序（x 較小者優先）決
                 # 定。

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

    只允許跳過「剛好 1 個非空白字元」還需要一個逐步幾何間距檢查（沿用
    `_has_normal_spacing` 的比例），排除真正的換行/換欄跳躍——不然
    「図書館」的振假名可能從「書」這個起點沿著 `館→へ→行` 這類只隔一個
    假名的路徑「跳」到下一個詞。"""
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
