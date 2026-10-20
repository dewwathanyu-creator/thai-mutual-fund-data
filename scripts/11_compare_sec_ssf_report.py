"""เทียบการจัดประเภท RMF ของเรากับรายงาน ก.ล.ต. SSF_TH.xls (ref/SSF_TH.xls: ตาราง SSF listed / SSF / RMF / LTF จำแนกรายกองทุน)
ไม่แตะเครือข่าย อ่านไฟล์ใน ref/ และ data/funds_table.csv -> data/sec_report_comparison.csv + พิมพ์สรุป
คีย์จับคู่: ชื่อย่อ (ชื่อย่อโครงการ/ชื่อ class) ที่ normalize แล้ว เพราะเลขที่จดทะเบียนในรายงาน (003/2545) ไม่ตรงรูปแบบ proj_id (M0004_2556)
"""
import re, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.stdout.reconfigure(encoding="utf-8")


VERIFIED = "sec_report_rmf_2569-07-31"
SEC_MRAP_RMF = {"M0061_2544": "sec_mrap_rmf_2569-09-15"}  # K-SELECTRMF: https://market.sec.or.th/public/mrap/MRAPView.aspx?FTYPE=M&PID=0061&PYR=2544&lang=en


def norm(s):
    return re.sub(r"[\s\-_().]", "", str(s)).upper()


def read_report(path):
    d = pd.read_excel(path, header=None).dropna(how="all", axis=1)
    out, tab, cols = [], None, None
    for _, r in d.iterrows():
        vals = [str(v) for v in r.values if str(v) != "nan"]
        s = " ".join(vals)
        m = re.search(r"ตารางที่ \d : (.*)", s)
        if m:
            tab, cols = m.group(1).strip(), None
            continue
        if tab and "เลขที่จดทะเบียน" in s:
            cols = {str(v).strip(): j for j, v in enumerate(r.values) if str(v) != "nan"}
            continue
        if tab and cols and str(r.iloc[0]).strip().isdigit():
            g = lambda k: str(r.iloc[cols[k]]).strip() if k in cols else ""
            out.append(dict(table=tab, reg=g("เลขที่จดทะเบียน"), name=g("ชื่อกองทุน"), abbr=g("ชื่อย่อ"),
                            unit=g("ชนิดหน่วยลงทุน"), status=g("สถานะกองทุน"), special=g("ลักษณะพิเศษ")))
    return pd.DataFrame(out)


def main():
    sec = read_report(ROOT / "ref" / "SSF_TH.xls")
    sec["n"] = sec.abbr.map(norm)
    print("แถวในรายงาน:", sec.table.value_counts().to_dict())
    f = pd.read_csv(ROOT / "data" / "funds_table.csv", dtype=str)
    f["n"] = f.proj_abbr_name.map(norm)
    f["nc"] = f.fund_class_name.map(norm)
    rmf = f[f.tax_type == "RMF"].copy()
    sec_by_table = {t: set(g.n) for t, g in sec.groupby("table")}
    srmf = sec[sec.table == "RMF"]

    def where(r):
        for t, s in sec_by_table.items():
            if r.n in s or r.nc in s:
                return t
        # ทางสำรอง: ชื่อย่อโครงการเป็นคำนำหน้าของชื่อย่อ class ในรายงาน (เช่น TFPRMF -> TFPRMF-PVD) นับเป็น "พบแบบหลวม"
        for t, s in sec_by_table.items():
            if len(r.n) >= 5 and any(x.startswith(r.n) for x in s):
                return t + " (หลวม)"
        return ""
    rmf["sec_table"] = rmf.apply(where, axis=1)
    # ทางสำรองที่ 2: ชื่อกองเต็ม (ตัดคำว่า กองทุนเปิด และส่วนต่อท้าย " - ชนิด...") ตรงกับตาราง RMF เท่านั้น
    # ใช้กับกองที่ชื่อย่อในรายงานเป็นรหัสสุ่ม/ชื่อย่อ class ต่างจาก API
    nn = lambda x: re.sub(r"[\s\-_().]|กองทุนเปิด|กองทุนรวม", "", str(x)).upper()
    rnames = {nn(re.split(r"\s-\s", x)[0]) for x in srmf.name}
    byname = (rmf.sec_table == "") & rmf.proj_name_th.map(lambda x: nn(x) in rnames)
    rmf.loc[byname, "sec_table"] = "RMF (ชื่อเต็ม)"
    print("\nRMF ของเรา (class):", len(rmf), "| ชื่อย่อไม่ซ้ำ:", rmf.n.nunique())
    print(rmf.sec_table.replace("", "(ไม่พบในรายงาน)").value_counts().to_dict())
    miss = rmf[rmf.sec_table == ""]
    print("\nRMF ของเราที่ไม่พบในรายงาน:", len(miss), miss.fund_status.value_counts().to_dict())
    print(miss[["proj_id", "fund_class_name", "proj_abbr_name", "fund_status"]].to_string())
    ours = set(rmf.n) | set(rmf.nc)
    only_sec = srmf[~srmf.n.isin(ours)]
    print("\nแถว RMF ในรายงานที่ไม่พบในตารางเรา:", len(only_sec), only_sec.status.value_counts().to_dict())
    print(only_sec[["reg", "abbr", "status"]].to_string())
    # ThaiESG/ThaiESGX/อื่นที่อยู่ในรายงาน
    other = f[f.tax_type != "RMF"].copy()
    other["sec_table"] = other.apply(where, axis=1)
    print("\nที่ไม่ใช่ RMF ของเราแต่พบในรายงาน:", other.groupby(["tax_type", "sec_table"]).size().to_dict())
    # เขียนสถานะกลับ: RMF ที่ตรงรายงาน หรือยืนยันจากหน้า SEC MRAP ของโครงการโดยตรง
    hit = set(zip(rmf[rmf.sec_table.str.startswith("RMF")].proj_id, rmf[rmf.sec_table.str.startswith("RMF")].fund_class_name))
    for fn in ("funds_table.csv", "fund_class_types.csv"):
        path = ROOT / "data" / fn
        t = pd.read_csv(path, dtype=str, keep_default_na=False, encoding="utf-8-sig")
        m = [(a, b) in hit and tt == "RMF" for a, b, tt in zip(t.proj_id, t.fund_class_name, t.tax_type)]
        t.loc[m, "verified_status"] = VERIFIED
        for proj_id, status in SEC_MRAP_RMF.items():
            direct = (t.proj_id == proj_id) & (t.tax_type == "RMF")
            t.loc[direct, "verified_status"] = status
        t.to_csv(path, index=False, encoding="utf-8-sig")
        print(f"{fn}: ตั้ง verified_status = {VERIFIED} จำนวน {sum(m)} แถว")
    rmf[["proj_id", "fund_class_name", "proj_abbr_name", "fund_status", "tax_type_confidence", "sec_table"]].to_csv(
        ROOT / "data" / "sec_report_comparison.csv", index=False, encoding="utf-8-sig")


if __name__ == "__main__":
    main()
