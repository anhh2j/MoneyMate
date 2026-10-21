"""Developer-owned P-01 evidence checks. Never prints notification data."""
import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPIKE = (b"com/app/moneymate/spike/", b"com/app/moneymate/capture/spike/")
SERVICE = "com.app.moneymate.capture.spike.SpikeNotificationListenerService"
ACTIVITY = "com.app.moneymate.spike.SpikeActivity"
ANDROID = "{http://schemas.android.com/apk/res/android}"


def declared_tests(paths):
    result = set()
    for path in paths:
        source = path.read_text()
        package = re.search(r"^package (\S+)", source, re.M).group(1)
        cls = re.search(r"class (\w+)", source).group(1)
        names = re.findall(r"@Test\s+fun (\w+)\(", source)
        assert len(names) == source.count("@Test"), "Unsupported test annotation layout"
        for name in names:
            key = (package + "." + cls, name)
            assert key not in result, "Duplicate declared test"
            result.add(key)
    return result


def verify_junit(module):
    base = list((module / "src/test").rglob("*.kt"))
    assert base, "Missing base tests"
    groups = sorted((module / "build/test-results").glob("*"))
    groups = [group for group in groups if group.is_dir() and list(group.glob("TEST-*.xml"))]
    assert groups, "No executed test variants"
    seen_debug = False
    for group in groups:
        variants = {"test": None, "testDebugUnitTest": "testDebug", "testReleaseUnitTest": "testRelease"}
        assert group.name in variants, "Unknown test variant"
        variant = variants[group.name]
        sources = base + (list((module / "src" / variant).rglob("*.kt")) if variant else [])
        expected = declared_tests(sources)
        executed = set()
        for report in group.glob("TEST-*.xml"):
            suite = ET.parse(report).getroot()
            assert int(suite.get("tests", 0)) > 0, "Empty suite"
            assert all(int(suite.get(k, 0)) == 0 for k in ("failures", "errors", "skipped")), "Failed/skipped tests"
            cases = suite.findall("testcase")
            assert len(cases) == int(suite.get("tests", 0)), "Invalid suite count"
            for case in cases:
                assert not list(case), "Testcase has failure/skip/error or unknown content"
                key = (case.get("classname"), case.get("name"))
                assert key not in executed, "Duplicate executed test"
                executed.add(key)
        assert executed == expected, "Declared/executed tests differ for variant"
        seen_debug = seen_debug or group.name == "testDebugUnitTest"
    if list((module / "src/testDebug").rglob("*.kt")):
        assert seen_debug, "Missing debug unit test execution"
    return True


def verify_manifest(xml, debug):
    root = ET.fromstring(xml)
    assert not [e for e in root if e.tag.startswith("uses-permission")], "Unexpected permission"
    services = root.findall(".//service")
    spike = [e for e in services if e.get(ANDROID + "name") == SERVICE]
    activities = [e for e in root.findall(".//activity") if e.get(ANDROID + "name") == ACTIVITY]
    if debug:
        assert len(spike) == 1 and len(activities) == 1, "Missing debug component"
        assert spike[0].get(ANDROID + "exported") == "false", "Service exported"
        assert spike[0].get(ANDROID + "permission") == "android.permission.BIND_NOTIFICATION_LISTENER_SERVICE", "Binding permission missing"
        assert any(e.get(ANDROID + "name") == "android.service.notification.NotificationListenerService" for e in spike[0].findall(".//action")), "Listener filter missing"
        assert activities[0].get(ANDROID + "exported") == "true", "Missing debug launcher"
    else:
        assert not spike and not activities and "spike" not in xml.lower(), "Spike in release manifest"


def verify_apk(path, debug):
    with zipfile.ZipFile(path) as archive:
        dexes = [archive.read(n) for n in archive.namelist() if re.fullmatch(r"classes\d*\.dex", n)]
        assert dexes, "Missing DEX"
        found = all(any(signature in dex for dex in dexes) for signature in SPIKE)
        if debug:
            assert found, "Debug spike missing from DEX"
        else:
            assert not any(signature in dex for dex in dexes for signature in SPIKE), "Spike in release DEX"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def scan_canary(data):
    # Built at runtime; the complete sentinel must not occur in stored application/evidence data.
    canary = "_".join(("T01", "SYNTHETIC", "CANARY")).encode()
    assert canary not in data, "Sensitive canary detected (content suppressed)"


def checks():
    sdk = pathlib.Path(os.environ["ANDROID_HOME"])
    analyzer = sdk / "cmdline-tools/latest/bin/apkanalyzer"
    results = {}
    for variant in ("debug", "release"):
        apk = ROOT / f"app/build/outputs/apk/{variant}/app-{variant}.apk"
        if variant == "release" and not apk.exists():
            apk = apk.with_name("app-release-unsigned.apk")
        assert apk.is_file(), "Missing APK"
        xml = subprocess.check_output([str(analyzer), "manifest", "print", str(apk)], text=True)
        verify_manifest(xml, variant == "debug")
        results[variant] = verify_apk(apk, variant == "debug")
        resources = subprocess.check_output([str(analyzer), "files", "list", str(apk)])
        table = subprocess.check_output([str(sdk / "build-tools/37.0.0/aapt2"), "dump", "resources", str(apk)])
        if variant == "release":
            assert b"spike" not in resources.lower() and b"spike_" not in table.lower(), "Spike resource in release"
    # Unshrunk library classes prove isolation was not merely achieved by R8 removal.
    jars = [p for p in (ROOT / "capture/build/intermediates").rglob("*.jar")
            if "release" in str(p.relative_to(ROOT)).lower() and "classes" in p.name]
    assert jars, "Missing unshrunk release class inventory"
    for jar in jars:
        with zipfile.ZipFile(jar) as archive:
            assert not any("/spike/" in n for n in archive.namelist()), "Spike in unshrunk release"
    app_classes = [p for p in (ROOT / "app/build/intermediates").rglob("*.class")
                   if "release" in str(p.relative_to(ROOT)).lower()]
    assert app_classes, "Missing unshrunk app class inventory"
    assert not any("/spike/" in p.as_posix() for p in app_classes), "Spike in unshrunk app"
    results["unshrunk_app_classes"] = len(app_classes)
    results["unshrunk_release_jars"] = len(jars)
    report = ROOT / "build/reports/t01/static"
    report.mkdir(parents=True, exist_ok=True)
    (report / "result.json").write_text(json.dumps({"status": "PASS", "sha256": results}, indent=2) + "\n")
    print("PASS: P-01 APK manifest/DEX/resource path and unshrunk library isolation")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scan", type=pathlib.Path)
    args = parser.parse_args()
    if args.scan:
        scan_canary(args.scan.read_bytes())
        print("PASS: no canary in supplied bytes")
    else:
        checks()
