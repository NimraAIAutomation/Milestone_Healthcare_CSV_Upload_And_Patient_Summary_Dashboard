# Healthcare Patient Dashboard

An interactive Streamlit dashboard for exploring patient records. Upload three CSV files and explore clinical metrics, risk levels, patient details, visit history and vital-sign trends.

> **Note:** The risk score is a simple, documented rule for demonstration. It is **not** a clinical model and must not be used for medical decisions. Use synthetic or de-identified data only.

## Features

- **CSV upload** for `patients.csv`, `encounters.csv` and `observations.csv`, with column validation and friendly error messages
- **Metric cards:** Total Patients, Total Visits, High Risk, Avg Risk Score
- **Risk filter and threshold slider** that update the cards, table, chart and patient dropdown
- **Patient summary table** with color-coded risk (green = Low, yellow = Medium, red = High) and CSV download
- **Risk distribution** bar chart
- **Patient details** with latest vitals and a risk badge
- **Visiting history** table for the selected patient
- **Vital trend charts** (Blood Pressure, Heart rate, BMI, Glucose) with dashed clinical reference lines, viewable one at a time or all together
- **Reset filters** button using `st.session_state`

## Tech stack

Python, Streamlit, pandas, NumPy, Altair

## Project structure

```
healthcare_dashboard/
├── app.py                    # Streamlit UI
├── requirements.txt
├── README.md
└── utils/
    ├── __init__.py
    └── data_processing.py    # Validation, vitals pivot, summary, risk score
```

## Getting started

```bash
# 1. Clone
git clone https://github.com/<your-username>/<your-repo>.git
cd <your-repo>

# 2. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # macOS / Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run
streamlit run app.py
```

The app opens at `http://localhost:8501`. Upload the three CSV files from the sidebar.

## Expected data

The app expects Synthea-style CSV files with at least these columns:

| File | Required columns |
|---|---|
| `patients.csv` | `Id`, `BIRTHDATE`, `FIRST`, `LAST`, `GENDER` (optional: `DEATHDATE`) |
| `encounters.csv` | `Id`, `PATIENT`, `START`, `ENCOUNTERCLASS` (also uses `DESCRIPTION`, `REASONDESCRIPTION`) |
| `observations.csv` | `DATE`, `PATIENT`, `ENCOUNTER`, `CATEGORY`, `DESCRIPTION`, `VALUE`, `UNITS` |

Vitals are read from `observations.csv` by description: Systolic/Diastolic Blood Pressure, Heart rate, Body mass index (BMI) [Ratio], and glucose labs in mg/dL.

## Risk rule

Each factor scores 0, 1 or 2 points. The **risk score = total points ÷ 8**. Missing values count as 0 points.

| Factor | 0 | 1 | 2 |
|---|---|---|---|
| Systolic BP (mm[Hg]) | < 130 | 130–139 | ≥ 140 |
| Glucose (mg/dL) | < 100 | 100–125 | ≥ 126 |
| BMI (kg/m²) | < 25 | 25–29.9 | ≥ 30 |
| Age (years) | < 50 | 50–64 | ≥ 65 |

**Risk level:** score below 0.25 is **Low**, score at or above the sidebar threshold (default 0.50) is **High**, everything in between is **Medium**.

Each patient's values come from their most recent recorded reading. If the latest reading is missing, the previous one is used.

## Error handling

- Missing uploads show an info message
- Missing columns are reported per file
- Unreadable or empty CSVs show an error instead of a traceback
- A filter with no matching patients shows a warning
- Missing vitals display as `N/A` or "No readings for this patient"

## Screenshots
### Wireframe
<img width="600" height="960" alt="wireframe" src="https://github.com/user-attachments/assets/69b23c6d-b983-4fd1-8cd4-c2d2f22dcd3a" />
### Actual App
<img width="1581" height="736" alt="image" src="https://github.com/user-attachments/assets/244d7cbf-fe29-4409-8e47-6d6ed2c7a7bb" />

<img width="1579" height="643" alt="image" src="https://github.com/user-attachments/assets/f6ed8f5f-4aa5-497c-8201-ce91d4ef1b51" />

<img width="1497" height="542" alt="image" src="https://github.com/user-attachments/assets/d8871017-478f-42c8-8352-5b2c701d71a7" />

<img width="1561" height="656" alt="image" src="https://github.com/user-attachments/assets/3f81839a-2d42-4f5f-86ea-d2d73b96fddf" />


## Limitations and future work

- Risk rule is illustrative, not clinically validated
- Age and gender filters and patient name search
- Additional labs (HbA1c, cholesterol) in the risk score
- Caching for large files with `st.cache_data`
