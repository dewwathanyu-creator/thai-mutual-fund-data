"""เทสต์ API ด้วย TestClient (ไม่ต้องเปิดเซิร์ฟเวอร์ ไม่เรียกเครือข่าย)"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import csv  # noqa: E402
import shutil  # noqa: E402
import tempfile  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from api import funds_data  # noqa: E402
from api.main import app  # noqa: E402

c = TestClient(app)

# ข้อมูลจำลองขนาดเล็ก: เทสต์ไม่ต้องพึ่งไฟล์จริงใน data/ (ซึ่งไม่ขึ้น GitHub) จึงรันผ่านได้บนเครื่องที่เพิ่ง clone
_COLS = ["proj_id", "fund_class_name", "tax_type", "tax_type_confidence", "classified_by", "verified_status", "fund_status",
         "comp_name_th", "proj_name_th", "proj_abbr_name", "policy_desc", "risk_level", "fee_ter_actual", "sharpe_ratio",
         "nav", "nav_date", "data_as_of", "min_subscription"]
_ROWS = [
    {"proj_id": "M0001_2560", "fund_class_name": "main", "tax_type": "RMF", "tax_type_confidence": "medium", "classified_by": "name",
     "verified_status": "unverified", "fund_status": "Registered", "comp_name_th": "บลจ.ทดสอบ", "proj_name_th": "กองทดสอบเพื่อการเลี้ยงชีพ",
     "proj_abbr_name": "TESTRMF", "policy_desc": "ตราสารทุน", "risk_level": "6", "fee_ter_actual": "1.2", "sharpe_ratio": "0.5",
     "nav": "10.5", "nav_date": "2026-10-01", "data_as_of": "2026-10-01", "min_subscription": "1000"},
    {"proj_id": "M0002_2567", "fund_class_name": "main", "tax_type": "ThaiESG", "tax_type_confidence": "high", "classified_by": "field+name",
     "verified_status": "unverified", "fund_status": "Registered", "comp_name_th": "บลจ.ทดสอบ", "proj_name_th": "กองทดสอบ ThaiESG",
     "proj_abbr_name": "TESTESG", "policy_desc": "ผสม", "risk_level": "5", "fee_ter_actual": "", "sharpe_ratio": "",
     "nav": "", "nav_date": "", "data_as_of": "2026-08-31", "min_subscription": ""},
]


@pytest.fixture(autouse=True, scope="module")
def fake_data():
    d = Path(tempfile.mkdtemp(prefix="tfp-test-data-"))
    with open(d / "funds_table.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_COLS)
        w.writeheader()
        w.writerows(_ROWS)
    with open(d / "nav_series.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["proj_id", "fund_class_name", "nav_date", "nav"])
        w.writerows([["M0001_2560", "main", "2026-09-30", 10.4], ["M0001_2560", "main", "2026-10-01", 10.5]])
    old = funds_data.DATA_DIR
    funds_data.DATA_DIR = d
    funds_data.load_funds.cache_clear()
    funds_data.load_list.cache_clear()
    funds_data._nav_index.cache_clear()
    yield
    funds_data.DATA_DIR = old
    funds_data.load_funds.cache_clear()
    funds_data.load_list.cache_clear()
    funds_data._nav_index.cache_clear()
    shutil.rmtree(d, ignore_errors=True)


def test_meta():
    m = c.get("/api/meta").json()
    assert m["funds"]["n_classes"] == 2 and "มิใช่คำแนะนำ" in m["disclaimer"] and "ไม่ใช่การฝากเงิน" in m["disclaimer"]
    assert "มิได้เป็นสิ่งยืนยัน" in m["past_performance_notice"]


def test_tax_endpoints_are_gone():
    # ส่วนคำนวณภาษีถูกนำออกจากเว็บสาธารณะ ต้องไม่มี endpoint ภาษีหลงเหลือ
    assert c.post("/api/tax/calculate", json={}).status_code in (404, 405)
    assert c.get("/api/rules").status_code in (404,) or c.get("/api/rules").headers.get("content-type", "").startswith("text/html")


def test_funds_endpoints():
    f = c.get("/api/funds").json()
    assert len(f["items"]) == f["summary"]["n_classes"] and "มิได้เป็นสิ่งยืนยัน" in f["past_performance_notice"]
    row = next(x for x in f["items"] if x["nav"] is not None)
    assert c.get(f"/api/funds/{row['proj_id']}").status_code == 200
    n = c.get(f"/api/funds/{row['proj_id']}/nav", params={"fund_class_name": row["fund_class_name"]}).json()
    assert len(n["series"]) == 2 and not n["empty"]
    assert c.get("/api/funds/NOPE").status_code == 404
    # ค่าไม่ครบเป็น null ไม่ใช่ 0
    assert any(x["sharpe_ratio"] is None for x in f["items"])


def test_no_banned_wording_in_api_text():
    import json
    blob = json.dumps(c.get("/api/meta").json(), ensure_ascii=False)
    assert not any(w in blob for w in ("Top pick", "น่าซื้อ", "แนะนำให้ซื้อ"))


def test_list_is_slim_and_prefers_all_funds_table():
    f = c.get("/api/funds").json()["items"]
    assert set(f[0]) == set(funds_data.LIST_COLS)
    d = Path(tempfile.mkdtemp(prefix="tfp-test-all-"))
    old = funds_data.DATA_DIR
    try:
        cols = _COLS + ["asset_allocation", "sec_tax_tag"]
        row = dict(_ROWS[0], proj_id="M0009_2560", tax_type="", asset_allocation="หุ้น 90.00%", sec_tax_tag="")
        with open(d / "all_funds.csv", "w", encoding="utf-8-sig", newline="") as fh:
            w = csv.DictWriter(fh, fieldnames=cols)
            w.writeheader()
            w.writerow(row)
        funds_data.DATA_DIR = d
        funds_data.load_funds.cache_clear(); funds_data.load_list.cache_clear(); funds_data._nav_index.cache_clear()
        items = c.get("/api/funds").json()["items"]
        assert [x["proj_id"] for x in items] == ["M0009_2560"] and items[0]["tax_type"] is None  # กองทั่วไป: tax_type ว่าง = null
        assert "asset_allocation" not in items[0]  # ส่วนที่ไม่อยู่ในรายการ มาเฉพาะ /api/funds/{proj_id}
        assert c.get("/api/funds/M0009_2560").json()["classes"][0]["asset_allocation"] == "หุ้น 90.00%"
    finally:
        funds_data.DATA_DIR = old
        funds_data.load_funds.cache_clear(); funds_data.load_list.cache_clear(); funds_data._nav_index.cache_clear()
        shutil.rmtree(d, ignore_errors=True)


def test_unverified_tax_type_is_not_exposed():
    # RMF ที่จัดจากชื่ออย่างเดียวและยังไม่ยืนยัน (ความเชื่อมั่น medium, unverified) ต้องไม่ออกทาง API; ThaiESG ที่ ก.ล.ต. ระบุเอง (high) ออกได้
    items = {x["proj_id"]: x for x in c.get("/api/funds").json()["items"]}
    assert items["M0001_2560"]["tax_type"] is None and items["M0002_2567"]["tax_type"] == "ThaiESG"
    detail = c.get("/api/funds/M0001_2560").json()["classes"][0]
    assert detail["tax_type"] is None and "tax_type_unverified" not in detail
    assert c.get("/api/meta").json()["funds"]["by_type"]["RMF"] == 0
