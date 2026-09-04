import streamlit as st
import geopandas as gpd
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
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
    gdf['geometry'] = gdf['geometry'].simplify(0.05, preserve_topology=True)
    return gdf

@st.cache_data
def load_data():
    # For now use dummy 10-year monthly data. Replace with pd.read_csv("mrv_data.csv")
    admins = load_admins()
    records = []
    years = list(range(2016, 2026))
    months = list(range(1, 13))
    indicators = ['NDVI','SOC','LULC','DesertificationRisk','Flooding','HeatStress','Drought','Rainfall']
    
    lulc_classes = {1:'Forest', 2:'Grassland', 3:'Cropland', 4:'Built-up', 5:'Water', 6:'Bare'}
    
    for year in years:
        for month in months:
            for _, row in admins.iterrows():
                for ind in indicators:
                    if ind == 'NDVI': mean = np.random.uniform(0.2, 0.9)
                    elif ind == 'SOC': mean = np.random.uniform(5, 60)
                    elif ind == 'LULC': mean = np.random.choice(list(lulc_classes.keys()))
                    else: mean = np.random.uniform(0, 100)
                    records.append({
                        'admin_id': row['id'], 'name': row['name'],
                        'indicator': ind, 'year': year, 'month': month,
                        'mean': mean, 'std': mean*0.1, 'min': mean*0.8, 'max': mean*1.2,
                    })
    return pd.DataFrame(records), lulc_classes

admins = load_admins()
indicators_df, lulc_classes = load_data()

st.sidebar.title("🇳🇬 Nigeria MRV System")
year = st.sidebar.slider("Year", 2016, 2025, 2025)
month = st.sidebar.selectbox("Month", ["Annual"] + list(range(1,13)), index=12)
indicator = st.sidebar.selectbox("Indicator", indicators_df['indicator'].unique())
admin_filter = st.sidebar.multiselect("Filter by State", admins['name'].tolist())

month_val = 13 if month == "Annual" else month
filtered_ind = indicators_df[(indicators_df['year']==year) & (indicators_df['indicator']==indicator)]
if month_val != 13:
    filtered_ind = filtered_ind[filtered_ind['month']==month_val]
else:
    filtered_ind = filtered_ind.groupby(['admin_id','name','indicator','year']).mean(numeric_only=True).reset_index()

filtered_admins = admins[admins['name'].isin(admin_filter)] if admin_filter else admins
merged = filtered_admins.merge(filtered_ind, left_on='id', right_on='admin_id').rename(columns={'name_x':'name'})

st.title(f"Nigeria MRV: {indicator} - {year} {'' if month=='Annual' else f'Month {month}'}")

col1, col2 = st.columns([2,1])

with col1:
    m = folium.Map(location=[9.0820, 8.6753], zoom_start=6, tiles="CartoDB positron")
    
    if not merged.empty:
        merged['mean'] = merged['mean'].fillna(0)
        
        if indicator == 'LULC':
            # Categorical colormap for LULC
            colors = ['#228B22','#90EE90','#DAA520','#8B0000','#0000CD','#D2B48C']
            colormap = cm.StepColormap(colors, index=list(lulc_classes.keys()), vmin=1, vmax=6)
            tooltip_fields = ['name','mean']
            tooltip_alias = ['State','LULC Class']
        else:
            vmin, vmax = merged['mean'].min(), merged['mean'].max()
            if vmin == vmax: vmax = vmin + 1
            colormap = cm.LinearColormap(['#8B0000','#FFFF00','#006400'], vmin=vmin, vmax=vmax)
            tooltip_fields = ['name','mean']
            tooltip_alias = ['State','Value']

        folium.GeoJson(
            merged.to_json(), 
            style_function=lambda f: {
                'fillColor': colormap(f['properties'].get('mean', 0)), 
                'color': 'white', 'weight': 1, 'fillOpacity': 0.8
            }, 
            tooltip=folium.GeoJsonTooltip(fields=tooltip_fields, aliases=tooltip_alias)
        ).add_to(m)
        colormap.caption = indicator
        colormap.add_to(m)
    st_folium(m, use_container_width=True, height=500, returned_objects=[])

with col2:
    if not merged.empty:
        st.metric("National Mean", f"{merged['mean'].mean():.2f}")
        
        # Time series if not annual
        if month == "Annual":
            ts = indicators_df[indicators_df['indicator']==indicator].groupby('year')['mean'].mean()
            fig = px.line(x=ts.index, y=ts.values, title=f"10-Year Trend: {indicator}")
            st.plotly_chart(fig, use_container_width=True)
        else:
            top10 = merged.sort_values('mean', ascending=False).head(10)
            fig = px.bar(top10, x='name', y='mean', title="Top 10 States")
            fig.update_layout(xaxis_tickangle=-45, height=350)
            st.plotly_chart(fig, use_container_width=True)
            
        st.download_button("Download CSV", merged.to_csv(index=False), f"MRV_{indicator}_{year}_{month}.csv")
