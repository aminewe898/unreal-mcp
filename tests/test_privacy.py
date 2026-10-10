import importlib.util
from pathlib import Path
import unittest

FILE = Path(__file__).resolve().parents[1] / "Plugins/AmineUnrealMCP/Content/Python/amine_unreal_mcp/common/privacy.py"
spec = importlib.util.spec_from_file_location("amine_privacy", FILE)
privacy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(privacy)


class PrivacyTests(unittest.TestCase):
    def test_nested_sensitive_values_do_not_escape(self):
        source = {"position": {"x": 42}, "settings": [{"api_key": "private", "credential": "private"}], "password": "private"}
        result = privacy.redact(source)
        self.assertNotIn("private", str(result))
        self.assertEqual(result["position"], {"x": 42})
        self.assertEqual(source["password"], "private")

    def test_log_secrets_and_bearer(self):
        log = 'password="private value" access_token=private; Authorization: Bearer abc.def.xyz sk-proj-abcdefghijklmnopqrstuvwx'
        result = privacy.redact(log)
        for secret in ("private", "abc.def.xyz", "abcdefghijklmnopqrstuvwx"):
            self.assertNotIn(secret, result)

    def test_paths_and_ordinary_values_are_preserved(self):
        value = {"identifier": "/Game/BP_Actor.BP_Actor:Mesh", "default": 42.5, "message": "Shader compilation requested"}
        self.assertEqual(privacy.redact(value), value)


if __name__ == "__main__":
    unittest.main()
