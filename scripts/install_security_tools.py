"""Install pinned public scanner binaries outside the repository, verifying SHA-256."""
import argparse
import hashlib
import io
import json
import pathlib
import tarfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parents[1]


def install(directory):
    directory = pathlib.Path(directory).resolve()
    if directory == ROOT or ROOT in directory.parents:
        raise ValueError("Install security tools outside the repository")
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    tools = json.loads((ROOT / "scripts/security-tools.json").read_text())
    for name, spec in tools.items():
        with urllib.request.urlopen(spec["url"], timeout=120) as response:
            data = response.read()
        if hashlib.sha256(data).hexdigest() != spec["sha256"]:
            raise ValueError("Checksum mismatch for " + name)
        with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
            member = archive.getmember(name)
            if not member.isfile():
                raise ValueError("Unexpected scanner archive member")
            binary = archive.extractfile(member).read()
        path = directory / name
        path.write_bytes(binary)
        path.chmod(0o700)
        print("PASS: installed " + name + " " + spec["version"] + "; SHA-256 verified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=pathlib.Path)
    install(parser.parse_args().directory)
