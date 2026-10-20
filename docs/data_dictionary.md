# พจนานุกรมข้อมูลตารางกองทุน

`scripts/08_build_funds_table.py` สร้าง `data/funds_table.csv` จากไฟล์ดิบใน `data/raw_latest/` โดยไม่เรียก API หนึ่งแถวคือหนึ่งคู่ `proj_id` + `fund_class_name` ที่จัดเป็น RMF, ThaiESG หรือ ThaiESGX และมีสถานะ Registered/IPO ตารางนี้เป็นข้อมูลสำหรับ **คัดกรองตามเกณฑ์ผู้ใช้** ไม่ใช่รายการแนะนำลงทุน

## คีย์และสถานะ

| คอลัมน์ | ความหมาย / แหล่งข้อมูล |
| --- | --- |
| `proj_id`, `fund_class_name` | คีย์ระดับกองและชนิดหน่วยลงทุนจาก SEC `profiles` |
| `api_class_name`, `class_match` | ชื่อ class ใน endpoint รายละเอียดและวิธีจับคู่: `exact`, `single_class_main`, `single_class_renamed`, `unmatched`, `no_data` |
| `tax_type`, `tax_type_confidence`, `classified_by` | ผลจัดประเภทจาก `scripts/fund_type_rules.py`; `verified_status = sec_report_rmf_2569-07-31` = RMF ที่ตรงรายงาน ก.ล.ต. (docs/sec_report_comparison.md); `medium` หมายถึงอาศัยชื่อและยังไม่เทียบรายชื่อทางการ |
| `verified_status`, `fund_status` | สถานะการยืนยันประเภท และสถานะกองใน SEC `profiles` |
| `comp_name_th`, `proj_name_th`, `proj_abbr_name`, `policy_desc`, `invest_country_flag`, `fund_class_isin_code` | ข้อมูลทั่วไปจาก `profiles` |

## ตัวชี้วัดและวันที่

| คอลัมน์ | ความหมาย / แหล่งข้อมูล |
| --- | --- |
| `risk_spectrum`, `risk_level`, `risk_spectrum_desc`, `risk_as_of` | ระดับความเสี่ยงจาก `risk-spectrum`; `risk_level` แยกตัวเลขจากรหัส `RS` |
| `fee_*_max`, `fee_*_actual`, `fees_as_of` | อัตราสูงสุดและอัตราที่เรียกเก็บจริงจาก `fees`; `mgmt` = ค่าบริหารจัดการ, `ter` = ค่าธรรมเนียมและค่าใช้จ่ายรวม, `front`/`back` = ค่าขาย/รับซื้อคืน |
| `ret_*`, `vol_*`, `bench_ret_*`, `peer_ret_*`, `perf_as_of` | ผลตอบแทน ความผันผวน ตัวชี้วัด และกลุ่มเดียวกัน จาก `performance`; ช่วงเวลา `3m`, `6m`, `ytd`, `1y`, `3y`, `5y`, `10y`, `inception` |
| `maximum_drawdown`, `sharpe_ratio`, `beta`, `alpha`, `tracking_error`, `portfolio_turnover_ratio`, `recovering_period`, `yield_to_maturity`, `fx_hedging`, `stats_as_of` | สถิติจาก `statistics` |
| `benchmark` | ตัวชี้วัดจาก `benchmarks` |
| `asset_allocation`, `alloc_as_of` | สัดส่วนสินทรัพย์จาก `asset-allocation` จัดเรียงตามสัดส่วน |
| `top5_holdings`, `top5_as_of` | หลักทรัพย์/สินทรัพย์ 5 อันดับแรกจาก `top5-holdings` |
| `nav`, `nav_date`, `net_asset` | NAV ล่าสุดและสินทรัพย์สุทธิจาก `daily-info/nav` |
| `nav_change_1y_pct` | การเปลี่ยนแปลงของ NAV ระหว่างรายการแรกและล่าสุดในช่วงที่ดึงย้อนหลังประมาณ 1 ปี คำนวณเฉพาะเมื่อห่างกันอย่างน้อย 330 วัน; **ไม่ใช่ผลตอบแทนรวม** และอาจไม่รวมเงินปันผล |
| `min_subscription`, `min_redemption`, `min_as_of` | ยอดซื้อ/ขายคืนขั้นต่ำจาก `subscription-redemption-minimums` |
| `factsheet_pdf`, `amc_factsheet_url` | URL จาก `factsheet/urls` |
| `data_as_of`, `fetched_at` | วันที่ข้อมูลที่แสดง (ใช้ NAV ก่อน แล้วใช้วันที่ของข้อมูลอื่น) และเวลาที่ดึงจาก API |

ค่า `"None"`, `null` และค่าที่ไม่มีข้อมูลถูกแปลงเป็นเซลล์ว่าง ไม่ตีความเป็นศูนย์ วันที่ของแต่ละ endpoint อาจต่างกัน จึงควรดูคอลัมน์ `*_as_of` คู่กับตัวเลขเสมอ

