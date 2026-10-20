"""รันแอป: python run.py          -> โหมดผลิต (build frontend ถ้ายังไม่มี แล้วเสิร์ฟทั้งหมดที่ http://127.0.0.1:8000)
         python run.py --dev    -> โหมดพัฒนา (FastAPI :8000 + Vite :5173 พร้อม hot reload)
         python run.py --port 8765   -> เปลี่ยนพอร์ต API (ถ้า 8000 ถูกโปรแกรมอื่นใช้อยู่)
ไม่แตะ .env และไม่เรียก SEC API: อ่านเฉพาะไฟล์ใน data/
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
NPM = shutil.which("npm") or shutil.which("npm.cmd")


def need_npm():
    if not NPM:
        sys.exit("ไม่พบ npm: ติดตั้ง Node.js (>= 20) ก่อน")


def ensure_deps():
    need_npm()
    if not (WEB / "node_modules").exists():
        subprocess.run([NPM, "install", "--no-fund", "--no-audit"], cwd=WEB, check=True)


def get_port():
    if "--port" in sys.argv:
        return sys.argv[sys.argv.index("--port") + 1]
    return "8000"


def main():
    dev = "--dev" in sys.argv
    port = get_port()
    api_cmd = [sys.executable, "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", port, "--no-access-log"]
    if not (ROOT / "data" / "funds_table.csv").exists():
        print("คำเตือน: ไม่พบ data/funds_table.csv (หน้าสำรวจกองทุนจะว่าง) ดู README หัวข้อ 'สร้างข้อมูล'")
    if dev:
        ensure_deps()
        procs = [subprocess.Popen(api_cmd + ["--reload"], cwd=ROOT), subprocess.Popen([NPM, "run", "dev"], cwd=WEB)]
        print("\nเปิด http://localhost:5173 (API ที่ :8000) กด Ctrl+C เพื่อหยุดทั้งหมด\n")
        try:
            for p in procs:
                p.wait()
        except KeyboardInterrupt:
            pass
        finally:
            for p in procs:
                p.terminate()
        return
    if not (WEB / "dist" / "index.html").exists():
        ensure_deps()
        subprocess.run([NPM, "run", "build"], cwd=WEB, check=True)
    print("\nเปิด http://127.0.0.1:8000 กด Ctrl+C เพื่อหยุด\n")
    subprocess.run(api_cmd, cwd=ROOT)


if __name__ == "__main__":
    main()
