import React from "react";
import { AbsoluteFill, Easing, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import rects from "../public/states/rects.json";
import { C, fontFamily, thaiFamily } from "./theme";

// ---------- พิกัดโลก ----------
const WW = 1760; // ความกว้างหน้าต่างเบราว์เซอร์ในวิดีโอ (px)
const B = WW / 1920; // อัตราย่อหน้าจอ 1920x1080 เข้าหน้าต่าง
const OFF_X = (1920 - WW) / 2;
const BAR = 40;
const OFF_Y = (1080 - (BAR + 1080 * B)) / 2;
const CENTER_Y = 520;

const bez = Easing.bezier(0.45, 0, 0.2, 1);
const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const seg = (t: number, a: number, b: number) => clamp01((t - a) / (b - a));

const R: any = rects;
const cx = (r: { x: number; w: number }) => r.x + r.w / 2;
const cy = (r: { y: number; h: number }) => r.y + r.h / 2;

// ---------- กล้อง ----------
interface Cam { t: number; dur: number; x: number; y: number; z: number }
const CAMS: Cam[] = [
  { t: 0, dur: 0, x: 960, y: 540, z: 1 },
  { t: 1.7, dur: 1.2, x: 700, y: 170, z: 1.6 },
  { t: 2.9, dur: 0.9, x: 780, y: 400, z: 1.8 },
  { t: 5.8, dur: 0.8, x: 800, y: 560, z: 1.8 },
  { t: 7.3, dur: 0.8, x: 900, y: 570, z: 1.5 },
  { t: 8.9, dur: 0.9, x: 1000, y: 420, z: 1.7 },
  { t: 13.6, dur: 0.9, x: 1000, y: 620, z: 1.7 },
  { t: 14.4, dur: 0.9, x: 1500, y: 430, z: 1.6 },
  { t: 16.0, dur: 0.7, x: 1500, y: 600, z: 1.5 },
  { t: 17.9, dur: 0.9, x: 1000, y: 560, z: 1.7 },
  { t: 20.5, dur: 0.9, x: 1500, y: 520, z: 1.4 },
  { t: 22.9, dur: 0.9, x: 1050, y: 560, z: 1.7 },
  { t: 24.5, dur: 0.8, x: 800, y: 330, z: 1.6 },
  { t: 26.6, dur: 0.9, x: 960, y: 540, z: 1 },
];

const camAt = (t: number) => {
  let cur = CAMS[0];
  for (let i = 1; i < CAMS.length; i++) {
    const k = CAMS[i], start = k.t - k.dur;
    if (t <= start) break;
    if (t >= k.t) { cur = k; continue; }
    const e = bez(seg(t, start, k.t));
    return clampCam({ x: cur.x + (k.x - cur.x) * e, y: cur.y + (k.y - cur.y) * e, z: cur.z + (k.z - cur.z) * e });
  }
  return clampCam(cur);
};
const clampCam = (c: { x: number; y: number; z: number }) => {
  const half = 960 / (B * c.z), top = CENTER_Y / (B * c.z), bot = (1080 - CENTER_Y) / (B * c.z);
  const x = half >= 960 ? 960 : Math.max(half - 40, Math.min(1920 - half + 40, c.x));
  const y = top + bot >= 1080 ? 540 : Math.max(top - 50, Math.min(1080 - bot + 20, c.y));
  return { x, y, z: c.z };
};

// ---------- สถานะหน้าจอ ----------
interface St { t: number; src: string; fade?: number }
const STATES: St[] = [
  { t: 0, src: "st00-home" },
  { t: 2.2, src: "st01-funds" },
  { t: 3.95, src: "st02-search" },
  { t: 5.4, src: "st01-funds" },
  { t: 6.8, src: "st03-policy" },
  { t: 8.2, src: "st04-ter" },
  { t: 10.0, src: "st05-sort" },
  { t: 11.65, src: "st04-ter" },
  { t: 13.15, src: "st06-group" },
  { t: 14.15, src: "st07-detail", fade: 0.22 },
  { t: 16.0, src: "st08-detail2", fade: 0.4 },
  { t: 17.65, src: "st06-group", fade: 0.22 },
  { t: 18.45, src: "st09-pick1", fade: 0.06 },
  { t: 18.95, src: "st010-pick2", fade: 0.06 },
  { t: 19.45, src: "st011-pick3", fade: 0.06 },
  { t: 20.3, src: "st12-compare", fade: 0.22 },
  { t: 22.7, src: "st011-pick3", fade: 0.22 },
  { t: 23.45, src: "st13-save1", fade: 0.06 },
  { t: 23.95, src: "st14-save2", fade: 0.06 },
  { t: 24.9, src: "st15-saved", fade: 0.2 },
];

// ---------- เคอร์เซอร์ ----------
interface Mv { t0: number; t1: number; x: number; y: number }
const g = R.group;
const POP = (sel: any, idx: number) => ({ x: sel.x + 120, y: sel.y + sel.h + 4 + 6 + idx * 46 + 23 });
const pPol = POP(R.funds0.policy, 1), pSort1 = POP(R.funds0.sort, 2), pSort2 = POP(R.funds0.sort, 1), pGrp = POP(R.funds0.group, 3);
const MOVES: Mv[] = [
  { t0: 0.6, t1: 1.7, x: cx(R.home.navFunds), y: cy(R.home.navFunds) },
  { t0: 2.35, t1: 3.0, x: cx(R.funds0.search), y: cy(R.funds0.search) },
  { t0: 5.4, t1: 5.95, x: cx(R.funds0.policy), y: cy(R.funds0.policy) },
  { t0: 6.1, t1: 6.6, ...pPol },
  { t0: 7.0, t1: 7.45, x: cx(R.funds0.ter), y: cy(R.funds0.ter) },
  { t0: 8.6, t1: 9.15, x: cx(R.funds0.sort), y: cy(R.funds0.sort) },
  { t0: 9.3, t1: 9.85, ...pSort1 },
  { t0: 10.4, t1: 10.95, x: cx(R.funds0.sort), y: cy(R.funds0.sort) },
  { t0: 11.1, t1: 11.5, ...pSort2 },
  { t0: 11.9, t1: 12.4, x: cx(R.funds0.group), y: cy(R.funds0.group) },
  { t0: 12.55, t1: 13.0, ...pGrp },
  { t0: 13.4, t1: 14.0, x: cx(g.names[0]), y: cy(g.names[0]) },
  { t0: 16.8, t1: 17.5, x: cx(R.detail.close), y: cy(R.detail.close) },
  { t0: 17.9, t1: 18.35, x: cx(g.boxes[0]), y: cy(g.boxes[0]) },
  { t0: 18.55, t1: 18.85, x: cx(g.boxes[1]), y: cy(g.boxes[1]) },
  { t0: 19.05, t1: 19.35, x: cx(g.boxes[2]), y: cy(g.boxes[2]) },
  { t0: 19.7, t1: 20.15, x: cx(R.pick.compareBtn), y: cy(R.pick.compareBtn) },
  { t0: 22.0, t1: 22.55, x: cx(R.compare.close), y: cy(R.compare.close) },
  { t0: 22.95, t1: 23.35, x: cx(g.saves[0]), y: cy(g.saves[0]) },
  { t0: 23.6, t1: 23.85, x: cx(g.saves[1]), y: cy(g.saves[1]) },
  { t0: 24.2, t1: 24.75, x: cx(R.saved.navSaved), y: cy(R.saved.navSaved) },
  { t0: 25.5, t1: 26.3, x: 1000, y: 500 },
];
const CLICKS = [2.0, 3.1, 6.0, 6.75, 7.5, 9.2, 9.95, 11.0, 11.6, 12.45, 13.1, 14.1, 17.6, 18.4, 18.9, 19.4, 20.25, 22.65, 23.4, 23.9, 24.85];
const START = { x: 1200, y: 640 };

const cursorAt = (t: number) => {
  let p = START;
  for (const m of MOVES) {
    if (t <= m.t0) return p;
    if (t < m.t1) {
      const e = bez(seg(t, m.t0, m.t1));
      const dx = m.x - p.x, dy = m.y - p.y, d = Math.hypot(dx, dy) || 1;
      const arc = Math.sin(Math.PI * e) * Math.min(60, d * 0.12);
      return { x: p.x + dx * e + (-dy / d) * arc, y: p.y + dy * e + (dx / d) * arc };
    }
    p = { x: m.x, y: m.y };
  }
  return p;
};

// ---------- overlay ----------
interface Pop { open: number; close: number; sel: any; items: string[]; idx: number; wide?: boolean }
const POPS: Pop[] = [
  { open: 6.0, close: 6.8, sel: R.funds0.policy, items: R.options.policy.map((o: any) => o.t).slice(0, 6), idx: 1 },
  { open: 9.2, close: 10.0, sel: R.funds0.sort, items: R.options.sort.map((o: any) => o.t).slice(0, 6), idx: 2, wide: true },
  { open: 11.0, close: 11.65, sel: R.funds0.sort, items: R.options.sort.map((o: any) => o.t).slice(0, 6), idx: 1, wide: true },
  { open: 12.45, close: 13.15, sel: R.funds0.group, items: R.options.group.map((o: any) => o.t).slice(0, 6), idx: 3, wide: true },
];

const Popup: React.FC<{ p: Pop; t: number }> = ({ p, t }) => {
  if (t < p.open || t > p.close + 0.08) return null;
  const a = clamp01(seg(t, p.open, p.open + 0.14)) * (1 - clamp01(seg(t, p.close, p.close + 0.08)));
  const w = Math.max(p.sel.w, p.wide ? 300 : 0);
  const hover = t > p.close - 0.45 ? p.idx : -1;
  return (
    <div style={{ position: "absolute", left: p.sel.x, top: p.sel.y + p.sel.h + 4, width: w, padding: 6, borderRadius: 10, background: "#fff", boxShadow: "0 14px 40px rgba(10,31,68,.28), 0 0 0 1px rgba(10,31,68,.12)", opacity: a, transform: `translateY(${(1 - a) * -8}px)`, fontFamily: thaiFamily, fontSize: 15, color: "#0b1f3a" }}>
      {p.items.map((it, i) => (
        <div key={i} style={{ height: 46, display: "flex", alignItems: "center", padding: "0 12px", borderRadius: 7, background: i === hover ? "#dce8ff" : "transparent", fontWeight: i === hover ? 600 : 400 }}>{it}</div>
      ))}
    </div>
  );
};

const TypeBox: React.FC<{ rect: any; text: string; on: number; typeStart: number; cps: number; delAt?: number; end: number; t: number }> = ({ rect, text, on, typeStart, cps, delAt, end, t }) => {
  if (t < on || t >= end) return null;
  let n = Math.max(0, Math.min(text.length, Math.floor((t - typeStart) * cps)));
  if (delAt !== undefined && t >= delAt) n = Math.max(0, text.length - Math.floor((t - delAt) * 16));
  const caret = Math.floor(t * 2.4) % 2 === 0;
  return (
    <div style={{ position: "absolute", left: rect.x, top: rect.y, width: rect.w, height: rect.h, background: "#fff", borderRadius: 8, border: `2px solid ${C.brand}`, boxShadow: "0 0 0 4px rgba(27,75,155,.22)", display: "flex", alignItems: "center", paddingLeft: 11, fontFamily, fontSize: 15, color: "#0b1f3a", boxSizing: "border-box" }}>
      {text.slice(0, n)}
      <span style={{ width: 1.5, height: 20, background: "#0b1f3a", marginLeft: 1, opacity: caret ? 1 : 0 }} />
    </div>
  );
};

const Ring: React.FC<{ rect: any; at: number; len: number; t: number; pad?: number }> = ({ rect, at, len, t, pad = 6 }) => {
  if (t < at || t > at + len) return null;
  const a = clamp01(seg(t, at, at + 0.2)) * (1 - clamp01(seg(t, at + len - 0.3, at + len)));
  const pulse = 0.6 + 0.4 * Math.sin((t - at) * 9);
  return <div style={{ position: "absolute", left: rect.x - pad, top: rect.y - pad, width: rect.w + pad * 2, height: rect.h + pad * 2, borderRadius: 10, border: `2.5px solid ${C.accent}`, boxShadow: `0 0 ${22 * pulse}px ${C.accent}`, opacity: a }} />;
};

const CountPill: React.FC<{ t: number }> = ({ t }) => {
  const at = 8.3, end = 10.6;
  if (t < at || t > end) return null;
  const e = bez(seg(t, at, at + 0.7));
  const n = Math.round(4970 + (853 - 4970) * e);
  const a = clamp01(seg(t, at, at + 0.2)) * (1 - clamp01(seg(t, end - 0.3, end)));
  return <div style={{ position: "absolute", left: 862, top: 205, height: 34, padding: "0 16px", borderRadius: 17, background: C.accent, color: C.navy, fontFamily, fontWeight: 700, fontSize: 18, display: "flex", alignItems: "center", opacity: a, transform: `translateX(${(1 - a) * -14}px)`, whiteSpace: "nowrap" }}>{n.toLocaleString("en-US")} of 4,970 classes</div>;
};

const Cursor: React.FC<{ t: number; z: number }> = ({ t, z }) => {
  const p = cursorAt(t);
  const press = CLICKS.some((c) => t >= c && t < c + 0.12) ? 0.82 : 1;
  const k = 1.15 / Math.pow(z, 0.55);
  return (
    <>
      {CLICKS.map((c, i) => {
        if (t < c || t > c + 0.5) return null;
        const e = bez(seg(t, c, c + 0.5));
        const pos = cursorAt(c);
        return <div key={i} style={{ position: "absolute", left: pos.x - 30, top: pos.y - 30, width: 60, height: 60, borderRadius: 30, border: `3px solid ${C.accent}`, opacity: 1 - e, transform: `scale(${0.25 + e * 0.9})` }} />;
      })}
      <svg width={30} height={30} viewBox="0 0 24 24" style={{ position: "absolute", left: p.x, top: p.y, transformOrigin: "3px 2px", transform: `translate(-3px,-2px) scale(${k * press})`, filter: "drop-shadow(0 3px 4px rgba(0,0,0,.4))" }}>
        <path d="M3 2l7 18 2.6-7.4L20 10z" fill="#fff" stroke="#0b1f3a" strokeWidth="1.5" strokeLinejoin="round" />
      </svg>
    </>
  );
};

const CAPS: { a: number; b: number; k: string; text: string }[] = [
  { a: 2.6, b: 5.6, k: "01", text: "Search by name, ticker or project ID" },
  { a: 5.8, b: 8.9, k: "02", text: "Filter by policy, risk, fees and returns" },
  { a: 9.0, b: 12.2, k: "03", text: "Sort by any column" },
  { a: 12.3, b: 14.0, k: "04", text: "Group to see the shape of the market" },
  { a: 14.1, b: 17.7, k: "05", text: "Open any fund: NAV, performance, fees, risk" },
  { a: 18.2, b: 22.8, k: "06", text: "Compare up to four funds side by side" },
  { a: 23.2, b: 27.2, k: "07", text: "Save in your browser. No sign-up" },
];

const Caption: React.FC<{ t: number }> = ({ t }) => {
  const c = CAPS.find((x) => t >= x.a && t < x.b);
  if (!c) return null;
  const inn = bez(seg(t, c.a, c.a + 0.35)), out = bez(seg(t, c.b - 0.25, c.b));
  const o = inn * (1 - out);
  return (
    <div style={{ position: "absolute", left: 0, right: 0, bottom: 38, display: "flex", justifyContent: "center", opacity: o, transform: `translateY(${(1 - inn) * 28 + out * 18}px)` }}>
      <div style={{ display: "flex", alignItems: "center", gap: 18, padding: "14px 30px 14px 16px", borderRadius: 999, background: "rgba(8,22,50,.92)", border: "1px solid rgba(255,255,255,.18)", boxShadow: "0 14px 40px rgba(0,0,0,.45)", fontFamily }}>
        <div style={{ width: 44, height: 44, borderRadius: 22, background: C.accent, color: C.navy, fontWeight: 700, fontSize: 20, display: "flex", alignItems: "center", justifyContent: "center" }}>{c.k}</div>
        <div style={{ color: C.ink, fontSize: 34, fontWeight: 600 }}>{c.text}</div>
      </div>
    </div>
  );
};

export const SESSION_SECONDS = 27.4;

export const Session: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = frame / fps;
  const cam = camAt(t);
  const fxw = OFF_X + cam.x * B, fyw = OFF_Y + BAR + cam.y * B;
  let si = 0;
  STATES.forEach((s, i) => { if (t >= s.t) si = i; });
  const cur = STATES[si], prev = STATES[Math.max(0, si - 1)];
  const fa = si === 0 ? 1 : clamp01((t - cur.t) / (cur.fade ?? 0.12));
  const enter = bez(seg(t, 0, 0.5));

  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080, transformOrigin: "0 0", transform: `translate(${960 - cam.z * fxw}px, ${CENTER_Y - cam.z * fyw}px) scale(${cam.z})`, opacity: enter }}>
        <div style={{ position: "absolute", left: OFF_X, top: OFF_Y, width: WW, height: BAR + 1080 * B, borderRadius: 14, overflow: "hidden", background: "#e9eef6", boxShadow: "0 40px 110px rgba(0,0,0,.6), 0 0 0 1px rgba(255,255,255,.14)" }}>
          <div style={{ height: BAR, display: "flex", alignItems: "center", gap: 8, padding: "0 16px" }}>
            {["#ff5f57", "#febc2e", "#28c840"].map((c) => <div key={c} style={{ width: 12, height: 12, borderRadius: 6, background: c }} />)}
            <div style={{ marginLeft: 14, height: 24, width: 420, borderRadius: 12, background: "#fff", color: "#6b7a90", fontSize: 14, fontFamily, display: "flex", alignItems: "center", paddingLeft: 12 }}>thai-mutual-fund-data · demo</div>
          </div>
          <div style={{ position: "absolute", left: 0, top: BAR, width: 1920, height: 1080, transformOrigin: "0 0", transform: `scale(${B})`, overflow: "hidden" }}>
            {si > 0 && <Img src={staticFile(`states/${prev.src}.jpg`)} style={{ position: "absolute", inset: 0, width: 1920, height: 1080 }} />}
            <Img src={staticFile(`states/${cur.src}.jpg`)} style={{ position: "absolute", inset: 0, width: 1920, height: 1080, opacity: fa }} />
            <TypeBox rect={R.funds0.search} text="global" on={3.1} typeStart={3.2} cps={9} end={3.95} t={t} />
            <TypeBox rect={R.funds0.search} text="global" on={5.0} typeStart={0} cps={99} delAt={5.0} end={5.4} t={t} />
            <TypeBox rect={R.funds0.ter} text="1.5" on={7.5} typeStart={7.7} cps={7} end={8.2} t={t} />
            {POPS.map((p, i) => <Popup key={i} p={p} t={t} />)}
            <Ring rect={R.ter.count} at={8.3} len={2.0} t={t} />
            <Ring rect={{ x: 654, y: 337, w: 340, h: 24 }} at={8.4} len={1.8} t={t} pad={4} />
            <CountPill t={t} />
            <Cursor t={t} z={cam.z} />
          </div>
        </div>
      </div>
      <Caption t={t} />
    </AbsoluteFill>
  );
};
