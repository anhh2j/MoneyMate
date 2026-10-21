"""Local/CI security gates: full Git history, tracked tree, Gradle SBOMs and npm lock."""
import argparse
import json
import pathlib
import shutil
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]


def scan(tools, output):
    output.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(tools / "gitleaks"), "git", "--redact=100", "--no-banner", "--log-opts=--all", "--report-format=json", "--report-path=" + str(output / "secrets-history.json"), str(ROOT)], check=True)
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT).decode().split("\0")
    with tempfile.TemporaryDirectory(prefix="moneymate-tracked-scan-") as directory:
        tree = pathlib.Path(directory)
        for name in filter(None, tracked):
            target = tree / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)
        subprocess.run([str(tools / "gitleaks"), "dir", "--redact=100", "--no-banner", "--report-format=json", "--report-path=" + str(output / "secrets-tree.json"), str(tree)], check=True)
        npm = tree / "package-lock.json"
        if not npm.is_file():
            raise ValueError("Missing npm lockfile")
        subprocess.run([str(tools / "trivy"), "fs", "--scanners", "vuln", "--include-dev-deps", "--severity", "HIGH,CRITICAL", "--exit-code", "1", "--format", "json", "--output", str(output / "npm-vulnerabilities.json"), str(tree)], check=True)
    inventories = [ROOT / "build/reports/security/dependencies.cdx.json", ROOT / "build-logic/build/reports/security/build-logic.cdx.json"]
    for path in inventories:
        if not json.loads(path.read_text()).get("components"):
            raise ValueError("Missing/empty dependency inventory: " + str(path))
        subprocess.run([str(tools / "trivy"), "sbom", "--severity", "HIGH,CRITICAL", "--exit-code", "1", "--format", "json", "--output", str(output / (path.stem + "-vulnerabilities.json")), str(path)], check=True)
    print("PASS: history/tree secret scans and HIGH/CRITICAL dependency gates")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tools", required=True, type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path, default=ROOT / "build/reports/security")
    args = parser.parse_args()
    scan(args.tools.resolve(), args.output.resolve())
