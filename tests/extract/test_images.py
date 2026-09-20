import os
import re
import shutil
import struct
import tempfile
import unittest
import zlib

from tools.extract.pdfobj import PDFDoc
from tools.extract.images import extract_images, _page_xobjects, _find_placements


# ---------------------------------------------------------------------------
# 合成 PDF 建構工具：只用來造出乾淨、受控的邊界案例（不同色彩空間分支、
# 不支援的過濾器等），不觸碰任何根目錄的 *.pdf。單頁、單一影像，內容流
# 固定為 `q\n<cm> cm\n/Im1 Do\nQ\n`。
# ---------------------------------------------------------------------------

def _obj(num, head, stream=None):
    if stream is None:
        return ("%d 0 obj\n" % num).encode("ascii") + head + b"\nendobj\n"
    dict_with_len = head[:-2].rstrip() + (" /Length %d >>" % len(stream)).encode("ascii")
    return (("%d 0 obj\n" % num).encode("ascii") + dict_with_len +
             b"\nstream\n" + stream + b"\nendstream\nendobj\n")


def _make_pdf(image_head, image_stream, extra_objects=b"", cm=b"2 0 0 1 100 200"):
    """單頁 PDF：/Im1 指向物件 2（依 `image_head`／`image_stream` 建構），
    內容流以 `cm` 這組 6 參數把它放到頁面上並 `Do` 出來。"""
    content = b"q\n" + cm + b" cm\n/Im1 Do\nQ\n"
    page = _obj(1, b"<< /Type /Page /Resources << /XObject << /Im1 2 0 R >> >> "
                   b"/Contents 3 0 R >>")
    image = _obj(2, image_head, image_stream)
    contentobj = _obj(3, b"<< >>", content)
    return page + image + extra_objects + contentobj


def _png_chunks(data):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    chunks = {}
    i = 8
    while i < len(data):
        length = struct.unpack(">I", data[i:i + 4])[0]
        tag = data[i + 4:i + 8]
        payload = data[i + 8:i + 8 + length]
        chunks[tag] = payload
        i += 12 + length
    return chunks


