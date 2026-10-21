"""T00 DoD checks against generated artifacts and tracked files (stdlib only)."""

import pathlib
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
ANDROID = "{http://schemas.android.com/apk/res/android}"
REPORT = ROOT / "build/reports/dod"
REPORT.mkdir(parents=True, exist_ok=True)
results = []


def passed(message):
    results.append("PASS: " + message)
    print(results[-1])


for variant in ("debug", "release"):
    manifests = list((ROOT / "app/build/intermediates").glob(
        f"merged_manifest*/{variant}/**/AndroidManifest.xml"
    ))
    assert manifests, f"Missing generated {variant} manifest"
    for manifest in manifests:
        document = ET.parse(manifest).getroot()
        permissions = [element.get(ANDROID + "name") for element in document
                       if element.tag.startswith("uses-permission")]
        assert not permissions, f"Unexpected permissions in {manifest}: {permissions}"
    passed(f"{variant} merged manifest has no uses-permission ({len(manifests)} files)")

for module in ("parser", "dedup", "categorizer", "app"):
    report = (REPORT / f"{module}-dependencies.txt").read_text()
    assert "BUILD SUCCESSFUL" in report and "FAILED" not in report, module
    assert not re.search(r"com\.google\.firebase|com\.squareup\.okhttp|io\.ktor|retrofit", report), module
    if module != "app":
        assert not re.search(r"androidx\.|com\.android[.:]", report), module
    passed(f"{module} dependency report: no forbidden runtime dependency")

tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
for path in filter(None, tracked):
    name = pathlib.PurePosixPath(path).name
    assert name not in ("local.properties", "google-services.json"), path
    assert not name.endswith((".jks", ".keystore", ".p12", ".pem")), path
    data = (ROOT / path).read_bytes()
    assert b"-----BEGIN " + b"PRIVATE KEY-----" not in data, path
    assert not re.search(rb"gh[pousr]_[A-Za-z0-9]{36,}", data), path
passed("tracked files: no keystore, known secret signatures, local.properties")

sys.path.insert(0, str(ROOT / "scripts"))
from versioning import validate_source
validate_source(ROOT, tracked)
passed("version.properties is tracked and canonical; no version assignments in Gradle scripts")

for module in ("app", "core-model", "capture", "data", "privacy", "security", "parser", "dedup", "categorizer"):
    tests = list((ROOT / module / "src/test").rglob("*.kt"))
    smoke = [path for path in tests if path.name == "ModuleSmokeTest.kt"]
    assert len(smoke) == 1 and smoke[0].read_text().count("@Test") == 1, module
    # Developer-owned variant-aware check: every source test must execute, including testDebug.
    from t01_spike_checks import verify_junit
    verify_junit(ROOT / module)
passed("all nine smoke tests and all declared app metadata tests executed without failure/error/skip")
(REPORT / "skeleton-checks.txt").write_text("\n".join(results) + "\n")

logic_xmls = list((ROOT / "build-logic/build/test-results/test").glob("TEST-*.xml"))
assert logic_xmls, "Missing executed build-logic unit tests"
for xml in logic_xmls:
    suite = ET.parse(xml).getroot()
    assert int(suite.get("tests", 0)) > 0, xml
    assert all(int(suite.get(field, 0)) == 0 for field in ("failures", "errors", "skipped")), xml
passed("build-logic tests executed without failure/error/skip")
(REPORT / "skeleton-checks.txt").write_text("\n".join(results) + "\n")
