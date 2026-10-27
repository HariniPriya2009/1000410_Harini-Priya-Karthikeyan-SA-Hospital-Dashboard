"""
MediScope Health Analytics - Hospital Inpatient Discharges Dashboard
====================================================================
An interactive Streamlit dashboard for exploring de-identified hospital
inpatient discharge records (patient demographics, diagnoses, length of stay,
charges, costs, severity, hospitals, counties and payment types).

This is a DATA ANALYTICS tool. It is not a clinical diagnosis tool.

Run locally:   streamlit run app.py

File layout (read top to bottom):
    1. Constants & column mapping
    2. Formatting helpers
    3. Data loading & cleaning
    4. Sidebar filters
    5. Chart helpers & chart functions
    6. Pages (Summary, Patient, Cost, Hospital, Data Quality)
    7. main()
"""

from __future__ import annotations

import re
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# st.set_page_config must be the first Streamlit command.
st.set_page_config(
    page_title="MediScope Health Analytics",
    page_icon="🩺",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# 1. CONSTANTS & COLUMN MAPPING
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).parent
DEFAULT_FILES = [BASE_DIR / "hospital_discharges.csv", BASE_DIR / "hospital_discharges.xlsx"]

# Colour palette (from the project brief)
PRIMARY = "#706DB3"
DARK = "#514F91"
BG = "#F3F2FB"
CARD = "#FFFFFF"
TEXT = "#292A46"
TEAL = "#67B7B0"
MUTED = "#6B6C8A"
PALETTE = [PRIMARY, TEAL, "#9C99D6", DARK, "#A8D8D3", "#C9C7EA", "#8E8BC7", "#3F8F89"]

SEVERITY_ORDER = ["Minor", "Moderate", "Major", "Extreme"]
SEVERITY_COLORS = {"Minor": "#A8D8D3", "Moderate": TEAL, "Major": "#8E8BC7", "Extreme": DARK, "Unknown": "#C9C7EA"}
SEVERITY_CODE_MAP = {"1": "Minor", "2": "Moderate", "3": "Major", "4": "Extreme"}

# Internal (canonical) column name -> accepted raw names. The first raw name is
# also the friendly label used in tables and downloads. Add more spellings here
# if your dataset uses different headings.
RAW_COLUMNS = {
    "service_area": ["Hospital Service Area"],
    "county": ["Hospital County", "County"],
    "operating_cert": ["Operating Certificate Number"],
    "facility_id": ["Permanent Facility Id", "Permanent Facility ID"],
    "facility": ["Facility Name", "Facility", "Hospital Name"],
    "age_group": ["Age Group"],
    "zip3": ["Zip Code - 3 digits", "Zip Code 3 digits"],
    "gender": ["Gender", "Sex"],
    "race": ["Race"],
    "ethnicity": ["Ethnicity"],
    "los": ["Length of Stay", "LOS"],
    "admission_type": ["Type of Admission", "Admission Type"],
    "disposition": ["Patient Disposition", "Disposition"],
    "year": ["Discharge Year", "Year"],
    "dx_code": ["CCSR Diagnosis Code"],
    "dx_desc": ["CCSR Diagnosis Description"],
    "proc_code": ["CCSR Procedure Code"],
    "proc_desc": ["CCSR Procedure Description"],
    "drg_code": ["APR DRG Code"],
    "drg_desc": ["APR DRG Description"],
    "mdc_code": ["APR MDC Code"],
    "mdc_desc": ["APR MDC Description"],
    "sev_code": ["APR Severity of Illness Code"],
    "severity": ["APR Severity of Illness Description", "Severity of Illness"],
    "mortality": ["APR Risk of Mortality"],
    "med_surg": ["APR Medical Surgical Description"],
    "pay1": ["Payment Typology 1"],
    "pay2": ["Payment Typology 2"],
    "pay3": ["Payment Typology 3"],
    "birth_weight": ["Birth Weight"],
    "ed_indicator": ["Emergency Department Indicator"],
    "charges": ["Total Charges"],
    "costs": ["Total Costs"],
}
LABELS = {key: names[0] for key, names in RAW_COLUMNS.items()}
NUMERIC_COLUMNS = ["los", "charges", "costs", "year", "birth_weight"]
CATEGORICAL_COLUMNS = [c for c in RAW_COLUMNS if c not in NUMERIC_COLUMNS]
HIDDEN_COLUMNS = ["zip3", "operating_cert", "facility_id"]  # not shown in previews/downloads
ESSENTIAL_COLUMNS = ["age_group", "gender", "los", "charges", "costs", "severity", "facility", "county", "pay1"]

# Sidebar filters: (column, label)
FILTERS = [
    ("year", "Discharge year"),
    ("county", "Hospital county"),
    ("facility", "Facility name"),
    ("age_group", "Age group"),
    ("gender", "Gender"),
    ("severity", "Severity of illness"),
    ("admission_type", "Type of admission"),
    ("pay1", "Payment type"),
]

PAGES = ["Summary", "Patient Analysis", "Cost Analysis", "Hospital Analysis", "Data Quality"]
PAGE_ICONS = {"Summary": "📊", "Patient Analysis": "🧑‍⚕️", "Cost Analysis": "💳", "Hospital Analysis": "🏥", "Data Quality": "🧹"}

# Streamlit renamed use_container_width -> width="stretch" in newer releases.
_ST_VERSION = tuple(int(x) for x in re.findall(r"\d+", st.__version__)[:2])
_NEW_WIDTH_API = _ST_VERSION >= (1, 50)
STRETCH = {"width": "stretch"} if _NEW_WIDTH_API else {"use_container_width": True}


# ---------------------------------------------------------------------------
# 2. FORMATTING HELPERS
# ---------------------------------------------------------------------------
def cur() -> str:
    """Currency symbol chosen in the sidebar."""
    return st.session_state.get("currency", "$")


def fmt_int(value) -> str:
    return "–" if value is None or pd.isna(value) else f"{int(round(value)):,}"


def fmt_money(value) -> str:
    """Readable currency: 1,234 -> $1,234 ; 1.2e6 -> $1.20M ; 3.4e9 -> $3.40B."""
    if value is None or pd.isna(value):
        return "–"
    sign = "-" if value < 0 else ""
    amount = abs(float(value))
    for limit, suffix in [(1e9, "B"), (1e6, "M"), (1e3, "K")]:
        if amount >= limit:
            return f"{sign}{cur()}{amount / limit:,.2f}{suffix}"
    return f"{sign}{cur()}{amount:,.0f}"


def short(label: str, n: int = 42) -> str:
    label = str(label)
    return label if len(label) <= n else label[: n - 1] + "…"


def age_sort_key(label: str) -> int:
    """Sort age groups by their first number ('0 to 17' < '18 to 29' < '70 or Older')."""
    match = re.search(r"\d+", str(label))
    return int(match.group()) if match else 10_000


# ---------------------------------------------------------------------------
# 3. DATA LOADING & CLEANING
# ---------------------------------------------------------------------------
def normalise_name(name) -> str:
    """'Zip Code - 3 digits ' -> 'zipcode3digits' (so small spelling differences still match)."""
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def map_columns(raw: pd.DataFrame):
    """Rename raw columns to canonical names. Returns (dataframe, unmapped_column_names)."""
    lookup = {normalise_name(alias): key for key, aliases in RAW_COLUMNS.items() for alias in aliases}
    rename, used = {}, set()
    for col in raw.columns:
        key = lookup.get(normalise_name(col))
        if key and key not in used:
            rename[col] = key
            used.add(key)
    unmapped = [str(c) for c in raw.columns if c not in rename]
    return raw[list(rename)].rename(columns=rename), unmapped


