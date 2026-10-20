import React from "react";
import { AbsoluteFill, Easing, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { TransitionSeries, springTiming } from "@remotion/transitions";
import { slide } from "@remotion/transitions/slide";
import { wipe } from "@remotion/transitions/wipe";
import { Session, SESSION_SECONDS } from "./Session";
import { C, fontFamily } from "./theme";

const FPS = 60;
const bez = Easing.bezier(0.22, 1, 0.36, 1);
const clamp01 = (v: number) => Math.max(0, Math.min(1, v));
const rise = (t: number, at: number, d = 0.55) => bez(clamp01((t - at) / d));

const BG: React.FC = () => (
  <AbsoluteFill style={{ background: `radial-gradient(1300px 760px at 18% -5%, ${C.navy2}, ${C.navy} 58%, #06142e)` }}>
    <AbsoluteFill style={{ backgroundImage: "linear-gradient(rgba(255,255,255,.035) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,.035) 1px, transparent 1px)", backgroundSize: "64px 64px" }} />
  </AbsoluteFill>
);

const useT = () => useCurrentFrame() / useVideoConfig().fps;

const Stat: React.FC<{ to: number; label: string; at: number }> = ({ to, label, at }) => {
  const t = useT();
  const p = rise(t, at, 0.9);
  return (
    <div style={{ opacity: clamp01(p * 2), transform: `translateY(${(1 - p) * 34}px)`, textAlign: "center", minWidth: 330 }}>
      <div style={{ fontSize: 104, fontWeight: 700, color: C.ink, fontVariantNumeric: "tabular-nums", letterSpacing: -2 }}>{Math.round(to * p).toLocaleString("en-US")}</div>
      <div style={{ fontSize: 28, color: C.sky, marginTop: 2 }}>{label}</div>
    </div>
  );
};

const Intro: React.FC = () => {
  const t = useT();
  const words = ["Thai", "Mutual", "Fund", "Data"];
  const sub = rise(t, 0.7);
  return (
    <AbsoluteFill style={{ fontFamily, alignItems: "center", justifyContent: "center" }}>
      <BG />
      <div style={{ textAlign: "center" }}>
        <div style={{ display: "flex", gap: 28, justifyContent: "center" }}>
          {words.map((w, i) => {
            const p = rise(t, 0.05 + i * 0.09);
            return <div key={w} style={{ overflow: "hidden", height: 130 }}><div style={{ fontSize: 112, fontWeight: 700, color: C.ink, letterSpacing: -2, transform: `translateY(${(1 - p) * 120}px)`, lineHeight: "130px" }}>{w}</div></div>;
          })}
        </div>
        <div style={{ opacity: sub, transform: `translateY(${(1 - sub) * 20}px)`, fontSize: 36, color: C.mute, marginTop: 6 }}>Search, filter, compare and save funds with public SEC Open API data</div>
        <div style={{ display: "flex", justifyContent: "center", gap: 100, marginTop: 80 }}>
          <Stat to={4970} label="fund classes" at={0.7} />
          <Stat to={2398} label="fund projects" at={0.8} />
          <Stat to={22} label="asset managers" at={0.9} />
        </div>
      </div>
    </AbsoluteFill>
  );
};

const Card: React.FC<{ at: number; big: React.ReactNode; label: string; sub: string; bar?: number }> = ({ at, big, label, sub, bar }) => {
  const t = useT();
  const p = rise(t, at, 0.7);
  return (
    <div style={{ width: 520, padding: "44px 40px", borderRadius: 26, background: "rgba(255,255,255,.06)", border: "1px solid rgba(255,255,255,.16)", opacity: clamp01(p * 1.6), transform: `translateY(${(1 - p) * 70}px)` }}>
      <div style={{ fontSize: 96, fontWeight: 700, color: C.accent, letterSpacing: -2, fontVariantNumeric: "tabular-nums", lineHeight: 1 }}>{big}</div>
      <div style={{ fontSize: 34, fontWeight: 600, color: C.ink, marginTop: 20 }}>{label}</div>
      <div style={{ fontSize: 24, color: C.mute, marginTop: 8, lineHeight: 1.35 }}>{sub}</div>
      {bar !== undefined && (
        <div style={{ height: 10, borderRadius: 5, background: "rgba(255,255,255,.14)", marginTop: 26, overflow: "hidden" }}>
          <div style={{ height: "100%", width: `${bar * rise(t, at + 0.3, 1.0) * 100}%`, background: C.accent, borderRadius: 5 }} />
        </div>
      )}
    </div>
  );
};

const Integrity: React.FC = () => {
  const t = useT();
  const k = rise(t, 0, 0.5);
  const rmf = Math.round(423 * rise(t, 0.5, 1.1));
  const zero = rise(t, 0.9, 0.5);
  return (
    <AbsoluteFill style={{ fontFamily, alignItems: "center", justifyContent: "center" }}>
      <BG />
      <div style={{ textAlign: "center", opacity: k, transform: `translateY(${(1 - k) * 24}px)` }}>
        <div style={{ fontSize: 28, color: C.accent, fontWeight: 600, letterSpacing: 4 }}>DATA YOU CAN CHECK</div>
        <div style={{ fontSize: 64, fontWeight: 700, color: C.ink, marginTop: 10 }}>Shown as the source reports it</div>
      </div>
      <div style={{ display: "flex", gap: 36, marginTop: 70 }}>
        <Card at={0.35} big="0" label="Mismatches in audit" sub="Every table value reconciled against the raw API files" />
        <Card at={0.5} big={<span>0.00 <span style={{ opacity: zero }}>→ –</span></span>} label="Placeholder zeros" sub="Missing data is a dash with a note, never a fake zero" />
        <Card at={0.65} big={`${rmf} / 437`} label="RMF classes verified" sub="Matched to the SEC report; unverified types show no label" bar={423 / 437} />
      </div>
    </AbsoluteFill>
  );
};

const Outro: React.FC = () => {
  const t = useT();
  const a = rise(t, 0.05), tags = ["Python", "FastAPI", "React", "TypeScript", "Tailwind", "TanStack Table", "Recharts"], d = rise(t, 1.1, 0.7);
  return (
    <AbsoluteFill style={{ fontFamily, alignItems: "center", justifyContent: "center", textAlign: "center" }}>
      <BG />
      <div>
        <div style={{ opacity: a, transform: `translateY(${(1 - a) * 40}px)`, fontSize: 84, fontWeight: 700, color: C.ink, letterSpacing: -1 }}>Thai Mutual Fund Data</div>
        <div style={{ display: "flex", gap: 14, justifyContent: "center", marginTop: 40, flexWrap: "wrap", maxWidth: 1300 }}>
          {tags.map((x, i) => { const p = rise(t, 0.35 + i * 0.07); return <div key={x} style={{ padding: "10px 24px", borderRadius: 999, border: "1px solid rgba(255,255,255,.3)", color: C.ink, fontSize: 28, opacity: p, transform: `translateY(${(1 - p) * 20}px)` }}>{x}</div>; })}
        </div>
        <div style={{ marginTop: 56, fontSize: 26, color: C.mute, lineHeight: 1.55, opacity: d }}>Data source: SEC Open API (public data), shown as reported by asset managers.<br />For information only. Not investment or tax advice. Past performance does not guarantee future results.</div>
      </div>
    </AbsoluteFill>
  );
};

const sec = (s: number) => Math.round(s * FPS);
const INTRO = sec(2.7), SESSION = sec(SESSION_SECONDS), INTEG = sec(3.6), OUTRO = sec(3.2), TR = 30;
export const TOTAL_FRAMES = INTRO + SESSION + INTEG + OUTRO - 3 * TR;
export const VIDEO_FPS = FPS;

export const Demo: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: C.navy }}>
      <TransitionSeries>
        <TransitionSeries.Sequence durationInFrames={INTRO}><Intro /></TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={slide({ direction: "from-bottom" })} timing={springTiming({ config: { damping: 200 }, durationInFrames: TR })} />
        <TransitionSeries.Sequence durationInFrames={SESSION}><SessionBG /></TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={wipe({ direction: "from-left" })} timing={springTiming({ config: { damping: 200 }, durationInFrames: TR })} />
        <TransitionSeries.Sequence durationInFrames={INTEG}><Integrity /></TransitionSeries.Sequence>
        <TransitionSeries.Transition presentation={slide({ direction: "from-right" })} timing={springTiming({ config: { damping: 200 }, durationInFrames: TR })} />
        <TransitionSeries.Sequence durationInFrames={OUTRO}><Outro /></TransitionSeries.Sequence>
      </TransitionSeries>
      <div style={{ position: "absolute", left: 0, bottom: 0, height: 5, width: `${(frame / TOTAL_FRAMES) * 100}%`, background: C.accent }} />
    </AbsoluteFill>
  );
};

const SessionBG: React.FC = () => (
  <AbsoluteFill>
    <BG />
    <Session />
  </AbsoluteFill>
);
