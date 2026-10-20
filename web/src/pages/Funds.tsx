import { useEffect, useMemo, useState } from "react";
import type { SortingState, VisibilityState } from "@tanstack/react-table";
import { api, type Fund } from "../api";
import { CompareTable, FundDetailLoader, MAX_COMPARE, TYPE_LABEL, amcShort, fundKey, riskText, unreliableFee } from "../components/fund";
import FundTable, { COLUMN_LABELS, DEFAULT_VISIBILITY, useFundColumns, type PickMeta } from "../components/FundTable";
import { Callout, Drawer, Empty, Skeleton } from "../components/ui";
import { DASH, downloadCsv, isNum, num0, num2, thaiDate } from "../format";
import { useStore } from "../store";

/** ตัวเลือกเรียงลำดับสำเร็จรูป: ผู้ใช้เป็นผู้เลือกเอง ระบบไม่จัดอันดับให้ (รายการที่ค่าธรรมเนียมมีหมายเหตุถูกเรียงไว้ท้ายเมื่อเรียงตามค่าธรรมเนียม) */
const SORT_PRESETS: { id: string; label: string; sort: { id: string; desc: boolean } | null }[] = [
  { id: "name", label: "Fund name (A-Z)", sort: { id: "name", desc: false } },
  { id: "size", label: "Net assets (high to low)", sort: { id: "size", desc: true } },
  { id: "ter_asc", label: "TER (low to high)", sort: { id: "ter", desc: false } },
  { id: "ter_desc", label: "TER (high to low)", sort: { id: "ter", desc: true } },
  { id: "ytd", label: "YTD return (high to low)", sort: { id: "ytd", desc: true } },
  { id: "r1", label: "1Y return (high to low)", sort: { id: "r1", desc: true } },
  { id: "r3", label: "3Y return (high to low)", sort: { id: "r3", desc: true } },
  { id: "risk_asc", label: "Risk level (low to high)", sort: { id: "risk", desc: false } },
  { id: "risk_desc", label: "Risk level (high to low)", sort: { id: "risk", desc: true } },
  { id: "vol", label: "1Y volatility (low to high)", sort: { id: "vol", desc: false } },
  { id: "asof", label: "Latest data (newest first)", sort: { id: "asof", desc: true } },
];

type GroupBy = "none" | "policy" | "amc" | "risk" | "fx" | "type" | "classdetail";
const GROUPS: { id: GroupBy; label: string }[] = [
  { id: "none", label: "No grouping" }, { id: "policy", label: "Investment policy" }, { id: "amc", label: "AMC (management company)" }, { id: "risk", label: "Risk level" },
  { id: "fx", label: "FX hedging policy" }, { id: "type", label: "Tax-advantaged type (verified only)" }, { id: "classdetail", label: "Unit class type (as reported)" },
];

const policyName = (p: string | null) => (p && p.startsWith("ไม่ระบุ") ? "ไม่ระบุ (ETF แบบ leveraged/inverse)" : p);
const median = (xs: number[]) => {
  if (!xs.length) return null;
  const s = [...xs].sort((a, b) => a - b), m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
};
const countBy = (rows: Fund[], get: (f: Fund) => string | null | undefined) => {
  const m = new Map<string, number>();
  rows.forEach((r) => { const k = get(r); if (k) m.set(k, (m.get(k) ?? 0) + 1); });
  return m;
};

interface Group { key: string; label: string; rows: Fund[]; order: number }

