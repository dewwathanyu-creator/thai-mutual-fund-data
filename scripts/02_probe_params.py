"""ทดสอบว่ากรอง profiles ด้วย company_info หรือ amc_id ได้ (เอกสารสองหน้าใช้ชื่อไม่ตรงกัน)"""
import json

from sec_client import (DATA_DIR, SecClient, find_records, save_json,
                        utf8_stdout)

PROFILES = "/v2/fund/general-info/profiles"
AMCS = "/v2/fund/general-info/amcs"


def main():
    utf8_stdout()
    client = SecClient()

    amc_records, _, _ = client.get_all(AMCS)
    print(f"จำนวน บลจ.: {len(amc_records)}")
    if not amc_records:
        raise SystemExit("amcs ไม่มี record ให้ทดสอบต่อ")
    first = amc_records[0]
    print("ตัวอย่าง บลจ. แรก:", str(first)[:400])
    uid = first.get("unique_id")
    if not uid:
        raise SystemExit(f"ไม่พบ field unique_id ใน record แรก field ที่มี: {list(first.keys())}")

    full_path = DATA_DIR / "profiles_raw.json"
    if full_path.exists():
        total = len(find_records(json.loads(full_path.read_text(encoding="utf-8"))))
        print(f"ใช้จำนวน profiles ทั้งหมดจากไฟล์ที่ดึงไว้: {total}")
    else:
        full, _, _ = client.get_all(PROFILES)
        total = len(full)
        print(f"จำนวน profiles ทั้งหมด: {total}")

    results = {"unique_id_tested": uid, "total_profiles": total, "params": {}}
    for name in ("company_info", "amc_id"):
        try:
            items, pages, _ = client.get_all(PROFILES, params={name: uid})
            n = len(items)
            entry = {"status": 200, "records": n, "pages": pages,
                     "filters_effectively": 0 < n < total}
        except SystemExit:
            entry = {"status": "error", "note": "ดูข้อความ error ด้านบน (พารามิเตอร์นี้อาจไม่รองรับ)"}
        results["params"][name] = entry
        print(f"{name}: {entry}")

    save_json(DATA_DIR / "probe_params_result.json", results)
    print("\nอ่านผล: ตัวที่ filters_effectively = true คือชื่อพารามิเตอร์ที่ใช้ได้จริง"
          " (ถ้าจำนวนเท่ากับทั้งหมด แปลว่าระบบเมินพารามิเตอร์นั้น)")


if __name__ == "__main__":
    main()
