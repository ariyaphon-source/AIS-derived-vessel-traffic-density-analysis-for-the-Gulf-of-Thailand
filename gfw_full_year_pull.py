# ============================================================
# Global Fishing Watch API - Gulf of Thailand FULL YEAR PULL
# ใช้งานใน Google Colab
# ============================================================
#
# วิธีใช้:
# 1. รันต่อจาก gfw_gulf_thailand_test.py เดิม (token เดิมใช้ได้)
#    หรือวางใน notebook ใหม่ก็ได้ (ใส่ ACCESS_TOKEN ใหม่)
# 2. ปรับ YEAR ด้านล่างตามปีที่ต้องการ (แนะนำ 2023 หรือ 2024
#    เพราะ AIS coverage ใน SEA ดีขึ้นตั้งแต่ 2022)
# 3. รัน — จะดึงทีละเดือน (กัน request ใหญ่เกินไป/timeout)
#    แล้วรวมเป็นไฟล์เดียว
#
# หมายเหตุ: ใช้ spatial-resolution = HIGH (0.01deg ~ 1.1km) ตามที่
# ควรใช้จริงสำหรับงานตีพิมพ์ (ต่างจาก sample เดิมที่ใช้ LOW เพื่อทดสอบ)
# ผลคือขนาดข้อมูล/เวลาโหลดจะมากขึ้นมาก จึงต้อง chunk เป็นรายเดือน
# ============================================================

import requests
import pandas as pd
import time
import calendar

# -------------------- 1) ใส่ TOKEN ตรงนี้ --------------------
ACCESS_TOKEN = "PASTE_YOUR_GFW_TOKEN_HERE"
# ----------------------------------------------------------------

HEADERS = {
    "Authorization": f"Bearer {ACCESS_TOKEN}",
    "Content-Type": "application/json",
}

BASE_URL = "https://gateway.api.globalfishingwatch.org"

# -------------------- 2) ตั้งค่าการดึงข้อมูล --------------------
YEAR = 2025                  # ปีล่าสุดที่มีข้อมูลเต็มปี (แก้ตามต้องการ)
                              # หมายเหตุ: ตั้งแต่ 26 ก.พ. 2026 GFW เปลี่ยน
                              # data pipeline เป็น v4 (ใช้ Kpler แทน AIS
                              # service เดิม) methodology อาจต่างจากข้อมูล
                              # ปี 2023 ที่เคยดึงไปแล้ว — ถ้าจะเทียบข้าม
                              # ปีต้องระบุเป็น limitation ใน paper
SPATIAL_RES = "HIGH"         # HIGH = 0.01deg (~1.1km) เหมาะกับงานตีพิมพ์
                              # ถ้า timeout บ่อย ลองเปลี่ยนกลับเป็น LOW ก่อน
DATASET = "public-global-fishing-effort:latest"

GEOJSON_BBOX = {
    "type": "Polygon",
    "coordinates": [[
        [99.5, 11.0],
        [102.0, 11.0],
        [102.0, 13.5],
        [99.5, 13.5],
        [99.5, 11.0],
    ]]
}
# หมายเหตุสำคัญ: bounding box นี้ถูกปรับให้แคบลงจากเดิม (99.0-104.5E,
# 5.5-13.5N) เพื่อ "ตัดออก" พื้นที่ทางใต้/ตะวันออกที่ทับซ้อนกับ
# Thailand-Cambodia Overlapping Claims Area (OCA, ~10.0-10.5N, 103.4-
# 104.0E) และพื้นที่ใกล้พรมแดนทางทะเลอื่นๆ ที่อาจมีประเด็น sensitive
# ทางภูมิรัฐศาสตร์ — ขอบเขตใหม่ครอบคลุมเฉพาะอ่าวไทยตอนบน-กลาง
# (กรุงเทพ, แหลมฉบัง, สัตหีบ, มาบตาพุด, ระยอง) ซึ่งเป็น scope ที่
# ตั้งใจศึกษาจริงตามที่ตัดสินใจไว้


