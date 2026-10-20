"""ดึง /v2/fund/general-info/profiles แบบไม่ใส่พารามิเตอร์ (กองทั้งตลาด)
บันทึกดิบลง data/ แล้วสรุปให้ดูว่ามี field อะไร, field ไหนบอกประเภทกอง, มี pagination ไหม
"""
from collections import Counter

from sec_client import (DATA_DIR, SecClient, find_records, response_meta,
                        save_json, utf8_stdout)

PATH = "/v2/fund/general-info/profiles"
KEYWORDS = ["thaiesgx", "thaiesg", "thai esg", "esgx", "rmf", "ltf", "ssf",
            "ลดหย่อน", "เพื่อการเลี้ยงชีพ", "ความยั่งยืน"]
PAGE_HINTS = ("page", "total", "count", "next", "cursor", "limit", "link", "size", "rate", "retry")


def summarize(data, meta=None):
    lines = []
    out = lines.append
    records = find_records(data)
    out(f"ชนิดข้อมูลชั้นนอก: {type(data).__name__}")
    if isinstance(data, dict):
        out("key ชั้นนอก: " + ", ".join(f"{k}({type(v).__name__})" for k, v in data.items()))
        scalars = {k: v for k, v in data.items() if not isinstance(v, (list, dict))}
        if scalars:
            out(f"ค่าชั้นนอกที่ไม่ใช่ list (อาจเป็นตัวบอกหน้า/จำนวนรวม): {scalars}")
    out(f"จำนวน record: {len(records)}")
    if len(records) in (10, 20, 25, 50, 100, 200, 500, 1000, 5000, 10000):
        out("!! จำนวนเป็นเลขกลม อาจถูกจำกัดต่อหน้า ให้เช็ค pagination")
    if not records:
        return "\n".join(lines)

    fields = Counter()
    for rec in records:
        if isinstance(rec, dict):
            fields.update(rec.keys())
    out("\nfield ที่พบ (จำนวน record ที่มี field นี้):")
    for k, n in fields.most_common():
        out(f"  {k}: {n}")

    out("\nตัวอย่าง 2 record แรก:")
    for rec in records[:2]:
        out(str(rec)[:1200])

    hits = Counter()
    sample_hits = {}
    for rec in records:
        if not isinstance(rec, dict):
            continue
        for k, v in rec.items():
            if isinstance(v, str):
                low = v.lower()
                for kw in KEYWORDS:
                    if kw in low:
                        hits[(k, kw)] += 1
                        sample_hits.setdefault((k, kw), v)
    out("\nคำที่เกี่ยวกับกองลดหย่อนที่พบ (field, คำ): จำนวน | ตัวอย่างค่า")
    if not hits:
        out("  ไม่พบเลย -> field ประเภทกองอาจไม่อยู่ใน profiles ให้ดู endpoint อื่น/ไฟล์รายงาน ก.ล.ต.")
    for (k, kw), n in hits.most_common(40):
        out(f"  ({k}, {kw}): {n} | {sample_hits[(k, kw)][:80]}")

    if meta:
        hh = {k: v for k, v in meta["headers"].items() if any(h in k.lower() for h in PAGE_HINTS)}
        out(f"\nheader ที่อาจเกี่ยวกับ pagination/rate limit: {hh or 'ไม่พบ'}")
    return "\n".join(lines)


def main():
    utf8_stdout()
    client = SecClient()
    items, pages, meta = client.get_all(PATH)
    print(f"ดึงครบ {pages} หน้า รวม {len(items)} รายการ")
    data = {"items": items, "pages_fetched": pages}
    save_json(DATA_DIR / "profiles_raw.json", data)
    save_json(DATA_DIR / "profiles_raw_meta.json", meta)
    text = summarize(data, meta)
    (DATA_DIR / "profiles_summary.txt").write_text(text, encoding="utf-8")
    print(text)
    print("\nบันทึกแล้ว: data/profiles_raw.json, data/profiles_raw_meta.json, data/profiles_summary.txt")


if __name__ == "__main__":
    main()
