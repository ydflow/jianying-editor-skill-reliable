import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
VENDOR = SCRIPTS / "vendor"
for path in (str(SCRIPTS), str(VENDOR)):
    if path not in sys.path:
        sys.path.insert(0, path)

from auto_exporter import auto_export
from doctor import _detect_playwright_browser, collect_diagnostics
from jy_wrapper import JyProject
from utils.media_normalizer import _norm_output_path, should_normalize_video_for_jianying


class TestReliableEdition(unittest.TestCase):
    def test_overwrite_moves_existing_draft_to_backup(self):
        with tempfile.TemporaryDirectory() as temp:
            drafts = os.path.join(temp, "drafts")
            backups = os.path.join(temp, "backups")
            first = JyProject(
                "SafeReplace", drafts_root=drafts, overwrite=True, backup_root=backups
            )
            first.save()
            marker = os.path.join(drafts, "SafeReplace", "keep-me.txt")
            Path(marker).write_text("original", encoding="utf-8")

            second = JyProject(
                "SafeReplace", drafts_root=drafts, overwrite=True, backup_root=backups
            )

            self.assertTrue(second.last_backup_path)
            self.assertTrue(os.path.isfile(os.path.join(second.last_backup_path, "keep-me.txt")))
            self.assertTrue(os.path.isdir(os.path.join(drafts, "SafeReplace")))

    def test_existing_draft_is_loaded_by_default(self):
        with tempfile.TemporaryDirectory() as temp:
            drafts = os.path.join(temp, "drafts")
            created = JyProject("LoadByDefault", drafts_root=drafts, overwrite=True)
            created.save()
            marker = os.path.join(drafts, "LoadByDefault", "keep-me.txt")
            Path(marker).write_text("original", encoding="utf-8")

            loaded = JyProject("LoadByDefault", drafts_root=drafts)

            self.assertIsNotNone(loaded.script)
            self.assertEqual(Path(marker).read_text(encoding="utf-8"), "original")
            self.assertIsNone(loaded.last_backup_path)

    def test_doctor_is_read_only(self):
        with tempfile.TemporaryDirectory() as temp:
            before = sorted(os.listdir(temp))
            result = collect_diagnostics(skill_root=str(ROOT), drafts_root=temp)
            after = sorted(os.listdir(temp))

            self.assertTrue(result["read_only"])
            self.assertEqual(before, after)

    @patch("doctor.os.path.isfile", return_value=False)
    def test_playwright_cache_without_expected_executable_is_not_ready(self, _mock_file):
        result = _detect_playwright_browser()

        self.assertFalse(result["installed"])
        self.assertTrue(result["executable"])

    @patch(
        "auto_exporter.detect_jianying_installation",
        return_value={"installed": True, "version": "11.4.2.14459", "executable": "x"},
    )
    def test_auto_export_blocks_unverified_new_version(self, _mock_detect):
        code, result = auto_export("Draft", "output.mp4")

        self.assertEqual(code, 2)
        self.assertEqual(result["code"], "unsupported_jianying_version")
        self.assertTrue(result["data"]["manual_export_required"])

    def test_normalized_media_cache_is_outside_source_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            source_dir = os.path.join(temp, "source")
            cache_dir = os.path.join(temp, "cache")
            os.makedirs(source_dir)
            source = os.path.join(source_dir, "clip.mp4")
            Path(source).write_bytes(b"demo")
            with patch.dict(os.environ, {"JY_CACHE_ROOT": cache_dir}):
                output = _norm_output_path(source)

            self.assertTrue(os.path.commonpath([cache_dir, output]) == cache_dir)
            self.assertFalse(os.path.commonpath([source_dir, output]) == source_dir)

    @patch("utils.media_normalizer.subprocess.run", side_effect=FileNotFoundError)
    def test_missing_ffprobe_degrades_without_crashing(self, _mock_run):
        self.assertFalse(should_normalize_video_for_jianying("clip.mp4"))


if __name__ == "__main__":
    unittest.main()
