import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, type Fund } from "../api";
import { ClassBadge, CompareTable, FundDetailLoader, MAX_COMPARE, SaveButton, fundKey, riskText } from "../components/fund";
import { Callout, Drawer, Empty, Skeleton } from "../components/ui";
import { dqList } from "../dq";
import { DASH, downloadCsv, nav4, num2, thaiDate } from "../format";
import { useStore } from "../store";

const MAX_SHARE = 40;

const toB64 = (s: string) => btoa(String.fromCharCode(...new TextEncoder().encode(s))).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
function fromB64(s: string): string | null {
  try {
    const b = atob(s.replace(/-/g, "+").replace(/_/g, "/"));
    return new TextDecoder().decode(Uint8Array.from(b, (c) => c.charCodeAt(0)));
  } catch { return null; }
}
const isKey = (x: unknown): x is string => typeof x === "string" && /^[^|]+\|[^|]+$/.test(x) && x.length < 200;

function parseShared(param: string | null): string[] {
  if (!param) return [];
  const j = fromB64(param);
  if (!j) return [];
  try {
    const v = JSON.parse(j);
    return Array.isArray(v) ? v.filter(isKey).slice(0, MAX_SHARE) : [];
  } catch { return []; }
}

export default function Saved() {
  const { saved, removeSaved, clearSaved, addSaved, storageOk } = useStore();
  const [params, setParams] = useSearchParams();
  const [all, setAll] = useState<Fund[] | null>(null);
  const [notice, setNotice] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [picked, setPicked] = useState<string[]>([]);
  const [detail, setDetail] = useState<Fund | null>(null);
  const [compare, setCompare] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => { api.funds().then((r) => { setAll(r.items); setNotice(r.past_performance_notice); }).catch((e: Error) => setErr(e.message)); }, []);

  const shared = useMemo(() => parseShared(params.get("s")), [params]);
  const byKey = useMemo(() => new Map((all ?? []).map((f) => [fundKey(f), f])), [all]);
  const toggle = (k: string) => setPicked((p) => (p.includes(k) ? p.filter((x) => x !== k) : p.length >= MAX_COMPARE ? p : [...p, k]));

  const shareLink = () => {
    const keys = saved.slice(0, MAX_SHARE);
    const url = `${location.origin}${location.pathname}#/saved?s=${toB64(JSON.stringify(keys))}`;
    const done = () => setMsg(`คัดลอกลิงก์แล้ว (${keys.length} รายการ${saved.length > MAX_SHARE ? ` จาก ${saved.length} รายการ จำกัดสูงสุด ${MAX_SHARE} รายการต่อลิงก์` : ""})`);
    navigator.clipboard?.writeText(url).then(done, () => setMsg(`ไม่สามารถคัดลอกอัตโนมัติได้ ลิงก์คือ ${url}`)) ?? setMsg(`ลิงก์คือ ${url}`);
  };
  const exportJson = () => {
    const blob = new Blob([JSON.stringify({ version: 1, saved }, null, 2)], { type: "application/json" });
    const a = document.createElement("a"); a.href = URL.createObjectURL(blob); a.download = "saved_funds.json"; a.click(); URL.revokeObjectURL(a.href);
  };
  const importJson = (file: File) => {
    file.text().then((t) => {
      try {
        const v = JSON.parse(t);
        const keys: unknown[] = Array.isArray(v) ? v : Array.isArray(v?.saved) ? v.saved : [];
        const ok = keys.filter(isKey);
        addSaved(ok);
        setMsg(`นำเข้ารายการแล้ว ${ok.length} รายการ${keys.length !== ok.length ? ` (ข้ามรายการที่รูปแบบไม่ถูกต้อง ${keys.length - ok.length} รายการ)` : ""}`);
      } catch { setMsg("ไฟล์ไม่ถูกต้อง ไม่สามารถนำเข้าได้"); }
    }).catch(() => setMsg("ไม่สามารถอ่านไฟล์ได้"));
  };

  if (err) return <Callout tone="danger" title="ไม่สามารถโหลดข้อมูลกองทุนได้">{err}</Callout>;
  if (!all) return <div className="space-y-3" aria-busy><Skeleton h={30} w={240} /><Skeleton h={240} /></div>;

  const found = saved.map((k) => byKey.get(k)).filter(Boolean) as Fund[];
  const missing = saved.filter((k) => !byKey.has(k));
  const pickedFunds = picked.map((k) => byKey.get(k)).filter(Boolean) as Fund[];
  const sharedFunds = shared.map((k) => byKey.get(k)).filter(Boolean) as Fund[];

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-bold">Saved funds</h1>
        <p className="text-sm text-ink2 mt-1">เก็บกองทุนที่สนใจไว้เพื่อกลับมาดูหรือเปรียบเทียบภายหลัง รายการถูกเก็บในเบราว์เซอร์ของผู้ใช้เครื่องนี้เท่านั้น ไม่มีการส่งไปยังเซิร์ฟเวอร์และไม่ต้องสมัครสมาชิก หากล้างข้อมูลเบราว์เซอร์หรือเปลี่ยนเครื่อง รายการจะไม่ติดไปด้วย (สำรองไว้ได้ด้วยปุ่มส่งออกไฟล์หรือสร้างลิงก์)</p>
      </div>
      {!storageOk && <Callout tone="warn" title="ไม่สามารถบันทึกในเบราว์เซอร์ได้">เบราว์เซอร์นี้ไม่อนุญาตให้เก็บข้อมูล (เช่น โหมดส่วนตัว) รายการจะหายเมื่อปิดหน้าต่าง ควรส่งออกไฟล์สำรองไว้</Callout>}
      {msg && <Callout tone="info"><div className="flex flex-wrap items-center justify-between gap-2"><span className="break-all">{msg}</span><button className="btn !min-h-8 text-xs" onClick={() => setMsg(null)}>ปิดข้อความ</button></div></Callout>}

      {shared.length > 0 && (
        <section className="card p-4 border-brand/40">
          <h2 className="font-semibold">Shared with you ({shared.length} รายการ)</h2>
          <p className="text-xs text-ink2 mt-1">ลิงก์นี้มีรายการกองทุนที่ผู้อื่นแชร์มา ข้อมูลที่แสดงเป็นข้อมูลปัจจุบันในระบบ มิใช่ข้อมูล ณ เวลาที่แชร์ และมิใช่ข้อเสนอแนะ</p>
          <ul className="mt-2 text-sm list-disc pl-5">{shared.map((k) => { const f = byKey.get(k); return <li key={k}>{f ? `${f.proj_abbr_name}${f.fund_class_name !== "main" ? ` · ${f.fund_class_name}` : ""} — ${f.proj_name_th}` : `${k.replace("|", " · ")} (ไม่พบข้อมูลในระบบ)`}</li>; })}</ul>
          <div className="mt-3 flex flex-wrap gap-2">
            <button className="btn btn-primary" disabled={!sharedFunds.length} onClick={() => { addSaved(sharedFunds.map(fundKey)); setParams({}); setMsg(`เพิ่ม ${sharedFunds.length} รายการลงในรายการที่บันทึกแล้ว`); }}>เพิ่มลงในรายการที่บันทึก</button>
            <button className="btn" onClick={() => setParams({})}>ไม่เพิ่ม</button>
          </div>
        </section>
      )}

      {saved.length === 0 ? (
        <Empty title="ยังไม่มีรายการที่บันทึก">เลือกปุ่ม &ldquo;บันทึก&rdquo; ที่กองทุนในหน้า <Link to="/funds">ข้อมูลกองทุนรวม</Link> เพื่อเก็บรายการไว้ที่นี่ หรือนำเข้าไฟล์ที่เคยส่งออกไว้
          <div className="mt-3"><input ref={fileRef} type="file" accept="application/json,.json" className="sr-only" aria-label="เลือกไฟล์รายการที่บันทึก" onChange={(e) => { const f = e.target.files?.[0]; if (f) importJson(f); e.target.value = ""; }} /><button className="btn" onClick={() => fileRef.current?.click()}>นำเข้าจากไฟล์</button></div></Empty>
      ) : (
        <>
          <div className="flex flex-wrap items-center justify-between gap-2 no-print">
            <p className="text-sm text-ink2">บันทึกไว้ {saved.length} รายการ · เลือกเปรียบเทียบได้สูงสุด {MAX_COMPARE} กองทุน (เลือกแล้ว {picked.length})</p>
            <div className="flex flex-wrap gap-2">
              <button className="btn btn-primary" disabled={pickedFunds.length < 2} onClick={() => setCompare(true)}>เปรียบเทียบ {pickedFunds.length >= 2 ? `(${pickedFunds.length})` : ""}</button>
              <button className="btn" onClick={shareLink}>คัดลอกลิงก์แชร์</button>
              <button className="btn" onClick={() => downloadCsv("saved_funds.csv", found as unknown as Record<string, unknown>[], [
                { key: "proj_id", label: "รหัสโครงการ" }, { key: "fund_class_name", label: "class" }, { key: "proj_abbr_name", label: "ชื่อย่อ" }, { key: "proj_name_th", label: "ชื่อกองทุน" },
                { key: "comp_name_th", label: "บริษัทจัดการ" }, { key: "risk_level", label: "ความเสี่ยง (1-8)" }, { key: "fee_ter_actual", label: "ค่าธรรมเนียมรวมที่รายงาน %" }, { key: "ret_1y", label: "ผลตอบแทน 1 ปี %" },
                { key: "nav", label: "NAV" }, { key: "nav_date", label: "วันที่ NAV" }, { key: "data_as_of", label: "ข้อมูล ณ" }])} disabled={!found.length}>ส่งออก CSV</button>
              <button className="btn" onClick={exportJson}>สำรองเป็นไฟล์</button>
              <input ref={fileRef} type="file" accept="application/json,.json" className="sr-only" aria-label="เลือกไฟล์รายการที่บันทึก" onChange={(e) => { const f = e.target.files?.[0]; if (f) importJson(f); e.target.value = ""; }} />
              <button className="btn" onClick={() => fileRef.current?.click()}>นำเข้าจากไฟล์</button>
              <button className="btn" onClick={() => { if (window.confirm("ต้องการล้างรายการที่บันทึกทั้งหมดหรือไม่")) { clearSaved(); setPicked([]); } }}>ล้างทั้งหมด</button>
            </div>
          </div>
          <div className="card overflow-hidden">
            <div className="table-wrap">
              <table className="dt">
                <thead><tr><th>Compare</th><th>Fund / Class</th><th>Tax type (verified)</th><th className="num">Risk</th><th className="num">TER (reported %)</th><th className="num">1Y return %</th><th className="num">NAV</th><th>As of</th><th>Actions</th></tr></thead>
                <tbody>
                  {found.map((f) => (
                    <tr key={fundKey(f)}>
                      <td><input type="checkbox" className="h-4 w-4 accent-[var(--brand)]" aria-label={`เลือก ${f.proj_abbr_name} เพื่อเปรียบเทียบ`} checked={picked.includes(fundKey(f))} disabled={!picked.includes(fundKey(f)) && picked.length >= MAX_COMPARE} onChange={() => toggle(fundKey(f))} /></td>
                      <td><button className="text-left font-semibold text-brand hover:underline" onClick={() => setDetail(f)}>{f.proj_abbr_name}{dqList(f.dq_flags).length > 0 && <span className="ml-1 badge badge-warn" title={dqList(f.dq_flags).join("\n")}>หมายเหตุ</span>}
                        <span className="block text-xs font-normal text-ink2 max-w-[280px] truncate">{f.fund_class_name !== "main" ? `class ${f.fund_class_name} · ` : ""}{f.proj_name_th}</span></button></td>
                      <td><ClassBadge f={f} /></td>
                      <td className="num">{f.risk_level === null ? DASH : riskText(f)}</td>
                      <td className="num">{num2(f.fee_ter_actual)}</td><td className="num">{num2(f.ret_1y)}</td><td className="num">{nav4(f.nav)}</td>
                      <td className="text-xs num">{thaiDate(f.data_as_of)}</td>
                      <td><SaveButton f={f} compact /></td>
                    </tr>))}
                  {missing.map((k) => (
                    <tr key={k}><td /><td className="text-ink2" colSpan={7}>{k.replace("|", " · ")} <span className="text-xs">(ไม่พบข้อมูลของรายการนี้ในชุดข้อมูลปัจจุบัน อาจเป็นกองทุนที่ยกเลิกแล้วหรือชื่อ class เปลี่ยน)</span></td><td><button className="btn !min-h-8 text-xs" onClick={() => removeSaved(k)}>นำออก</button></td></tr>))}
                </tbody>
              </table>
            </div>
          </div>
          <p className="text-xs text-ink3">ตารางนี้แสดงข้อมูลตามที่ บลจ. รายงานต่อ ก.ล.ต. ลำดับเป็นไปตามลำดับที่บันทึก มิได้จัดอันดับหรือแนะนำกองทุนใด {notice}</p>
        </>
      )}

      <Drawer open={detail !== null} onClose={() => setDetail(null)} wide title={detail ? `${detail.proj_abbr_name}${detail.fund_class_name !== "main" ? ` · ${detail.fund_class_name}` : ""}` : ""}>
        {detail && <FundDetailLoader f={detail} notice={notice} />}
      </Drawer>
      <Drawer open={compare} onClose={() => setCompare(false)} wide title="Compare funds">
        <CompareTable funds={pickedFunds} notice={notice} />
      </Drawer>
    </div>
  );
}
