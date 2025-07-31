import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import re
import glob
from math import pi
from fpdf import FPDF
from datetime import datetime
import os

def sanitize_filename(name):
    return re.sub(r'[^a-zA-Z0-9_\-]', '_', name)

st.set_page_config(page_title="Nuvira AuditTrack", layout="centered", initial_sidebar_state="auto")
st.markdown("""
    <style>
        .stApp { background-color: #121212; color: white; }
    </style>
""", unsafe_allow_html=True)

#st.markdown(f"<h1 style='color:#ffffff;'>🔐 Nuvira AuditTrack – {framework}</h1>", unsafe_allow_html=True)

# --- Client Metadata ---
client_name = st.text_input("Client Company Name")
auditor_name = st.text_input("Auditor Name")
contact_email = st.text_input("Contact Email")
audit_date = datetime.today().strftime('%Y-%m-%d')

# --- Map framework names to CSV files ---
framework_files = {
    "Essential Eight": "essential8.csv",
    "ISO/IEC 27001": "iso27001.csv",
    "ISO 27017 & 27018": "iso_27017_27018_controls.csv",
    "NIST Cybersecurity Framework": "nist_csf_controls.csv",
    "ACSC Cloud Security": "acsc_cloud_security_controls.csv",
    "IRAP/ISM": "irap_ism.csv",
    "PCI DSS": "pci_dss_controls.csv"
}

# --- Framework Selector ---
framework = st.selectbox(
    "Select Framework",
    options=list(framework_files.keys()),
    index=0
)

# --- Dynamic Title ---
st.markdown(f"<h1 style='color:#ffffff;'>🔐 Nuvira AuditTrack – {framework}</h1>", unsafe_allow_html=True)

# --- Load Selected Checklist ---
df = pd.read_csv(framework_files[framework])

responses = []

scoring_weights = {
    "Essential Eight": {"Yes": 1, "Partial": 0.5, "No": 0},
    "ISO/IEC 27001": {"Yes": 1, "Partial": 0.5, "No": 0},
    "ISO 27017 & 27018": {"Yes": 1, "Partial": 0.5, "No": 0},
    "NIST Cybersecurity Framework": {"Yes": 1, "Partial": 0.5, "No": 0},
    "ACSC Cloud Security": {"Yes": 1, "Partial": 0.5, "No": 0},
    "IRAP/ISM": {"Yes": 1, "Partial": 0.5, "No": 0},
    "PCI DSS": {"Yes": 1, "Partial": 0.5, "No": 0}
}
    
# --- Render Checklist ---
for index, row in df.iterrows():
    st.subheader(row["Control"])
    st.write(row["Description"])

    status = st.radio(f"Status for {row['Control']}", ["Yes", "Partial", "No"], key=index)
    notes = st.text_area("Notes:", key=f"notes_{index}")
    uploaded_files = st.file_uploader("Upload evidence (optional)", key=f"file_{index}", accept_multiple_files=True)
    
    # Create evidence directory
    evidence_dir = os.path.join("evidence", "client", framework.replace(" ", "_"), row["Control"].replace(" ", "_"))
    os.makedirs(evidence_dir, exist_ok=True)

    # Get existing evidence files from directory
    evidence_links = []
    if os.path.exists(evidence_dir):
        for file_name in os.listdir(evidence_dir):
            file_path = os.path.join(evidence_dir, file_name)
            if os.path.isfile(file_path):
                rel_path = os.path.relpath(file_path)
                evidence_links.append(rel_path.replace("\\", "/"))

    # Handle new file uploads
    if uploaded_files:
        for file in uploaded_files:
            save_path = os.path.join(evidence_dir, file.name)
            # Only save if file doesn't already exist to avoid duplicates
            if not os.path.exists(save_path):
                with open(save_path, "wb") as f:
                    f.write(file.getbuffer())
                rel_path = os.path.relpath(save_path)
                if rel_path.replace("\\", "/") not in evidence_links:
                    evidence_links.append(rel_path.replace("\\", "/"))

    recommendation = row.get("Recommendation", "").strip()

    # Show recommendation only if status is not fully compliant
    if status in ["No", "Partial"] and recommendation:
        st.markdown(f"**Recommendation:** {recommendation}", unsafe_allow_html=True)

    # Display uploaded evidence with delete functionality
    for i, ev in enumerate(evidence_links):
        ev_name = os.path.basename(ev)
        with st.expander(f"📎 {ev_name}"):
            # Create two columns for download and delete buttons
            col1, col2 = st.columns([3, 1])
            
            with col1:
                if os.path.exists(ev):
                    with open(ev, "rb") as f:
                        file_data = f.read()
                    st.download_button(
                        label=f"📥 Download {ev_name}",
                        data=file_data,
                        file_name=ev_name,
                        key=f"download_{index}_{i}"
                    )
            
            with col2:
                if st.button(f"🗑️ Delete", key=f"delete_{index}_{i}"):
                    try:
                        if os.path.exists(ev):
                            os.remove(ev)
                            st.success(f"{ev_name} deleted.")
                            st.rerun()  # force rerun after deletion
                        else:
                            st.warning(f"{ev_name} not found.")
                    except Exception as e:
                        st.error(f"Error deleting {ev_name}: {str(e)}")

    responses.append({
        "Control": row["Control"],
        "Status": status,
        "Notes": notes,
        "Recommendation": recommendation if status in ["No", "Partial"] else "",
        "Evidence": evidence_links
    })