def clean_text(series: pd.Series) -> pd.Series:
    """Trim spaces, collapse repeated spaces, and turn blank/'nan' strings into real missing values."""
    s = series.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    return s.mask(s.str.lower().isin(["", "nan", "none", "null", "n/a", "na"]))


def parse_number(series: pd.Series) -> pd.Series:
    """'$1,234.50' -> 1234.5. Removes currency symbols, commas and other formatting characters."""
    cleaned = series.astype("string").str.replace(r"[^0-9.\-]", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce").astype("float64")


def standardise_age(series: pd.Series) -> pd.Series:
    s = series.str.replace(r"\s*-\s*", " to ", regex=True)
    return s.str.replace(r"(?i)\bor older\b", "or Older", regex=True)


GENDER_MAP = {"m": "Male", "male": "Male", "f": "Female", "female": "Female", "u": "Unknown", "unknown": "Unknown", "other": "Other"}


def standardise_gender(series: pd.Series) -> pd.Series:
    mapped = series.str.lower().map(GENDER_MAP)
    return mapped.fillna(series.str.title())


def read_table(source: str, file_bytes: bytes) -> pd.DataFrame:
    """Read a CSV/Excel file (from an upload or from disk). Everything is read as text first."""
    buffer = BytesIO(file_bytes) if file_bytes else source
    if str(source).lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(buffer, dtype=str)
    return pd.read_csv(buffer, dtype=str, low_memory=False, encoding_errors="replace")


def clean_data(raw: pd.DataFrame, drop_duplicates: bool = False):
    """
    Reusable cleaning function. Returns (clean_dataframe, report_dict).
    Nothing is silently deleted: invalid values become missing, duplicates are
    only removed if the user chooses, and outliers are counted but kept.
    """
    df, unmapped = map_columns(raw)
    notes = []
    report = {
        "raw_rows": len(raw),
        "raw_cols": raw.shape[1],
        "unmapped_cols": unmapped,
        "absent_cols": [LABELS[c] for c in ESSENTIAL_COLUMNS if c not in df.columns],
        "notes": notes,
    }

    # Step 1: trim every text column and mark blanks as missing.
    for col in df.columns:
        df[col] = clean_text(df[col])
    report["missing_by_col"] = df.isna().sum()

    # Step 2: duplicates are reported first; removal is optional.
    report["duplicates"] = int(df.duplicated().sum())
    if drop_duplicates and report["duplicates"]:
        df = df.drop_duplicates().reset_index(drop=True)
        notes.append(f"{report['duplicates']:,} exact duplicate rows were removed (sidebar option).")
    elif report["duplicates"]:
        notes.append(
            f"{report['duplicates']:,} exact duplicate rows were found and KEPT. In de-identified discharge data, "
            "identical rows can be genuinely different patients. Tick the sidebar option to remove them."
        )

    # Step 3: length of stay -> numeric. Negative / unreadable values are invalid.
    report["los_topcoded"], report["invalid_los"] = 0, 0
    if "los" in df.columns:
        raw_los = df["los"]
        report["los_topcoded"] = int(raw_los.str.contains("+", regex=False, na=False).sum())
        los = parse_number(raw_los)
        invalid = (los < 0) | (los.isna() & raw_los.notna())
        report["invalid_los"] = int(invalid.sum())
        df["los"] = los.where(~invalid)  # invalid -> missing, so only length-of-stay analyses skip them
        if report["invalid_los"]:
            notes.append(f"{report['invalid_los']:,} invalid length-of-stay values (negative or unreadable) were set to missing; the records themselves are kept.")
        if report["los_topcoded"]:
            notes.append(f"{report['los_topcoded']:,} stays are top-coded (e.g. '120+'). They are treated as the number shown, so long-stay averages may be slightly low.")

    # Step 4: money columns -> numeric.
    report["negative_money"] = 0
    for col in ["charges", "costs"]:
        if col in df.columns:
            df[col] = parse_number(df[col])
            report["negative_money"] += int((df[col] < 0).sum())

    # Step 5: outliers are counted, never deleted (Tukey fence: Q3 + 3 x IQR).
    report["extreme_charges"], report["extreme_fence"] = 0, None
    if "charges" in df.columns and df["charges"].notna().any():
        q1, q3 = df["charges"].quantile([0.25, 0.75])
        fence = float(q3 + 3 * (q3 - q1))
        report["extreme_fence"] = fence
        report["extreme_charges"] = int((df["charges"] > fence).sum())

    # Step 6: discharge year -> whole number (falls back to parsing dates).
    if "year" in df.columns:
        years = pd.to_numeric(df["year"], errors="coerce")
        if years.notna().mean() < 0.5:
            years = pd.to_datetime(df["year"], errors="coerce").dt.year
        df["year"] = years.astype("Int64")

    # Step 7: standardise labels.
    if "age_group" in df.columns:
        df["age_group"] = standardise_age(df["age_group"])
    if "gender" in df.columns:
        df["gender"] = standardise_gender(df["gender"])
    if "severity" in df.columns:
        df["severity"] = df["severity"].str.title()
    elif "sev_code" in df.columns:
        df["severity"] = df["sev_code"].map(SEVERITY_CODE_MAP)
        notes.append("Severity descriptions were built from the severity codes (1=Minor ... 4=Extreme).")

    # Step 8: birth weight is only meaningful for newborns - drop it if mostly empty/zero.
    if "birth_weight" in df.columns:
        birth_weight = parse_number(df["birth_weight"])
        usable = float((birth_weight > 0).mean())
        if usable < 0.5:
            df = df.drop(columns="birth_weight")
            notes.append(f"Birth Weight was excluded: only {usable:.1%} of records have a usable value (it applies to newborns).")
        else:
            df["birth_weight"] = birth_weight

    # Step 9: missing categories become 'Unknown' (records are never dropped); order age/severity logically.
    for col in CATEGORICAL_COLUMNS + ["severity"]:
        if col not in df.columns:
            continue
        values = df[col].fillna("Unknown").astype(str)
        present = list(pd.unique(values))
        if col == "age_group":
            order = sorted(present, key=age_sort_key)
        elif col == "severity":
            order = [c for c in SEVERITY_ORDER if c in present] + sorted(c for c in present if c not in SEVERITY_ORDER)
        else:
            order = None
        df[col] = pd.Categorical(values, categories=order, ordered=True) if order else values.astype("category")

    report["missing_cells"] = int(report["missing_by_col"].sum())
    return df.reset_index(drop=True), report


@st.cache_data(show_spinner="Loading and cleaning the dataset…")
def load_and_clean(source: str, file_bytes: bytes, stamp: float, drop_duplicates: bool):
    """Cached wrapper: the file is only read and cleaned again when the inputs change."""
    return clean_data(read_table(source, file_bytes), drop_duplicates)


# ---------------------------------------------------------------------------
# 4. SIDEBAR FILTERS
# ---------------------------------------------------------------------------
def filter_options(df: pd.DataFrame, col: str) -> list:
    if col == "year":
        return sorted(int(v) for v in df[col].dropna().unique())
    if isinstance(df[col].dtype, pd.CategoricalDtype):
        return [str(c) for c in df[col].cat.categories]
    return sorted(df[col].dropna().astype(str).unique())


def clear_filters() -> None:
    for col, _ in FILTERS:
        st.session_state[f"flt_{col}"] = []


def render_filters(df: pd.DataFrame) -> None:
    st.markdown("### Filters")
    for col, label in FILTERS:
        if col in df.columns:
            st.multiselect(label, filter_options(df, col), key=f"flt_{col}", placeholder="All")
        else:
            st.caption(f"{label}: column not found in dataset")
    st.button("Clear Filters", on_click=clear_filters, key="clear_filters", **STRETCH)


def apply_filters(df: pd.DataFrame) -> pd.DataFrame:
    mask = pd.Series(True, index=df.index)
    for col, _ in FILTERS:
        selected = st.session_state.get(f"flt_{col}")
        if col in df.columns and selected:
            mask &= df[col].isin(selected)
    return df[mask]


# ---------------------------------------------------------------------------
# 5. CHART HELPERS & CHART FUNCTIONS
# ---------------------------------------------------------------------------
def style(fig: go.Figure, title: str, height: int = 340, legend: bool = False) -> go.Figure:
    """Apply the same look to every chart."""
    fig.update_layout(
        title=dict(text=title, x=0, xanchor="left", font=dict(size=15, color=DARK)),
        height=height,
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI, Roboto, Helvetica, Arial, sans-serif", color=TEXT, size=12),
        margin=dict(l=10, r=10, t=50, b=10),
        showlegend=legend,
        colorway=PALETTE,
        hoverlabel=dict(bgcolor="white", font_size=12),
    )
    fig.update_xaxes(gridcolor="#ECEBF7", zeroline=False, automargin=True)
    fig.update_yaxes(gridcolor="#ECEBF7", zeroline=False, automargin=True)
    return fig


def show_chart(fig: go.Figure, key: str) -> None:
    config = {"displaylogo": False, "responsive": True}
    st.plotly_chart(fig, key=f"chart_{key}", config=config, **STRETCH)


def show_table(data: pd.DataFrame, **kwargs) -> None:
    st.dataframe(data, hide_index=True, **STRETCH, **kwargs)


@contextmanager
def card(key: str):
    """A white rounded panel (styled in the CSS through the 'card_' key prefix)."""
    with st.container(key=f"card_{key}"):
        yield


def plot(fig, key: str, note: str | None = None) -> None:
    """Show a chart (or a friendly message if it cannot be drawn) plus a one-line explanation."""
    if fig is None:
        st.info("This chart needs a column that is missing from the dataset, or no records match the current filters.")
    else:
        show_chart(fig, key)
    if note:
        st.caption(note)


def grid(renderers: list) -> None:
    """Lay chart panels out two per row (they stack automatically on small screens)."""
    for i in range(0, len(renderers), 2):
        for column, render in zip(st.columns(2), renderers[i : i + 2]):
            with column:
                render()


def sample(df: pd.DataFrame, n: int) -> pd.DataFrame:
    """Random sample so very large datasets stay responsive (fixed seed = repeatable)."""
    return df if len(df) <= n else df.sample(n, random_state=42)


def top_values(df: pd.DataFrame, col: str, n: int) -> list:
    counts = df[col].value_counts()
    return [str(v) for v in counts[counts > 0].head(n).index]


def top_with_other(g: pd.DataFrame, name_col: str, value_col: str, n: int) -> pd.DataFrame:
    g = g.sort_values(value_col, ascending=False)
    if len(g) <= n:
        return g
    other = pd.DataFrame({name_col: ["Other"], value_col: [g.iloc[n:][value_col].sum()]})
    return pd.concat([g.head(n), other], ignore_index=True)


def trim_extremes(df: pd.DataFrame, col: str, percentile: float) -> pd.DataFrame:
    """Hide values above a percentile from a CHART only. The dataset itself is never changed."""
    if col not in df.columns or df[col].notna().sum() == 0:
        return df
    limit = df[col].quantile(percentile / 100)
    return df[df[col].isna() | (df[col] <= limit)]


# ----- counts & distributions ----------------------------------------------------------------
def fig_counts(df, col, title, horizontal=False, top=None, color=PRIMARY, height=340):
    """Bar chart of discharge counts for one categorical column."""
    if col not in df.columns or df.empty:
        return None
    g = df.groupby(col, observed=True).size().reset_index(name="Discharges")
    g[col] = g[col].astype(str)
    if horizontal or top:
        g = g.sort_values("Discharges", ascending=False)
    if top:
        g = g.head(top)
    label = LABELS.get(col, col)
    if horizontal:
        fig = px.bar(g, x="Discharges", y=col, orientation="h", labels={col: label})
        fig.update_yaxes(autorange="reversed")
    else:
        fig = px.bar(g, x=col, y="Discharges", labels={col: label})
        fig.update_xaxes(type="category", categoryorder="array", categoryarray=list(g[col]))
    fig.update_traces(marker_color=color, hovertemplate=f"{label}: %{{{'y' if horizontal else 'x'}}}<br>Discharges: %{{{'x' if horizontal else 'y'}:,}}<extra></extra>")
    return style(fig, title, height)


def fig_donut(df, col, title, top=None):
    if col not in df.columns or df.empty:
        return None
    g = df.groupby(col, observed=True).size().reset_index(name="Discharges")
    g[col] = g[col].astype(str)
    if top:
        g = top_with_other(g, col, "Discharges", top)
    fig = px.pie(g, names=col, values="Discharges", hole=0.55, color_discrete_sequence=PALETTE)
    fig.update_traces(textinfo="percent", sort=False, hovertemplate="%{label}<br>%{value:,} discharges (%{percent})<extra></extra>")
    return style(fig, title, legend=True)


def fig_year(df):
    if "year" not in df.columns or df["year"].nunique() < 2:
        return None  # a single year would make a misleading "trend"
    g = df.dropna(subset=["year"]).groupby("year").size().reset_index(name="Discharges")
    g["Year"] = g["year"].astype(int).astype(str)
    fig = px.line(g, x="Year", y="Discharges", markers=True)
    fig.update_traces(line_color=PRIMARY, marker_size=8, hovertemplate="Year %{x}<br>Discharges: %{y:,}<extra></extra>")
    fig.update_xaxes(type="category")
    return style(fig, "Discharge records by year")


def fig_los_hist(df, group_long=True):
    """Histogram built with NumPy so it stays fast even with millions of rows."""
    if "los" not in df.columns:
        return None
    values = df["los"].dropna()
    if values.empty:
        return None
    cap = float(values.quantile(0.99)) if group_long else float(values.max())
    cap = max(1, int(np.ceil(cap)))
    width = max(1, int(np.ceil(cap / 40)))
    edges = np.arange(0, cap + width + 1, width)
    counts, _ = np.histogram(values.clip(upper=cap), bins=edges)
    last = int(np.searchsorted(edges, cap, side="right")) - 1
    counts, starts = counts[: last + 1], edges[: last + 1]
    has_long = group_long and bool((values > cap).any())
    labels = [f"{s}–{s + width - 1} days" if width > 1 else f"{s} days" for s in starts]
    if has_long:
        labels[-1] = f"{starts[-1]}+ days (includes all longer stays)"
    fig = go.Figure(go.Bar(x=starts + width / 2, y=counts, width=width * 0.92, marker_color=PRIMARY, customdata=labels,
                           hovertemplate="%{customdata}<br>Discharges: %{y:,}<extra></extra>"))
    median = float(values.median())
    fig.add_vline(x=median + 0.5, line_dash="dash", line_color=TEAL, annotation_text=f"Median {median:.0f} d", annotation_position="top right")
    fig.update_xaxes(title="Length of stay (days)")
    fig.update_yaxes(title="Discharge records")
    return style(fig, "Length of stay distribution")


# ----- diagnoses ------------------------------------------------------------------------------
def diag_table(df, basis, min_n):
    """Average length of stay per diagnosis (only groups with at least min_n records)."""
    if basis not in df.columns or "los" not in df.columns:
        return pd.DataFrame()
    d = df.dropna(subset=["los"])
    d = d[d[basis] != "Unknown"]
    g = d.groupby(basis, observed=True)["los"].agg(Discharges="size", AvgLOS="mean").reset_index()
    g = g[g["Discharges"] >= min_n].rename(columns={basis: "Label"})
    g["Label"] = g["Label"].astype(str)
    if basis == "dx_code" and "dx_desc" in df.columns:
        names = d.groupby("dx_code", observed=True)["dx_desc"].first().astype(str)
        g["Full"] = g["Label"] + " – " + g["Label"].map(names).fillna("")
    else:
        g["Full"] = g["Label"]
    return g


def fig_dx_bar(g, rank_by, top_n, title):
    if g is None or g.empty:
        return None
    sort_col = "AvgLOS" if rank_by == "Average length of stay" else "Discharges"
    g = g.sort_values(sort_col, ascending=False).head(top_n).copy()
    g["Short"] = g["Full"].map(short)
    if g["Short"].duplicated().any():
        g["Short"] = g["Full"]
    fig = go.Figure(go.Bar(
        x=g["AvgLOS"], y=g["Short"], orientation="h", marker_color=PRIMARY,
        customdata=g[["Full", "Discharges"]].to_numpy(),
        hovertemplate="%{customdata[0]}<br>Average stay: %{x:.2f} days<br>Discharges: %{customdata[1]:,}<extra></extra>"))
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title="Average length of stay (days)")
    return style(fig, title, height=max(320, 34 * len(g) + 90))


