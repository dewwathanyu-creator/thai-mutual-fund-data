"""รอบ 2: ดึงข้อมูลกองที่คัดแล้ว (RMF/ThaiESG/ThaiESGX, Registered/IPO) ทุก proj_id
latest=true สำหรับ factsheet, NAV ย้อนหลัง 1 ปี; ผลที่ data/raw_latest/<endpoint>/<proj_id>.json
รันซ้ำได้: ข้ามไฟล์ที่ complete แล้ว; หยุดทันทีเมื่อ 429 ซ้ำ; เรียงตามความสำคัญ (endpoint ถูกก่อน)
"""
import csv
import sys
import time
from datetime import date

from fund_fetch import LATEST_DIR, ROUND2_ORDER, NetworkError, RateLimited, fetch, new_state, round2_params
from sec_client import DATA_DIR, SecClient, save_json, utf8_stdout

TYPES = ("RMF", "ThaiESG", "ThaiESGX")


def target_projects():
    rows = csv.DictReader(open(DATA_DIR / "fund_class_types.csv", encoding="utf-8-sig"))
    return sorted({r["proj_id"] for r in rows if r["tax_type"] in TYPES and r["fund_status"] in ("Registered", "IPO")})


def main():
    utf8_stdout()
    projs, today = target_projects(), date.today()
    only = sys.argv[1:]  # ระบุชื่อ endpoint เพื่อรันเฉพาะบางตัวได้
    order = [n for n in ROUND2_ORDER if not only or n in only]
    print(f"proj_id {len(projs)} | endpoint {order} | วันที่รัน {today}", flush=True)
    client, state, t0 = SecClient(), new_state(), time.time()
    status = "ok"
    try:
        for name in order:
            extra = round2_params(name, today)
            done0 = state["skipped"]
            for i, pj in enumerate(projs, 1):
                fetch(client, name, pj, state, max_pages=40, extra=extra, base=LATEST_DIR)
                if i % 50 == 0:
                    print(f"  {name} {i}/{len(projs)} calls={state['calls']} 429={state['n429']} t={time.time() - t0:.0f}s", flush=True)
            print(f"จบ {name}: calls สะสม {state['calls']} (ข้ามที่มีแล้ว {state['skipped'] - done0})", flush=True)
    except RateLimited as e:
        status = f"หยุดเพราะ 429 ซ้ำ: {e}"
        print(status, flush=True)
    except NetworkError as e:
        status = f"หยุดเพราะเครือข่ายผิดพลาดซ้ำ: {e}"
        print(status, flush=True)
    state["seconds"] = round(time.time() - t0)
    save_json(DATA_DIR / "round2_state.json", {"status": status, "state": state, "date": today.isoformat(), "n_proj": len(projs)})
    print(state, status, flush=True)
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
