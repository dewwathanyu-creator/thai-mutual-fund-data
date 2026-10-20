import { useMemo, useState } from "react";
import { flexRender, getCoreRowModel, getPaginationRowModel, getSortedRowModel, useReactTable, type ColumnDef, type OnChangeFn, type SortingState, type VisibilityState } from "@tanstack/react-table";
import type { Fund } from "../api";
import { dqList } from "../dq";
import { DASH, isNum, nav4, num0, num2, thaiDate } from "../format";
import { ClassBadge, SaveButton, amcShort, fundKey, nullsLast, riskText, unreliableFee } from "./fund";

export interface PickMeta { picked: string[]; toggle: (f: Fund) => void; max: number; open: (f: Fund) => void }

/** สินทรัพย์สุทธิเป็นล้านบาท (ตามที่รายงานใน NAV ล่าสุดของ class) */
export const netAssetM = (f: Fund) => (isNum(f.net_asset) ? f.net_asset / 1_000_000 : null);

export const COLUMN_LABELS: Record<string, string> = {
  amc: "AMC", type: "Tax type", risk: "Risk", policy: "Policy", size: "Net assets", ter: "TER", mgmt: "Mgmt fee",
  ytd: "YTD return", r1: "1Y return", r3: "3Y return", vol: "1Y volatility", nav: "NAV", asof: "As of",
};
export const DEFAULT_VISIBILITY: VisibilityState = { amc: true, type: true, risk: true, policy: false, size: true, ter: true, mgmt: false, ytd: false, r1: true, r3: true, vol: false, nav: true, asof: true };

const numCol = (id: string, header: string, get: (f: Fund) => number | null, fmt: (v: number | null) => string, title?: string): ColumnDef<Fund> => ({
  id, header, accessorFn: (f) => get(f) ?? undefined, sortingFn: (a, b) => nullsLast(get(a.original), get(b.original)), sortUndefined: "last",
  cell: ({ row }) => <span className="num">{fmt(get(row.original))}</span>, meta: { num: true, title },
});

/** คอลัมน์ของตารางกองทุน (ใช้ร่วมกันทั้งมุมมองตารางและมุมมองจัดกลุ่ม) */
export function useFundColumns(): ColumnDef<Fund>[] {
  return useMemo<ColumnDef<Fund>[]>(() => [
    { id: "pick", header: "Compare", enableSorting: false, enableHiding: false, cell: ({ row, table }) => {
      const m = table.options.meta as PickMeta, k = fundKey(row.original), on = m.picked.includes(k);
      return <input type="checkbox" className="h-4 w-4 accent-[var(--brand)]" aria-label={`เลือก ${row.original.proj_abbr_name} เพื่อเปรียบเทียบ`} checked={on} disabled={!on && m.picked.length >= m.max} onChange={() => m.toggle(row.original)} />;
    } },
    { id: "name", header: "Fund / Class", enableHiding: false, accessorFn: (f) => f.proj_abbr_name, cell: ({ row, table }) => {
      const f = row.original, m = table.options.meta as PickMeta;
      return (
        <button className="text-left font-semibold text-brand hover:underline" onClick={() => m.open(f)}>
          {f.proj_abbr_name}{dqList(f.dq_flags).length > 0 && <span className="ml-1 badge badge-warn" aria-label="มีข้อควรระวังเรื่องข้อมูล" title={dqList(f.dq_flags).join("\n")}>หมายเหตุ</span>}
          <span className="block text-xs font-normal text-ink2 max-w-[260px] truncate">{f.fund_class_name !== "main" ? `class ${f.fund_class_name}${f.class_detail ? ` (${f.class_detail})` : ""} · ` : ""}{f.proj_name_th}</span>
        </button>);
    } },
    { id: "amc", header: COLUMN_LABELS.amc, accessorFn: (f) => amcShort(f.comp_name_th), cell: ({ getValue }) => <span className="text-xs">{String(getValue())}</span> },
    { id: "type", header: COLUMN_LABELS.type, accessorFn: (f) => f.tax_type ?? "", cell: ({ row }) => <ClassBadge f={row.original} /> },
    { id: "risk", header: COLUMN_LABELS.risk, accessorFn: (f) => (f.risk_level === null ? undefined : f.risk_level + (f.risk_label === "8+" ? 0.5 : 0)), sortUndefined: "last",
      cell: ({ row }) => <span className="num">{row.original.risk_level === null ? DASH : `${riskText(row.original)}/8`.replace("8+/8", "8+")}</span>, meta: { num: true } },
    { id: "policy", header: COLUMN_LABELS.policy, accessorFn: (f) => f.policy_desc ?? "", cell: ({ getValue }) => <span className="text-xs">{String(getValue()) || DASH}</span> },
    numCol("size", "Net assets (THB m)", netAssetM, (v) => (v === null ? DASH : num0(v)), "สินทรัพย์สุทธิตามที่รายงานใน NAV ล่าสุด"),
    { ...numCol("ter", "TER (reported %)", (f) => f.fee_ter_actual, num2),
      sortingFn: (a, b) => nullsLast(unreliableFee(a.original) ? null : a.original.fee_ter_actual, unreliableFee(b.original) ? null : b.original.fee_ter_actual),
      cell: ({ row }) => <span className="num">{num2(row.original.fee_ter_actual)}{unreliableFee(row.original) && <span className="ml-1 badge badge-warn" title={dqList(row.original.dq_flags).join("\n")}>ตรวจสอบ</span>}</span> } as ColumnDef<Fund>,
    numCol("mgmt", "Mgmt fee (actual %)", (f) => f.fee_mgmt_actual, num2),
    numCol("ytd", "YTD return %", (f) => f.ret_ytd, num2),
    numCol("r1", "1Y return %", (f) => f.ret_1y, num2),
    numCol("r3", "3Y return %", (f) => f.ret_3y, num2),
    numCol("vol", "1Y volatility %", (f) => f.vol_1y, num2),
    numCol("nav", "NAV", (f) => f.nav, nav4),
    { id: "asof", header: COLUMN_LABELS.asof, accessorFn: (f) => f.data_as_of ?? "", cell: ({ getValue }) => <span className="text-xs num">{thaiDate(String(getValue()) || null)}</span> },
    { id: "save", header: "Save", enableSorting: false, enableHiding: false, meta: { sticky: true }, cell: ({ row }) => <SaveButton f={row.original} compact /> },
  ], []);
}

