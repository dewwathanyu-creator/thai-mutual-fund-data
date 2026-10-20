"""รอบ 1 ขั้น A: ลอง endpoint ที่คาดว่ามี (ยังไม่ยืนยัน) ทีละตัวด้วยกองตัวอย่าง 1 class
เรียกแต่ละ endpoint ครั้งเดียว (ไม่เดาชื่อเพิ่ม) บันทึกดิบใน data/probe/ สรุปผลที่ data/probe_endpoints_result.json
หยุดทันทีถ้าได้ 429 สองครั้ง
"""
import csv
import json
import random
import sys

from sec_client import DATA_DIR, SecClient, find_records, save_json, utf8_stdout

CANDIDATES = [
    "/v2/fund/daily-info/nav",
    "/v2/fund/daily-info/dividend-history",
    "/v2/fund/factsheet/fees",
    "/v2/fund/factsheet/performance",
    "/v2/fund/factsheet/statistics",
    "/v2/fund/factsheet/benchmarks",
    "/v2/fund/factsheet/asset-allocation",
    "/v2/fund/factsheet/risk-spectrum",
    "/v2/fund/factsheet/top5-holdings",
    "/v2/fund/factsheet/urls",
    "/v2/fund/factsheet/subscription-redemption-minimums",
]


def pick_sample():
    rows = list(csv.DictReader(open(DATA_DIR / "fund_class_types.csv", encoding="utf-8-sig")))
    pool = sorted([r for r in rows if r["tax_type"] == "ThaiESG" and r["fund_status"] == "Registered"
                   and r["fund_class_name"] != "main"], key=lambda r: (r["proj_id"], r["fund_class_name"]))
    return random.Random(2569).choice(pool)


def main():
    utf8_stdout()
    s = pick_sample()
    print(f"ตัวอย่าง: {s['proj_abbr_name']} | {s['proj_id']} | class {s['fund_class_name']}")
    client = SecClient()
    out, n429 = {"sample": {k: s[k] for k in ("proj_id", "fund_class_name", "proj_abbr_name")}, "results": {}}, 0
    (DATA_DIR / "probe").mkdir(exist_ok=True)
    for path in CANDIDATES:
        r = client.get(path, {"proj_id": s["proj_id"]}, retries=0)
        info = {"status": r.status_code, "bytes": len(r.content)}
        if r.status_code == 429:
            n429 += 1
            info["note"] = "429"
            out["results"][path] = info
            if n429 >= 2:
                print("429 ซ้ำ หยุด")
                break
            continue
        try:
            data = r.json()
        except ValueError:
            data = None
            info["text"] = client._mask(r.text[:200])
        if data is not None:
            save_json(DATA_DIR / "probe" / (path.strip("/").replace("/", "__") + ".json"), data)
            recs = find_records(data)
            info["top_keys"] = list(data.keys()) if isinstance(data, dict) else type(data).__name__
            info["message"] = data.get("message") if isinstance(data, dict) else None
            info["n_items"] = len(recs)
            if recs and isinstance(recs[0], dict):
                info["item_fields"] = list(recs[0].keys())
        out["results"][path] = info
        print(path, info["status"], info.get("n_items"), (info.get("message") or "")[:80])
    save_json(DATA_DIR / "probe_endpoints_result.json", out)


if __name__ == "__main__":
    main()
