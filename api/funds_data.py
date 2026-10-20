"""อ่านตารางกองทุนจากไฟล์ใน data/ (ไม่เรียก SEC API ไม่รู้จัก .env)"""
import csv
from collections import defaultdict
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

TEXT_COLS = {"proj_id", "fund_class_name", "api_class_name", "class_match", "tax_type", "tax_type_confidence", "classified_by",
             "verified_status", "fund_status", "comp_name_th", "proj_name_th", "proj_abbr_name", "policy_desc", "invest_country_flag",
             "fund_class_isin_code", "risk_spectrum", "risk_spectrum_desc", "risk_as_of", "fees_as_of", "perf_as_of", "stats_as_of",
             "benchmark", "asset_allocation", "alloc_as_of", "top5_holdings", "top5_as_of", "nav_date", "min_as_of", "factsheet_pdf",
             "amc_factsheet_url", "data_as_of", "fetched_at", "recovering_period", "fx_hedging", "unique_id", "regis_date",
             "sec_tax_tag", "risk_label", "dq_flags", "min_sub_note", "class_detail", "fx_policy", "master_fund", "master_country"}

# คอลัมน์ในรายการ /api/funds (ตาราง ตัวกรอง เปรียบเทียบ ส่งออก CSV) ส่วนที่เหลือโหลดเมื่อเปิดรายละเอียด (/api/funds/{proj_id})
LIST_COLS = ["proj_id", "fund_class_name", "tax_type", "tax_type_confidence", "classified_by", "verified_status", "fund_status",
             "comp_name_th", "proj_name_th", "proj_abbr_name", "policy_desc", "risk_level", "fee_mgmt_actual", "fee_ter_actual",
             "fee_front_max", "ret_ytd", "ret_1y", "ret_3y", "vol_1y", "maximum_drawdown", "sharpe_ratio", "nav", "nav_date",
             "min_subscription", "data_as_of", "sec_tax_tag", "risk_label", "dq_flags", "class_detail", "net_asset", "fx_policy", "master_fund"]
TAX_TYPES = ("RMF", "SSF", "ThaiESG", "ThaiESGX")


def _val(col, v):
    if v is None or v == "":
        return None
    if col in TEXT_COLS:
        return v
    try:
        f = float(v)
    except ValueError:
        return v
    return int(f) if col == "risk_level" else f


def _table_path():
    """ใช้ตารางทุกกอง (all_funds.csv) ถ้ามี ไม่งั้นใช้ตารางกองลดหย่อนเดิม (funds_table.csv)"""
    for name in ("all_funds.csv", "funds_table.csv"):
        if (DATA_DIR / name).exists():
            return DATA_DIR / name
    return None


def _nav_path():
    return DATA_DIR / ("all_nav_series.csv" if _table_path() and _table_path().name == "all_funds.csv" else "nav_series.csv")


def is_sure_type(row):
    """ประเภทกองทุนลดหย่อนภาษีที่ "แน่ใจ": ก.ล.ต. ระบุในข้อมูลเอง (ความเชื่อมั่นสูง) หรือตรวจกับรายงาน/เอกสารทางการแล้ว (verified_status ขึ้นต้นด้วย sec_)
    ประเภทที่จัดจากชื่อกองทุนอย่างเดียวและยังไม่ตรวจยืนยันจะไม่แสดงเป็นป้ายหรือตัวกรอง"""
    return bool(row.get("tax_type")) and (row.get("tax_type_confidence") == "high" or str(row.get("verified_status") or "").startswith("sec_"))


@lru_cache(maxsize=1)
def load_funds():
    path = _table_path()
    if path is None:
        return []
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = [{c: _val(c, v) for c, v in row.items()} for row in csv.DictReader(f)]
    for r in rows:
        if r.get("tax_type") and not is_sure_type(r):
            r["tax_type"] = None  # ไม่ส่งค่าที่ยังไม่แน่ใจออกไปทาง API
    return rows


@lru_cache(maxsize=1)
def _nav_index():
    path = _nav_path()
    idx = defaultdict(list)
    if path.exists():
        with open(path, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                try:
                    idx[(r["proj_id"], r["fund_class_name"])].append((r["nav_date"], float(r["nav"])))
                except (ValueError, KeyError):
                    continue
    for k in idx:
        idx[k].sort()
    return idx


@lru_cache(maxsize=1)
def load_list():
    return [{c: r.get(c) for c in LIST_COLS} for r in load_funds()]


def nav_series(proj_id, fund_class_name):
    return [{"date": d, "nav": v} for d, v in _nav_index().get((proj_id, fund_class_name), [])]


def summary():
    rows = load_funds()
    dates = sorted(r["data_as_of"] for r in rows if r.get("data_as_of"))
    return {"n_classes": len(rows), "n_funds": len({r["proj_id"] for r in rows}),
            "n_amc": len({r["comp_name_th"] for r in rows}),
            "by_type": {t: sum(1 for r in rows if r["tax_type"] == t) for t in TAX_TYPES},
            "data_as_of_latest": dates[-1] if dates else None, "data_as_of_oldest": dates[0] if dates else None}
