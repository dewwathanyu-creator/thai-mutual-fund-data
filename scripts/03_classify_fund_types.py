"""คัดประเภทกองลดหย่อนระดับ class จาก data/profiles_raw.json (ไม่เรียก API)
ผลลัพธ์: data/fund_class_types.csv + data/fund_class_types_report.txt
"""
import csv
import json
from collections import Counter

from fund_type_rules import classify, ESG_FAMILY
from sec_client import DATA_DIR, utf8_stdout

STATUS_GROUP = {"Registered": "จดทะเบียนอยู่ (Registered)", "IPO": "IPO (แยกบอก)"}
COLS = ["unique_id", "comp_name_th", "proj_id", "fund_class_name", "fund_class_isin_code",
        "proj_abbr_name", "proj_name_th", "fund_status", "availability", "tax_type",
        "classified_by", "confidence", "verified_status", "conflict", "ambiguous", "ltf_mention",
        "field_type_raw", "evidence", "last_upd_date"]


def write_spot_check(rows, seed=2569):
    """สุ่มตัวอย่าง 15 class (เมล็ดคงที่) ให้ผู้ใช้ตรวจมือ -> docs/classification_spot_check.md"""
    import random
    rng = random.Random(seed)
    reg = [r for r in rows if r["fund_status"] == "Registered"]
    plan = [("RMF", 5), ("ThaiESG", 3), ("ThaiESGX", 4), ("", 3)]
    lines = ["# ตรวจสุ่มการคัดประเภทกอง (กรอกมือ)", "",
             f"สุ่มด้วยเมล็ด `{seed}` จากกลุ่ม Registered เท่านั้น (สร้างโดย `scripts/03_classify_fund_types.py` ผลเดิมทุกครั้งถ้าข้อมูลไม่เปลี่ยน)",
             "วิธีตรวจ: เปิดเว็บ บลจ. หรือ factsheet ของกอง/class แล้วดูว่ากองนี้เป็นกองลดหย่อนประเภทที่ระบบคัดไว้จริงหรือไม่",
             "URL factsheet: profiles ไม่มี field URL (endpoint factsheet/urls ยังไม่ยืนยัน จะเติมในเฟส 3)", "",
             "| # | ระบบคัดว่า | confidence | classified_by | ชื่อกอง | ชื่อย่อ | class | proj_id | บลจ. | factsheet URL | ผลตรวจ (ตรงกัน/ไม่ตรง) | หมายเหตุ |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    n = 0
    for t, k in plan:
        pool = sorted([r for r in reg if r["tax_type"] == t], key=lambda r: (r["proj_id"], r["fund_class_name"]))
        for r in rng.sample(pool, k):
            n += 1
            lines.append(f"| {n} | {t or 'ไม่ได้คัด'} | {r['confidence'] or '-'} | {r['classified_by'] or '-'} | "
                         f"{r['proj_name_th']} | {r['proj_abbr_name']} | {r['fund_class_name']} | {r['proj_id']} | "
                         f"{r['comp_name_th']} | ยังไม่มีข้อมูล |  |  |")
    docs = DATA_DIR.parent / "docs"
    docs.mkdir(exist_ok=True)
    (docs / "classification_spot_check.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    utf8_stdout()
    items = json.loads((DATA_DIR / "profiles_raw.json").read_text(encoding="utf-8"))["items"]
    rows = []
    for r in items:
        c = classify(r)
        rows.append({
            "unique_id": r["unique_id"], "comp_name_th": r["comp_name_th"],
            "proj_id": r["proj_id"], "fund_class_name": r["fund_class_name"],
            "fund_class_isin_code": r["fund_class_isin_code"] or "",
            "proj_abbr_name": r["proj_abbr_name"], "proj_name_th": r["proj_name_th"],
            "fund_status": r["fund_status"],
            "availability": STATUS_GROUP.get(r["fund_status"], "ไม่ใช่กองที่จดทะเบียนอยู่ (" + r["fund_status"] + ")"),
            "field_type_raw": r["fund_class_tax_incentive_type"] or "", "verified_status": "unverified",
            "last_upd_date": r["last_upd_date"], **c})
    keys = [(r["proj_id"], r["fund_class_name"]) for r in rows]
    assert len(keys) == len(set(keys)), "proj_id+fund_class_name ซ้ำ"
    with open(DATA_DIR / "fund_class_types.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)

    typed = [r for r in rows if r["tax_type"]]
    out = []
    p = out.append
    p(f"class ทั้งหมด {len(rows)} | จัดประเภทได้ {len(typed)} | ไม่เข้าข่าย {len(rows) - len(typed)}")
    p("\n== จำนวนต่อประเภท x confidence (ทุกสถานะ) ==")
    for t, n in sorted(Counter(r["tax_type"] for r in typed).items()):
        cc = Counter(r["confidence"] for r in typed if r["tax_type"] == t)
        p(f"  {t}: {n} | high {cc['high']} medium {cc['medium']} low {cc['low']}")
    p("\n== ประเภท x fund_status ==")
    for t in sorted({r["tax_type"] for r in typed}):
        sc = Counter(r["fund_status"] for r in typed if r["tax_type"] == t)
        p(f"  {t}: " + ", ".join(f"{k} {v}" for k, v in sc.most_common()))
    p("\n== เฉพาะที่จดทะเบียนอยู่ (Registered) ประเภท x confidence ==")
    for t in sorted({r["tax_type"] for r in typed}):
        cc = Counter(r["confidence"] for r in typed if r["tax_type"] == t and r["fund_status"] == "Registered")
        p(f"  {t}: {sum(cc.values())} | high {cc['high']} medium {cc['medium']} low {cc['low']}")
    ipo = Counter(r["tax_type"] for r in typed if r["fund_status"] == "IPO")
    p(f"  IPO (แยก): {dict(ipo)}")

    p("\n== classified_by (ทุกสถานะ) ==")
    for k, n in Counter(r["classified_by"] for r in typed).most_common():
        p(f"  {k}: {n}")

    p("\n== field กับชื่อขัดกัน (conflict) ==")
    conf = [r for r in typed if r["conflict"]]
    p(f"  {len(conf)} class")
    for r in conf[:25]:
        p(f"  {r['proj_abbr_name']} | {r['fund_class_name']} | {r['fund_status']} | {r['conflict']}")

    p("\n== field ระบุประเภท แต่ชื่อไม่ยืนยัน ==")
    fo = [r for r in typed if r["classified_by"] == "field"]
    p(f"  {len(fo)} class")
    for r in fo[:15]:
        p(f"  {r['proj_abbr_name']} | {r['fund_class_name']} | {r['field_type_raw'][:30]}")

    p("\n== ชื่อกำกวม (RMF ตามด้วยตัวอักษร) ==")
    am = [r for r in rows if r["ambiguous"]]
    p(f"  {len(am)} class")
    for r in am[:15]:
        p(f"  {r['proj_abbr_name']} | {r['fund_class_name']} | {r['tax_type'] or '-'} | {r['ambiguous']}")

    p("\n== Thai ESG (ไม่ระบุ X) ที่แยกไม่ได้ ==")
    un = [r for r in typed if r["tax_type"] == "Thai ESG (ไม่ระบุ X)"]
    p(f"  {len(un)} class")
    for r in un[:15]:
        p(f"  {r['proj_abbr_name']} | {r['fund_class_name']} | {r['fund_status']}")

    p("\n== classified_by = description อย่างเดียว (low) ==")
    de = [r for r in typed if r["classified_by"] == "description"]
    p(f"  {len(de)} class")
    for r in de[:15]:
        p(f"  {r['proj_abbr_name']} | {r['fund_class_name']} | {r['tax_type']} | {r['evidence'][:80]}")

    write_spot_check(rows)
    text = "\n".join(out)
    (DATA_DIR / "fund_class_types_report.txt").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
