"""Reproduce B dependency graphs and package independent QA evidence in CI."""
import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import tomllib
import zipfile
import xml.etree.ElementTree as ET

ROOT = pathlib.Path(__file__).resolve().parents[1]
MODULES = ["app", "core-model", "capture", "parser", "dedup", "categorizer", "data", "privacy", "security"]
REPORT = ROOT / "build/reports/b-experiment"


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2))


def run(command, log, cwd=ROOT, expected=0):
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("w") as stream:
        stream.write("COMMAND: " + " ".join(map(str, command)) + "\n")
        stream.flush()
        result = subprocess.run(list(map(str, command)), cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
        stream.write(f"\nEXIT_CODE: {result.returncode}\nEXPECTED_EXIT_CODE: {expected}\n")
    if result.returncode != expected:
        raise RuntimeError(f"Unexpected exit for {log.name}: {result.returncode}")
    return result.returncode


def tracked():
    return [x for x in subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0") if x]


def graph_snapshot(work, destination, write_metadata):
    probe = ROOT / "scripts/dependency_graph_probe.init.gradle"
    command = [work / "gradlew", "--no-daemon", "--console=plain", "--warning-mode", "all"]
    command += ["--write-verification-metadata", "sha256"] if write_metadata else ["--dependency-verification", "strict"]
    command += ["-I", str(probe), ":reviewFullGraph"]
    command += [":" + module + ":reviewFullGraph" for module in MODULES]
    command += [":build-logic:reviewFullGraph"]
    run(command, destination / "resolve.log", cwd=work)
    union = set()
    files = []
    for project in ["", *MODULES, "build-logic"]:
        path = work / project / "build/reports/security/review-full-graph.json"
        data = json.loads(path.read_text())
        target = destination / project / "full-graph.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        files.append(str(target.relative_to(destination)))
        union.update(c["id"] for scope in data["configurations"] for c in scope["components"])
    components = []
    for gav in sorted(union):
        group, name, version = gav.split(":")
        components.append({"type": "library", "group": group, "name": name, "version": version, "purl": f"pkg:maven/{group}/{name}@{version}"})
    dump(destination / "full-resolved.cdx.json", {"bomFormat": "CycloneDX", "specVersion": "1.5", "version": 1, "components": components})
    dump(destination / "context.json", {"projects": files, "coordinates": len(union)})
    return union


def compare_graphs(tools):
    REPORT.mkdir(parents=True, exist_ok=True)
    original = (ROOT / "gradle/verification-metadata.xml").read_bytes()
    catalog = tomllib.loads((ROOT / "gradle/libs.versions.toml").read_text())["versions"]
    pins = {
        "org.bitbucket.b_c:jose4j": catalog["toolingJose4j"],
        "org.bouncycastle:bcprov-jdk18on": catalog["toolingBc"],
        "org.bouncycastle:bcutil-jdk18on": catalog["toolingBc"],
        "org.bouncycastle:bcpkix-jdk18on": catalog["toolingBc"],
        "org.jdom:jdom2": catalog["toolingJdom2"],
    }
    with tempfile.TemporaryDirectory(prefix="moneymate-before-b-") as directory:
        baseline = pathlib.Path(directory)
        for name in tracked():
            target = baseline / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        settings = baseline / "settings.gradle.kts"
        text = settings.read_text()
        marker = 'plugins { id("moneymate.dependency-policy") }'
        if text.count(marker) != 1:
            raise ValueError("Policy marker changed; review the baseline recipe")
        settings.write_text(text.replace(marker, "// B policy disabled only in this isolated baseline copy"))
        build = baseline / "build-logic/build.gradle.kts"
        text = build.read_text()
        start = text.index("    constraints {")
        brace = text.index("{", start)
        depth = 1
        end = brace + 1
        while depth:
            depth += (text[end] == "{") - (text[end] == "}")
            end += 1
        removed = text[start:end]
        if removed.count("implementation(libs.tooling.") != 5:
            raise ValueError("Unexpected constraint baseline")
        build.write_text(text[:start] + text[end:])
        (baseline / "gradle/verification-metadata.xml").unlink()
        before = graph_snapshot(baseline, REPORT / "before", True)
        shutil.copyfile(baseline / "gradle/verification-metadata.xml", REPORT / "before/verification-metadata.xml")
        dump(REPORT / "baseline-recipe.json", {
            "kind": "reproduced-before-B-dependency-set",
            "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip(),
            "changes_in_isolated_copy": ["disable settings B plugin", "remove exactly five tooling constraints", "generate baseline-only metadata"],
            "production_source_modified": False,
            "removed_constraint_block": removed,
        })
    after = graph_snapshot(ROOT, REPORT / "after", False)
    removed, added = before - after, after - before
    if len(removed) != 5 or len(added) != 5 or {x.rsplit(":", 1)[0] for x in removed} != set(pins):
        raise RuntimeError("Dependency delta exceeds the five approved GAVs")
    if added != {gav + ":" + version for gav, version in pins.items()}:
        raise RuntimeError("Unexpected secure versions")
    purls = set()
    for path in [ROOT / "build/reports/security/dependencies.cdx.json", ROOT / "build-logic/build/reports/security/build-logic.cdx.json"]:
        purls.update(x["purl"] for x in json.loads(path.read_text())["components"])
    expected = {"pkg:maven/" + gav.rsplit(":", 1)[0].replace(":", "/") + "@" + gav.rsplit(":", 1)[1] for gav in after}
    if purls != expected:
        raise RuntimeError("Production SBOM does not cover the independent graph")
    loaded = []
    for path in ROOT.glob("**/build/reports/security/dependency-graph.json"):
        data = json.loads(path.read_text())
        for item in data["loadedClasses"]:
            name = item["gav"].split(":")[1] + "-" + pins[item["gav"]] + ".jar"
            if not (item["source"].endswith("/" + name) or item["source"].endswith("/instrumented-" + name)):
                raise RuntimeError("Wrong loaded tooling JAR")
            loaded.append({"project": data["project"], **item})
    if len(loaded) != 60:
        raise RuntimeError("Incomplete actual-JAR audit")
    for label, expected_exit in [("before", 1), ("after", 0)]:
        result = REPORT / (label + "-vulnerabilities.json")
        run([tools / "trivy", "sbom", "--severity", "HIGH,CRITICAL", "--exit-code", "1", "--format", "json", "--output", result, REPORT / label / "full-resolved.cdx.json"], REPORT / (label + "-scan.log"), expected=expected_exit)
        findings = [v for r in json.loads(result.read_text()).get("Results", []) for v in r.get("Vulnerabilities", [])]
        print("SCAN " + label + " " + json.dumps([{"id": v.get("VulnerabilityID"), "severity": v.get("Severity"), "package": v.get("PkgName"), "installed": v.get("InstalledVersion")} for v in findings]), flush=True)
        if (label == "before" and not findings) or (label == "after" and findings):
            raise RuntimeError("Scanner control did not produce the required evidence")
    if (ROOT / "gradle/verification-metadata.xml").read_bytes() != original:
        raise RuntimeError("Production metadata was modified")
    dump(REPORT / "loaded-jar-audit.json", loaded)
    dump(REPORT / "validation.json", {"result": "PASS", "before": len(before), "after": len(after), "removed": sorted(removed), "added": sorted(added), "independent_sbom_union_matches": True, "loaded_class_checks": len(loaded), "source_metadata_unchanged": True})
    print((REPORT / "validation.json").read_text(), flush=True)
    print("PASS: independent before/after graphs, exact five-GAV delta, full SBOM coverage, actual JARs and scans")


class JunitEvidenceError(RuntimeError):
    """Lỗi mã hóa bằng reason ID; không đưa nội dung test vào log lỗi."""


def junit_require(condition, reason):
    if not condition:
        raise JunitEvidenceError(reason)


def kotlin_code_only(text):
    """Giữ vị trí/newline, bỏ comment và literal để không đếm annotation giả."""
    output = list(text)
    index = 0
    while index < len(text):
        start = index
        if text.startswith('//', index):
            end = text.find('\n', index)
            index = len(text) if end < 0 else end
        elif text.startswith('/*', index):
            depth = 1
            index += 2
            while index < len(text) and depth:
                if text.startswith('/*', index):
                    depth += 1
                    index += 2
                elif text.startswith('*/', index):
                    depth -= 1
                    index += 2
                else:
                    index += 1
            junit_require(depth == 0, 'SOURCE_COMMENT')
        elif text.startswith('"""', index):
            end = text.find('"""', index + 3)
            junit_require(end >= 0, 'SOURCE_LITERAL')
            index = end + 3
        elif text[index] in ('"', "'"):
            quote = text[index]
            index += 1
            while index < len(text):
                if text[index] == '\\':
                    index += 2
                elif text[index] == quote:
                    index += 1
                    break
                else:
                    index += 1
            else:
                raise JunitEvidenceError('SOURCE_LITERAL')
        else:
            index += 1
            continue
        for pos in range(start, min(index, len(output))):
            if output[pos] not in ('\n', '\r'):
                output[pos] = ' '
    return ''.join(output)


def junit_source_inventory(source):
    """Chỉ hỗ trợ JUnit4 thường trong các source set/task đã được pipeline chạy."""
    source = pathlib.Path(source)
    inventory = {}
    for module in [*MODULES, 'build-logic']:
        build = source / module / 'build.gradle.kts'
        junit_require(build.is_file(), 'SOURCE_MODULE')
        android = bool(re.search(r'libs\.plugins\.android\.(application|library)', build.read_text()))
        task, variant = ('testDebugUnitTest', 'debugUnitTest') if android else ('test', 'jvm')
        test_sets = {'test', 'testDebug'} if android else {'test'}
        for path in sorted((source / module / 'src').rglob('*.kt')):
            relative = path.relative_to(source)
            source_set = relative.parts[2]
            if not source_set.startswith('test'):
                continue
            raw = path.read_bytes()
            code = kotlin_code_only(raw.decode('utf-8'))
            annotations = re.findall(r'@(?:org\.junit\.)?Test\b', code)
            if not annotations:
                continue
            junit_require(source_set in test_sets, 'SOURCE_SET')
            if re.search(r'@Test\b', code):
                junit_require(re.search(r'^\s*import\s+org\.junit\.Test\s*$', code, re.M), 'SOURCE_IMPORT')
            junit_require(not re.search(r'@(?:Ignore|Disabled)\b|@(?:RunWith|Parameterized|TestFactory)\b', code), 'SOURCE_UNSUPPORTED')
            packages = re.findall(r'^\s*package\s+([A-Za-z_][\w.]*)\s*$', code, re.M)
            classes = re.findall(r'\bclass\s+([A-Za-z_]\w*)', code)
            junit_require(len(packages) == len(classes) == 1, 'SOURCE_CLASS')
            methods = re.findall(r'@(?:org\.junit\.)?Test\b\s*(?:\([^)]*\)\s*)?(?:(?:public|internal)\s+)?fun\s+([A-Za-z_]\w*|`[^`]+`)\s*\(', code)
            junit_require(len(methods) == len(annotations), 'SOURCE_METHOD')
            classname = packages[0] + '.' + classes[0]
            for method in methods:
                method = method.strip('`')
                key = (module, task, variant, classname, method)
                junit_require(key not in inventory, 'SOURCE_DUPLICATE')
                inventory[key] = {
                    'module': module, 'task': task, 'variant': variant,
                    'sourceSet': source_set, 'class': classname, 'method': method,
                    'sourcePath': relative.as_posix(), 'sourceSha256': hashlib.sha256(raw).hexdigest(),
                }
    junit_require(inventory, 'SOURCE_EMPTY')
    return inventory


def verify_junit_inventory(source, artifacts):
    """Đối chiếu identity chính xác; không ghim tổng 20/22 hoặc dùng ngưỡng tối thiểu."""
    artifacts = pathlib.Path(artifacts)
    expected = junit_source_inventory(source)
    actual = {}
    xml_provenance = []
    xmls = sorted(p for p in artifacts.rglob('*.xml')
                  if p.name.startswith('TEST-') or 'test-results' in p.relative_to(artifacts).parts)
    junit_require(xmls, 'XML_EMPTY')
    for path in xmls:
        parts = path.relative_to(artifacts).parts
        junit_require(len(parts) == 5 and parts[0] in [*MODULES, 'build-logic']
                      and parts[1:3] == ('build', 'test-results'), 'XML_LOCATION')
        module, task = parts[0], parts[3]
        allowed = {k[1]: k[2] for k in expected if k[0] == module}
        junit_require(task in allowed, 'XML_VARIANT')
        raw = path.read_bytes()
        junit_require(b'<!DOCTYPE' not in raw and b'<!ENTITY' not in raw, 'XML_MALFORMED')
        try:
            suite = ET.fromstring(raw)
        except (ET.ParseError, ValueError):
            raise JunitEvidenceError('XML_MALFORMED') from None
        junit_require(suite.tag == 'testsuite', 'XML_SUITE')
        classname = suite.get('name')
        junit_require(classname and path.name == 'TEST-' + classname + '.xml', 'XML_CLASS')
        for field in ('tests', 'failures', 'errors', 'skipped'):
            junit_require(re.fullmatch(r'[0-9]+', suite.get(field, '')) is not None, 'XML_COUNTS')
        cases = list(suite.findall('testcase'))
        junit_require(cases and len(cases) == len(list(suite.iter('testcase')))
                      and int(suite.get('tests')) == len(cases), 'XML_COUNTS')
        junit_require(all(int(suite.get(k)) == 0 for k in ('failures', 'errors', 'skipped')), 'XML_OUTCOME')
        junit_require(not any(list(suite.iter(tag)) for tag in ('failure', 'error', 'skipped')), 'XML_OUTCOME')
        for case in cases:
            junit_require(case.get('classname') == classname and case.get('name'), 'XML_CLASS')
            key = (module, task, allowed[task], classname, case.get('name'))
            junit_require(key not in actual, 'XML_DUPLICATE')
            junit_require(key in expected, 'XML_EXTRA')
            actual[key] = path.relative_to(artifacts).as_posix()
        xml_provenance.append({'path': path.relative_to(artifacts).as_posix(),
                               'sha256': hashlib.sha256(raw).hexdigest(), 'module': module,
                               'task': task, 'variant': allowed[task], 'tests': len(cases)})
    junit_require(set(actual) == set(expected), 'XML_MISSING')
    rows = [dict(expected[key], xmlPath=actual[key]) for key in sorted(expected)]
    return {'tests': len(actual), 'failures': 0, 'errors': 0, 'skipped': 0}, {
        'status': 'PASS', 'sourceTestCount': len(expected), 'actualTestCount': len(actual),
        'inventory': rows, 'xmlProvenance': xml_provenance,
    }


def package_review(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    review = output / "review"
    review.mkdir(exist_ok=True)
    head = os.environ.get("REVIEW_HEAD_SHA") or subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    base = os.environ.get("REVIEW_BASE_SHA") or subprocess.check_output(["git", "rev-parse", head + "^"], cwd=ROOT).decode().strip()
    if not re.fullmatch(r"[0-9a-f]{40}", head) or not re.fullmatch(r"[0-9a-f]{40}", base):
        raise ValueError("Invalid source SHA")
    head_tree = subprocess.check_output(["git", "rev-parse", head + "^{tree}"], cwd=ROOT).decode().strip()
    checkout = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT).decode().strip()
    checkout_tree = subprocess.check_output(["git", "rev-parse", "HEAD^{tree}"], cwd=ROOT).decode().strip()
    if head_tree != checkout_tree:
        raise RuntimeError("CI preview differs from PR source tree; rebase before packaging")
    source = output / "MoneyMate"
    checksums = []
    for line in subprocess.check_output(["git", "ls-tree", "-rz", head], cwd=ROOT).decode().split("\0"):
        if not line:
            continue
        meta, name = line.split("\t", 1)
        mode, kind, blob = meta.split()
        if kind != "blob" or mode not in {"100644", "100755"}:
            raise ValueError("Unsupported source entry: " + name)
        data = subprocess.check_output(["git", "show", head + ":" + name], cwd=ROOT)
        target = source / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        target.chmod(int(mode[-3:], 8))
        checksums.append(hashlib.sha256(data).hexdigest() + "  " + name + "\n")
    (review / "source-sha256.txt").write_text("".join(checksums))
    shutil.copytree(args.reports, review / "artifacts", dirs_exist_ok=True)
    shutil.copytree(ROOT / "build/reports/emulator", review / "emulator", dirs_exist_ok=True)
    apks = output / "apks"
    apks.mkdir(exist_ok=True)
    shutil.copyfile(ROOT / "apk/app-debug.apk", apks / "app-debug.apk")
    shutil.copyfile(ROOT / "apk-release/app-release.apk", apks / "app-release.apk")
    shutil.copyfile(ROOT / "apk-release/app-release.apk.sha256", apks / "app-release.apk.sha256")
    for label, apk in [("debug", "app-debug.apk"), ("release-r8", "app-release.apk")]:
        digest = hashlib.sha256((apks / apk).read_bytes()).hexdigest()
        evidence = review / "emulator" / label
        if (evidence / "apk-sha256.txt").read_text().split()[0] != digest:
            raise RuntimeError("Installed APK differs from packaged APK")
        if "Status: ok" not in (evidence / "launch.txt").read_text():
            raise RuntimeError("Missing launch success")
        if not any(n.get("text") == "MoneyMate" and n.get("package") == "com.app.moneymate" for n in ET.parse(evidence / "window.xml").getroot().iter()):
            raise RuntimeError("MoneyMate not visible")
    totals, junit_inventory = verify_junit_inventory(source, review / "artifacts")
    junit_inventory['head'] = head
    junit_inventory['tree'] = head_tree
    dump(review / "junit-inventory.json", junit_inventory)
    exits = {}
    with tempfile.TemporaryDirectory(prefix="moneymate-review-git-") as directory:
        gitdir = pathlib.Path(directory) / "refs.git"
        for name, command in [
            ("git-init", ["git", "init", "--bare", "--quiet", gitdir]),
            ("git-fetch", ["git", "--git-dir", gitdir, "fetch", "--quiet", ROOT, base + ":refs/heads/main", head + ":refs/heads/review-head"]),
            ("git-head", ["git", "--git-dir", gitdir, "symbolic-ref", "HEAD", "refs/heads/review-head"]),
        ]:
            exits[name] = run(command, review / "commands" / (name + ".log"))
        for name, command in [
            ("diff-stat-main", ["diff", "--stat", "main...HEAD"]),
            ("changed-files", ["diff", "--name-status", "main...HEAD"]),
            ("docs-list", ["ls-tree", "-r", "--name-only", "HEAD", "docs/"]),
            ("git-log", ["log", "--format=fuller", "main..HEAD"]),
            ("diff-check", ["diff", "--check", "main...HEAD"]),
            ("bundle-create", ["bundle", "create", review / "MoneyMate.git.bundle", "--all"]),
            ("bundle-verify", ["bundle", "verify", review / "MoneyMate.git.bundle"]),
        ]:
            exits[name] = run(["git", "--git-dir", gitdir, *command], review / (name + ".txt"))
        restore = pathlib.Path(directory) / "restored"
        exits["bundle-clone"] = run(["git", "clone", "--quiet", "-b", "review-head", review / "MoneyMate.git.bundle", restore], review / "bundle-clone.log")
        conversions = []
        for item in checksums:
            digest, name = item.rstrip("\n").split("  ", 1)
            restored_blob = subprocess.check_output(["git", "-C", restore, "show", "HEAD:" + name])
            if hashlib.sha256(restored_blob).hexdigest() != digest:
                raise RuntimeError("Restored bundle Git blob mismatch: " + name)
            expected_checkout = subprocess.check_output(["git", "-C", restore, "cat-file", "--filters", "--path=" + name, "HEAD:" + name])
            actual_checkout = (restore / name).read_bytes()
            if actual_checkout != expected_checkout:
                raise RuntimeError("Restored checkout differs from Git attributes: " + name)
            if expected_checkout != restored_blob:
                conversions.append({"path": name, "blob_sha256": digest, "checkout_sha256": hashlib.sha256(actual_checkout).hexdigest(), "reason": "Git attributes checkout filter"})
        dump(review / "bundle-checkout-conversions.json", conversions)
        print("BUNDLE_CHECKOUT_CONVERSIONS " + json.dumps(conversions), flush=True)
    dump(review / "exit-codes.json", exits)
    run_url = "https://github.com/" + os.environ["GITHUB_REPOSITORY"] + "/actions/runs/" + os.environ["GITHUB_RUN_ID"]
    dump(review / "context.json", {"head": head, "base": base, "checkout": checkout, "tree": head_tree, "run": run_url, "junit": totals, "source_files": len(checksums), "acceptance": "PENDING independent QA/Leader"})
    command = ["python3", ROOT / "qa/tools/verify_review_package.py", output, "--json", review / "QA_AUTO_CHECKS.json", "--md", review / "QA_AUTO_CHECKS.md"]
    with (review / "qa-tool.log").open("w") as log:
        result = subprocess.run(list(map(str, command)), cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        log.write("\nEXIT_CODE: " + str(result.returncode) + "\n")
    dump(review / "qa-status.json", {"auto_tool_exit": result.returncode, "independent_qa": "NOT PERFORMED", "note": "QA result is recorded, not converted to acceptance. Known unchanged QA self-test triggers C07; QA/Leader must resolve it. PR remains Draft."})
    (output / "REVIEW.md").write_text(
        "# MoneyMate T00b — review evidence\n\nHEAD: " + head + "\nBase: " + base + "\nCI: " + run_url +
        "\n\nSource: MoneyMate/. Source hashes, bundle, exact main...HEAD diff, JUnit/lint/security/negative logs, baseline/after graphs and emulator are under review/. "
        "Baseline dependency set was reproduced in an isolated copy by disabling only the two B mechanisms; see artifacts/build/reports/b-experiment/baseline-recipe.json. "
        "This is not a claim that historical source was changed. Source metadata remains strict and unchanged. "
        "The actual installed debug/R8 APK hashes match apks/. No real keystore or release is included.\n\n"
        "Read review/QA_AUTO_CHECKS.md and qa-status.json: a failed QA finding stays failed; this archive is not QA acceptance. "
        "Known C07 is in the unchanged Approved QA tool self-test. Dependabot server validation and real first release remain deferred to QA/Leader/PO. "
        "Use README bootstrap instructions for ci-only squash and the Release-As footer when PO is ready; no tag/release was created by this task.\n"
    )
    scan_log = output.parent / "review-secrets.log"
    scan_json = output.parent / "review-secrets.json"
    run([args.tools / "gitleaks", "dir", "--redact=100", "--no-banner", "--report-format=json", "--report-path=" + str(scan_json), output], scan_log)
    shutil.copyfile(scan_log, review / "package-secrets.log")
    shutil.copyfile(scan_json, review / "package-secrets.json")
    paths = sorted(p for p in output.rglob("*") if p.is_file())
    (output / "MANIFEST.sha256").write_text("".join(hashlib.sha256(p.read_bytes()).hexdigest() + "  " + str(p.relative_to(output)) + "\n" for p in paths))
    archive = output.parent / ("MoneyMate_T00b_REVIEW_" + head[:7] + ".zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        for path in sorted(output.rglob("*")):
            if path.is_file():
                z.write(path, str(path.relative_to(output)))
    with zipfile.ZipFile(archive) as z:
        if z.testzip() is not None:
            raise RuntimeError("ZIP CRC failure")
    pathlib.Path(str(archive) + ".sha256").write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + "  " + archive.name + "\n")
    print((review / "diff-stat-main.txt").read_text(), flush=True)
    print((review / "context.json").read_text(), flush=True)
    print((review / "QA_AUTO_CHECKS.md").read_text(), flush=True)
    print("ARCHIVE_SHA256 " + hashlib.sha256(archive.read_bytes()).hexdigest(), flush=True)
    print("REVIEW_ARCHIVE " + str(archive))
    print("QA_AUTO_EXIT " + str(result.returncode) + " (not independent QA acceptance)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["graph", "package"])
    parser.add_argument("--tools", required=True, type=pathlib.Path)
    parser.add_argument("--reports", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    if args.mode == "graph":
        compare_graphs(args.tools.resolve())
    else:
        if not args.reports or not args.output:
            parser.error("package requires --reports and --output")
        package_review(args)