การดึงข้อมูลวันที่ 9 ตุลาคม 2569 พบ 22 class ที่ชื่อใน `profiles` ไม่ปรากฏใน endpoint รายละเอียดของ `proj_id` เดียวกัน เช่น `SCBRMUSA(E)` ขณะที่ endpoint มี `SCBRMUSA(A)` เท่านั้น ระบบเว้นตัวชี้วัดระดับ class ว่างเพื่อไม่คัดลอกข้อมูลของ class อื่นมาใส่ ส่วนตัวชี้วัดระดับ `proj_id` ยังแสดงได้

`data/nav_series.csv` เก็บ NAV รายวันย้อนหลังสำหรับ class ที่จับคู่ได้ โดยมี `proj_id`, `fund_class_name`, `nav_date`, `nav` ข้อมูลดิบใน `data/` ไม่ควรนำขึ้น GitHub

## ตารางรวมทุกกอง (`data/all_funds.csv`, `data/all_nav_series.csv`)
สร้างด้วย `python scripts/08_build_funds_table.py --all` (อ่านจาก `data/raw_latest/` ที่ดึงด้วย `scripts/12_fetch_all_funds.py`; ไม่แตะ `funds_table.csv` เดิม)
- 1 แถวต่อ class ที่ Registered/IPO = 4,970 class จาก 2,398 โครงการ คอลัมน์เหมือน `funds_table.csv` + `unique_id` (บลจ.), `regis_date`, `sec_tax_tag` (ค่า `fund_class_tax_incentive_type` จาก SEC ตามที่ API ให้ ไม่ผ่านกฎของเรา)
- `tax_type` ว่างสำหรับกองที่ไม่ใช่ RMF/SSF/ThaiESG/ThaiESGX; ค่าที่ไม่ครบเป็นเซลล์ว่าง ไม่ใช่ 0
- `class_match` เพิ่มค่า `class_absent` = endpoint ไม่มีข้อมูลของ class นี้เลย (ไม่ใช่ชื่อไม่ตรง) ค่าระดับ class เว้นว่าง; `unmatched` เหลือเฉพาะกรณีที่ endpoint มีชื่อ class ที่ไม่ตรงกับ profiles (อาจเป็นการเปลี่ยนชื่อ) ซึ่งไม่เดาจับคู่
- ค่าว่างต่อคอลัมน์และคุณภาพข้อมูล: `data/all_funds_quality.txt`

## กฎความถูกต้องของข้อมูล (เพิ่ม 2569-10-15; ตรวจโดย `scripts/14_audit_all_funds.py` ผลที่ `docs/data_audit_all_funds.md`)
ค่าในตารางมาจาก SEC Open API ตามที่ บลจ. รายงาน เราไม่ปรับค่าเอง ยกเว้นกรณีเหล่านี้ซึ่งตรวจพบจากข้อมูลจริงว่า "ค่าที่ API ส่งมาไม่ใช่ค่าจริง" และบันทึกไว้ในคอลัมน์ `dq_flags`:

| กรณี | พบอะไร | การจัดการ | ธง |
|---|---|---|---|
| ผลตอบแทน 1/3/5/10 ปีเป็น 0.00 แต่กองจดทะเบียนมาสั้นกว่าช่วงนั้น | `ret_10y` = 0 มี 540 class, 464 เป็นกองอายุน้อยกว่า 10 ปี (ค่า 0.00 ใช้แทนข้อมูลที่ไม่มี) | แสดงเป็นว่าง (ถ้าความผันผวนช่วงเดียวกันเป็น 0 ด้วยก็ว่าง) | `perf_zero_blanked` |
| ผลตอบแทนต้นปี/3/6 เดือนเป็น 0.00 แต่ NAV ช่วงเดียวกันเปลี่ยนมาก | เช่น KTSET50FF-A (บลจ. กรุงไทย) รายงาน YTD 0.00 ขณะที่ NAV เพิ่ม ~31% และ class NT ของกองเดียวกันรายงาน 30.96%; พบ 19 class; ถ้า class นั้นมีผลตอบแทนช่วงอื่นเป็น 0.00 พอดี จะแสดงเป็นว่างด้วย | แสดงเป็นว่าง | `perf_zero_vs_nav` |
| ผลตอบแทนที่ ก.ล.ต. รายงานต่ำกว่าการเปลี่ยนของ NAV เกิน 2 จุด | ผลตอบแทนรวมเงินปันผลต้องไม่ต่ำกว่าราคา จึงอธิบายด้วยปันผลไม่ได้ | แสดงค่าตามรายงาน + ธงเตือน | `ret_below_nav` |
| ระดับความเสี่ยง `RS81`/`RS8+` | ระดับ 8+ (สูงกว่า 8) เดิมถูกแปลงเป็น 81 | `risk_level` = 8 และ `risk_label` = "8+" | – |
| ลงทุนขั้นต่ำไม่ใช่บาทชัดเจน | `minimum_sub_cur` เป็น USD (52 class), มีข้อความหน่วย, หรือค่า 0 ที่ไม่ระบุว่า "ไม่กำหนด" | `min_subscription` ว่าง + `min_sub_note` อธิบาย ("ไม่กำหนด" = 0 บาท พร้อมหมายเหตุ) | `min_sub_unclear` |
| ค่าธรรมเนียมรวมที่เก็บจริงเป็น 0 | 165 class; อาจเป็นยังไม่มีข้อมูลหรือยกเว้น | แสดงตามรายงาน + ธง (ไม่ควรตีความว่าเป็นกองที่ถูกที่สุด) | `fee_ter_zero` |
| ค่ารวม < ค่าจัดการ / เก็บจริง > ตัวเลขสูงสุด / นอกช่วง / NAV ไม่ตามเวลา / ผลตอบแทนหรือความผันผวนสูงผิดปกติ | ตรวจความสมเหตุสมผล; ค่ารวมกับค่าจัดการอาจเป็นคนละช่วงเวลา และค่าใช้จ่ายจริงอาจรวมรายการที่ประมาณการไม่ได้ | แสดงตามรายงาน + ธง | `ter_lt_mgmt`, `fee_actual_gt_max`, `fee_out_of_range`, `nav_stale`, `ret_extreme` |

