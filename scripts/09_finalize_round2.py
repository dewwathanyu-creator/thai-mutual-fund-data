"""ตรวจความครบของข้อมูลรอบ 2 แล้วสร้างตารางกองทุนจากไฟล์ (ไม่เรียก API)"""

import csv
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

from fund_fetch import LATEST_DIR, ROUND2_ORDER
from sec_client import DATA_DIR, utf8_stdout


def target_projects():
    with (DATA_DIR / "fund_class_types.csv").open(encoding="utf-8-sig", newline="") as f:
        return sorted({row["proj_id"] for row in csv.DictReader(f)
                       if row["tax_type"] in ("RMF", "ThaiESG", "ThaiESGX")
                       and row["fund_status"] in ("Registered", "IPO")})


def audit_files(projects):
    missing, unfinished, errors = [], [], []
    statuses = Counter()
    for endpoint in ROUND2_ORDER:
        for proj_id in projects:
            path = LATEST_DIR / endpoint / f"{proj_id}.json"
            if not path.exists():
                missing.append((endpoint, proj_id))
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (ValueError, OSError):
                unfinished.append((endpoint, proj_id, "ไฟล์อ่านไม่ได้"))
                continue
            status = data.get("status")
            statuses[(endpoint, status)] += 1
            if not data.get("complete"):
                unfinished.append((endpoint, proj_id, "pagination ยังไม่ครบ"))
            elif status not in (200, 204):
                errors.append((endpoint, proj_id, status))
    return missing, unfinished, errors, statuses


def main():
    utf8_stdout()
    projects = target_projects()
    missing, unfinished, errors, statuses = audit_files(projects)
    print(f"เป้าหมาย {len(projects)} proj_id x {len(ROUND2_ORDER)} endpoint")
    for endpoint in ROUND2_ORDER:
        ok = statuses[(endpoint, 200)] + statuses[(endpoint, 204)]
        print(f"  {endpoint}: พบไฟล์สถานะ 200/204 จำนวน {ok}/{len(projects)}")
    print(f"ขาดไฟล์ {len(missing)}, ยังไม่สมบูรณ์ {len(unfinished)}, HTTP error {len(errors)}")
    for title, rows in (("ขาด", missing), ("ไม่สมบูรณ์", unfinished), ("HTTP error", errors)):
        if rows:
            print(f"ตัวอย่าง {title}: {rows[:5]}")
    if missing or unfinished or errors:
        return 1

    script = Path(__file__).with_name("08_build_funds_table.py")
    spec = importlib.util.spec_from_file_location("build_funds_table", script)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.main()
    return 0


if __name__ == "__main__":
    sys.exit(main())
