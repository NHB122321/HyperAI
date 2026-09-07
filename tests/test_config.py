import importlib.util
import os
from pathlib import Path
import unittest
from unittest.mock import patch


CONFIG_PATH = Path(__file__).resolve().parents[1] / "config.py"


def read_config(environment):
    # Изолируем настройки от настоящего .env и не меняем импорт config у бота.
    spec = importlib.util.spec_from_file_location("isolated_test_config", CONFIG_PATH)
    module = importlib.util.module_from_spec(spec)
    with patch.dict(os.environ, environment, clear=True):
        with patch("dotenv.load_dotenv") as load:
            spec.loader.exec_module(module)
    return module, load


class ConfigTests(unittest.TestCase):
    def test_defaults_and_compatibility_alias(self):
        config, _ = read_config({})
        self.assertEqual(config.FAST_MODEL, "gpt-5.6-luna")
        self.assertEqual(config.SMART_MODEL, "gpt-6-astra")
        self.assertEqual(config.TRANSCRIPTION_MODEL, "gpt-transcribe")
        self.assertEqual(config.MODEL_MODE, "auto")
        self.assertEqual(config.MODEL, config.FAST_MODEL)

    def test_environment_can_override_each_model_and_default_mode(self):
        config, _ = read_config({
            "FAST_MODEL": " local-fast ",
            "SMART_MODEL": "local-smart",
            "TRANSCRIPTION_MODEL": "local-voice",
            "MODEL_MODE": " SMART ",
        })
        self.assertEqual(config.FAST_MODEL, "local-fast")
        self.assertEqual(config.SMART_MODEL, "local-smart")
        self.assertEqual(config.TRANSCRIPTION_MODEL, "local-voice")
        self.assertEqual(config.MODEL_MODE, "smart")
        self.assertEqual(config.MODEL, "local-fast")

    def test_dotenv_path_is_anchored_to_config_and_preserves_environment(self):
        _, load = read_config({})
        load.assert_called_once_with(CONFIG_PATH.parent / ".env", override=False)

    def test_empty_model_settings_are_rejected(self):
        for name in ("FAST_MODEL", "SMART_MODEL", "TRANSCRIPTION_MODEL"):
            with self.subTest(name=name):
                with self.assertRaisesRegex(ValueError, name):
                    read_config({name: "  "})

    def test_unknown_or_empty_default_modes_are_rejected(self):
        for mode in ("", "premium", "automatic"):
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(ValueError, "MODEL_MODE"):
                    read_config({"MODEL_MODE": mode})


if __name__ == "__main__":
    unittest.main()
