"""สร้างกราฟและตัวเลขสรุปสำหรับ README จาก data/all_funds.csv (ไม่เรียกเครือข่าย)
ผลลัพธ์: docs/img/fee_by_policy.png, docs/img/dq_flags.png และพิมพ์ตัวเลขสรุปที่ใช้ใน README
ฐานการวิเคราะห์ค่าธรรมเนียม: class ที่รายงานค่าใช้จ่ายรวม (TER) มากกว่า 0 และไม่ติดธงค่าธรรมเนียม
"""
import sys
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "img"
OUT.mkdir(parents=True, exist_ok=True)

FEE_FLAGS = {"fee_ter_zero", "ter_lt_mgmt", "fee_actual_gt_max", "fee_out_of_range"}
POLICY_EN = {"ตราสารทุน": "Equity", "ผสม": "Mixed", "ตราสารหนี้": "Fixed income", "ทรัพย์สินทางเลือก": "Alternative"}
FLAG_EN = {
    "min_sub_unclear": "Minimum investment unclear",
    "perf_zero_blanked": "Placeholder 0.00 return blanked (fund younger than period)",
    "fee_ter_zero": "Reported total expense is exactly 0",
    "ret_below_nav": "Reported return below NAV change",
    "nav_stale": "NAV older than 14 days",
    "ter_lt_mgmt": "Total expense below management fee",
    "perf_zero_vs_nav": "Placeholder 0.00 return blanked (contradicts NAV)",
}


def main() -> None:
    d = pd.read_csv(ROOT / "data" / "all_funds.csv", dtype=str)
    for c in ["fee_ter_actual", "ret_1y", "risk_level"]:
        d[c] = pd.to_numeric(d[c], errors="coerce")
    flags = d["dq_flags"].fillna("").apply(lambda s: [x for x in s.replace(";", ",").replace("|", ",").split(",") if x.strip()])
    flags = flags.apply(lambda xs: [x.strip() for x in xs])
    n = len(d)
    print("classes", n, "projects", d["proj_id"].nunique(), "AMCs", d["comp_name_th"].nunique())
    print("classes with >=1 note:", int((flags.str.len() > 0).sum()))

    # ---- ค่าธรรมเนียมตามนโยบายลงทุน
    ok = d[(d.fee_ter_actual > 0) & ~flags.apply(lambda xs: bool(FEE_FLAGS & set(xs)))].copy()
    ok["policy"] = ok["policy_desc"].map(POLICY_EN)
    ok = ok.dropna(subset=["policy"])
    print("TER base", len(ok), "of", int(d.fee_ter_actual.notna().sum()), "with TER reported")
    print("share TER > 2%:", round((ok.fee_ter_actual > 2).mean() * 100, 1))
    order = ["Equity", "Mixed", "Fixed income", "Alternative"]
    stats = ok.groupby("policy").fee_ter_actual.describe(percentiles=[0.1, 0.5, 0.9]).loc[order]
    print(stats[["count", "10%", "50%", "90%"]].round(2).to_string())
    print("overall median", round(ok.fee_ter_actual.median(), 2))
    by_risk = ok.groupby("risk_level").fee_ter_actual.agg(["count", "median"]).round(2)
    print(by_risk.to_string())

    fig, ax = plt.subplots(figsize=(8.5, 4.2))
    data = [ok[ok.policy == p].fee_ter_actual.values for p in order]
    bp = ax.boxplot(data, vert=False, whis=(10, 90), showfliers=False, patch_artist=True, medianprops=dict(color="#0a1f44", linewidth=2))
    for patch in bp["boxes"]:
        patch.set(facecolor="#9bbfff", edgecolor="#1b4b9b")
    ax.set_yticklabels([f"{p} (n={len(v):,})" for p, v in zip(order, data)])
    ax.invert_yaxis()
    ax.set_xlabel("Reported total expense ratio, % per year (box = 25th-75th pct, whiskers = 10th-90th pct)")
    ax.set_title("Fee dispersion by investment policy", loc="left", fontweight="bold")
    ax.grid(axis="x", alpha=0.3)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "fee_by_policy.png", dpi=160)

    # ---- ธงคุณภาพข้อมูล
    cnt = Counter(f for xs in flags for f in set(xs))
    print("flags:", dict(cnt.most_common()))
    keys = [k for k in FLAG_EN if k in cnt]
    keys.sort(key=lambda k: cnt[k])
    fig, ax = plt.subplots(figsize=(8.5, 3.8))
    ax.barh([FLAG_EN[k] for k in keys], [cnt[k] for k in keys], color="#1b4b9b")
    for i, k in enumerate(keys):
        ax.text(cnt[k] + 8, i, f"{cnt[k]:,}", va="center", fontsize=9)
    ax.set_xlabel(f"Fund classes with the note (of {n:,})")
    ax.set_title("What the data-quality checks found", loc="left", fontweight="bold")
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    fig.tight_layout()
    fig.savefig(OUT / "dq_flags.png", dpi=160)
    print("charts written to", OUT)


if __name__ == "__main__":
    sys.exit(main())
