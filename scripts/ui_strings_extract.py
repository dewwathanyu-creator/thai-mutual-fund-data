"""ดึงข้อความภาษาไทยทั้งหมดใน web/src เป็นรายการ (ไฟล์:บรรทัด: ข้อความ) เพื่อรีวิวถ้อยคำ
พิมพ์ผลที่ stdout ไม่แก้ไฟล์ใด ๆ  ใช้: python scripts/ui_strings_extract.py [ไฟล์ ...]
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent / "web" / "src"
TH = re.compile("[฀-๿]")
JSX = re.compile(r">([^<>{}]*[฀-๿][^<>{}]*)(?=<|\{)|\}([^<>{}]*[฀-๿][^<>{}]*)(?=<|\{)")


def string_literals(text):
    """สแกนหา string literal แบบ "..." '...' `...` (รองรับเครื่องหมายแบ็กสแลชหลบอักขระ)"""
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c in "\"'`":
            j = i + 1
            while j < n and text[j] != c:
                if text[j] == "\\":
                    j += 1
                if c != "`" and j < n and text[j] == "\n":
                    break
                j += 1
            if j < n and text[j] == c:
                yield i, text[i + 1:j]
                i = j
        i += 1


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    files = [Path(a) for a in sys.argv[1:]] or sorted(list((ROOT / "pages").glob("*.tsx")) + list((ROOT / "components").glob("*.tsx")) + [ROOT / "App.tsx"])
    for p in files:
        text = p.read_text(encoding="utf-8")
        seen = set()
        items = [(pos, t) for pos, t in string_literals(text)]
        items += [(m.start(), next(g for g in m.groups() if g)) for m in JSX.finditer(text)]
        for pos, t in sorted(items):
            t = t.strip()
            if not t or not TH.search(t) or t in seen:
                continue
            seen.add(t)
            print(f"{p.name}:{text.count(chr(10), 0, pos) + 1}: {t}")


if __name__ == "__main__":
    main()
