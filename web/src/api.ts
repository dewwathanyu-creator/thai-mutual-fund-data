// ชนิดข้อมูลและตัวเรียก API ข้อมูลกองทุน (อ่านอย่างเดียว ไม่มีข้อมูลส่วนบุคคลถูกส่งไปที่เซิร์ฟเวอร์)

export interface Meta {
  disclaimer: string; past_performance_notice: string;
  funds: { n_classes: number; n_funds: number; n_amc: number; by_type: Record<string, number>; data_as_of_latest: string | null; data_as_of_oldest: string | null };
}

export interface Fund {
  proj_id: string; fund_class_name: string; api_class_name: string | null; class_match: string;
  tax_type: "RMF" | "SSF" | "ThaiESG" | "ThaiESGX" | null; sec_tax_tag: string | null; risk_label: string | null; dq_flags: string | null;
  min_sub_note: string | null; class_detail: string | null; fx_policy: string | null; master_fund: string | null; master_country: string | null;
  tax_type_confidence: string; classified_by: string; verified_status: string; fund_status: string;
  comp_name_th: string; proj_name_th: string; proj_abbr_name: string; policy_desc: string | null;
  risk_spectrum: string | null; risk_level: number | null; risk_spectrum_desc: string | null; risk_as_of: string | null;
  fee_mgmt_max: number | null; fee_mgmt_actual: number | null; fee_ter_max: number | null; fee_ter_actual: number | null;
  fee_front_max: number | null; fee_front_actual: number | null; fee_back_max: number | null; fee_back_actual: number | null;
  fee_switch_in_max: number | null; fee_switch_out_max: number | null; fees_as_of: string | null;
  ret_3m: number | null; ret_6m: number | null; ret_ytd: number | null; ret_1y: number | null; ret_3y: number | null; ret_5y: number | null; ret_10y: number | null; ret_inception: number | null;
  vol_1y: number | null; bench_ret_1y: number | null; peer_ret_1y: number | null; perf_as_of: string | null;
  maximum_drawdown: number | null; sharpe_ratio: number | null; beta: number | null; alpha: number | null; tracking_error: number | null;
  portfolio_turnover_ratio: number | null; stats_as_of: string | null;
  benchmark: string | null; asset_allocation: string | null; alloc_as_of: string | null; top5_holdings: string | null; top5_as_of: string | null;
  nav: number | null; nav_date: string | null; net_asset: number | null; nav_change_1y_pct: number | null;
  min_subscription: number | null; min_redemption: number | null; factsheet_pdf: string | null; amc_factsheet_url: string | null;
  data_as_of: string | null; fetched_at: string | null;
  [k: string]: string | number | null;
}

export class ApiError extends Error {
  constructor(message: string, public status: number) { super(message); }
}

async function req<T>(url: string, signal?: AbortSignal): Promise<T> {
  const r = await fetch(url, { signal });
  if (!r.ok) {
    let msg = `เกิดข้อผิดพลาด (${r.status})`;
    try {
      const j = await r.json();
      if (typeof j.detail === "string") msg = j.detail;
    } catch { /* ไม่ใช่ JSON */ }
    throw new ApiError(msg, r.status);
  }
  return r.json() as Promise<T>;
}

// โหมด static (vite --mode static): อ่านไฟล์ JSON ที่ส่งออกไว้ใน data/ แทนการเรียก API (ใช้โฮสต์ไฟล์ธรรมดาได้)
const STATIC = import.meta.env.MODE === "static";
/** ชื่อไฟล์ปลอดภัย ต้องตรงกับ safe() ใน scripts/15_export_static.py */
const safe = (s: string) => s.replace(/[^A-Za-z0-9_-]/g, (c) => "~" + c.charCodeAt(0).toString(16));
const dataUrl = (p: string) => `${import.meta.env.BASE_URL}data/${p}`;

type FundsRes = { items: Fund[]; summary: Meta["funds"]; past_performance_notice: string };
type NavRes = { series: { date: string; nav: number }[]; empty: boolean };

export const api = {
  meta: () => req<Meta>(STATIC ? dataUrl("meta.json") : "/api/meta"),
  funds: () => req<FundsRes>(STATIC ? dataUrl("funds.json") : "/api/funds"),
  fund: (projId: string) => req<{ proj_id: string; classes: Fund[] }>(STATIC ? dataUrl(`funds/${safe(projId)}.json`) : `/api/funds/${encodeURIComponent(projId)}`),
  nav: (projId: string, cls: string) =>
    req<NavRes>(STATIC ? dataUrl(`nav/${safe(projId)}__${safe(cls)}.json`) : `/api/funds/${encodeURIComponent(projId)}/nav?fund_class_name=${encodeURIComponent(cls)}`),
};
