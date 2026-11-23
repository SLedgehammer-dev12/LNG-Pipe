"""ASME B36.10M (wrought carbon/alloy steel) and B36.19M (stainless steel) pipe dimensions.

Values are nominal outside diameter (OD, mm) and wall thickness (mm) for the
schedules used in cryogenic LNG transfer lines. Inner diameter is computed as
ID = OD - 2 * wall. Use the tables for selection; it is still the engineer's
responsibility to verify the schedule against the design code.

Schedule coverage:
- B36.10: Sch 5, 10, 20, 30, 40, STD, 60, 80, XS, 100, 120, 140, 160, XXS
  (only the schedules the standard lists for each size).
- B36.19: 5S, 10S, 40S, 80S.
"""

# NPS label -> {od_mm, schedules: {schedule label: wall mm}}
ASME_B36_10_CARBON_STEEL = {
    'DN15 (NPS 1/2")':  {"od_mm": 21.3,  "schedules": {"Sch 5": 1.65, "Sch 10": 2.11, "Sch 40": 2.77, "STD": 2.77, "Sch 80": 3.73, "XS": 3.73, "Sch 160": 4.78, "XXS": 7.47}},
    'DN20 (NPS 3/4")':  {"od_mm": 26.7,  "schedules": {"Sch 5": 1.65, "Sch 10": 2.11, "Sch 40": 2.87, "STD": 2.87, "Sch 80": 3.91, "XS": 3.91, "Sch 160": 5.56, "XXS": 7.82}},
    'DN25 (NPS 1")':    {"od_mm": 33.4,  "schedules": {"Sch 5": 1.65, "Sch 10": 2.77, "Sch 40": 3.38, "STD": 3.38, "Sch 80": 4.55, "XS": 4.55, "Sch 160": 6.35, "XXS": 9.09}},
    'DN32 (NPS 1-1/4")':{"od_mm": 42.2,  "schedules": {"Sch 5": 1.65, "Sch 10": 2.77, "Sch 40": 3.56, "STD": 3.56, "Sch 80": 4.85, "XS": 4.85, "Sch 160": 6.35, "XXS": 9.70}},
    'DN40 (NPS 1-1/2")':{"od_mm": 48.3,  "schedules": {"Sch 5": 1.65, "Sch 10": 2.77, "Sch 40": 3.68, "STD": 3.68, "Sch 80": 5.08, "XS": 5.08, "Sch 160": 7.14, "XXS": 10.15}},
    'DN50 (NPS 2")':    {"od_mm": 60.3,  "schedules": {"Sch 5": 1.65, "Sch 10": 2.77, "Sch 40": 3.91, "STD": 3.91, "Sch 80": 5.54, "XS": 5.54, "Sch 160": 8.74, "XXS": 11.07}},
    'DN65 (NPS 2-1/2")':{"od_mm": 73.0,  "schedules": {"Sch 5": 2.11, "Sch 10": 3.05, "Sch 40": 5.16, "STD": 5.16, "Sch 80": 7.01, "XS": 7.01, "Sch 160": 9.53, "XXS": 14.02}},
    'DN80 (NPS 3")':    {"od_mm": 88.9,  "schedules": {"Sch 5": 2.11, "Sch 10": 3.05, "Sch 40": 5.49, "STD": 5.49, "Sch 80": 7.62, "XS": 7.62, "Sch 160": 11.13, "XXS": 15.24}},
    'DN100 (NPS 4")':   {"od_mm": 114.3, "schedules": {"Sch 5": 2.11, "Sch 10": 3.05, "Sch 40": 6.02, "STD": 6.02, "Sch 80": 8.56, "XS": 8.56, "Sch 120": 11.13, "Sch 160": 13.49, "XXS": 17.12}},
    'DN125 (NPS 5")':   {"od_mm": 141.3, "schedules": {"Sch 5": 2.77, "Sch 10": 3.40, "Sch 40": 6.55, "STD": 6.55, "Sch 80": 9.53, "XS": 9.53, "Sch 120": 12.70, "Sch 160": 15.88, "XXS": 19.05}},
    'DN150 (NPS 6")':   {"od_mm": 168.3, "schedules": {"Sch 5": 2.77, "Sch 10": 3.40, "Sch 40": 7.11, "STD": 7.11, "Sch 80": 10.97, "XS": 10.97, "Sch 120": 14.27, "Sch 160": 18.26, "XXS": 21.95}},
    'DN200 (NPS 8")':   {"od_mm": 219.1, "schedules": {"Sch 5": 2.77, "Sch 10": 3.76, "Sch 20": 6.35, "Sch 30": 7.04, "Sch 40": 8.18, "STD": 8.18, "Sch 60": 10.31, "Sch 80": 12.70, "XS": 12.70, "Sch 100": 15.09, "Sch 120": 18.26, "Sch 140": 20.62, "Sch 160": 23.01, "XXS": 22.23}},
    'DN250 (NPS 10")':  {"od_mm": 273.1, "schedules": {"Sch 5": 3.40, "Sch 10": 4.19, "Sch 20": 6.35, "Sch 30": 7.80, "Sch 40": 9.27, "STD": 9.27, "Sch 60": 12.70, "Sch 80": 15.09, "XS": 12.70, "Sch 100": 18.26, "Sch 120": 21.44, "Sch 140": 25.40, "Sch 160": 28.58, "XXS": 25.40}},
    'DN300 (NPS 12")':  {"od_mm": 323.9, "schedules": {"Sch 5": 3.96, "Sch 10": 4.57, "Sch 20": 6.35, "Sch 30": 8.38, "Sch 40": 10.31, "STD": 9.53, "Sch 60": 14.27, "Sch 80": 17.48, "XS": 12.70, "Sch 100": 21.44, "Sch 120": 25.40, "Sch 140": 28.58, "Sch 160": 33.32, "XXS": 25.40}},
    'DN350 (NPS 14")':  {"od_mm": 355.6, "schedules": {"Sch 5": 3.96, "Sch 10": 6.35, "Sch 20": 7.92, "Sch 30": 9.53, "Sch 40": 11.13, "STD": 9.53, "Sch 60": 15.09, "Sch 80": 19.05, "XS": 12.70, "Sch 100": 23.83, "Sch 120": 27.79, "Sch 140": 31.75, "Sch 160": 35.71}},
    'DN400 (NPS 16")':  {"od_mm": 406.4, "schedules": {"Sch 5": 4.19, "Sch 10": 6.35, "Sch 20": 7.92, "Sch 30": 9.53, "Sch 40": 12.70, "STD": 9.53, "Sch 60": 16.66, "Sch 80": 21.44, "XS": 12.70, "Sch 100": 26.19, "Sch 120": 30.96, "Sch 140": 36.53, "Sch 160": 40.49}},
    'DN450 (NPS 18")':  {"od_mm": 457.2, "schedules": {"Sch 5": 4.19, "Sch 10": 6.35, "Sch 20": 7.92, "Sch 30": 11.13, "Sch 40": 14.27, "STD": 9.53, "Sch 60": 19.05, "Sch 80": 23.83, "XS": 12.70, "Sch 100": 29.36, "Sch 120": 34.93, "Sch 140": 39.67, "Sch 160": 45.24}},
    'DN500 (NPS 20")':  {"od_mm": 508.0, "schedules": {"Sch 10": 6.35, "Sch 20": 9.53, "Sch 30": 12.70, "Sch 40": 15.09, "STD": 9.53, "Sch 60": 20.62, "Sch 80": 26.19, "XS": 12.70, "Sch 100": 32.54, "Sch 120": 38.10, "Sch 140": 44.45, "Sch 160": 50.01}},
    'DN600 (NPS 24")':  {"od_mm": 609.6, "schedules": {"Sch 10": 6.35, "Sch 20": 9.53, "Sch 30": 14.27, "Sch 40": 17.48, "STD": 9.53, "Sch 60": 24.61, "Sch 80": 30.96, "XS": 12.70, "Sch 100": 38.89, "Sch 120": 46.02, "Sch 140": 52.37, "Sch 160": 59.54}},
}