def fig_charges_age_gender(df):
    need = {"age_group", "gender", "charges"}
    if not need.issubset(df.columns):
        return None
    g = df.dropna(subset=["charges"]).groupby(["age_group", "gender"], observed=True)["charges"].agg(Average="mean", Records="size").reset_index()
    if g.empty:
        return None
    g["age_group"], g["gender"] = g["age_group"].astype(str), g["gender"].astype(str)
    fig = px.bar(g, x="age_group", y="Average", color="gender", barmode="group", custom_data=["Records"],
                 category_orders={"age_group": sorted(g["age_group"].unique(), key=age_sort_key)},
                 labels={"age_group": "Age group", "Average": f"Average total charges ({cur()})", "gender": "Gender"},
                 color_discrete_sequence=PALETTE)
    fig.update_traces(hovertemplate="Age group: %{x}<br>Average charges: " + cur() + "%{y:,.0f}<br>Records: %{customdata[0]:,}<extra></extra>")
    return style(fig, "Average total charges by age group and gender", legend=True)


# ----- costs & severity -----------------------------------------------------------------------
def fig_box(df, value_col, title, ytitle, log=False, n=20000):
    if not {"severity", value_col}.issubset(df.columns):
        return None
    d = df.dropna(subset=[value_col])
    if log:
        d = d[d[value_col] > 0]
    if d.empty:
        return None
    d = sample(d, n).copy()
    d["severity"] = d["severity"].astype(str)
    order = [s for s in df["severity"].cat.categories if s in set(d["severity"])]
    fig = px.box(d, x="severity", y=value_col, color="severity", color_discrete_map=SEVERITY_COLORS,
                 category_orders={"severity": order}, labels={"severity": "Severity of illness", value_col: ytitle})
    if log:
        fig.update_yaxes(type="log")
    return style(fig, title, height=360)


