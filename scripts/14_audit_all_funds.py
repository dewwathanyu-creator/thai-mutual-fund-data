"""ตรวจความถูกต้องของ data/all_funds.csv ด้วยวิธีอิสระจากตัวสร้างตาราง (08_build_funds_table.py)
1) คำนวณค่าสำคัญใหม่จากไฟล์ดิบ data/raw_latest/ ด้วยโค้ดแยกต่างหาก แล้วเทียบกับตารางทุกแถว (ไม่สุ่ม)
2) ตรวจความสมเหตุสมผล (กฎใน data_quality.py) และความขัดแย้งภายในข้อมูลดิบ
3) เทียบผลตอบแทน 1 ปีที่ ก.ล.ต. รายงานกับการคำนวณจาก NAV ของเราเอง
ผลลัพธ์: docs/data_audit_all_funds.md (ขึ้น GitHub) + data/all_funds_audit_flags.csv (ไม่ขึ้น GitHub)
ไม่เรียกเครือข่าย
"""
import csv
import json
import statistics
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from data_quality import FLAG_TEXT, row_flags
from sec_client import DATA_DIR, utf8_stdout

ROOT = Path(__file__).resolve().parent.parent
RAW = DATA_DIR / "raw_latest"
TOL = 1e-6


def num(v):
    if v is None or str(v).strip() in ("", "None", "null"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def raw_items(name, proj):
    p = RAW / name / f"{proj}.json"
    if not p.exists():
        return []
    d = json.loads(p.read_text(encoding="utf-8"))
    return d["items"] if d.get("status") == 200 else []


def latest(rows, key="start_date"):
    ds = [str(r.get(key)) for r in rows if str(r.get(key)) not in ("None", "")]
    if not ds:
        return rows
    m = max(ds)
    return [r for r in rows if str(r.get(key)) == m]


def expected_min_sub(x):
    """กฎเดียวกับที่ประกาศใน docs/data_dictionary.md เขียนแยกจากตัวสร้างตารางเพื่อตรวจ"""
    if x is None:
        return None
    unit = (x.get("minimum_sub_unit") or "").replace("ํา", "ำ").strip()
    if unit == "ไม่กำหนด":
        return 0.0
    cur = (x.get("minimum_sub_cur") or "").strip().upper()
    if (cur and cur != "THB") or unit not in ("", "-"):
        return None
    v = num(x.get("minimum_sub"))
    return None if v in (None, 0) else v


def same(a, b):
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(a - b) <= TOL


def main():
    utf8_stdout()
    rows = list(csv.DictReader(open(DATA_DIR / "all_funds.csv", encoding="utf-8-sig")))
    n = len(rows)
    mism, checked, examples = Counter(), Counter(), defaultdict(list)
    dup_conflicts = Counter()
    cache = {}

    def get(name, proj):
        k = (name, proj)
        if k not in cache:
            cache[k] = raw_items(name, proj)
        return cache[k]

    def cmp(field, row, expect, got):
        checked[field] += 1
        if not same(expect, got):
            mism[field] += 1
            if len(examples[field]) < 5:
                examples[field].append((row["proj_id"], row["fund_class_name"], expect, got))

    for r in rows:
        proj, cls = r["proj_id"], r["api_class_name"]
        # ระดับกอง: ความเสี่ยง
        rk = latest(get("risk_spectrum", proj))
        exp_risk = rk[0].get("risk_spectrum") if rk else None
        exp_risk = None if exp_risk in (None, "None", "") else exp_risk
        checked["risk_spectrum"] += 1
        if (r["risk_spectrum"] or None) != exp_risk:
            mism["risk_spectrum"] += 1
            if len(examples["risk_spectrum"]) < 5:
                examples["risk_spectrum"].append((proj, r["fund_class_name"], r["risk_spectrum"], exp_risk))
        if not cls:
            # class ที่ไม่มีข้อมูลระดับ class: ตารางต้องว่างทุกช่องระดับ class
            for c in ("fee_ter_actual", "ret_1y", "nav", "min_subscription"):
                checked["blank_when_no_class"] += 1
                if r[c] != "":
                    mism["blank_when_no_class"] += 1
            continue
        # ค่าธรรมเนียม
        fees = latest([x for x in get("fees", proj) if x.get("fund_class_name") == cls])
        by = {}
        for x in fees:
            by.setdefault(x["fee_type_desc"], []).append(x)
        for desc, lst in by.items():
            if len({(x.get("rate"), x.get("actual_value")) for x in lst}) > 1:
                dup_conflicts["fees"] += 1
        pick = lambda frag: next((v[0] for d, v in by.items() if frag in d), None)
        for frag, col in (("Total Fee and Expense", "fee_ter"), ("Management Fee", "fee_mgmt"), ("Front-end Fee", "fee_front")):
            x = pick(frag)
            cmp(col + "_max", r, num(r[col + "_max"]), num(x.get("rate")) if x else None)
            cmp(col + "_actual", r, num(r[col + "_actual"]), num(x.get("actual_value")) if x else None)
        # ผลตอบแทน
        perf = latest([x for x in get("performance", proj) if x.get("fund_class_name") == cls])
        for ptype, period, col in (("ผลตอบแทนกองทุนรวม", "1 year", "ret_1y"), ("ผลตอบแทนกองทุนรวม", "year to date", "ret_ytd"),
                                   ("ความผันผวนของกองทุนรวม", "1 year", "vol_1y"), ("ผลตอบแทนกองทุนรวม", "3 years", "ret_3y")):
            xs = [x for x in perf if x.get("performance_type_desc") == ptype and x.get("reference_period") == period]
            if len({x.get("performance_value") for x in xs}) > 1:
                dup_conflicts["performance"] += 1
            exp = num(xs[0].get("performance_value")) if xs else None
            if exp == 0 and r[col] == "" and ("perf_zero_blanked" in r["dq_flags"] or "perf_zero_vs_nav" in r["dq_flags"]):
                checked[col + "_zero_blanked_by_rule"] += 1  # 0.00 ที่ถูกแสดงเป็นว่างตามกฎและมีธงกำกับ
                continue
            cmp(col, r, num(r[col]), exp)
        # NAV
        navs = [x for x in get("nav", proj) if x.get("fund_class_name") == cls and str(x.get("nav_date")) not in ("None", "")]
        last = max(navs, key=lambda x: x["nav_date"]) if navs else None
        checked["nav_date"] += 1
        if (r["nav_date"] or None) != (last["nav_date"] if last else None):
            mism["nav_date"] += 1
            if len(examples["nav_date"]) < 5:
                examples["nav_date"].append((proj, r["fund_class_name"], r["nav_date"], last and last["nav_date"]))
        cmp("nav", r, num(r["nav"]), num(last.get("last_val")) if last else None)
        cmp("net_asset", r, num(r["net_asset"]), num(last.get("net_asset")) if last else None)
        # ขั้นต่ำ
        ms = latest([x for x in get("min_sub_red", proj) if x.get("fund_class_name") == cls])
        cmp("min_subscription", r, num(r["min_subscription"]), expected_min_sub(ms[0]) if ms else None)

    # ความสมเหตุสมผล
    ref_nav = max((r["nav_date"] for r in rows if r["nav_date"]), default="")
    flag_rows, fc, fex = [], Counter(), defaultdict(list)
    for r in rows:
        fl = [x for x in r["dq_flags"].split(";") if x]
        if not set(row_flags(r, ref_nav)) <= set(fl):  # ธงจากกฎพื้นฐานต้องอยู่ในคอลัมน์ dq_flags ครบ (ตรวจว่าตัวสร้างตารางไม่ทำธงหาย)
            mism["dq_flags_missing"] += 1
        checked["dq_flags_missing"] += 1
        for f in fl:
            fc[f] += 1
            if len(fex[f]) < 4:
                fex[f].append(f"{r['proj_abbr_name']}/{r['fund_class_name']}")
        if fl:
            flag_rows.append({"proj_id": r["proj_id"], "fund_class_name": r["fund_class_name"], "proj_abbr_name": r["proj_abbr_name"],
                              "flags": ";".join(fl), "fee_ter_actual": r["fee_ter_actual"], "fee_mgmt_actual": r["fee_mgmt_actual"],
                              "fee_ter_max": r["fee_ter_max"], "ret_1y": r["ret_1y"], "nav_change_1y_pct": r["nav_change_1y_pct"],
                              "nav_date": r["nav_date"]})
    with open(DATA_DIR / "all_funds_audit_flags.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(flag_rows[0]) if flag_rows else ["proj_id"])
        w.writeheader()
        w.writerows(flag_rows)

    # เทียบผลตอบแทนของ ก.ล.ต. (ต้นปี, 3 เดือน) กับการคำนวณจาก NAV ของเราเองที่วันเดียวกัน (perf_as_of)
    navs = defaultdict(list)
    for x in csv.DictReader(open(DATA_DIR / "all_nav_series.csv", encoding="utf-8-sig")):
        if x["nav"] not in ("", "None"):
            navs[(x["proj_id"], x["fund_class_name"])].append((x["nav_date"], float(x["nav"])))
    for v in navs.values():
        v.sort()

    def nav_on_or_before(series, d, max_gap):
        best = None
        for dt, v in series:
            if dt <= d:
                best = (dt, v)
            else:
                break
        if best and (date.fromisoformat(d) - date.fromisoformat(best[0])).days <= max_gap:
            return best[1]
        return None

    def minus_months(d, m):
        y, mo = d.year, d.month - m
        while mo <= 0:
            mo += 12
            y -= 1
        day = min(d.day, [31, 29 if y % 4 == 0 and (y % 100 or y % 400 == 0) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mo - 1])
        return date(y, mo, day)

    xcheck = {}
    for label, col in (("ต้นปี (YTD)", "ret_ytd"), ("3 เดือน", "ret_3m")):
        res = []
        for r in rows:
            if r[col] == "" or not r["perf_as_of"] or not r["api_class_name"]:
                continue
            ser = navs.get((r["proj_id"], r["fund_class_name"]))
            if not ser:
                continue
            asof = date.fromisoformat(r["perf_as_of"])
            base_d = date(asof.year - 1, 12, 31) if col == "ret_ytd" else minus_months(asof, 3)
            end_v, base_v = nav_on_or_before(ser, asof.isoformat(), 5), nav_on_or_before(ser, base_d.isoformat(), 7)
            if end_v is None or base_v in (None, 0):
                continue
            res.append((abs((end_v / base_v - 1) * 100 - float(r[col])), r, float(r[col]) - (end_v / base_v - 1) * 100))
        xcheck[label] = res

    # คอลัมน์ตรวจความครบ/ลำดับ
    keys = Counter((r["proj_id"], r["fund_class_name"]) for r in rows)
    dup_keys = sum(1 for v in keys.values() if v > 1)
    ter_ge = [r for r in rows if r["fee_ter_actual"] != "" and r["fee_mgmt_actual"] != ""]

    L = ["# รายงานตรวจความถูกต้องของตารางทุกกอง (`data/all_funds.csv`)", "",
         f"ตรวจเมื่อ {__import__('datetime').date.today().isoformat()} · สคริปต์ `scripts/14_audit_all_funds.py` (ไม่เรียกเครือข่าย อ่านจากไฟล์ดิบ)", "",
         f"ตาราง {n:,} class · วันที่ NAV ล่าสุดของทั้งตาราง {ref_nav}", "",
         "## 1) คำนวณใหม่จากไฟล์ดิบ (ทุกแถว ไม่สุ่ม) เทียบกับตาราง", "",
         "ใช้โค้ดแยกจากตัวสร้างตาราง ดึงค่าจาก `data/raw_latest/` โดยตรง แล้วเทียบ (ค่าเท่ากันภายใน 1e-6)", "",
         "| ช่อง | ตรวจ | ไม่ตรง |", "|---|---|---|"]
    for k in sorted(checked):
        L.append(f"| {k} | {checked[k]:,} | {mism[k]:,} |")
    L.append("")
    if any(mism.values()):
        L.append("**ตัวอย่างที่ไม่ตรง** (proj, class, ค่าในตาราง, ค่าที่คำนวณใหม่):")
        for k, ex in examples.items():
            L.append(f"- {k}: {ex}")
        L.append("")
    L += [f"- ความขัดแย้งภายในข้อมูลดิบ (หลายค่าในช่องเดียวกัน ช่วงวันที่เดียวกัน): ค่าธรรมเนียม {dup_conflicts['fees']} · ผลตอบแทน/ความผันผวน {dup_conflicts['performance']}",
          f"- คีย์ (proj_id, class) ซ้ำ: {dup_keys}", "",
          "## 2) ความสมเหตุสมผลของค่า (ธง `dq_flags`)", "",
          "| ธง | ความหมาย | จำนวนแถว | ตัวอย่าง |", "|---|---|---|---|"]
    for k, t in FLAG_TEXT.items():
        L.append(f"| `{k}` | {t} | {fc[k]:,} | {', '.join(fex[k]) or '-'} |")
    L += ["", f"แถวที่มีธงอย่างน้อย 1 ตัว: {len(flag_rows):,} จาก {n:,} (รายการเต็ม `data/all_funds_audit_flags.csv`)", "",
          "ธงเป็นการแจ้งเตือนว่า \"ควรตรวจกับเอกสารต้นทาง\" ไม่ใช่ข้อสรุปว่าผิด ตารางและหน้าเว็บแสดงค่าตามที่ ก.ล.ต. รายงาน ยกเว้นสามกรณีที่แก้ตามกฎใน docs/data_dictionary.md: ผลตอบแทนที่เป็น 0.00 แทนข้อมูลที่ไม่มี (แสดงเป็นว่าง), ลงทุนขั้นต่ำที่ไม่ใช่บาทชัดเจน (ว่างพร้อมหมายเหตุ) และระดับความเสี่ยง 8+", "",
          "## 3) เทียบผลตอบแทนของ ก.ล.ต. กับการคำนวณจาก NAV ของเราที่วันเดียวกัน", "",
          "ผลตอบแทนที่ ก.ล.ต. สูงกว่าการเปลี่ยนของ NAV เป็นเรื่องปกติของกองจ่ายปันผล (ผลตอบแทนรวมปันผล) ส่วนที่ ก.ล.ต. ต่ำกว่า NAV อธิบายด้วยปันผลไม่ได้ จึงติดธง `ret_below_nav`", "",
          "คำนวณ (NAV ณ วันที่ข้อมูลผลตอบแทน ÷ NAV วันฐาน − 1) แล้วเทียบกับค่าที่ ก.ล.ต. รายงาน เป็นการตรวจอิสระว่าข้อมูล NAV และผลตอบแทนสอดคล้องกัน (กองที่จ่ายปันผลจะต่างโดยธรรมชาติ เพราะผลตอบแทนของ ก.ล.ต. รวมปันผล)", "",
          "| ช่วง | เทียบได้ | ต่าง ≤ 0.1 จุด | ≤ 0.5 | ≤ 1 | ≤ 2 | > 2 | มัธยฐาน |", "|---|---|---|---|---|---|---|---|"]
    worst = []
    for label, res in xcheck.items():
        ds = [t[0] for t in res]
        if not ds:
            continue
        k = lambda t: sum(1 for x in ds if x <= t)
        L.append(f"| {label} | {len(ds):,} | {k(.1):,} ({k(.1) / len(ds):.0%}) | {k(.5):,} ({k(.5) / len(ds):.0%}) | {k(1):,} ({k(1) / len(ds):.0%}) | {k(2):,} ({k(2) / len(ds):.0%}) | {len(ds) - k(2):,} ({(len(ds) - k(2)) / len(ds):.0%}) | {statistics.median(ds):.2f} |")
        if label.startswith("ต้นปี"):
            worst = sorted(res, key=lambda t: -t[0])[:8]
        big = [t for t in res if t[0] > 2]
        hi = sum(1 for t in big if t[2] > 0)
        L.append(f"| ↳ {label}: ต่าง > 2 จุด แยกทิศทาง | {len(big):,} | ก.ล.ต. สูงกว่า NAV {hi:,} | ก.ล.ต. ต่ำกว่า NAV {len(big) - hi:,} | | | | |")
    L += ["", "**ตัวอย่างที่ต่างมากที่สุด (ต้นปี)** — ควรตรวจกับเอกสารต้นทาง/ดูว่าเป็นกองจ่ายปันผลหรือไม่: " + ", ".join(f"{r['proj_abbr_name']}/{r['fund_class_name']} (ต่าง {d_:.1f})" for d_, r, _ in worst), ""]
    L += ["## 4) ค่าธรรมเนียม", "",
          f"- มีทั้งค่าธรรมเนียมรวมและค่าจัดการ: {len(ter_ge):,} class · ค่ารวม < ค่าจัดการ: {fc['ter_lt_mgmt']:,}",
          "- ฟิลด์ `rate` = ตัวเลขสูงสุดที่แสดง, `actual_value` = อัตราที่เก็บจริง ตามชื่อฟิลด์ใน SEC API; อย่าถือว่าตัวเลขสูงสุดเป็นเพดานของค่าใช้จ่ายทุกชนิด",
          "- [Fact Sheet PRINCIPAL BARMF](https://www.principal.th/sites/default/files/fund-documents/Thailand%20Site/th_PRINCIPAL_BARMF_FFS.pdf) หน้า 1/4 ระบุค่าใช้จ่ายรวมเก็บจริง 2.5498% สูงกว่าตัวเลขสูงสุด 2.14% เพราะตัวเลขสูงสุดครอบคลุมเฉพาะค่าใช้จ่ายที่ประมาณการได้ ธง `fee_actual_gt_max` ของกองนี้จึงเป็นกรณีที่อธิบายได้ ไม่ใช่ข้อมูลผิด",
          "- [Fact Sheet ES-CHINAA-SSF](https://www.eastspring.co.th/THDocs/FS/31F_03.pdf) หน้า 2 ระบุค่าจัดการ 1.6050% และค่าใช้จ่ายรวม 1.0310% โดยค่ารวมเป็นรอบปีบัญชี 1 มี.ค. 2568–28 ก.พ. 2569 จึงอาจต่ำกว่าค่าจัดการปัจจุบันได้ ธง `ter_lt_mgmt` ควรตีความเป็นตัวเลขต่างช่วงเวลา ไม่ใช่ข้อผิดพลาดที่ยืนยันแล้ว",
          "- ธง `ret_below_nav` ยังต้องเทียบ Fact Sheet รายกอง จึงคงค่าตามต้นทางและเตือนในหน้าเว็บ; เมื่อค่ารวมต่ำกว่าค่าจัดการที่แสดง ระบบงดแสดงค่าธรรมเนียมประมาณการเป็นบาท", ""]
    (ROOT / "docs" / "data_audit_all_funds.md").write_text("\n".join(L), encoding="utf-8")
    print("\n".join(L))


if __name__ == "__main__":
    sys.exit(main())
