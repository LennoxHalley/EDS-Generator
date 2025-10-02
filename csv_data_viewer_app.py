import streamlit as st
import pandas as pd
import re
from fpdf import FPDF
from io import BytesIO
from PIL import Image
from datetime import datetime

st.set_page_config(page_title="CSV Data Viewer", layout="centered")
st.title("📊 Clean CSV Data Viewer")
st.write("Upload your classification CSV file to view and filter its contents interactively.")

# Upload CSV file
uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

# Use pre-converted PNG logo (adjust path if needed)
logo_png_path = "NOV_Logo_RGB_Full_Color.png"

if uploaded_file:
    st.sidebar.header("Settings")
    use_header = st.sidebar.checkbox("First row contains headers", value=False)

    try:
        df = pd.read_csv(uploaded_file, header=0 if use_header else None)
        # Auto-generate column names if needed
        if df.shape[1] >= 3:
            df.columns = ["Name", "UOM", "Value"] + list(df.columns[3:])
        else:
            st.error("CSV must have at least three columns: Name, UOM, and Value.")
            st.stop()

        # Drop extra columns if present
        df = df[["Name", "UOM", "Value"]]

        # Clean up formatting
        def clean_value(val):
            if isinstance(val, str):
                return re.sub(r'^="|"$', '', val).strip()
            return val

        df = df.applymap(clean_value)
        df = df.dropna(subset=["Name"]).reset_index(drop=True)

        # Search bar
        search_term = st.sidebar.text_input("Search names")
        if search_term:
            df = df[df["Name"].str.contains(search_term, case=False, na=False)]

        # Checkbox filters
        st.sidebar.markdown("### Row Filters")
        select_all = st.sidebar.checkbox("Select All", value=True)

        selected_rows = []
        for i, row in df.iterrows():
            label = row["Name"]
            checked = st.sidebar.checkbox(label, value=select_all, key=f"row_{i}")
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

            # Generate PDF
            def generate_pdf(dataframe):
                pdf = FPDF()
                pdf.add_page()


                # Calculate center position for logo
                logo_width = 50  # Width of the logo in mm
                page_width = pdf.w  # Total width of the page
                center_x = (page_width - logo_width) / 2

		#Logo
                try:
                    pdf.image(logo_png_path, x=center_x, y=8, w=logo_width)
                except Exception as e:
                    st.warning(f"Could not render logo in PDF: {e}")
		#Date
                current_date = datetime.now().strftime("%B %d, %Y")
                pdf.set_font("Arial", size=10)
                pdf.cell(190, 10, txt=f"Print Date: {current_date}", ln=True, align='R')
		#Title
                pdf.set_font("Arial", 'B', 16)
                pdf.ln(10)
                pdf.cell(190, 10, txt="Engineering Data Sheet", ln=True, align='C')
                pdf.ln(10)
		#Table Header
                indent_x = 20
                pdf.set_x(indent_x)
                col_widths = [60, 100, 20]
		#Table body
                pdf.set_font("Arial", size=10)
                for index, row in dataframe.iterrows():
                    pdf.set_x(indent_x)
                    pdf.cell(col_widths[0], 10, str(row["Name"]), border=0)
                    pdf.cell(col_widths[1], 10, str(row["Value"]), border=0)
                    pdf.cell(col_widths[2], 10, str(row["UOM"]), border=0)
                    pdf.ln()

                return pdf.output(dest='S').encode('latin1')

            pdf_bytes = generate_pdf(filtered_df)

            st.download_button(
                label="📄 Download Filtered Data as PDF",
                data=pdf_bytes,
                file_name="classification.pdf",
                mime="application/pdf"
            )
        else:
            st.info("Use the checkboxes in the sidebar to select which data to display.")

    except Exception as e:
        st.error(f"Failed to read CSV file: {e}")
else:
    st.info("Awaiting CSV upload...")
