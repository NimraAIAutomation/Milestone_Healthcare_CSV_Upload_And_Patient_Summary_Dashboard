import streamlit as st
import pandas as pd
import datetime as dt
from pathlib import Path

st.set_page_config(
    page_title="Clinical Dashboard",
    layout="wide"
)
# -----------------------------
# LOAD DATA
# -----------------------------

DATA_DIR = Path(__file__).resolve().parent / "data"

patients = pd.read_csv(DATA_DIR / "patients.csv")
encounters = pd.read_csv(DATA_DIR / "encounters.csv")
observations = pd.read_csv(DATA_DIR / "observations.csv")

# Convert dates
patients["BIRTHDATE"] = pd.to_datetime(
    patients["BIRTHDATE"]
)

encounters["START"] = pd.to_datetime(
    encounters["START"]
)
observations["DATE"] = pd.to_datetime(
    observations["DATE"]
)

# Convert values to numeric
observations["VALUE"] = pd.to_numeric(
    observations["VALUE"],
    errors="coerce"
)

# Remove missing values
observations = observations.dropna(
    subset=["VALUE"]
)

# Calculate age
today = pd.Timestamp.today()

patients["AGE"] = (
    today.year - patients["BIRTHDATE"].dt.year
    - (
        (
            patients["BIRTHDATE"].dt.month > today.month
        )
        |
        (
            (patients["BIRTHDATE"].dt.month == today.month)
            & (patients["BIRTHDATE"].dt.day > today.day)
        )
    ).astype(int)
)
# Create patient name
patients["PATIENT_NAME"] = (
    patients["FIRST"] + " " + patients["LAST"]
)
# -----------------------------
# PATIENT SELECTION
# -----------------------------

patient_options = patients["PATIENT_NAME"].dropna().tolist()

if not patient_options:
    st.error("No patients found in patients.csv.")
    st.stop()

if "selected_patient" not in st.session_state:
    st.session_state.selected_patient = patient_options[0]

selected_patient = st.selectbox(
    "Select Patient",
    patient_options,
    key="selected_patient"
)

# Get selected patient's data
patient = patients[
    patients["PATIENT_NAME"] == selected_patient
].iloc[0]

# -----------------------------
# COUNT PATIENT VISITS
# -----------------------------

total_visits = encounters[
    encounters["PATIENT"] == patient["Id"]
].shape[0]
# -----------------------------
# SESSION STATE
# -----------------------------

if "threshold_description" not in st.session_state:
    st.session_state.threshold_description = "Heart rate"

if "threshold_operator" not in st.session_state:
    st.session_state.threshold_operator = "Above"

if "threshold_value" not in st.session_state:
    st.session_state.threshold_value = 80.0

# -----------------------------
# DASHBOARD TITLE
# -----------------------------

st.title("Clinical Patient Dashboard")

st.write("Total Patients:", len(patients))
st.write("Total Encounters:", len(encounters))

# Count patient visits
total_visits = encounters[
    encounters["PATIENT"] == patient["Id"]
].shape[0]
# -----------------------------
# PATIENT OBSERVATIONS
# -----------------------------

patient_id = patient["Id"]

patient_observations = observations[
    observations["PATIENT"] == patient_id
].copy()

st.write(
    "Total Observations:",
    len(patient_observations)
)
# -----------------------------
# PATIENT INFORMATION CARDS
# -----------------------------

col1, col2 = st.columns(2)

with col1:
    st.metric(
        label="Patient Name",
        value=patient["PATIENT_NAME"]
    )

with col2:
    st.metric(
        label="Age",
        value=f"{patient['AGE']} years"
    )

col3, col4 = st.columns(2)

with col3:
    st.metric(
        label="Gender",
        value=patient["GENDER"]
    )

with col4:
    st.metric(
        label="Total Visits",
        value=total_visits
    )
# -----------------------------
# DATE FILTER
# -----------------------------

st.subheader("Filter by Date")

if patient_observations.empty:
    st.warning("No observations are available for this patient.")
    st.stop()

