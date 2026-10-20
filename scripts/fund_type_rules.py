"""กฎคัดประเภทกองลดหย่อน (RMF / ThaiESG / ThaiESGX / SSF) ระดับ class

ไม่แตะเครือข่าย ไม่อ่าน .env: รับ record 1 แถวจาก /v2/fund/general-info/profiles
คืน dict ที่มี tax_type, classified_by, confidence, conflict, evidence

ลำดับหลักฐาน (ตามที่ผู้ใช้กำหนด)
  1. fund_class_tax_incentive_type ("Thai ESG", "SSF")          -> high
  2. ชื่อ (proj_abbr_name, fund_class_name, proj_name_th/en) และ
     fund_class_detail                                           -> medium
  fund_class_description / policy_desc / proj_retail_type ตรวจแล้ว **ไม่ใช้จัดประเภท**:
     description อ้างถึงผลิตภัณฑ์ภาษีอื่นปนกัน (SSF พูดถึง RMF, กอง LTF เดิมพูดว่า "ไม่สามารถลดหย่อนได้")

หลักการกันจับผิด
  - "ESG" เฉยๆ (เช่น K ESG Balanced, ซัสเทนเนเบิล, ไทยยั่งยืน) ไม่ใช่ ThaiESG
  - ThaiESG ต้องเห็น THAI ESG / THAILAND ESG / "ไทยเพื่อความยั่งยืน"; ThaiESGX ต้องเห็น ESGX หรือ "แบบพิเศษ"
  - RMF ต้องเป็นท้าย token (K-VIETNAMRMF, RMF1) ไม่นับ RMF ที่ตามด้วยตัวอักษร (ไปรายงานเป็นกำกวม)
  - "กองทุนสำรองเลี้ยงชีพ" (provident fund) ไม่ใช่ "เพื่อการเลี้ยงชีพ" (RMF)
"""
import re

RMF = "RMF"
THAIESG = "ThaiESG"
THAIESGX = "ThaiESGX"
THAIESG_UNSPEC = "Thai ESG (ไม่ระบุ X)"
SSF = "SSF"
NONE = ""

ESG_FAMILY = {THAIESG, THAIESGX, THAIESG_UNSPEC}
FIELD_MAP = {"thai esg": THAIESG_UNSPEC, "ssf": SSF}

# ThaiESGX: ESGX (รวม TESGX, THAIESGX) หรือ "ESG Extra" หรือ "ไทยเพื่อความยั่งยืนแบบพิเศษ"
_X = re.compile(r"ESGX|ESG[\s\-_]*EXTRA|ความยั่งยืน\s*แบบพิเศษ", re.I)
# ThaiESG (ไม่ระบุ X): ต้องมีคำว่า Thai/Thailand ติดกับ ESG หรือ "ไทยเพื่อความยั่งยืน"
# (กันชื่อบลจ. "Krung Thai ESG ..." / "Krungthai ESG ..." ที่เป็นกอง ESG ทั่วไป ไม่ใช่ ThaiESG)
_ESG = re.compile(r"(?<!KRUNG)(?<!KRUNG )THAI(?:LAND)?[\s\-_]*ESG|ไทยเพื่อความยั่งยืน|กองทุนรวมไทยเพื่อความยั่งยืน", re.I)
# RMF: ท้าย token (อนุญาตเลขต่อท้าย) หรือ "เพื่อการเลี้ยงชีพ"
_RMF_TOKEN = re.compile(r"(?<![A-Z0-9])[A-Z0-9]*RMF\d*(?![A-Z])", re.I)
_RMF_TH = re.compile(r"เพื่อการเลี้ยงชีพ")
_RMF_AMBIG = re.compile(r"RMF(?=[A-Z])", re.I)  # RMF ตามด้วยตัวอักษร เช่น RMFA, RMFUND
# SSF: ท้าย token (SSF, ASSF, SSFX, SSF1)
_SSF_TOKEN = re.compile(r"(?<![A-Z0-9])[A-Z0-9]*SSFX?\d*(?![A-Z])", re.I)
_SSF_TH = re.compile(r"เพื่อการออม")
_LTF = re.compile(r"(?<![A-Z0-9])[A-Z0-9]*LTF\d*(?![A-Z])", re.I)

