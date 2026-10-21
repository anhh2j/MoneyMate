"""Check DOC-VER naming, identity, header version and history without editing DOCX."""
import argparse
import pathlib
import re
import sys
import xml.etree.ElementTree as ET
import zipfile

NAME = re.compile(r"[0-9]{2}_.+_v([0-9]+\.[0-9]+\.[0-9]+)\.docx")
CODES = {"DOC-SPEC", "DOC-PLAN", "DOC-TEST", "DOC-VER", "DOC-BRIEF-M0", "DOC-SEC", "DOC-UX", "DOC-QA", "DOC-TC"}


def check(root):
    seen = set()
    paths = sorted(pathlib.Path(root).glob("*.docx"))
    for path in paths:
        match = NAME.fullmatch(path.name)
        if not match:
            raise ValueError("Invalid document filename: " + path.name)
        with zipfile.ZipFile(path) as archive:
            document = ET.fromstring(archive.read("word/document.xml"))
        paragraphs = ["".join(p.itertext()).strip() for p in document.findall(".//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p")]
        code = paragraphs[paragraphs.index("Mã tài liệu") + 1]
        version = paragraphs[paragraphs.index("Phiên bản") + 1]
        if code not in CODES or code in seen:
            raise ValueError("Unknown/duplicate current document: " + code)
        if version != match[1] or "Lịch sử thay đổi" not in paragraphs:
            raise ValueError("Document header/version/history mismatch: " + path.name)
        seen.add(code)
    if seen != CODES:
        raise ValueError("Missing current documents: " + ", ".join(sorted(CODES - seen)))
    print(f"PASS: {len(paths)} current DOCX files; unique document codes, filenames, header versions and history")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--docs", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parents[1] / "docs")
    try:
        check(parser.parse_args().docs)
    except (ValueError, OSError, zipfile.BadZipFile, ET.ParseError) as error:
        print("FAIL: " + str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