class TestImagesFromRealLesson(unittest.TestCase):
    """07.pdf：第 3 頁右側玄関脫鞋插圖（簡報指定的驗收案例）。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.doc = PDFDoc.from_path("07.pdf")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_extracts_illustrations(self):
        """簡報原始測試碼對每張抽出影像斷言檔案大小 > 200 位元組——實測
        07.pdf 第 2 頁（ことば 頁）另外還有 6 張裝飾用的小色塊／漸層短
        條（實際像素尺寸 80x2、2x8、9x2、15x2、29x2，不是插畫，是版面
        裝飾），壓縮後檔案本身只有 77~98 位元組，比 200 小。這條門檻是
        簡報作者的假設，不是對這份課本語料庫量測後的事實（同一類「引
        用的例子跟實際內容不符」問題，本專案已出現多次）——這裡改成
        斷言『每個檔案都是合法、非空的 PNG/JPEG』，不對檔案大小設武斷
        門檻；第 3 頁那張真正的插畫（9850 位元組）由
        `test_page3_illustration_exact_file_and_coords` 個別驗證確實
        遠大於 200 位元組。"""
        images = extract_images(self.doc, 7, self.tmp)
        self.assertTrue(images, "未抽出任何影像")
        for img in images:
            self.assertTrue(os.path.exists(img["file"]))
            with open(img["file"], "rb") as f:
                header = f.read(8)
            self.assertTrue(
                header == b"\x89PNG\r\n\x1a\n" or header[:2] == b"\xff\xd8",
                "%s 檔頭既非 PNG 也非 JPEG" % img["file"],
            )
            self.assertGreater(os.path.getsize(img["file"]), 0)
            self.assertGreater(img["w"], 0)

    def test_filenames_are_deterministic(self):
        first = [i["file"] for i in extract_images(self.doc, 7, self.tmp)]
        second = [i["file"] for i in extract_images(self.doc, 7, self.tmp)]
        self.assertEqual(first, second)

    def test_reruns_produce_byte_identical_files(self):
        """檔名相同還不夠——重跑必須產出逐位元組相同的檔案內容，不能只
        是巧合地選到同一個檔名卻寫入不同位元組。"""
        first = extract_images(self.doc, 7, self.tmp)
        tmp2 = tempfile.mkdtemp()
        try:
            second = extract_images(self.doc, 7, tmp2)
            self.assertEqual(len(first), len(second))
            for a, b in zip(first, second):
                with open(a["file"], "rb") as fa, open(b["file"], "rb") as fb:
                    self.assertEqual(fa.read(), fb.read())
        finally:
            shutil.rmtree(tmp2, ignore_errors=True)

    def test_page3_illustration_exact_file_and_coords(self):
        """實測值：07.pdf 頁面內容流 `203 0 0 117 381.6 338.0003 cm
        /Im6 Do`——物件 12 是唯一一張、Indexed 色彩空間、203x117 的
        FlateDecode 影像，頁面上也只有這一張（第 3 頁沒有其他 Do）。"""
        images = extract_images(self.doc, 7, self.tmp)
        page3 = [i for i in images if i["page"] == 3]
        self.assertEqual(len(page3), 1)
        img = page3[0]
        self.assertEqual(os.path.basename(img["file"]), "07-p03-01.png")
        self.assertEqual(img["x"], 381.6)
        self.assertEqual(img["y"], 338.0003)
        self.assertEqual(img["w"], 203.0)
        self.assertEqual(img["h"], 117.0)

        with open(img["file"], "rb") as f:
            data = f.read()
        chunks = _png_chunks(data)
        width, height, bpc, color_type = struct.unpack(">IIBB", chunks[b"IHDR"][:10])
        self.assertEqual((width, height, bpc, color_type), (203, 117, 8, 3))
        self.assertIn(b"PLTE", chunks)
        self.assertEqual(len(chunks[b"PLTE"]) % 3, 0)
        raw = zlib.decompress(chunks[b"IDAT"])
        self.assertEqual(len(raw), (width + 1) * height)  # 每列 1 個 filter byte + width 個索引

    def test_lesson_total_matches_flate_placement_count(self):
        """獨立檢查角度一：抽出的影像數必須恰好等於內容流中『引用到
        FlateDecode 且非 ImageMask 的 /Subtype /Image』的 `cm ... Do`
        出現次數——這裡不呼叫 `extract_images` 內部的任何輔助函式來算
        期望值（用獨立的正規表示式重新掃一次内容流與物件字典），避免
        跟被測程式共用同一套（可能同樣錯誤的）邏輯。實測 07.pdf 全 9
        頁共 51 張。"""
        images = extract_images(self.doc, 7, self.tmp)

        num = rb"[+-]?\d*\.?\d+"
        cm_do = re.compile(
            rb"(?:" + num + rb"\s+){2}" + num + rb"\s+" + num + rb"\s+" +
            num + rb"\s+" + num + rb"\s+cm\s*/([^\s/()<>\[\]{}%]+)\s+Do"
        )
        expected = 0
        for page in self.doc.pages:
            xo_m = re.search(rb"/XObject\s*(<<.*?>>)", page.resources, re.S)
            xo = {}
            if xo_m:
                for mm in re.finditer(rb"/([^\s/()<>\[\]{}%]+)\s+(\d+)\s+0\s+R", xo_m.group(1)):
                    xo[mm.group(1)] = int(mm.group(2))
            for m in cm_do.finditer(page.content):
                obj_num = xo.get(m.group(1))
                if obj_num is None:
                    continue
                body = self.doc.get_object(obj_num)
                if (re.search(rb"/Subtype\s*/Image", body) and b"/FlateDecode" in body
                        and b"/ImageMask" not in body):
                    expected += 1

        self.assertEqual(len(images), 51)
        self.assertEqual(len(images), expected)

    def test_ccitt_bullet_icon_skipped_not_error(self):
        """獨立檢查角度二：頁面 6 的 `/Im16`（CCITTFaxDecode，30x18 的小
        勾選圖示）在同一頁被 `Do` 了 9 次，全部應該被跳過、不產生檔
        案、也不佔用 index（見 `test_reused_object_gets_distinct_indices`
        驗證 index 連號不留缺口）。"""
        page6 = self.doc.pages[5]
        xo = _page_xobjects(page6)
        self.assertIn("Im16", xo)
        body = self.doc.get_object(xo["Im16"])
        self.assertIn(b"/CCITTFaxDecode", body)

        images = extract_images(self.doc, 7, self.tmp)
        page6_files = [os.path.basename(i["file"]) for i in images if i["page"] == 6]
        self.assertEqual(len(page6_files), 9, "頁 6 應有 9 張成功抽出的插圖（Im16 跳過不計）")
        self.assertEqual(page6_files, ["07-p06-%02d.png" % k for k in range(1, 10)])

    def test_reused_object_gets_distinct_indices_same_bytes(self):
        """`/Im20`（物件 34）在頁 6 被放置兩次（不同座標），依實測順序
        分別是第 6、7 張成功抽出的影像：同一來源物件，檔名與座標各自
        獨立，但寫出的位元組必須完全相同（都是同一張線稿）。"""
        images = extract_images(self.doc, 7, self.tmp)
        page6 = [i for i in images if i["page"] == 6]
        img6, img7 = page6[5], page6[6]
        self.assertEqual(os.path.basename(img6["file"]), "07-p06-06.png")
        self.assertEqual(os.path.basename(img7["file"]), "07-p06-07.png")
        self.assertNotEqual((img6["x"], img6["y"]), (img7["x"], img7["y"]))
        with open(img6["file"], "rb") as f6, open(img7["file"], "rb") as f7:
            self.assertEqual(f6.read(), f7.read())

    def test_no_form_xobjects_in_corpus_sample(self):
        """`_page_xobjects` 找到的名稱裡，07.pdf 沒有 `/Subtype /Form`
        （這份課本的 XObject 全是影像，不是可重複使用的頁面片段）；驗
        證『非 Image 的 XObject 會被跳過』這條防呆邏輯目前在這份文件
        裡沒有被真的觸發過，屬於防禦性程式碼而非已驗證分支。"""
        forms = 0
        for page in self.doc.pages:
            for num in _page_xobjects(page).values():
                if re.search(rb"/Subtype\s*/Form", self.doc.get_object(num)):
                    forms += 1
        self.assertEqual(forms, 0)


class TestImagesAllLessonsSmoke(unittest.TestCase):
    """15 課全跑一次的煙霧測試：只斷言『不炸、每張都是合法檔案』，不在
    這裡重複斷言逐課精確數字（精確數字見 task-11-report.md 的量測結
    果，由控制端可自行重跑核對）。"""

    def test_every_lesson_extracts_only_valid_nonempty_files(self):
        for lesson in range(1, 16):
            doc = PDFDoc.from_path("%02d.pdf" % lesson)
            tmp = tempfile.mkdtemp()
            try:
                images = extract_images(doc, lesson, tmp)
                self.assertTrue(images, "第 %d 課未抽出任何影像" % lesson)
                for img in images:
                    self.assertTrue(os.path.exists(img["file"]))
                    with open(img["file"], "rb") as f:
                        data = f.read()
                    self.assertEqual(data[:8], b"\x89PNG\r\n\x1a\n",
                                      "%s 不是合法 PNG 檔頭" % img["file"])
            finally:
                shutil.rmtree(tmp, ignore_errors=True)


class TestSyntheticColorSpaces(unittest.TestCase):
    """合成邊界案例：這份課本語料庫實測全部 238 張 Indexed 影像的
    base 都是間接參照（解到 /ICCBased，N=3）、lookup 都是串流間接參
    照（見 tools/extract/images.py `_classify_indexed` 模組說明），也
    沒有任何 DCTDecode、DeviceCMYK、多重過濾器鏈的影像。以下分支在
    真實語料庫裡從未被觸發，只靠這裡的合成測試驗證行為。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_indexed_named_base_with_literal_lookup_string(self):
        """base 用直接名稱 `/DeviceRGB`（非間接參照），lookup 用 PDF
        literal string `(...)`（非串流間接參照）——兩者在真實語料庫都
        沒出現過。2x1 影像：索引 0 = 紅、索引 1 = 綠。"""
        palette = bytes([0xFF, 0x00, 0x00, 0x00, 0xFF, 0x00])
        cs = _obj(4, b"[ /Indexed /DeviceRGB 1 (" + palette + b") ]")
        pixels = zlib.compress(bytes([0, 1]))
        head = (b"<< /Type /XObject /Subtype /Image /Width 2 /Height 1 "
                b"/BitsPerComponent 8 /ColorSpace 4 0 R /Filter /FlateDecode >>")
        pdf_bytes = _make_pdf(head, pixels, extra_objects=cs)
        doc = PDFDoc(pdf_bytes)

        images = extract_images(doc, 1, self.tmp)
        self.assertEqual(len(images), 1)
        with open(images[0]["file"], "rb") as f:
            data = f.read()
        chunks = _png_chunks(data)
        self.assertEqual(chunks[b"PLTE"], palette)
        width, height, bpc, color_type = struct.unpack(">IIBB", chunks[b"IHDR"][:10])
        self.assertEqual((width, height, color_type), (2, 1, 3))
        raw = zlib.decompress(chunks[b"IDAT"])
        self.assertEqual(raw, b"\x00\x00\x01")  # filter byte, 索引0, 索引1

    def test_indexed_gray_base_expands_palette_to_rgb_triples(self):
        """base 是 `/DeviceGray`：PNG 的 PLTE 恆為 RGB 三元組，灰階調色
        盤必須被展開成 R=G=B，不能直接把單一位元組塞進 PLTE。"""
        gray_lookup = bytes([0x40, 0xC0])  # 2 個灰階調色盤項目
        cs = _obj(4, b"[ /Indexed /DeviceGray 1 (" + gray_lookup + b") ]")
        pixels = zlib.compress(bytes([1, 0]))
        head = (b"<< /Type /XObject /Subtype /Image /Width 2 /Height 1 "
                b"/BitsPerComponent 8 /ColorSpace 4 0 R /Filter /FlateDecode >>")
        pdf_bytes = _make_pdf(head, pixels, extra_objects=cs)
        doc = PDFDoc(pdf_bytes)

        images = extract_images(doc, 1, self.tmp)
        self.assertEqual(len(images), 1)
        with open(images[0]["file"], "rb") as f:
            chunks = _png_chunks(f.read())
        self.assertEqual(chunks[b"PLTE"], bytes([0x40, 0x40, 0x40, 0xC0, 0xC0, 0xC0]))

    def test_indexed_lookup_stream_without_filter(self):
        """lookup 是串流間接參照，但那個串流本身沒有 `/Filter`（原始未
        壓縮位元組）——語料庫裡實測全部都有 `/FlateDecode`，這條『無過
        濾器』分支未被真實資料觸發。"""
        palette = bytes([0x11, 0x22, 0x33, 0x44, 0x55, 0x66])
        lookup = _obj(5, b"<< >>", palette)
        cs = _obj(4, b"[ /Indexed /DeviceRGB 1 5 0 R ]")
        pixels = zlib.compress(bytes([0, 1]))
        head = (b"<< /Type /XObject /Subtype /Image /Width 2 /Height 1 "
                b"/BitsPerComponent 8 /ColorSpace 4 0 R /Filter /FlateDecode >>")
        pdf_bytes = _make_pdf(head, pixels, extra_objects=cs + lookup)
        doc = PDFDoc(pdf_bytes)

        images = extract_images(doc, 1, self.tmp)
        self.assertEqual(len(images), 1)
        with open(images[0]["file"], "rb") as f:
            chunks = _png_chunks(f.read())
        self.assertEqual(chunks[b"PLTE"], palette)

    def test_direct_rgb_colorspace_without_indexing(self):
        """非 Indexed 的直接 `/DeviceRGB`：樣本本身就是 RGB 三元組，PNG
        應該是 color type 2，不需要 PLTE。"""
        pixels = zlib.compress(bytes([255, 0, 0, 0, 255, 0]))
        head = (b"<< /Type /XObject /Subtype /Image /Width 2 /Height 1 "
                b"/BitsPerComponent 8 /ColorSpace /DeviceRGB /Filter /FlateDecode >>")
        pdf_bytes = _make_pdf(head, pixels)
        doc = PDFDoc(pdf_bytes)

        images = extract_images(doc, 1, self.tmp)
        self.assertEqual(len(images), 1)
        with open(images[0]["file"], "rb") as f:
            chunks = _png_chunks(f.read())
        width, height, bpc, color_type = struct.unpack(">IIBB", chunks[b"IHDR"][:10])
        self.assertEqual((width, height, color_type), (2, 1, 2))
        self.assertNotIn(b"PLTE", chunks)
        raw = zlib.decompress(chunks[b"IDAT"])
        self.assertEqual(raw, b"\x00" + bytes([255, 0, 0, 0, 255, 0]))

    def test_direct_gray_colorspace(self):
        pixels = zlib.compress(bytes([10, 20, 30, 40]))
        head = (b"<< /Type /XObject /Subtype /Image /Width 2 /Height 2 "
                b"/BitsPerComponent 8 /ColorSpace /DeviceGray /Filter /FlateDecode >>")
        pdf_bytes = _make_pdf(head, pixels)
        doc = PDFDoc(pdf_bytes)

        images = extract_images(doc, 1, self.tmp)
        self.assertEqual(len(images), 1)
        with open(images[0]["file"], "rb") as f:
            chunks = _png_chunks(f.read())
        width, height, bpc, color_type = struct.unpack(">IIBB", chunks[b"IHDR"][:10])
        self.assertEqual((width, height, color_type), (2, 2, 0))
        raw = zlib.decompress(chunks[b"IDAT"])
        self.assertEqual(raw, b"\x00\x0a\x14\x00\x1e\x28")

    def test_iccbased_direct_three_components_is_rgb(self):
        """`/ColorSpace` 指到 `[ /ICCBased n 0 R ]`、n 物件宣告 `/N 3`
        （非 Indexed）：跟 07.pdf 實際遇到的漸層條紋同一種結構。"""
        icc = _obj(5, b"<< /N 3 /Length 0 >>", b"")
        cs = _obj(4, b"[ /ICCBased 5 0 R ]")
        pixels = zlib.compress(bytes([1, 2, 3, 4, 5, 6]))
        head = (b"<< /Type /XObject /Subtype /Image /Width 2 /Height 1 "
                b"/BitsPerComponent 8 /ColorSpace 4 0 R /Filter /FlateDecode >>")
        pdf_bytes = _make_pdf(head, pixels, extra_objects=cs + icc)
        doc = PDFDoc(pdf_bytes)

        images = extract_images(doc, 1, self.tmp)
        self.assertEqual(len(images), 1)
        with open(images[0]["file"], "rb") as f:
            chunks = _png_chunks(f.read())
        _, _, _, color_type = struct.unpack(">IIBB", chunks[b"IHDR"][:10])
        self.assertEqual(color_type, 2)


