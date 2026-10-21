#!/usr/bin/env python3
"""MoneyMate QA – kiểm tra tự động một gói review của dev (chỉ thư viện chuẩn).

Dùng: verify_review_package.py <thư mục gốc gói> [--json out.json] [--md out.md]
      verify_review_package.py --selftest
Mã thoát: 0 = không FAIL/BLOCKED, 1 = có FAIL, 2 = có BLOCKED (thiếu bằng chứng).
Script chỉ kiểm tra các điều khách quan. Phán đoán còn lại là việc của QA agent.
"""
import hashlib, json, os, re, subprocess, sys, tempfile, shutil
import xml.etree.ElementTree as ET

FORBIDDEN_LIBS = re.compile(r"firebase|okhttp|ktor|retrofit|volley|play-services|gms", re.I)
ANDROID_DEP = re.compile(r"androidx\.|com\.android", re.I)
PURE = ("parser", "dedup", "categorizer", "core-model")
SECRET_PATTERNS = [
    (re.compile(r"-----BEGIN (RSA |EC |OPENSSH |)PRIVATE KEY-----"), "private key"),
    (re.compile(r"AKIA[0-9A-Z]{16}"), "AWS access key"),
    (re.compile(r"AIza[0-9A-Za-z_\-]{35}"), "Google API key"),
    (re.compile(r"(?i)(password|passwd|storePassword|keyPassword)\s*[=:]\s*['\"][^'\"\s$]{4,}['\"]"), "mật khẩu viết cứng"),
]
PII = [(re.compile(r"\d{8,}"), "≥ 8 chữ số liên tiếp"),
       (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "email"),
       (re.compile(r"(?<!\d)(0|\+84)\d{9,10}(?!\d)"), "số điện thoại VN")]
R = []

def add(cid, name, res, detail=""):
    R.append({"id": cid, "check": name, "result": res, "detail": detail})

def walk(root, pred):
    for d, _, fs in os.walk(root):
        for f in fs:
            p = os.path.join(d, f)
            if pred(p): yield p

def find_src(root):
    for c in ("MoneyMate", "src", "."):
        p = os.path.join(root, c)
        if os.path.isdir(os.path.join(p, "app")) or os.path.isfile(os.path.join(p, "settings.gradle.kts")):
            return p
    return None

def c01(root):
    f = os.path.join(root, "review", "source-sha256.txt")
    if not os.path.isfile(f): return add("C01", "Toàn vẹn gói (SHA-256)", "BLOCKED", "thiếu review/source-sha256.txt")
    bad, miss, n = [], [], 0
    for line in open(f, encoding="utf-8"):
        m = re.match(r"^([0-9a-f]{64})\s+\*?(.+)$", line.strip())
        if not m: continue
        n += 1; h, p = m.groups()
        cand = [os.path.join(root, "MoneyMate", p), os.path.join(root, p)]
        fp = next((c for c in cand if os.path.isfile(c)), None)
        if not fp: miss.append(p); continue
        if hashlib.sha256(open(fp, "rb").read()).hexdigest() != h: bad.append(p)
    ok = not bad and not miss and n > 0
    add("C01", "Toàn vẹn gói (SHA-256)", "PASS" if ok else "FAIL", f"{n} mục; lệch: {bad[:5]}; thiếu: {miss[:5]}")

def c02(root):
    f = os.path.join(root, "review", "exit-codes.json")
    if not os.path.isfile(f): return add("C02", "Mã thoát các lệnh", "BLOCKED", "thiếu review/exit-codes.json")
    d = json.load(open(f, encoding="utf-8"))
    bad = {k: v for k, v in d.items() if v != 0}
    add("C02", "Mã thoát các lệnh", "PASS" if d and not bad else "FAIL", f"{len(d)} lệnh; khác 0: {bad}")

def c03(root):
    xs = list(walk(os.path.join(root, "review"), lambda p: os.path.basename(p).startswith("TEST-") and p.endswith(".xml")))
    if not xs: return add("C03", "Kết quả test (JUnit XML)", "BLOCKED", "không có TEST-*.xml")
    t = f = e = s = 0
    for x in xs:
        r = ET.parse(x).getroot()
        t += int(r.get("tests", 0)); f += int(r.get("failures", 0)); e += int(r.get("errors", 0)); s += int(r.get("skipped", 0))
    res = "FAIL" if (f or e or t == 0) else ("WARN" if s else "PASS")
    add("C03", "Kết quả test (JUnit XML)", res, f"{len(xs)} file; tests={t} failures={f} errors={e} skipped={s}")

