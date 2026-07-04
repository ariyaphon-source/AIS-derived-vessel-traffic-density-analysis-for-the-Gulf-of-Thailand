# ============================================================
# Gulf of Thailand - CRI (Collision Risk Index) & Hotspot Mapping
# ต่อยอดจาก gfw_full_year_pull.py (full-year dataset, 246K+ แถว)
# ใช้งานใน Google Colab
# ============================================================
#
# วิธีใช้:
# 1. รันสคริปต์ gfw_full_year_pull.py ก่อน จนได้
#    gulf_thailand_ais_2025_full.csv
# 2. Copy โค้ดนี้ไปวางในเซลล์ถัดไป แล้วรัน
# ============================================================

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# ติดตั้ง package ที่จำเป็น (รันครั้งแรกครั้งเดียว)
# !pip install scipy -q

from scipy.stats import gaussian_kde

# -------------------- 1) โหลดข้อมูล --------------------
CSV_PATH = "gulf_thailand_ais_2025_scoped.csv"   # scope ตัด OCA ออกแล้ว
df = pd.read_csv(CSV_PATH)

print("จำนวนข้อมูลทั้งหมด (ก่อนทำความสะอาด):", len(df))
print(df.head())


# ============================================================
# 1.1) จัดการ flag ว่างเปล่า/ไม่ระบุสัญชาติ
# ============================================================
# พบว่ามีสัดส่วนสูงพอสมควร (~122,439 ชั่วโมง จาก proof-of-concept
# รอบก่อน) เป็น unidentified flag ต้องตัดสินใจว่าจะ:
#   (a) เก็บไว้แต่ label ชัดเจนว่า "UNKNOWN" (แนะนำ - ไม่ทิ้งข้อมูล)
#   (b) ตัดทิ้งถ้าจะโฟกัสเฉพาะ traffic ที่ identify สัญชาติได้แน่นอน
# สคริปต์นี้เลือก (a) เป็นค่าเริ่มต้น เพื่อไม่ให้เสียข้อมูล traffic
# density โดยรวม (เพราะเป้าหมายคือ hotspot ไม่ใช่ flag-state analysis)
df["flag"] = df["flag"].fillna("UNKNOWN")
df.loc[df["flag"].str.strip() == "", "flag"] = "UNKNOWN"

n_unknown = (df["flag"] == "UNKNOWN").sum()
pct_unknown = n_unknown / len(df) * 100
print(f"\nแถวที่ไม่ระบุธงเรือ (UNKNOWN): {n_unknown} ({pct_unknown:.1f}%)")
print("-> ต้องรายงานตัวเลขนี้ใน paper เป็น data limitation")

print("\nสรุปตามธงเรือ (หลังทำความสะอาด) - Top 10:")
print(df.groupby("flag")["hours"].sum().sort_values(ascending=False).head(10))


# ============================================================
# 2) Traffic Density Index (proxy สำหรับ CRI เบื้องต้น)
# ============================================================
# หมายเหตุ: CRI แบบเต็มรูปแบบ (เช่น Ship Domain / VCRO / CPA-TCPA model)
# ต้องใช้ trajectory data แบบ point-to-point (lat/lon ต่อ timestamp
# ของแต่ละลำ) ซึ่ง fishing-effort dataset ระดับ grid-cell ไม่มีให้
#
# ในขั้นนี้เราจึงคำนวณ "Traffic Density Index" เป็น proxy:
#   - ยิ่งมี vessel-hours สะสมสูงในจุดเดียวกัน = ยิ่งมีความเสี่ยงชนกันสูง
# ============================================================

# รวมชั่วโมงกิจกรรมต่อ grid cell (ไม่แยกวัน/ธงเรือ) เพื่อดู pattern สะสมทั้งปี
density = (
    df.groupby(["lat", "lon"])
    .agg(total_hours=("hours", "sum"), total_vessel_ids=("vesselIDs", "sum"))
    .reset_index()
)

print(f"\nจำนวน grid cell ที่ไม่ซ้ำหลัง aggregate: {len(density)}")

# Normalize เป็น 0-1
density["density_score"] = (
    density["total_hours"] - density["total_hours"].min()
) / (density["total_hours"].max() - density["total_hours"].min())

# จัดอันดับ hotspot 15 อันดับแรก (เพิ่มจาก 10 เพราะ dataset ใหญ่ขึ้นมาก)
top_hotspots = density.sort_values("total_hours", ascending=False).head(15)
print("\n=== Top 15 Traffic Density Hotspots (Full Year 2025) ===")
print(top_hotspots[["lat", "lon", "total_hours", "total_vessel_ids", "density_score"]])

top_hotspots.to_csv("gulf_thailand_top_hotspots_2025_scoped.csv", index=False)
density.to_csv("gulf_thailand_density_grid_2025_scoped.csv", index=False)
print("\nบันทึก gulf_thailand_top_hotspots_2025_scoped.csv และ")
print("gulf_thailand_density_grid_2025_scoped.csv แล้ว")


