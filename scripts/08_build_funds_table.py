"""สร้าง data/funds_table.csv (1 แถวต่อ class ที่คัดแล้ว Registered/IPO) จากข้อมูลดิบ data/raw_latest/
และ data/nav_series.csv (NAV ย้อนหลัง 1 ปี) + data/funds_table_quality.txt (รายงานคุณภาพข้อมูล)
ไม่เรียก API: อ่านจากไฟล์เท่านั้น; ค่าไม่ครบเป็นเซลล์ว่าง (ไม่ใช่ 0)
ดู docs/data_dictionary.md สำหรับที่มาของแต่ละคอลัมน์
"""
import csv
import json
import sys
from datetime import date
from collections import Counter, defaultdict
from pathlib import Path

from data_quality import fix_placeholder_zeros, fx_policy_label, min_sub_value, row_flags
from sec_client import DATA_DIR, utf8_stdout

TYPES = ("RMF", "ThaiESG", "ThaiESGX")
RAW = DATA_DIR / "raw_latest"
FEE_KEYS = {  # คำใน fee_type_desc -> ชื่อคอลัมน์
    "Management Fee": "mgmt", "Total Fee and Expense": "ter", "Front-end Fee": "front",
    "Back-end Fee": "back", "SWITCHING IN": "switch_in", "SWITCHING OUT": "switch_out", "Transfer Fee": "transfer",
}
PERF_TYPES = {"ผลตอบแทนกองทุนรวม": "ret", "ความผันผวนของกองทุนรวม": "vol", "ผลตอบแทนตัวชี้วัด": "bench_ret",
              "ความผันผวนของตัวชี้วัด": "bench_vol", "ค่าเฉลี่ยในกลุ่มเดียวกัน": "peer_ret"}
PERF_PERIODS = {"3 months": "3m", "6 months": "6m", "year to date": "ytd", "1 year": "1y", "3 years": "3y",
                "5 years": "5y", "10 years": "10y", "inception date": "inception"}
PERF_COLS = [f"{t}_{p}" for t in ("ret", "vol", "bench_ret", "peer_ret") for p in PERF_PERIODS.values()]
STAT_COLS = ["maximum_drawdown", "sharpe_ratio", "beta", "alpha", "tracking_error", "portfolio_turnover_ratio",
             "recovering_period", "yield_to_maturity", "fx_hedging"]
COLS = (["proj_id", "fund_class_name", "api_class_name", "class_match", "tax_type", "tax_type_confidence", "classified_by",
         "verified_status", "fund_status", "comp_name_th", "proj_name_th", "proj_abbr_name", "policy_desc", "invest_country_flag",
         "fund_class_isin_code", "risk_spectrum", "risk_level", "risk_label", "risk_spectrum_desc", "risk_as_of"]
        + [f"fee_{k}_{s}" for k in FEE_KEYS.values() for s in ("max", "actual")] + ["fees_as_of"]
        + PERF_COLS + ["perf_as_of"] + STAT_COLS + ["stats_as_of", "benchmark", "asset_allocation", "alloc_as_of",
         "top5_holdings", "top5_as_of", "nav", "nav_date", "net_asset", "nav_change_1y_pct", "min_subscription", "min_redemption",
         "min_as_of", "min_sub_note", "factsheet_pdf", "amc_factsheet_url", "data_as_of", "fetched_at", "dq_flags", "class_detail", "fx_policy", "master_fund", "master_country"])


def clean(v):
    return "" if v is None or str(v).strip() in ("", "None", "null") else v


def num(v):
    v = clean(v)
    try:
        return float(v) if v != "" else ""
    except ValueError:
        return ""


def load(name, proj):
    p = RAW / name / f"{proj}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    return d if d.get("status") == 200 else None


def latest_rows(rows):
    """เก็บเฉพาะแถวที่ start_date (หรือ as_of_date) ล่าสุด ต่อกลุ่มที่ส่งมา (กรณี API ไม่ได้กรองให้)"""
    key = "start_date" if rows and "start_date" in rows[0] else "as_of_date"
    best = max((str(clean(r.get(key))) for r in rows), default="")
    return [r for r in rows if str(clean(r.get(key))) == best], best


