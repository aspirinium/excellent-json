import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape
import json
from io import BytesIO

# ----------------------------
# Helper Functions
# ----------------------------

def replace_commas_with_dots_excel(data):
    for column in data.columns:
        if data[column].dtype in ['float64', 'int64']:
            data[column] = data[column].apply(lambda x: str(x).replace(',', '.') if isinstance(x, str) else x)
    return data

def replace_commas_with_dots(geo_data, numeric_columns):
    for column in numeric_columns:
        if column in geo_data.columns:
            geo_data[column] = geo_data[column].astype(str).replace({',': '.'}, regex=True)
    return geo_data

# ----------------------------
# Excel → GeoJSON Conversion
# ----------------------------

def convert_to_geojson(uploaded_file):
    excel_data = pd.read_excel(uploaded_file)
    numeric_columns = ['GesamthoeheM', "KEV-Liste", "Rotordurchmesser", 'TotalTurbinen', "MW", "GWhA"]
    
    for column in numeric_columns:
        if column in excel_data.columns:
            excel_data[column] = pd.to_numeric(excel_data[column], errors='coerce')

    if "Kanton" in excel_data.columns:
        excel_data["Kanton"] = excel_data["Kanton"].fillna("").apply(
            lambda x: [k.strip() for k in x.split(",")] if isinstance(x, str) and x.strip() else []
        )

    excel_data = replace_commas_with_dots_excel(excel_data)
    excel_data = excel_data.fillna("")

    # Convert WKT to geometry if available
    if "geometry" in excel_data.columns:
        excel_data["geometry"] = gpd.GeoSeries.from_wkt(excel_data["geometry"])
        geo_data = gpd.GeoDataFrame(excel_data, geometry=excel_data["geometry"])
    else:
        st.warning("No 'geometry' column found in Excel file.")
        return None

    geojson_bytes = geo_data.to_json().encode('utf-8')
    return geojson_bytes

# ----------------------------
# GeoJSON → Excel Conversion
# ----------------------------

def convert_geojson_to_excel(uploaded_file):
    raw = json.load(uploaded_file)
    records = []
    for feature in raw["features"]:
        props = feature["properties"]
        geometry = shape(feature["geometry"])
        props["geometry"] = geometry
        records.append(props)

    geo_data = gpd.GeoDataFrame(records, geometry="geometry")

    def join_kanton(val):
        if isinstance(val, list):
            return ", ".join(val)
        elif val is None:
            return ""
        return str(val)

    if "Kanton" in geo_data.columns:
        geo_data["Kanton"] = geo_data["Kanton"].apply(join_kanton)

    numeric_columns = ['GesamthoeheM', "KEV-Liste", "Rotordurchmesser", 'TotalTurbinen', "MW", "GWhA"]
    geo_data = replace_commas_with_dots(geo_data, numeric_columns)

    geo_data['lat'] = geo_data['geometry'].apply(lambda x: x.y if x else None)
    geo_data['lon'] = geo_data['geometry'].apply(lambda x: x.x if x else None)

    for column in numeric_columns:
        if column in geo_data.columns:
            geo_data[column] = pd.to_numeric(geo_data[column], errors='coerce')

    output = BytesIO()
    geo_data.to_excel(output, index=False)
    output.seek(0)
    return output

# ----------------------------
# Streamlit UI
# ----------------------------

st.set_page_config(page_title="Excel ↔ GeoJSON Converter", page_icon="🗺️", layout="centered")
st.title("🗺️ Excel ↔ GeoJSON Converter")
st.write("Upload your Excel or GeoJSON file to convert between formats.")

tab1, tab2 = st.tabs(["📄 Excel → GeoJSON", "🌍 GeoJSON → Excel"])

# --- Excel to GeoJSON ---
with tab1:
    excel_file = st.file_uploader("Upload Excel File (.xlsx)", type=["xlsx"])
    if excel_file:
        geojson_bytes = convert_to_geojson(excel_file)
        if geojson_bytes:
            st.success("✅ Successfully converted to GeoJSON!")
            st.download_button(
                label="⬇️ Download GeoJSON",
                data=geojson_bytes,
                file_name="converted.geojson",
                mime="application/geo+json"
            )

# --- GeoJSON to Excel ---
with tab2:
    geojson_file = st.file_uploader("Upload GeoJSON File (.json, .geojson)", type=["json", "geojson"])
    if geojson_file:
        excel_output = convert_geojson_to_excel(geojson_file)
        if excel_output:
            st.success("✅ Successfully converted to Excel!")
            st.download_button(
                label="⬇️ Download Excel File",
                data=excel_output,
                file_name="converted.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

st.markdown("---")
st.caption("Built with ❤️ using Streamlit and GeoPandas")
