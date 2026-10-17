"""T00 DoD checks against generated artifacts and tracked files (stdlib only)."""

import pathlib
import re
import subprocess
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
    assert name not in ("local.properties", "google-services.json", "version.properties"), path
    assert not name.endswith((".jks", ".keystore", ".p12", ".pem")), path
    data = (ROOT / path).read_bytes()
    assert b"-----BEGIN " + b"PRIVATE KEY-----" not in data, path
    assert not re.search(rb"gh[pousr]_[A-Za-z0-9]{36,}", data), path
passed("tracked files: no keystore, known secret signatures, local.properties or version.properties")

assignments = []
for path in ROOT.rglob("*.gradle.kts"):
    if "build" in path.relative_to(ROOT).parts or ".gradle" in path.parts:
        continue
    for field, value in re.findall(r'\b(versionName|versionCode)\s*=\s*("[^"\n]*"|\d+)', path.read_text()):
        assignments.append((path.relative_to(ROOT).as_posix(), field, value))
assert sorted(assignments) == [
    ("app/build.gradle.kts", "versionCode", "1"),
    ("app/build.gradle.kts", "versionName", '\"0.0.0-dev\"'),
], assignments
assert "tạm, sẽ được T00b thay bằng version.properties" in (ROOT / "app/build.gradle.kts").read_text()
passed("temporary version values have one source with the required comment")

for module in ("app", "core-model", "capture", "data", "privacy", "security", "parser", "dedup", "categorizer"):
    tests = list((ROOT / module / "src/test").rglob("*.kt"))
    assert sum(path.read_text().count("@Test") for path in tests) == 1, module
    xmls = list((ROOT / module / "build/test-results").rglob("TEST-*.xml"))
    assert xmls, f"No executed test results: {module}"
    for xml in xmls:
        suite = ET.parse(xml).getroot()
        assert int(suite.get("tests", 0)) == 1, xml
        assert all(int(suite.get(field, 0)) == 0 for field in ("failures", "errors", "skipped")), xml
passed("all nine modules have exactly one smoke test and passing executed test reports")
(REPORT / "skeleton-checks.txt").write_text("\n".join(results) + "\n")
