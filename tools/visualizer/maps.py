import folium


def visualize_parcel_on_map(parcel_data):
    """Create a map showing the parcel boundary"""
    coords = parcel_data["geometry"]["coordinates"][0]
    latlon_coords = [(lat, lon) for lon, lat in coords]

    lats = [lat for lat, _ in latlon_coords]
    lons = [lon for _, lon in latlon_coords]
    center = [sum(lats) / len(lats), sum(lons) / len(lons)]

    m = folium.Map(location=center, zoom_start=16)

    folium.Polygon(
        locations=latlon_coords,
        color="green",
        weight=2,
        fill=True,
        fill_opacity=0.3,
    ).add_to(m)

    return m


def create_base_map(center=[51.5074, -0.1278], zoom=10):
    """Create a folium map with drawing tools"""
    m = folium.Map(
        location=center,
        zoom_start=zoom,
        tiles="OpenStreetMap",
    )

    # Add drawing tools
    folium.plugins.Draw(
        export=True,
        filename="parcel_boundary.geojson",
        position="topleft",
        draw_options={
            "polyline": False,
            "rectangle": True,
            "polygon": True,
            "circle": False,
            "marker": False,
            "circlemarker": False,
        },
        edit_options={"edit": True},
    ).add_to(m)

    return m