# ============================================================
# 3) Kernel Density Estimation (KDE) สำหรับ Hotspot Map
# ============================================================
# หมายเหตุ: dataset นี้ใหญ่กว่า proof-of-concept เดิมมาก (หมื่น grid
# cells แทนหลักร้อย) gaussian_kde จาก scipy อาจช้า/ใช้ RAM เยอะถ้า
# จุดข้อมูลมากเกินไป -> ถ้า cell เยอะเกิน ~20,000 จุด แนะนำ subsample
# หรือลด grid resolution ของแผนที่ผลลัพธ์ (ไม่ใช่ข้อมูลนำเข้า) ลง
# ============================================================

MAX_POINTS_FOR_KDE = 20000
if len(density) > MAX_POINTS_FOR_KDE:
    print(f"\nจำนวนจุด ({len(density)}) เกิน {MAX_POINTS_FOR_KDE} "
          f"-> สุ่มตัวอย่างแบบถ่วงน้ำหนักตาม total_hours เพื่อความเร็ว")
    density_kde = density.sample(
        n=MAX_POINTS_FOR_KDE, weights="total_hours", random_state=42
    )
else:
    density_kde = density

lats = density_kde["lat"].values
lons = density_kde["lon"].values
weights = density_kde["total_hours"].values

kde = gaussian_kde(np.vstack([lons, lats]), weights=weights, bw_method=0.1)

# Grid สำหรับ plot (ครอบคลุมอ่าวไทย) — ลดความละเอียดของ plot grid
# ลงเล็กน้อย (150->120) เพื่อความเร็ว ไม่กระทบข้อมูลนำเข้า
grid_lon = np.linspace(99.5, 102.0, 120)
grid_lat = np.linspace(11.0, 13.5, 120)
grid_lon_mesh, grid_lat_mesh = np.meshgrid(grid_lon, grid_lat)
grid_coords = np.vstack([grid_lon_mesh.ravel(), grid_lat_mesh.ravel()])

kde_values = kde(grid_coords).reshape(grid_lon_mesh.shape)

# -------------------- 4) Plot Hotspot Map --------------------
fig, ax = plt.subplots(figsize=(11, 11))
contour = ax.contourf(grid_lon_mesh, grid_lat_mesh, kde_values, levels=20, cmap="YlOrRd")
ax.scatter(
    top_hotspots["lon"], top_hotspots["lat"],
    s=80, c="blue", marker="x", linewidths=1.5,
    label="Top 15 hotspot points"
)
ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_title("Gulf of Thailand: Vessel Traffic Density Hotspot Map\n"
              "(Full Year 2025, OCA-excluded - AIS Fishing-Effort Derived Proxy)")
plt.colorbar(contour, label="Density (KDE, weighted by vessel-hours)")
ax.legend(loc="upper right")
plt.tight_layout()
plt.savefig("gulf_thailand_hotspot_map_2025_scoped.tif", dpi=300,
            format="tiff", pil_kwargs={"compression": "tiff_lzw"})
plt.show()
print("\nบันทึกไฟล์ gulf_thailand_hotspot_map_2025_scoped.tif แล้ว")
print("(300 dpi, format TIFF ตามเกณฑ์ JoNav สำหรับ Colour Halftone Artwork)")
print("\n*** สำคัญ: อย่าคลิกขวา Save image จากภาพที่โชว์ในเซลล์นี้ ***")
print("*** ให้ไปที่แถบ Files (ไอคอนโฟลเดอร์) ด้านซ้าย Colab แล้ว ***")
print("*** ดาวน์โหลดไฟล์ .tif ตัวจริงแทน ***")



# ============================================================
# หมายเหตุสำคัญสำหรับ Paper (Journal of Navigation):
# ============================================================
# 1. นี่ยังเป็น fishing-effort dataset เท่านั้น (ไม่ใช่ vessel-
#    presence เต็มรูปแบบ) — ต้องระบุใน Limitations
#
# 2. Traffic Density Index != CRI ที่แท้จริง
#    CRI มาตรฐานต้องใช้ pairwise vessel encounter data (CPA, TCPA)
#    ซึ่งต้องมี trajectory แบบจุดต่อจุด
#
# 3. สัดส่วนข้อมูลที่ไม่ระบุธงเรือ (UNKNOWN) จะถูกพิมพ์ออกมาตอนรัน
#    (ดูค่า pct_unknown ใน output) — ต้องรายงานตัวเลขนี้ใน paper
#    เป็น data quality limitation
#
# 4. Dataset นี้ใช้ spatial-resolution HIGH (0.01deg ~ 1.1km) ตาม
# 4. Dataset นี้ใช้ spatial-resolution HIGH (0.01deg ~ 1.1km) ตาม
#    มาตรฐานงานตีพิมพ์ ครอบคลุมทั้งปี 2025 (546,325 แถวก่อน cleaning)
#    ใช้ GFW data pipeline v4 (Kpler-based, เปิดใช้ 26 ก.พ. 2026)
#    -> ต้องระบุ pipeline version นี้ใน Methodology section
# ============================================================
