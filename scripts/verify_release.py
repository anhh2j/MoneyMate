"""Verify a locally built/signed APK before publishing; never publishes."""
import argparse
import hashlib
import os
import pathlib
import re
import shutil
import subprocess
import sys
from versioning import parse_version, read_version

ROOT = pathlib.Path(__file__).resolve().parents[1]


def tool(name, explicit):
    if explicit:
        return explicit
    found = shutil.which(name)
    if found:
        return found
    sdk = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if sdk:
        candidate = pathlib.Path(sdk) / "build-tools/37.0.0" / name
        if candidate.is_file():
            return str(candidate)
    raise ValueError("Missing Android build tool: " + name)


def verify(args):
    if not args.tag.startswith("v"):
        raise ValueError("Tag must start with v")
    expected = read_version(args.root)
    tagged = parse_version(args.tag[1:])
    if args.tag != "v" + expected[0] or tagged != expected:
        raise ValueError("Tag does not match canonical version.properties")
    apk = pathlib.Path(args.apk)
    badging = subprocess.check_output([tool("aapt", args.aapt), "dump", "badging", str(apk)], text=True)
    match = re.search(r"package: name='([^']+)' versionCode='(\d+)' versionName='([^']+)'", badging)
    if not match or (match[1], int(match[2]), match[3]) != ("com.app.moneymate", expected[1], expected[0]):
        raise ValueError("APK applicationId/versionName/versionCode does not match tag and formula")
    subprocess.run([tool("apksigner", args.apksigner), "verify", "--verbose", str(apk)], check=True)
    changelog = (pathlib.Path(args.root) / "CHANGELOG.md").read_text()
    if not re.search(r"^## \[" + re.escape(expected[0]) + r"\](?:\([^\s)]+\))?(?:[ \t]|$)", changelog, re.MULTILINE):
        raise ValueError("Missing CHANGELOG entry for release version")
    tracked = subprocess.check_output(["git", "ls-files", "-z"], cwd=args.root).decode().split("\0")
    if any(pathlib.Path(p).suffix.lower() in {".jks", ".keystore", ".p12", ".pem"} for p in tracked if p):
        raise ValueError("Tracked signing material is forbidden")
    digest = hashlib.sha256(apk.read_bytes()).hexdigest()
    print(f"PASS: {args.tag}; applicationId=com.app.moneymate; versionCode={expected[1]}; signed APK")
    print(f"SHA256 {digest}  {apk.name}")
    if args.checksum:
        pathlib.Path(args.checksum).write_text(f"{digest}  {apk.name}\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tag")
    parser.add_argument("apk")
    parser.add_argument("--root", type=pathlib.Path, default=ROOT)
    parser.add_argument("--aapt")
    parser.add_argument("--apksigner")
    parser.add_argument("--checksum")
    try:
        verify(parser.parse_args())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print("FAIL: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
