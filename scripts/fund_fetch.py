"""ดึงข้อมูลกองต่อ (endpoint, proj_id) แบบมี checkpoint: มีไฟล์ครบแล้วไม่เรียกซ้ำ, หยุดทันทีเมื่อ 429 ซ้ำ
บันทึกดิบที่ data/raw/<endpoint>/<proj_id>.json  (ไม่แตะ .env และไม่พิมพ์ key)
"""
import time
from datetime import datetime, timezone

from sec_client import DATA_DIR, find_records, save_json
import json
import requests

RAW_DIR = DATA_DIR / "raw"          # รอบนำร่อง: ประวัติเต็ม
LATEST_DIR = DATA_DIR / "raw_latest"  # รอบเต็ม: เฉพาะค่าล่าสุด (latest=true) + NAV ย้อนหลัง 1 ปี

# พารามิเตอร์กรองที่ยืนยันจากหน้าเอกสาร ก.ล.ต. + ทดสอบจริง 2569-10-08
# performance/fees/statistics/risk-spectrum/asset-allocation/top5/benchmarks/min-sub รับ latest=true
# nav ใช้ start_nav_date/end_nav_date (ไม่รับ latest) ; urls ไม่รับ latest (มีหน้าเดียวอยู่แล้ว) ; dividend: นำร่อง 204 ทั้งหมด จึงข้าม
LATEST_ENDPOINTS = ("performance", "fees", "statistics", "risk_spectrum", "asset_allocation", "top5", "benchmarks", "min_sub_red")
ROUND2_ORDER = ("fees", "statistics", "risk_spectrum", "asset_allocation", "urls", "min_sub_red", "benchmarks", "performance", "top5", "nav")


def round2_params(name, today):
    """พารามิเตอร์เพิ่มของรอบเต็ม; today = date ของวันรัน"""
    if name in LATEST_ENDPOINTS:
        return {"latest": "true"}
    if name == "nav":
        return {"start_nav_date": today.replace(year=today.year - 1).isoformat()}
    return {}

# endpoint ที่ยืนยันแล้วว่ามีจริงและกรองด้วย proj_id ได้ (ทดสอบ 2569-10-08 ดู data/probe_endpoints_result.json)
ENDPOINTS = {
    "nav": "/v2/fund/daily-info/nav",
    "dividend": "/v2/fund/daily-info/dividend-history",
    "fees": "/v2/fund/factsheet/fees",
    "performance": "/v2/fund/factsheet/performance",
    "statistics": "/v2/fund/factsheet/statistics",
    "benchmarks": "/v2/fund/factsheet/benchmarks",
    "asset_allocation": "/v2/fund/factsheet/asset-allocation",
    "risk_spectrum": "/v2/fund/factsheet/risk-spectrum",
    "top5": "/v2/fund/factsheet/top5-holdings",
    "urls": "/v2/fund/factsheet/urls",
    "min_sub_red": "/v2/fund/factsheet/subscription-redemption-minimums",
}


class RateLimited(Exception):
    pass


class NetworkError(Exception):
    pass


def raw_path(name, proj_id, base=None):
    return (base or RAW_DIR) / name / f"{proj_id}.json"


def is_done(name, proj_id, base=None):
    p = raw_path(name, proj_id, base)
    if not p.exists():
        return False
    try:
        return bool(json.loads(p.read_text(encoding="utf-8")).get("complete"))
    except ValueError:
        return False


def _get(client, path, params, state):
    """ลองใหม่เมื่อเครือข่ายสะดุด; 429 ซ้ำต้องหยุดโดยไม่ให้ client retry เพิ่ม"""
    network_failures = 0
    rate_failures = 0
    while True:
        state["calls"] += 1
        try:
            r = client.get(path, params, retries=0, raise_network=True)
        except requests.RequestException as exc:
            network_failures += 1
            if network_failures >= 3:
                raise NetworkError(f"{path}: {type(exc).__name__} ติดต่อกัน {network_failures} ครั้ง") from exc
            time.sleep(max(client.delay, 2 ** network_failures))
            continue
        if r.status_code != 429:
            state["consecutive_429"] = 0
            return r
        state["n429"] += 1
        rate_failures += 1
        state["consecutive_429"] = rate_failures
        if rate_failures >= 2:
            raise RateLimited(f"429 ซ้ำที่ {path}")
        wait = min(float(r.headers.get("Retry-After", 5)), 60)
        time.sleep(wait)


def fetch(client, name, proj_id, state, max_pages=60, force=False, extra=None, base=None):
    """ดึงทุกหน้าของ endpoint สำหรับ proj_id; คืน dict ที่บันทึก"""
    if not force and is_done(name, proj_id, base):
        state["skipped"] += 1
        return None
    path = ENDPOINTS[name]
    items, cursor, pages, status = [], "", 0, None
    while True:
        q = {"proj_id": proj_id, "page_size": 100, **(extra or {})}
        if cursor:
            q["next_cursor"] = cursor
        r = _get(client, path, q, state)
        status = r.status_code
        if status == 204:
            break
        if status != 200:
            rec = {"endpoint": path, "proj_id": proj_id, "status": status, "complete": True, "error": client._mask(r.text[:200]),
                   "fetched_at": datetime.now(timezone.utc).isoformat(), "items": []}
            save_json(raw_path(name, proj_id, base), rec)
            return rec
        data = r.json()
        items.extend(find_records(data))
        pages += 1
        cursor = data.get("next_cursor", "") if isinstance(data, dict) else ""
        if not cursor:
            break
        if pages >= max_pages:
            break
    rec = {"endpoint": path, "proj_id": proj_id, "params": extra or {}, "status": status, "pages": pages,
           "complete": not cursor, "n_items": len(items),
           "fetched_at": datetime.now(timezone.utc).isoformat(), "items": items}
    save_json(raw_path(name, proj_id, base), rec)
    return rec


def new_state():
    return {"calls": 0, "n429": 0, "consecutive_429": 0, "skipped": 0}
