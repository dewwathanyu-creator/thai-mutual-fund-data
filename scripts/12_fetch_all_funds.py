"""ดึงข้อมูลกองทุนที่ยังไม่เลิก (Registered/IPO) ทุกกองจาก profiles_raw.json (ไม่จำกัดเฉพาะกองลดหย่อนภาษี)
ใช้ตัวดึงเดิม (fund_fetch.fetch) และโฟลเดอร์เดียวกับรอบ 2 (data/raw_latest/) จึงข้ามกองที่ดึงครบแล้วโดยอัตโนมัติ
รันซ้ำได้ (resume): ไฟล์ที่ complete แล้วไม่เรียกซ้ำ; 429 ซ้ำ = หยุดทันที; เครือข่ายสะดุดเป็นรายโครงการ = ข้ามไปทำต่อ

ตัวอย่าง:
  python scripts/12_fetch_all_funds.py --dry                    # นับงาน ไม่เรียกเครือข่าย
  python scripts/12_fetch_all_funds.py --limit 2 --only fees    # ทดสอบเล็ก
  python scripts/12_fetch_all_funds.py --amc C0000000569        # เฉพาะ บลจ. เดียว
  python scripts/12_fetch_all_funds.py                          # ทั้งหมด (หลายชั่วโมง)
  python scripts/12_fetch_all_funds.py --nav-days 7 --only nav  # อัปเดต NAV เฉพาะช่วงสั้น (ใช้ทำรอบรายวัน)
ข้อมูลที่ได้เป็นไฟล์ดิบต่อ (endpoint, proj_id) ขั้นสร้างตารางรวมอยู่ในงานขั้นถัดไป
"""
import argparse
import json
import sys
import time
from datetime import date, timedelta

from fund_fetch import (LATEST_DIR, ROUND2_ORDER, ENDPOINTS, NetworkError, RateLimited, fetch, is_done, new_state,
                        round2_params)
from sec_client import DATA_DIR, SecClient, save_json, utf8_stdout

LIVE = ("Registered", "IPO")
MAX_CONSECUTIVE_NET_FAIL = 8
# คำขอเฉลี่ยต่อโครงการเมื่อใช้ latest=true / NAV 1 ปี (ประมาณการ ใช้ประเมินเวลาเท่านั้น)
EST_CALLS = {"fees": 1, "statistics": 1, "risk_spectrum": 1, "asset_allocation": 1, "urls": 1, "min_sub_red": 1,
             "benchmarks": 1, "performance": 1, "top5": 1, "nav": 5}
SEC_PER_CALL = 0.7  # รอบ 2: 4,372 คำขอ / 2,759 วินาที = 0.63


def target_projects(amc=None):
    raw = json.load(open(DATA_DIR / "profiles_raw.json", encoding="utf-8"))
    rows = raw if isinstance(raw, list) else next(v for v in raw.values() if isinstance(v, list))
    projs = {r["proj_id"] for r in rows if r.get("fund_status") in LIVE and (not amc or r.get("unique_id") == amc)}
    return sorted(projs)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="นับงานที่เหลือ ไม่เรียกเครือข่าย")
    ap.add_argument("--limit", type=int, help="จำกัดจำนวนโครงการ (ทดสอบ)")
    ap.add_argument("--only", nargs="*", help="เฉพาะ endpoint ที่ระบุ: " + ", ".join(ROUND2_ORDER))
    ap.add_argument("--amc", help="เฉพาะ บลจ. (unique_id เช่น C0000000569)")
    ap.add_argument("--nav-days", type=int, default=365, help="NAV ย้อนหลังกี่วัน (ค่าเริ่มต้น 365)")
    ap.add_argument("--refresh", action="store_true", help="ดึงใหม่แม้มีไฟล์ complete แล้ว (ใช้ตอนอัปเดตรอบสัปดาห์/วัน)")
    a = ap.parse_args()
    utf8_stdout()

    projs = target_projects(a.amc)
    if a.limit:
        projs = projs[:a.limit]
    order = [n for n in ROUND2_ORDER if not a.only or n in a.only]
    bad = [n for n in (a.only or []) if n not in ENDPOINTS]
    if bad:
        print("ไม่รู้จัก endpoint:", bad)
        return 2
    today = date.today()

    def extra_for(name):
        p = round2_params(name, today)
        if name == "nav":
            p = {"start_nav_date": (today - timedelta(days=a.nav_days)).isoformat()}
        return p

    # นับงานที่เหลือ
    todo = {n: [p for p in projs if a.refresh or not is_done(n, p, LATEST_DIR)] for n in order}
    est_calls = sum(len(v) * EST_CALLS.get(n, 2) for n, v in todo.items())
    print(f"โครงการเป้าหมาย {len(projs)} | วันที่รัน {today}")
    for n in order:
        print(f"  {n:<17} เหลือ {len(todo[n]):>5} โครงการ")
    print(f"ประเมิน ~{est_calls:,} คำขอ ≈ {est_calls * SEC_PER_CALL / 3600:.1f} ชั่วโมง (ประมาณการจากรอบ 2)")
    if a.dry:
        return 0

    client, state, t0 = SecClient(), new_state(), time.time()
    failed, status, consecutive_fail = [], "ok", 0
    try:
        for name in order:
            extra, pend = extra_for(name), todo[name]
            for i, pj in enumerate(pend, 1):
                try:
                    fetch(client, name, pj, state, max_pages=40, extra=extra, base=LATEST_DIR, force=a.refresh)
                    consecutive_fail = 0
                except NetworkError as e:
                    consecutive_fail += 1
                    failed.append({"endpoint": name, "proj_id": pj, "error": str(e)[:200]})
                    print(f"  ข้าม {name} {pj}: {str(e)[:100]}", flush=True)
                    if consecutive_fail >= MAX_CONSECUTIVE_NET_FAIL:
                        raise
                    time.sleep(10)
                if i % 100 == 0:
                    el = time.time() - t0
                    print(f"  {name} {i}/{len(pend)} calls={state['calls']} 429={state['n429']} t={el:.0f}s", flush=True)
            print(f"จบ {name}: calls สะสม {state['calls']}", flush=True)
    except RateLimited as e:
        status = f"หยุดเพราะ 429 ซ้ำ: {e}"
    except NetworkError as e:
        status = f"หยุดเพราะเครือข่ายผิดพลาดติดกัน {consecutive_fail} ครั้ง: {e}"
    except KeyboardInterrupt:
        status = "ผู้ใช้หยุดเอง (รันซ้ำเพื่อทำต่อ)"
    state["seconds"] = round(time.time() - t0)
    save_json(DATA_DIR / "fetch_all_state.json",
              {"status": status, "state": state, "date": today.isoformat(), "n_proj": len(projs), "failed": failed})
    print(status, state, f"ล้มเหลวรายโครงการ {len(failed)}", flush=True)
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    sys.exit(main())
