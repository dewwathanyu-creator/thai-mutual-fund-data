import { Link } from "react-router-dom";
import { Callout, Skeleton } from "../components/ui";
import { num0, thaiDate } from "../format";
import { useStore } from "../store";

const FEATURES = [
  { t: "Search & filter", d: "ค้นหาด้วยชื่อกองทุนหรือรหัส กรองตามบริษัทจัดการ นโยบายการลงทุน ระดับความเสี่ยง ค่าธรรมเนียม และผลตอบแทนย้อนหลัง" },
  { t: "Fund details", d: "NAV ย้อนหลัง 1 ปี ค่าธรรมเนียม ผลการดำเนินงาน สถิติความเสี่ยง การจัดสรรสินทรัพย์ ทรัพย์สินที่ลงทุน และลิงก์ Fact Sheet" },
  { t: "Side-by-side compare", d: "เลือกได้สูงสุด 4 กองทุนหรือ class เพื่อดูข้อมูลชุดเดียวกันเปรียบเทียบกัน โดยไม่มีการจัดอันดับหรือให้คะแนน" },
  { t: "Save & share", d: "บันทึกกองทุนที่สนใจไว้ในเบราว์เซอร์ ส่งออกเป็นไฟล์ หรือสร้างลิงก์ส่งต่อได้ โดยไม่ต้องสมัครสมาชิก" },
];

export default function Home() {
  const { meta, saved } = useStore();
  const f = meta?.funds;
  return (
    <div className="space-y-6">
      <section className="rounded-xl bg-navy text-white p-6 sm:p-10 shadow-[var(--shadow)]">
        <div className="max-w-3xl">
          <h1 className="text-2xl sm:text-3xl font-bold leading-snug">Thai Mutual Fund Data<br className="hidden sm:block" />Search, compare and save</h1>
          <p className="mt-4 text-white/80 text-[15px] leading-relaxed">
            รวบรวมข้อมูลกองทุนรวมที่จดทะเบียนกับสำนักงานคณะกรรมการ ก.ล.ต. จากข้อมูลสาธารณะ (SEC Open API) ได้แก่ ค่าธรรมเนียม ผลการดำเนินงาน ระดับความเสี่ยง NAV
            และการจัดสรรสินทรัพย์ แสดงตามที่บริษัทจัดการรายงาน พร้อมวันที่ของข้อมูลและหมายเหตุกำกับในรายการที่ควรตรวจสอบเพิ่มเติม
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Link to="/funds" className="btn btn-primary !bg-white !text-[#0a1f44] !border-white no-underline hover:!bg-[#e6eefb]">Open Fund Explorer</Link>
            <Link to="/saved" className="btn !bg-transparent !text-white !border-white/50 no-underline hover:!bg-white/10">Saved{saved.length ? ` (${saved.length})` : ""}</Link>
          </div>
        </div>
      </section>

      <section aria-labelledby="what" className="card p-5 sm:p-6">
        <h2 id="what" className="text-lg font-semibold mb-4">What you can do</h2>
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((x, i) => (
            <li key={x.t} className="flex gap-3">
              <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brandsoft text-brand font-bold num">{i + 1}</span>
              <span><b className="block">{x.t}</b><span className="text-sm text-ink2">{x.d}</span></span>
            </li>
          ))}
        </ul>
      </section>

      <section aria-labelledby="data" className="card p-5 sm:p-6">
        <h2 id="data" className="text-lg font-semibold mb-4">Data in the system</h2>
        {!f ? <Skeleton h={64} /> : (
          <dl className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              ["Unit classes", num0(f.n_classes)],
              ["Fund projects", num0(f.n_funds)],
              ["Management companies", num0(f.n_amc)],
              ["Latest data as of", thaiDate(f.data_as_of_latest)],
            ].map(([k, v]) => (
              <div key={k} className="rounded-lg bg-surface2 p-3">
                <dt className="text-xs text-ink2">{k}</dt>
                <dd className="mt-0.5 text-xl font-semibold num">{v}</dd>
              </div>
            ))}
          </dl>
        )}
        <p className="mt-3 text-xs text-ink2">
          ครอบคลุมกองทุนรวมที่จดทะเบียนอยู่และกองทุนที่อยู่ระหว่างเสนอขายครั้งแรก (IPO) ข้อมูลเป็นภาพ ณ เวลาที่ดึงจาก SEC Open API ไม่ใช่ข้อมูลแบบทันที
          รายละเอียดการตรวจสอบข้อมูลและข้อจำกัดอยู่ที่หน้า <Link to="/about">Sources &amp; Limitations</Link>
        </p>
      </section>

      <Callout tone="info" title="Disclaimer">
        {meta?.disclaimer ?? "ระบบนี้จัดทำขึ้นเพื่อให้ข้อมูลกองทุนรวมแก่ผู้สนใจเท่านั้น มิใช่คำแนะนำด้านการลงทุนหรือภาษี"} {meta?.past_performance_notice}
      </Callout>
    </div>
  );
}
