"""`validate_lesson` 不變式檢查測試。

任務簡報 Step 1 的 10 個官方測試（`TestValidate`）原封不動保留，逐字
比對簡報範例，確保介面契約不被實作細節帶偏。

`TestExtraInvariants` 是全案複審清單額外要求納入的檢查——每一條都有
「壞資料真的會被抓到」的斷言，不是只驗「好資料通過」（好資料通過測
不出檢查邏輯本身是否被改壞；這正是全案六次「測試全綠但資料是壞的」
事故的共同成因）。`TestPatternSubstitutionCompleteness` 額外用全 15
課實測找到的僅有 4 處代入表空槽位（2 好 2 壞，見 `tools/extract/
validate.py` 模組說明）做為判準的具體證據，不是憑空捏造的合成案例。
"""
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


class TestOptionalKeysAreTolerated(unittest.TestCase):
    """驗收條件明確要求選用鍵一律 `data.get(key, [])`，不得假設存在。
    只給 `lesson` 這一個鍵，若實作內部直接索引 `data["vocab"]` 之類會
    立刻 KeyError，這裡斷言不會拋例外、且視為通過（沒有資料可查就沒
    有問題可報）。"""

    def test_missing_optional_keys_do_not_raise(self):
        self.assertEqual(validate_lesson({"lesson": 1}), [])

    def test_empty_dict_does_not_raise(self):
        self.assertEqual(validate_lesson({}), [])


