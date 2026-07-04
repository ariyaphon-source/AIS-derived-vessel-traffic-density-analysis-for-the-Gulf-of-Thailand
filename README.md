# Gulf of Thailand AIS Vessel Traffic Density Analysis

Reproducible data pipeline and analysis scripts supporting the
manuscript "Vessel Traffic Density, Gulf of Thailand" (working title),
submitted to *The Journal of Navigation*.

## Author

Ariyaphon Theerachutikun
Education Division, Royal Thai Naval Academy, Samut Prakan, Thailand
ORCID: 0009-0006-3345-2929
ariyaphon@gmail.com

## Overview

This repository contains the scripts used to retrieve, process, and
analyse AIS-derived vessel traffic data for the upper Gulf of
Thailand, using Global Fishing Watch's public API. The pipeline
identifies traffic density hotspots via kernel density estimation and
cross-references them against Vessel Traffic Service operational
coverage and official port statistics.

## Requirements

- Python 3.9+
- Packages: `requests`, `pandas`, `numpy`, `scipy`, `matplotlib`
- A free Global Fishing Watch API access token
  (register at https://globalfishingwatch.org/our-apis/)

Install dependencies:
```
pip install requests pandas numpy scipy matplotlib
```

## Scripts (run in order)

1. **`gfw_full_year_pull.py`**
   Retrieves a full calendar year of AIS-derived apparent fishing
   effort data from the GFW 4Wings API, for a defined bounding box,
   month by month. Requires a GFW API token pasted into the
   `ACCESS_TOKEN` variable. Outputs
   `gulf_thailand_ais_<YEAR>_scoped.csv`.

2. **`gfw_cri_hotspot_analysis.py`**
   Loads the pulled dataset, aggregates traffic density per grid
   cell, identifies the highest-density locations, and produces a
   kernel-density-estimated hotspot map (exported at 300 dpi TIFF).
   Outputs `gulf_thailand_density_grid_<YEAR>_scoped.csv`,
   `gulf_thailand_top_hotspots_<YEAR>_scoped.csv`, and the figure file.

3. **`mtp_vts_distance_check.py`**
   Computes the great-circle distance from each grid cell in the Map
   Ta Phut/Sattahip area to a reference coordinate representing the
   Map Ta Phut Navigation Coordination and Facilitation Centre, and
   classifies cells into Vessel Traffic Service coverage zones.
   Outputs `mtp_lobe_vts_distance_analysis_<YEAR>_scoped.csv`.

4. **`pat_ais_validation.py`**
   Cross-references AIS-derived vessel-hours for the Bangkok Port and
   Laem Chabang Port approaches against official Port Authority of
   Thailand vessel-call statistics as an indicative consistency check.

## Data Availability

Raw AIS-derived data are retrieved on demand from the Global Fishing
Watch public API and are not redistributed in this repository, in
accordance with GFW's terms of use. Any user with a free GFW API
token can reproduce the exact dataset used in this study by running
`gfw_full_year_pull.py` with the same date range and bounding box
parameters specified in the script.

## Notes on Scope

The bounding box used excludes waters associated with the
Thailand–Cambodia Overlapping Claims Area; see the manuscript
(Section 2.2) for the rationale.

## Citation

If you use this pipeline, please cite the associated manuscript
(citation details to be added upon publication) and Global Fishing
Watch's underlying data (Kroodsma et al., 2018, *Science*).

## Licence

[To be determined by author — e.g. MIT License for code]

