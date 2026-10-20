import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, type Meta } from "./api";

// ข้อมูลระบบ (meta) และรายการที่ผู้ใช้บันทึกไว้ รายการที่บันทึกเก็บใน localStorage ของเบราว์เซอร์ผู้ใช้เท่านั้น ไม่ถูกส่งไปที่เซิร์ฟเวอร์
// รูปแบบรายการ: "proj_id|fund_class_name"

const SAVED_KEY = "tfm-saved-v1";

function loadSaved(): string[] {
  try {
    const raw = localStorage.getItem(SAVED_KEY);
    const v = raw ? JSON.parse(raw) : [];
    return Array.isArray(v) ? v.filter((x): x is string => typeof x === "string" && x.includes("|")).slice(0, 500) : [];
  } catch { return []; }
}

interface Ctx {
  meta: Meta | null; metaError: string | null;
  saved: string[]; isSaved: (k: string) => boolean; toggleSaved: (k: string) => void;
  addSaved: (keys: string[]) => void; removeSaved: (k: string) => void; clearSaved: () => void;
  storageOk: boolean;
}

const StoreCtx = createContext<Ctx | null>(null);

export function StoreProvider({ children }: { children: ReactNode }) {
  const [meta, setMeta] = useState<Meta | null>(null);
  const [metaError, setMetaError] = useState<string | null>(null);
  const [saved, setSaved] = useState<string[]>(loadSaved);
  const [storageOk, setStorageOk] = useState(true);

  useEffect(() => { api.meta().then(setMeta).catch((e: Error) => setMetaError(e.message)); }, []);
  useEffect(() => {
    try { localStorage.setItem(SAVED_KEY, JSON.stringify(saved)); setStorageOk(true); } catch { setStorageOk(false); }
  }, [saved]);

  const value = useMemo<Ctx>(() => ({
    meta, metaError, saved, storageOk,
    isSaved: (k) => saved.includes(k),
    toggleSaved: (k) => setSaved((s) => (s.includes(k) ? s.filter((x) => x !== k) : [...s, k])),
    addSaved: (keys) => setSaved((s) => [...s, ...keys.filter((k) => !s.includes(k))].slice(0, 500)),
    removeSaved: (k) => setSaved((s) => s.filter((x) => x !== k)),
    clearSaved: () => setSaved([]),
  }), [meta, metaError, saved, storageOk]);

  return <StoreCtx.Provider value={value}>{children}</StoreCtx.Provider>;
}

export function useStore() {
  const c = useContext(StoreCtx);
  if (!c) throw new Error("StoreProvider missing");
  return c;
}