class TestExtraInvariants(unittest.TestCase):
    """全案複審清單額外要求的檢查，簡報 Step 3 的表格沒有列出。每條
    都用「壞資料真的被抓到」證明檢查邏輯有在運作。"""

    def test_good_data_still_passes_with_extra_checks(self):
        self.assertEqual(validate_lesson(copy.deepcopy(GOOD)), [])

    def test_detects_cp1252_misdecoding_fingerprint(self):
        """第二種誤解碼指紋：Shift-JIS 誤讀為 cp1252，首位元組
        0x82／0x83 變成 `‚`（U+201A）／`ƒ`（U+0192），第二位元組直接
        映成同碼位的 Latin-1 補充字元。這裡用 Shift-JIS「こと」「ば」
        誤讀後的真實結果 `‚±‚Æ‚Î` 當壞資料——這正是任務簡報以外、開
        發過程中真實讓第 13 課整課日文變成亂碼的損毀類型，原本的
        `MISDECODE_FINGERPRINT` 字元集合完全不涵蓋它（那個集合只涵蓋
        GB18030 誤讀路徑），若移除 cp1252 專屬的正則檢查，這個測試會
        變紅但官方 10 個測試依然全綠——證明官方測試集本身不足以擋住
        這第二種真實發生過的損毀，必須額外補上。"""
        bad = copy.deepcopy(GOOD)
        bad["sentences"][0]["jp"] = "‚±‚Æ‚Î"
        problems = validate_lesson(bad)
        self.assertTrue(any("誤解碼" in p for p in problems))
        self.assertTrue(any("cp1252" in p for p in problems))

    def test_cp1252_fingerprint_does_not_false_positive_on_normal_japanese(self):
        """好資料（一般日文假名／漢字／中文）不該被 cp1252 指紋誤判——
        `‚`／`ƒ` 這兩個字元不會出現在正常日文或中文文字裡，這裡用
        GOOD 本身（已含假名、漢字、中文標點「」）驗證沒有誤報。"""
        self.assertEqual(validate_lesson(copy.deepcopy(GOOD)), [])

    def test_detects_circled_mark_left_in_sentence(self):
        """例句的 jp 不應含課本編號用的圈號（①②③…⑳），那是課本排版
        的編號標記，不是句子內容。"""
        bad = copy.deepcopy(GOOD)
        bad["sentences"][0]["jp"] = "①わたしは 手紙を 書きます。"
        problems = validate_lesson(bad)
        self.assertTrue(any("圈號" in p for p in problems))

    def test_detects_circled_mark_left_in_grammar_example(self):
        """圈號殘留也可能出現在文法解說的例句裡，不只是 `sentences`
        陣列——兩處都要查，否則同一種損毀換個位置就會漏檢。"""
        bad = copy.deepcopy(GOOD)
        bad["grammar"][0]["examples"][0]["jp"] = "③はしで 食べます。"
        problems = validate_lesson(bad)
        self.assertTrue(any("圈號" in p for p in problems))

    def test_good_data_has_no_circled_marks_false_positive(self):
        self.assertEqual(validate_lesson(copy.deepcopy(GOOD)), [])

    def test_detects_kanji_field_as_pure_punctuation(self):
        """漢字欄若被誤抽成純標點（例如把課本的頓號誤判成漢字內
        容），代表欄位歸屬壞掉，必須攔下。"""
        bad = copy.deepcopy(GOOD)
        bad["vocab"][0]["kanji"] = "、"
        problems = validate_lesson(bad)
        self.assertTrue(any("漢字" in p for p in problems))

    def test_kanji_field_none_is_not_flagged_as_punctuation(self):
        """`kanji` 為 `None`（單字本身就沒有漢字寫法，例如純假名詞）
        是合法狀態，不該被誤判成「純標點」缺陷。"""
        good = copy.deepcopy(GOOD)
        good["vocab"][0]["kanji"] = None
        self.assertEqual(validate_lesson(good), [])

    def test_detects_incomplete_usage(self):
        """帶 `usage` 的單字，其 `usage.kana`／`usage.kanji` 皆須非
        空——回歸第 7 課第 9 筆「かけます」的遺失缺陷（spec §13 明文
        列出的既有回歸案例）。"""
        bad = copy.deepcopy(GOOD)
        bad["vocab"][0]["usage"] = {"kana": "でんわを～", "kanji": ""}
        problems = validate_lesson(bad)
        self.assertTrue(any("搭配" in p for p in problems))

    def test_usage_none_is_not_flagged(self):
        """大多數單字沒有搭配用法子行，`usage: None` 是常態，不該被
        誤判成缺陷。"""
        self.assertEqual(validate_lesson(copy.deepcopy(GOOD)), [])

    def test_detects_missing_kana(self):
        """spec §13「每筆三欄（假名／漢字／中文）齊備」是假名與中文
        兩者都要非空的複合條件——官方 10 個測試只用 `zh` 缺漏當範例，
        沒有測到 `kana` 缺漏那一半，這裡補上，否則把 kana 檢查整段刪
        掉，官方測試依然全綠。"""
        bad = copy.deepcopy(GOOD)
        bad["vocab"][0]["kana"] = ""
        problems = validate_lesson(bad)
        self.assertTrue(any("假名" in p for p in problems))

    def test_detects_pattern_index_out_of_range(self):
        """spec §13「每張代入表各列長度一致且索引在範圍內」是兩個子條
        件——官方 10 個測試只測了「長度一致」（row 長度不一致），沒有
        測到「索引在範圍內」那一半。這裡用長度正確、但索引超出候選詞
        清單範圍的壞資料補上，否則把索引範圍檢查整段刪掉，官方測試依
        然全綠。"""
        bad = copy.deepcopy(GOOD)
        bad["patterns"][0]["rows"] = [[0], [5]]  # 只有 2 個候選詞（0,1），5 越界
        problems = validate_lesson(bad)
        self.assertTrue(any("範圍" in p for p in problems))