- **ค่าธรรมเนียมและ VAT:** รูปแบบตัวเลขเพียงอย่างเดียวพิสูจน์ไม่ได้ว่าแต่ละกองรวมหรือไม่รวม VAT ต่างกันอย่างไร จึงไม่ปรับค่าอัตโนมัติ หน้าเว็บเตือนให้ตรวจหมายเหตุใน Fact Sheet ของแต่ละกองก่อนเทียบ ตัวอย่าง [Fact Sheet PRINCIPAL BARMF](https://www.principal.th/sites/default/files/fund-documents/Thailand%20Site/th_PRINCIPAL_BARMF_FFS.pdf) ระบุว่าค่าธรรมเนียมรวมภาษีแล้ว และค่าใช้จ่ายรวมเก็บจริง 2.5498% สูงกว่าตัวเลขสูงสุด 2.14% เพราะตัวเลขสูงสุดครอบคลุมเฉพาะค่าใช้จ่ายที่ประมาณการได้ ส่วนเก็บจริงรวมค่าใช้จ่ายที่ประมาณการไม่ได้ด้วย (หน้า 1 และ 4)
- [Fact Sheet ES-CHINAA-SSF](https://www.eastspring.co.th/THDocs/FS/31F_03.pdf) หน้า 2 ระบุค่าจัดการเก็บจริง 1.6050% และค่าใช้จ่ายรวม 1.0310% โดยหมายเหตุบอกว่าค่ารวมเป็นของรอบปีบัญชี 1 มี.ค. 2568–28 ก.พ. 2569 จึงไม่ควรสมมติว่าเป็นอัตราปัจจุบันในช่วงเดียวกับค่าจัดการ ตัวอย่างนี้แสดงเหตุที่ระบบงดคำนวณค่าใช้จ่ายต่อปีเป็นบาทเมื่อเจอธง `ter_lt_mgmt`
- ธงทุกตัวแปลว่า "ควรตรวจกับ Fact Sheet" ไม่ใช่ข้อสรุปว่าข้อมูลผิด; ข้อความธงอยู่ที่ `scripts/data_quality.py` (`FLAG_TEXT`) และ `web/src/dq.ts` (เทสต์ `tests/test_dq_flags_sync.py` บังคับให้ตรงกัน)

## ลักษณะของ class (`class_detail`)
คอลัมน์ `class_detail` คือคำอธิบายชนิดหน่วยลงทุนที่ บลจ. รายงานต่อ ก.ล.ต. (`fund_class_detail`) แสดงตามต้นฉบับ เช่น "ชนิดเงินลงทุนเดิม" "ชนิดรองรับกองทุนสำรองเลี้ยงชีพ"
ระบบ **ไม่จัดกลุ่มหรือตีความ** ข้อความนี้เป็นป้าย (เคยทดลองจัดกลุ่มแล้วนำออกเมื่อ 2569-10-15 เพราะยังยืนยันกับเอกสารทางการไม่ได้) ผู้ลงทุนต้องอ่านเงื่อนไขการซื้อของแต่ละ class จากหนังสือชี้ชวน

## ป้ายประเภทกองทุนเพื่อการลดหย่อนภาษีในเว็บ
เว็บและ API แสดง `tax_type` เฉพาะประเภทที่แน่ใจ คือ ก.ล.ต. ระบุไว้เอง (`tax_type_confidence = high`: SSF 398, ThaiESG 44 class) หรือตรวจตรงกับรายงาน/เอกสารของ ก.ล.ต. (`verified_status` ขึ้นต้นด้วย `sec_`: RMF 424 class)
ประเภทที่จัดจากชื่ออย่างเดียวและยังไม่ยืนยัน (ThaiESGX ทั้งหมด 123 class, RMF/SSF/ThaiESG บางส่วน) เว็บไม่แสดงป้ายและ API ส่ง `tax_type = null` ค่าเต็มยังอยู่ใน `data/*.csv` สำหรับการตรวจภายใน
