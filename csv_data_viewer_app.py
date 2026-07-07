import streamlit as st
import pandas as pd
import re
from fpdf import FPDF
from datetime import datetime

st.set_page_config(page_title="CSV Data Viewer", layout="centered")
st.title("📊 Clean CSV Data Viewer")
st.write("Upload your classification CSV file to view and filter its contents interactively.")

# Upload CSV file
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

# Logo file path
logo_png_path = "NOV_Logo_RGB_Full_Color.png"


def clean_value(val):
    """Remove Excel-style wrapping quotes like ="text" and trim whitespace."""
    if isinstance(val, str):
        return re.sub(r'^="|"$', '', val).strip()
    return val


def generate_pdf(dataframe):
    pdf = FPDF()
    pdf.add_page()

    # Logo
    logo_width = 50
    page_width = pdf.w
    center_x = (page_width - logo_width) / 2

    try:
        pdf.image(logo_png_path, x=center_x, y=8, w=logo_width)
    except Exception:
        pass

    # Date
    current_date = datetime.now().strftime("%B %d, %Y")
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 10, txt=f"Print Date: {current_date}", ln=True, align="R")

    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.ln(10)
    pdf.cell(190, 10, txt="Engineering Data Sheet", ln=True, align="C")
    pdf.ln(10)

    # Table layout
    indent_x = 20
    col_widths = [60, 100, 20]

    # Header row
    pdf.set_x(indent_x)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(col_widths[0], 10, "Name", border=0)
    pdf.cell(col_widths[1], 10, "Value", border=0)
    pdf.cell(col_widths[2], 10, "UOM", border=0)
    pdf.ln()

    # Body rows
    pdf.set_font("Arial", size=10)
    for _, row in dataframe.iterrows():
        pdf.set_x(indent_x)
        pdf.cell(col_widths[0], 10, str(row["Name"]), border=0)
        pdf.cell(col_widths[1], 10, str(row["Value"]), border=0)
        pdf.cell(col_widths[2], 10, str(row["UOM"]), border=0)
        pdf.ln()

    return pdf.output(dest="S").encode("latin1")


if uploaded_file:
    st.sidebar.header("Settings")
    use_header = st.sidebar.checkbox("First row contains headers", value=False)

    try:
        # Read CSV
        df = pd.read_csv(uploaded_file, header=0 if use_header else None)

        # Make sure there are at least 3 columns
        if df.shape[1] < 3:
            st.error("CSV must have at least three columns: Name, UOM, and Value.")
            st.stop()

        # Rename first 3 columns
        df.columns = ["Name", "UOM", "Value"] + list(df.columns[3:])

        # Keep only the columns we need
        df = df[["Name", "UOM", "Value"]]

        # Clean values
        for col in ["Name", "UOM", "Value"]:
            df[col] = df[col].map(clean_value)

        # Remove rows with no Name
        df = df.dropna(subset=["Name"]).reset_index(drop=True)

        # Search bar
        search_term = st.sidebar.text_input("Search names")
        if search_term:
            df = df[df["Name"].astype(str).str.contains(search_term, case=False, na=False)].reset_index(drop=True)

        # Row filter checkboxes
        st.sidebar.markdown("### Row Filters")

        if "select_all" not in st.session_state:
            st.session_state.select_all = True

        def set_all_rows():
            for i in range(len(df)):
                st.session_state[f"row_{i}"] = st.session_state.select_all

        st.sidebar.checkbox("Select All", key="select_all", on_change=set_all_rows)

        selected_rows = []
        for i, row in df.iterrows():
            key = f"row_{i}"
            if key not in st.session_state:
                st.session_state[key] = st.session_state.select_all

            checked = st.sidebar.checkbox(str(row["Name"]), key=key)
            if checked:
                selected_rows.append(i)

        if selected_rows:
            filtered_df = df.loc[selected_rows].reset_index(drop=True)

            st.subheader("Filtered Data Table")
            st.dataframe(filtered_df)

            # Preview logo in app
            try:
                st.image(logo_png_path, width=150)
            except Exception as e:
                st.warning(f"Could not preview logo: {e}")

            # PDF download
            try:
                pdf_bytes = generate_pdf(filtered_df)
                st.download_button(
                    label="📄 Download Filtered Data as PDF",
                    data=pdf_bytes,
                    file_name="classification.pdf",
                    mime="application/pdf",
                )
            except Exception as e:
                st.error(f"Failed to generate PDF: {e}")
        else:
            st.info("Use the checkboxes in the sidebar to select which data to display.")

    except Exception as e:
        st.error(f"Failed to read CSV file: {e}")
else:
    st.info("Awaiting CSV upload...")
