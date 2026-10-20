"""กฎตรวจความสมเหตุสมผลของข้อมูลต่อแถว (ไม่แก้ค่า แค่ติดธงเพื่อแสดงให้ผู้ใช้เห็น)
ใช้ร่วมกันระหว่าง 08_build_funds_table.py (เขียนคอลัมน์ dq_flags) และ 14_audit_all_funds.py (รายงาน)
ธงทุกตัวหมายถึง "ควรตรวจกับเอกสารต้นทางก่อนใช้" ไม่ได้หมายความว่าข้อมูลผิดแน่นอน
"""
from datetime import date

# รหัสธง -> ข้อความอธิบายสำหรับผู้ใช้ (ภาษาไทย)
FLAG_TEXT = {
    "fee_actual_gt_max": "ค่าใช้จ่ายรวมเก็บจริงสูงกว่าตัวเลขสูงสุดที่แสดง (ตัวเลขสูงสุดอาจครอบคลุมเฉพาะค่าใช้จ่ายที่ประมาณการได้; ดูหมายเหตุ Fact Sheet)",
    "ter_lt_mgmt": "ค่าใช้จ่ายรวมรอบปีบัญชีต่ำกว่าค่าจัดการที่แสดงปัจจุบัน (อาจเป็นคนละช่วงเวลา; ตรวจหมายเหตุ Fact Sheet)",
    "fee_out_of_range": "ค่าธรรมเนียมอยู่นอกช่วงปกติ (ติดลบหรือเกิน 10% ต่อปี)",
    "risk_out_of_range": "ระดับความเสี่ยงอยู่นอกช่วง 1–8",
    "ret_extreme": "ผลตอบแทนหรือความผันผวนสูงผิดปกติ",
    "nav_nonpositive": "NAV ไม่เป็นบวก",
    "nav_stale": "NAV ไม่ได้อัปเดตมากกว่า 14 วันก่อนวันที่ข้อมูลล่าสุดของทั้งตาราง",
    "perf_zero_blanked": "ผลตอบแทนบางช่วงที่ ก.ล.ต. รายงานเป็น 0.00 ถูกแสดงเป็นว่าง เพราะกองมีอายุสั้นกว่าช่วงนั้น (0.00 เป็นค่าแทนข้อมูลที่ไม่มี)",
    "perf_zero_vs_nav": "ผลตอบแทนบางช่วงที่ ก.ล.ต. รายงานเป็น 0.00 แต่ NAV ในช่วงเดียวกันเปลี่ยนแปลงมาก จึงแสดงเป็นว่าง รวมช่วงอื่นของ class นี้ที่เป็น 0.00 พอดี (0.00 น่าจะเป็นค่าแทนข้อมูลที่ไม่มี)",
    "ret_below_nav": "ผลตอบแทนที่ ก.ล.ต. รายงานต่ำกว่าการเปลี่ยนแปลงของ NAV ในช่วงเดียวกันเกิน 2 จุด ซึ่งอธิบายด้วยเงินปันผลไม่ได้ (รายงานอาจคลาดเคลื่อน)",
    "min_sub_unclear": "ลงทุนขั้นต่ำไม่ได้เป็นจำนวนบาทที่ชัดเจน (เป็นสกุลเงินอื่น มีหน่วยอื่น หรือรายงานเป็น 0 โดยไม่ระบุว่าไม่กำหนด) จึงแสดงเป็นว่าง ดูข้อความหมายเหตุ",
    "fee_ter_zero": "ค่าธรรมเนียมรวมที่เก็บจริงเป็น 0 (อาจหมายถึงยังไม่มีข้อมูลหรือยกเว้นค่าธรรมเนียม ไม่ควรตีความว่าเป็นกองที่ถูกที่สุด)",
}
STALE_DAYS = 14


def _f(v):
    try:
        return float(v) if v not in ("", None) else None
    except (TypeError, ValueError):
        return None