def risk_from_spectrum(rs):
    """RS1-RS8 -> ระดับ 1-8; RS81 และ RS8+ = ระดับ 8+ (ความเสี่ยงสูงกว่าระดับ 8 ตามนิยาม ก.ล.ต.) เก็บระดับเป็น 8 และป้ายเป็น "8+" """
    rs = str(rs or "")
    if rs in ("RS81", "RS8+"):
        return 8, "8+"
    if len(rs) == 3 and rs.startswith("RS") and rs[2] in "12345678":
        return int(rs[2]), rs[2]
    return "", ""


def match_class(row, api_names, n_typed):
    if not api_names:
        return "", "no_data"
    if row["fund_class_name"] in api_names:
        return row["fund_class_name"], "exact"
    if len(api_names) == 1:
        if row["fund_class_name"] == "main":
            return next(iter(api_names)), "single_class_main"
        if n_typed == 1:
            return next(iter(api_names)), "single_class_renamed"
    return "", "unmatched"


def money(rows, cls):
    return [r for r in rows if r.get("fund_class_name") == cls]


EXTRA_COLS_ALL = ["unique_id", "regis_date", "sec_tax_tag"]


def build(raw_base=None, scope="tax"):
    """scope="tax": เฉพาะ RMF/ThaiESG/ThaiESGX (funds_table.csv เดิม); scope="all": ทุก class ที่ Registered/IPO"""
    global RAW
    if raw_base:
        RAW = Path(raw_base)
    types = list(csv.DictReader(open(DATA_DIR / "fund_class_types.csv", encoding="utf-8-sig")))
    live = [r for r in types if r["fund_status"] in ("Registered", "IPO")]
    typed = live if scope == "all" else [r for r in live if r["tax_type"] in TYPES]
    profiles = {(p["proj_id"], p["fund_class_name"]): p
                for p in json.loads((DATA_DIR / "profiles_raw.json").read_text(encoding="utf-8"))["items"]}
    per_proj = defaultdict(list)
    for r in typed:
        per_proj[r["proj_id"]].append(r)

    out, nav_rows = [], []
    for proj, rows in sorted(per_proj.items()):
        d = {n: load(n, proj) for n in ("fees", "statistics", "risk_spectrum", "asset_allocation", "urls", "min_sub_red",
                                        "benchmarks", "performance", "top5", "nav")}
        items = {n: (v["items"] if v else []) for n, v in d.items()}
        api_names = {i["fund_class_name"] for n in ("fees", "performance", "statistics", "nav", "urls", "min_sub_red")
                     for i in items[n] if clean(i.get("fund_class_name")) != ""}
        fetched = max((v["fetched_at"] for v in d.values() if v), default="")
        risk, risk_asof = latest_rows(items["risk_spectrum"]) if items["risk_spectrum"] else ([], "")
        alloc, alloc_asof = latest_rows(items["asset_allocation"]) if items["asset_allocation"] else ([], "")
        top5, top5_asof = latest_rows(items["top5"]) if items["top5"] else ([], "")
        bench, _ = latest_rows(items["benchmarks"]) if items["benchmarks"] else ([], "")
        for r in rows:
            prof = profiles.get((r["proj_id"], r["fund_class_name"]), {})
            api_cls, how = match_class(r, api_names, len(rows))
            if scope == "all" and how == "unmatched" and not (api_names - {x["fund_class_name"] for x in rows}):
                how = "class_absent"  # endpoint ไม่มีข้อมูลของ class นี้เลย (ไม่ใช่ชื่อไม่ตรง) : ค่าระดับ class เว้นว่าง
            o = {c: "" for c in COLS + (EXTRA_COLS_ALL if scope == "all" else [])}
            extra_flags = []
            o.update({"proj_id": proj, "fund_class_name": r["fund_class_name"], "api_class_name": api_cls, "class_match": how,
                      "tax_type": r["tax_type"], "tax_type_confidence": r["confidence"], "classified_by": r["classified_by"],
                      "verified_status": r["verified_status"], "fund_status": r["fund_status"], "comp_name_th": r["comp_name_th"],
                      "proj_name_th": r["proj_name_th"], "proj_abbr_name": r["proj_abbr_name"],
                      "policy_desc": clean(prof.get("policy_desc")), "invest_country_flag": clean(prof.get("invest_country_flag")),
                      "fund_class_isin_code": r["fund_class_isin_code"], "fetched_at": fetched})
            o["class_detail"] = clean(prof.get("fund_class_detail")) or ""
            o["fx_policy"] = fx_policy_label(prof.get("exchange_rate_protection_policy"))
            o["master_fund"] = clean(prof.get("feederfund_master_fund")) or ""
            o["master_country"] = clean(prof.get("feederfund_country")) or ""
            if scope == "all":
                o.update({"unique_id": r["unique_id"], "regis_date": clean(prof.get("regis_date")),
                          "sec_tax_tag": clean(prof.get("fund_class_tax_incentive_type"))})
            # ระดับกอง (ไม่ขึ้นกับ class)
            if risk:
                o["risk_spectrum"] = clean(risk[0].get("risk_spectrum"))
                o["risk_level"], o["risk_label"] = risk_from_spectrum(o["risk_spectrum"])
                o["risk_spectrum_desc"] = clean(risk[0].get("risk_spectrum_desc"))
                o["risk_as_of"] = risk_asof
            if alloc:
                o["asset_allocation"] = "; ".join(f"{a['asset_name']} {a['asset_ratio']:.2f}%" for a in sorted(
                    alloc, key=lambda a: -(num(a.get("asset_ratio")) or 0)) if num(a.get("asset_ratio")) != "")
                o["alloc_as_of"] = alloc_asof
            if top5:
                o["top5_holdings"] = "; ".join(f"{a['asset_name']} {num(a.get('asset_ratio')):.2f}%" if num(a.get("asset_ratio")) != "" else a["asset_name"]
                                               for a in sorted(top5, key=lambda a: clean(a.get("asset_seq")) or 99))
                o["top5_as_of"] = top5_asof
            if bench:
                o["benchmark"] = "; ".join(sorted({b["benchmark"] for b in bench if clean(b.get("benchmark")) != ""}))
            # ระดับ class
            if api_cls:
                f, fa = latest_rows(money(items["fees"], api_cls)) if money(items["fees"], api_cls) else ([], "")
                for row in f:
                    for key, short in FEE_KEYS.items():
                        if key in row["fee_type_desc"]:
                            o[f"fee_{short}_max"], o[f"fee_{short}_actual"] = num(row.get("rate")), num(row.get("actual_value"))
                o["fees_as_of"] = fa if f else ""
                pr, pa = latest_rows(money(items["performance"], api_cls)) if money(items["performance"], api_cls) else ([], "")
                for row in pr:
                    t, p = PERF_TYPES.get(row["performance_type_desc"]), PERF_PERIODS.get(row["reference_period"])
                    if t and p and f"{t}_{p}" in o:
                        o[f"{t}_{p}"] = num(row.get("performance_value"))
                o["perf_as_of"] = pa if pr else ""
                st, sa = latest_rows(money(items["statistics"], api_cls)) if money(items["statistics"], api_cls) else ([], "")
                if st:
                    for c in STAT_COLS:
                        o[c] = num(st[0].get(c)) if c != "recovering_period" and c != "fx_hedging" else clean(st[0].get(c))
                    o["stats_as_of"] = sa
                mn, ma = latest_rows(money(items["min_sub_red"], api_cls)) if money(items["min_sub_red"], api_cls) else ([], "")
                if mn:
                    o["min_subscription"], o["min_sub_note"] = min_sub_value(mn[0])
                    o["min_redemption"], o["min_as_of"] = num(mn[0].get("minimum_redempt")), ma
                    if o["min_sub_note"] and o["min_subscription"] == "":
                        extra_flags.append("min_sub_unclear")
                u = money(items["urls"], api_cls)
                if u:
                    o["factsheet_pdf"], o["amc_factsheet_url"] = clean(u[0].get("pdf_factsheet")), clean(u[0].get("amc_url_factsheet"))
                navs = sorted((n for n in money(items["nav"], api_cls) if clean(n.get("nav_date")) != ""), key=lambda n: n["nav_date"])
                if navs:
                    last = navs[-1]
                    o["nav"], o["nav_date"], o["net_asset"] = num(last.get("last_val")), last["nav_date"], num(last.get("net_asset"))
                    first = navs[0]
                    days = (date.fromisoformat(last["nav_date"]) - date.fromisoformat(first["nav_date"])).days
                    fv, lv = num(first.get("last_val")), num(last.get("last_val"))
                    if days >= 330 and fv not in ("", 0) and lv != "":  # ช่วง NAV ครอบคลุม ~1 ปีเท่านั้น (กองอายุน้อยกว่าเว้นว่าง)
                        o["nav_change_1y_pct"] = round((lv / fv - 1) * 100, 2)
                    for n in navs:
                        nav_rows.append({"proj_id": proj, "fund_class_name": r["fund_class_name"], "nav_date": n["nav_date"],
                                         "nav": num(n.get("last_val"))})
            if api_cls:
                extra_flags += fix_placeholder_zeros(o, prof.get("regis_date"), [(n["nav_date"], num(n.get("last_val"))) for n in sorted(
                    (n for n in money(items["nav"], api_cls) if clean(n.get("nav_date")) != "" and num(n.get("last_val")) != ""), key=lambda n: n["nav_date"])])
            o["dq_flags"] = ";".join(sorted(set(extra_flags)))
            o["data_as_of"] = o["nav_date"] or max((o[k] for k in ("fees_as_of", "perf_as_of", "risk_as_of", "stats_as_of")), default="")
            out.append(o)
    ref_nav = max((o["nav_date"] for o in out if o["nav_date"]), default="")
    for o in out:
        o["dq_flags"] = ";".join(sorted({x for x in o["dq_flags"].split(";") if x} | set(row_flags(o, ref_nav))))
    return out, nav_rows


