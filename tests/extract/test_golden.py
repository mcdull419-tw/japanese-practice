import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from tools.extract import cli

GOLDEN = "data/lessons/07.json"


class TestGolden(unittest.TestCase):
    def test_cli_reproduces_golden_file(self):
        """重跑管線必須產出與 golden file 完全相同的結果（決定性）。

        golden file 是用 `--images data/images` 產生的（Task 14：最終
        資料含影像清單），所以這裡也帶 `--images` 呼叫，但刻意指向一個
        跟 `data/images` 不同的暫存目錄——`images[].file` 存的是規範化
        識別碼（固定 `data/images/<檔名>`，見 cli.py `extract_lesson`
        說明），不受實際寫檔目錄影響，這樣才能同時驗證「內容決定性」與
        「識別碼與呼叫參數無關」兩件事。"""
        self.assertTrue(os.path.exists(GOLDEN), "golden file 不存在，請先執行 CLI 產生")
        with open(GOLDEN, encoding="utf-8") as fh:
            expected = json.load(fh)
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as img_tmp:
            subprocess.run(
                ["python3", "-m", "tools.extract.cli", "7", "--out", tmp,
                 "--images", img_tmp],
                check=True)
            with open(os.path.join(tmp, "07.json"), encoding="utf-8") as fh:
                actual = json.load(fh)
        self.assertEqual(actual, expected)

    def test_cli_output_is_byte_identical_to_golden_file(self):
        """`assertEqual` 比對的是 parse 後的物件，容忍鍵序／空白等差
        異；但 golden file 比對真正要保證的是位元組層級的決定性（同一
        道題的 SRS 歷史不會因為重跑就失效），所以另外直接比對檔案內
        容本身，不透過 json.load 正規化掉任何差異。同樣帶 `--images`
        指向另一個暫存目錄（理由同上）。"""
        with open(GOLDEN, "rb") as fh:
            expected_bytes = fh.read()
        with tempfile.TemporaryDirectory() as tmp, \
             tempfile.TemporaryDirectory() as img_tmp:
            subprocess.run(
                ["python3", "-m", "tools.extract.cli", "7", "--out", tmp,
                 "--images", img_tmp],
                check=True)
            with open(os.path.join(tmp, "07.json"), "rb") as fh:
                actual_bytes = fh.read()
        self.assertEqual(actual_bytes, expected_bytes)

    def test_golden_passes_validation(self):
        from tools.extract.validate import validate_lesson
        with open(GOLDEN, encoding="utf-8") as fh:
            data = json.load(fh)
        self.assertEqual(validate_lesson(data), [])

    def test_cli_exits_nonzero_when_validation_fails(self):
        """`--validate` 有問題時，程序結束碼須為 1，讓 CI 能攔截。用
        一份刻意留空 kana 的假課次資料換掉 golden file 位置不可行（不
        能動 golden file），改成直接對 CLI 產出的資料做人為破壞後跑
        `validate_lesson`，並且另外對「真的跑過 CLI」這件事本身做一次
        結束碼檢查（成功情境）。"""
        result = subprocess.run(
            ["python3", "-m", "tools.extract.cli", "7", "--out", tempfile.mkdtemp(),
             "--validate"],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(result.returncode, 0,
                          "第 7 課驗證應通過，結束碼應為 0：%r" % (result.stderr,))
        self.assertIn(b"\xe2\x9c\x93", result.stdout)  # ✓

    def test_main_exits_1_when_validate_finds_problems(self):
        """對 CLI 的 main() 做進程內測試（不透過 subprocess，較快也較
        穩定）：把 `validate_lesson` 換成永遠回報一個問題的假函式，確
        認 `--validate` 模式下結束碼真的是 1，不是只有訊息裡印個
        ✗ 但結束碼仍是 0 這種半吊子失敗。"""
        with tempfile.TemporaryDirectory() as tmp:
            argv = ["cli.py", "7", "--out", tmp, "--validate"]
            with mock.patch.object(sys, "argv", argv), \
                 mock.patch.object(cli, "validate_lesson", return_value=["假的問題"]):
                with self.assertRaises(SystemExit) as ctx:
                    cli.main()
            self.assertEqual(ctx.exception.code, 1)

    def test_main_exits_0_when_validate_finds_no_problems(self):
        with tempfile.TemporaryDirectory() as tmp:
            argv = ["cli.py", "7", "--out", tmp, "--validate"]
            with mock.patch.object(sys, "argv", argv):
                with self.assertRaises(SystemExit) as ctx:
                    cli.main()
            self.assertEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
