import streamlit as st
import geopandas as gpd
import pandas as pd
import numpy as np
import plotly.express as px
import folium
from streamlit_folium import st_folium
import branca.colormap as cm

st.set_page_config(page_title="Nigeria MRV Dashboard", layout="wide", page_icon="🇳🇬")

@st.cache_data
def load_admins():
    url = "https://geodata.ucdavis.edu/gadm/gadm4.1/json/gadm41_NGA_1.json"
    gdf = gpd.read_file(url)
    gdf = gdf[['NAME_1','geometry']].rename(columns={'NAME_1':'name'})
    gdf['id'] = range(1, len(gdf)+1)
    gdf['level'] = 'State'
    gdf['geometry'] = gdf['geometry'].simplify(0.05, preserve_topology=True)
    return gdf

def generate_dummy_data(): 
    np.random.seed(42)
    admins = load_admins()
    records = []
    indicators = ['NDVI','SOC','DesertificationRisk','Flooding','Rainfall']
    for year in [2024, 2025]:
        for _, row in admins.iterrows():
            for ind in indicators:
                if ind == 'NDVI': mean = np.random.uniform(0.2, 0.9)
                elif ind == 'SOC': mean = np.random.uniform(5, 60)
                else: mean = np.random.uniform(0, 100)
                records.append({
                    'admin_id': row['id'], 'name': row['name'],
                    'indicator': ind, 'year': year,
                    'mean': mean, 'std': mean*0.1, 'min': mean*0.8, 'max': mean*1.2,
                })
    return pd.DataFrame(records)

admins = load_admins()
indicators = generate_dummy_data()

st.sidebar.title("🇳🇬 Nigeria MRV System - DEMO")
year = st.sidebar.selectbox("Year", sorted(indicators['year'].unique()))
indicator = st.sidebar.selectbox("Indicator", indicators['indicator'].unique())
admin_filter = st.sidebar.multiselect("Filter by State", admins['name'].tolist())

filtered_admins = admins[admins['name'].isin(admin_filter)] if admin_filter else admins
filtered_ind = indicators[(indicators['year']==year) & (indicators['indicator']==indicator)]
merged = filtered_admins.merge(filtered_ind, left_on='id', right_on='admin_id')

st.title(f"Nigeria MRV Dashboard: {indicator} {year}")
st.info("Demo mode with synthetic data. Replace with GEE exports later.")

# THIS LINE MUST BE HERE
merged = filtered_admins.merge(filtered_ind, left_on='id', right_on='admin_id')

# Clean column names after merge
merged = merged.rename(columns={'name_x': 'name'})

st.title(f"Nigeria MRV Dashboard: {indicator} {year}")
st.info("Demo mode with synthetic data. Replace with GEE exports later.")

col1, col2 = st.columns([2,1])

with col1:
    m = folium.Map(location=[9.0820, 8.6753], zoom_start=6, tiles="CartoDB positron")
    
    if not merged.empty:
        merged['mean'] = merged['mean'].fillna(0)
        
        vmin = merged['mean'].min()
        vmax = merged['mean'].max()
        if vmin == vmax:
            vmax = vmin + 1

        colormap = cm.LinearColormap(['#8B0000','#FFFF00','#006400'], vmin=vmin, vmax=vmax)
        
        folium.GeoJson(
            merged.to_json(), 
            style_function=lambda f: {
                'fillColor': colormap(f['properties'].get('mean', 0)), 
                'color': 'white', 'weight': 1, 'fillOpacity': 0.8
            }, 
            tooltip=folium.GeoJsonTooltip(
                fields=['name','mean'],  # now 'name' exists
                aliases=['State','Value'],
                localize=True
            )
        ).add_to(m)
        colormap.caption = indicator
        colormap.add_to(m)
    else:
        folium.Marker([9.0820, 8.6753], popup="No data for selection").add_to(m)
        
    st_folium(m, use_container_width=True, height=500, returned_objects=[])

with col2:
    if not merged.empty:
        st.metric("National Mean", f"{merged['mean'].mean():.2f}")
        top10 = merged.sort_values('mean', ascending=False).head(10)
        fig = px.bar(top10, x='name', y='mean', title="Top 10 States") # now uses 'name'
        fig.update_layout(xaxis_tickangle=-45, height=400)
        st.plotly_chart(fig, use_container_width=True)
        st.download_button("Download CSV", merged.to_csv(index=False), f"MRV_{indicator}_{year}.csv")
    else:
        st.warning("Select at least 1 filter to see data")
