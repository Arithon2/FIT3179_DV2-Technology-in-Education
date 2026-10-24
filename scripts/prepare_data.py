"""
Author: Luke Downward
Date Last Modified: 24th of October 2026

This file builds the compact files in processed/ from the raw xlsx files in Data/.

Usage: python scripts/prepare_data.py [path-to-data-folder]
"""
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "Data"
OUT = ROOT / "processed"
OUT.mkdir(exist_ok=True)
PC_URL = "https://raw.githubusercontent.com/matthewproctor/australianpostcodes/master/australian_postcodes.csv"


def strip(s):
    # drops the "a ", "b " sort prefixes used in the ABS tables
    return re.sub(r"^[a-z] ", "", str(s)).strip()


# ACARA school profile 2025 
sp = pd.read_excel(RAW / "School_Profile_2008-2025.xlsx", sheet_name="SchoolProfile 2008-2025")
s = sp[sp["Calendar Year"] == 2025].copy()
s["postcode"] = s["Postcode"].astype(str).str.replace(".0", "", regex=False).str.zfill(4)
s["key"] = s["postcode"] + "|" + s["Suburb"].str.upper().str.strip()

# locality centroids (matthewproctor/australianpostcodes)
pc_file = RAW / "australian_postcodes.csv"
pc = pd.read_csv(pc_file if pc_file.exists() else PC_URL, dtype={"postcode": str},
                 usecols=["postcode", "locality", "long", "lat", "Lat_precise", "Long_precise"])
pc["lat"] = pc["Lat_precise"].where(pc["Lat_precise"].fillna(0) != 0, pc["lat"])
pc["long"] = pc["Long_precise"].where(pc["Long_precise"].fillna(0) != 0, pc["long"])
pc = pc[(pc["lat"] != 0) & (pc["long"] != 0)]
pc["postcode"] = pc["postcode"].str.zfill(4)
pc["key"] = pc["postcode"] + "|" + pc["locality"].str.upper().str.strip()
by_loc = pc.groupby("key")[["lat", "long"]].mean()
by_pc = pc.groupby("postcode")[["lat", "long"]].mean()

s["lat"] = s["key"].map(by_loc["lat"]).fillna(s["postcode"].map(by_pc["lat"]))
s["lon"] = s["key"].map(by_loc["long"]).fillna(s["postcode"].map(by_pc["long"]))
s = s.dropna(subset=["lat", "lon", "Total Enrolments"])
s = s[(s["lon"] > 112) & (s["lon"] < 155) & (s["lat"] < -9) & (s["lat"] > -45)]

schools = pd.DataFrame({
    "id": s["ACARA SML ID"], "name": s["School Name"], "state": s["State"],
    "sector": s["School Sector"], "type": s["School Type"],
    "remoteness": s["Geolocation"], "icsea": s["ICSEA"],
    "enrolments": s["Total Enrolments"].astype(int),
    "lat": s["lat"].round(3), "lon": s["lon"].round(3),
})
schools.to_csv(OUT / "schools_2025.csv", index=False)

# chart 01: sector scale
sec = schools.groupby("sector").agg(schools=("id", "count"), enrolments=("enrolments", "sum")).reset_index()
sec["avg_size"] = (sec["enrolments"] / sec["schools"]).round(0)
sec.to_csv(OUT / "sector_summary.csv", index=False)

# chart 08: enrolments and mean ICSEA on a 0.75 degree grid
g = schools.dropna(subset=["icsea"]).copy()
step = 0.75
g["gx"] = (g["lon"] // step) * step + step / 2
g["gy"] = (g["lat"] // step) * step + step / 2
g["w"] = g["icsea"] * g["enrolments"]
grid = g.groupby(["gx", "gy"]).agg(enrolments=("enrolments", "sum"), schools=("id", "count"),
                                   w=("w", "sum")).reset_index()
grid["mean_icsea"] = (grid["w"] / grid["enrolments"]).round(0)
grid = grid.rename(columns={"gx": "lon", "gy": "lat"}).drop(columns="w")
grid.to_csv(OUT / "enrolment_grid.csv", index=False)

# chart 10: beeswarm sample (up to 120 schools per remoteness class, fixed seed)
order = ["Major Cities", "Inner Regional", "Outer Regional", "Remote", "Very Remote"]
parts = [g[g["remoteness"] == r_].sample(min(120, (g["remoteness"] == r_).sum()), random_state=3179) for r_ in order]
pd.concat(parts)[["id", "name", "state", "sector", "remoteness", "icsea", "enrolments"]].to_csv(
    OUT / "icsea_beeswarm_sample.csv", index=False)
med = g.groupby("remoteness")["icsea"].agg(["median", "count"]).reindex(order).reset_index()
med.to_csv(OUT / "icsea_medians.csv", index=False)

# ABS table 53a: FTE student-to-teacher ratio 
r = pd.read_excel(next(RAW.glob("Table_53a*.xlsx")), sheet_name="Table 1 Data table", header=3).dropna()
r.columns = ["year", "state", "affiliation", "level", "ratio"]
for c in ["state", "affiliation", "level"]:
    r[c] = r[c].map(strip)
r = r[(r["affiliation"] == "All Affiliations") & (r["level"].str.lower() == "all levels") & (r["state"] != "Aust.")]
r = r[r["year"].between(2015, 2025)].copy()
r = r.sort_values(["year", "ratio", "state"]) # ties broken alphabetically
r["rank"] = r.groupby("year").cumcount() + 1
r.to_csv(OUT / "student_teacher_ratio_rank.csv", index=False)

# ABS table 46a: FTE students by remoteness and affiliation 
a = pd.read_excel(next(RAW.glob("Table_46a*.xlsx")), sheet_name="Table 2 Data table", header=3).dropna()
a.columns = ["year", "state", "affiliation", "remoteness", "male", "female", "fte"]
a["affiliation"] = a["affiliation"].map(strip)
a["remoteness"] = a["remoteness"].map(strip)
t = a.groupby(["remoteness", "affiliation"])["fte"].sum().round(0).reset_index()
tot = t["fte"].sum()
nodes = [{"id": "All students", "parent": None, "name": "All students", "value": None, "share": None}]
for rem in ["Major City", "Inner Regional", "Outer Regional", "Remote", "Very Remote"]:
    grp = round(100 * t[t["remoteness"] == rem]["fte"].sum() / tot, 2)
    nodes.append({"id": rem, "parent": "All students", "name": rem, "value": None, "share": grp})
for _, row in t.iterrows():
    nodes.append({"id": f"{row.remoteness}|{row.affiliation}", "parent": row.remoteness,
                  "name": row.affiliation, "value": row.fte, "share": round(100 * row.fte / tot, 2)})
pd.DataFrame(nodes).to_csv(OUT / "fte_remoteness_affiliation.csv", index=False)

print("schools mapped:", len(schools), "of", int((sp["Calendar Year"] == 2025).sum()))
print(sec.to_string())
print(med.to_string())
