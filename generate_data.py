from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
rng = np.random.default_rng(SEED)
TODAY = date.today()
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_PATH = SCRIPT_DIR / "data" / "patients.xlsx"
READMISSION_DAYS = 30  # boundary rule: a gap of <= 30 days counts as readmission

# patient_id -> (age, sex, [days ago for each visit, oldest first])
PATIENTS = {
    "P001": (67, "M", [200, 150, 95, 50, 20, 5]),   # 6 visits, trend chart example
    "P002": (45, "F", [3]),                          # new patient (1 visit)
    "P003": (58, "M", [90, 60, 40, 12]),             # last two visits 28 days apart (< 30)
    "P004": (50, "M", [60, 45, 30, 15, 5]),          # 5 visits
    "P005": (65, "F", [25, 14, 5]),
    "P006": (40, "M", [180, 120, 100, 70, 40, 5]),   # last gap 35 (> 30), not all gaps > 30
    "P007": (60, "M", [40, 10]),                     # exact boundary: 30-day gap
    "P008": (58, "F", [30, 21, 12, 4]),
    "P009": (54, "F", [18, 10, 2]),
    "P010": (46, "M", [240, 170, 100, 35]),          # all gaps > 30
    "P011": (80, "M", [30, 20, 10, 4]),
    "P012": (50, "F", [20, 10]),
}

# Deliberate missing values: (patient_id, visit position, column). -1 = latest visit.
MISSING = [
    ("P001", -1, "glucose"),
    ("P003", 2, "temperature"),
]


def compute_readmission_risk(age: int, bp_systolic: int, glucose: float) -> float:
    """Return a 0-100 risk score based on age, systolic BP, and glucose."""
    age_risk = min(max((age - 20) / 60, 0), 1) * 100
    bp_risk = min(max(abs(bp_systolic - 120) / 60, 0), 1) * 100
    glucose_risk = min(max(abs(glucose - 100) / 200, 0), 1) * 100
    score = age_risk * 0.40 + bp_risk * 0.35 + glucose_risk * 0.25
    return round(float(np.clip(score, 0, 100)), 1)


def make_baseline(age: int) -> dict:
    """Per-patient baseline. Older patients trend higher in BP and glucose."""
    return {
        "bp_systolic": int(105 + (age - 20) * 0.5 + rng.integers(-8, 8)),
        "bp_diastolic": int(80 + rng.integers(-10, 10)),
        "glucose": float(90 + (age - 20) * 0.6 + rng.integers(-10, 10)),
        "heart_rate": int(70 + rng.integers(-15, 15)),
        "temperature": float(np.clip(36.5 + rng.normal(0, 0.3), 36.2, 37.5)),
    }


def make_visit(base: dict) -> dict:
    """Return random vitals near a patient's baseline, clipped to plausible ranges."""
    return {
        "bp_systolic": int(np.clip(rng.normal(base["bp_systolic"], 14), 90, 180)),
        "bp_diastolic": int(np.clip(rng.normal(base["bp_diastolic"], 6), 50, 110)),
        "glucose": round(float(np.clip(rng.normal(base["glucose"], 22), 70, 300)), 1),
        "heart_rate": int(np.clip(rng.normal(base["heart_rate"], 8), 55, 120)),
        "temperature": round(float(np.clip(rng.normal(base["temperature"], 0.4), 36.0, 39.0)), 1),
    }


def build_dataframe() -> pd.DataFrame:
    rows = []
    for patient_id, (age, sex, days_ago) in PATIENTS.items():
        baseline = make_baseline(age)  # once per patient
        for d in days_ago:
            vitals = make_visit(baseline)
            vitals["readmission_risk_score"] = compute_readmission_risk(
                age, vitals["bp_systolic"], vitals["glucose"]
            )
            rows.append(
                {
                    "patient_id": patient_id,
                    "visit_id": f"V{len(rows) + 1:04d}",
                    "visit_date": TODAY - timedelta(days=d),
                    "age": age,
                    "sex": sex,
                    **vitals,
                }
            )
    df = pd.DataFrame(rows)
    df["visit_date"] = pd.to_datetime(df["visit_date"])
    return df


def inject_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Set specific cells to NaN by patient and visit position (not row index)."""
    for patient_id, position, column in MISSING:
        visit_ids = df.loc[df["patient_id"] == patient_id, "visit_id"].tolist()
        df.loc[df["visit_id"] == visit_ids[position], column] = np.nan
    return df


def in_range(series: pd.Series, low: float, high: float) -> bool:
    """True if every non-missing value is within [low, high]."""
    return bool(series.dropna().between(low, high).all())


def validate(df: pd.DataFrame) -> None:
    """Raise ValueError if the dataset violates the spec."""
    checks = {
        "visit_id unique": df["visit_id"].is_unique,
        "systolic 90-180": in_range(df["bp_systolic"], 90, 180),
        "diastolic < systolic": bool((df["bp_diastolic"] < df["bp_systolic"]).all()),
        "glucose 70-300": in_range(df["glucose"], 70, 300),
        "heart_rate 55-120": in_range(df["heart_rate"], 55, 120),
        "temperature 36.0-39.0": in_range(df["temperature"], 36.0, 39.0),
        "risk score 0-100": in_range(df["readmission_risk_score"], 0, 100),
        "age constant per patient": bool(df.groupby("patient_id")["age"].nunique().eq(1).all()),
        "10-12 patients": 10 <= df["patient_id"].nunique() <= 12,
        "1-6 visits per patient": bool(df.groupby("patient_id").size().between(1, 6).all()),
        ">= 2 missing values": int(df[["glucose", "temperature"]].isna().sum().sum()) >= 2,
    }

    # Scenario coverage, computed from the data itself
    df = df.sort_values(["patient_id", "visit_date"])
    df["gap"] = df.groupby("patient_id")["visit_date"].diff().dt.days
    g = df.groupby("patient_id")["gap"]
    last_gap = g.last()
    max_gap = g.max()
    min_gap = g.min()
    n_visits = df.groupby("patient_id").size()

    checks.update(
        {
            "has 1-visit patient": bool((n_visits == 1).any()),
            "has 5+ visit patient": bool((n_visits >= 5).any()),
            "has last gap < 30": bool((last_gap < READMISSION_DAYS).any()),
            "has last gap == 30": bool((last_gap == READMISSION_DAYS).any()),
            "has last gap > 30": bool((last_gap > READMISSION_DAYS).any()),
            "has all gaps > 30": bool((min_gap > READMISSION_DAYS).any()),
            "no gap under 5 days": bool((df["gap"].dropna() >= 5).all()),
        }
    )

    failed = [name for name, ok in checks.items() if not ok]
    if failed:
        raise ValueError(f"Validation failed: {failed}")


def main() -> None:
    df = inject_missing(build_dataframe())
    validate(df)
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_excel(DATA_PATH, index=False)
    print(df.head(10))
    print(f"\nSaved {len(df)} rows for {df['patient_id'].nunique()} patients to {DATA_PATH}")


if __name__ == "__main__":
    main()