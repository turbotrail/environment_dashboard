import streamlit as st
import json

def get_seismic_risk_score(lat, lon):
    """
    Returns a simple risk category based on latitude.
    For demo purposes: 
      - 'High Risk' if latitude > 50,
      - 'Moderate Risk' if latitude < -50,
      - 'Low Risk' otherwise.
    """
    if lat > 50:
        return "High Risk"
    elif lat < -50:
        return "Moderate Risk"
    else:
        return "Low Risk"

def get_educational_tip(magnitude):
    """
    Returns earthquake safety tips based on magnitude.
    For demo purposes:
      - 'Drop, Cover, and Hold On' if magnitude >= 7,
      - 'Be Prepared' if magnitude >= 5,
      - 'Stay Alert' otherwise.
    """
    if magnitude >= 7:
        return "Drop, Cover, and Hold On"
    elif magnitude >= 5:
        return "Be Prepared"
    else:
        return "Stay Alert"

def calculate_impact_level(magnitude, depth):
    """
    Returns an estimated impact level based on magnitude and depth.
    For demo purposes:
      - 'Severe' if magnitude >= 7,
      - 'Moderate' if magnitude >= 5 and depth < 70,
      - 'Minor' otherwise.
    """
    if magnitude >= 7:
        return "Severe"
    elif magnitude >= 5 and depth < 70:
        return "Moderate"
    else:
        return "Minor"

import pandas as pd
import requests
import folium
from folium.plugins import MarkerCluster, HeatMap
from streamlit_folium import st_folium
from datetime import datetime, timedelta

# === App Config ===
st.set_page_config(page_title="🌍 Earthquake Tracker", layout="wide")
st.title("🌍 Real-Time Earthquake Tracker")

# === Sidebar Filters ===
st.sidebar.header("🔎 Filter Earthquakes")
min_mag = st.sidebar.slider("Minimum Magnitude", 0.0, 10.0, 4.5, 0.1)
max_mag = st.sidebar.slider("Maximum Magnitude", 0.0, 10.0, 10.0, 0.1)
min_depth = st.sidebar.slider("Minimum Depth (km)", 0, 700, 0, 10)
max_depth = st.sidebar.slider("Maximum Depth (km)", 0, 700, 700, 10)
days = st.sidebar.selectbox("Show Events From (Past Days)", [1, 3, 7, 14, 30], index=2)
show_volcanoes = st.sidebar.checkbox("🌋 Show Volcanoes", value=True)
uploaded_geojson = st.sidebar.file_uploader("Upload Volcano GeoJSON", type="geojson")

# === Fetch Earthquake Data from USGS ===
end_time = datetime.utcnow()
start_time = end_time - timedelta(days=days)
url = (
    "https://earthquake.usgs.gov/fdsnws/event/1/query?"
    f"format=geojson&starttime={start_time.date()}&endtime={end_time.date()}"
    f"&minmagnitude={min_mag}&maxmagnitude={max_mag}"
    f"&mindepth={min_depth}&maxdepth={max_depth}"
)

response = requests.get(url)
data = response.json()

