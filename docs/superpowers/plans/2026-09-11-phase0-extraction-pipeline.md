# Phase 0：課本抽取管線 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把「大家的日本語」第 1 ~ 15 課的 PDF 轉成結構化 JSON 題庫素材，含單字、句子、振假名、句型代入表與文法解說，並以自動不變式檢查與版面視覺對照驗證品質。

**Architecture:** 三階段管線，字串化是最後一步。階段一解析 PDF 得到帶座標的文字片段（Fragment）；階段二在座標層做行分組、欄位切分、振假名配對、區段切分；階段三才序列化為 JSON。原型的所有缺陷都源於過早把文字壓平成字串而丟失位置資訊，此架構即為修正。

**Tech Stack:** Python 3.9.6（僅標準函式庫：`re`、`zlib`、`json`、`dataclasses`、`unittest`）。無 pytest、無 pip 套件、無 PDF 函式庫。視覺驗證用 macOS 內建 `swift` + PDFKit（`tools/render.swift`，已存在）。

**Spec:** `docs/superpowers/specs/2026-09-10-japanese-practice-design.md`

## Global Constraints

- **Python 3.9.6，僅標準函式庫。** 不得 `pip install`。不得使用 3.10+ 語法（無 `match`、無 `X | Y` 型別聯集，用 `typing.Optional` / `typing.Union`）。
- **測試框架為 `unittest`**（pytest 不存在）。從專案根目錄執行：`python3 -m unittest discover -s tests -t . -v`
- **絕不修改專案根目錄的 `*.pdf` 與 `*.jpeg`**，它們是唯讀來源。
- **編碼對應**（實測確認，不可寫死字型代號）：`/Encoding` 含 `RKSJ` 或 `90ms` → `cp932`；含 `GBK` 或 `GB-` → `gb18030`；`WinAnsiEncoding` → `cp1252`。
- **誤解碼指紋**：若輸出出現 `偁偄偆偊偍偐偑偒偓偔偕偖偗偘偙偠偡偣偤偦偨偩偪偭偮偯偰偱偲偵偲偼偄` 一類罕見漢字，代表 Shift-JIS 位元組被誤用 GB18030 解讀。驗證步驟必須偵測此情形。
- **PDF 結構有多種變體**（實測）：`07.pdf` 為 PDF 1.3，9 個明文 Page 物件，0 個 ObjStm；`11.pdf` 為 PDF 1.6，**0 個明文 Page 物件、16 個 ObjStm**；`13.pdf` 為 PDF 1.7，9 個明文 Page 物件**且** 14 個 ObjStm（混合）。物件層必須同時支援明文物件與壓縮物件流。
- **提交訊息結尾**必須附上：
  ```
  Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01QazTpwM3ApzPa47zWjy26D
  ```

---

## File Structure

```
tools/
  __init__.py                 空檔，使 tools 成為套件
  render.swift                （已存在）PDF 頁面算繪，視覺驗證用
  extract/
    __init__.py               空檔
    pdfobj.py     PDF 物件層：xref、明文物件、ObjStm、頁面 content 與 Resources
    fonts.py      字型名 → 編碼對應；十六進位字串解碼
    fragments.py  內容流 → Fragment[]（text, x, y, size, font, page）
    layout.py     Fragment → Line；Line → Cell[]（欄位切分）
    ruby.py       振假名配對
    sections.py   區段切分（ことば/文型/例文/会話/練習ＡＢＣ/問題/文法）
    vocab.py      單字表解析（含 usage 子行）
    sentences.py  句子解析（含 alt 替代形）
    patterns.py   練習Ａ 代入表 → 模板 + 槽位；練習Ｂ 變換題
    grammar.py    文法解說（日中交錯）
    images.py     插畫影像抽取
    validate.py   不變式檢查
    cli.py        命令列入口
tests/
  __init__.py                 空檔
  extract/
    __init__.py               空檔
    test_pdfobj.py  test_fonts.py  test_fragments.py  test_layout.py
    test_ruby.py    test_sections.py  test_vocab.py   test_sentences.py
    test_patterns.py  test_grammar.py  test_validate.py  test_golden.py
data/
  lessons/01.json … 15.json   產出
  images/                     產出：抽出的插畫
```

**依賴方向為單向**：`pdfobj` ← `fonts` ← `fragments` ← `layout` ← {`ruby`, `sections`} ← {`vocab`, `sentences`, `patterns`, `grammar`} ← `cli`。`validate` 只依賴產出的 JSON，不依賴任何解析模組。

**可平行執行的任務**：Task 7 ~ 11（vocab / sentences / patterns / grammar / images）彼此獨立，皆只依賴 Task 1 ~ 6 的成果，可分派給不同 subagent 同時進行。Task 1 ~ 6 必須依序完成。

---

## Task 1: PDF 物件層

**Files:**
- Create: `tools/__init__.py`, `tools/extract/__init__.py`, `tools/extract/pdfobj.py`
- Create: `tests/__init__.py`, `tests/extract/__init__.py`, `tests/extract/test_pdfobj.py`

**Interfaces:**
- Consumes: 無
- Produces:
  ```python
  @dataclass
  class Page:
      number: int        # 1-based
      content: bytes     # 已解壓並串接的內容流
      resources: bytes   # /Resources 字典的原始位元組（含外層 << >>）

  class PDFDoc:
      @classmethod
      def from_path(cls, path: str) -> "PDFDoc"
      def get_object(self, num: int) -> bytes   # 物件本體位元組（不含 "N 0 obj"/"endobj"）
      @property
      def pages(self) -> List[Page]
  ```

- [ ] **Step 1: 建立套件骨架**

```bash
mkdir -p tools/extract tests/extract data/lessons
touch tools/__init__.py tools/extract/__init__.py tests/__init__.py tests/extract/__init__.py
```

- [ ] **Step 2: 寫失敗的測試**

`tests/extract/test_pdfobj.py`：

```python
import unittest
from tools.extract.pdfobj import PDFDoc


class TestPDFDoc(unittest.TestCase):
    def test_plain_pdf_page_count(self):
        """07.pdf 是 PDF 1.3、9 頁、無壓縮物件流。"""
        doc = PDFDoc.from_path("07.pdf")
        self.assertEqual(len(doc.pages), 9)

    def test_objstm_pdf_page_count(self):
        """11.pdf 是 PDF 1.6，Page 物件全在壓縮物件流裡，明文找不到。"""
        doc = PDFDoc.from_path("11.pdf")
        self.assertEqual(len(doc.pages), 9)

    def test_mixed_pdf_page_count(self):
        """13.pdf 同時有明文物件與壓縮物件流。"""
        doc = PDFDoc.from_path("13.pdf")
        self.assertEqual(len(doc.pages), 9)

    def test_pages_have_content_and_resources(self):
        doc = PDFDoc.from_path("07.pdf")
        first = doc.pages[0]
        self.assertEqual(first.number, 1)
        self.assertIn(b"BT", first.content)
        self.assertIn(b"/Font", first.resources)

    def test_page_one_font_resource_names(self):
        """實測值：07.pdf 第 1 頁的 /Font 資源為 /TT2 /TT4 /TT5。"""
        doc = PDFDoc.from_path("07.pdf")
        res = doc.pages[0].resources
        for name in (b"/TT2", b"/TT4", b"/TT5"):
            self.assertIn(name, res)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: 執行測試確認失敗**

Run: `python3 -m unittest tests.extract.test_pdfobj -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'tools.extract.pdfobj'`

- [ ] **Step 4: 實作 `tools/extract/pdfobj.py`**

關鍵實作要點：

1. **建立物件表**：先掃描全檔的明文物件 `re.finditer(rb'(\d+)\s+0\s+obj(.*?)endobj', data, re.S)`，存入 `{num: body}`。
2. **解壓物件流**：找出所有 `/Type /ObjStm` 的物件，其 stream 解壓後格式為「前 `N` 組 `objnum offset` 整數對，接著從 `/First` 位移起是各物件本體」。將解出的物件併入物件表（**明文物件優先，不覆蓋**）。
3. **找 Pages tree**：從 `/Type /Catalog` 取 `/Pages`，遞迴展開 `/Kids`；若找不到 Catalog，退回掃描所有 `/Type /Page` 物件並依物件編號排序。
4. **Resources 繼承**：頁面若無 `/Resources`，沿 `/Parent` 向上找。`/Resources` 可能是間接參照（`12 0 R`）或**直接內嵌字典**（13.pdf 第一頁即如此），兩者都要支援。
5. **內容流**：`/Contents` 可為單一參照或陣列，全部取出、各自 `zlib.decompress`（失敗則視為未壓縮原樣使用）後以 `b"\n"` 串接。

括號平衡的字典擷取（內嵌字典必需）：

```python
def extract_balanced_dict(data: bytes, start: int) -> bytes:
    """從 data[start] 的 '<<' 開始，回傳含外層 << >> 的完整字典位元組。"""
    assert data[start:start + 2] == b"<<"
    depth = 0
    i = start
    while i < len(data) - 1:
        pair = data[i:i + 2]
        if pair == b"<<":
            depth += 1
            i += 2
            continue
        if pair == b">>":
            depth -= 1
            i += 2
            if depth == 0:
                return data[start:i]
            continue
        i += 1
    raise ValueError("unbalanced dictionary")