class TestSyntheticSkipsAndDCT(unittest.TestCase):
    """跳過邏輯與 DCTDecode 直通：語料庫裡完全沒有 DCTDecode 影像（全
    15 課、908 張影像全部是 FlateDecode 或 CCITTFaxDecode），這裡用合
    成資料驗證簡報要求的行為。"""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_dct_decode_passthrough_writes_jpg(self):
        jpeg_bytes = b"\xff\xd8\xff\xe0" + bytes(range(256)) * 2 + b"\xff\xd9"
        head = (b"<< /Type /XObject /Subtype /Image /Width 10 /Height 10 "
                b"/BitsPerComponent 8 /ColorSpace /DeviceRGB /Filter /DCTDecode >>")
        pdf_bytes = _make_pdf(head, jpeg_bytes)
        doc = PDFDoc(pdf_bytes)

        images = extract_images(doc, 1, self.tmp)
        self.assertEqual(len(images), 1)
        self.assertTrue(images[0]["file"].endswith(".jpg"))
        with open(images[0]["file"], "rb") as f:
            data = f.read()
        self.assertEqual(data, jpeg_bytes)
        self.assertEqual(data[:2], b"\xff\xd8")
        self.assertEqual(data[-2:], b"\xff\xd9")

    def test_ccitt_fax_decode_skipped(self):
        head = (b"<< /Type /XObject /Subtype /Image /Width 30 /Height 18 "
                b"/BitsPerComponent 1 /ImageMask true /Filter /CCITTFaxDecode "
                b"/DecodeParms << /K -1 /Columns 30 >> >>")
        pdf_bytes = _make_pdf(head, b"\x91\xc33:\x8e\x9f\xfc\xe2#\xa2:")
        doc = PDFDoc(pdf_bytes)

        images = extract_images(doc, 1, self.tmp)
        self.assertEqual(images, [])
        self.assertEqual(os.listdir(self.tmp), [])

    def test_cmyk_colorspace_skipped(self):
        pixels = zlib.compress(bytes([0, 0, 0, 255]))
        head = (b"<< /Type /XObject /Subtype /Image /Width 1 /Height 1 "
                b"/BitsPerComponent 8 /ColorSpace /DeviceCMYK /Filter /FlateDecode >>")
        pdf_bytes = _make_pdf(head, pixels)
        doc = PDFDoc(pdf_bytes)

        images = extract_images(doc, 1, self.tmp)
        self.assertEqual(images, [])
        self.assertEqual(os.listdir(self.tmp), [])

    def test_image_mask_without_ccitt_also_skipped(self):
        """`/ImageMask true` 是遮罩語意（用當時填色狀態上色），不是獨
        立可還原的色彩影像，即使過濾器換成 FlateDecode 也該跳過。"""
        pixels = zlib.compress(bytes([0xFF]))
        head = (b"<< /Type /XObject /Subtype /Image /Width 1 /Height 1 "
                b"/BitsPerComponent 1 /ImageMask true /Filter /FlateDecode >>")
        pdf_bytes = _make_pdf(head, pixels)
        doc = PDFDoc(pdf_bytes)

        images = extract_images(doc, 1, self.tmp)
        self.assertEqual(images, [])

    def test_chained_filters_skipped(self):
        """`/Filter` 為陣列且超過一個過濾器（例如
        `[/ASCII85Decode /FlateDecode]`）：這裡不嘗試串接多重過濾器，
        直接跳過。語料庫裡沒有這種鏈。"""
        pixels = zlib.compress(bytes([1, 2, 3, 4]))
        head = (b"<< /Type /XObject /Subtype /Image /Width 2 /Height 2 "
                b"/BitsPerComponent 8 /ColorSpace /DeviceGray "
                b"/Filter [ /ASCII85Decode /FlateDecode ] >>")
        pdf_bytes = _make_pdf(head, pixels)
        doc = PDFDoc(pdf_bytes)

        images = extract_images(doc, 1, self.tmp)
        self.assertEqual(images, [])

    def test_skipped_placement_does_not_consume_index(self):
        """一頁裡先放一張不支援的影像、再放一張支援的影像：後者的檔名
        index 必須是 01，不能因為前面跳過的那張而變成 02。"""
        cmyk_pixels = zlib.compress(bytes([0, 0, 0, 255]))
        cmyk_head = (b"<< /Type /XObject /Subtype /Image /Width 1 /Height 1 "
                     b"/BitsPerComponent 8 /ColorSpace /DeviceCMYK /Filter /FlateDecode >>")
        gray_pixels = zlib.compress(bytes([9]))
        gray_head = (b"<< /Type /XObject /Subtype /Image /Width 1 /Height 1 "
                     b"/BitsPerComponent 8 /ColorSpace /DeviceGray /Filter /FlateDecode >>")

        content = b"q\n1 0 0 1 0 0 cm\n/Im1 Do\nQ\nq\n1 0 0 1 10 10 cm\n/Im2 Do\nQ\n"
        page = _obj(1, b"<< /Type /Page /Resources << /XObject << /Im1 2 0 R "
                       b"/Im2 4 0 R >> >> /Contents 3 0 R >>")
        img1 = _obj(2, cmyk_head, cmyk_pixels)
        img2 = _obj(4, gray_head, gray_pixels)
        contentobj = _obj(3, b"<< >>", content)
        doc = PDFDoc(page + img1 + img2 + contentobj)

        images = extract_images(doc, 1, self.tmp)
        self.assertEqual(len(images), 1)
        self.assertEqual(os.path.basename(images[0]["file"]), "01-p01-01.png")


if __name__ == "__main__":
    unittest.main()
