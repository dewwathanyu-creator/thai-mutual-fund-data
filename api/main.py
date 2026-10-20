"""FastAPI ให้บริการข้อมูลกองทุนรวมจากตารางใน data/ (อ่านอย่างเดียว)
รัน: uvicorn api.main:app  (ดู README) ไม่มี API key ฝั่งเบราว์เซอร์ ไม่เรียก SEC API ระหว่างใช้งาน และไม่รับข้อมูลส่วนบุคคลจากผู้ใช้
ส่วนคำนวณภาษีถูกนำออกจากเว็บ (สำเนาอยู่ที่ archive/tax-planner-ui/) ตัวคำนวณ planner/ ยังอยู่ในโปรเจกต์แต่ไม่ถูกเรียกจากที่นี่
"""
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import funds_data

DISCLAIMER = ("ระบบนี้จัดทำขึ้นเพื่อให้ข้อมูลกองทุนรวมแก่ผู้สนใจเท่านั้น มิใช่คำแนะนำด้านการลงทุนหรือภาษี "
              "และมิได้จัดอันดับหรือแนะนำกองทุนใด ผู้ลงทุนควรศึกษาหนังสือชี้ชวนและข้อมูลจากสำนักงาน ก.ล.ต. หรือบริษัทจัดการกองทุน "
              "ก่อนตัดสินใจลงทุน การลงทุนในกองทุนรวมไม่ใช่การฝากเงิน")
PAST_PERF = "ผลการดำเนินงานในอดีตมิได้เป็นสิ่งยืนยันถึงผลการดำเนินงานในอนาคต"
WEB_DIST = Path(__file__).resolve().parent.parent / "web" / "dist"

app = FastAPI(title="Thai Mutual Fund Data API", version="2.0", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.add_middleware(GZipMiddleware, minimum_size=1000)


@app.get("/api/meta")
def meta():
    return {"disclaimer": DISCLAIMER, "past_performance_notice": PAST_PERF, "funds": funds_data.summary()}


@app.get("/api/funds")
def funds():
    return {"items": funds_data.load_list(), "summary": funds_data.summary(), "past_performance_notice": PAST_PERF}


@app.get("/api/funds/{proj_id}")
def fund_detail(proj_id: str):
    items = [r for r in funds_data.load_funds() if r["proj_id"] == proj_id]
    if not items:
        raise HTTPException(404, "ไม่พบกองทุน")
    return {"proj_id": proj_id, "classes": items}


@app.get("/api/funds/{proj_id}/nav")
def fund_nav(proj_id: str, fund_class_name: str):
    series = funds_data.nav_series(proj_id, fund_class_name)
    return {"proj_id": proj_id, "fund_class_name": fund_class_name, "series": series, "empty": not series}


if WEB_DIST.exists():  # โหมดผลิต: เสิร์ฟ frontend ที่ build แล้ว
    app.mount("/assets", StaticFiles(directory=WEB_DIST / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = WEB_DIST / path
        return FileResponse(f if path and f.is_file() else WEB_DIST / "index.html")
