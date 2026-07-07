import streamlit as st
import pandas as pd
import re
from fpdf import FPDF
from datetime import datetime
from tempfile import NamedTemporaryFile
from pathlib import Path
from PIL import Image

st.set_page_config(page_title="CSV Data Viewer", layout="centered")
st.title("📊 Clean CSV Data Viewer")
st.write("Upload your classification CSV file to view and filter its contents interactively.")

uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
tool_image_file = st.file_uploader("Choose a tool image (optional)", type=["png", "jpg", "jpeg"])

logo_png_path = "NOV_Logo_RGB_Full_Color.png"


def clean_value(val):
    if pd.isna(val):
        return ""
    text = str(val).strip()
    if text.lower() == "nan":
        return ""
    return re.sub(r'^="|"$', "", text).strip()


def wrap_text(pdf, text, width):
    text = clean_value(text)
    if not text:
        return [""]

    words = text.split()
    lines = []
    current = ""

    for word in words:
        tentative = word if not current else f"{current} {word}"
        if pdf.get_string_width(tentative) <= width:
            current = tentative
        else:
            if current:
                lines.append(current)

            if pdf.get_string_width(word) <= width:
                current = word
            else:
                chunk = ""
                for ch in word:
                    test_chunk = chunk + ch
                    if pdf.get_string_width(test_chunk) <= width:
                        chunk = test_chunk
                    else:
                        if chunk:
                            lines.append(chunk)
                        chunk = ch
                current = chunk

    if current:
        lines.append(current)

    return lines if lines else [""]


def save_uploaded_image(uploaded_image):
    if uploaded_image is None:
        return None

    suffix = Path(uploaded_image.name).suffix.lower()
    if suffix not in [".png", ".jpg", ".jpeg"]:
        suffix = ".png"

    temp_file = NamedTemporaryFile(delete=False, suffix=suffix)
    temp_file.write(uploaded_image.getbuffer())
    temp_file.flush()
    temp_file.close()
    return temp_file.name


def draw_table_header(pdf, x0, col_widths):
    header_height = 8
    pdf.set_fill_color(235, 235, 235)
    pdf.set_font("Arial", "B", 9)
    pdf.set_x(x0)
    pdf.cell(col_widths[0], header_height, "Name", border=1, align="C", fill=True)
    pdf.cell(col_widths[1], header_height, "Value", border=1, align="C", fill=True)
    pdf.cell(col_widths[2], header_height, "UOM", border=1, align="C", fill=True)
    pdf.ln(header_height)


def fit_image_into_box(image_path, box_w, box_h):
    with Image.open(image_path) as img:
        img_w, img_h = img.size

    img_ratio = img_w / img_h
    box_ratio = box_w / box_h

    if img_ratio > box_ratio:
        draw_w = box_w
        draw_h = box_w / img_ratio
    else:
        draw_h = box_h
        draw_w = box_h * img_ratio

    return draw_w, draw_h


def draw_page_layout(pdf, tool_image_path=None):
    page_w = pdf.w
    page_h = pdf.h

    left_margin = 10
    right_margin = 10
    top_logo_y = 6
    title_y = 34
    table_top_y = 40
    bottom_margin = 10

    image_box_w = 45
    image_x = page_w - right_margin - image_box_w
    image_y = table_top_y
    image_box_h = page_h - image_y - bottom_margin

    # Logo in the centre
    logo_width = 50
    center_x = (page_w - logo_width) / 2
    try:
        pdf.image(logo_png_path, x=center_x, y=6, w=logo_width)
    except Exception:
        pass

    # Print date in upper-right
    current_date = datetime.now().strftime("%B %d, %Y")
    pdf.set_font("Arial", size=10)
    pdf.set_xy(0, 8)
    pdf.cell(page_w - right_margin, 8, txt=f"Print Date: {current_date}", ln=0, align="R")

    # Title
    pdf.set_font("Arial", "B", 16)
    pdf.set_y(title_y)
    pdf.cell(0, 8, txt="Technical Data Sheet", ln=True, align="C")

    # Full-height image panel on the right
    pdf.set_draw_color(0, 0, 0)
    pdf.rect(image_x, image_y, image_box_w, image_box_h)

    if tool_image_path:
        try:
            inner_pad = 2
            draw_w, draw_h = fit_image_into_box(
                tool_image_path,
                image_box_w - (2 * inner_pad),
                image_box_h - (2 * inner_pad),
            )
            img_x = image_x + (image_box_w - draw_w) / 2
            img_y = image_y + (image_box_h - draw_h) / 2
            pdf.image(tool_image_path, x=img_x, y=img_y, w=draw_w, h=draw_h)
        except Exception:
            pdf.set_font("Arial", "I", 9)
            pdf.set_xy(image_x + 3, image_y + 5)
            pdf.multi_cell(image_box_w - 6, 5, "Tool image here", align="C")
    else:
        pdf.set_font("Arial", "I", 9)
        pdf.set_xy(image_x + 3, image_y + 5)
        pdf.multi_cell(image_box_w - 6, 5, "Tool image here", align="C")

    return table_top_y, image_x


