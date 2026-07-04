# ============================================================
# Map Ta Phut/Sattahip Hotspot - VTS Coverage Distance Analysis
# ต่อยอดจาก gfw_cri_hotspot_analysis.py (ต้องมี
# gulf_thailand_density_grid_2025_scoped.csv อยู่แล้ว)
# ใช้งานใน Google Colab
# ============================================================
#
# วัตถุประสงค์: กรองเฉพาะ hotspot lobe บริเวณ Map Ta Phut/Sattahip
# แล้วคำนวณระยะทางจริง (nautical miles) จากตำแหน่งเรดาร์ VTS มาบตาพุด
# ไปยังแต่ละจุด hotspot เพื่อจำแนกว่าอยู่ในโซนไหนตามข้อมูล VTS ที่ได้รับ:
#   - Approach Zone (ปฏิบัติจริง): 12-15 nm จาก fairway buoy
#   - High-Resolution Tracking: 12-24 nm
#   - Theoretical Max Detection: 24-48 nm
#   - นอกระยะทั้งหมด: > 48 nm
# ============================================================

import pandas as pd
import numpy as np

# -------------------- 1) โหลดข้อมูล density grid --------------------
density = pd.read_csv("gulf_thailand_density_grid_2025_scoped.csv")
print("จำนวน grid cell ทั้งหมด:", len(density))

# -------------------- 2) กรองเฉพาะพื้นที่ Map Ta Phut/Sattahip lobe -----
# จากภาพ KDE เดิม lobe ที่สองอยู่ราว lat 12.0-12.6, lon 101.0-101.5
# (ปรับ bounding box นี้ได้ถ้าต้องการกรองกว้าง/แคบกว่านี้)
mtp_lobe = density[
    (density["lat"] >= 12.0) & (density["lat"] <= 12.6) &
    (density["lon"] >= 101.0) & (density["lon"] <= 101.5)
].copy()

print(f"จำนวน grid cell ในพื้นที่ Map Ta Phut/Sattahip lobe: {len(mtp_lobe)}")

if len(mtp_lobe) == 0:
    print("ไม่พบข้อมูลในกรอบพิกัดนี้ — ลองปรับ bounding box ให้กว้างขึ้น")
else:
    top_in_lobe = mtp_lobe.sort_values("total_hours", ascending=False).head(10)
    print("\n=== Top 10 Hotspot ภายใน Map Ta Phut/Sattahip Lobe ===")
    print(top_in_lobe[["lat", "lon", "total_hours", "total_vessel_ids"]])


# ============================================================
# 3) คำนวณระยะทาง Haversine จาก VTS Radar Reference Point
# ============================================================
# ตำแหน่งอ้างอิงเรดาร์ VTS มาบตาพุด (จาก Google Plus Code: M47M+XHV,
# Map Ta Phut, Mueang Rayong District — decode ด้วย reference เมือง
# Map Ta Phut แล้วได้พิกัดแม่นยำ)
VTS_RADAR_LAT = 12.664987499999999   # 12°39'54"N
VTS_RADAR_LON = 101.13392187500001   # 101°08'02"E

def haversine_nm(lat1, lon1, lat2, lon2):
    """คำนวณระยะทางระหว่าง 2 จุดพิกัด หน่วยเป็นไมล์ทะเล (nautical miles)"""
    R_km = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2)**2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2)**2
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    dist_km = R_km * c
    dist_nm = dist_km / 1.852  # 1 nm = 1.852 km
    return dist_nm


def classify_zone(distance_nm):
    """จำแนกโซนตามข้อมูล VTS ที่ได้รับ"""
    if distance_nm <= 15:
        return "Approach Zone (ปฏิบัติจริง, <=15nm)"
    elif distance_nm <= 24:
        return "High-Resolution Tracking (12-24nm)"
    elif distance_nm <= 48:
        return "Theoretical Max Detection (24-48nm)"
    else:
        return "นอกระยะตรวจจับทั้งหมด (>48nm)"


mtp_lobe["distance_nm_from_vts"] = haversine_nm(
    mtp_lobe["lat"], mtp_lobe["lon"], VTS_RADAR_LAT, VTS_RADAR_LON
)
mtp_lobe["vts_zone"] = mtp_lobe["distance_nm_from_vts"].apply(classify_zone)

# -------------------- 4) สรุปผล --------------------
print("\n=== Top 10 Hotspot พร้อมระยะห่างจาก VTS Radar และการจำแนกโซน ===")
top_with_dist = mtp_lobe.sort_values("total_hours", ascending=False).head(10)
print(top_with_dist[["lat", "lon", "total_hours", "distance_nm_from_vts", "vts_zone"]]
      .to_string(index=False))

print("\n=== สัดส่วนพื้นที่ (จำนวน grid cell) แยกตามโซน VTS ===")
zone_counts = mtp_lobe["vts_zone"].value_counts()
print(zone_counts)

print("\n=== สัดส่วน traffic (total_hours) แยกตามโซน VTS ===")
zone_hours = mtp_lobe.groupby("vts_zone")["total_hours"].sum().sort_values(ascending=False)
print(zone_hours)
pct_outside_approach = (
    mtp_lobe.loc[mtp_lobe["vts_zone"] != "Approach Zone (ปฏิบัติจริง, <=15nm)", "total_hours"].sum()
    / mtp_lobe["total_hours"].sum() * 100
)
print(f"\n% ของ traffic (vessel-hours) ในพื้นที่นี้ที่อยู่ 'นอก' Approach Zone ปฏิบัติจริง: {pct_outside_approach:.1f}%")

mtp_lobe.to_csv("mtp_lobe_vts_distance_analysis_2025_scoped.csv", index=False)
print("\nบันทึกไฟล์ mtp_lobe_vts_distance_analysis_2025_scoped.csv แล้ว")


# ============================================================
# หมายเหตุสำคัญสำหรับการเขียน paper:
# ============================================================
# 1. VTS_RADAR_LAT/LON มาจากการ decode Google Plus Code (M47M+XHV)
#    ที่ผู้ใช้ระบุว่าเป็นตำแหน่งเรดาร์ VTS จริง — แม่นยำกว่าค่าประมาณ
#    จาก LNG Terminal ที่ใช้ในรอบก่อนหน้า
# 2. ผลลัพธ์นี้บอกได้แค่ "ระยะทางเชิงเรขาคณิต" ไม่ได้คำนึงถึง line-of-
#    sight/terrain/curvature ที่แท้จริงของเรดาร์ (theoretical range
#    ที่ให้มาก็เป็นค่าตามสเปกอยู่แล้ว จึงใช้เทียบกันได้ในระดับหนึ่ง)
# 3. ควรเขียนผลลัพธ์เป็น "ส่วนหนึ่งของ traffic อยู่นอก operational
#    approach zone" ไม่ใช่ "ไม่มี VTS coverage เลย" — ตรงกับสิ่งที่
#    ข้อมูลแสดงจริง (nuanced claim ไม่ overclaim)
# ============================================================