export default function Funds() {
  const { meta } = useStore();
  const [rows, setRows] = useState<Fund[] | null>(null);
  const [notice, setNotice] = useState("");
  const [err, setErr] = useState<string | null>(null);
  // ตัวกรอง
  const [q, setQ] = useState("");
  const [types, setTypes] = useState<string[]>([]);
  const [amc, setAmc] = useState(""), [policy, setPolicy] = useState(""), [fx, setFx] = useState(""), [feeder, setFeeder] = useState("");
  const [riskMin, setRiskMin] = useState(1), [riskMax, setRiskMax] = useState(8);
  const [terMax, setTerMax] = useState(""), [retMin, setRetMin] = useState(""), [minSubMax, setMinSubMax] = useState("");
  const [showUnknownMin, setShowUnknownMin] = useState(false);
  // มุมมอง
  const [sorting, setSorting] = useState<SortingState>([{ id: "size", desc: true }]);
  const [groupBy, setGroupBy] = useState<GroupBy>("none");
  const [visibility, setVisibility] = useState<VisibilityState>(() => {
    try { const v = JSON.parse(localStorage.getItem("tfm-columns-v1") ?? "null"); return v && typeof v === "object" ? { ...DEFAULT_VISIBILITY, ...v } : DEFAULT_VISIBILITY; } catch { return DEFAULT_VISIBILITY; }
  });
  const [pageSize, setPageSize] = useState(25);
  const [groupPage, setGroupPage] = useState<Record<string, number>>({});
  const [collapsed, setCollapsed] = useState<Record<string, boolean>>({});
  const [showFilters, setShowFilters] = useState(false);
  const [picked, setPicked] = useState<string[]>([]);
  const [detail, setDetail] = useState<Fund | null>(null);
  const [compare, setCompare] = useState(false);

  useEffect(() => { api.funds().then((r) => { setRows(r.items); setNotice(r.past_performance_notice); }).catch((e: Error) => setErr(e.message)); }, []);
  useEffect(() => { try { localStorage.setItem("tfm-columns-v1", JSON.stringify(visibility)); } catch { /* ไม่เก็บก็ได้ */ } }, [visibility]);
  const columns = useFundColumns();

  const all = useMemo(() => rows ?? [], [rows]);
  const amcCounts = useMemo(() => countBy(all, (r) => amcShort(r.comp_name_th)), [all]);
  const policyCounts = useMemo(() => countBy(all, (r) => r.policy_desc), [all]);
  const fxCounts = useMemo(() => countBy(all, (r) => r.fx_policy), [all]);
  const typeCounts = useMemo(() => countBy(all, (r) => r.tax_type), [all]);
  const amcNames = useMemo(() => [...amcCounts.keys()].sort((a, b) => a.localeCompare(b, "th")), [amcCounts]);
  const topClassDetails = useMemo(() => new Set([...countBy(all, (r) => r.class_detail).entries()].sort((a, b) => b[1] - a[1]).slice(0, 10).map(([k]) => k)), [all]);

  const filtered = useMemo(() => {
    const ql = q.trim().toLowerCase();
    const ter = terMax === "" ? null : Number(terMax), rmin = retMin === "" ? null : Number(retMin), mx = minSubMax === "" ? null : Number(minSubMax);
    return all.filter((r) => {
      if (types.length && !(r.tax_type && types.includes(r.tax_type))) return false;
      if (amc && amcShort(r.comp_name_th) !== amc) return false;
      if (policy && r.policy_desc !== policy) return false;
      if (fx && r.fx_policy !== fx) return false;
      if (feeder === "yes" && !r.master_fund) return false;
      if (feeder === "no" && r.master_fund) return false;
      if ((riskMin > 1 || riskMax < 8) && (r.risk_level === null || r.risk_level < riskMin || r.risk_level > riskMax)) return false;
      if (ter !== null && (!isNum(r.fee_ter_actual) || r.fee_ter_actual > ter)) return false;
      if (rmin !== null && (!isNum(r.ret_1y) || r.ret_1y < rmin)) return false;
      if (mx !== null && (!isNum(r.min_subscription) ? !showUnknownMin : r.min_subscription > mx)) return false;
      if (ql && !`${r.proj_name_th} ${r.proj_abbr_name} ${r.fund_class_name} ${r.proj_id}`.toLowerCase().includes(ql)) return false;
      return true;
    });
  }, [all, q, types, amc, policy, fx, feeder, riskMin, riskMax, terMax, retMin, minSubMax, showUnknownMin]);

  const groups = useMemo<Group[]>(() => {
    if (groupBy === "none") return [];
    const label = (f: Fund): { label: string; order: number } => {
      switch (groupBy) {
        case "policy": return { label: policyName(f.policy_desc) ?? "ไม่ระบุ", order: 0 };
        case "amc": return { label: amcShort(f.comp_name_th), order: 0 };
        case "risk": return { label: f.risk_level === null ? "Risk level not stated" : `Risk level ${riskText(f)}`, order: f.risk_level === null ? 99 : f.risk_level + (f.risk_label === "8+" ? 0.5 : 0) };
        case "fx": return { label: f.fx_policy || "ไม่ระบุ", order: 0 };
        case "type": return { label: f.tax_type ? TYPE_LABEL[f.tax_type] : "ไม่ได้แสดงประเภท (ไม่ใช่หรือยังไม่ยืนยัน)", order: f.tax_type ? 0 : 1 };
        case "classdetail": return { label: f.class_detail ? (topClassDetails.has(f.class_detail) ? f.class_detail : "อื่น ๆ (คำอธิบายอื่น)") : "ไม่ระบุ", order: 0 };
        default: return { label: "ทั้งหมด", order: 0 };
      }
    };
    const m = new Map<string, Group>();
    filtered.forEach((f) => { const g = label(f); const cur = m.get(g.label) ?? { key: g.label, label: g.label, rows: [], order: g.order }; cur.rows.push(f); m.set(g.label, cur); });
    return [...m.values()].sort((a, b) => (groupBy === "risk" || groupBy === "type" ? a.order - b.order : b.rows.length - a.rows.length) || a.label.localeCompare(b.label, "th"));
  }, [filtered, groupBy, topClassDetails]);

  const toggle = (f: Fund) => setPicked((p) => (p.includes(fundKey(f)) ? p.filter((x) => x !== fundKey(f)) : p.length >= MAX_COMPARE ? p : [...p, fundKey(f)]));
  const meta2: PickMeta = { picked, toggle, max: MAX_COMPARE, open: setDetail };

  const currentPreset = SORT_PRESETS.find((p) => p.sort && sorting.length === 1 && sorting[0].id === p.sort.id && sorting[0].desc === p.sort.desc)?.id ?? "custom";
  const onPreset = (id: string) => { const p = SORT_PRESETS.find((x) => x.id === id); if (p?.sort) setSorting([p.sort]); };

  const chips: { label: string; clear: () => void }[] = [];
  if (q.trim()) chips.push({ label: `Search: ${q.trim()}`, clear: () => setQ("") });
  types.forEach((t) => chips.push({ label: `Type: ${t}`, clear: () => setTypes((p) => p.filter((x) => x !== t)) }));
  if (amc) chips.push({ label: `AMC: ${amc}`, clear: () => setAmc("") });
  if (policy) chips.push({ label: `Policy: ${policyName(policy)}`, clear: () => setPolicy("") });
  if (fx) chips.push({ label: `FX: ${fx}`, clear: () => setFx("") });
  if (feeder) chips.push({ label: feeder === "yes" ? "ลงทุนผ่านกองทุนหลัก" : "ไม่ได้ลงทุนผ่านกองทุนหลัก", clear: () => setFeeder("") });
  if (riskMin > 1 || riskMax < 8) chips.push({ label: `Risk ${riskMin}–${riskMax}`, clear: () => { setRiskMin(1); setRiskMax(8); } });
  if (terMax) chips.push({ label: `TER ≤ ${terMax}%`, clear: () => setTerMax("") });
  if (retMin) chips.push({ label: `1Y return ≥ ${retMin}%`, clear: () => setRetMin("") });
  if (minSubMax) chips.push({ label: `Min. investment ≤ ${num0(Number(minSubMax))} THB`, clear: () => setMinSubMax("") });
  const reset = () => { setQ(""); setTypes([]); setAmc(""); setPolicy(""); setFx(""); setFeeder(""); setRiskMin(1); setRiskMax(8); setTerMax(""); setRetMin(""); setMinSubMax(""); setShowUnknownMin(false); };

  const exportCsv = () => downloadCsv("funds_filtered.csv", filtered as unknown as Record<string, unknown>[], [
    { key: "proj_id", label: "รหัสโครงการ" }, { key: "fund_class_name", label: "class" }, { key: "proj_abbr_name", label: "ชื่อย่อ" }, { key: "proj_name_th", label: "ชื่อกองทุน" },
    { key: "comp_name_th", label: "บริษัทจัดการ" }, { key: "tax_type", label: "ประเภทลดหย่อนภาษีที่ยืนยันแล้ว" }, { key: "class_detail", label: "ลักษณะของ class (ตามที่ บลจ. รายงาน)" }, { key: "policy_desc", label: "นโยบายลงทุน" },
    { key: "fx_policy", label: "นโยบายป้องกันความเสี่ยงอัตราแลกเปลี่ยน" }, { key: "master_fund", label: "กองทุนหลัก (ถ้ามี)" }, { key: "risk_level", label: "ความเสี่ยง (1-8)" }, { key: "net_asset", label: "สินทรัพย์สุทธิ (บาท)" },
    { key: "fee_mgmt_actual", label: "ค่าจัดการเก็บจริง %" }, { key: "fee_ter_actual", label: "ค่าธรรมเนียมรวมที่รายงาน %" }, { key: "ret_ytd", label: "ผลตอบแทนต้นปี %" }, { key: "ret_1y", label: "ผลตอบแทน 1 ปี %" },
    { key: "ret_3y", label: "ผลตอบแทน 3 ปี %" }, { key: "vol_1y", label: "ความผันผวน 1 ปี %" }, { key: "nav", label: "NAV" }, { key: "nav_date", label: "วันที่ NAV" }, { key: "data_as_of", label: "ข้อมูล ณ" }, { key: "dq_flags", label: "ธงตรวจข้อมูล" },
  ]);

  if (err) return <Callout tone="danger" title="ไม่สามารถโหลดข้อมูลกองทุนได้">{err}</Callout>;
  if (!rows) return <div className="space-y-3" aria-busy><Skeleton h={30} w={240} /><Skeleton h={120} /><Skeleton h={420} /></div>;
  const pickedFunds = picked.map((k) => rows.find((r) => fundKey(r) === k)).filter(Boolean) as Fund[];

  const lab = (htmlFor: string, text: string) => <label htmlFor={htmlFor} className="block text-xs font-medium text-ink2 mb-1">{text}</label>;
  const filtersPanel = (
    <form className="space-y-4" onSubmit={(e) => e.preventDefault()} aria-label="ตัวกรองกองทุน">
      <div>{lab("q", "Search (name, ticker or project ID)")}<input id="q" className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder="เช่น K-ESG หรือ M0844" /></div>
      <fieldset><legend className="block text-xs font-medium text-ink2 mb-1">Tax-advantaged type (verified only)</legend>
        <div className="flex flex-wrap gap-2">{(["RMF", "SSF", "ThaiESG"] as const).filter((t) => typeCounts.has(t)).map((t) => (
          <label key={t} className={`btn !min-h-8 !py-0.5 !px-2.5 text-xs cursor-pointer ${types.includes(t) ? "!bg-brandsoft !border-brand !text-brand" : ""}`}>
            <input type="checkbox" className="sr-only" checked={types.includes(t)} onChange={() => setTypes((p) => (p.includes(t) ? p.filter((x) => x !== t) : [...p, t]))} />{t} ({num0(typeCounts.get(t))})
          </label>))}</div>
        <p className="mt-1 text-xs text-ink3">กองทุนที่ยังไม่ได้ยืนยันประเภท (รวมถึง ThaiESGX) ไม่ปรากฏในตัวกรองนี้ ค้นหาด้วยชื่อแทนได้</p></fieldset>
      <div>{lab("amc", "AMC (management company)")}<select id="amc" className="input" value={amc} onChange={(e) => setAmc(e.target.value)}><option value="">ทั้งหมด</option>{amcNames.map((a) => <option key={a} value={a}>{a} ({num0(amcCounts.get(a))})</option>)}</select></div>
      <div>{lab("pol", "Investment policy")}<select id="pol" className="input" value={policy} onChange={(e) => setPolicy(e.target.value)}><option value="">ทั้งหมด</option>{[...policyCounts.entries()].sort((a, b) => b[1] - a[1]).map(([p, n]) => <option key={p} value={p}>{policyName(p)} ({num0(n)})</option>)}</select></div>
      <div>{lab("fx", "FX hedging policy")}<select id="fx" className="input" value={fx} onChange={(e) => setFx(e.target.value)}><option value="">ทั้งหมด</option>{[...fxCounts.entries()].sort((a, b) => b[1] - a[1]).map(([p, n]) => <option key={p} value={p}>{p} ({num0(n)})</option>)}</select></div>
      <div>{lab("fd", "Feeder fund")}<select id="fd" className="input" value={feeder} onChange={(e) => setFeeder(e.target.value)}><option value="">ทั้งหมด</option><option value="yes">ลงทุนผ่านกองทุนหลัก</option><option value="no">ไม่ได้ลงทุนผ่านกองทุนหลัก</option></select></div>
      <div className="grid grid-cols-2 gap-2"><div>{lab("r1", "Risk level from (1–8)")}<select id="r1" className="input" value={riskMin} onChange={(e) => setRiskMin(Number(e.target.value))}>{[1, 2, 3, 4, 5, 6, 7, 8].map((n) => <option key={n}>{n}</option>)}</select></div>
        <div>{lab("r2", "to")}<select id="r2" className="input" value={riskMax} onChange={(e) => setRiskMax(Number(e.target.value))}>{[1, 2, 3, 4, 5, 6, 7, 8].map((n) => <option key={n}>{n}</option>)}</select></div></div>
      <div>{lab("ter", "TER, max (% per year)")}<input id="ter" className="input num" inputMode="decimal" value={terMax} onChange={(e) => setTerMax(e.target.value.replace(/[^\d.]/g, ""))} placeholder="เช่น 1.5" /></div>
      <div>{lab("ret", "1Y return, min (%)")}<input id="ret" className="input num" inputMode="decimal" value={retMin} onChange={(e) => setRetMin(e.target.value.replace(/[^\d.-]/g, ""))} placeholder="เช่น 5" /></div>
      <div>{lab("mins", "Min. investment, max (THB)")}<input id="mins" className="input num" inputMode="numeric" value={minSubMax} onChange={(e) => setMinSubMax(e.target.value.replace(/[^\d]/g, ""))} placeholder="เช่น 1000" />
        {minSubMax !== "" && <label className="mt-2 flex items-start gap-2 text-xs text-ink2"><input type="checkbox" className="mt-0.5 h-4 w-4 accent-[var(--brand)]" checked={showUnknownMin} onChange={(e) => setShowUnknownMin(e.target.checked)} /><span>รวมกองทุนที่ไม่มีข้อมูลการลงทุนขั้นต่ำ (โดยปกติไม่แสดง เนื่องจากตรวจสอบเกณฑ์ไม่ได้)</span></label>}</div>
      <button type="button" className="btn w-full" onClick={reset}>ล้างตัวกรองทั้งหมด</button>
    </form>
  );

  const groupStats = (g: Group) => {
    const fee = median(g.rows.filter((r) => isNum(r.fee_ter_actual) && !unreliableFee(r)).map((r) => r.fee_ter_actual as number));
    const r1 = median(g.rows.filter((r) => isNum(r.ret_1y)).map((r) => r.ret_1y as number));
    return `Median TER ${fee === null ? DASH : `${num2(fee)}%`} · Median 1Y return ${r1 === null ? DASH : `${num2(r1)}%`}`;
  };

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Fund Explorer</h1>
        <p className="text-sm text-ink2 mt-1">ค้นหา กรอง เรียง จัดกลุ่ม และเปรียบเทียบข้อมูลกองทุนรวมตามเกณฑ์ที่ผู้ใช้เลือก · ระบบไม่จัดอันดับหรือให้คะแนนกองทุน · ข้อมูลล่าสุด ณ วันที่ {thaiDate(meta?.funds.data_as_of_latest)} (บางกองทุนมีข้อมูลเก่ากว่านี้ ดูคอลัมน์ &ldquo;ข้อมูล ณ&rdquo;)</p>
      </div>

      <div className="lg:grid lg:grid-cols-[290px_minmax(0,1fr)] lg:gap-5 lg:items-start">
        <aside className="mb-4 lg:mb-0 lg:sticky lg:top-3">
          <div className="lg:hidden"><button className="btn w-full" aria-expanded={showFilters} onClick={() => setShowFilters((v) => !v)}>{showFilters ? "ซ่อนตัวกรอง" : `แสดงตัวกรอง${chips.length ? ` (${chips.length})` : ""}`}</button></div>
          <div className={`card p-4 mt-3 lg:mt-0 lg:max-h-[calc(100vh-1.5rem)] lg:overflow-y-auto ${showFilters ? "" : "hidden lg:block"}`}>{filtersPanel}</div>
        </aside>

        <div className="space-y-3 min-w-0">
          <div className="card p-3 flex flex-wrap items-end justify-between gap-3">
            <span className="text-sm text-ink2" aria-live="polite">แสดง <b className="num text-ink">{num0(filtered.length)}</b> จาก {num0(rows.length)} class</span>
            <div className="flex flex-wrap items-end gap-3">
              <div><label htmlFor="sort" className="block text-xs text-ink2 mb-1">Sort by</label>
                <select id="sort" className="input !min-h-9 !w-64 max-w-full" value={currentPreset} onChange={(e) => onPreset(e.target.value)}>
                  {currentPreset === "custom" && <option value="custom">Custom (column header)</option>}
                  {SORT_PRESETS.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}</select></div>
              <div><label htmlFor="group" className="block text-xs text-ink2 mb-1">Group by</label>
                <select id="group" className="input !min-h-9 !w-64 max-w-full" value={groupBy} onChange={(e) => { setGroupBy(e.target.value as GroupBy); setGroupPage({}); setCollapsed({}); }}>{GROUPS.map((g) => <option key={g.id} value={g.id}>{g.label}</option>)}</select></div>
              <details className="relative">
                <summary className="btn !min-h-9 cursor-pointer list-none">Columns</summary>
                <div className="absolute right-0 z-20 mt-1 w-60 rounded-lg border border-line bg-surface p-3 shadow-lg">
                  {Object.entries(COLUMN_LABELS).map(([id, label]) => (
                    <label key={id} className="flex items-center gap-2 py-1 text-sm"><input type="checkbox" className="h-4 w-4 accent-[var(--brand)]" checked={visibility[id] !== false} onChange={(e) => setVisibility((v) => ({ ...v, [id]: e.target.checked }))} />{label}</label>))}
                  <button className="btn !min-h-8 mt-2 w-full text-xs" onClick={() => setVisibility(DEFAULT_VISIBILITY)}>กลับค่าเริ่มต้น</button>
                </div>
              </details>
              <button type="button" className="btn !min-h-9" onClick={exportCsv} disabled={!filtered.length}>Export CSV</button>
            </div>
          </div>

          {chips.length > 0 && (
            <div className="flex flex-wrap items-center gap-2" aria-label="ตัวกรองที่ใช้อยู่">
              {chips.map((c) => <button key={c.label} className="badge badge-partial !text-xs" onClick={c.clear} title="กดเพื่อนำตัวกรองนี้ออก">{c.label} ×</button>)}
              <button className="text-xs text-brand underline" onClick={reset}>ล้างทั้งหมด</button>
            </div>)}

          <div className="flex flex-wrap items-center justify-between gap-2 no-print">
            <p className="text-sm text-ink2">เลือกเปรียบเทียบได้สูงสุด {MAX_COMPARE} กองทุน (เลือกแล้ว {picked.length}) · ปุ่ม &ldquo;บันทึก&rdquo; เก็บกองทุนไว้ในหน้า &ldquo;รายการที่บันทึก&rdquo;</p>
            <div className="flex gap-2">{picked.length > 0 && <button className="btn" onClick={() => setPicked([])}>ล้างการเลือก</button>}<button className="btn btn-primary" disabled={picked.length < 2} onClick={() => setCompare(true)}>เปรียบเทียบ {picked.length >= 2 ? `(${picked.length})` : ""}</button></div>
          </div>

          {filtered.length === 0 ? <Empty title="ไม่พบกองทุนที่ตรงตามเกณฑ์">กรุณาปรับเกณฑ์ เช่น ขยายช่วงระดับความเสี่ยง หรือยกเลิกตัวกรองค่าธรรมเนียมและผลตอบแทน <button className="ml-2 text-brand underline" onClick={reset}>ล้างตัวกรอง</button></Empty> : groupBy === "none" ? (
            <div className="card overflow-hidden">
              <FundTable data={filtered} columns={columns} sorting={sorting} onSortingChange={setSorting} visibility={visibility} meta={meta2} pageSize={pageSize} onPageSizeChange={setPageSize} />
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-xs text-ink3">แสดง {num0(groups.length)} กลุ่ม ค่ากลางของแต่ละกลุ่มคำนวณจาก class ที่มีข้อมูลเท่านั้น (ไม่รวมรายการที่ค่าธรรมเนียมมีหมายเหตุ) เป็นข้อมูลประกอบ มิใช่เกณฑ์ตัดสินว่าดีหรือไม่ดี การเรียงในแต่ละกลุ่มเป็นไปตามตัวเลือก &ldquo;เรียงตาม&rdquo;</p>
              {groups.map((g) => {
                const open = !collapsed[g.key];
                const size = groupPage[g.key] ?? 10;
                return (
                  <section key={g.key} className="card overflow-hidden">
                    <button className="flex w-full flex-wrap items-center justify-between gap-2 bg-surface2 px-4 py-3 text-left" aria-expanded={open} onClick={() => setCollapsed((c) => ({ ...c, [g.key]: open }))}>
                      <span className="font-semibold">{g.label} <span className="font-normal text-ink2 num">({num0(g.rows.length)} class)</span></span>
                      <span className="text-xs text-ink2">{groupStats(g)} · {open ? "ซ่อน" : "แสดง"}</span>
                    </button>
                    {open && <FundTable data={g.rows} columns={columns} sorting={sorting} onSortingChange={setSorting} visibility={visibility} meta={meta2} pageSize={size} onPageSizeChange={(n) => setGroupPage((p) => ({ ...p, [g.key]: n }))} footer="more" />}
                  </section>);
              })}
            </div>
          )}
        </div>
      </div>

      <Callout tone="warn" title="Before using this data">
        ตัวเลขทั้งหมดมาจาก SEC Open API ตามที่บริษัทจัดการรายงานไว้ ช่องที่แสดงเป็น &ldquo;{DASH}&rdquo; คือไม่มีข้อมูล ไม่ได้แปลว่าเป็นศูนย์ และเมื่อตั้งตัวกรองค่าธรรมเนียมหรือผลตอบแทน กองทุนที่ไม่มีข้อมูลช่องนั้นจะไม่ถูกนับในผลลัพธ์ {notice}
      </Callout>

      <Drawer open={detail !== null} onClose={() => setDetail(null)} wide title={detail ? `${detail.proj_abbr_name}${detail.fund_class_name !== "main" ? ` · ${detail.fund_class_name}` : ""}` : ""}>
        {detail && <FundDetailLoader f={detail} notice={notice} />}
      </Drawer>
      <Drawer open={compare} onClose={() => setCompare(false)} wide title="Compare funds">
        <CompareTable funds={pickedFunds} notice={notice} />
      </Drawer>
    </div>
  );
}
