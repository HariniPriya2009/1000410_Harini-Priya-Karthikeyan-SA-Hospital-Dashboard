# 1000410_Harini-Priya-Karthikeyan-SA-Hospital-Dashboard

#  MediScope Health Analytics
## Hospital Inpatient Discharges Dashboard

 **Live Dashboard:** [Open MediScope Dashboard](https://1000410-harini-priya-karthikeyan-sa-hospital-dashboard.streamlit.app/)

**Canva Link:**[Open Storyboard and Screenshots]( https://canva.link/ndi6y8w7yabsjy2)
##  Project Overview

MediScope Health Analytics is an interactive healthcare data analytics dashboard developed using Python and Streamlit.

The project analyses hospital inpatient discharge records to identify patterns in patient demographics, hospital admissions, length of stay, diagnosis categories, hospital charges, healthcare costs, and hospital utilisation.

The dashboard helps hospital administrators and healthcare professionals explore data through interactive visualisations and make informed, data-driven operational decisions.

##  Project Objectives

- Analyse hospital inpatient discharge trends.
- Understand patient demographics and diagnosis patterns.
- Examine the relationship between illness severity and hospital charges.
- Identify hospitals and counties with longer average patient stays.
- Explore payment methods and healthcare expenditure.
- Present healthcare data through an interactive dashboard.

##  Key Features

### 1. Summary Dashboard
- Total discharge records.
- Average length of hospital stay.
- Total hospital charges.
- Total hospital costs.
- Discharge distribution by admission type.
- Gender distribution.
- Length-of-stay distribution.

### 2. Patient Analysis
- Patient distribution by age group.
- Gender and race distribution.
- Diagnosis-wise average length of stay.
- Hospital charges by age group and gender.
- Top diagnoses based on discharge records.

### 3. Cost Analysis
- Hospital charges by severity of illness.
- Average charges by severity level.
- Total hospital costs by severity.
- Length of stay versus hospital charges.
- Charges and costs by age group.
- Payment type distribution.
- Average charges by primary payment type.

### 4. Hospital Analysis
- Interactive hospital and county heatmap.
- Top 10 hospitals by discharge volume.
- Average length of stay by county.
- Hospital summary table.
- Facility-wise diagnosis comparison.

### 5. Data Quality
- Dataset dimensions and column information.
- Missing-value analysis.
- Duplicate record identification.
- Invalid length-of-stay detection.
- Numeric summary statistics.
- Cleaned dataset preview.
- Download cleaned dataset.

## 🔍 Research Questions

The dashboard is designed to investigate five key questions:

1. Which diagnoses are associated with the longest average hospital stays?
2. How do hospital charges vary across different age groups and genders?
3. How does the severity of illness relate to hospital charges and length of stay?
4. Which hospitals and counties have the longest average patient stays?
5. How do different payment types vary in discharge volume and hospital charges?

## Project Structure

```text
MediScope-Health-Analytics/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
│
├── hospital_discharges.csv
│
└── screenshots/
    ├── summary.png
    ├── patient_analysis.png
    ├── cost_analysis.png
    ├── hospital_analysis.png
    └── data_quality.png
```

*Note: The dataset can be uploaded directly through the dashboard also.*

## Data Processing

The application performs the following preprocessing operations:

- Standardises dataset column names.
- Cleans categorical values.
- Converts hospital charges and costs into numeric values.
- Handles missing values.
- Identifies duplicate records.
- Detects invalid length-of-stay values.
- Standardises age groups and gender categories.
- Converts severity codes into readable categories where possible.
- Investigates extreme charge values without automatically deleting valid records.

The dashboard uses the uploaded hospital discharge dataset and calculates its metrics dynamically.


## Expected Outcomes

- Better understanding of inpatient discharge patterns.
- Identification of diagnoses associated with longer hospital stays.
- Improved visibility into hospital expenditure.
- Comparison of healthcare utilisation across facilities and counties.
- Data-driven insights to support hospital operational planning.

## Limitations

- The analysis depends on the quality and completeness of the uploaded dataset.
- Missing or unavailable columns may limit certain visualisations.
- The dataset contains discharge records; reliable readmission rates cannot be established without linked patient admission histories.
- The dashboard is intended for educational and analytical purposes and is not a clinical decision-making system.

## Project Information

**Student Name:** Harini Priya Karthikeyan

**CRS:** Artificial Intelligence

**Project:** Hospital Inpatient Discharges Dashboard

**Organisation:** MediScope Health Analytics