def generate_pdf(dataframe, tool_image_path=None):
    pdf = FPDF(unit="mm", format="A4")
    pdf.set_auto_page_break(False)
    pdf.set_margins(10, 10, 10)
    pdf.add_page()

    table_top_y, image_x = draw_page_layout(pdf, tool_image_path=tool_image_path)

    x0 = 10
    gap_to_image = 4
    table_right = image_x - gap_to_image
    table_width = table_right - x0

    # Wider Name column, narrower UOM column, like the example layout
    col_widths = [70, 55, table_width - 70 - 55]
    line_height = 5
    bottom_margin = 10
    page_break_limit = pdf.h - bottom_margin

    pdf.set_y(table_top_y)
    draw_table_header(pdf, x0, col_widths)

    pdf.set_font("Arial", size=9)

    for _, row in dataframe.iterrows():
        name = clean_value(row["Name"])
        value = clean_value(row["Value"])
        uom = clean_value(row["UOM"])

        name_lines = wrap_text(pdf, name, col_widths[0] - 2)
        value_lines = wrap_text(pdf, value, col_widths[1] - 2)
        uom_lines = wrap_text(pdf, uom, col_widths[2] - 2)

        row_height = max(len(name_lines), len(value_lines), len(uom_lines)) * line_height + 2
        if row_height < 8:
            row_height = 8

        if pdf.get_y() + row_height > page_break_limit:
            pdf.add_page()
            table_top_y, image_x = draw_page_layout(pdf, tool_image_path=tool_image_path)

            table_right = image_x - gap_to_image
            table_width = table_right - x0
            col_widths = [70, 55, table_width - 70 - 55]

            pdf.set_y(table_top_y)
            draw_table_header(pdf, x0, col_widths)
            pdf.set_font("Arial", size=9)

        y = pdf.get_y()
        x1 = x0
        x2 = x1 + col_widths[0]
        x3 = x2 + col_widths[1]

        pdf.rect(x1, y, col_widths[0], row_height)
        pdf.rect(x2, y, col_widths[1], row_height)
        pdf.rect(x3, y, col_widths[2], row_height)

        pdf.set_xy(x1 + 1, y + 1)
        pdf.multi_cell(col_widths[0] - 2, line_height, name, border=0)

        pdf.set_xy(x2 + 1, y + 1)
        pdf.multi_cell(col_widths[1] - 2, line_height, value, border=0,align="R")

        pdf.set_xy(x3 + 1, y + 1)
        pdf.multi_cell(col_widths[2] - 2, line_height, uom, border=0,align="C")

        pdf.set_y(y + row_height)

    return pdf.output(dest="S").encode("latin1")


if uploaded_file:
    try:
        tool_image_path = save_uploaded_image(tool_image_file)

        df = pd.read_csv(uploaded_file, header=0)
        df.columns = df.columns.str.strip()

        required_columns = ["Name", "Value", "UOM"]
        missing = [col for col in required_columns if col not in df.columns]

        if missing:
            st.error(f"CSV is missing required column(s): {', '.join(missing)}")
            st.stop()

        df = df[["Name", "Value", "UOM"]]

        for col in ["Name", "Value", "UOM"]:
            df[col] = df[col].map(clean_value)

        df = df.dropna(subset=["Name"]).reset_index(drop=True)

        search_term = st.sidebar.text_input("Search names")
        if search_term:
            df = df[df["Name"].astype(str).str.contains(search_term, case=False, na=False)].reset_index(drop=True)

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

            try:
                st.image(logo_png_path, width=150)
            except Exception as e:
                st.warning(f"Could not preview logo: {e}")

            try:
                pdf_bytes = generate_pdf(filtered_df, tool_image_path=tool_image_path)
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