interface Props {
  data: Fund[]; columns: ColumnDef<Fund>[]; sorting: SortingState; onSortingChange: OnChangeFn<SortingState>; visibility: VisibilityState;
  meta: PickMeta; pageSize: number; pageSizeOptions?: number[]; onPageSizeChange?: (n: number) => void; footer?: "full" | "more";
}

/** ตารางข้อมูลกองทุน: เรียงตามคอลัมน์ (ควบคุมจากภายนอก) แบ่งหน้า */
export default function FundTable({ data, columns, sorting, onSortingChange, visibility, meta, pageSize, pageSizeOptions, onPageSizeChange, footer = "full" }: Props) {
  // หน้าปัจจุบันจัดการภายในตาราง ส่วนจำนวนแถวต่อหน้าถูกควบคุมจากภายนอก (ผูกกับ pageSize)
  const [pageIndex, setPageIndex] = useState(0);
  const table = useReactTable({
    data, columns, state: { sorting, columnVisibility: visibility, pagination: { pageIndex, pageSize } }, onSortingChange,
    onPaginationChange: (u) => { const next = typeof u === "function" ? u({ pageIndex, pageSize }) : u; setPageIndex(next.pageIndex); },
    getCoreRowModel: getCoreRowModel(), getSortedRowModel: getSortedRowModel(), getPaginationRowModel: getPaginationRowModel(), autoResetPageIndex: true, meta,
  });
  const s = table.getState().pagination;
  const total = data.length;

  return (
    <div>
      <div className="table-wrap">
        <table className="dt">
          <thead>{table.getHeaderGroups().map((hg) => (
            <tr key={hg.id}>{hg.headers.map((h) => {
              const sorted = h.column.getIsSorted();
              const cm = h.column.columnDef.meta as { num?: boolean; title?: string; sticky?: boolean } | undefined;
              return (
                <th key={h.id} className={`${cm?.num ? "num" : ""} ${cm?.sticky ? "sticky-r" : ""}`} title={cm?.title} aria-sort={sorted === "asc" ? "ascending" : sorted === "desc" ? "descending" : "none"}>
                  {h.column.getCanSort() ? (
                    <button className="inline-flex items-center gap-1 font-semibold" onClick={h.column.getToggleSortingHandler()} title="กดเพื่อเรียงตามคอลัมน์นี้ (กดซ้ำเพื่อสลับทิศทาง)">
                      {flexRender(h.column.columnDef.header, h.getContext())}<span aria-hidden className="text-xs">{sorted === "asc" ? "▲" : sorted === "desc" ? "▼" : "↕"}</span>
                    </button>) : flexRender(h.column.columnDef.header, h.getContext())}
                </th>);
            })}</tr>))}</thead>
          <tbody>{table.getRowModel().rows.map((r) => (
            <tr key={r.id}>{r.getVisibleCells().map((c) => <td key={c.id} className={`${(c.column.columnDef.meta as { num?: boolean } | undefined)?.num ? "num" : ""} ${(c.column.columnDef.meta as { sticky?: boolean } | undefined)?.sticky ? "sticky-r" : ""}`}>{flexRender(c.column.columnDef.cell, c.getContext())}</td>)}</tr>))}</tbody>
        </table>
      </div>
      {footer === "full" ? (
        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-4 py-3 text-sm">
          <span className="text-ink2 num">หน้า {s.pageIndex + 1} / {table.getPageCount()} · {num0(total)} รายการ</span>
          <div className="flex items-center gap-2">
            <label className="text-xs text-ink2" htmlFor="ps">แถวต่อหน้า</label>
            <select id="ps" className="input !w-20 !min-h-9" value={pageSize} onChange={(e) => onPageSizeChange?.(Number(e.target.value))}>{(pageSizeOptions ?? [25, 50, 100]).map((n) => <option key={n}>{n}</option>)}</select>
            <button className="btn !min-h-9" onClick={() => table.previousPage()} disabled={!table.getCanPreviousPage()}>ก่อนหน้า</button>
            <button className="btn !min-h-9" onClick={() => table.nextPage()} disabled={!table.getCanNextPage()}>ถัดไป</button>
          </div>
        </div>
      ) : (
        total > pageSize && (
          <div className="flex flex-wrap items-center justify-between gap-2 border-t border-line px-4 py-2 text-sm">
            <span className="text-ink2 num">แสดง {Math.min(pageSize, total)} จาก {num0(total)} รายการ</span>
            <button className="btn !min-h-8 text-xs" onClick={() => onPageSizeChange?.(Math.min(total, pageSize + 25))}>แสดงเพิ่ม</button>
          </div>
        )
      )}
    </div>
  );
}