min_date = patient_observations["DATE"].min().date()
max_date = patient_observations["DATE"].max().date()

date_range = st.date_input(
    "Select Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)
# -----------------------------
# APPLY DATE FILTER
# -----------------------------

if len(date_range) == 2:

    start_date, end_date = date_range

    filtered_observations = patient_observations[
        (
            patient_observations["DATE"].dt.date
            >= start_date
        )
        &
        (
            patient_observations["DATE"].dt.date
            <= end_date
        )
    ].copy()

else:

    filtered_observations = patient_observations.copy()

    
# -----------------------------
# LATEST VITALS
# -----------------------------

def get_latest_value(df, description):

    data = df[
        df["DESCRIPTION"] == description
    ].sort_values("DATE")

    if data.empty:
        return None, None

    latest = data.iloc[-1]

    return latest["VALUE"], latest["DATE"]


latest_systolic, systolic_date = get_latest_value(
    filtered_observations,
    "Systolic Blood Pressure"
)

latest_diastolic, diastolic_date = get_latest_value(
    filtered_observations,
    "Diastolic Blood Pressure"
)

latest_glucose, glucose_date = get_latest_value(
    filtered_observations,
    "Glucose [Mass/volume] in Blood"
)
# -----------------------------
# LATEST VITAL SUMMARY
# -----------------------------

st.subheader("Latest Vital Measurements")

col1, col2 = st.columns(2)

with col1:

    st.metric(
        label="Latest Systolic BP",
        value=(
            f"{latest_systolic:.0f} mmHg"
            if latest_systolic is not None
            else "N/A"
        )
    )

with col2:

    st.metric(
        label="Latest Diastolic BP",
        value=(
            f"{latest_diastolic:.0f} mmHg"
            if latest_diastolic is not None
            else "N/A"
        )
    )

col3, col4 = st.columns(2)

with col3:

    st.metric(
        label="Latest Glucose",
        value=(
            f"{latest_glucose:.1f} mg/dL"
            if latest_glucose is not None
            else "N/A"
        )
    )

with col4:

    latest_dates = [
        d for d in [
            systolic_date,
            diastolic_date,
            glucose_date
        ]
        if d is not None
    ]

    latest_date = max(latest_dates) if latest_dates else None

    st.metric(
        label="Last Measurement",
        value=(
            latest_date.strftime("%Y-%m-%d")
            if latest_date is not None
            else "N/A"
        )
    )

# -----------------------------
# THRESHOLD FILTER
# -----------------------------

st.subheader("Vital / Laboratory Threshold Filter")

threshold_options = [
    {
        "description": "Heart rate",
        "title": "Heart Rate",
        "unit": "bpm",
        "default": 80.0,
        "min": 40.0,
        "max": 180.0,
        "step": 1.0
    },
    {
        "description": "Respiratory rate",
        "title": "Respiratory Rate",
        "unit": "breaths/min",
        "default": 20.0,
        "min": 5.0,
        "max": 60.0,
        "step": 1.0
    },
    {
        "description": "Body Weight",
        "title": "Body Weight",
        "unit": "kg",
        "default": 70.0,
        "min": 20.0,
        "max": 200.0,
        "step": 1.0
    },
    {
        "description": "Body mass index (BMI) [Ratio]",
        "title": "BMI",
        "unit": "kg/m²",
        "default": 25.0,
        "min": 10.0,
        "max": 60.0,
        "step": 0.5
    },
    {
        "description": "Hemoglobin A1c/Hemoglobin.total in Blood",
        "title": "Hemoglobin A1c",
        "unit": "%",
        "default": 5.7,
        "min": 3.0,
        "max": 15.0,
        "step": 0.1
    },
    {
        "description": "Creatinine [Mass/volume] in Blood",
        "title": "Creatinine",
        "unit": "mg/dL",
        "default": 1.0,
        "min": 0.1,
        "max": 10.0,
        "step": 0.1
    },
    {
        "description": "Urea nitrogen [Mass/volume] in Blood",
        "title": "Blood Urea Nitrogen",
        "unit": "mg/dL",
        "default": 20.0,
        "min": 1.0,
        "max": 100.0,
        "step": 1.0
    }
]
# Select vital/laboratory measurement

selected_threshold = st.selectbox(
    "Select Measurement",
    threshold_options,
    format_func=lambda x: x["title"],
    key="threshold_measurement"
)

# Select filter condition

operator = st.radio(
    "Condition",
    ["Above", "Below"],
    horizontal=True,
    key="threshold_operator"
)
# Threshold slider

threshold = st.slider(
    f"Threshold ({selected_threshold['unit']})",
    min_value=selected_threshold["min"],
    max_value=selected_threshold["max"],
    value=selected_threshold["default"],
    step=selected_threshold["step"],
    key="threshold_slider"
)
# -----------------------------
# APPLY THRESHOLD FILTER
# -----------------------------

threshold_data = filtered_observations[
    filtered_observations["DESCRIPTION"]
    == selected_threshold["description"]
].copy()

if operator == "Above":

    threshold_data = threshold_data[
        threshold_data["VALUE"] > threshold
    ]

else:

    threshold_data = threshold_data[
        threshold_data["VALUE"] < threshold
    ]
# -----------------------------
# THRESHOLD RESULTS
# -----------------------------

st.subheader("Threshold Results")

st.write(
    f"{selected_threshold['title']} "
    f"{operator.lower()} "
    f"{threshold} {selected_threshold['unit']}"
)

st.metric(
    "Matching Measurements",
    len(threshold_data)
)
if threshold_data.empty:

    st.info(
        "No measurements match the selected threshold."
    )

else:

    st.dataframe(
        threshold_data[
            [
                "DATE",
                "DESCRIPTION",
                "VALUE",
                "UNITS"
            ]
        ].sort_values(
            "DATE",
            ascending=False
        ),
        use_container_width=True
    )
# -----------------------------
# THRESHOLD TREND
# -----------------------------

st.subheader(
    f"{selected_threshold['title']} - Threshold Trend"
)

if threshold_data.empty:

    st.info(
        "No data available for the selected threshold."
    )

else:

    st.line_chart(
        threshold_data.set_index("DATE")["VALUE"],
        y_label=(
            f"{selected_threshold['title']} "
            f"({selected_threshold['unit']})"
        ),
        x_label="Date"
    )

# -----------------------------
# REUSABLE VITAL GRAPH
# -----------------------------

def show_vital_graph(
    df,
    description,
    title,
    y_label
):

    data = df[
        df["DESCRIPTION"] == description
    ].copy()

    data = data.sort_values("DATE")

    if data.empty:

        st.info(
            f"No {title} data available."
        )

    else:

        st.line_chart(
            data.set_index("DATE")["VALUE"],
            y_label=y_label,
            x_label="Date"
        )
# -----------------------------
# ADDITIONAL VITAL GRAPHS
# -----------------------------

st.subheader("Additional Vital Trends")

show_vital_graph(
    filtered_observations,
    "Heart rate",
    "Heart Rate",
    "bpm"
)

show_vital_graph(
    filtered_observations,
    "Respiratory rate",
    "Respiratory Rate",
    "breaths/min"
)

show_vital_graph(
    filtered_observations,
    "Body Weight",
    "Body Weight",
    "kg"
)

show_vital_graph(
    filtered_observations,
    "Body mass index (BMI) [Ratio]",
    "BMI",
    "kg/m²"
)

# -----------------------------
# LABORATORY TRENDS
# -----------------------------

st.subheader("Laboratory Trends")

show_vital_graph(
    filtered_observations,
    "Hemoglobin A1c/Hemoglobin.total in Blood",
    "Hemoglobin A1c",
    "%"
)

show_vital_graph(
    filtered_observations,
    "Creatinine [Mass/volume] in Blood",
    "Creatinine",
    "mg/dL"
)

show_vital_graph(
    filtered_observations,
    "Urea nitrogen [Mass/volume] in Blood",
    "Blood Urea Nitrogen",
    "mg/dL"
)

