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
        if (label == "before" and not findings) or (label == "after" and findings):
            raise RuntimeError("Scanner control did not produce the required evidence")
    if (ROOT / "gradle/verification-metadata.xml").read_bytes() != original:
        raise RuntimeError("Production metadata was modified")
    dump(REPORT / "loaded-jar-audit.json", loaded)
    dump(REPORT / "validation.json", {"result": "PASS", "before": len(before), "after": len(after), "removed": sorted(removed), "added": sorted(added), "independent_sbom_union_matches": True, "loaded_class_checks": len(loaded), "source_metadata_unchanged": True})
    print("PASS: independent before/after graphs, exact five-GAV delta, full SBOM coverage, actual JARs and scans")


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
    junit = [ET.parse(p).getroot() for p in (review / "artifacts").rglob("TEST-*.xml")]
    totals = {key: sum(int(x.get(key, 0)) for x in junit) for key in ["tests", "failures", "errors", "skipped"]}
    if totals != {"tests": 20, "failures": 0, "errors": 0, "skipped": 0}:
        raise RuntimeError("Unexpected JUnit outcome")
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
        for item in checksums:
            digest, name = item.rstrip("\n").split("  ", 1)
            if hashlib.sha256((restore / name).read_bytes()).hexdigest() != digest:
                raise RuntimeError("Restored bundle source mismatch")
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