```

物件流解析：

```python
def _parse_objstm(self, body: bytes, stream: bytes) -> None:
    n = int(re.search(rb"/N\s+(\d+)", body).group(1))
    first = int(re.search(rb"/First\s+(\d+)", body).group(1))
    header = stream[:first].split()
    for k in range(n):
        num = int(header[2 * k])
        off = int(header[2 * k + 1])
        end = int(header[2 * k + 3]) + first if k + 1 < n else len(stream)
        if num not in self._objects:          # 明文物件優先
            self._objects[num] = stream[first + off:end]
```

- [ ] **Step 5: 執行測試確認通過**

Run: `python3 -m unittest tests.extract.test_pdfobj -v`
Expected: 5 tests PASS

- [ ] **Step 6: 提交**

```bash
git add tools/ tests/
git commit -m "feat(extract): PDF 物件層，支援明文物件與壓縮物件流

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QazTpwM3ApzPa47zWjy26D"
```

---

## Task 2: 字型編碼對應

**Files:**
- Create: `tools/extract/fonts.py`
- Create: `tests/extract/test_fonts.py`

**Interfaces:**
- Consumes: `PDFDoc`, `Page`（Task 1）
- Produces:
  ```python
  def font_encodings(doc: PDFDoc, page: Page) -> Dict[str, str]
      # {'TT2': 'cp932', 'TT4': 'gb18030', 'TT5': 'cp1252'}
  def decode_hex(hex_str: str, encoding: str) -> str
  ```

- [ ] **Step 1: 寫失敗的測試**

`tests/extract/test_fonts.py`：

```python
import unittest
from tools.extract.pdfobj import PDFDoc
from tools.extract.fonts import font_encodings, decode_hex


class TestFonts(unittest.TestCase):
    def test_lesson07_page1_encodings(self):
        """實測：07.pdf 的 TT2 是 MSGothic/90ms-RKSJ-H，TT4 是 SimSun/GBK-EUC-H。"""
        doc = PDFDoc.from_path("07.pdf")
        enc = font_encodings(doc, doc.pages[0])
        self.assertEqual(enc["TT2"], "cp932")
        self.assertEqual(enc["TT4"], "gb18030")

    def test_decode_japanese(self):
        self.assertEqual(decode_hex("82b182c682ce", "cp932"), "ことば")

    def test_decode_chinese(self):
        self.assertEqual(decode_hex("b5daa3b1d56e", "gb18030"), "第１課")

    def test_all_lessons_have_both_encodings(self):
        """1~15 課每一課都必須同時偵測到日文與中文字型，否則必有一半內容遺失。"""
        for n in range(1, 16):
            doc = PDFDoc.from_path("%02d.pdf" % n)
            found = set()
            for page in doc.pages:
                found.update(font_encodings(doc, page).values())
            self.assertIn("cp932", found, "第 %d 課缺日文字型" % n)
            self.assertIn("gb18030", found, "第 %d 課缺中文字型" % n)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python3 -m unittest tests.extract.test_fonts -v`
Expected: FAIL — `No module named 'tools.extract.fonts'`

- [ ] **Step 3: 實作 `tools/extract/fonts.py`**

```python
import re
from typing import Dict

_ENCODING_RULES = (
    (("RKSJ", "90MS", "90MSP"), "cp932"),
    (("GBK", "GB-", "GBPC", "GBKP"), "gb18030"),
    (("WINANSI",), "cp1252"),
)


def _encoding_from_name(name: str) -> str:
    upper = name.upper()
    for needles, enc in _ENCODING_RULES:
        for needle in needles:
            if needle in upper:
                return enc
    return "cp1252"


def font_encodings(doc, page) -> Dict[str, str]:
    """回傳 {字型資源名(去掉斜線): python 編碼名}。"""
    result = {}
    block = re.search(rb"/Font\s*(<<.*?>>)", page.resources, re.S)
    if not block:
        return result
    for m in re.finditer(rb"/(\w+)\s+(\d+)\s+0\s+R", block.group(1)):
        res_name = m.group(1).decode("latin-1")
        body = doc.get_object(int(m.group(2)))
        enc = re.search(rb"/Encoding\s*/([\w-]+)", body)
        if enc:
            result[res_name] = _encoding_from_name(enc.group(1).decode("latin-1"))
        else:
            base = re.search(rb"/BaseFont\s*/([^\s/>\]]+)", body)
            name = base.group(1).decode("latin-1") if base else ""
            result[res_name] = "cp932" if "Gothic" in name or "Mincho" in name else "cp1252"
    return result


def decode_hex(hex_str: str, encoding: str) -> str:
    if len(hex_str) % 2:
        hex_str += "0"
    return bytes.fromhex(hex_str).decode(encoding, errors="replace")
```

- [ ] **Step 4: 執行測試確認通過**

Run: `python3 -m unittest tests.extract.test_fonts -v`
Expected: 4 tests PASS

- [ ] **Step 5: 提交**

```bash
git add tools/extract/fonts.py tests/extract/test_fonts.py
git commit -m "feat(extract): 由 /Encoding 判定字型編碼，涵蓋 1~15 課

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QazTpwM3ApzPa47zWjy26D"
```

---

## Task 3: Fragment 抽取（保留座標）

**Files:**
- Create: `tools/extract/fragments.py`
- Create: `tests/extract/test_fragments.py`

**Interfaces:**
- Consumes: `PDFDoc`, `Page`（Task 1）、`font_encodings`, `decode_hex`（Task 2）
- Produces:
  ```python
  @dataclass
  class Fragment:
      text: str
      x: float
      y: float
      size: float
      font: str     # 資源名，如 'TT2'
      page: int     # 1-based

  def extract_fragments(doc: PDFDoc) -> List[Fragment]
  def page_fragments(doc: PDFDoc, page: Page) -> List[Fragment]
  ```

- [ ] **Step 1: 寫失敗的測試**

`tests/extract/test_fragments.py`：

```python
import unittest
from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments


class TestFragments(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frags = extract_fragments(PDFDoc.from_path("07.pdf"))

    def test_has_kotoba_heading(self):
        heads = [f for f in self.frags if f.text.strip() == "ことば"]
        self.assertTrue(heads, "找不到『ことば』標題")

    def test_first_vocab_entry_present(self):
        texts = "".join(f.text for f in self.frags if f.page == 1)
        for expected in ("きります", "切ります", "剪"):
            self.assertIn(expected, texts)

    def test_fragments_carry_coordinates(self):
        for f in self.frags[:50]:
            self.assertIsInstance(f.x, float)
            self.assertIsInstance(f.y, float)
            self.assertGreater(f.size, 0.0)

    def test_ruby_fragments_are_smaller(self):
        """振假名為 4.8pt 小字；正文為 10pt 以上。兩種字級必須都存在。"""
        sizes = {round(f.size, 1) for f in self.frags}
        self.assertTrue(any(s <= 6.0 for s in sizes), "找不到小字級（振假名）")
        self.assertTrue(any(s >= 10.0 for s in sizes), "找不到正文字級")

    def test_no_misdecoding_fingerprint(self):
        """Shift-JIS 被誤讀為 GB18030 會產生這些罕見漢字。"""
        text = "".join(f.text for f in self.frags)
        for bad in "偁偄偆偊偍偐偑偒偓偔偕偖偗偘偙偠偡偣偤偦偨偩偪偭偮偯偰偱偲偵偼":
            self.assertNotIn(bad, text, "偵測到誤解碼指紋：%s" % bad)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python3 -m unittest tests.extract.test_fragments -v`
Expected: FAIL — `No module named 'tools.extract.fragments'`

- [ ] **Step 3: 實作 `tools/extract/fragments.py`**

要點：逐一掃描內容流的運算子，維護目前字型與文字矩陣。

- `/NAME size Tf` → 切換字型（size 通常為 1，實際字級由 Tm 的 a、d 決定）
- `a b c d e f Tm` → 設定文字矩陣：`x = e`、`y = f`、`size = d`
- `tx ty Td` / `TD` → 相對位移，累加到目前 x、y
- `T*` 與行距 `TL` → 換行位移
- `<hex> Tj` → 產生一個 Fragment
- `[ <hex> num <hex> ... ] TJ` → 陣列中的每個十六進位字串各產生一個 Fragment；其間的數字為字距調整，單位為 1/1000 文字空間，需累加到 x：`x -= num / 1000.0 * size`
- `BT` 重設文字矩陣

**每個十六進位字串產生一個 Fragment，不要合併**——後續的欄位切分與振假名配對都依賴細粒度的 x 座標。

```python
_TOKEN = re.compile(rb"""
    /(?P<font>[A-Za-z0-9]+)\s+[\d.]+\s+Tf
  | (?P<tm>[-\d.]+\s+[-\d.]+\s+[-\d.]+\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+))\s+Tm
  | (?P<td>[-\d.]+\s+[-\d.]+)\s+(?P<tdop>TD|Td)
  | <(?P<tj>[0-9A-Fa-f]+)>\s*Tj
  | \[(?P<tjarr>[^\]]*)\]\s*TJ
  | (?P<bt>BT)
  | (?P<tstar>T\*)
  | (?P<tl>[-\d.]+)\s+TL
""", re.X)
```

- [ ] **Step 4: 執行測試確認通過**

Run: `python3 -m unittest tests.extract.test_fragments -v`
Expected: 5 tests PASS

- [ ] **Step 5: 對 1~15 課全數執行，確認不崩潰**

```bash
python3 -c "
from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments
for n in range(1,16):
    d=PDFDoc.from_path('%02d.pdf'%n)
    fs=extract_fragments(d)
    print('%02d.pdf 頁數=%d fragments=%d'%(n,len(d.pages),len(fs)))
"
```
Expected: 15 行輸出，每課 fragments 數量皆 > 500

- [ ] **Step 6: 提交**

```bash
git add tools/extract/fragments.py tests/extract/test_fragments.py
git commit -m "feat(extract): 內容流轉為帶座標的 Fragment，保留位置資訊

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QazTpwM3ApzPa47zWjy26D"
```

---

## Task 4: 版面分組（行與欄）

**Files:**
- Create: `tools/extract/layout.py`
- Create: `tests/extract/test_layout.py`

**Interfaces:**
- Consumes: `Fragment`（Task 3）
- Produces:
  ```python
  @dataclass
  class Cell:
      x: float
      text: str
      frags: List[Fragment]

  @dataclass
  class Line:
      y: float
      page: int
      frags: List[Fragment]          # 已依 x 排序
      def text(self) -> str          # 各 fragment 文字串接（不加分隔）
      def cells(self, min_gap: float = 10.0) -> List[Cell]

  def group_lines(frags: List[Fragment], y_tol: float = 2.0) -> List[Line]
      # 只納入正文字級（size >= 8.0）；振假名由 ruby.py 處理
      # 回傳依 (page, -y) 排序，即閱讀順序
  ```

- [ ] **Step 1: 寫失敗的測試**

`tests/extract/test_layout.py`：

```python
import unittest
from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments
from tools.extract.layout import group_lines


class TestLayout(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.lines = group_lines(extract_fragments(PDFDoc.from_path("07.pdf")))

    def test_reading_order(self):
        """行必須依頁碼遞增、頁內 y 遞減排序。"""
        prev = None
        for ln in self.lines:
            key = (ln.page, -ln.y)
            if prev is not None:
                self.assertGreaterEqual(key, prev)
            prev = key

    def test_vocab_row_splits_into_three_cells(self):
        """單字列有三欄：假名、漢字、中文。"""
        target = None
        for ln in self.lines:
            if "きります" in ln.text() and "切ります" in ln.text():
                target = ln
                break
        self.assertIsNotNone(target, "找不到第 1 筆單字所在行")
        cells = target.cells()
        texts = [c.text.strip() for c in cells]
        self.assertIn("きります", texts)
        self.assertIn("切ります", texts)
        self.assertTrue(any("剪" in t for t in texts))

    def test_kana_only_entry_has_empty_kanji_column(self):
        """第 3 筆 あげます 沒有漢字，中文欄的 x 必須仍落在第三欄位置。"""
        target = None
        for ln in self.lines:
            if "あげます" in ln.text():
                target = ln
                break
        self.assertIsNotNone(target)
        xs = [c.x for c in target.cells()]
        self.assertGreaterEqual(len(xs), 2)

    def test_substitution_table_columns_align(self):
        """練習Ａ-2 的三個候選詞必須落在相同 x 欄位。"""
        rows = [ln for ln in self.lines
                if any(w in ln.text() for w in ("にほんご", "えいご", "ちゅうごくご"))]
        self.assertGreaterEqual(len(rows), 3, "找不到練習Ａ-2 的代入表")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python3 -m unittest tests.extract.test_layout -v`
Expected: FAIL — `No module named 'tools.extract.layout'`

- [ ] **Step 3: 實作 `tools/extract/layout.py`**

`group_lines`：過濾 `size >= 8.0` 的 fragment，依 `(page, y)` 分群，同群 y 差距在 `y_tol` 內視為同一行，群內依 x 排序。

`Line.cells`：對已排序的 fragment 逐一比較「前一個 fragment 的右端」與「目前 fragment 的左端」，間距超過 `min_gap` 即切新欄。右端估算為 `x + len(text) * size * 0.9`（CJK 全形字寬約等於字級；此係數在測試中微調至通過）。

```python
def cells(self, min_gap: float = 10.0) -> List["Cell"]:
    out: List[Cell] = []
    cur: List[Fragment] = []
    prev_right = None
    for f in self.frags:
        left = f.x
        if prev_right is not None and left - prev_right > min_gap and cur:
            out.append(Cell(x=cur[0].x, text="".join(g.text for g in cur), frags=cur))
            cur = []
        cur.append(f)
        prev_right = f.x + len(f.text) * f.size * 0.9
    if cur:
        out.append(Cell(x=cur[0].x, text="".join(g.text for g in cur), frags=cur))
    return out
```

- [ ] **Step 4: 執行測試確認通過**

Run: `python3 -m unittest tests.extract.test_layout -v`
Expected: 4 tests PASS

- [ ] **Step 5: 提交**

```bash
git add tools/extract/layout.py tests/extract/test_layout.py
git commit -m "feat(extract): 行分組與欄位切分，修正原型的表格錯位問題

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QazTpwM3ApzPa47zWjy26D"
```

---

## Task 5: 振假名配對

**Files:**
- Create: `tools/extract/ruby.py`
- Create: `tests/extract/test_ruby.py`

**Interfaces:**
- Consumes: `Fragment`（Task 3）、`Line`（Task 4）
- Produces:
  ```python
  RUBY_MAX_SIZE = 6.0      # 振假名字級 4.8pt；正文 10pt 以上
  RUBY_Y_OFFSET = 12.0     # 振假名 y 比漢字高 12.0pt（PDF 座標 y 軸向上 = 視覺在上方）
  RUBY_Y_TOL = 2.5
  RUBY_X_MAX_DIST = 11.0

  @dataclass
  class RubyPair:
      base: str      # 漢字
      kana: str      # 讀音
      at: int        # base 在該行文字中的字元位置

  def pair_ruby(all_frags: List[Fragment], line: Line) -> List[RubyPair]
  ```

- [ ] **Step 1: 寫失敗的測試**

`tests/extract/test_ruby.py`：

```python
import unittest
from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments
from tools.extract.layout import group_lines
from tools.extract.ruby import pair_ruby


class TestRuby(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frags = extract_fragments(PDFDoc.from_path("07.pdf"))
        cls.lines = group_lines(cls.frags)

    def _pairs_for(self, needle):
        for ln in self.lines:
            if needle in ln.text():
                return {p.base: p.kana for p in pair_ruby(self.frags, ln)}
        self.fail("找不到含『%s』的行" % needle)

    def test_multi_syllable_kanji(self):
        """木村 → きむら。原型的 bug 是只取第一個假名，得到『きむ』。"""
        pairs = self._pairs_for("木村さんに")
        self.assertEqual(pairs.get("木村"), "きむら")

    def test_compound_kanji(self):
        """手紙 → てがみ。"""
        pairs = self._pairs_for("手紙を")
        self.assertEqual(pairs.get("手紙"), "てがみ")

    def test_single_kanji(self):
        pairs = self._pairs_for("花を")
        self.assertEqual(pairs.get("花"), "はな")

    def test_base_appears_in_line(self):
        """每個配對的 base 必須真的出現在該行文字中，且 at 位置正確。"""
        for ln in self.lines:
            text = ln.text()
            for p in pair_ruby(self.frags, ln):
                self.assertIn(p.base, text)
                self.assertEqual(text[p.at:p.at + len(p.base)], p.base)

    def test_coverage_rate(self):
        """全課振假名字符的配對率須達 98% 以上。"""
        ruby_chars = sum(len(f.text.strip()) for f in self.frags
                         if f.size <= 6.0 and f.text.strip())
        paired = sum(len(p.kana) for ln in self.lines for p in pair_ruby(self.frags, ln))
        self.assertGreater(ruby_chars, 300, "第 7 課應有 400 個以上振假名字符")
        self.assertGreaterEqual(paired / ruby_chars, 0.98,
                                "配對率僅 %.1f%%" % (100.0 * paired / ruby_chars))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python3 -m unittest tests.extract.test_ruby -v`
Expected: FAIL — `No module named 'tools.extract.ruby'`

- [ ] **Step 3: 實作 `tools/extract/ruby.py`**

演算法（原型已驗證，配對率 99%）：

1. 取出所有 `size <= RUBY_MAX_SIZE` 的 fragment，**逐字元展開**為 `(字元, x, y)`。
2. 對目標行的每個正文字元（同樣逐字元展開，只保留 CJK 表意文字），尋找滿足以下條件的假名字元：
   - `abs(kana.y - (base.y + RUBY_Y_OFFSET)) <= RUBY_Y_TOL`
   - `abs(kana.x - base.x) <= RUBY_X_MAX_DIST`
3. **同一個漢字可對應多個假名**（`木村` 的 `ら` 距離 `村` 8.4pt）。將落在同一漢字上的所有假名**依 x 排序後串接**——原型的 bug 正是只取第一個，導致 `きむら` 變成 `きむ`。
4. 相鄰漢字若各自有假名，合併為一個 `RubyPair`（`手` + `紙` → `手紙`/`てがみ`），判定條件為兩漢字在行內相鄰且皆有假名。
5. `at` 為合併後 base 在 `line.text()` 中的起始索引。

**測試門檻設 98% 而非 100%**：已知有邊緣案例——填空題模板中漢字被代換成 `～` 符號，其振假名找不到可配對的漢字。這是原始版面就沒有對應漢字，非演算法缺陷。

- [ ] **Step 4: 執行測試確認通過**

Run: `python3 -m unittest tests.extract.test_ruby -v`
Expected: 5 tests PASS

- [ ] **Step 5: 提交**

```bash
git add tools/extract/ruby.py tests/extract/test_ruby.py
git commit -m "feat(extract): 振假名配對，處理多音節串接與複合漢字合併

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QazTpwM3ApzPa47zWjy26D"
```

---

## Task 6: 區段切分

**Files:**
- Create: `tools/extract/sections.py`
- Create: `tests/extract/test_sections.py`

**Interfaces:**
- Consumes: `Line`（Task 4）
- Produces:
  ```python
  SECTION_NAMES = ("ことば", "文型", "例文", "会話",
                   "練習Ａ", "練習Ｂ", "練習Ｃ", "問題", "文法")

  @dataclass
  class Section:
      name: str
      lines: List[Line]

  def split_sections(lines: List[Line]) -> List[Section]
  ```

- [ ] **Step 1: 寫失敗的測試**

`tests/extract/test_sections.py`：

```python
import unittest
from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments
from tools.extract.layout import group_lines
from tools.extract.sections import split_sections


class TestSections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lines = group_lines(extract_fragments(PDFDoc.from_path("07.pdf")))
        cls.sections = split_sections(lines)
        cls.by_name = {}
        for s in cls.sections:
            cls.by_name.setdefault(s.name, []).append(s)

    def test_all_expected_sections_present(self):
        for name in ("ことば", "文型", "例文", "会話", "練習Ａ", "練習Ｂ", "練習Ｃ", "問題", "文法"):
            self.assertIn(name, self.by_name, "缺少區段：%s" % name)

    def test_kaiwa_appears_once(self):
        """『会話』標題在課本出現兩次：ことば 頁尾的會話用語小框，以及對話本文。
        原型把兩者都當成新區段，導致会話#1 其實是詞彙註解。"""
        self.assertEqual(len(self.by_name["会話"]), 1,
                         "会話 區段應只有一個，實得 %d 個" % len(self.by_name["会話"]))

    def test_kaiwa_contains_dialogue(self):
        """真正的対話含佐藤與米勒的對白。"""
        text = "".join(ln.text() for ln in self.by_name["会話"][0].lines)
        self.assertIn("佐藤", text)

    def test_sections_in_order(self):
        order = [s.name for s in self.sections]
        self.assertLess(order.index("ことば"), order.index("文型"))
        self.assertLess(order.index("文型"), order.index("例文"))
        self.assertLess(order.index("練習Ａ"), order.index("練習Ｂ"))
        self.assertLess(order.index("問題"), order.index("文法"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python3 -m unittest tests.extract.test_sections -v`
Expected: FAIL — `No module named 'tools.extract.sections'`

- [ ] **Step 3: 實作 `tools/extract/sections.py`**

判定一行是否為區段標題的條件（全部滿足）：

1. 行文字去除空白後**等於**某個區段名（不是「包含」）
2. 該行的字級大於正文字級（標題較大）
3. 區段順序必須遞增——若偵測到的標題其順序早於目前區段，視為誤判並忽略

第 3 條即為 `会話` 重複問題的解法：ことば 頁尾的「会話」小框出現在 `文型` 之前，而正確順序是 `会話` 在 `例文` 之後，因此被順序檢查擋下。若順序檢查仍不足，退回以字級判定（小框標題字級較小）。

同時過濾頁首頁尾：每頁右上角的 `課:7 (頁:1/9)` 與頁尾的 `課頁`，依 y 座標位於頁面極上／極下判定並排除。

- [ ] **Step 4: 執行測試確認通過**

Run: `python3 -m unittest tests.extract.test_sections -v`
Expected: 4 tests PASS

- [ ] **Step 5: 提交**

```bash
git add tools/extract/sections.py tests/extract/test_sections.py
git commit -m "feat(extract): 區段切分，以順序檢查修正 会話 標題重複

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QazTpwM3ApzPa47zWjy26D"
```

---

## Task 7: 單字表解析（含 usage 子行）

> **本任務與 Task 8 ~ 11 彼此獨立，可平行執行。**

**Files:**
- Create: `tools/extract/vocab.py`
- Create: `tests/extract/test_vocab.py`

**Interfaces:**
- Consumes: `Section`（Task 6）、`Line`/`Cell`（Task 4）
- Produces:
  ```python
  def parse_vocab(section: Section) -> List[Dict]
      # [{"no": 1, "kana": "きります", "kanji": "切ります",
      #   "zh": "剪，切", "usage": None}, ...]
      # usage 形如 {"kana": "でんわを～", "kanji": "電話を～"}
  ```

- [ ] **Step 1: 寫失敗的測試**

`tests/extract/test_vocab.py`：

```python
import unittest
from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments
from tools.extract.layout import group_lines
from tools.extract.sections import split_sections
from tools.extract.vocab import parse_vocab


class TestVocab(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lines = group_lines(extract_fragments(PDFDoc.from_path("07.pdf")))
        section = [s for s in split_sections(lines) if s.name == "ことば"][0]
        cls.vocab = parse_vocab(section)
        cls.by_no = {v["no"]: v for v in cls.vocab}

    def test_count(self):
        """第 7 課實測有 38 筆單字。"""
        self.assertEqual(len(self.vocab), 38)

    def test_numbers_are_contiguous(self):
        self.assertEqual(sorted(self.by_no), list(range(1, 39)))

    def test_entry_with_kanji(self):
        self.assertEqual(self.by_no[1],
                         {"no": 1, "kana": "きります", "kanji": "切ります",
                          "zh": "剪，切", "usage": None})

    def test_entry_without_kanji(self):
        v = self.by_no[3]
        self.assertEqual(v["kana"], "あげます")
        self.assertIsNone(v["kanji"])
        self.assertIn("給", v["zh"])

    def test_tight_spaced_entry(self):
        """第 10 筆 て/手 是單一字串靠字距撐開，須以第一個表意文字為切點。"""
        v = self.by_no[10]
        self.assertEqual(v["kana"], "て")
        self.assertEqual(v["kanji"], "手")

    def test_usage_subline_preserved(self):
        """第 9 筆 かけます 下方有 ［でんわを～］／［電話を～］，原型整行遺失。"""
        v = self.by_no[9]
        self.assertEqual(v["kana"], "かけます")
        self.assertIsNotNone(v["usage"], "搭配用法子行遺失")
        self.assertIn("でんわ", v["usage"]["kana"])
        self.assertIn("電話", v["usage"]["kanji"])

    def test_chinese_brackets_not_stripped(self):
        """第 9 筆中文為『打〔電話〕』，角括號不可被當成偽漢字過濾掉。"""
        self.assertIn("〔", self.by_no[9]["zh"])

    def test_katakana_entries(self):
        self.assertEqual(self.by_no[21]["kana"], "セロテープ")
        self.assertIsNone(self.by_no[21]["kanji"])
        self.assertIn("膠帶", self.by_no[21]["zh"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python3 -m unittest tests.extract.test_vocab -v`
Expected: FAIL — `No module named 'tools.extract.vocab'`

- [ ] **Step 3: 實作 `tools/extract/vocab.py`**

要點：

1. 以行首的 `N.`（如 `1.`、`38.`）辨識新單字列，取得編號。
2. 該行 `cells()` 切出的欄位依 x 由左至右為：假名、漢字（可能不存在）、中文。以**欄位 x 座標**而非欄位順序判定歸屬——漢字欄缺席時，中文欄的 x 仍在第三欄位置。
3. 假名／漢字若被切在同一個 Cell 內（`て　手`），以「字串中第一個 CJK 表意文字」為切點分開。
4. **後續無編號的行若其 x 起點與上一筆對齊且內容含 `［` 或 `〔`，視為該筆的 `usage` 子行**，解析為 `{"kana": ..., "kanji": ...}`，不可丟棄。
5. 中文欄一律原樣保留，**不得過濾 `〔〕`**；僅在判定「漢字欄是否為真漢字」時排除純標點欄位。

- [ ] **Step 4: 執行測試確認通過**

Run: `python3 -m unittest tests.extract.test_vocab -v`
Expected: 8 tests PASS

- [ ] **Step 5: 提交**

```bash
git add tools/extract/vocab.py tests/extract/test_vocab.py
git commit -m "feat(extract): 單字表解析，保留搭配用法子行與角括號

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QazTpwM3ApzPa47zWjy26D"
```

---

## Task 8: 句子解析（文型／例文／会話／問題）

> **可與 Task 7、9 ~ 11 平行執行。**

**Files:**
- Create: `tools/extract/sentences.py`
- Create: `tests/extract/test_sentences.py`

**Interfaces:**
- Consumes: `Section`（Task 6）、`pair_ruby`（Task 5）
- Produces:
  ```python
  def parse_sentences(section: Section, all_frags: List[Fragment],
                      lesson: int) -> List[Dict]
      # [{"id": "L07-文型-1", "section": "文型", "no": 1,
      #   "jp": "わたしは ワープロで 手紙を 書きます。",
      #   "ruby": [{"base": "手紙", "kana": "てがみ", "at": 9}],
      #   "zh": None, "alt": []}, ...]
  ```

- [ ] **Step 1: 寫失敗的測試**

`tests/extract/test_sentences.py`：

```python
import unittest
from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments
from tools.extract.layout import group_lines
from tools.extract.sections import split_sections
from tools.extract.sentences import parse_sentences


class TestSentences(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frags = extract_fragments(PDFDoc.from_path("07.pdf"))
        lines = group_lines(cls.frags)
        cls.sections = {s.name: s for s in split_sections(lines)}

    def _parse(self, name):
        return parse_sentences(self.sections[name], self.frags, 7)

    def test_bunkei_count(self):
        """第 7 課文型實測為 3 句。"""
        self.assertEqual(len(self._parse("文型")), 3)

    def test_bunkei_first_sentence(self):
        s = self._parse("文型")[0]
        self.assertIn("わたしは", s["jp"])
        self.assertIn("ワープロで", s["jp"])
        self.assertIn("手紙を", s["jp"])
        self.assertIn("書きます", s["jp"])
        self.assertTrue(s["jp"].rstrip().endswith("。"))

    def test_bunkei_ruby_attached(self):
        s = self._parse("文型")[0]
        pairs = {r["base"]: r["kana"] for r in s["ruby"]}
        self.assertEqual(pairs.get("手紙"), "てがみ")

    def test_alternative_particle_captured(self):
        """文型 3 課本標註『（から）』，表示 に／から 皆可，須存進 alt。"""
        s = self._parse("文型")[2]
        self.assertIn("もらいました", s["jp"])
        self.assertIn("から", s["alt"])
        self.assertNotIn("（", s["jp"], "替代形註記不應留在句子本體")

    def test_reibun_count(self):
        """第 7 課例文實測為 7 組。"""
        self.assertEqual(len(self._parse("例文")), 7)

    def test_ids_are_unique_and_stable(self):
        ids = [s["id"] for s in self._parse("文型") + self._parse("例文")]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(self._parse("文型")[0]["id"], "L07-文型-1")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python3 -m unittest tests.extract.test_sentences -v`
Expected: FAIL — `No module named 'tools.extract.sentences'`

- [ ] **Step 3: 實作 `tools/extract/sentences.py`**

要點：

1. 以行首編號 `N.` 切分句子；一個句子可跨多行（問答對的 `……` 回答行屬同一筆）。
2. 句子結尾為 `。`、`？`、`！`；問答對保留 `……` 前綴的回答行，以 `\n` 連接。
3. **替代形註記**：句尾的 `（ から ）` 形式（全形括號內為單一詞）移出句子本體，存入 `alt` 陣列。
4. 對每一行呼叫 `pair_ruby`，將結果合併，`at` 需依該行在整句中的偏移量調整。
5. `id` 格式為 `L{lesson:02d}-{section}-{no}`，**決定性、不含亂數**。

- [ ] **Step 4: 執行測試確認通過**

Run: `python3 -m unittest tests.extract.test_sentences -v`
Expected: 6 tests PASS

- [ ] **Step 5: 提交**

```bash
git add tools/extract/sentences.py tests/extract/test_sentences.py
git commit -m "feat(extract): 句子解析，含振假名附掛與替代形註記

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QazTpwM3ApzPa47zWjy26D"
```

---

## Task 9: 練習Ａ 代入表與練習Ｂ 變換題

> **可與 Task 7、8、10、11 平行執行。這是句型代入練習的題庫來源，價值最高的一項。**

**Files:**
- Create: `tools/extract/patterns.py`
- Create: `tests/extract/test_patterns.py`

**Interfaces:**
- Consumes: `Section`（Task 6）、`Line`/`Cell`（Task 4）
- Produces:
  ```python
  def parse_pattern_tables(section: Section, lesson: int) -> List[Dict]
      # 練習Ａ → [{"id": "L07-A1",
      #            "template": "{S}は {T}で ごはんを 食べます。",
      #            "slots": {"S": ["日本人", "インドネシア人", "アメリカ人"],
      #                      "T": ["はし", "スプーンと フォーク", "ナイフと フォーク"]},
      #            "rows": [[0, 0], [1, 1], [2, 2]],
      #            "requires_lesson": 7}, ...]

  def parse_drills(section: Section, lesson: int) -> List[Dict]
      # 練習Ｂ → [{"id": "L07-B3", "model_cue": "あげます",
      #            "model_answer": "テレサちゃんに ノートを あげます。",
      #            "items": ["貸します", "教えます", "書きます", "かけます"]}, ...]
  ```

- [ ] **Step 1: 寫失敗的測試**

`tests/extract/test_patterns.py`：

```python
import unittest
from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments
from tools.extract.layout import group_lines
from tools.extract.sections import split_sections
from tools.extract.patterns import parse_pattern_tables, parse_drills


class TestPatterns(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        lines = group_lines(extract_fragments(PDFDoc.from_path("07.pdf")))
        cls.sections = {s.name: s for s in split_sections(lines)}
        cls.tables = parse_pattern_tables(cls.sections["練習Ａ"], 7)
        cls.drills = parse_drills(cls.sections["練習Ｂ"], 7)

    def test_table_count(self):
        """第 7 課練習Ａ 實測有 6 張代入表。"""
        self.assertEqual(len(self.tables), 6)

    def test_single_slot_table(self):
        """練習Ａ-2：わたしは にほんご／えいご／ちゅうごくご で レポートを 書きます。"""
        t = self.tables[1]
        values = [v for vals in t["slots"].values() for v in vals]
        for expected in ("にほんご", "えいご", "ちゅうごくご"):
            self.assertIn(expected, values)

    def test_two_slot_table_rows_are_paired(self):
        """練習Ａ-1 有兩個槽位，同列詞彙必須成組，不可跨列自由組合。"""
        t = self.tables[0]
        self.assertEqual(len(t["slots"]), 2, "應偵測到兩個槽位")
        self.assertEqual(len(t["rows"]), 3, "應有三列")
        slot_names = sorted(t["slots"])
        first = t["slots"][slot_names[0]]
        second = t["slots"][slot_names[1]]
        self.assertIn("日本人", first)
        self.assertIn("はし", second)
        idx_jp = first.index("日本人")
        row = [r for r in t["rows"] if r[0] == idx_jp][0]
        self.assertEqual(second[row[1]], "はし", "日本人 必須配 はし")

    def test_template_has_placeholders(self):
        for t in self.tables:
            self.assertIn("{", t["template"], "模板缺少槽位佔位符：%s" % t["id"])

    def test_ids_stable(self):
        self.assertEqual(self.tables[0]["id"], "L07-A1")
        self.assertEqual([t["id"] for t in self.tables],
                         ["L07-A%d" % i for i in range(1, 7)])

    def test_drill_count(self):
        """第 7 課練習Ｂ 實測有 7 題。"""
        self.assertEqual(len(self.drills), 7)

    def test_drill_item_order(self):
        """原型的 bug：同列的 1) 2) 順序錯亂，輸出成『2) 教えます 1) 貸します』。"""
        d = [x for x in self.drills if x["id"] == "L07-B3"][0]
        self.assertEqual(d["items"][:2], ["貸します", "教えます"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python3 -m unittest tests.extract.test_patterns -v`
Expected: FAIL — `No module named 'tools.extract.patterns'`

- [ ] **Step 3: 實作 `tools/extract/patterns.py`**

**練習Ａ 代入表**演算法：

1. 以行首編號 `N.` 找出每張表的起始行；該行即**基底句**。
2. 對基底句呼叫 `cells()` 取得各欄的 x 區間。
3. 後續無編號的行，其 cells 的 x 若落在基底句某欄的 x 區間內（容差 ±6pt），即為該欄的替代候選詞。
4. 有替代候選詞的欄位成為**槽位**，依序命名為 `S`、`T`、`U`…；基底句中該欄文字替換為 `{S}` 形成 `template`。
5. `rows` 記錄同一視覺列的候選詞索引組合。基底句本身為第 0 列。
6. 行尾的 `……か。` 提示（如練習Ａ-1 的第四列）為疑問句變體，**不納入槽位**，另存 `question_variant` 欄位。

**練習Ｂ 變換題**演算法：

1. 以行首 `例：` 找出示範，`→` 之後為示範答案。
2. 子項 `1)` ~ `4)` 可能一行並排多個（`2) 教えます 1) 貸します`）。**必須依 `N)` 的編號排序，不可依 x 座標排序**——這正是原型錯亂的原因，課本的視覺排列是雙欄，x 順序與編號順序不一致。
3. `items` 依編號 1、2、3、4 排列。

- [ ] **Step 4: 執行測試確認通過**

Run: `python3 -m unittest tests.extract.test_patterns -v`
Expected: 7 tests PASS

- [ ] **Step 5: 提交**

```bash
git add tools/extract/patterns.py tests/extract/test_patterns.py
git commit -m "feat(extract): 練習Ａ 代入表與練習Ｂ 變換題，依編號而非座標排序

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QazTpwM3ApzPa47zWjy26D"
```

---

## Task 10: 文法解說（日中交錯）

> **可與 Task 7 ~ 9、11 平行執行。**

**Files:**
- Create: `tools/extract/grammar.py`
- Create: `tests/extract/test_grammar.py`

**Interfaces:**
- Consumes: `Section`（Task 6）、`Fragment`（Task 3）
- Produces:
  ```python
  def parse_grammar(section: Section, all_frags: List[Fragment]) -> List[Dict]
      # [{"no": 1, "title": "名詞（工具／手段）＋で＋動詞",
      #   "body_zh": "助詞「で」表示手段、方法。",
      #   "examples": [{"jp": "はしで 食べます。", "zh": "用筷子吃。"}]}, ...]
  ```

- [ ] **Step 1: 寫失敗的測試**

`tests/extract/test_grammar.py`：

```python
import unittest
from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments
from tools.extract.layout import group_lines
from tools.extract.sections import split_sections
from tools.extract.grammar import parse_grammar


class TestGrammar(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frags = extract_fragments(PDFDoc.from_path("07.pdf"))
        lines = group_lines(cls.frags)
        section = [s for s in split_sections(lines) if s.name == "文法"][0]
        cls.items = parse_grammar(section, cls.frags)

    def test_count(self):
        """第 7 課文法解說實測有 5 則。"""
        self.assertEqual(len(self.items), 5)

    def test_title_keeps_japanese(self):
        """原型只取中文字型，標題的『で』遺失，變成『名詞（工具／手段）動詞』。"""
        self.assertIn("で", self.items[0]["title"])

    def test_quoted_japanese_inside_chinese(self):
        """原型輸出『助詞「」表示手段』——引號中間的日文掉了。"""
        body = self.items[0]["body_zh"]
        self.assertIn("「で」", body)
        self.assertNotIn("「」", body, "引號內的日文遺失")

    def test_japanese_examples_present(self):
        """原型只剩中文翻譯『用筷子吃』，日文例句整句消失。"""
        ex = self.items[0]["examples"]
        self.assertGreaterEqual(len(ex), 2)
        joined = " ".join(e["jp"] for e in ex)
        self.assertIn("はし", joined)
        self.assertIn("食べます", joined)
        self.assertIn("レポート", joined)

    def test_examples_paired_with_translation(self):
        for e in self.items[0]["examples"]:
            self.assertTrue(e["jp"].strip(), "日文為空")
            self.assertTrue(e["zh"].strip(), "中文為空")

    def test_every_item_has_japanese_example(self):
        """驗收條件：每則文法解說皆須含至少一句日文例句。"""
        for it in self.items:
            self.assertTrue(it["examples"], "第 %d 則無日文例句" % it["no"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python3 -m unittest tests.extract.test_grammar -v`
Expected: FAIL — `No module named 'tools.extract.grammar'`

- [ ] **Step 3: 實作 `tools/extract/grammar.py`**

**核心：必須同時保留日文字型與中文字型的 fragment，依 x 座標交錯合併**，這正是原型的缺陷所在。

1. 以行首的全形數字（`１`、`２`…）或 `.N` 辨識新的文法點。
2. 標題行由日文與中文 fragment 混排，**依 x 排序後串接**即得完整標題。
3. 內文中，日文片段被畫在中文引號 `「」` 的中間位置——同樣依 x 排序合併即可自然插入正確位置。
4. 例句以圈號 `①②③④⑤⑥⑦⑧⑨⑩⑪⑫⑬⑭` 起始，日文在前、中文翻譯在後，兩者間有明顯 x 間距（`cells()` 可切開）。
5. 例句下方的小字為振假名，`group_lines` 已濾除，不會混入。

- [ ] **Step 4: 執行測試確認通過**

Run: `python3 -m unittest tests.extract.test_grammar -v`
Expected: 6 tests PASS

- [ ] **Step 5: 提交**

```bash
git add tools/extract/grammar.py tests/extract/test_grammar.py
git commit -m "feat(extract): 文法解說，依座標交錯合併日中文字修復日文遺失

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QazTpwM3ApzPa47zWjy26D"
```

---

## Task 11: 插畫影像抽取

> **可與 Task 7 ~ 10 平行執行。**

**Files:**
- Create: `tools/extract/images.py`
- Create: `tests/extract/test_images.py`

**Interfaces:**
- Consumes: `PDFDoc`, `Page`（Task 1）
- Produces:
  ```python
  def extract_images(doc: PDFDoc, lesson: int, out_dir: str) -> List[Dict]
      # [{"file": "data/images/07-p03-01.png", "page": 3,
      #   "x": 420.0, "y": 300.0, "w": 120.0, "h": 150.0}, ...]
  ```

- [ ] **Step 1: 寫失敗的測試**

`tests/extract/test_images.py`：

```python
import os
import shutil
import tempfile
import unittest
from tools.extract.pdfobj import PDFDoc
from tools.extract.images import extract_images


class TestImages(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_extracts_illustrations(self):
        """第 7 課含情境插畫（第 3 頁右側有玄關脫鞋的線稿）。"""
        doc = PDFDoc.from_path("07.pdf")
        images = extract_images(doc, 7, self.tmp)
        self.assertTrue(images, "未抽出任何影像")
        for img in images:
            self.assertTrue(os.path.exists(img["file"]))
            self.assertGreater(os.path.getsize(img["file"]), 200)
            self.assertGreater(img["w"], 0)

    def test_filenames_are_deterministic(self):
        doc = PDFDoc.from_path("07.pdf")
        first = [i["file"] for i in extract_images(doc, 7, self.tmp)]
        second = [i["file"] for i in extract_images(doc, 7, self.tmp)]
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python3 -m unittest tests.extract.test_images -v`
Expected: FAIL — `No module named 'tools.extract.images'`

- [ ] **Step 3: 實作 `tools/extract/images.py`**

1. 掃描頁面 `/Resources` 的 `/XObject` 字典，取得各影像物件。
2. `/Subtype /Image` 者，依 `/Filter` 處理：
   - `DCTDecode` → 串流本身即 JPEG，直接寫檔（副檔名 `.jpg`）
   - `FlateDecode` → 解壓後為原始像素，依 `/Width`、`/Height`、`/BitsPerComponent`、`/ColorSpace` 組成 PNG。**PNG 可用標準函式庫 `zlib` + `struct` 手工封裝**（IHDR/IDAT/IEND 三個 chunk 即可），不需第三方套件。
   - `CCITTFaxDecode` 或其他不支援的過濾器 → 記錄並跳過，不視為錯誤
3. 影像的頁面座標由內容流的 `cm` 矩陣取得：`a 0 0 d e f cm` 後接 `/Name Do`，其中 `e`、`f` 為左下角座標，`a`、`d` 為寬高。
4. 檔名格式 `{lesson:02d}-p{page:02d}-{index:02d}.{ext}`，**決定性**。

- [ ] **Step 4: 執行測試確認通過**

Run: `python3 -m unittest tests.extract.test_images -v`
Expected: 2 tests PASS

- [ ] **Step 5: 提交**

```bash
git add tools/extract/images.py tests/extract/test_images.py
git commit -m "feat(extract): 抽取課本插畫影像與其頁面座標

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QazTpwM3ApzPa47zWjy26D"
```

---

## Task 12: 不變式檢查

**Files:**
- Create: `tools/extract/validate.py`
- Create: `tests/extract/test_validate.py`

**Interfaces:**
- Consumes: 產出的 JSON（不依賴任何解析模組）
- Produces:
  ```python
  def validate_lesson(data: Dict) -> List[str]
      # 回傳問題描述清單；空清單代表通過
  ```

- [ ] **Step 1: 寫失敗的測試**

`tests/extract/test_validate.py`：

```python
import copy
import unittest
from tools.extract.validate import validate_lesson

GOOD = {
    "lesson": 7,
    "vocab": [
        {"no": 1, "kana": "きります", "kanji": "切ります", "zh": "剪，切", "usage": None},
        {"no": 2, "kana": "おくります", "kanji": "送ります", "zh": "寄送", "usage": None},
    ],
    "sentences": [
        {"id": "L07-文型-1", "section": "文型", "no": 1,
         "jp": "わたしは 手紙を 書きます。",
         "ruby": [{"base": "手紙", "kana": "てがみ", "at": 5}],
         "zh": None, "alt": []},
    ],
    "patterns": [
        {"id": "L07-A1", "template": "{S}は 食べます。",
         "slots": {"S": ["日本人", "アメリカ人"]}, "rows": [[0], [1]],
         "requires_lesson": 7},
    ],
    "grammar": [
        {"no": 1, "title": "名詞＋で", "body_zh": "助詞「で」表示手段。",
         "examples": [{"jp": "はしで 食べます。", "zh": "用筷子吃。"}]},
    ],
}


class TestValidate(unittest.TestCase):
    def test_good_data_passes(self):
        self.assertEqual(validate_lesson(copy.deepcopy(GOOD)), [])

    def test_detects_vocab_number_gap(self):
        bad = copy.deepcopy(GOOD)
        bad["vocab"][1]["no"] = 3
        self.assertTrue(any("編號" in p for p in validate_lesson(bad)))

    def test_detects_missing_chinese(self):
        bad = copy.deepcopy(GOOD)
        bad["vocab"][0]["zh"] = ""
        self.assertTrue(any("中文" in p for p in validate_lesson(bad)))

    def test_detects_ruby_base_not_in_sentence(self):
        bad = copy.deepcopy(GOOD)
        bad["sentences"][0]["ruby"][0]["base"] = "電話"
        self.assertTrue(any("振假名" in p for p in validate_lesson(bad)))

    def test_detects_wrong_ruby_position(self):
        bad = copy.deepcopy(GOOD)
        bad["sentences"][0]["ruby"][0]["at"] = 0
        self.assertTrue(any("振假名" in p for p in validate_lesson(bad)))

    def test_detects_misdecoding_fingerprint(self):
        bad = copy.deepcopy(GOOD)
        bad["sentences"][0]["jp"] = "偼偄偆偊偍"
        self.assertTrue(any("誤解碼" in p for p in validate_lesson(bad)))

    def test_detects_sentence_without_terminator(self):
        bad = copy.deepcopy(GOOD)
        bad["sentences"][0]["jp"] = "わたしは 手紙を 書きます"
        self.assertTrue(any("結尾" in p for p in validate_lesson(bad)))

    def test_detects_grammar_without_japanese_example(self):
        bad = copy.deepcopy(GOOD)
        bad["grammar"][0]["examples"] = []
        self.assertTrue(any("例句" in p for p in validate_lesson(bad)))

    def test_detects_empty_quotes_in_grammar(self):
        bad = copy.deepcopy(GOOD)
        bad["grammar"][0]["body_zh"] = "助詞「」表示手段。"
        self.assertTrue(any("空引號" in p for p in validate_lesson(bad)))

    def test_detects_row_length_mismatch(self):
        bad = copy.deepcopy(GOOD)
        bad["patterns"][0]["rows"] = [[0], [1, 1]]
        self.assertTrue(any("列" in p for p in validate_lesson(bad)))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python3 -m unittest tests.extract.test_validate -v`
Expected: FAIL — `No module named 'tools.extract.validate'`

- [ ] **Step 3: 實作 `tools/extract/validate.py`**

檢查項目（對應 spec §13 Phase 0 驗收）：

| 檢查 | 訊息關鍵字 |
|---|---|
| 單字編號 1..N 連續無缺漏 | 編號 |
| 每筆單字的 `kana` 與 `zh` 非空 | 中文 |
| 漢字欄不得為純標點 | 漢字 |
| 每個 `ruby.base` 出現在 `jp` 的 `at` 位置 | 振假名 |
| 每個句子以 `。？！` 或 `→` 結尾 | 結尾 |
| 全檔不含誤解碼指紋字元 | 誤解碼 |
| 每張代入表各列長度一致且索引在範圍內 | 列 |
| 每則文法解說含至少一句日文例句 | 例句 |
| 文法內文不得出現空的 `「」` | 空引號 |
| 帶 `usage` 的單字其 `usage.kana` 與 `usage.kanji` 皆非空 | 搭配 |

誤解碼指紋字元集合（模組層級常數）：

```python
MISDECODE_FINGERPRINT = set("偁偄偆偊偍偐偑偒偓偔偕偖偗偘偙偠偡偣偤偦偨偩偪偭偮偯偰偱偲偵偼傑傒傓")
```

- [ ] **Step 4: 執行測試確認通過**

Run: `python3 -m unittest tests.extract.test_validate -v`
Expected: 10 tests PASS

- [ ] **Step 5: 提交**

```bash
git add tools/extract/validate.py tests/extract/test_validate.py
git commit -m "feat(extract): 不變式檢查，涵蓋 spec Phase 0 全部驗收條件

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QazTpwM3ApzPa47zWjy26D"
```

---

## Task 13: CLI 與 golden file 回歸測試

**Files:**
- Create: `tools/extract/cli.py`
- Create: `tests/extract/test_golden.py`
- Create: `data/lessons/07.json`（golden file，由本任務產生後納入版控）

**Interfaces:**
- Consumes: 全部前述模組
- Produces:
  ```bash
  python3 -m tools.extract.cli 7                  # 產出 data/lessons/07.json
  python3 -m tools.extract.cli 1-15               # 批次
  python3 -m tools.extract.cli 1-15 --validate    # 產出後執行不變式檢查
  ```

- [ ] **Step 1: 寫失敗的測試**

`tests/extract/test_golden.py`：

```python
import json
import os
import subprocess
import tempfile
import unittest

GOLDEN = "data/lessons/07.json"


class TestGolden(unittest.TestCase):
    def test_cli_reproduces_golden_file(self):
        """重跑管線必須產出與 golden file 完全相同的結果（決定性）。"""
        self.assertTrue(os.path.exists(GOLDEN), "golden file 不存在，請先執行 CLI 產生")
        with open(GOLDEN, encoding="utf-8") as fh:
            expected = json.load(fh)
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(
                ["python3", "-m", "tools.extract.cli", "7", "--out", tmp],
                check=True)
            with open(os.path.join(tmp, "07.json"), encoding="utf-8") as fh:
                actual = json.load(fh)
        self.assertEqual(actual, expected)

    def test_golden_passes_validation(self):
        from tools.extract.validate import validate_lesson
        with open(GOLDEN, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(validate_lesson(data), [])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: 執行測試確認失敗**

Run: `python3 -m unittest tests.extract.test_golden -v`
Expected: FAIL — golden file 不存在

- [ ] **Step 3: 實作 `tools/extract/cli.py`**

```python
import argparse
import json
import os
from tools.extract.pdfobj import PDFDoc
from tools.extract.fragments import extract_fragments
from tools.extract.layout import group_lines
from tools.extract.sections import split_sections
from tools.extract.vocab import parse_vocab
from tools.extract.sentences import parse_sentences
from tools.extract.patterns import parse_pattern_tables, parse_drills
from tools.extract.grammar import parse_grammar
from tools.extract.images import extract_images
from tools.extract.validate import validate_lesson


def extract_lesson(lesson: int, image_dir=None) -> dict:
    doc = PDFDoc.from_path("%02d.pdf" % lesson)
    frags = extract_fragments(doc)
    sections = {s.name: s for s in split_sections(group_lines(frags))}
    data = {"lesson": lesson, "vocab": [], "sentences": [],
            "patterns": [], "drills": [], "grammar": [], "images": []}
    if "ことば" in sections:
        data["vocab"] = parse_vocab(sections["ことば"])
    for name in ("文型", "例文", "会話", "問題"):
        if name in sections:
            data["sentences"].extend(parse_sentences(sections[name], frags, lesson))
    if "練習Ａ" in sections:
        data["patterns"] = parse_pattern_tables(sections["練習Ａ"], lesson)
    if "練習Ｂ" in sections:
        data["drills"] = parse_drills(sections["練習Ｂ"], lesson)
    if "文法" in sections:
        data["grammar"] = parse_grammar(sections["文法"], frags)
    if image_dir:
        data["images"] = extract_images(doc, lesson, image_dir)
    return data


def parse_range(spec: str):
    if "-" in spec:
        lo, hi = spec.split("-", 1)
        return list(range(int(lo), int(hi) + 1))
    return [int(spec)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("lessons")
    ap.add_argument("--out", default="data/lessons")
    ap.add_argument("--images", default=None)
    ap.add_argument("--validate", action="store_true")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    failures = 0
    for n in parse_range(args.lessons):
        data = extract_lesson(n, args.images)
        path = os.path.join(args.out, "%02d.json" % n)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=1, sort_keys=True)
        msg = "%s  單字=%d 句子=%d 代入表=%d 文法=%d" % (
            path, len(data["vocab"]), len(data["sentences"]),
            len(data["patterns"]), len(data["grammar"]))
        if args.validate:
            problems = validate_lesson(data)
            if problems:
                failures += 1
                msg += "\n  ✗ " + "\n  ✗ ".join(problems)
            else:
                msg += "  ✓"
        print(msg)
    raise SystemExit(1 if failures else 0)


if __name__ == "__main__":
    main()
```

**輸出必須 `sort_keys=True` 且 `indent=1`**，確保 golden file 比對是決定性的。

- [ ] **Step 4: 產生 golden file**

```bash
python3 -m tools.extract.cli 7 --validate
```
Expected: 輸出 `data/lessons/07.json  單字=38 句子=... 代入表=6 文法=5  ✓`

- [ ] **Step 5: 執行測試確認通過**

Run: `python3 -m unittest tests.extract.test_golden -v`
Expected: 2 tests PASS

- [ ] **Step 6: 提交**

```bash
git add tools/extract/cli.py tests/extract/test_golden.py data/lessons/07.json
git commit -m "feat(extract): CLI 入口與第 7 課 golden file 回歸測試

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QazTpwM3ApzPa47zWjy26D"
```

---

## Task 14: 全課次執行與視覺對照驗收

**Files:**
- Create: `data/lessons/01.json` … `15.json`
- Create: `data/images/`
- Create: `docs/superpowers/plans/2026-09-11-phase0-verification-report.md`

**Interfaces:**
- Consumes: 全部前述任務
- Produces: 完整的 Phase 0 產出與驗收報告

- [ ] **Step 1: 執行全部測試**

Run: `python3 -m unittest discover -s tests -t . -v`
Expected: 全數 PASS，無 ERROR、無 SKIP

- [ ] **Step 2: 對 1 ~ 15 課執行管線並驗證**

```bash
python3 -m tools.extract.cli 1-15 --images data/images --validate
```
Expected: 15 行輸出，每行結尾為 `✓`，程序結束碼為 0

若有任何課次失敗，**修正後重跑，不得放行**。已知風險：可能出現尚未支援的第三種 PDF 結構變體（目前僅驗證過 PDF 1.3 明文、PDF 1.6 純物件流、PDF 1.7 混合三種）。

- [ ] **Step 3: 算繪頁面供視覺對照**

```bash
for n in 01 03 07 11 15; do
  swift tools/render.swift $n.pdf /tmp/pages/$n 2.0
done
```

- [ ] **Step 4: 逐頁視覺對照，抽樣五課**

對第 1、3、7、11、15 課，逐頁比對算繪影像與 `data/lessons/NN.json`，確認：

- 單字表每一筆的假名、漢字、中文與版面一致，**特別注意帶方括號子行的單字其 `usage` 未遺失**
- 文型與例文的句子完整、無截斷、無多餘的頁首頁尾文字
- 練習Ａ 代入表的槽位候選詞與版面的欄位對應正確，同列詞彙成組
- 文法解說的日文例句存在且與版面一致
- 振假名的讀音與版面標註相符

**此步驟不可省略。** 實測顯示，遺失整行子項目這類缺陷會通過所有不變式檢查（欄位齊備、編號連續），只有比對版面才看得出來——第 7 課第 9 筆 `かけます` 的搭配用法遺失即為實例。

- [ ] **Step 5: 撰寫驗收報告**

`docs/superpowers/plans/2026-09-11-phase0-verification-report.md`，內容須包含：

- 15 課的統計表（單字數、句子數、代入表數、文法點數、影像數）
- 不變式檢查結果
- 視覺對照抽樣五課的發現，**誠實列出仍有瑕疵之處**
- 振假名配對率（各課）
- 尚未解決的已知問題與其影響範圍

- [ ] **Step 6: 提交**

```bash
git add data/ docs/
git commit -m "feat(extract): 第 1~15 課完整抽取與驗收報告

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01QazTpwM3ApzPa47zWjy26D"
```

---

## Phase 0 完成定義

全部達成才算完成：

- [ ] `python3 -m unittest discover -s tests -t . -v` 全數通過
- [ ] `python3 -m tools.extract.cli 1-15 --images data/images --validate` 結束碼為 0
- [ ] 第 7 課 golden file 回歸測試通過（管線具決定性）
- [ ] 五課視覺對照完成，驗收報告已提交
- [ ] 原型的六項已知缺陷全部修復：文法解說日文遺失、引號內日文遺失、`会話` 標題重複、練習Ａ 欄位對齊、練習Ｂ 順序錯亂、單字搭配用法子行遺失

## 不屬於 Phase 0 的工作

以下屬於後續階段，**本計畫不處理**：

- `data/concepts.json`（約 70 個文法／助詞概念的人工定義）→ Phase 2
- `data/verbs.json`（動詞分類與例外校對）→ Phase 1
- 補充講義 JPEG 的人工轉寫 → Phase 2
- 插畫與概念的關聯對應 → Phase 4（影像本身已於 Task 11 抽出）
- 任何 JavaScript、前端、SRS 相關程式碼 → Phase 1（另行撰寫計畫）