NAME_FIELDS_PROJECT = ("proj_abbr_name", "proj_name_th", "proj_name_en")
NAME_FIELDS_CLASS = ("fund_class_name", "fund_class_detail")


def _norm(text):
    return "" if text is None else str(text)


def match_types(text):
    """คืน (set ของประเภทที่พบในข้อความ, ธงกำกวม)"""
    text = _norm(text)
    found, ambiguous = set(), []
    if _X.search(text):
        found.add(THAIESGX)
    elif _ESG.search(text):
        found.add(THAIESG)  # ชื่อระบุ ThaiESG ชัด ไม่มี X
    if _RMF_TOKEN.search(text) or _RMF_TH.search(text):
        found.add(RMF)
    elif _RMF_AMBIG.search(text):
        ambiguous.append("RMF ตามด้วยตัวอักษร")
    if _SSF_TOKEN.search(text) or _SSF_TH.search(text):
        found.add(SSF)
    return found, ambiguous


def _family(t):
    return "ESG" if t in ESG_FAMILY else t


def classify(rec):
    """จัดประเภท 1 class คืน dict"""
    field_raw = _norm(rec.get("fund_class_tax_incentive_type")).strip()
    field_type = NONE
    for key, val in FIELD_MAP.items():
        if key in field_raw.lower():
            field_type = val
    ltf = bool(_LTF.search(" ".join(_norm(rec.get(k)) for k in
                                    NAME_FIELDS_PROJECT + NAME_FIELDS_CLASS)))

    ev = []  # (source, type)
    ambiguous = []
    for k in NAME_FIELDS_CLASS:
        found, amb = match_types(rec.get(k))
        ev += [(f"class:{k}", t) for t in found]
        ambiguous += amb
    for k in NAME_FIELDS_PROJECT:
        found, amb = match_types(rec.get(k))
        ev += [(f"proj:{k}", t) for t in found]
        ambiguous += amb
    name_types = {t for s, t in ev}
    class_types = {t for s, t in ev if s.startswith("class:")}

    # ประเภทจากชื่อ: ระดับ class ละเอียดกว่าระดับกอง จึงใช้ class ก่อน
    def pick(types):
        for t in (THAIESGX, THAIESG, RMF, SSF):
            if t in types:
                return t
        return NONE

    name_type = pick(class_types) or pick(name_types)

    sources = []
    conflict = ""
    if field_type:
        sources.append("field")
        tax_type, confidence = field_type, "high"
        if name_type:
            sources.append("name")
            if field_type in ESG_FAMILY and name_type in ESG_FAMILY:
                tax_type = name_type  # ชื่อช่วยแยก X/ไม่ X
            elif _family(field_type) != _family(name_type):
                conflict = f"field={field_type} แต่ชื่อบอก {name_type}"
                confidence = "low"
    elif name_type:
        sources.append("name")
        tax_type, confidence = name_type, "medium"
        if len({_family(t) for t in name_types}) > 1:
            conflict = f"ชื่อบอกหลายประเภท: {sorted(name_types)}"
            confidence = "low"
    else:
        return {"tax_type": NONE, "classified_by": "", "confidence": "",
                "conflict": "", "ambiguous": "; ".join(sorted(set(ambiguous))),
                "ltf_mention": ltf, "evidence": ""}

    if ambiguous and confidence == "medium":
        confidence = "low"
    evidence = ", ".join(f"{s}={t}" for s, t in ev)
    return {"tax_type": tax_type, "classified_by": "+".join(sources),
            "confidence": confidence, "conflict": conflict,
            "ambiguous": "; ".join(sorted(set(ambiguous))),
            "ltf_mention": ltf, "evidence": evidence}
