# ============================================================
# Ground-Truth Validation: AIS-Derived Density vs PAT Official
# Vessel-Call Statistics (Bangkok Port vs Laem Chabang Port)
# ============================================================
#
# วัตถุประสงค์: ตรวจสอบว่า AIS-derived traffic density (จาก GFW) มี
# ทิศทางสอดคล้องกับสถิติ vessel call ทางการของ PAT หรือไม่ เป็น
# consistency check เบื้องต้น (ไม่ใช่ formal statistical validation
# เนื่องจากมีแค่ 2 ท่าเรือที่เปรียบเทียบได้ในขอบเขตการศึกษา)
#
# ใช้งานใน Colab: รันต่อจาก gfw_cri_hotspot_analysis.py
# (ต้องมี gulf_thailand_density_grid_2025_scoped.csv อยู่แล้ว)
# ============================================================

import pandas as pd
import numpy as np

density = pd.read_csv("gulf_thailand_density_grid_2025_scoped.csv")
print("จำนวน grid cell ทั้งหมด:", len(density))

# ============================================================
# 1) กำหนด bounding box ของ Bangkok Port bar channel vs Laem Chabang
# ============================================================
# Bangkok Port (Zone A / Chao Phraya bar approach)
# แก้ไข: bbox เดิม (13.00-13.10N, 100.55-100.90E) ผิดตำแหน่ง จริงๆ
# ไปทับพื้นที่ใกล้ Laem Chabang แทน ปากแม่น้ำเจ้าพระยาจริง (Pak Nam)
# อยู่ที่ 13°29'N, 100°36'E (13.483, 100.605) ตามแหล่งอ้างอิงการเดินเรือ
bangkok_bbox = {
    "lat_min": 13.35, "lat_max": 13.60,
    "lon_min": 100.45, "lon_max": 100.70,
}

# Laem Chabang Port (พิกัดกลาง ~13.07N, 100.90E จากหลายแหล่งอ้างอิง
# สาธารณะ เฉลี่ยแล้วใช้กรอบครอบคลุม) — bbox เดิมถูกต้องอยู่แล้ว
laem_chabang_bbox = {
    "lat_min": 13.02, "lat_max": 13.12,
    "lon_min": 100.85, "lon_max": 100.95,
}


def sum_hours_in_bbox(df, bbox):
    subset = df[
        (df["lat"] >= bbox["lat_min"]) & (df["lat"] <= bbox["lat_max"]) &
        (df["lon"] >= bbox["lon_min"]) & (df["lon"] <= bbox["lon_max"])
    ]
    return subset["total_hours"].sum(), len(subset)


bkk_hours, bkk_cells = sum_hours_in_bbox(density, bangkok_bbox)
lcb_hours, lcb_cells = sum_hours_in_bbox(density, laem_chabang_bbox)

print("\n=== AIS-Derived Traffic Density (2025, scoped) ===")
print(f"Bangkok Port bbox (corrected): {bkk_hours:,.1f} vessel-hours ({bkk_cells} cells)")
print(f"Laem Chabang Port bbox:        {lcb_hours:,.1f} vessel-hours ({lcb_cells} cells)")

# --- Diagnostic: แสดง top 5 hotspot cells ภายใน Bangkok bbox ใหม่
# เพื่อยืนยันว่าจับจุดปากแม่น้ำเจ้าพระยาได้ถูกต้อง (ควรเห็นพิกัด
# ใกล้ 13.4-13.5N, 100.5-100.6E ไม่ใช่ 13.0-13.1N อีกต่อไป)
bkk_subset = density[
    (density["lat"] >= bangkok_bbox["lat_min"]) & (density["lat"] <= bangkok_bbox["lat_max"]) &
    (density["lon"] >= bangkok_bbox["lon_min"]) & (density["lon"] <= bangkok_bbox["lon_max"])
].sort_values("total_hours", ascending=False)
print("\nTop 5 cells ภายใน Bangkok bbox (ตรวจสอบตำแหน่ง):")
print(bkk_subset[["lat", "lon", "total_hours"]].head(5).to_string(index=False))

ais_ratio = lcb_hours / bkk_hours if bkk_hours > 0 else float("nan")
print(f"\nAIS-derived ratio (Laem Chabang : Bangkok) = {ais_ratio:.2f} : 1")

# ============================================================
# 2) เทียบกับสถิติทางการ PAT (Annual Report FY2568/2025)
# ============================================================
pat_bangkok_calls = 4460
pat_laemchabang_calls = 10653

pat_ratio = pat_laemchabang_calls / pat_bangkok_calls
print(f"PAT official ratio (Laem Chabang : Bangkok) = {pat_ratio:.2f} : 1")

print("\n=== Consistency Check ===")
print(f"AIS-derived ratio:  {ais_ratio:.2f}")
print(f"PAT official ratio: {pat_ratio:.2f}")
diff_pct = abs(ais_ratio - pat_ratio) / pat_ratio * 100
print(f"Difference: {diff_pct:.1f}%")

if diff_pct < 30:
    print("-> ทิศทางสอดคล้องกันในระดับที่ยอมรับได้ (same order of magnitude)")
else:
    print("-> ทิศทางต่างกันมาก ควรตรวจสอบ bounding box หรือ dataset เพิ่มเติม")

# ============================================================
# หมายเหตุสำคัญสำหรับ paper:
# ============================================================
# 1. นี่คือ consistency check ด้วย n=2 (ท่าเรือ) เท่านั้น ไม่ใช่
#    การ validate เชิงสถิติที่มีนัยสำคัญ (ต้องการ n มากกว่านี้สำหรับ
#    correlation coefficient ที่มีความหมาย) ต้องเขียนกำกับให้ชัดเจน
#    ว่าเป็น "preliminary/indicative" ไม่ใช่ "validated"
# 2. Bounding box ของ Bangkok/Laem Chabang เป็นค่าประมาณจากแหล่ง
#    สาธารณะหลายแหล่ง ไม่ใช่ port boundary ทางการ อาจมี overlap
#    หรือ mismatch เล็กน้อยกับ fairway/anchorage ที่แท้จริง
# 3. PAT vessel call = จำนวนเรือที่เทียบท่า (docking) ส่วน AIS-derived
#    hours = สะสมเวลาที่เรือทุกลำอยู่ในพื้นที่ (รวม transit ที่ไม่ได้
#    dock ด้วย) สองอย่างนี้วัดคนละมิติ ไม่ใช่ 1:1 mapping — ทิศทาง
#    เดียวกัน (proportionality) คือสิ่งที่เช็คได้ ไม่ใช่ magnitude ตรงกัน
# ============================================================
