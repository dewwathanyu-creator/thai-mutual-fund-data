"""ตัวเรียก SEC Thailand Open API V2 แบบเรียบง่าย
- อ่าน key จาก .env เท่านั้น และไม่พิมพ์ key ออกที่ใด
"""
import json
import os
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
PLACEHOLDER = "PASTE_YOUR_KEY_HERE"


def utf8_stdout():
    """กันปัญหาภาษาไทยพิมพ์ไม่ออกบน Windows"""
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


def load_env(path=None):
    path = Path(path) if path else ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def save_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")


def find_records(data, depth=0):
    """หา list ของ record (dict) ที่ใหญ่ที่สุดใน response โดยไม่รู้โครงสร้างล่วงหน้า"""
    if isinstance(data, list):
        return data
    if isinstance(data, dict) and depth < 3:
        best = []
        for v in data.values():
            cand = find_records(v, depth + 1)
            if len(cand) > len(best) and cand and isinstance(cand[0], dict):
                best = cand
        return best
    return []


class SecClient:
    def __init__(self):
        load_env()
        self.key = os.environ.get("SEC_API_KEY", "").strip()
        if not self.key or self.key == PLACEHOLDER:
            raise SystemExit("ยังไม่ได้ใส่ SEC_API_KEY ในไฟล์ .env (ให้เปิดไฟล์ .env แล้ววาง key ด้วยตัวเอง)")
        self.base = os.environ.get("SEC_API_BASE_URL", "https://api.sec.or.th").rstrip("/")
        self.header = os.environ.get("SEC_API_KEY_HEADER", "Ocp-Apim-Subscription-Key")
        self.delay = float(os.environ.get("SEC_REQUEST_DELAY_SEC", "0.5"))
        self.session = requests.Session()
        self.session.headers.update({self.header: self.key, "Accept": "application/json"})

    def _mask(self, text):
        return str(text).replace(self.key, "***")

    def get(self, path, params=None, retries=3, raise_network=False):
        url = self.base + path
        last = None
        for attempt in range(retries + 1):
            try:
                r = self.session.get(url, params=params, timeout=60)
            except requests.RequestException as e:
                if raise_network:
                    raise
                last = self._mask(e)
                print(f"[เครือข่ายผิดพลาด] {last}", file=sys.stderr)
                time.sleep(2 ** attempt)
                continue
            if r.status_code in (429, 500, 502, 503, 504) and attempt < retries:
                wait = float(r.headers.get("Retry-After", 2 ** attempt))
                print(f"[{r.status_code}] รอ {wait:.0f} วินาทีแล้วลองใหม่", file=sys.stderr)
                time.sleep(wait)
                continue
            time.sleep(self.delay)
            return r
        raise SystemExit(f"เรียก {path} ไม่สำเร็จ: {last}")

    def explain_failure(self, r):
        body = self._mask(r.text[:500])
        print(f"HTTP {r.status_code} จาก {r.request.method} {r.url}", file=sys.stderr)
        print(f"เนื้อหาตอบกลับ (ตัดสั้น): {body}", file=sys.stderr)
        if r.status_code in (401, 403):
            print(
                "-> เช็ค 1) key วางถูกใน .env ไหม  2) ชื่อ header (SEC_API_KEY_HEADER) ตรงกับคู่มือนักพัฒนาไหม"
                "  3) key ผูกกับ API กองทุนแล้วหรือยัง (อาจต้องกด subscribe ในพอร์ทัล)",
                file=sys.stderr,
            )

    def get_json(self, path, params=None):
        r = self.get(path, params)
        if r.status_code != 200:
            self.explain_failure(r)
            raise SystemExit(1)
        try:
            return r, r.json()
        except ValueError:
            print("ตอบกลับไม่ใช่ JSON:", self._mask(r.text[:300]), file=sys.stderr)
            raise SystemExit(1)

    def get_all(self, path, params=None, page_size=100, max_pages=3000):
        """ดึงทุกหน้า: ส่ง page_size (สูงสุด 100) และ next_cursor จนกว่า next_cursor จะว่าง"""
        base = dict(params or {})
        base["page_size"] = page_size
        items, cursor, pages, first_meta = [], "", 0, None
        while True:
            q = dict(base)
            if cursor:
                q["next_cursor"] = cursor
            r, data = self.get_json(path, q)
            if first_meta is None:
                first_meta = response_meta(r)
            recs = find_records(data)
            items.extend(recs)
            pages += 1
            cursor = data.get("next_cursor", "") if isinstance(data, dict) else ""
            if pages % 10 == 0:
                print(f"  ... {pages} หน้า, สะสม {len(items)} รายการ", flush=True)
            if not cursor or not recs or pages >= max_pages:
                break
        return items, pages, first_meta


def response_meta(r):
    """เก็บ header ที่ช่วยดู pagination/rate limit (ตัด set-cookie ออก)"""
    hdrs = {k: v for k, v in r.headers.items() if k.lower() not in ("set-cookie",)}
    return {"url": r.url.split("?")[0], "status": r.status_code, "headers": hdrs, "bytes": len(r.content)}