if "features" in data:
    earthquakes = pd.json_normalize(data["features"])
    earthquakes["time"] = pd.to_datetime(earthquakes["properties.time"], unit='ms')
    earthquakes = earthquakes.rename(columns={
        "properties.place": "place",
        "properties.mag": "magnitude",
        "geometry.coordinates": "coordinates"
    })
    earthquakes["longitude"] = earthquakes["coordinates"].apply(lambda x: x[0])
    earthquakes["latitude"] = earthquakes["coordinates"].apply(lambda x: x[1])
    earthquakes["depth"] = earthquakes["coordinates"].apply(lambda x: x[2])

    # Add new columns for seismic risk score and safety tip
    earthquakes["risk_score"] = earthquakes.apply(lambda row: get_seismic_risk_score(row['latitude'], row['longitude']), axis=1)
    earthquakes["safety_tip"] = earthquakes["magnitude"].apply(get_educational_tip)

    # === 📆 Disaster Alert Timeline ===
    earthquakes.set_index("time", inplace=True)
    daily_counts = earthquakes.resample('D').size()
    earthquakes.reset_index(inplace=True)
    st.markdown("### 📆 Disaster Alert Timeline")
    st.bar_chart(daily_counts)

    # === 🚨 Estimated Impact Level ===
    earthquakes["impact_level"] = earthquakes.apply(lambda row: calculate_impact_level(row['magnitude'], row['depth']), axis=1)

    st.markdown(f"### 📊 {len(earthquakes)} Earthquakes Found")
    st.dataframe(earthquakes[["time", "place", "magnitude", "depth", "latitude", "longitude", "risk_score", "safety_tip", "impact_level"]])

    st.markdown("""
    ### 🌋 What is the Ring of Fire?
    The Ring of Fire is a horseshoe-shaped area in the Pacific Ocean known for its high seismic activity. 
    It includes about 75% of the world's active and dormant volcanoes and is the site of frequent earthquakes and volcanic eruptions. 
    This region is formed by the movement of several tectonic plates.
    """)
    
    # === Earthquake Map with Clustering ===
    st.markdown("### 🗺️ Earthquake Cluster Map")

    m = folium.Map(
        location=[10, -150],
        zoom_start=3,
        tiles="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        attr="© OpenStreetMap contributors",
        world_copy_jump=True
    )
    
    # Outline the Ring of Fire using tectonic boundaries along the eastern Pacific rim
    ring_of_fire_segments = [
        [[-55, -70], [-40, -70], [-20, -70], [0, -80], [10, -85], [30, -120], [45, -130], [60, -150], [60, -170]],
        [[55, 170], [40, 140], [0, 110], [-40, 175]]
    ]
    for segment in ring_of_fire_segments:
        folium.PolyLine(segment, color="red", weight=3, tooltip="Ring of Fire").add_to(m)

    marker_cluster = MarkerCluster().add_to(m)

    for _, row in earthquakes.iterrows():
        popup_text = f"""
            <b>{row['place']}</b><br>
            Magnitude: {row['magnitude']}<br>
            Depth: {row['depth']} km<br>
            Time: {row['time']}<br>
            Educational Tip: {row['safety_tip']}<br>
            Regional Seismic Risk: {row['risk_score']}
        """
        color = "red" if row['magnitude'] >= 6 else "orange" if row['magnitude'] >= 5 else "blue"

        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=row["magnitude"] * 1.5,
            color=color,
            fill=True,
            fill_opacity=0.8,
            popup=folium.Popup(popup_text, max_width=300)
        ).add_to(marker_cluster)

    # === Volcano Markers ===
    if show_volcanoes and uploaded_geojson is not None:
        try:
            volcano_data = json.load(uploaded_geojson)
            for feature in volcano_data["features"]:
                coords = feature["geometry"]["coordinates"]
                props = feature["properties"]
                name = props.get("name") or props.get("Volcano_Name", "Unknown")
                country = props.get("country", props.get("Country", "N/A"))
                elev = props.get("elevation", props.get("Elevation", "N/A"))
                eruption = props.get("last_eruption", props.get("Last_Eruption_Year", "Unknown"))
                popup = f"<b>{name}</b><br>Country: {country}<br>Elevation: {elev} m<br>Last Eruption: {eruption}"
                folium.Marker(
                    location=[coords[1], coords[0]],
                    icon=folium.Icon(color="red", icon="fire", prefix="fa"),
                    popup=popup
                ).add_to(m)
        except Exception as e:
            st.error(f"Failed to load uploaded volcano data: {e}")

    # === Community Safety Heatmap ===
    heat_data = [[row["latitude"], row["longitude"]] for _, row in earthquakes.iterrows()]
    HeatMap(heat_data).add_to(m)

    st_folium(m, width=1000, height=600)

else:
    st.error("❌ Failed to retrieve earthquake data from USGS.")