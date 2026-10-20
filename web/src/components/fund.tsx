import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, type Fund } from "../api";
import { VAT_NOTE, dqList } from "../dq";
import { DASH, isNum, nav4, num0, num2, pct, thaiDate } from "../format";
import { useStore } from "../store";
import { Callout, Skeleton } from "./ui";

export const TYPE_LABEL: Record<string, string> = { RMF: "RMF", SSF: "SSF (สิทธิซื้อใหม่สิ้นสุด)", ThaiESG: "ThaiESG", ThaiESGX: "ThaiESGX" };
export const riskText = (f: Fund) => (f.risk_label ? f.risk_label : f.risk_level !== null ? String(f.risk_level) : DASH);
export const fundKey = (f: Fund) => `${f.proj_id}|${f.fund_class_name}`;
export const amcShort = (s: string) => s.replace(/^บริษัทหลักทรัพย์จัดการกองทุน\s*/, "").replace(/\s*จำกัด$/, "").trim();
export const unreliableFee = (f: Fund) => ["fee_ter_zero", "ter_lt_mgmt", "fee_out_of_range"].some((flag) => f.dq_flags?.split(";").includes(flag));
export const nullsLast = (a: unknown, b: unknown) => {
  const x = isNum(a) ? a : null, y = isNum(b) ? b : null;
  if (x === null && y === null) return 0;
  if (x === null) return 1;
  if (y === null) return -1;
  return x - y;
};

/** ป้ายประเภทกองทุนเพื่อการลดหย่อนภาษี แสดงเฉพาะประเภทที่แน่ใจแล้ว (API ไม่ส่งประเภทที่ยังไม่ยืนยันมา) */
export function ClassBadge({ f }: { f: Fund }) {
  if (!f.tax_type) return <span className="text-ink3">{DASH}</span>;
  return (
    <span className="badge badge-ok" title={`ที่มาของประเภท: ${f.classified_by === "field+name" ? "ข้อมูลประเภทที่ ก.ล.ต. ระบุ" : "รายงานหรือเอกสารของ ก.ล.ต."}`}>
      {TYPE_LABEL[f.tax_type]}
    </span>
  );
}

/** ปุ่มบันทึกกองทุนไว้ในรายการของผู้ใช้ (เก็บในเบราว์เซอร์นี้เท่านั้น) */
export function SaveButton({ f, compact }: { f: Fund; compact?: boolean }) {
  const { isSaved, toggleSaved } = useStore();
  const on = isSaved(fundKey(f));
  return (
    <button type="button" className={`btn !min-h-8 !px-2.5 text-xs ${on ? "!bg-brandsoft !border-brand !text-brand" : ""}`} aria-pressed={on}
      aria-label={`${on ? "นำออกจากรายการที่บันทึก" : "บันทึกลงรายการ"} ${f.proj_abbr_name}`} onClick={() => toggleSaved(fundKey(f))}>
      {on ? (compact ? "บันทึกแล้ว" : "บันทึกแล้ว (กดเพื่อนำออก)") : (compact ? "บันทึก" : "บันทึกลงรายการ")}
    </button>
  );
}

function parseList(s: string | null): { name: string; ratio: number | null }[] {
  if (!s) return [];
  return s.split("; ").map((p) => {
    const m = /^(.*) (-?[\d.]+)%$/.exec(p);
    return m ? { name: m[1], ratio: Number(m[2]) } : { name: p, ratio: null };
  });
}

