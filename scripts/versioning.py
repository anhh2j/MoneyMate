"""Independent release verification of DOC-VER 3.5 (stdlib only)."""
import pathlib
import re

PATTERN = re.compile(r"(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-(alpha|beta|rc)\.([1-9][0-9]*))?(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?")


def parse_version(value):
    match = PATTERN.fullmatch(value)
    if not match:
        raise ValueError("Invalid or unsupported SemVer: " + value)
    major, minor, patch = map(int, match.group(1, 2, 3))
    if minor > 99 or patch > 99:
        raise ValueError("MINOR/PATCH must be in 0..99")
    stage, number = match.group(4, 5)
    rank = 99
    if stage:
        number = int(number)
        if not 1 <= number <= 29:
            raise ValueError("Pre-release sequence must be in 1..29")
        rank = {"alpha": 0, "beta": 30, "rc": 60}[stage] + number
    code = major * 1_000_000 + minor * 10_000 + patch * 100 + rank
    if code > 2_147_483_647:
        raise ValueError("versionCode exceeds Android integer range")
    return value.split("+", 1)[0], code


def read_version(root):
    path = pathlib.Path(root) / "version.properties"
    values = [line.strip() for line in path.read_text().splitlines() if line.strip() and not line.lstrip().startswith("#")]
    if len(values) != 1 or not values[0].startswith("VERSION_NAME="):
        raise ValueError("version.properties must contain exactly one VERSION_NAME assignment and no other keys")
    return parse_version(values[0].split("=", 1)[1])


def validate_source(root, tracked):
    root = pathlib.Path(root)
    if "version.properties" not in tracked:
        raise ValueError("version.properties must be tracked")
    read_version(root)
    for name in tracked:
        if name.endswith(".gradle.kts"):
            text = (root / name).read_text()
            if re.search(r"\b(versionName|versionCode)\s*(?:=|\.set\s*\()", text):
                raise ValueError("Version assignment must live in build-logic convention plugin: " + name)
    plugin = (root / "build-logic/src/main/kotlin/com/app/moneymate/buildlogic/AppBuildPlugin.kt").read_text()
    if 'Versioning.read(project.rootProject.file("version.properties"))' not in plugin:
        raise ValueError("App plugin must read the canonical version.properties")
