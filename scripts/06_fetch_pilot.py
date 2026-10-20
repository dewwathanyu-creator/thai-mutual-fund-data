"""รอบ 1 ขั้น B: ดึงทุกหน้าของทุก endpoint สำหรับ 36 class ตัวอย่าง (สุ่มเมล็ด 2569, เฉพาะ Registered/IPO)
เพื่อวัดจำนวนคำขอที่ต้องใช้จริง และดูโครงสร้างข้อมูล; รันซ้ำได้ (ข้ามไฟล์ที่ครบแล้ว)
"""
import csv
import random
import time

from fund_fetch import ENDPOINTS, RateLimited, fetch, new_state
from sec_client import DATA_DIR, SecClient, save_json, utf8_stdout

PER_TYPE = {"RMF": 12, "ThaiESG": 12, "ThaiESGX": 12}


def pick():
    rows = list(csv.DictReader(open(DATA_DIR / "fund_class_types.csv", encoding="utf-8-sig")))
    rng, out = random.Random(2569), []
    for t, n in PER_TYPE.items():
        pool = sorted([r for r in rows if r["tax_type"] == t and r["fund_status"] in ("Registered", "IPO")],
                      key=lambda r: (r["proj_id"], r["fund_class_name"]))
        out += rng.sample(pool, n)
    return out


def main():
    utf8_stdout()
    sample = pick()
    save_json(DATA_DIR / "pilot_sample.json", [{k: r[k] for k in ("proj_id", "fund_class_name", "proj_abbr_name", "tax_type", "fund_status")} for r in sample])
    projs = sorted({r["proj_id"] for r in sample})
    print(f"{len(sample)} class จาก {len(projs)} proj_id | endpoint {len(ENDPOINTS)} ตัว")
    client, state, stats = SecClient(), new_state(), {}
    t0 = time.time()
    try:
        for i, pj in enumerate(projs, 1):
            for name in ENDPOINTS:
                rec = fetch(client, name, pj, state, max_pages=60)
                if rec:
                    s = stats.setdefault(name, {"funds": 0, "pages": 0, "rows": 0, "incomplete": 0, "no_content": 0, "errors": 0})
                    s["funds"] += 1
                    s["pages"] += rec.get("pages", 0)
                    s["rows"] += rec.get("n_items", 0)
                    s["incomplete"] += 0 if rec["complete"] else 1
                    s["no_content"] += 1 if rec.get("status") == 204 else 0
                    s["errors"] += 1 if rec.get("status") not in (200, 204) else 0
            print(f"  [{i}/{len(projs)}] {pj} calls={state['calls']} 429={state['n429']}", flush=True)
    except RateLimited as e:
        print("หยุด:", e)
    state["seconds"] = round(time.time() - t0)
    save_json(DATA_DIR / "pilot_stats.json", {"state": state, "per_endpoint": stats, "n_proj": len(projs)})
    print(state)
    for k, v in stats.items():
        print(k, v)


if __name__ == "__main__":
    main()
