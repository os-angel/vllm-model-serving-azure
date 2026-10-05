import importlib.util
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location("render_chat", Path(__file__).with_name("render-chat-manifest.py"))
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ManifestTests(unittest.TestCase):
    def test_digest_reference_and_cpu_resources(self):
        # Syntax-only fixture, never a published or deployable image.
        image = module.PREFIX + "@sha256:" + "0123456789abcdef" * 4
        rendered = module.render(image)
        self.assertIn("image: " + image, rendered)
        self.assertNotIn("${APP_IMAGE}", rendered)
        self.assertIn("workload: cpu", rendered)
        self.assertIn("type: ClusterIP", rendered)
        self.assertNotIn("nvidia.com/gpu", rendered)

    def test_tags_unknown_repository_and_injection_are_rejected(self):
        for image in [module.PREFIX + ":latest", module.PREFIX + "@sha256:" + "0" * 64,
                      "evil.example/chat@sha256:" + "0123456789abcdef" * 4,
                      module.PREFIX + "@sha256:abc\n---\nkind: Secret"]:
            with self.subTest(image=image), self.assertRaises(ValueError):
                module.render(image)


if __name__ == "__main__":
    unittest.main()
