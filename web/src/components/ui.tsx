import { useEffect, useId, useRef, type ReactNode } from "react";

export function Callout({ tone, title, children }: { tone: "warn" | "info" | "danger" | "good"; title?: string; children: ReactNode }) {
  const s = {
    warn: "bg-warnsoft text-warn border-warn/40",
    info: "bg-brandsoft text-brand border-brand/30",
    danger: "bg-dangersoft text-danger border-danger/40",
    good: "bg-goodsoft text-good border-good/40",
  }[tone];
  return (
    <div role={tone === "danger" || tone === "warn" ? "alert" : "note"} className={`rounded-lg border px-4 py-3 text-sm ${s}`}>
      {title && <div className="font-semibold mb-0.5">{title}</div>}
      <div className="text-ink">{children}</div>
    </div>
  );
}

export function Skeleton({ h = 20, w = "100%" }: { h?: number; w?: string | number }) {
  return <div className="skeleton" style={{ height: h, width: w }} aria-hidden />;
}

export function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="card p-8 text-center">
      <div className="text-lg font-semibold">{title}</div>
      {children && <div className="text-ink2 mt-1 text-sm">{children}</div>}
    </div>
  );
}

export function Drawer({ open, onClose, title, children, wide }: { open: boolean; onClose: () => void; title: string; children: ReactNode; wide?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const prev = document.activeElement as HTMLElement | null;
    ref.current?.focus();
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    document.body.style.overflow = "hidden";
    return () => { document.removeEventListener("keydown", onKey); document.body.style.overflow = ""; prev?.focus(); };
  }, [open, onClose]);
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex justify-end" role="dialog" aria-modal="true" aria-label={title}>
      <div className="absolute inset-0 bg-[#061630]/55" onClick={onClose} aria-hidden />
      <div ref={ref} tabIndex={-1} className={`relative h-full w-full ${wide ? "max-w-3xl" : "max-w-xl"} bg-surface border-l border-line shadow-2xl overflow-y-auto outline-none`}>
        <div className="sticky top-0 z-10 flex items-center justify-between gap-3 border-b border-line bg-surface px-5 py-3">
          <h2 className="text-lg font-semibold">{title}</h2>
          <button className="btn" onClick={onClose} aria-label="ปิด">ปิด</button>
        </div>
        <div className="p-5">{children}</div>
      </div>
    </div>
  );
}

export function Section({ title, subtitle, children, right }: { title: string; subtitle?: string; children: ReactNode; right?: ReactNode }) {
  return (
    <section className="card p-5">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div>
          <h2 className="text-lg font-semibold">{title}</h2>
          {subtitle && <p className="text-sm text-ink2 mt-0.5">{subtitle}</p>}
        </div>
        {right}
      </div>
      {children}
    </section>
  );
}
