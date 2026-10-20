// ถ่ายสถานะหน้าจอจริง (4K) + พิกัดองค์ประกอบ สำหรับวิดีโอแบบมีเคอร์เซอร์/คลิก
// รัน: node capture2.mjs  (ต้องเปิดเว็บ static ที่ http://127.0.0.1:8800 ไว้)
import puppeteer from "puppeteer-core";
import { mkdirSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

const BASE = process.env.BASE ?? "http://127.0.0.1:8800/";
const CHROME = fileURLToPath(new URL("./node_modules/.remotion/chrome-headless-shell/win64/chrome-headless-shell-win64/chrome-headless-shell.exe", import.meta.url));
const OUT = fileURLToPath(new URL("./public/states/", import.meta.url));
mkdirSync(OUT, { recursive: true });

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ["--no-first-run"], defaultViewport: { width: 1920, height: 1080, deviceScaleFactor: 2 } });
const page = await browser.newPage();
await page.emulateMediaFeatures([{ name: "prefers-color-scheme", value: "light" }]);

const rects = {};
const shot = async (name) => { await sleep(900); await page.screenshot({ path: `${OUT}${name}.jpg`, type: "jpeg", quality: 86 }); console.log("ok", name); };
const rect = (sel, i = 0) => page.evaluate((sel, i) => { const e = document.querySelectorAll(sel)[i]; if (!e) return null; const r = e.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }; }, sel, i);
const rectText = (sel, text) => page.evaluate((sel, text) => { const e = [...document.querySelectorAll(sel)].find((x) => x.innerText.trim().startsWith(text)); if (!e) return null; const r = e.getBoundingClientRect(); return { x: r.x, y: r.y, w: r.width, h: r.height }; }, sel, text);
const setSel = (id, v) => page.evaluate((id, v) => { const el = document.getElementById(id); Object.getOwnPropertyDescriptor(HTMLSelectElement.prototype, "value").set.call(el, v); el.dispatchEvent(new Event("change", { bubbles: true })); }, id, v);
const setInp = (id, v) => page.evaluate((id, v) => { const el = document.getElementById(id); Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, "value").set.call(el, v); el.dispatchEvent(new Event("input", { bubbles: true })); }, id, v);
const go = async (hash, wait) => { await page.goto(BASE + hash, { waitUntil: "networkidle0" }); await page.reload({ waitUntil: "networkidle0" }); await page.waitForSelector(wait, { timeout: 30000 }); await sleep(800); };
const options = (id) => page.evaluate((id) => [...document.getElementById(id).options].map((o) => ({ v: o.value, t: o.text })), id);
const inputStyle = (id) => page.evaluate((id) => { const s = getComputedStyle(document.getElementById(id)); return { fontSize: s.fontSize, color: s.color, pl: s.paddingLeft, radius: s.borderRadius, family: s.fontFamily }; }, id);
const clickRow = async (i, sel) => page.evaluate((i, sel) => document.querySelectorAll(sel)[i].click(), i, sel);

// ---- home
await go("#/", "h1");
rects.home = { navFunds: await rectText("nav a", "Fund Explorer") };
await shot("st00-home");

// ---- funds
await go("#/funds", "#sort");
await setSel("sort", "size"); await sleep(400);
rects.funds0 = { search: await rect("#q"), policy: await rect("#pol"), ter: await rect("#ter"), sort: await rect("#sort"), group: await rect("#group"), count: await rect("[aria-live=polite]"), navSaved: await rectText("nav a", "Saved"), filters: await rect("aside .card") };
rects.options = { policy: await options("pol"), sort: await options("sort"), group: await options("group") };
rects.inputStyle = { q: await inputStyle("q"), ter: await inputStyle("ter") };
await shot("st01-funds");

await setInp("q", "global"); await sleep(600);
rects.search = { count: await rect("[aria-live=polite]") };
await shot("st02-search");
await setInp("q", ""); await sleep(300);

await setSel("pol", "ตราสารทุน"); await sleep(500);
rects.policy = { count: await rect("[aria-live=polite]"), chips: await rect("[aria-label='ตัวกรองที่ใช้อยู่']") };
await shot("st03-policy");