def fig_by_severity(df, col, how, title, ytitle):
    """Average or total of charges/costs for each severity level."""
    if not {"severity", col}.issubset(df.columns):
        return None
    g = df.dropna(subset=[col]).groupby("severity", observed=True)[col].agg(Total="sum", Average="mean", Records="size").reset_index()
    if g.empty:
        return None
    g["severity"] = g["severity"].astype(str)
    fig = px.bar(g, x="severity", y=how, color="severity", color_discrete_map=SEVERITY_COLORS, custom_data=["Records", "Average", "Total"],
                 labels={"severity": "Severity of illness", how: ytitle})
    fig.update_traces(hovertemplate="%{x}<br>Records: %{customdata[0]:,}<br>Average: " + cur() + "%{customdata[1]:,.0f}<br>Total: " + cur() + "%{customdata[2]:,.0f}<extra></extra>")
    return style(fig, title)


def fig_scatter(df, n=5000):
    if not {"los", "charges"}.issubset(df.columns):
        return None
    d = df.dropna(subset=["los", "charges"])
    if d.empty:
        return None
    d = sample(d, n).copy()
    color = "severity" if "severity" in d.columns else None
    if color:
        d["severity"] = d["severity"].astype(str)
    hover = [c for c in ["dx_desc", "age_group", "pay1"] if c in d.columns]
    fig = px.scatter(d, x="los", y="charges", color=color, color_discrete_map=SEVERITY_COLORS, opacity=0.55, hover_data=hover,
                     labels={"los": "Length of stay (days)", "charges": f"Total charges ({cur()})", "severity": "Severity"})
    return style(fig, f"Length of stay vs total charges (random sample of up to {n:,} records)", height=380, legend=True)


def fig_age_cost(df):
    if not {"age_group", "charges", "costs"}.issubset(df.columns):
        return None
    g = df.groupby("age_group", observed=True).agg(Charges=("charges", "mean"), Costs=("costs", "mean"), Records=("charges", "size")).reset_index()
    if g.empty:
        return None
    g["age_group"] = g["age_group"].astype(str)
    fig = go.Figure()
    for col, color in [("Charges", PRIMARY), ("Costs", TEAL)]:
        fig.add_bar(x=g["age_group"], y=g[col], name=f"Average total {col.lower()}", marker_color=color, customdata=g["Records"],
                    hovertemplate="%{x}<br>" + col + ": " + cur() + "%{y:,.0f}<br>Records: %{customdata:,}<extra></extra>")
    fig.update_layout(barmode="group")
    fig.update_yaxes(title=f"Average amount ({cur()})")
    fig.update_xaxes(title="Age group", type="category")
    return style(fig, "Average charges vs average costs by age group", legend=True)


