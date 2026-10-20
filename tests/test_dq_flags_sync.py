"""ข้อความธงใน web/src/dq.ts ต้องตรงกับ scripts/data_quality.py (กันหน้าเว็บแสดงข้อความคนละอย่างกับรายงานตรวจ)"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from data_quality import FLAG_TEXT, row_flags  # noqa: E402


def test_ts_flag_text_matches_python():
    ts = (ROOT / "web" / "src" / "dq.ts").read_text(encoding="utf-8")
    found = dict(re.findall(r'^\s*(\w+): "([^"]+)",\s*$', ts, flags=re.M))
    assert found == FLAG_TEXT


def _row(**kw):
    base = {"fee_ter_actual": "1.5", "fee_mgmt_actual": "1.0", "fee_ter_max": "2.0", "fee_mgmt_max": "1.5", "risk_level": "6",
            "ret_1y": "5", "vol_1y": "10", "nav": "10", "nav_date": "2026-10-12"}
    base.update({k: str(v) for k, v in kw.items()})
    return base


def test_row_flags_hand_cases():
    assert row_flags(_row(), "2026-10-12") == []
    assert row_flags(_row(fee_ter_actual=0), "2026-10-12") == ["fee_ter_zero"]  # 0 ไม่ใช่ "ถูกที่สุด" ต้องมีธง
    assert "fee_actual_gt_max" in row_flags(_row(fee_ter_actual=2.5), "2026-10-12")
    assert "ter_lt_mgmt" in row_flags(_row(fee_ter_actual=0.5), "2026-10-12")
    assert "fee_out_of_range" in row_flags(_row(fee_ter_max=10.7), "2026-10-12")
    assert "nav_stale" in row_flags(_row(nav_date="2026-09-01"), "2026-10-12")
    assert "nav_stale" not in row_flags(_row(nav_date="2026-09-30"), "2026-10-12")
    assert "ret_extreme" in row_flags(_row(vol_1y=536), "2026-10-12")
    assert row_flags(_row(fee_ter_actual="", fee_mgmt_actual=""), "2026-10-12") == []  # ค่าว่างไม่ใช่ธง


# ---- กฎแก้ค่า 0.00 ที่เป็นค่าแทนข้อมูลที่ไม่มี (data_quality.fix_placeholder_zeros) และขั้นต่ำการลงทุน ----
from data_quality import fix_placeholder_zeros  # noqa: E402


def _perf(**kw):
    o = {"perf_as_of": "2026-08-31", "ret_ytd": "", "ret_3m": "", "ret_6m": "", "ret_1y": "", "ret_3y": "", "ret_5y": "", "ret_10y": "",
         "vol_3y": "", "vol_5y": "", "vol_10y": "", "vol_1y": ""}
    o.update({k: kw[k] for k in kw})
    return o


def test_young_fund_zero_period_becomes_blank():
    # จดทะเบียน 2024-03-01: ณ 2026-08-31 อายุ ~2.5 ปี -> 3y/5y/10y ที่เป็น 0 คือค่าแทนข้อมูลที่ไม่มี; 1y เป็น 0 จริงได้ ต้องคงไว้
    o = _perf(ret_1y=0.0, ret_3y=0.0, ret_5y=0.0, ret_10y=0.0, vol_5y=0.0)
    flags = fix_placeholder_zeros(o, "2024-03-01", [])
    assert o["ret_3y"] == "" and o["ret_5y"] == "" and o["ret_10y"] == "" and o["vol_5y"] == ""
    assert o["ret_1y"] == 0.0 and flags == ["perf_zero_blanked"]


def test_old_fund_zero_is_kept_and_nonzero_young_is_kept():
    o = _perf(ret_10y=0.0, ret_5y=3.2)
    assert fix_placeholder_zeros(o, "2001-01-01", []) == [] and o["ret_10y"] == 0.0  # อายุเกินช่วง: ไม่เดาว่าเป็นค่าแทน
    o2 = _perf(ret_5y=3.2)
    fix_placeholder_zeros(o2, "2024-03-01", [])
    assert o2["ret_5y"] == 3.2  # ค่าไม่ใช่ศูนย์ไม่แก้


def test_zero_ytd_vs_nav_change_is_blanked_and_below_nav_flagged():
    nav = [("2025-12-30", 10.0), ("2026-05-29", 11.0), ("2026-08-31", 13.0)]  # ต้นปี +30%, 3 เดือน +18.2%, 6 เดือน +30%
    o = _perf(ret_ytd=0.0, ret_3m=5.0, ret_6m=31.0)
    flags = fix_placeholder_zeros(o, "2010-01-01", nav)
    assert o["ret_ytd"] == "" and "perf_zero_vs_nav" in flags      # 0.00 ขัดกับ NAV +30% -> ว่าง
    assert o["ret_3m"] == 5.0 and "ret_below_nav" in flags           # 5% < 18% เป็นต้นไป อธิบายด้วยปันผลไม่ได้ -> ธง ไม่แก้ค่า
    assert o["ret_6m"] == 31.0                                        # รวมปันผลสูงกว่า NAV ได้ ไม่ติดธง


def test_zero_vs_nav_blanks_other_exact_zero_periods_of_same_class():
    nav = [("2025-12-30", 10.0), ("2026-08-31", 13.0)]
    o = _perf(ret_ytd=0.0, ret_1y=0.0, ret_3y=7.5)
    fix_placeholder_zeros(o, "2010-01-01", nav)
    assert o["ret_ytd"] == "" and o["ret_1y"] == "" and o["ret_3y"] == 7.5


def test_ytd_matches_when_close():
    nav = [("2025-12-31", 10.0), ("2026-08-31", 11.0)]
    o = _perf(ret_ytd=10.2)
    assert fix_placeholder_zeros(o, "2010-01-01", nav) == [] and o["ret_ytd"] == 10.2


from data_quality import min_sub_value  # noqa: E402


def test_min_subscription_rules():
    thb = "THB" + " " * 40  # ข้อมูลจริงมีช่องว่างต่อท้ายสกุลเงิน
    assert min_sub_value({"minimum_sub": 1000.0, "minimum_sub_cur": thb, "minimum_sub_unit": None}) == (1000.0, "")
    assert min_sub_value({"minimum_sub": 0.0, "minimum_sub_cur": thb, "minimum_sub_unit": "ไม่กำหนด"}) == (0.0, "ไม่กำหนดขั้นต่ำ")
    assert min_sub_value({"minimum_sub": 0.0, "minimum_sub_cur": thb, "minimum_sub_unit": "ไม่กําหนด"})[0] == 0.0  # สระ ํ + า
    v, note = min_sub_value({"minimum_sub": 100.0, "minimum_sub_cur": "USD" + " " * 40, "minimum_sub_unit": None})
    assert v == "" and "USD" in note                                     # สกุลอื่น ไม่ใช่บาท
    v, note = min_sub_value({"minimum_sub": 0.0, "minimum_sub_cur": thb, "minimum_sub_unit": "10 ดอลลาร์สหรัฐอเมริกา"})
    assert v == "" and "ดอลลาร์" in note                                 # ค่า 0 แต่ข้อความบอกว่า 10 ดอลลาร์
    v, note = min_sub_value({"minimum_sub": 0.0, "minimum_sub_cur": thb, "minimum_sub_unit": None})
    assert v == "" and note                                              # 0 ไม่ระบุว่าไม่กำหนด -> ว่าง ไม่เดาว่าไม่มีขั้นต่ำ
    assert min_sub_value({"minimum_sub": None, "minimum_sub_cur": None, "minimum_sub_unit": None}) == ("", "")



from data_quality import fx_policy_label, FX_LABELS  # noqa: E402


def test_fx_policy_label_uses_only_known_texts():
    assert fx_policy_label("ดุลยพินิจ (dynamic hedging) (0%-105% ของมูลค่า)") == FX_LABELS["dynamic"]
    assert fx_policy_label("ทั้งหมด (fully hedged) (95%-105% ของมูลค่า)") == FX_LABELS["fully"]
    assert fx_policy_label("ทั้งหมด/เกือบทั้งหมด") == FX_LABELS["fully"]
    assert fx_policy_label("ไม่ป้องกัน (unhedged)") == FX_LABELS["none"] and fx_policy_label("ไม่ป้องกัน") == FX_LABELS["none"]
    assert fx_policy_label("กำหนดในระดับชนิดหน่วยลงทุน") == FX_LABELS["class"]
    assert fx_policy_label("None") == "" and fx_policy_label(None) == "" and fx_policy_label("ข้อความอื่น") == ""