def c04(root):
    ms = list(walk(os.path.join(root, "review"), lambda p: p.endswith("AndroidManifest.xml") and "merged_manifest" in p))
    if not ms: return add("C04", "Merged manifest", "BLOCKED", "không có merged manifest")
    perms, expo, backup = set(), set(), set()
    A = "{http://schemas.android.com/apk/res/android}"
    for m in ms:
        r = ET.parse(m).getroot()
        for el in r:
            if el.tag.startswith("uses-permission"): perms.add(el.get(A + "name"))
        app = r.find("application")
        if app is not None:
            backup.add(app.get(A + "allowBackup"))
            for c in app:
                if c.get(A + "exported") == "true": expo.add(c.get(A + "name"))
    res = "FAIL" if perms or backup - {"false"} else "PASS"
    add("C04", "Merged manifest (chính sách MVP: không uses-permission, allowBackup=false)", res,
        f"permissions={sorted(p for p in perms if p)}; allowBackup={sorted(map(str, backup))}; exported(INFO)={sorted(expo)}")

def c05(root):
    fs = list(walk(os.path.join(root, "review"), lambda p: p.endswith("-dependencies.txt")))
    if not fs: return add("C05", "Dependency report", "BLOCKED", "không có *-dependencies.txt")
    bad = []
    for f in fs:
        mod = os.path.basename(f).replace("-dependencies.txt", ""); txt = open(f, encoding="utf-8", errors="ignore").read()
        if FORBIDDEN_LIBS.search(txt): bad.append(f"{mod}: thư viện mạng/Firebase")
        if mod in PURE and ANDROID_DEP.search(txt): bad.append(f"{mod}: phụ thuộc Android")
    add("C05", "Dependency report (không mạng/Firebase; module thuần không Android)", "FAIL" if bad else "PASS", f"{len(fs)} báo cáo; lỗi: {bad}")

def c06(root):
    rep, bad = 0, []
    for p in walk(os.path.join(root, "review"), lambda p: True):
        b = os.path.basename(p)
        if b in ("checkstyle.xml", "detekt.xml"):
            rep += 1
            if "<error" in open(p, encoding="utf-8", errors="ignore").read(): bad.append(b)
        if b.startswith("lint-results") and b.endswith(".txt"):
            rep += 1
            if "No issues found" not in open(p, encoding="utf-8", errors="ignore").read(): bad.append(b)
    add("C06", "ktlint / detekt / lint", "BLOCKED" if rep == 0 else ("FAIL" if bad else "PASS"), f"{rep} báo cáo; có lỗi: {bad}")

def c07(src):
    hits = []
    for p in walk(src, lambda p: ".git" + os.sep not in p and "build" + os.sep not in p):
        if p.endswith((".jks", ".keystore", ".p12")): hits.append((p, "file keystore")); continue
        if os.path.getsize(p) > 512_000: continue
        try: txt = open(p, encoding="utf-8").read()
        except Exception: continue
        for rx, nm in SECRET_PATTERNS:
            if rx.search(txt): hits.append((os.path.relpath(p, src), nm))
    add("C07", "Quét secret trong mã nguồn", "FAIL" if hits else "PASS", f"{hits[:8]}")

def c08(src):
    lit = re.compile(r"version(Name|Code)\s*=\s*(\"[^\"]+\"|\d+)")
    hits = [os.path.relpath(p, src) for p in walk(src, lambda p: p.endswith((".gradle.kts", ".gradle")) and "build" + os.sep not in p)
            if lit.search(open(p, encoding="utf-8", errors="ignore").read())]
    add("C08", "versionName/versionCode viết cứng (INFO)", "INFO", f"{hits}")

def c09(src):
    fx = os.path.join(src, "fixtures")
    if not os.path.isdir(fx): return add("C09", "PII trong fixture", "NA", "chưa có thư mục fixtures")
    hits = []
    for p in walk(fx, lambda p: p.endswith(".txt")):
        t = open(p, encoding="utf-8", errors="ignore").read()
        for rx, nm in PII:
            if rx.search(t): hits.append((os.path.relpath(p, fx), nm))
    add("C09", "PII trong fixture", "FAIL" if hits else "PASS", f"{hits[:8]}")