ASME_B36_19_STAINLESS_STEEL = {
    'DN15 (NPS 1/2")':  {
        "od_mm": 21.3,
        "schedules": {"5S": 1.65, "10S": 2.11, "40S": 2.77, "80S": 3.73},
        "unscheduled_mm": [1.20, 1.50, 2.00, 2.50, 3.00, 3.20, 4.00, 4.78],
    },
    'DN20 (NPS 3/4")':  {
        "od_mm": 26.7,
        "schedules": {"5S": 1.65, "10S": 2.11, "40S": 2.87, "80S": 3.91},
        "unscheduled_mm": [1.50, 2.00, 2.30, 2.50, 2.60, 3.00, 3.20, 4.00, 5.00],
    },
    'DN25 (NPS 1")':    {
        "od_mm": 33.4,
        "schedules": {"5S": 1.65, "10S": 2.77, "40S": 3.38, "80S": 4.55},
        "unscheduled_mm": [1.50, 2.00, 2.30, 2.50, 2.60, 3.00, 3.20, 3.60, 4.00, 5.00, 6.35],
    },
    'DN32 (NPS 1-1/4")':{
        "od_mm": 42.2,
        "schedules": {"5S": 1.65, "10S": 2.77, "40S": 3.56, "80S": 4.85},
        "unscheduled_mm": [2.00, 2.30, 2.60, 3.00, 3.20, 3.60, 4.00, 5.00, 6.35],
    },
    'DN40 (NPS 1-1/2")':{
        "od_mm": 48.3,
        "schedules": {"5S": 1.65, "10S": 2.77, "40S": 3.68, "80S": 5.08},
        "unscheduled_mm": [2.00, 2.30, 2.60, 3.00, 3.20, 4.00, 4.50, 5.00, 6.00, 7.14],
    },
    'DN50 (NPS 2")':    {
        "od_mm": 60.3,
        "schedules": {"5S": 1.65, "10S": 2.77, "40S": 3.91, "80S": 5.54},
        "unscheduled_mm": [2.00, 2.30, 2.60, 2.90, 3.00, 3.20, 3.60, 4.00, 4.50, 5.00, 6.00, 6.30, 7.10, 8.00, 8.74],
    },
    'DN65 (NPS 2-1/2")':{
        "od_mm": 73.0,
        "schedules": {"5S": 2.11, "10S": 3.05, "40S": 5.16, "80S": 7.01},
        "unscheduled_mm": [2.00, 2.30, 2.60, 2.90, 3.00, 3.20, 3.60, 4.00, 4.50, 5.00, 5.60, 6.00, 6.30, 8.00, 9.53],
    },
    'DN80 (NPS 3")':    {
        "od_mm": 88.9,
        "schedules": {"5S": 2.11, "10S": 3.05, "40S": 5.49, "80S": 7.62},
        "unscheduled_mm": [2.00, 2.30, 2.60, 2.90, 3.00, 3.20, 3.60, 4.00, 4.50, 5.00, 5.60, 6.00, 6.30, 7.10, 8.00, 8.80, 10.00, 11.13],
    },
    'DN100 (NPS 4")':   {
        "od_mm": 114.3,
        "schedules": {"5S": 2.11, "10S": 3.05, "40S": 6.02, "80S": 8.56},
        "unscheduled_mm": [2.00, 2.60, 2.90, 3.00, 3.20, 3.60, 4.00, 4.50, 5.00, 5.60, 6.30, 7.10, 8.00, 8.80, 10.00, 11.13, 12.50, 13.49],
    },
    'DN125 (NPS 5")':   {
        "od_mm": 141.3,
        "schedules": {"5S": 2.77, "10S": 3.40, "40S": 6.55, "80S": 9.53},
        "unscheduled_mm": [2.60, 3.00, 3.20, 3.60, 4.00, 4.50, 5.00, 5.60, 6.00, 6.30, 7.10, 8.00, 8.80, 10.00, 11.00, 12.70],
    },
    'DN150 (NPS 6")':   {
        "od_mm": 168.3,
        "schedules": {"5S": 2.77, "10S": 3.40, "40S": 7.11, "80S": 10.97},
        "unscheduled_mm": [2.60, 3.00, 3.20, 3.60, 4.00, 4.50, 5.00, 5.60, 6.00, 6.35, 8.00, 8.80, 9.53, 10.00, 12.70, 14.27],
    },
    'DN200 (NPS 8")':   {
        "od_mm": 219.1,
        "schedules": {"5S": 2.77, "10S": 3.76, "40S": 8.18, "80S": 12.70},
        "unscheduled_mm": [3.00, 3.20, 4.00, 4.50, 5.00, 5.56, 6.00, 6.35, 7.04, 7.11, 8.00, 8.80, 9.53, 10.00, 10.31, 11.13, 12.00, 14.27, 15.09, 16.00, 18.26, 20.00],
    },
    'DN250 (NPS 10")':  {
        "od_mm": 273.1,
        "schedules": {"5S": 3.40, "10S": 4.19, "40S": 9.27, "80S": 12.70},
        "unscheduled_mm": [3.00, 3.60, 4.00, 4.50, 5.00, 5.56, 6.00, 6.35, 7.10, 7.80, 8.00, 8.80, 9.53, 10.00, 11.13, 12.00, 14.27, 15.09, 16.00, 18.26, 20.00, 21.44],
    },
    'DN300 (NPS 12")':  {
        "od_mm": 323.9,
        "schedules": {"5S": 3.96, "10S": 4.57, "40S": 9.53, "80S": 12.70},
        "unscheduled_mm": [3.60, 4.00, 5.00, 5.56, 6.00, 6.35, 7.10, 7.92, 8.00, 8.38, 8.80, 10.00, 10.31, 11.13, 12.00, 14.27, 15.88, 16.00, 17.48, 19.05, 20.00, 21.44],
    },
    'DN350 (NPS 14")':  {
        "od_mm": 355.6,
        "schedules": {"5S": 3.96, "10S": 4.78, "40S": 9.53, "80S": 12.70},
        "unscheduled_mm": [4.00, 4.50, 5.00, 5.56, 6.00, 6.35, 7.10, 7.92, 8.00, 8.80, 10.00, 10.31, 11.13, 12.00, 14.27, 15.09, 16.00, 17.48, 19.05, 20.00, 22.23],
    },
    'DN400 (NPS 16")':  {
        "od_mm": 406.4,
        "schedules": {"5S": 4.19, "10S": 4.78, "40S": 9.53, "80S": 12.70},
        "unscheduled_mm": [4.00, 4.50, 5.00, 5.56, 6.00, 6.35, 7.10, 7.92, 8.00, 8.80, 10.00, 10.31, 11.13, 12.00, 14.27, 15.88, 16.66, 17.48, 19.05, 20.00, 21.44, 25.40],
    },
    'DN450 (NPS 18")':  {
        "od_mm": 457.2,
        "schedules": {"5S": 4.19, "10S": 4.78, "40S": 9.53, "80S": 12.70},
        "unscheduled_mm": [4.50, 5.00, 5.56, 6.00, 6.35, 7.10, 7.92, 8.00, 8.80, 10.00, 10.31, 11.13, 12.00, 14.27, 15.88, 16.00, 17.48, 19.05, 20.00, 22.23, 23.83, 25.40],
    },
    'DN500 (NPS 20")':  {
        "od_mm": 508.0,
        "schedules": {"5S": 4.78, "10S": 5.54, "40S": 9.53, "80S": 12.70},
        "unscheduled_mm": [5.00, 6.00, 6.35, 7.10, 7.92, 8.00, 8.80, 10.00, 10.31, 11.13, 12.00, 14.27, 15.09, 15.88, 16.00, 17.48, 19.05, 20.62, 22.23, 25.40, 26.19],
    },
    'DN600 (NPS 24")':  {
        "od_mm": 609.6,
        "schedules": {"5S": 5.54, "10S": 6.35, "40S": 9.53, "80S": 12.70},
        "unscheduled_mm": [6.00, 7.10, 7.92, 8.00, 8.80, 10.00, 10.31, 11.13, 12.00, 14.27, 15.88, 16.00, 17.48, 19.05, 20.00, 22.23, 24.61, 25.40, 30.96],
    },
}

PIPE_TABLE_GROUPS = {
    "Karbon Çelik (ASME B36.10)": ASME_B36_10_CARBON_STEEL,
    "Paslanmaz Çelik (ASME B36.19)": ASME_B36_19_STAINLESS_STEEL,
}


def get_wall_thickness_options(group: str, dn_label: str) -> dict[str, float]:
    """
    Return an ordered mapping of selectable wall-thickness option labels -> wall_mm
    for a given pipe standard group and nominal diameter (DN/NPS).
    Includes both standard Schedule entries and unscheduled millimeter-only wall thicknesses.
    """
    row = PIPE_TABLE_GROUPS[group][dn_label]
    options: dict[str, float] = {}
    for sched_key, wall_val in row["schedules"].items():
        options[f"{sched_key} ({wall_val:.2f} mm)"] = float(wall_val)
    for mm_val in row.get("unscheduled_mm", []):
        options[f"{mm_val:.2f} mm (Schedule'sız)"] = float(mm_val)
    return options


def inner_diameter_mm(od_mm: float, wall_mm: float) -> float:
    """Return the nominal inner diameter in mm from OD and wall thickness."""
    return od_mm - 2.0 * wall_mm