def fig_pay_charges(df, min_n):
    if not {"pay1", "charges"}.issubset(df.columns):
        return None
    g = df.dropna(subset=["charges"]).groupby("pay1", observed=True)["charges"].agg(Average="mean", Records="size").reset_index()
    g = g[g["Records"] >= min_n].sort_values("Average", ascending=False)
    if g.empty:
        return None
    g["pay1"] = g["pay1"].astype(str)
    fig = px.bar(g, x="Average", y="pay1", orientation="h", custom_data=["Records"],
                 labels={"pay1": "Primary payment type", "Average": f"Average total charges ({cur()})"})
    fig.update_traces(marker_color=PRIMARY, hovertemplate="%{y}<br>Average charges: " + cur() + "%{x:,.0f}<br>Records: %{customdata[0]:,}<extra></extra>")
    fig.update_yaxes(autorange="reversed")
    return style(fig, "Average total charges by primary payment type", height=max(320, 32 * len(g) + 90))


# ----- hospitals ------------------------------------------------------------------------------
def fig_heatmap(df, col, n_fac, n_col, min_n):
    """Mean length of stay for the busiest facilities (rows) across a second dimension (columns)."""
    if not {"facility", col, "los"}.issubset(df.columns):
        return None
    d = df.dropna(subset=["los"])
    d = d[(d["facility"] != "Unknown") & (d[col] != "Unknown")]
    if d.empty:
        return None
    facilities, columns = top_values(d, "facility", n_fac), top_values(d, col, n_col)
    d = d[d["facility"].isin(facilities) & d[col].isin(columns)]
    args = dict(index="facility", columns=col, values="los", observed=True)
    mean, size = d.pivot_table(aggfunc="mean", **args), d.pivot_table(aggfunc="count", **args)  # MEAN stay, not the sum
    mean = mean.where(size >= min_n).dropna(how="all").dropna(axis=1, how="all")
    if mean.empty:
        return None
    mean = mean.reindex([f for f in facilities if f in mean.index])
    ordered = isinstance(d[col].dtype, pd.CategoricalDtype) and d[col].cat.ordered
    keep = [c for c in (d[col].cat.categories if ordered else columns) if c in mean.columns]
    mean = mean[keep]
    ys, xs = [str(i) for i in mean.index], [str(c) for c in mean.columns]
    label = LABELS.get(col, col)
    fig = go.Figure(go.Heatmap(z=mean.to_numpy(), x=xs, y=ys, hoverongaps=False, colorscale=[[0, BG], [0.5, "#9C99D6"], [1, DARK]],
                               colorbar=dict(title="Avg stay (days)"),
                               hovertemplate="%{y}<br>" + label + ": %{x}<br>Average stay: %{z:.2f} days<extra></extra>"))
    fig.update_yaxes(autorange="reversed", tickmode="array", tickvals=ys, ticktext=[short(y, 38) for y in ys])
    fig.update_xaxes(title=label, type="category")
    return style(fig, f"Average length of stay: facility × {label.lower()}", height=max(380, 24 * len(ys) + 140))


def fig_county_los(df, min_n, top=15):
    if not {"county", "los"}.issubset(df.columns):
        return None
    d = df.dropna(subset=["los"])
    d = d[d["county"] != "Unknown"]
    g = d.groupby("county", observed=True)["los"].agg(Average="mean", Discharges="size").reset_index()
    g = g[g["Discharges"] >= min_n].sort_values("Average", ascending=False).head(top)
    if g.empty:
        return None
    g["county"] = g["county"].astype(str)
    fig = px.bar(g, x="Average", y="county", orientation="h", custom_data=["Discharges"], labels={"county": "County", "Average": "Average length of stay (days)"})
    fig.update_traces(marker_color=TEAL, hovertemplate="%{y}<br>Average stay: %{x:.2f} days<br>Discharges: %{customdata[0]:,}<extra></extra>")
    fig.update_yaxes(autorange="reversed")
    return style(fig, f"Counties with the longest average stay (top {len(g)})", height=max(320, 28 * len(g) + 90))


def hospital_table(df):
    if not {"facility", "county"}.issubset(df.columns):
        return pd.DataFrame()
    spec = {"Discharges": ("facility", "size")}
    if "los" in df.columns:
        spec["Avg Stay (days)"] = ("los", "mean")
    if "charges" in df.columns:
        spec[f"Avg Charges ({cur()})"] = ("charges", "mean")
    if "costs" in df.columns:
        spec[f"Total Costs ({cur()})"] = ("costs", "sum")
    g = df.groupby(["facility", "county"], observed=True).agg(**spec).reset_index()
    g = g[g["Discharges"] > 0].sort_values("Discharges", ascending=False)
    g = g.rename(columns={"facility": "Hospital", "county": "County"})
    g["Hospital"], g["County"] = g["Hospital"].astype(str), g["County"].astype(str)
    for col in g.columns[3:]:
        g[col] = g[col].round(2 if "Stay" in col else 0)
    return g


# ---------------------------------------------------------------------------
# 6. PAGES
# ---------------------------------------------------------------------------
def page_header(title: str, subtitle: str) -> None:
    st.markdown(f'<div class="page-title">{title}</div><div class="page-sub">{subtitle}</div>', unsafe_allow_html=True)


def section(title: str) -> None:
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)


def kpi_cards(items: list) -> None:
    for column, (icon, label, value) in zip(st.columns(len(items)), items):
        column.markdown(
            f'<div class="kpi"><div class="kpi-icon">{icon}</div>'
            f'<div><div class="kpi-label">{label}</div><div class="kpi-value">{value}</div></div></div>',
            unsafe_allow_html=True,
        )


def download_block(data: pd.DataFrame, label: str, filename: str, key: str) -> None:
    """CSV download (identifier-style columns removed). Very large files are prepared on request."""
    out = data.drop(columns=[c for c in HIDDEN_COLUMNS if c in data.columns]).rename(columns=LABELS)
    if len(out) <= 100_000 or st.checkbox(f"Prepare {label.lower()} ({len(out):,} rows)", key=f"prep_{key}"):
        st.download_button(label, out.to_csv(index=False).encode("utf-8"), file_name=filename, mime="text/csv", key=f"dl_{key}", **STRETCH)


