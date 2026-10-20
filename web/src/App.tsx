import { useEffect, useState } from "react";
import { NavLink, Route, Routes, useLocation } from "react-router-dom";
import { Callout } from "./components/ui";
import About from "./pages/About";
import Funds from "./pages/Funds";
import Home from "./pages/Home";
import Saved from "./pages/Saved";
import { useStore } from "./store";

/** ค่าเริ่มต้นเป็นโหมดสว่าง (เหมาะกับงานเอกสารทางการเงิน) เปลี่ยนเป็นโหมดมืดได้ และจำค่าที่ผู้ใช้เลือกไว้เท่านั้น */
function useTheme() {
  const [theme, setTheme] = useState<"light" | "dark">(() => (document.documentElement.dataset.theme === "dark" ? "dark" : "light"));
  useEffect(() => { document.documentElement.dataset.theme = theme; }, [theme]);
  const toggle = () => setTheme((t) => {
    const next = t === "dark" ? "light" : "dark";
    try { localStorage.setItem("tfp-theme-pref", next); } catch { /* ไม่เก็บก็ได้ */ }
    return next;
  });
  return [theme, toggle] as const;
}

export default function App() {
  const { meta, metaError, saved } = useStore();
  const [theme, toggle] = useTheme();
  const loc = useLocation();
  useEffect(() => { window.scrollTo(0, 0); }, [loc.pathname]);

  const NAV = [
    { to: "/", label: "Home", end: true },
    { to: "/funds", label: "Fund Explorer" },
    { to: "/saved", label: saved.length ? `Saved (${saved.length})` : "Saved" },
    { to: "/about", label: "Sources & Limitations" },
  ];

  return (
    <div className="min-h-screen flex flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-surface focus:p-3">ข้ามไปยังเนื้อหา</a>
      <header className="bg-navy text-white border-b border-white/10">
        <div className="mx-auto max-w-7xl px-4 sm:px-6">
          <div className="flex items-center justify-between gap-3 py-3">
            <NavLink to="/" className="flex items-center gap-3 !text-white no-underline" aria-label="ข้อมูลกองทุนรวมไทย หน้าแรก">
              <svg width="34" height="34" viewBox="0 0 32 32" aria-hidden>
                <rect width="32" height="32" rx="7" fill="#1b4b9b" />
                <path d="M7 22l6-7 4 3 8-10" stroke="#fff" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
                <path d="M7 26h18" stroke="#9bbfff" strokeWidth="1.6" strokeLinecap="round" />
              </svg>
              <span className="leading-tight">
                <span className="block text-[15px] font-semibold">Thai Mutual Fund Data</span>
                <span className="block text-[11px] text-white/70">ค้นหา เปรียบเทียบ และบันทึกรายการ · ข้อมูลสาธารณะจากสำนักงาน ก.ล.ต.</span>
              </span>
            </NavLink>
            <button className="rounded-md border border-white/25 px-3 py-1.5 text-xs hover:bg-white/10" onClick={toggle}
              aria-label={theme === "dark" ? "เปลี่ยนเป็นโหมดสว่าง" : "เปลี่ยนเป็นโหมดมืด"}>
              {theme === "dark" ? "โหมดสว่าง" : "โหมดมืด"}
            </button>
          </div>
          <nav aria-label="เมนูหลัก" className="-mb-px flex gap-1 overflow-x-auto">
            {NAV.map((n) => (
              <NavLink key={n.to} to={n.to} end={n.end}
                className={({ isActive }) => `whitespace-nowrap px-4 py-2.5 text-sm no-underline border-b-2 ${isActive ? "border-white !text-white font-semibold" : "border-transparent !text-white/75 hover:!text-white"}`}>
                {n.label}
              </NavLink>
            ))}
          </nav>
        </div>
      </header>

      <main id="main" className="flex-1 mx-auto w-full max-w-7xl px-4 sm:px-6 py-6">
        {metaError && (
          <div className="mb-4">
            <Callout tone="danger" title="ไม่สามารถเชื่อมต่อกับระบบประมวลผลได้">
              {metaError} กรุณาตรวจสอบว่าเปิดใช้งานบริการ API แล้ว (ดูวิธีเริ่มระบบในไฟล์ README)
            </Callout>
          </div>
        )}
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/funds" element={<Funds />} />
          <Route path="/saved" element={<Saved />} />
          <Route path="/about" element={<About />} />
          <Route path="*" element={<Callout tone="info" title="ไม่พบหน้าที่ต้องการ">กรุณาเลือกหน้าจากเมนูด้านบน</Callout>} />
        </Routes>
      </main>

      <footer className="border-t border-line bg-surface">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 py-4 text-xs text-ink2 space-y-1">
          <p><b>Disclaimer:</b> {meta?.disclaimer ?? "ระบบนี้จัดทำขึ้นเพื่อให้ข้อมูลกองทุนรวมแก่ผู้สนใจเท่านั้น มิใช่คำแนะนำด้านการลงทุนหรือภาษี"}</p>
          <p><b>Data source:</b> SEC Open API ของสำนักงาน ก.ล.ต. (ข้อมูลสาธารณะ) · {meta?.past_performance_notice} · รายการที่บันทึกเก็บในเบราว์เซอร์ของผู้ใช้เท่านั้น</p>
        </div>
      </footer>
    </div>
  );
}