function NavChart({ f }: { f: Fund }) {
  const [state, setState] = useState<"loading" | "error" | "empty" | { date: string; nav: number }[]>("loading");
  useEffect(() => {
    let live = true;
    setState("loading");
    api.nav(f.proj_id, f.fund_class_name).then((r) => { if (live) setState(r.empty ? "empty" : r.series); }).catch(() => live && setState("error"));
    return () => { live = false; };
  }, [f.proj_id, f.fund_class_name]);
  if (state === "loading") return <Skeleton h={220} />;
  if (state === "error") return <Callout tone="danger">โหลดข้อมูล NAV ไม่สำเร็จ</Callout>;
  if (state === "empty") return <p className="text-sm text-ink2 rounded-lg bg-surface2 p-4">ไม่มีข้อมูล NAV ของ class นี้ในชุดข้อมูลที่ใช้</p>;
  return (
    <div className="h-56" role="img" aria-label="กราฟ NAV ย้อนหลัง 1 ปี">
      <ResponsiveContainer>
        <LineChart data={state} margin={{ top: 8, right: 12, bottom: 4, left: 4 }}>
          <CartesianGrid stroke="var(--line)" strokeDasharray="3 3" />
          <XAxis dataKey="date" tickFormatter={(d: string) => thaiDate(d).replace(/ \d{4}$/, "")} minTickGap={40} stroke="var(--ink-3)" fontSize={11} />
          <YAxis domain={["auto", "auto"]} tickFormatter={(v: number) => v.toFixed(2)} stroke="var(--ink-3)" fontSize={11} width={52} />
          <Tooltip contentStyle={{ background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 8 }} formatter={(v) => [nav4(Number(v)), "NAV"]} labelFormatter={(l) => thaiDate(String(l))} />
          <Line type="monotone" dataKey="nav" stroke="var(--brand)" strokeWidth={2} dot={false} isAnimationActive={false} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function SiblingClasses({ f, siblings }: { f: Fund; siblings: Fund[] }) {
  const rows = [...siblings].sort((a, b) => a.fund_class_name.localeCompare(b.fund_class_name));
  return (
    <section><h3 className="font-semibold mb-2">Other classes of this fund ({rows.length} class)</h3>
      <div className="table-wrap"><table className="dt">
        <thead><tr><th>class</th><th>ลักษณะของ class</th><th className="num">ค่าธรรมเนียมรวม รายงาน %</th><th className="num">ค่าจัดการ เก็บจริง %</th><th className="num">ค่าขาย (Front-end) สูงสุด %</th><th className="num">ลงทุนขั้นต่ำ (บาท)</th><th className="num">ผลตอบแทน 1 ปี %</th><th className="num">NAV</th></tr></thead>
        <tbody>{rows.map((c) => (
          <tr key={c.fund_class_name} className={c.fund_class_name === f.fund_class_name ? "bg-brandsoft" : ""}>
            <td className="font-medium">{c.fund_class_name}{c.fund_class_name === f.fund_class_name ? " (class นี้)" : ""}{dqList(c.dq_flags).length > 0 && <span className="ml-1 badge badge-warn" title={dqList(c.dq_flags).join("\n")}>หมายเหตุ</span>}</td>
            <td className="text-xs">{c.class_detail || DASH}</td>
            <td className="num">{num2(c.fee_ter_actual)}</td><td className="num">{num2(c.fee_mgmt_actual)}</td><td className="num">{num2(c.fee_front_max)}</td>
            <td className="num">{num0(c.min_subscription)}</td><td className="num">{num2(c.ret_1y)}</td><td className="num">{nav4(c.nav)}</td></tr>))}</tbody></table></div>
      <p className="mt-1 text-xs text-ink3">แต่ละ class ของกองทุนเดียวกันอาจแตกต่างกันที่ช่องทางจำหน่าย กลุ่มผู้ลงทุน และค่าธรรมเนียม ข้อความในคอลัมน์ &ldquo;ลักษณะของ class&rdquo; เป็นคำอธิบายที่ บริษัทจัดการรายงานต่อ ก.ล.ต. ผู้ลงทุนควรอ่านเงื่อนไขการซื้อของแต่ละ class จากหนังสือชี้ชวนก่อนตัดสินใจ เครื่องหมาย (–) หมายถึงไม่มีข้อมูลจาก ก.ล.ต. มิได้หมายถึงศูนย์ ตารางนี้ไม่ได้จัดอันดับ class</p>
    </section>
  );
}

function FundDetail({ f, notice, siblings }: { f: Fund; notice: string; siblings: Fund[] }) {
  const alloc = parseList(f.asset_allocation), top5 = parseList(f.top5_holdings);
  const feeRows: [string, number | null, number | null][] = [
    ["ค่าธรรมเนียมการจัดการ", f.fee_mgmt_max, f.fee_mgmt_actual], ["ค่าธรรมเนียมและค่าใช้จ่ายรวมทั้งหมด", f.fee_ter_max, f.fee_ter_actual],
    ["ค่าธรรมเนียมการขาย (Front-end)", f.fee_front_max, f.fee_front_actual], ["ค่าธรรมเนียมการรับซื้อคืน (Back-end)", f.fee_back_max, f.fee_back_actual],
    ["สับเปลี่ยนเข้า", f.fee_switch_in_max, null], ["สับเปลี่ยนออก (บาท/อัตรา ตามที่ ก.ล.ต. รายงาน)", f.fee_switch_out_max, null],
  ];
  const perf: [string, string][] = [["3 เดือน", "3m"], ["6 เดือน", "6m"], ["ตั้งแต่ต้นปี", "ytd"], ["1 ปี", "1y"], ["3 ปี", "3y"], ["5 ปี", "5y"], ["10 ปี", "10y"], ["ตั้งแต่จัดตั้ง", "inception"]];
  return (
    <div className="space-y-6 text-sm">
      <div>
        <div className="flex flex-wrap gap-2 items-center"><ClassBadge f={f} /><span className="badge badge-muted">{f.fund_status}</span>{f.policy_desc && <span className="badge badge-muted">{f.policy_desc}</span>}{f.risk_level && <span className="badge badge-warn">ความเสี่ยง {riskText(f)}{f.risk_label === "8+" ? " (สูงกว่าระดับ 8)" : "/8"}</span>}<SaveButton f={f} /></div>
        <p className="mt-2 text-ink2">{f.proj_name_th}</p>
        <p className="text-xs text-ink3">{f.comp_name_th} · รหัสโครงการ {f.proj_id} · class {f.fund_class_name}{f.class_detail ? ` · ${f.class_detail}` : ""}</p>
      </div>
      {f.tax_type ? (
        <Callout tone="info" title="ประเภทกองทุนเพื่อการลดหย่อนภาษี">
          {f.tax_type === "SSF" ? "SSF" : f.tax_type} ตามข้อมูลของ ก.ล.ต. ระบบนี้แสดงเฉพาะข้อมูลกองทุน มิได้คำนวณสิทธิประโยชน์ทางภาษี ผู้ลงทุนควรตรวจสอบสิทธิและเงื่อนไขจากหนังสือชี้ชวนและประกาศของกรมสรรพากรก่อนตัดสินใจ
          {f.tax_type === "SSF" && <p className="mt-2">สิทธิยกเว้นภาษีสำหรับค่าซื้อหน่วยลงทุน SSF สิ้นสุดที่เงินได้ปีภาษี 2567 ตามกฎกระทรวง ฉบับที่ 357 (พ.ศ. 2563) การแสดงข้อมูลกองทุน SSF ในหน้านี้เป็นข้อมูลกองทุนเท่านั้น</p>}
        </Callout>
      ) : null}
      {f.class_match === "unmatched" && <Callout tone="warn" title="ข้อมูลระดับ class ไม่ครบ">ชื่อ class ในข้อมูลรายละเอียดจาก ก.ล.ต. ไม่ตรงกับ class นี้ ระบบจึงเว้นข้อมูลระดับ class (ค่าธรรมเนียม ผลตอบแทน NAV และอื่น ๆ) ไว้ และไม่ใช้ข้อมูลของ class อื่นแทน</Callout>}
      {f.class_match === "class_absent" && <Callout tone="warn" title="ไม่มีข้อมูลระดับ class">SEC Open API ไม่มีข้อมูลค่าธรรมเนียม ผลตอบแทน หรือ NAV ของ class นี้ (อาจเป็น class ที่ยังไม่มีการซื้อขายหรือยังไม่ได้รายงาน) ข้อมูลระดับ class จึงเว้นว่างไว้ ส่วนระดับความเสี่ยงและการจัดสรรสินทรัพย์เป็นข้อมูลระดับกองทุน</Callout>}

      {dqList(f.dq_flags).length > 0 && (
        <Callout tone="warn" title="ข้อควรระวังเรื่องข้อมูลของ class นี้">
          <ul className="list-disc pl-5 space-y-1">{dqList(f.dq_flags).map((t) => <li key={t}>{t}</li>)}</ul>
          <p className="mt-1 text-xs">เป็นข้อควรระวังจากการตรวจความสมเหตุสมผลของข้อมูล ระบบไม่ได้แก้ไขตัวเลข ตัวเลขที่แสดงเป็นไปตามที่ บลจ. รายงานต่อ ก.ล.ต. ควรตรวจสอบกับ Fact Sheet ก่อนนำไปใช้</p>
        </Callout>
      )}

      <section><h3 className="font-semibold mb-2">NAV, last 1 year</h3>
        <NavChart f={f} />
        <p className="text-xs text-ink3 mt-1 num">NAV ล่าสุด {nav4(f.nav)} ณ {thaiDate(f.nav_date)} · มูลค่าทรัพย์สินสุทธิ {num0(f.net_asset)} บาท · เปลี่ยนแปลง 1 ปี {pct(f.nav_change_1y_pct)}</p>
      </section>

      <section><h3 className="font-semibold mb-2">Performance (%) <span className="font-normal text-xs text-ink3">ข้อมูล ณ {thaiDate(f.perf_as_of)}</span></h3>
        <div className="table-wrap"><table className="dt"><thead><tr><th>ช่วง</th><th className="num">กองทุน</th><th className="num">ตัวชี้วัด</th><th className="num">ค่าเฉลี่ยกลุ่ม</th><th className="num">ความผันผวน</th></tr></thead>
          <tbody>{perf.map(([l, k]) => <tr key={k}><td>{l}</td><td className="num">{num2(f[`ret_${k}`] as number | null)}</td><td className="num">{num2(f[`bench_ret_${k}`] as number | null)}</td><td className="num">{num2(f[`peer_ret_${k}`] as number | null)}</td><td className="num">{num2(f[`vol_${k}`] as number | null)}</td></tr>)}</tbody></table></div>
        <p className="mt-1 text-xs text-warn">{notice} (ยังไม่ได้ยืนยันว่าผลตอบแทนช่วงเกิน 1 ปีที่ ก.ล.ต. รายงานเป็นอัตราต่อปีหรือไม่)</p>
      </section>

      {siblings.length > 1 && <SiblingClasses f={f} siblings={siblings} />}

      <section><h3 className="font-semibold mb-2">Fees (% of NAV per year unless stated) <span className="font-normal text-xs text-ink3">ข้อมูล ณ {thaiDate(f.fees_as_of)}</span></h3>
        <div className="table-wrap"><table className="dt"><thead><tr><th>รายการ</th><th className="num">สูงสุดตามโครงการ</th><th className="num">เก็บจริง</th></tr></thead>
          <tbody>{feeRows.map(([l, mx, ac]) => <tr key={l}><td>{l}</td><td className="num">{num2(mx)}</td><td className="num">{num2(ac)}</td></tr>)}</tbody></table></div>
        <p className="mt-1 text-xs text-ink3">{VAT_NOTE}</p>
      </section>

      <section><h3 className="font-semibold mb-2">Risk statistics <span className="font-normal text-xs text-ink3">ข้อมูล ณ {thaiDate(f.stats_as_of)}</span></h3>
        <dl className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {[["Max drawdown (%)", num2(f.maximum_drawdown)], ["Sharpe ratio", num2(f.sharpe_ratio)], ["Beta", num2(f.beta)], ["Alpha", num2(f.alpha)], ["Tracking error", num2(f.tracking_error)], ["อัตราหมุนเวียนพอร์ต (เท่า)", num2(f.portfolio_turnover_ratio)]].map(([k, v]) => (
            <div key={k} className="rounded-lg bg-surface2 p-3"><dt className="text-xs text-ink2">{k}</dt><dd className="num font-semibold">{v}</dd></div>))}
        </dl>
        {f.risk_spectrum_desc && <p className="mt-2 text-xs text-ink2">ระดับความเสี่ยง {f.risk_spectrum}: {f.risk_spectrum_desc} (ข้อมูล ณ {thaiDate(f.risk_as_of)})</p>}
      </section>

      {alloc.length > 0 && (
        <section><h3 className="font-semibold mb-2">Asset allocation <span className="font-normal text-xs text-ink3">ณ {thaiDate(f.alloc_as_of)} · ชื่อประเภทสินทรัพย์ตามที่ บลจ. รายงาน</span></h3>
          <ul className="space-y-1.5">{alloc.map((a) => (
            <li key={a.name} className="grid grid-cols-[1fr_58px] gap-3 items-center"><span className="min-w-0"><span className="block truncate">{a.name}</span><span className="block h-2 rounded-full bg-[var(--bar-track)] overflow-hidden"><span className="block h-full" style={{ width: `${Math.min(100, a.ratio ?? 0)}%`, background: "var(--bar-before)" }} /></span></span><span className="num text-right">{pct(a.ratio, 1)}</span></li>))}</ul></section>
      )}
      {top5.length > 0 && (
        <section><h3 className="font-semibold mb-2">Top 5 holdings <span className="font-normal text-xs text-ink3">ณ {thaiDate(f.top5_as_of)}</span></h3>
          <ol className="list-decimal pl-5 space-y-1">{top5.map((a) => <li key={a.name}>{a.name} <span className="num text-ink2">{pct(a.ratio, 2)}</span></li>)}</ol></section>
      )}
      {f.benchmark && <section><h3 className="font-semibold mb-1">Benchmark</h3><p className="text-ink2">{f.benchmark}</p></section>}
      <section><h3 className="font-semibold mb-1">Documents</h3>
        <ul className="space-y-1">
          {f.factsheet_pdf ? <li><a href={f.factsheet_pdf} target="_blank" rel="noreferrer">Fund Fact Sheet (PDF จาก ก.ล.ต.)</a></li> : <li className="text-ink3">ไม่มีลิงก์ Fact Sheet ในข้อมูล</li>}
          {f.amc_factsheet_url && <li><a href={f.amc_factsheet_url} target="_blank" rel="noreferrer">เว็บไซต์บริษัทจัดการกองทุน</a></li>}
        </ul>
        <p className="mt-2 text-xs text-ink3 num">ลงทุนขั้นต่ำ {isNum(f.min_subscription) ? `${num0(f.min_subscription)} บาท` : DASH}{f.min_sub_note ? ` (${f.min_sub_note})` : ""} · ข้อมูล ณ {thaiDate(f.data_as_of)}</p>
      </section>
    </div>
  );
}

/** โหลดข้อมูลเต็มของกองทุนจาก API ตาม class ที่เลือก แล้วแสดงรายละเอียด (รายการแบบย่อไม่มีข้อมูลครบทุกช่อง) */
export function FundDetailLoader({ f, notice }: { f: Fund; notice: string }) {
  const [full, setFull] = useState<{ f: Fund; all: Fund[] } | "loading" | "error">("loading");
  useEffect(() => {
    let live = true;
    setFull("loading");
    api.fund(f.proj_id).then((r) => { const hit = r.classes.find((c) => c.fund_class_name === f.fund_class_name); if (live) setFull(hit ? { f: hit, all: r.classes } : "error"); }).catch(() => live && setFull("error"));
    return () => { live = false; };
  }, [f.proj_id, f.fund_class_name]);
  if (full === "loading") return <div className="space-y-3" aria-busy><Skeleton h={24} w={260} /><Skeleton h={180} /><Skeleton h={240} /></div>;
  if (full === "error") return <Callout tone="danger">โหลดรายละเอียดกองทุนไม่สำเร็จ</Callout>;
  return <FundDetail f={full.f} notice={notice} siblings={full.all} />;
}

const METRICS: [string, (f: Fund) => string][] = [
  ["ประเภทกองทุนเพื่อการลดหย่อนภาษี (ตามข้อมูล ก.ล.ต./ชื่อกอง)", (f) => (f.tax_type ? TYPE_LABEL[f.tax_type] : DASH)],
  ["ลักษณะของ class (ตามที่ บลจ. รายงาน)", (f) => f.class_detail || DASH],
  ["บริษัทจัดการ", (f) => amcShort(f.comp_name_th)],
  ["นโยบายการลงทุน", (f) => f.policy_desc ?? DASH], ["ระดับความเสี่ยง (1–8, 8+ = สูงกว่า 8)", (f) => riskText(f)],
  ["ค่าธรรมเนียมการจัดการ เก็บจริง (%)", (f) => num2(f.fee_mgmt_actual)], ["ค่าใช้จ่ายรวมที่รายงาน (%)", (f) => num2(f.fee_ter_actual)],
  ["ค่าขาย (Front-end) สูงสุด (%)", (f) => num2(f.fee_front_max)], ["ผลตอบแทนตั้งแต่ต้นปี (%)", (f) => num2(f.ret_ytd)], ["ผลตอบแทน 1 ปี (%)", (f) => num2(f.ret_1y)],
  ["ผลตอบแทน 3 ปี (%)", (f) => num2(f.ret_3y)], ["ความผันผวน 1 ปี (%)", (f) => num2(f.vol_1y)], ["Max drawdown (%)", (f) => num2(f.maximum_drawdown)],
  ["Sharpe ratio", (f) => num2(f.sharpe_ratio)], ["NAV ล่าสุด", (f) => nav4(f.nav)], ["วันที่ NAV", (f) => thaiDate(f.nav_date)],
  ["ลงทุนขั้นต่ำ (บาท)", (f) => (isNum(f.min_subscription) ? num0(f.min_subscription) : f.min_sub_note ? `${DASH} (${f.min_sub_note})` : DASH)], ["ข้อมูล ณ", (f) => thaiDate(f.data_as_of)],
];

export const MAX_COMPARE = 4;

/** ตารางเปรียบเทียบเคียงข้างกัน (ไม่จัดอันดับ) */
export function CompareTable({ funds, notice }: { funds: Fund[]; notice: string }) {
  return (
    <>
      <div className="table-wrap"><table className="dt"><thead><tr><th>รายการ</th>{funds.map((f) => <th key={fundKey(f)}>{f.proj_abbr_name}<span className="block text-xs font-normal">{f.fund_class_name !== "main" ? f.fund_class_name : ""}</span></th>)}</tr></thead>
        <tbody>{METRICS.map(([label, fn]) => <tr key={label}><td className="font-medium">{label}</td>{funds.map((f) => <td key={fundKey(f)} className="num">{fn(f)}</td>)}</tr>)}
          <tr><td className="font-medium">ข้อควรระวังเรื่องข้อมูล</td>{funds.map((f) => <td key={fundKey(f)} className="text-left text-xs">{dqList(f.dq_flags).length ? dqList(f.dq_flags).join("; ") : DASH}</td>)}</tr></tbody></table></div>
      <p className="mt-3 text-xs text-warn">{notice} ตารางนี้แสดงข้อมูลเปรียบเทียบตามที่ บลจ. รายงานต่อ ก.ล.ต. เท่านั้น มิได้จัดอันดับหรือแนะนำกองทุนใด</p>
      <p className="mt-1 text-xs text-ink3">{VAT_NOTE}</p>
    </>
  );
}
