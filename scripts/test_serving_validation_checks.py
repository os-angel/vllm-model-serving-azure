import json
import unittest
from serving_validation_checks import complete_choice, complete_stream, final_answer, quality


class AcceptanceChecks(unittest.TestCase):
    def test_reasoning_requires_a_nonempty_final_answer(self):
        self.assertEqual(final_answer("Razonamiento. </think>4", True), "4")
        for text in ("Solo razonamiento", "Razonamiento.</think>   "):
            with self.subTest(text=text), self.assertRaises(ValueError):
                final_answer(text, True)

    def test_request_profiles_and_budget(self):
        import importlib.util
        from pathlib import Path
        spec = importlib.util.spec_from_file_location("validator", Path(__file__).with_name("validate-serving.py"))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        module.configure_requests(True, 2048)
        self.assertEqual(module.CASES["system"], "/think")
        self.assertEqual(module.CASES["max_tokens"], 2048)
        self.assertEqual(module.CASES["temperature"], .6)
        module.configure_requests(False, 128)
        self.assertEqual(module.CASES["system"], "/no_think")
        for invalid in (0, -1, 4096):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                module.configure_requests(True, invalid)

    def test_chat_accepts_natural_completion(self):
        self.assertEqual(complete_choice({"message": {"content": "4"}, "finish_reason": "stop"}), "4")

    def test_chat_rejects_truncation_and_empty_output(self):
        for content, reason in (("4", "length"), ("", "stop"), ("4", None)):
            with self.subTest(content=content, reason=reason), self.assertRaises(ValueError):
                complete_choice({"message": {"content": content}, "finish_reason": reason})

    def test_quality_rejects_wrong_answer_and_multiple_sentences(self):
        with self.assertRaises(ValueError):
            quality("2", {"exact": "4"})
        with self.assertRaises(ValueError):
            quality("FP16 ahorra memoria.", {"required": [r"\bFP8\b"]})
        with self.assertRaises(ValueError):
            quality("Primera oración. Segunda oración.", {"one_sentence": True})

    def test_stream_requires_content_stop_and_done(self):
        for content, reason, done in (("4", "stop", True), ("4", "length", True), ("4", "stop", False), ("", "stop", True)):
            events = [{"data": json.dumps({"choices": [{"delta": {"content": content}, "finish_reason": reason}]})}]
            if done:
                events.append({"data": "[DONE]"})
            with self.subTest(content=content, reason=reason, done=done):
                if content and reason == "stop" and done:
                    self.assertEqual(complete_stream(events), "4")
                else:
                    with self.assertRaises(ValueError):
                        complete_stream(events)


if __name__ == "__main__":
    unittest.main()