def page_summary(f: pd.DataFrame, total_rows: int) -> None:
    page_header("Hospital Inpatient Discharges Dashboard",
                "Interactive insights into patient demographics, hospital utilisation, and healthcare expenditure.")
    avg_los = f["los"].mean() if "los" in f.columns else np.nan
    charges = f["charges"].sum() if "charges" in f.columns else np.nan
    costs = f["costs"].sum() if "costs" in f.columns else np.nan
    kpi_cards([("📋", "Total Discharge Records", fmt_int(len(f))),
               ("⏱️", "Average Length of Stay", "–" if pd.isna(avg_los) else f"{avg_los:.2f} days"),
               ("💳", "Total Hospital Charges", fmt_money(charges)),
               ("🏥", "Total Hospital Costs", fmt_money(costs))])

    info, download = st.columns([3, 1])
    info.caption(f"Showing {len(f):,} of {total_rows:,} records. Amounts use the “{cur()}” symbol (change it under Dataset & options in the sidebar; "
                 "check your dataset documentation for the real currency). Charges = amounts billed; costs = estimated cost of providing care.")
    with download:
        download_block(f, "Download filtered data (CSV)", "filtered_discharges.csv", "summary")

    with st.expander("The 5 research questions this dashboard helps you explore"):
        st.markdown("1. **Which diagnoses are linked to the longest stays?** → Patient Analysis, diagnosis chart\n"
                    "2. **How do charges vary by age group and gender?** → Patient Analysis and Cost Analysis\n"
                    "3. **How does severity relate to charges and length of stay?** → Cost Analysis\n"
                    "4. **Which hospitals and counties have the longest average stay?** → Hospital Analysis\n"
                    "5. **How do payment types differ in volume and charges?** → Cost Analysis, payment section")

    def r_year():
        with card("year"):
            plot(fig_year(f), "year", "Helps you see whether discharge volume is rising or falling over time.")

    def r_adm():
        with card("adm"):
            plot(fig_counts(f, "admission_type", "Discharges by type of admission", horizontal=True), "adm",
                 "Shows how patients arrive (e.g. emergency, elective) - useful for planning capacity.")

    def r_gender():
        with card("gender"):
            plot(fig_donut(f, "gender", "Patient gender distribution"), "gender", "Share of discharge records by gender.")

    def r_los():
        with card("los"):
            group = st.toggle("Group very long stays (above the 99th percentile) into the last bar", value=True, key="los_group_summary")
            plot(fig_los_hist(f, group), "los", "Most stays are short, with a long tail. The dashed line marks the median. Long stays are kept, not deleted.")

    def r_extra():
        with card("extra"):
            col = "severity" if "severity" in f.columns else "disposition"
            plot(fig_counts(f, col, f"Discharges by {LABELS.get(col, col).lower()}"), "extra", "Only one discharge year is present, so no yearly trend is shown.")

    has_trend = "year" in f.columns and f["year"].nunique() > 1
    grid([r_year, r_adm, r_gender, r_los] if has_trend else [r_adm, r_gender, r_los, r_extra])


def page_patient(f: pd.DataFrame) -> None:
    page_header("Patient Analysis", "Who is being discharged, and how do length of stay and charges differ across patient groups?")

    def r_age():
        with card("age"):
            plot(fig_counts(f, "age_group", "Discharge records by age group"), "age", "Age groups are shown in logical order, not alphabetically.")

    def r_gender():
        with card("gender2"):
            plot(fig_donut(f, "gender", "Gender distribution"), "gender2", "Share of discharge records by gender.")

    def r_race():
        with card("race"):
            plot(fig_counts(f, "race", "Race distribution", horizontal=True), "race", "Records by recorded race category. Differences in counts reflect who the hospitals treat, not risk.")

    def r_eth():
        with card("eth"):
            plot(fig_counts(f, "ethnicity", "Ethnicity distribution", horizontal=True), "eth", "Records by recorded ethnicity category.")

    grid([r_age, r_gender, r_race, r_eth])

    section("Diagnoses and length of stay (research question 1)")
    options = {"Diagnosis description": "dx_desc", "Diagnosis code": "dx_code", "Body-system category (APR MDC)": "mdc_desc"}
    options = {label: col for label, col in options.items() if col in f.columns}
    with card("dx"):
        if not options or "los" not in f.columns:
            st.info("Diagnosis or length-of-stay columns were not found in this dataset.")
        else:
            c1, c2, c3, c4 = st.columns(4)
            basis_label = c1.selectbox("Group diagnoses by", list(options), key="dx_basis")
            rank_by = c2.selectbox("Rank by", ["Average length of stay", "Discharge count"], key="dx_rank")
            min_n = c3.slider("Minimum records per diagnosis", 1, 500, 20, key="dx_min")
            top_n = c4.slider("Number shown", 5, 25, 10, key="dx_top")
            table = diag_table(f, options[basis_label], min_n)
            title = f"Top {top_n} by {rank_by.lower()}: average length of stay"
            fig = fig_dx_bar(table, rank_by, top_n, title)
            if fig is None:
                st.warning("No diagnosis has enough records. Lower the minimum-records threshold or clear some filters.")
            plot(fig, "dx", "Groups with very few records can give misleading averages, so only groups above the threshold are shown. "
                            "Hover for the full name and record count.")
            if not table.empty:
                with st.expander("View the diagnosis table"):
                    shown = table.sort_values("AvgLOS", ascending=False)[["Full", "Discharges", "AvgLOS"]]
                    show_table(shown.rename(columns={"Full": basis_label, "AvgLOS": "Average stay (days)"}).round(2))

    section("Charges by age group and gender (research question 2)")
    with card("agecharge"):
        plot(fig_charges_age_gender(f), "agecharge", "Compares average billed charges across age groups, split by gender. "
                                                     "Charges depend on diagnosis, severity and length of stay, so differences are not explained by age or gender alone.")


def page_cost(f: pd.DataFrame) -> None:
    page_header("Cost Analysis", "How do charges, costs and length of stay vary with severity, age group and payment type?")
    st.info("**Total Charges** are the amounts hospitals bill. **Total Costs** are the estimated cost of providing the care. They are different measures "
            "and are never mixed on one axis. Relationships shown here are associations, not proof of cause and effect.")

    with card("costopts"):
        c1, c2, c3 = st.columns(3)
        hide = c1.checkbox("Hide extreme charges in the box plot and scatter plot", value=False, key="hide_extreme",
                           help="Only affects those two charts. The records stay in the dataset and in every other number.")
        percentile = c2.selectbox("Show charges up to the…", [95.0, 99.0, 99.9], index=1, format_func=lambda p: f"{p:g}th percentile", key="extreme_pct", disabled=not hide)
        log_scale = c3.checkbox("Logarithmic charges axis (box plot)", value=False, key="log_box")
        if "charges" in f.columns and f["charges"].notna().any():
            q1, q3 = f["charges"].quantile([0.25, 0.75])
            fence = q3 + 3 * (q3 - q1)
            n_ext = int((f["charges"] > fence).sum())
            st.caption(f"{n_ext:,} of {len(f):,} records ({n_ext / max(len(f), 1):.1%}) have charges above {fmt_money(fence)} (Q3 + 3×IQR). "
                       "They are kept in all totals and averages.")
    view = trim_extremes(f, "charges", percentile) if hide else f
    hidden = len(f) - len(view)

    def r_box():
        with card("box"):
            plot(fig_box(view, "charges", "Total charges by severity of illness", f"Total charges ({cur()})", log_scale), "box",
                 "Each box shows the middle 50% of charges; dots are unusually high or low values (random sample for speed)."
                 + (f" {hidden:,} extreme records are hidden from this chart only." if hide else ""))

    def r_avg():
        with card("avgsev"):
            plot(fig_by_severity(f, "charges", "Average", "Average total charges by severity", f"Average charges ({cur()})"), "avgsev",
                 "Average billed charge per record for each severity level (all records included).")

    def r_cost():
        with card("costsev"):
            plot(fig_by_severity(f, "costs", "Total", "Total costs by severity", f"Total costs ({cur()})"), "costsev",
                 "Sum of hospital costs per severity level. Hover to see record counts and average cost.")

    def r_losbox():
        with card("losbox"):
            plot(fig_box(f, "los", "Length of stay by severity of illness", "Length of stay (days)"), "losbox",
                 "Compares how long patients of each severity level stay (research question 3).")

    def r_scatter():
        with card("scatter"):
            d = view.dropna(subset=["los", "charges"]) if {"los", "charges"}.issubset(view.columns) else pd.DataFrame()
            note = "Each dot is one discharge. A pattern between stay and charges is an association, not proof that one causes the other."
            if len(d) > 2 and d["los"].nunique() > 1 and d["charges"].nunique() > 1:
                note += f" Pearson correlation in the data shown: {d['los'].corr(d['charges']):.2f}."
            plot(fig_scatter(view), "scatter", note)

    def r_age():
        with card("agecost"):
            plot(fig_age_cost(f), "agecost", "Average billed charges versus average estimated costs for each age group.")

    grid([r_box, r_avg, r_cost, r_losbox, r_scatter, r_age])

    section("Payment type (research question 5)")
    min_pay = st.slider("Minimum records per payment type (bar chart)", 1, 1000, 10, key="min_pay")

    def r_pay_donut():
        with card("paydonut"):
            plot(fig_donut(f, "pay1", "Discharge records by primary payment type", top=8), "paydonut",
                 "Uses Payment Typology 1 only, so no record is counted twice. Small categories are grouped as “Other”.")

    def r_pay_bar():
        with card("paybar"):
            plot(fig_pay_charges(f, min_pay), "paybar", "Average billed charges per record for each primary payer. Payer mix, diagnoses and severity all influence these averages.")

    grid([r_pay_donut, r_pay_bar])


