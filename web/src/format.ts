// จัดรูปแบบตัวเลขแบบไทย (คั่นหลักพัน บาท) ค่าที่ไม่มีข้อมูลแสดงเป็น "–" ไม่ใช่ 0

const nf0 = new Intl.NumberFormat("th-TH", { maximumFractionDigits: 0 });
const nf2 = new Intl.NumberFormat("th-TH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const nf4 = new Intl.NumberFormat("th-TH", { minimumFractionDigits: 4, maximumFractionDigits: 4 });

export const DASH = "–";
export const isNum = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);

export const baht = (v: number | null | undefined) => (isNum(v) ? `${nf0.format(Math.round(v))} บาท` : DASH);
export const num0 = (v: number | null | undefined) => (isNum(v) ? nf0.format(Math.round(v)) : DASH);
export const num2 = (v: number | null | undefined) => (isNum(v) ? nf2.format(v) : DASH);
export const nav4 = (v: number | null | undefined) => (isNum(v) ? nf4.format(v) : DASH);
export const pct = (v: number | null | undefined, digits = 2) =>
  isNum(v) ? `${v.toLocaleString("th-TH", { minimumFractionDigits: digits, maximumFractionDigits: digits })}%` : DASH;
export const pctRate = (r: number) => `${Math.round(r * 100)}%`;

const MONTHS = ["ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."];
export function thaiDate(iso: string | null | undefined): string {
  if (!iso) return DASH;
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso);
  if (!m) return iso;
  return `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]} ${Number(m[1]) + 543}`;
}

export function parseMoney(s: string): number {
  const n = Number(s.replace(/[^\d.]/g, ""));
  return Number.isFinite(n) ? n : 0;
}

export function downloadCsv(filename: string, rows: Record<string, unknown>[], columns: { key: string; label: string }[]) {
  const esc = (v: unknown) => {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const csv = [columns.map((c) => esc(c.label)).join(","), ...rows.map((r) => columns.map((c) => esc(r[c.key])).join(","))].join("\r\n");
  const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.click();
  URL.revokeObjectURL(url);
}