def c10(root):
    b = next(iter(walk(os.path.join(root, "review"), lambda p: p.endswith(".bundle"))), None)
    if not b: return add("C10", "Git bundle", "NA", "không có bundle")
    tmp = tempfile.mkdtemp()
    try:
        subprocess.run(["git", "init", "-q", tmp], check=True, capture_output=True, timeout=30)
        r = subprocess.run(["git", "-C", tmp, "bundle", "verify", os.path.abspath(b)], capture_output=True, text=True, timeout=60)
        out = (r.stdout + r.stderr).strip().replace("\n", " ")[:200]
        if r.returncode == 0: add("C10", "Git bundle verify", "PASS", out)
        elif "prerequisite" in out.lower() or "lacks" in out.lower():
            add("C10", "Git bundle verify", "WARN", "bundle cần commit nền; hãy verify trong bản clone của repo: " + out)
        else: add("C10", "Git bundle verify", "FAIL", out)
    except Exception as ex:
        add("C10", "Git bundle verify", "NA", f"không chạy được git: {ex}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

def run(root):
    R.clear(); src = find_src(root)
    c01(root); c02(root); c03(root); c04(root); c05(root); c06(root)
    if src: c07(src); c08(src); c09(src)
    else: add("C07", "Quét secret / version / PII", "BLOCKED", "không tìm thấy thư mục mã nguồn")
    c10(root)
    return list(R)

def verdict(rs):
    if any(r["result"] == "FAIL" for r in rs): return "QA-FAIL", 1
    if any(r["result"] == "BLOCKED" for r in rs): return "QA-BLOCKED", 2
    return "AUTO-CHECKS-PASS", 0

def md(rs, v):
    L = [f"# Kết quả kiểm tra tự động: {v}", "", "| ID | Kiểm tra | Kết quả | Chi tiết |", "|---|---|---|---|"]
    L += [f"| {r['id']} | {r['check']} | **{r['result']}** | {str(r['detail']).replace('|', '/')} |" for r in rs]
    L += ["", "Lưu ý: AUTO-CHECKS-PASS không phải QA-PASS. QA agent vẫn phải thực hiện các bước kiểm tra độc lập và đánh giá phán đoán."]
    return "\n".join(L)

def selftest():
    tmp = tempfile.mkdtemp()
    try:
        def mk(good):
            root = os.path.join(tmp, "good" if good else "bad"); os.makedirs(root + "/review/artifacts/app/build/intermediates/merged_manifest/debug")
            os.makedirs(root + "/MoneyMate/app"); open(root + "/MoneyMate/app/a.txt", "w").write("x")
            h = hashlib.sha256(b"x").hexdigest()
            open(root + "/review/source-sha256.txt", "w").write(f"{h}  app/a.txt\n")
            json.dump({"build": 0 if good else 1}, open(root + "/review/exit-codes.json", "w"))
            open(root + "/review/artifacts/TEST-a.xml", "w").write(f'<testsuite tests="1" failures="{0 if good else 1}" errors="0" skipped="0"/>')
            perm = "" if good else '<uses-permission android:name="android.permission.INTERNET"/>'
            open(root + "/review/artifacts/app/build/intermediates/merged_manifest/debug/AndroidManifest.xml", "w").write(
                f'<manifest xmlns:android="http://schemas.android.com/apk/res/android">{perm}<application android:allowBackup="false"/></manifest>')
            open(root + "/review/parser-dependencies.txt", "w").write("ok" if good else "implementation com.squareup.okhttp3")
            open(root + "/review/lint-results-debug.txt", "w").write("No issues found.")
            fake_password_assignment = "".join(("storePassword", ' = "', "hunter2xx", '"'))
            open(root + "/MoneyMate/app/build.gradle.kts", "w").write("android {}" if good else fake_password_assignment)
            return root
        g, b = run(mk(True)), run(mk(False))
        assert verdict(g)[1] == 0, g
        fails = {r["id"] for r in b if r["result"] == "FAIL"}
        assert {"C02", "C03", "C04", "C05", "C07"} <= fails, fails
        print("SELFTEST OK: gói tốt qua; gói lỗi bị bắt:", sorted(fails)); return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a or a[0] in ("-h", "--help"): print(__doc__); sys.exit(0)
    if a[0] == "--selftest": sys.exit(selftest())
    rs = run(a[0]); v, code = verdict(rs); out = md(rs, v); print(out)
    for i, x in enumerate(a):
        if x == "--json" and i + 1 < len(a): json.dump({"verdict": v, "results": rs}, open(a[i + 1], "w"), ensure_ascii=False, indent=2)
        if x == "--md" and i + 1 < len(a): open(a[i + 1], "w", encoding="utf-8").write(out)
    sys.exit(code)