def fetch_month(year, month, max_retries=3):
    """ดึงข้อมูล 1 เดือน พร้อม retry เมื่อเจอ rate limit (429)"""
    start = f"{year}-{month:02d}-01"
    last_day = calendar.monthrange(year, month)[1]
    end = f"{year}-{month:02d}-{last_day:02d}"

    url = f"{BASE_URL}/v3/4wings/report"
    params = {
        "spatial-resolution": SPATIAL_RES,
        "temporal-resolution": "DAILY",
        "group-by": "FLAG",
        "datasets[0]": DATASET,
        "date-range": f"{start},{end}",
        "format": "JSON",
    }
    body = {"geojson": GEOJSON_BBOX}

    for attempt in range(max_retries):
        r = requests.post(url, headers=HEADERS, params=params, json=body)

        if r.status_code == 200:
            return r.json()
        elif r.status_code == 429:
            wait = 10 * (attempt + 1)
            print(f"  Rate limited (429) — รอ {wait} วินาทีแล้วลองใหม่...")
            time.sleep(wait)
        else:
            print(f"  เดือน {month}: Status {r.status_code} — {r.text[:300]}")
            return None

    print(f"  เดือน {month}: ล้มเหลวหลังลองครบ {max_retries} ครั้ง")
    return None


def flatten_result(result):
    """แปลง response JSON ที่ซ้อนกันให้เป็น list of dict (แถวข้อมูล)"""
    rows = []
    if not result:
        return rows
    for entry in result.get("entries", []):
        for dataset_key, records in entry.items():
            for rec in records:
                rec["dataset"] = dataset_key
                rows.append(rec)
    return rows


# ============================================================
# 3) ดึงข้อมูลทีละเดือน รวมทั้งปี
# ============================================================
all_rows = []

print(f"=== เริ่มดึงข้อมูล AIS อ่าวไทย ปี {YEAR} (resolution: {SPATIAL_RES}) ===\n")

for month in range(1, 13):
    print(f"กำลังดึงเดือน {month:02d}/{YEAR}...")
    result = fetch_month(YEAR, month)
    rows = flatten_result(result)
    print(f"  ได้ {len(rows)} แถว")
    all_rows.extend(rows)
    time.sleep(2)  # เว้นจังหวะกัน rate limit สะสม

df = pd.DataFrame(all_rows)

print(f"\n=== เสร็จสิ้น ===")
print(f"จำนวนแถวข้อมูลทั้งหมด: {len(df)}")

if len(df) > 0:
    print("ช่วงวันที่:", df["date"].min(), "-", df["date"].max())
    print("จำนวนจุด (lat/lon) ที่ไม่ซ้ำ:", df[["lat", "lon"]].drop_duplicates().shape[0])
    print("รวมชั่วโมงกิจกรรมเรือทั้งหมด:", round(df["hours"].sum(), 2))
    print("\nแยกตามธงเรือ (flag) - Top 10:")
    print(df.groupby("flag")["hours"].sum().sort_values(ascending=False).head(10))
    print("\nแยกตามเดือน:")
    df["month"] = pd.to_datetime(df["date"]).dt.month
    print(df.groupby("month")["hours"].sum())

    out_path = f"gulf_thailand_ais_{YEAR}_scoped.csv"
    df.to_csv(out_path, index=False)
    print(f"\nบันทึกไฟล์ {out_path} แล้ว ({len(df)} แถว)")
    print("(ไฟล์นี้ใช้ bounding box ที่ตัดพื้นที่ OCA ออกแล้ว —")
    print(" ไม่ใช่ไฟล์เดิมที่ครอบคลุมทั้งอ่าวไทย)")
    print("ไฟล์นี้พร้อมใช้เป็น dataset หลักสำหรับ paper")
else:
    print("ไม่ได้ข้อมูลเลย — เช็ค token/parameter หรือดู error message ด้านบน")


# ============================================================
# หมายเหตุสำคัญ:
# 1. ถ้า HIGH resolution ทำให้ request timeout/ช้ามาก ให้ลองเปลี่ยน
#    SPATIAL_RES = "LOW" ก่อน (ยังใช้เป็น full-year dataset ได้
#    แต่ต้องระบุ limitation เรื่อง resolution ใน paper)
# 2. ถ้าต้องการหลายปี ให้ห่อ loop นี้ด้วย for YEAR in [2022,2023,2024]
#    แต่ระวังเวลารันจะนานขึ้นมาก และอาจโดน rate limit บ่อยขึ้น
# 3. ไฟล์ CSV จะมีขนาดใหญ่กว่า sample เดิมมาก — ควร sanity check
#    ด้วยการเปิดดูใน pandas ก่อนใช้ต่อ (เช่น df.isnull().sum(),
#    df.describe())
# ============================================================