def page_hospital(f: pd.DataFrame) -> None:
    page_header("Hospital Analysis", "Which hospitals and counties handle the most discharges, and how long do patients stay?")
    st.info("These figures describe activity, not quality. Length of stay and cost depend on case mix, severity and hospital specialisation, "
            "so hospitals should not be ranked as better or worse using these numbers alone.")
    if "facility" not in f.columns:
        st.warning("A facility-name column was not found, so hospital analysis is unavailable.")
        return

    query = st.text_input("Search hospital name", key="hosp_search", placeholder="Type part of a hospital name…")
    h = f
    if query.strip():
        matches = [c for c in f["facility"].cat.categories if query.strip().lower() in str(c).lower()]
        h = f[f["facility"].isin(matches)]
    if h.empty:
        st.warning("No hospitals match this search with the current filters.")
        return
    unknown = int((h["facility"] == "Unknown").sum())
    if unknown:
        st.caption(f"{unknown:,} records have no facility name; they are left out of hospital rankings and the heatmap.")
    named = h[h["facility"] != "Unknown"]

    with card("heat"):
        heat_options = {LABELS[c]: c for c in ["county", "severity", "admission_type", "age_group"] if c in h.columns}
        c1, c2, c3, c4 = st.columns(4)
        dim_label = c1.selectbox("Compare facilities across", list(heat_options), key="heat_dim")
        n_fac = c2.slider("Facilities shown", 5, 30, 15, key="heat_fac")
        n_col = c3.slider("Columns shown", 3, 15, 8, key="heat_cols")
        min_cell = c4.slider("Minimum records per cell", 1, 50, 5, key="heat_min")
        plot(fig_heatmap(named, heat_options.get(dim_label, "county"), n_fac, n_col, min_cell), "heat",
             "Each cell is the MEAN length of stay for that facility and group; blank cells have too few records. "
             "A facility normally sits in one county, so the county view is sparse - try severity or age group to compare facilities.")

    min_county = st.slider("Minimum discharges per county (county chart)", 1, 1000, 30, key="county_min")

    def r_top():
        with card("top10"):
            plot(fig_counts(named, "facility", "Top 10 hospitals by discharge volume", horizontal=True, top=10, height=380), "top10",
                 "Busiest facilities by number of discharge records (volume, not performance).")

    def r_county():
        with card("countylos"):
            plot(fig_county_los(h, min_county), "countylos", "Counties with the longest average stay (research question 4). Counties with few records are hidden.")

    grid([r_top, r_county])

    section("Hospital summary table")
    table = hospital_table(h)
    with card("table"):
        if table.empty:
            st.info("The table needs facility and county columns.")
        else:
            show_table(table.head(500), height=380)
            st.caption(f"Showing the {min(len(table), 500):,} busiest of {len(table):,} hospital-county combinations.")

    with st.expander("Diagnosis-level comparison for one facility"):
        facilities = top_values(named, "facility", 50)
        if facilities and "los" in named.columns:
            chosen = st.selectbox("Facility (50 busiest shown)", facilities, key="dx_facility")
            basis = "dx_desc" if "dx_desc" in named.columns else "dx_code" if "dx_code" in named.columns else None
            sub = named[named["facility"] == chosen]
            plot(fig_dx_bar(diag_table(sub, basis, 1), "Discharge count", 10, "Most common diagnoses at this facility (average stay shown)") if basis else None,
                 "dx_facility", "Bars show the average length of stay for the facility's 10 most common diagnoses.")
        else:
            st.info("Facility and length-of-stay columns are needed for this comparison.")


def page_quality(df: pd.DataFrame, report: dict) -> None:
    page_header("Data Quality", "How the dataset was cleaned and what to keep in mind when reading the charts.")
    kpi_cards([("🧾", "Rows (cleaned)", f"{len(df):,}"), ("🧱", "Columns (used)", f"{df.shape[1]}"),
               ("❓", "Missing values", f"{report['missing_cells']:,}"), ("♊", "Duplicate rows", f"{report['duplicates']:,}"),
               ("⚠️", "Invalid length of stay", f"{report['invalid_los']:,}")])
    st.write("")
    st.caption(f"Original file: {report['raw_rows']:,} rows × {report['raw_cols']} columns. Missing cells are counted before blanks are labelled “Unknown”.")

    for note in report["notes"]:
        st.info(note)
    if report["extreme_charges"]:
        st.info(f"{report['extreme_charges']:,} records have extreme charges (above {fmt_money(report['extreme_fence'])}, Q3 + 3×IQR). "
                "They are real discharges, so they were kept. Use the Cost Analysis option to hide them from charts only.")
    if report["negative_money"]:
        st.warning(f"{report['negative_money']:,} negative charge/cost values were found and kept. Check your dataset documentation.")
    if report["absent_cols"]:
        st.warning("Expected columns not found (related charts or filters are skipped): " + ", ".join(report["absent_cols"]))
    if report["unmapped_cols"]:
        with st.expander(f"{len(report['unmapped_cols'])} columns in the file were not recognised and were ignored"):
            st.write(", ".join(report["unmapped_cols"]))

    tab1, tab2, tab3 = st.tabs(["Columns and types", "Numeric summary", "Cleaned data preview"])
    with tab1:
        rows = []
        for col in df.columns:
            unique = len(df[col].cat.categories) if isinstance(df[col].dtype, pd.CategoricalDtype) else df[col].nunique()
            missing = int(report["missing_by_col"].get(col, 0))
            rows.append({"Column": LABELS.get(col, col), "Data type": str(df[col].dtype), "Missing values": missing,
                         "% missing": round(100 * missing / max(report["raw_rows"], 1), 2), "Unique values": unique})
        show_table(pd.DataFrame(rows))
    with tab2:
        numeric = df[[c for c in ["los", "charges", "costs", "birth_weight"] if c in df.columns]]
        if numeric.empty:
            st.info("No numeric columns found.")
        else:
            show_table(numeric.describe().T.round(2).rename(index=LABELS).reset_index().rename(columns={"index": "Column"}))
    with tab3:
        preview = df.drop(columns=[c for c in HIDDEN_COLUMNS if c in df.columns]).head(100).rename(columns=LABELS)
        show_table(preview)
        st.caption("Identifier-style columns (facility IDs, certificate numbers, ZIP prefix) are hidden. The data is de-identified; no personal identifiers are shown.")
    download_block(df, "Download cleaned dataset (CSV)", "cleaned_discharges.csv", "quality")


