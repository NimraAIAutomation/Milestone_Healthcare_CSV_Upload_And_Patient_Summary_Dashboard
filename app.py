import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
from utils.data_processing import missing_columns, build_vitals, build_summary

st.set_page_config(page_title="Healthcare Patient Dashboard", layout="wide")
st.title("Healthcare Patient Dashboard")
st.write("Upload patient records and explore clinical metrics, risk levels, patient details and vital trends.")

CHARTS = {
    "Blood Pressure": {"cols": {"sbp": "Systolic", "dbp": "Diastolic"}, "refs": [140, 90], "unit": "mm[Hg]"},
    "Heart rate": {"cols": {"heart_rate": "Heart rate"}, "refs": [100], "unit": "beats/min"},
    "BMI": {"cols": {"bmi": "BMI"}, "refs": [25, 30], "unit": "kg/m²"},
    "Glucose": {"cols": {"glucose": "Glucose"}, "refs": [126], "unit": "mg/dL"},
}
RISK_COLORS = {  # (background, text)
    "Low": ("#D4F6D4", "black"),
    "Medium": ("#FFFFC5", "black"),
    "High": ("#FFDBE0", "black"),
}

def style_risk_row(row):
    bg, fg = RISK_COLORS[row["Risk Level"]]
    css = f"background-color: {bg}; color: {fg}; font-weight: bold"
    return [css if c in ("Risk Level") else "" for c in row.index]

# ---------- Sidebar: data ----------
with st.sidebar:
    st.header("Data")
    files = {
        "patients": st.file_uploader("Patients.csv", type=["csv"]),
        "encounters": st.file_uploader("Encounters.csv", type=["csv"]),
        "observations": st.file_uploader("Observations.csv", type=["csv"]),
    }

if not all(files.values()):
    st.info("Upload all three CSV files in the sidebar to begin.")
    st.stop()

try:
    data = {name: pd.read_csv(f) for name, f in files.items()}
except Exception as e:
    st.error(f"Could not read one of the files: {e}")
    st.stop()

errors = {n: missing_columns(df, n) for n, df in data.items() if missing_columns(df, n)}
if errors:
    for n, cols in errors.items():
        st.error(f"{n}.csv is missing columns: {', '.join(cols)}")
    st.stop()

try:
    vitals = build_vitals(data["observations"])
    summary = build_summary(data["patients"], data["encounters"], vitals)
except Exception as e:
    st.error(f"Could not process the data: {e}")
    st.stop()

def reset_filters():
    st.session_state.risk_filter = "All"
    st.session_state.risk_threshold = 0.5
    st.session_state.selected_vital = "All vitals"
    st.session_state.pop("selected_patient", None)

# ---------- Sidebar: filters ----------
with st.sidebar:
    st.caption(f"Glucose found for {summary['glucose'].notna().sum()} of {len(summary)} patients")
    st.header("Filters")
    level_filter = st.selectbox("Risk Level", ["All", "Low", "Medium", "High"], key="risk_filter")
    threshold = st.slider("Risk Threshold (High if score ≥)", 0.25, 1.0, 0.5, 0.05, key="risk_threshold")
    st.button("Reset filters", on_click=reset_filters)

summary["risk_level"] = np.where(
    summary["risk_score"] >= threshold, "High",
    np.where(summary["risk_score"] < 0.25, "Low", "Medium"),
)
filtered = summary if level_filter == "All" else summary[summary["risk_level"] == level_filter]

if filtered.empty:
    st.warning("No patients match the current filter.")
    st.stop()

# ---------- Sidebar: patient + vital ----------
names = filtered.set_index("PATIENT")["name"]

with st.sidebar:
    st.header("Patient")
    patient_id = st.selectbox(
        "Select patient", names.index, format_func=lambda i: names[i], key="selected_patient"
    )
    st.header("Vital to Display")
    vital_label = st.selectbox("Vital", ["All vitals"] + list(CHARTS), key="selected_vital")

# ---------- Top metric cards ----------
st.subheader("Top Metric Cards")
cards = [
    ("Total Patients", len(filtered)),
    ("Total Visits", int(filtered["encounters"].sum())),
    ("High Risk", int((filtered["risk_level"] == "High").sum())),
    ("Avg Risk Score", f"{filtered['risk_score'].mean():.2f}"),
]
slots = st.columns(2) + st.columns(2)
for slot, (label, value) in zip(slots, cards):
    with slot.container(border=True):
        st.metric(label, value)