class TestPatternSubstitutionCompleteness(unittest.TestCase):
    """代入表「代入後是否為完整句子」的判準必須是結構性的，不能只看
    句尾有無「。」，也不能只看有無空槽位（見任務簡報明確指出的四個
    真實案例）。這裡直接用全 15 課實測找到的僅有 4 處空槽位（`tools/
    extract/validate.py` 已記錄如何從 01.pdf／04.pdf／13.pdf／15.pdf
    用 `parse_pattern_tables` 實際跑出這四組 template／slots／rows），
    逐一斷言正確分類：2 處應保留（不報問題），2 處應標記。"""

    def test_l13_a4_empty_subject_slot_with_fixed_suffix_is_complete(self):
        """L13-A4：模板「わたしは{S}{T}に行きます。」——即使 S 留空，
        「に行きます。」這段固定尾綴保證代入結果一定有述語（買い物 是
        名詞可以直接接「に行きます」）。"""
        data = {
            "patterns": [{
                "id": "L13-A4",
                "template": "わたしは{S}{T}に行きます。",
                "slots": {
                    "S": ["神戸へ", "ロシア料理を", "", "びじゅつの"],
                    "T": ["あそび", "たべ", "かいもの", "べんきょう"],
                },
                "rows": [[0, 0], [1, 1], [2, 2], [3, 3]],
                "requires_lesson": 13,
            }],
        }
        problems = validate_lesson(data)
        self.assertEqual(problems, [], "L13-A4 空槽位是課本原本的排版，不該被標記")

    def test_l15_a3_empty_subject_slot_with_nonfinal_predicate_is_complete(self):
        """L15-A3：模板「わたしは{S}{T}います」——沒有句號，但最後一
        個佔位符 T 本身有值（けっこんして），代入結果依然是完整句
        子。單看句尾有無「。」會誤判這一例。"""
        data = {
            "patterns": [{
                "id": "L15-A3",
                "template": "わたしは{S}{T}います",
                "slots": {
                    "S": ["京都に", "マリアさんを", ""],
                    "T": ["すんで", "しって", "けっこんして"],
                },
                "rows": [[0, 0], [1, 1], [2, 2]],
                "requires_lesson": 15,
            }],
        }
        problems = validate_lesson(data)
        self.assertEqual(problems, [], "L15-A3 模板本身沒有句號，但代入結果完整，不該被標記")

    def test_l01_a4_empty_predicate_slot_is_flagged(self):
        """L01-A4：模板「{S}{T}」——T 是最後一個佔位符，這一列留空且
        模板在它之後沒有任何固定文字，代入結果「あの ひと」缺述語
        （課本跨列合併格造成的真實缺陷），必須標記。"""
        data = {
            "patterns": [{
                "id": "L01-A4",
                "template": "{S}{T}",
                "slots": {
                    "S": ["サントスさんは", "マリアさん", "あの ひと"],
                    "T": ["ブラジル人です。", "も ブラジル人です。", ""],
                },
                "rows": [[0, 0], [1, 1], [2, 2]],
                "requires_lesson": 1,
            }],
        }
        problems = validate_lesson(data)
        self.assertTrue(
            any("L01-A4" in p and "不完整" in p for p in problems),
            "L01-A4 第 2 列缺述語（あの ひと），必須被標記",
        )

    def test_l04_a6_empty_predicate_slot_is_flagged_for_both_rows(self):
        """L04-A6：模板「わたしは{S}{T}」——同一張表有兩列共用同一個
        空的 T 候選詞（index 1），兩列都該被標記，不是只抓到第一列就
        停手。"""
        data = {
            "patterns": [{
                "id": "L04-A6",
                "template": "わたしは{S}{T}",
                "slots": {
                    "S": ["まいにち", "あした", "きのう", "おととい"],
                    "T": ["勉強します。", "", "勉強しました。"],
                },
                "rows": [[0, 0], [1, 1], [2, 2], [3, 1]],
                "requires_lesson": 4,
            }],
        }
        problems = validate_lesson(data)
        flagged_rows = [p for p in problems if "L04-A6" in p and "不完整" in p]
        self.assertEqual(
            len(flagged_rows), 2,
            "L04-A6 有兩列（row 1＝あした、row 3＝おととい）都缺述語，必須各自被標記：%r" % problems,
        )


if __name__ == "__main__":
    unittest.main()