# ---------------------------------------------------------------------------
# 7. STYLING & MAIN
# ---------------------------------------------------------------------------
CSS = f"""
<style>
.stApp {{ background: {BG}; color: {TEXT}; }}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 1.6rem; padding-bottom: 2.5rem; max-width: 1500px; }}
.page-title {{ font-size: 1.65rem; font-weight: 700; color: {DARK}; margin: 0; line-height: 1.25; }}
.page-sub {{ font-size: .95rem; color: {MUTED}; margin: .15rem 0 1.1rem 0; }}
.section-title {{ font-size: 1.1rem; font-weight: 700; color: {DARK}; margin: 1.3rem 0 .6rem 0; }}
.kpi {{ background: {CARD}; border-radius: 14px; padding: 14px 16px; display: flex; gap: 12px; align-items: center;
        box-shadow: 0 2px 10px rgba(81,79,145,.10); min-height: 76px; }}
.kpi-icon {{ width: 40px; height: 40px; border-radius: 10px; background: #EDEBFA; display: flex; align-items: center; justify-content: center; font-size: 20px; flex: none; }}
.kpi-label {{ font-size: .78rem; color: {MUTED}; font-weight: 600; }}
.kpi-value {{ font-size: 1.4rem; font-weight: 700; color: {TEXT}; line-height: 1.2; }}
div[class*="st-key-card_"] {{ background: {CARD}; border-radius: 14px; padding: 14px 18px 8px 18px; box-shadow: 0 2px 10px rgba(81,79,145,.10); margin-bottom: .6rem; }}
section[data-testid="stSidebar"] {{ background: {PRIMARY}; }}
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p,
section[data-testid="stSidebar"] .stCaption, section[data-testid="stSidebar"] summary p,
section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {{ color: #FFFFFF !important; }}
section[data-testid="stSidebar"] h3 {{ font-size: 1.05rem; margin-top: .6rem; }}
.brand {{ display: flex; align-items: center; gap: 10px; margin: .2rem 0 1rem 0; }}
.brand-logo {{ width: 40px; height: 40px; border-radius: 12px; background: #FFFFFF; color: {PRIMARY}; display: flex; align-items: center; justify-content: center; font-size: 22px; font-weight: 800; }}
.brand-name {{ color: #FFFFFF; font-weight: 700; font-size: 1.05rem; line-height: 1.2; }}
section[data-testid="stSidebar"] div[role="radiogroup"] label {{ padding: 8px 12px; border-radius: 10px; width: 100%; }}
section[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {{ display: none; }}
section[data-testid="stSidebar"] div[role="radiogroup"] label p {{ color: #FFFFFF !important; font-weight: 600; }}
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{ background: rgba(255,255,255,.22); }}
section[data-testid="stSidebar"] .stButton button {{ background: #FFFFFF; color: {DARK}; border: none; border-radius: 10px; font-weight: 600; }}
section[data-testid="stSidebar"] [data-baseweb="tag"] {{ background: #EDEBFA !important; }}
section[data-testid="stSidebar"] [data-baseweb="tag"] span {{ color: {DARK} !important; }}
section[data-testid="stSidebar"] details {{ background: rgba(255,255,255,.12); border: none; border-radius: 10px; }}
.stDownloadButton button {{ background: {PRIMARY}; color: #FFFFFF; border: none; border-radius: 10px; }}
.stDownloadButton button:hover {{ background: {DARK}; color: #FFFFFF; }}
</style>
"""

BRAND = '<div class="brand"><div class="brand-logo">✚</div><div class="brand-name">MediScope<br>Health Analytics</div></div>'


def welcome_screen() -> None:
    page_header("Hospital Inpatient Discharges Dashboard", "Interactive insights into patient demographics, hospital utilisation, and healthcare expenditure.")
    with card("welcome"):
        st.markdown("#### Welcome - let's load a dataset")
        st.markdown("No dataset was found yet. You have two options:\n\n"
                    "1. **Upload a file** - open *Dataset & options* in the sidebar and upload a CSV or Excel file of hospital inpatient discharges.\n"
                    "2. **Add a default file** - save your data as `hospital_discharges.csv` in the same folder as `app.py`, then refresh.\n\n"
                    "The dashboard only shows numbers calculated from your own data. Nothing is made up.")


def main() -> None:
    st.markdown(CSS, unsafe_allow_html=True)
    sb = st.sidebar
    sb.markdown(BRAND, unsafe_allow_html=True)
    nav_box, filter_box, data_box = sb.container(), sb.container(), sb.container()  # fixes the visual order

    with nav_box:
        page = st.radio("Navigate", PAGES, key="page", label_visibility="collapsed", format_func=lambda p: f"{PAGE_ICONS[p]}  {p}")

    # --- dataset: upload, default file, or friendly message -------------------------------------------
    default_path = next((p for p in DEFAULT_FILES if p.exists()), None)
    with data_box:
        with st.expander("Dataset & options", expanded=default_path is None):
            uploaded = st.file_uploader("Upload CSV or Excel", type=["csv", "xlsx", "xls"], key="upload")
            st.text_input("Currency symbol", value="$", max_chars=4, key="currency",
                          help="Only changes the symbol shown. Check your dataset documentation for the real currency.")
            drop_dupes = st.checkbox("Remove exact duplicate rows", value=False, key="drop_dupes",
                                     help="Off by default: identical rows can be different patients in de-identified data.")
        st.caption("MediScope is a data analytics tool, not a clinical diagnosis tool.")

    if uploaded is not None:
        source, file_bytes, stamp = uploaded.name, uploaded.getvalue(), 0.0
    elif default_path is not None:
        source, file_bytes, stamp = str(default_path), b"", default_path.stat().st_mtime
    else:
        welcome_screen()
        st.stop()

    try:
        df, report = load_and_clean(source, file_bytes, stamp, drop_dupes)
    except Exception as error:  # show a readable message instead of a stack trace
        st.error(f"The file could not be read: {error}. Please upload a valid CSV or Excel file.")
        st.stop()
    if df.empty or df.shape[1] == 0:
        st.error("None of the expected columns were recognised in this file. Check the column headings (see README).")
        st.stop()

    signature = f"{source}|{stamp}|{len(file_bytes)}|{drop_dupes}"
    if st.session_state.get("_dataset_signature") != signature:  # new dataset -> reset filters
        clear_filters()
        st.session_state["_dataset_signature"] = signature

    with filter_box:
        render_filters(df)
    filtered = apply_filters(df)

    if page == "Data Quality":
        page_quality(df, report)
    elif filtered.empty:
        page_header(page, "No records match the current filters.")
        st.warning("No discharge records match the selected filters. Use “Clear Filters” in the sidebar or widen your selection.")
    elif page == "Summary":
        page_summary(filtered, len(df))
    elif page == "Patient Analysis":
        page_patient(filtered)
    elif page == "Cost Analysis":
        page_cost(filtered)
    else:
        page_hospital(filtered)


main()