def row_flags(r, ref_nav_date):
    """คืน list รหัสธงของแถว r (dict ของค่าสตริงจาก CSV หรือค่าจริง); ref_nav_date = วันที่ NAV ล่าสุดของทั้งตาราง (YYYY-MM-DD)"""
    out = []
    ter, mg, mx = _f(r.get("fee_ter_actual")), _f(r.get("fee_mgmt_actual")), _f(r.get("fee_ter_max"))
    if ter is not None and mx is not None and ter > mx + 0.01:
        out.append("fee_actual_gt_max")
    if ter is not None and ter == 0:
        out.append("fee_ter_zero")
    if ter is not None and ter > 0 and mg is not None and ter < mg - 0.005:
        out.append("ter_lt_mgmt")
    pct_fees = [_f(r.get(k)) for k in ("fee_ter_actual", "fee_mgmt_actual", "fee_ter_max", "fee_mgmt_max")]
    if any(v is not None and (v < 0 or v > 10) for v in pct_fees):
        out.append("fee_out_of_range")
    rl = _f(r.get("risk_level"))
    if rl is not None and not (1 <= rl <= 8):
        out.append("risk_out_of_range")
    ret, vol = _f(r.get("ret_1y")), _f(r.get("vol_1y"))
    if (ret is not None and abs(ret) > 300) or (vol is not None and abs(vol) > 200):
        out.append("ret_extreme")
    nav = _f(r.get("nav"))
    if nav is not None and nav <= 0:
        out.append("nav_nonpositive")
    nd = r.get("nav_date")
    if nd and ref_nav_date:
        try:
            if (date.fromisoformat(ref_nav_date) - date.fromisoformat(nd)).days > STALE_DAYS:
                out.append("nav_stale")
        except ValueError:
            pass
    return out


PERIOD_DAYS = {"1y": 365, "3y": 1095, "5y": 1826, "10y": 3652}
NAV_TOL_PP = 2.0


def _months_back(d, m):
    y, mo = d.year, d.month - m
    while mo <= 0:
        mo += 12
        y -= 1
    leap = y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)
    return date(y, mo, min(d.day, [31, 29 if leap else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][mo - 1]))


def _nav_on_or_before(series, d, max_gap_days):
    """series = [(YYYY-MM-DD, nav)] เรียงวันที่; คืน nav ล่าสุดที่ไม่เกินวัน d และห่างไม่เกิน max_gap_days"""
    best = None
    for dt, v in series:
        if dt <= d.isoformat():
            best = (dt, v)
        else:
            break
    if best and (d - date.fromisoformat(best[0])).days <= max_gap_days:
        return best[1]
    return None


def fix_placeholder_zeros(o, regis_date, nav_series):
    """แก้ค่า 0.00 ที่เป็น "ค่าแทนข้อมูลที่ไม่มี" ใน o (แก้ในที่เดิม) คืน list ธงที่เกิดขึ้น
    1) ผลตอบแทน 1/3/5/10 ปีเป็น 0 ทั้งที่กองจดทะเบียนมาสั้นกว่าช่วงนั้น -> ว่าง
    2) ผลตอบแทน ต้นปี/3 เดือน/6 เดือน เป็น 0 แต่ NAV ช่วงเดียวกันเปลี่ยนเกิน 2 จุด -> ว่าง
    3) ผลตอบแทนที่ไม่ใช่ 0 แต่ต่ำกว่า NAV เปลี่ยนเกิน 2 จุด -> ติดธง (ผลตอบแทนรวมปันผลต้องไม่ต่ำกว่าราคา)"""
    flags = []
    asof = o.get("perf_as_of")
    try:
        a = date.fromisoformat(asof) if asof else None
        g = date.fromisoformat(str(regis_date)[:10]) if regis_date else None
    except ValueError:
        a = g = None
    if a and g:
        for p, days in PERIOD_DAYS.items():
            if _f(o.get(f"ret_{p}")) == 0 and (a - g).days < days - 15:
                o[f"ret_{p}"] = ""
                if _f(o.get(f"vol_{p}")) == 0:
                    o[f"vol_{p}"] = ""
                flags.append("perf_zero_blanked")
    if a and nav_series:
        for col, base in (("ret_ytd", date(a.year - 1, 12, 31)), ("ret_3m", _months_back(a, 3)), ("ret_6m", _months_back(a, 6))):
            sec = _f(o.get(col))
            end_v, base_v = _nav_on_or_before(nav_series, a, 5), _nav_on_or_before(nav_series, base, 7)
            if sec is None or end_v is None or not base_v:
                continue
            derived = (end_v / base_v - 1) * 100
            if sec == 0 and abs(derived) > NAV_TOL_PP:
                o[col] = ""
                flags.append("perf_zero_vs_nav")
            elif sec != 0 and sec < derived - NAV_TOL_PP:
                flags.append("ret_below_nav")
    if "perf_zero_vs_nav" in flags:
        # รายงานของ class นี้ใช้ 0.00 แทนข้อมูลที่ไม่มีอยู่แล้วอย่างชัดเจน (ขัดกับ NAV) ช่วงอื่นที่เป็น 0.00 พอดีจึงถือเป็นค่าแทนเช่นกัน
        for k in list(o):
            if k.startswith("ret_") and _f(o.get(k)) == 0:
                o[k] = ""
    return sorted(set(flags))


