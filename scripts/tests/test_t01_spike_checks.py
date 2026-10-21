"""Negative controls for the developer-owned P-01 checker, not QA policy."""
import importlib.util
import pathlib
import tempfile
import unittest
import zipfile

SPEC = importlib.util.spec_from_file_location("t01_spike_checks", pathlib.Path(__file__).resolve().parents[1] / "t01_spike_checks.py")
CHECKS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKS)


class SpikeChecksTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)

    def module(self, case='<testcase classname="sample.Check" name="works" />', attributes='tests="1" failures="0" errors="0" skipped="0"', group="test"):
        source = self.root / "src/test/Check.kt"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text("package sample\nclass Check {\n @Test\n fun works() {}\n}\n")
        output = self.root / "build/test-results" / group
        output.mkdir(parents=True, exist_ok=True)
        report = output / "TEST-sample.Check.xml"
        report.write_text(f'<testsuite {attributes}>{case}</testsuite>')
        return report

    def test_exact_tests_pass(self):
        self.module()
        self.assertTrue(CHECKS.verify_junit(self.root))

    def test_missing_and_extra_fail(self):
        self.module(case='<testcase classname="sample.Check" name="unknown" />')
        with self.assertRaises(AssertionError):
            CHECKS.verify_junit(self.root)

    def test_skip_and_failure_fail(self):
        for field in ("skipped", "errors", "failures"):
            self.module(attributes=f'tests="1" failures="{int(field == "failures")}" errors="{int(field == "errors")}" skipped="{int(field == "skipped")}"')
            with self.assertRaises(AssertionError):
                CHECKS.verify_junit(self.root)

    def test_unknown_variant_and_missing_debug_fail(self):
        self.module(group="unexpected")
        with self.assertRaises(AssertionError):
            CHECKS.verify_junit(self.root)
        self.module()
        debug = self.root / "src/testDebug/Extra.kt"
        debug.parent.mkdir(parents=True)
        debug.write_text("package sample\nclass Extra { @Test\n fun debugOnly() {} }")
        with self.assertRaises(AssertionError):
            CHECKS.verify_junit(self.root)

    def test_empty_or_malformed_xml_fail(self):
        report = self.module(case="", attributes='tests="0"')
        with self.assertRaises(AssertionError):
            CHECKS.verify_junit(self.root)
        report.write_text("invalid")
        with self.assertRaises(Exception):
            CHECKS.verify_junit(self.root)

    def test_missing_dex_and_release_spike_fail(self):
        path = self.root / "app.apk"
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("AndroidManifest.xml", b"placeholder")
        with self.assertRaises(AssertionError):
            CHECKS.verify_apk(path, False)
        with zipfile.ZipFile(path, "w") as archive:
            archive.writestr("classes.dex", CHECKS.SPIKE[0])
        with self.assertRaises(AssertionError):
            CHECKS.verify_apk(path, False)

    def test_release_manifest_and_binding_fail_closed(self):
        manifest = '<manifest xmlns:android="http://schemas.android.com/apk/res/android"><application /></manifest>'
        CHECKS.verify_manifest(manifest, False)
        with self.assertRaises(AssertionError):
            CHECKS.verify_manifest(manifest, True)
        with self.assertRaises(AssertionError):
            CHECKS.verify_manifest(manifest.replace('<application />', '<uses-permission android:name="android.permission.INTERNET"/><application/>'), False)

    def test_canary_redaction(self):
        CHECKS.scan_canary(b"metadata only")
        with self.assertRaisesRegex(AssertionError, "content suppressed"):
            CHECKS.scan_canary("_".join(("T01", "SYNTHETIC", "CANARY")).encode())


if __name__ == "__main__":
    unittest.main()