await setInp("ter", "1.5"); await sleep(500);
rects.ter = { count: await rect("[aria-live=polite]"), chips: await rect("[aria-label='ตัวกรองที่ใช้อยู่']") };
await shot("st04-ter");

await setSel("sort", "ter_asc"); await sleep(500);
rects.sort = { thTer: await rectText("thead th", "TER"), firstRows: await rect("tbody tr", 0) };
await shot("st05-sort");
await setSel("sort", "size"); await sleep(500);

await setSel("group", "risk"); await sleep(700);
// เลือกแถวที่ไม่มีป้ายหมายเหตุ 3 แถวแรก (ในกลุ่มแรก)
const clean = await page.evaluate(() => {
  const out = [];
  document.querySelectorAll("tbody tr").forEach((tr, i) => { if (out.length < 3 && !tr.innerText.includes("หมายเหตุ") && !tr.innerText.includes("ตรวจสอบ") && tr.getBoundingClientRect().bottom < 1040) out.push(i); });
  return out;
});
console.log("clean rows", clean);
rects.group = {
  count: await rect("[aria-live=polite]"), groupHeader: await rect("section.card button[aria-expanded]", 0), clean,
  names: [await rect("tbody tr td button.text-brand", clean[0]), await rect("tbody tr td button.text-brand", clean[1]), await rect("tbody tr td button.text-brand", clean[2])],
  boxes: [await rect("tbody tr input[type=checkbox]", clean[0]), await rect("tbody tr input[type=checkbox]", clean[1]), await rect("tbody tr input[type=checkbox]", clean[2])],
  saves: [await rect("tbody tr td:last-child button", clean[0]), await rect("tbody tr td:last-child button", clean[1])],
  compareBtn: await rectText("button", "เปรียบเทียบ"),
  rowNames: await page.evaluate((c) => c.map((i) => document.querySelectorAll("tbody tr td button.text-brand")[i].innerText.split("\n")[0]), clean),
};
await shot("st06-group");

// ---- detail drawer
await clickRow(clean[0], "tbody tr td button.text-brand");
await sleep(2500);
rects.detail = { close: await rectText("button", "ปิด") };
await shot("st07-detail");
await page.evaluate(() => {
  const d = [...document.querySelectorAll("div")].filter((e) => e.scrollHeight > e.clientHeight + 200 && ["auto", "scroll"].includes(getComputedStyle(e).overflowY)).pop();
  d?.scrollTo(0, 620);
});
await shot("st08-detail2");
await page.evaluate(() => [...document.querySelectorAll("button")].find((b) => b.innerText.trim() === "ปิด").click());
await sleep(600);

// ---- compare (3 picks)
for (let k = 0; k < 3; k++) {
  await page.evaluate((i) => document.querySelectorAll("tbody tr input[type=checkbox]")[i].click(), clean[k]);
  await shot(`st0${9 + k}-pick${k + 1}`.replace("st012", "st11"));
}
rects.pick = { compareBtn: await rectText("button", "เปรียบเทียบ") };
await page.evaluate(() => [...document.querySelectorAll("button")].find((b) => b.innerText.trim().startsWith("เปรียบเทียบ (")).click());
await sleep(1500);
rects.compare = { close: await rectText("button", "ปิด") };
await shot("st12-compare");
await page.evaluate(() => [...document.querySelectorAll("button")].find((b) => b.innerText.trim() === "ปิด").click());
await sleep(600);

// ---- save x2
for (let k = 0; k < 2; k++) {
  await page.evaluate((i) => document.querySelectorAll("tbody tr td:last-child button")[i].click(), clean[k]);
  await shot(`st${13 + k}-save${k + 1}`);
}
rects.saved = { navSaved: await rectText("nav a", "Saved") };
await page.evaluate(() => [...document.querySelectorAll("nav a")].find((a) => a.innerText.trim().startsWith("Saved")).click());
await sleep(1500);
await shot("st15-saved");

writeFileSync(`${OUT}rects.json`, JSON.stringify(rects, null, 1));
await browser.close();
console.log("rects.json written");
