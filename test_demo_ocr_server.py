import unittest

from demo_ocr_server import build_completion_response


class DemoOcrServerTests(unittest.TestCase):
    def test_returns_openai_compatible_completion_without_external_service(self):
        response = build_completion_response("demo-ocr")

        self.assertEqual(response["model"], "demo-ocr")
        self.assertIn("本地演示 OCR 结果", response["choices"][0]["message"]["content"])


if __name__ == "__main__":
    unittest.main()