FX_LABELS = {
    "fully": "ป้องกันความเสี่ยงทั้งหมด (fully hedged)",
    "dynamic": "ผู้จัดการใช้ดุลยพินิจ (dynamic hedging)",
    "none": "ไม่ป้องกัน (unhedged)",
    "class": "กำหนดในระดับชนิดหน่วยลงทุน",
}


def fx_policy_label(raw):
    """นโยบายป้องกันความเสี่ยงอัตราแลกเปลี่ยนตามข้อความของ ก.ล.ต. (exchange_rate_protection_policy) แปลงเป็นกลุ่มมาตรฐาน
    ข้อความที่ไม่รู้จักหรือไม่มีข้อมูลคืนสตริงว่าง (ไม่เดา)"""
    t = str(raw or "").strip()
    if t.startswith("ดุลยพินิจ"):
        return FX_LABELS["dynamic"]
    if t.startswith("ทั้งหมด"):
        return FX_LABELS["fully"]
    if t.startswith("ไม่ป้องกัน"):
        return FX_LABELS["none"]
    if t.startswith("กำหนดในระดับชนิดหน่วยลงทุน"):
        return FX_LABELS["class"]
    return ""


def _clean(v):
    return None if v is None or str(v).strip() in ("", "None", "null") else v


def _num(v):
    v = _clean(v)
    try:
        return float(v) if v is not None else ""
    except ValueError:
        return ""


def min_sub_value(row):
    """ลงทุนขั้นต่ำเป็นบาท: ใช้ค่าเมื่อสกุล THB และไม่มีหน่วยอื่น; "ไม่กำหนด" = 0 บาท (ไม่มีขั้นต่ำ) พร้อมหมายเหตุ;
    สกุลอื่น/หน่วยอื่น/ค่า 0 ที่ไม่ระบุว่าไม่กำหนด -> ว่าง (ไม่เดา) พร้อมหมายเหตุ  คืน (ค่า, หมายเหตุ)"""
    v = _num(row.get("minimum_sub"))
    cur = str(_clean(row.get("minimum_sub_cur")) or "").strip().upper()
    unit = str(_clean(row.get("minimum_sub_unit")) or "").strip()
    if unit.replace("ํา", "ำ") == "ไม่กำหนด":
        return 0.0, "ไม่กำหนดขั้นต่ำ"
    if cur and cur != "THB":
        return "", f"รายงานเป็นสกุล {cur}" + (f" ({unit})" if unit else "")
    if unit not in ("", "-"):
        return "", f"หน่วย/ข้อความจาก บลจ.: {unit}"
    if v == "":
        return "", ""
    if v == 0:
        return "", "รายงานเป็น 0 โดยไม่ระบุว่าไม่กำหนดขั้นต่ำ"
    return v, ""
