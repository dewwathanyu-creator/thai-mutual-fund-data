"""เทสต์กฎคัดประเภทกอง: รันด้วย `python -m pytest tests` หรือ `python tests/test_fund_type_rules.py`"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from fund_type_rules import (RMF, SSF, THAIESG, THAIESGX, THAIESG_UNSPEC,  # noqa: E402
                             classify, match_types)


def rec(**kw):
    base = {k: None for k in ("proj_abbr_name", "proj_name_th", "proj_name_en", "fund_class_name",
                              "fund_class_detail", "fund_class_description",
                              "fund_class_tax_incentive_type")}
    base.update(kw)
    return base


def test_should_match():
    cases = [("K-VIETNAMRMF", RMF), ("TFPRMF-A", RMF), ("กองทุนเปิดกรุงไทยผสมเพื่อการเลี้ยงชีพ (RMF1)", RMF),
             ("KT-ESG RMF", RMF), ("K-HDThaiESGX-68", THAIESGX), ("BEQD-TESGX", THAIESGX),
             ("MFC Mixed Thailand ESG Extra Fund", THAIESGX), ("หุ้นไทยเพื่อความยั่งยืนแบบพิเศษ", THAIESGX),
             ("B-EQ-THAIESG", THAIESG), ("MFC Flexible Thailand ESG Fund", THAIESG),
             ("กองทุนเปิดวรรณ หุ้นไทยเพื่อความยั่งยืน", THAIESG),
             ("X-SEQS-ASSF", SSF), ("K-SUPSTAR-SSFX", SSF), ("BCAP-GW10 SSF", SSF)]
    for text, want in cases:
        assert want in match_types(text)[0], (text, want)


def test_should_not_match():
    cases = ["K ESG Balanced 30 Fund",                       # ESG ทั่วไป
             "Krungthai ESG A Grade Fund",                   # ชื่อ บลจ. มีคำว่า thai
             "Krung Thai ESG Sovereign Instruments Fund",
             "กองทุนเปิดไทยพาณิชย์ หุ้นไทยยั่งยืนแบบพาสซีฟ",  # ยั่งยืน ไม่ใช่ ไทยเพื่อความยั่งยืน
             "กองทุนสำรองเลี้ยงชีพ", "ชนิดกองทุนสำรองเลี้ยงชีพ",  # provident fund ไม่ใช่ RMF
             "SCBLTSE", "CLASSFUND-A", "SCB Thai Sustainable Equity"]
    for text in cases:
        assert not match_types(text)[0], text


def test_rmf_followed_by_letters_is_ambiguous_not_matched():
    found, amb = match_types("XRMFUND")
    assert RMF not in found and amb


def test_field_plus_name_splits_esg_x():
    r = classify(rec(fund_class_tax_incentive_type="กองทุนรวมไทยเพื่อความยั่งยืน (Thailand ESG Fund : Thai ESG)",
                     proj_abbr_name="K-HDThaiESGX", fund_class_name="K-HDThaiESGX-68"))
    assert (r["tax_type"], r["confidence"], r["classified_by"]) == (THAIESGX, "high", "field+name")


def test_field_only_esg_is_unspecified():
    r = classify(rec(fund_class_tax_incentive_type="กองทุนรวมไทยเพื่อความยั่งยืน (Thailand ESG Fund : Thai ESG)",
                     proj_abbr_name="ABC", fund_class_name="main"))
    assert r["tax_type"] == THAIESG_UNSPEC and r["confidence"] == "high"


def test_name_only_is_medium_and_field_name_conflict_is_low():
    assert classify(rec(proj_abbr_name="K-BLRMF", fund_class_name="main"))["confidence"] == "medium"
    r = classify(rec(fund_class_tax_incentive_type="SSF", proj_abbr_name="X-RMF", fund_class_name="main"))
    assert r["confidence"] == "low" and "ชื่อบอก" in r["conflict"]


def test_description_alone_never_classifies():
    r = classify(rec(proj_abbr_name="K-VALUE", fund_class_name="A",
                     fund_class_description="เมื่อรวมกับกองทุน RMF กองทุนสำรองเลี้ยงชีพ"))
    assert r["tax_type"] == ""


if __name__ == "__main__":
    from sec_client import utf8_stdout
    utf8_stdout()
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
            print("ผ่าน", n)
