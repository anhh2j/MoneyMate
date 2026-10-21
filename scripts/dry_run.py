"""Build/verify R8 with an isolated disposable keystore; never tags or publishes."""
import base64
import os
import pathlib
import secrets
import shutil
import subprocess
import sys
import tempfile
from versioning import read_version

ROOT = pathlib.Path(__file__).resolve().parents[1]


def dry_run():
    reports = ROOT / "build/reports/release"
    reports.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    password = secrets.token_urlsafe(24)
    env["MM_DRY_STORE_PASSWORD"] = password
    env["MM_DRY_KEY_PASSWORD"] = password
    with tempfile.TemporaryDirectory(prefix="moneymate-dry-run-") as directory:
        store = pathlib.Path(directory) / "dry-run.jks"
        with (reports / "keytool.log").open("w") as log:
            subprocess.run(["keytool", "-genkeypair", "-noprompt", "-storetype", "JKS", "-keystore", str(store), "-storepass:env", "MM_DRY_STORE_PASSWORD", "-keypass:env", "MM_DRY_KEY_PASSWORD", "-alias", "moneymate-dry-run", "-keyalg", "RSA", "-keysize", "2048", "-validity", "2", "-dname", "CN=MoneyMate dry run,O=Local tests"], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        env.update(KEYSTORE_BASE64=base64.b64encode(store.read_bytes()).decode(), KEYSTORE_PASSWORD=password, KEY_PASSWORD=password, KEY_ALIAS="moneymate-dry-run")
        with (reports / "signed-build.log").open("w") as log:
            subprocess.run([str(ROOT / "gradlew"), ":app:assembleRelease", "--dependency-verification", "strict", "--console=plain", "--no-daemon", "--warning-mode", "all"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        apk = ROOT / "app/build/outputs/apk/release/app-release.apk"
        name, _ = read_version(ROOT)
        command = [sys.executable, str(ROOT / "scripts/verify_release.py")]
        with (reports / "verify-pass.log").open("w") as log:
            subprocess.run(command + ["v" + name, str(apk), "--checksum", str(apk) + ".sha256"], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
            log.write("\nEXIT_CODE: 0\n")
        # Validate release-please headings without editing tracked source.
        with tempfile.TemporaryDirectory(prefix="moneymate-changelog-probe-") as fixture:
            fixture = pathlib.Path(fixture)
            shutil.copyfile(ROOT / "version.properties", fixture / "version.properties")
            subprocess.run(["git", "init", "--quiet", str(fixture)], check=True)
            headings = [
                ("plain", "## " + name + "\n", 0),
                ("bracket", "## [" + name + "]\n", 0),
                ("linked", "## [" + name + "](https://example.invalid/compare)\n", 0),
                ("wrong-version", "## " + name + ".0\n", 1),
            ]
            for label, heading, expected in headings:
                (fixture / "CHANGELOG.md").write_text(heading)
                with (reports / ("verify-changelog-" + label + ".log")).open("w") as log:
                    result = subprocess.run(command + ["v" + name, str(apk), "--root", str(fixture)], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
                    log.write("\nEXIT_CODE: " + str(result.returncode) + "\nEXPECTED_EXIT_CODE: " + str(expected) + "\n")
                if result.returncode != expected:
                    raise RuntimeError("Unexpected changelog verification result: " + label)
                if expected and "Missing CHANGELOG entry" not in (reports / ("verify-changelog-" + label + ".log")).read_text():
                    raise RuntimeError("Changelog negative failed for an unrelated reason")
        different = "v0.0.1" if name != "0.0.1" else "v0.0.2"
        with (reports / "verify-tag-mismatch.log").open("w") as log:
            result = subprocess.run(command + [different, str(apk)], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            if result.returncode != 1:
                raise RuntimeError("Verifier did not reject mismatched tag")
            log.write("\nEXPECTED_EXIT_CODE: 1\n")
        # Re-run positive verification after the negative control.
        with (reports / "verify-restored-pass.log").open("w") as log:
            subprocess.run(command + ["v" + name, str(apk)], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
            log.write("\nEXIT_CODE: 0\n")
        debug = ROOT / "app/build/outputs/apk/debug/app-debug.apk"
        if not debug.is_file():
            raise ValueError("Build assembleDebug first to compare APK sizes")
        (reports / "apk-sizes.txt").write_text(f"debug_bytes={debug.stat().st_size}\nrelease_r8_bytes={apk.stat().st_size}\nrelease_minus_debug_bytes={apk.stat().st_size - debug.stat().st_size}\n")
    if store.exists():
        raise RuntimeError("Temporary keystore was not removed")
    print("PASS: signed R8 release; aapt/apksigner/checksum; mismatched tag rejected; positive verification restored; temporary keystore removed")


if __name__ == "__main__":
    dry_run()