# --- Scoring ---
total_controls = len(responses)
weights = scoring_weights[framework]
score = sum(weights[r["Status"]] for r in responses)
score_percentage = round((score / total_controls) * 100, 1)

st.subheader("📊 Audit Summary")
st.markdown(f"**Score:** {score} / {total_controls} ({score_percentage}%)")

# --- Pie Chart ---
status_counts = {"Yes": 0, "Partial": 0, "No": 0}
for r in responses:
    status_counts[r["Status"]] += 1
labels = []
sizes = []
colors = []
color_map = {"Yes": "#00C853", "Partial": "#FFD600", "No": "#D50000"}

for k, v in status_counts.items():
    if v > 0:
        labels.append(k)
        sizes.append(v)
        colors.append(color_map[k])

fig, ax = plt.subplots(facecolor='#121212')
wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors, textprops=dict(color='white'))
for text in texts: text.set_color('white')
for autotext in autotexts: autotext.set_color('white')
ax.axis('equal')
plt.title("Maturity Snapshot", color='white')
fig.patch.set_facecolor('#121212')
chart_path = "maturity_snapshot.png"
plt.savefig(chart_path, facecolor=fig.get_facecolor())
st.pyplot(fig)

st.subheader("🚧 Compliance Gaps")
for r in responses:
    if r["Status"] != "Yes":
        st.markdown(f"- **{r['Control']}**: {r['Status']} – {r['Notes']}")

# --- PDF Export ---
if st.button("📥 Export Report"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Nuvira Audit Report", ln=True, align='C')

    pdf.set_font("Arial", '', 12)
    pdf.ln(10)
    pdf.cell(0, 10, f"Framework: {framework}", ln=True)
    pdf.cell(0, 10, f"Date: {audit_date}", ln=True)
    pdf.cell(0, 10, f"Auditor: {auditor_name}", ln=True)
    pdf.cell(0, 10, f"Client: {client_name}", ln=True)
    pdf.cell(0, 10, f"Email: {contact_email}", ln=True)

    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Overall Score: {score} / {total_controls} ({score_percentage}%)", ln=True)

    pdf.image(chart_path, x=30, w=150)

    pdf.ln(10)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Control Breakdown:", ln=True)

    pdf.set_font("Arial", '', 11)
    for r in responses:
        pdf.cell(0, 10, f"{r['Control']} - {r['Status']}", ln=True)
        if r['Notes']:
            pdf.set_text_color(100, 100, 100)
            pdf.set_font("Arial", 'I', 10)
            pdf.multi_cell(0, 10, f"  Notes: {r['Notes']}")
            pdf.set_font("Arial", '', 11)
            pdf.set_text_color(0, 0, 0)
        if r["Evidence"] and r["Evidence"] != "None":
            pdf.set_text_color(0, 102, 204)
            pdf.set_font("Arial", 'I', 10)
            pdf.multi_cell(0, 10, f"  Evidence: {r['Evidence']}")

    filename = f"Nuvira_Audit_{framework.replace(' ', '_')}_{client_name.replace(' ', '_')}.pdf"
    pdf.output(filename)
    with open(filename, "rb") as f:
        st.download_button(label="Download PDF", data=f, file_name=filename, mime='application/pdf')