def quality_report(rows):
    n = len(rows)
    L = [f"funds_table: {n} class จาก {len({r['proj_id'] for r in rows})} proj_id", ""]
    L.append("จับคู่ class กับ endpoint: " + ", ".join(f"{k} {v}" for k, v in Counter(r["class_match"] for r in rows).most_common()))
    L.append("ประเภท: " + ", ".join(f"{k} {v}" for k, v in Counter(r["tax_type"] for r in rows).most_common()))
    L.append("")
    L.append("ค่าว่างต่อคอลัมน์ (จำนวนแถวที่ว่าง / %):")
    key_cols = ["risk_spectrum", "fee_mgmt_actual", "fee_ter_actual", "fee_front_max", "ret_1y", "ret_ytd", "ret_inception", "vol_1y",
                "maximum_drawdown", "sharpe_ratio", "asset_allocation", "top5_holdings", "nav", "min_subscription", "factsheet_pdf",
                "policy_desc", "benchmark"]
    for c in key_cols:
        e = sum(1 for r in rows if r[c] == "")
        L.append(f"  {c}: {e} ({e / n:.0%})")
    L.append("")
    stale = Counter((r["data_as_of"] or "ไม่มี")[:7] for r in rows)
    L.append("data_as_of (เดือน): " + ", ".join(f"{k} {v}" for k, v in sorted(stale.items())))
    nonav = [r for r in rows if r["nav_date"] == ""]
    L.append(f"ไม่มี NAV: {len(nonav)} class")
    old = [r for r in rows if r["nav_date"] and r["nav_date"] < "2026-09-01"]
    L.append(f"NAV เก่ากว่า 1 ก.ย. 2569: {len(old)} class (ตัวอย่าง: " + ", ".join(f"{r['proj_abbr_name']}/{r['fund_class_name']}={r['nav_date']}" for r in old[:5]) + ")")
    um = [r for r in rows if r["class_match"] == "unmatched"]
    L.append(f"จับคู่ class ไม่ได้ (ข้อมูลระดับ class ว่าง): {len(um)} class (ตัวอย่าง: " + ", ".join(f"{r['proj_abbr_name']}/{r['fund_class_name']}" for r in um[:5]) + ")")
    L.append("ไม่มีข้อมูลเลยทั้งแถว (ไม่มี risk/fee/nav): " + str(sum(1 for r in rows if r["risk_spectrum"] == "" and r["fee_ter_actual"] == "" and r["nav"] == "")))
    return "\n".join(L)


def main():
    """python 08_build_funds_table.py [raw_dir] [--all]   --all = ทุกกอง -> all_funds.csv / all_nav_series.csv (ไม่แตะ funds_table.csv)"""
    utf8_stdout()
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    scope = "all" if "--all" in sys.argv else "tax"
    names = {"tax": ("funds_table.csv", "nav_series.csv", "funds_table_quality.txt"),
             "all": ("all_funds.csv", "all_nav_series.csv", "all_funds_quality.txt")}[scope]
    rows, nav_rows = build(args[0] if args else None, scope)
    with open(DATA_DIR / names[0], "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS + (EXTRA_COLS_ALL if scope == "all" else []))
        w.writeheader()
        w.writerows(rows)
    with open(DATA_DIR / names[1], "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["proj_id", "fund_class_name", "nav_date", "nav"])
        w.writeheader()
        w.writerows(nav_rows)
    rep = quality_report(rows)
    (DATA_DIR / names[2]).write_text(rep, encoding="utf-8")
    print(rep)


if __name__ == "__main__":
    main()
