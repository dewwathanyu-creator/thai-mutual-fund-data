"""ส่งออกข้อมูลเป็นไฟล์ JSON สำหรับโฮสต์แบบ static (ไม่ต้องมีเซิร์ฟเวอร์ Python)
ผลลัพธ์: web/public/data/{meta.json, funds.json, funds/<proj_id>.json, nav/<proj_id>__<class>.json}
จากนั้น build ด้วย `npm run build:static` (VITE_STATIC=1) จะได้ web/dist ที่เปิดจากโฮสต์ไฟล์ธรรมดาได้
ไฟล์ที่ได้เป็นข้อมูลสาธารณะจาก SEC Open API: ตรวจเงื่อนไขการเผยแพร่ซ้ำก่อนนำขึ้นอินเทอร์เน็ตสาธารณะ (ดู docs/sec_api_terms_check.md)
"""
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api import funds_data  # noqa: E402
from api.main import DISCLAIMER, PAST_PERF  # noqa: E402

OUT = ROOT / "web" / "public" / "data"


def safe(s: str) -> str:
    """ชื่อไฟล์ที่ปลอดภัย (ต้องตรงกับฟังก์ชันเดียวกันใน web/src/api.ts)"""
    return re.sub(r"[^A-Za-z0-9_-]", lambda m: "~%x" % ord(m.group()), s)


def dump(path: Path, obj) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), default=str)
    path.write_text(text, encoding="utf-8")
    return len(text.encode("utf-8"))


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    summary = funds_data.summary()
    dump(OUT / "meta.json", {"disclaimer": DISCLAIMER, "past_performance_notice": PAST_PERF, "funds": summary})
    size = dump(OUT / "funds.json", {"items": funds_data.load_list(), "summary": summary, "past_performance_notice": PAST_PERF})
    print(f"funds.json {size/1e6:.1f} MB")

    by_proj: dict[str, list] = {}
    for r in funds_data.load_funds():
        by_proj.setdefault(r["proj_id"], []).append(r)
    n_nav = 0
    for pid, classes in by_proj.items():
        dump(OUT / "funds" / f"{safe(pid)}.json", {"proj_id": pid, "classes": classes})
        for c in classes:
            series = funds_data.nav_series(pid, c["fund_class_name"])
            dump(OUT / "nav" / f"{safe(pid)}__{safe(c['fund_class_name'])}.json", {"series": series, "empty": not series})
            n_nav += 1
    total = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"{len(by_proj)} โครงการ, {n_nav} ไฟล์ NAV, รวม {total/1e6:.1f} MB ที่ {OUT}")


if __name__ == "__main__":
    main()