# ---------- Risk distribution ----------
st.subheader("Risk Distribution")
dist = (
    filtered["risk_level"]
    .value_counts()
    .reindex(["Low", "Medium", "High"], fill_value=0)
    .rename_axis("Risk Level")
    .reset_index(name="Patients")
)
with st.container(border=True):
    bars = alt.Chart(dist).mark_bar().encode(
        x=alt.X("Risk Level:N", sort=["Low", "Medium", "High"], title=None),
        y=alt.Y("Patients:Q", title="Patients"),
        color=alt.Color(
            "Risk Level:N",
            scale=alt.Scale(
                domain=["Low", "Medium", "High"],
                range=[RISK_COLORS[k][0] for k in ("Low", "Medium", "High")],
            ),
            legend=None,
        ),
        tooltip=["Risk Level:N", "Patients:Q"],
    )
    st.altair_chart(bars, use_container_width=True)


# ---------- Patient summary table ----------
def fmt_bp(r):
    return f"{r['sbp']:.0f}/{r['dbp']:.0f}" if pd.notna(r["sbp"]) and pd.notna(r["dbp"]) else "N/A"

table = filtered.copy()
table["BP"] = table.apply(fmt_bp, axis=1)
table = table[["name", "GENDER", "age", "BP", "glucose", "risk_score", "risk_level"]]
table.columns = ["Name", "Sex", "Age", "BP", "Glucose", "Risk Score", "Risk Level"]

st.subheader("Patient Summary Table")
with st.container(border=True):
    styled = table.style.apply(style_risk_row, axis=1).format(
        {"Risk Score": "{:.2f}", "Glucose": "{:.0f}"}, na_rep="N/A"
    )
    st.dataframe(styled, use_container_width=True, hide_index=True)

# ---------- Patient details ----------

row = filtered[filtered["PATIENT"] == patient_id].iloc[0]
hr = f"{row['heart_rate']:.0f}" if pd.notna(row["heart_rate"]) else "N/A"
bmi = f"{row['bmi']:.1f}" if pd.notna(row["bmi"]) else "N/A"
glu = f"{row['glucose']:.0f}" if pd.notna(row["glucose"]) else "N/A"

st.subheader("Patient Details")
with st.container(border=True):
    d1, d2, d3 = st.columns(3)
    d1.write(f"**Name:** {row['name']}")
    d1.write(f"**Sex:** {row['GENDER']}")
    d1.write(f"**Age:** {row['age']}")
    d2.write(f"**Latest BP:** {fmt_bp(row)}")
    d2.write(f"**Latest Glucose:** {glu}")
    d2.write(f"**Latest Heart Rate:** {hr}")
    d3.write(f"**Latest BMI:** {bmi}")
    d3.write(f"**Risk Score:** {row['risk_score']:.2f}")
    bg, fg = RISK_COLORS[row["risk_level"]]
    d3.markdown(
        f"**Risk Level:** <span style='background:{bg};color:{fg};padding:2px 10px;"
        f"border-radius:10px;font-weight:bold'>{row['risk_level']}</span>",
        unsafe_allow_html=True,
    )
st.download_button(
        "Download filtered table (CSV)",
        table.to_csv(index=False).encode("utf-8"),
        file_name="patient_summary.csv",
        mime="text/csv",
    )

# ---------- Visiting history ----------
st.subheader("Visiting History")
visits = data["encounters"]
visits = visits[visits["PATIENT"] == patient_id].sort_values("START", ascending=False)
with st.container(border=True):
    st.dataframe(
        visits[["START", "ENCOUNTERCLASS", "DESCRIPTION", "REASONDESCRIPTION"]],
        use_container_width=True,
        hide_index=True,
    )

# ---------- Vitals charts ----------
st.subheader("Visualization Of Vitals Over Time")
pv = vitals[vitals["PATIENT"] == patient_id].set_index("DATE")


def draw(label, container):
    cfg = CHARTS[label]
    df = pv.reset_index()[["DATE", *cfg["cols"]]].rename(columns=cfg["cols"])
    df = df.melt("DATE", var_name="Measure", value_name="Value").dropna()

    container.markdown(f"**{label}** ({cfg['unit']})")
    if df.empty:
        container.info("No readings for this patient.")
        return

    line = alt.Chart(df).mark_line(point=True).encode(
        x=alt.X("DATE:T", title="Visit date"),
        y=alt.Y("Value:Q", title=cfg["unit"], scale=alt.Scale(zero=False)),
        color=alt.Color("Measure:N", title=None),
        tooltip=["DATE:T", "Measure:N", "Value:Q"],
    )
    rules = alt.Chart(pd.DataFrame({"y": cfg["refs"]})).mark_rule(
        strokeDash=[4, 4], color="red"
    ).encode(y="y:Q")
    container.altair_chart(line + rules, use_container_width=True)


if vital_label == "All vitals":
    grid = st.columns(2)
    for i, label in enumerate(CHARTS):
        draw(label, grid[i % 2])
else:
    draw(vital_label, st)
