with col1:
    m = folium.Map(location=[9.0820, 8.6753], zoom_start=6, tiles="CartoDB positron")
    
    if not merged.empty:
        # 1. Fill NaN so colormap doesn't break
        merged['mean'] = merged['mean'].fillna(0)
        
        vmin = merged['mean'].min()
        vmax = merged['mean'].max()
        if vmin == vmax: # avoid colormap error if all values same
            vmax = vmin + 1

        colormap = cm.LinearColormap(['#8B0000','#FFFF00','#006400'],
                                     vmin=vmin, vmax=vmax)
        
        # 2. Convert to JSON and make sure 'mean' exists in properties
        geojson_data = merged.to_json()
        
        folium.GeoJson(
            geojson_data, 
            style_function=lambda f: {
                'fillColor': colormap(f['properties'].get('mean', 0)), 
                'color': 'white',
                'weight': 1, 
                'fillOpacity': 0.8
            }, 
            tooltip=folium.GeoJsonTooltip(
                fields=['name','mean'], 
                aliases=['State','Value'],
                localize=True
            )
        ).add_to(m)
        colormap.caption = indicator
        colormap.add_to(m)
    else:
        folium.Marker([9.0820, 8.6753], popup="No data for selection").add_to(m)
        
    st_folium(m, use_container_width=True, height=500, returned_objects=[])
