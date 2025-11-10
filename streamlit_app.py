import streamlit as st
import pandas as pd
import geopandas as gpd
from shapely.geometry import shape
import json
import base64
import requests
from io import BytesIO

# --------------------------
# GitHub Upload Function
# --------------------------


def login():
    """Simple password login stored in Streamlit secrets."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("🔐 Login Required")

        password = st.text_input("Enter password", type="password")
        if st.button("Login"):
            if password == st.secrets["APP_PASSWORD"]:
                st.session_state.authenticated = True
                st.success("✅ Login successful")
            else:
                st.error("❌ Incorrect password")
        st.stop()  # Prevent rest of app from running


def upload_to_github(file_bytes, filename):
    """Uploads GeoJSON file to a GitHub repository using REST API."""
    token = st.secrets["GITHUB_TOKEN"]
    username = st.secrets["GITHUB_USERNAME"]
    repo = st.secrets["GITHUB_REPO"]
    branch = st.secrets.get("GITHUB_BRANCH", "main")

    # Build GitHub API endpoint
    url = f"https://api.github.com/repos/{username}/{repo}/contents/{filename}"

    # Get SHA if file exists (needed for overwrite)
    headers = {"Authorization": f"token {token}"}
    get_resp = requests.get(url, headers=headers, params={"ref": branch})
    sha = get_resp.json().get("sha") if get_resp.status_code == 200 else None

    # Prepare upload payload
    message = "Update GeoJSON via Streamlit app"
    content = base64.b64encode(file_bytes).decode("utf-8")
    data = {"message": message, "content": content, "branch": branch}
    if sha:
        data["sha"] = sha

    # Send PUT request to GitHub API
    resp = requests.put(url, headers=headers, data=json.dumps(data))

    if resp.status_code in [200, 201]:
        st.success("✅ File uploaded to GitHub successfully!")
        cdn_url = f"https://cdn.jsdelivr.net/gh/{username}/{repo}/{filename}"
        st.markdown(f"**Public CDN URL:** [📎 {cdn_url}]({cdn_url})")
    else:
        st.error(f"❌ GitHub upload failed: {resp.status_code} - {resp.text}")


# --------------------------
# Excel → GeoJSON Conversion
# --------------------------

def convert_to_geojson(uploaded_file):
    df = pd.read_excel(uploaded_file)
    if "geometry" not in df.columns:
        st.error("Excel must contain a 'geometry' column in WKT format.")
        return None

    df["geometry"] = gpd.GeoSeries.from_wkt(df["geometry"])
    gdf = gpd.GeoDataFrame(df, geometry="geometry")

    geojson_bytes = gdf.to_json().encode("utf-8")
    return geojson_bytes

# --------------------------
# Streamlit UI
# --------------------------

login()
st.title("🗺️ Excel → GeoJSON → GitHub CDN")

uploaded_file = st.file_uploader("Upload Excel File", type=["xlsx"])
if uploaded_file:
    geojson_bytes = convert_to_geojson(uploaded_file)
    if geojson_bytes:
        filename = st.text_input("GitHub Filename (e.g. data/converted.geojson)", "converted.geojson")
        if st.button("🚀 Upload to GitHub"):
            upload_to_github(geojson_bytes, filename)
