"""Negative controls for the developer-owned P-01 checker, not QA policy."""
import importlib.util
import pathlib
import shutil
import tempfile
import unittest
import zipfile
import xml.etree.ElementTree as ET

SPEC = importlib.util.spec_from_file_location("t01_spike_checks", pathlib.Path(__file__).resolve().parents[1] / "t01_spike_checks.py")
CHECKS = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECKS)
PACKAGER_SPEC = importlib.util.spec_from_file_location("t00b_review_evidence", pathlib.Path(__file__).resolve().parents[1] / "t00b_review_evidence.py")
PACKAGER = importlib.util.module_from_spec(PACKAGER_SPEC)
PACKAGER_SPEC.loader.exec_module(PACKAGER)


class PackagerJUnitTest(unittest.TestCase):
    MODULES = ("app", "core-model")

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = pathlib.Path(self.temp.name)
        self.source = self.root / "source"
        self.reports = self.root / "reports"
        for module, plugin, group in (("app", "android.application", "testDebugUnitTest"), ("core-model", "kotlin.jvm", "test")):
            project = self.source / module
            project.mkdir(parents=True)
            (project / "build.gradle.kts").write_text(f"plugins {{ alias(libs.plugins.{plugin}) }}")
            for source_set, cls in (("test", "Common"), ("testDebug", "DebugOnly")) if module == "app" else (("test", "Jvm"),):
                path = project / "src" / source_set / f"{cls}.kt"
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(f'package sample\nclass {cls} {{\n @Test\n fun works() {{ val fixture = "class NotATest" }}\n}}\n')
                report = self.reports / module / "build/test-results" / group / f"TEST-sample.{cls}.xml"
                report.parent.mkdir(parents=True, exist_ok=True)
                report.write_text(f'<testsuite name="sample.{cls}" tests="1" failures="0" errors="0" skipped="0"><testcase classname="sample.{cls}" name="works" /></testsuite>')

    def verify(self):
        return PACKAGER.verify_review_junit(self.source, self.reports, self.MODULES)

    def test_packager_exact_source_set_inventory_and_controls(self):
        result = self.verify()
        self.assertEqual(3, result["totals"]["tests"])
        self.assertEqual({"test", "testDebug"}, {x["source_set"] for x in result["tests"]})
        controls = PACKAGER.junit_negative_controls(self.source, self.reports, self.MODULES)
        self.assertEqual(7, len(controls["controls"]))
        self.assertEqual({"REJECTED"}, set(controls["controls"].values()))
        self.assertTrue(controls["original_xml_unchanged"])
        self.assertEqual(result, self.verify())

    def test_packager_missing_module_rejected(self):
        shutil.rmtree(self.reports / "core-model")
        with self.assertRaises(RuntimeError):
            self.verify()

    def test_packager_duplicate_xml_rejected(self):
        report = next(self.reports.rglob("TEST-*.xml"))
        shutil.copyfile(report, report.with_name("TEST-duplicate.xml"))
        with self.assertRaises(RuntimeError):
            self.verify()

    def test_packager_wrong_known_variant_rejected(self):
        path = self.reports / "app/build/test-results/testDebugUnitTest"
        path.rename(path.with_name("testReleaseUnitTest"))
        with self.assertRaises(RuntimeError):
            self.verify()

    def test_packager_counters_and_suite_identity_rejected(self):
        report = next(self.reports.rglob("TEST-*.xml"))
        original = report.read_text()
        for field in ("tests", "failures", "errors", "skipped", "name"):
            with self.subTest(field=field):
                suite = ET.fromstring(original)
                suite.set(field, "2")
                report.write_bytes(ET.tostring(suite))
                with self.assertRaises(RuntimeError):
                    self.verify()

    def test_packager_malformed_or_relocated_xml_rejected(self):
        report = next(self.reports.rglob("TEST-*.xml"))
        original = report.read_bytes()
        report.write_text("invalid")
        with self.assertRaises(ET.ParseError):
            self.verify()
        report.unlink()
        (self.reports / "TEST-relocated.xml").write_bytes(original)
        with self.assertRaises(RuntimeError):
            self.verify()

    def test_packager_unsupported_source_and_duplicate_declarations_rejected(self):
        path = self.source / "app/src/testRelease/Release.kt"
        path.parent.mkdir(parents=True)
        path.write_text("package sample\nclass Release { @Test fun works() {} }")
        with self.assertRaises(RuntimeError):
            self.verify()
        path.unlink()
        original = self.source / "app/src/test/Common.kt"
        duplicate = original.with_name("Duplicate.kt")
        duplicate.write_bytes(original.read_bytes())
        with self.assertRaises(RuntimeError):
            self.verify()


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
        shutil.rmtree(self.root / "build/test-results/unexpected")
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

    def test_probe_rejects_target_only_runtime(self):
        path = self.root / "Probe.class"
        path.write_bytes(bytes.fromhex("cafebabe") + b"framework-only")
        CHECKS.verify_probe_bytecode([path])
        path.write_bytes(bytes.fromhex("cafebabe") + b"kotlin/jvm/internal/Intrinsics")
        with self.assertRaises(AssertionError):
            CHECKS.verify_probe_bytecode([path])
        with self.assertRaises(AssertionError):
            CHECKS.verify_probe_bytecode([])

    def test_canary_redaction(self):
        CHECKS.scan_canary(b"metadata only")
        with self.assertRaisesRegex(AssertionError, "content suppressed"):
            CHECKS.scan_canary("_".join(("T01", "SYNTHETIC", "CANARY")).encode())


if __name__ == "__main__":
    unittest.main()
