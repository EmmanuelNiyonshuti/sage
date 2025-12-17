import pandas as pd
import streamlit as st
from api import (
    create_parcel,
    fetch_parcel_details,
    fetch_parcels,
    fetch_raw_stats,
    fetch_time_series,
)
from maps import create_base_map, visualize_parcel_on_map
from streamlit_folium import st_folium

# Page configuration
st.set_page_config(
    page_title="SAGE Dashboard",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Initialize session state
if "selected_parcel" not in st.session_state:
    st.session_state.selected_parcel = None
if "drawn_polygon" not in st.session_state:
    st.session_state.drawn_polygon = None

st.title("🌾 SAGE Dashboard")
st.markdown("Monitor your farm parcels with satellite-derived NDVI data")

st.sidebar.header("Navigation")
page = st.sidebar.radio("Go to", ["Dashboard", "Create Parcel", "Analytics"])

st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.info(
    "This dashboard is an internal visualization tool for SAGE.\n\n"
    "It shows parcel boundaries, satellite-derived NDVI statistics, "
    "aggregated time series, and basic anomaly signals computed by "
    "scheduled backend jobs using Sentinel Hub data."
)


def display_parcel_card(parcel):
    """Display a single parcel as a card"""
    with st.container():
        col1, col2, col3 = st.columns([3, 2, 1])

        with col1:
            st.subheader(parcel.get("name", "Unnamed Parcel"))
            if parcel.get("crop_type"):
                st.caption(f"🌱 {parcel['crop_type']}")

        with col2:
            if parcel.get("area_hectares"):
                st.metric("Area", f"{parcel['area_hectares']:.2f} ha")

        with col3:
            if st.button("View Details", key=f"view_{parcel['uid']}"):
                st.session_state.selected_parcel = parcel["uid"]
                st.rerun()

        # Additional info
        cols = st.columns(4)
        with cols[0]:
            st.caption(f"**Soil:** {parcel.get('soil_type', 'N/A')}")
        with cols[1]:
            st.caption(f"**Irrigation:** {parcel.get('irrigation_type', 'N/A')}")
        with cols[2]:
            if parcel.get("latest_acquisition_date"):
                st.caption(f"**Latest Data:** {parcel['latest_acquisition_date']}")
        with cols[3]:
            status = "🟢 Active" if parcel.get("is_active") else "🔴 Inactive"
            st.caption(f"**Status:** {status}")

        st.markdown("---")


# ========== PAGE ROUTING ==========

if page == "Dashboard":
    st.header("Your Parcels")

    # Back button if viewing details
    if st.session_state.selected_parcel:
        if st.button("← Back to all parcels"):
            st.session_state.selected_parcel = None
            st.rerun()

        # Show parcel details
        parcel_id = st.session_state.selected_parcel
        parcel = fetch_parcel_details(parcel_id)

        if parcel:
            st.markdown(f"## {parcel['name']}")

            # Parcel info
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Area", f"{parcel.get('area_hectares', 0):.2f} ha")
            with col2:
                st.metric("Crop Type", parcel.get("crop_type", "N/A"))
            with col3:
                st.metric("Soil Type", parcel.get("soil_type", "N/A"))
            with col4:
                status = "Active" if parcel.get("is_active") else "Inactive"
                st.metric("Status", status)

            st.markdown("---")

            # Tabs for different views
            tab1, tab2, tab3 = st.tabs(["Raw Statistics", "Time Series", "Map View"])

            with tab1:
                st.subheader("Raw NDVI Statistics")
                with st.spinner("Loading raw statistics..."):
                    raw_stats = fetch_raw_stats(parcel_id)
                    stats = raw_stats.get("stats")
                if stats:
                    # Convert to DataFrame for easy display
                    df = pd.DataFrame(stats)
                    # Sort by date
                    df["acquisition_date"] = pd.to_datetime(df["acquisition_date"])
                    df = df.sort_values("acquisition_date", ascending=False)

                    st.write(f"**Total observations:** {len(df)}")

                    # Display table
                    st.dataframe(
                        df[
                            [
                                "acquisition_date",
                                "metric_type",
                                "mean_value",
                                "min_value",
                                "max_value",
                                "std_dev",
                                # "cloud_cover_percent",
                            ]
                        ],
                        use_container_width=True,
                        hide_index=True,
                    )

                    # Simple line chart of mean values over time
                    st.subheader("NDVI Mean Values Over Time")
                    chart_df = df[["acquisition_date", "mean_value"]].set_index(
                        "acquisition_date"
                    )
                    st.line_chart(chart_df)
                else:
                    st.info(
                        "No raw statistics available yet. Data ingestion may still be in progress."
                    )

            with tab2:
                st.subheader("Time Series Analysis")

                # Period selector
                period = st.selectbox(
                    "Select time period", ["weekly", "monthly"], index=0
                )

                with st.spinner(f"Loading {period} time series..."):
                    ts_data = fetch_time_series(parcel_id, period)
                    stats = ts_data.get("stats")
                if stats:
                    df_ts = pd.DataFrame(stats)
                    df_ts["start_date"] = pd.to_datetime(df_ts["start_date"])
                    df_ts = df_ts.sort_values("start_date")

                    # Metrics
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        avg_value = df_ts["value"].mean()
                        st.metric("Average NDVI", f"{avg_value:.3f}")
                    with col2:
                        anomaly_count = df_ts["is_anomaly"].sum()
                        st.metric("Anomalies Detected", anomaly_count)
                    with col3:
                        latest_change = df_ts.iloc[-1]["change_from_previous"]
                        if pd.notna(latest_change):
                            st.metric(
                                "Latest Change",
                                f"{latest_change:.2f}%",
                                delta=f"{latest_change:.2f}%",
                            )

                    st.markdown("---")

                    # Time series chart with anomalies highlighted
                    st.subheader(f"{period.capitalize()} NDVI Trend")

                    chart_df = df_ts[["start_date", "value"]].set_index("start_date")
                    st.line_chart(chart_df)

                    # Highlight anomalies
                    anomalies = df_ts[df_ts["is_anomaly"] == True]  # noqa
                    if not anomalies.empty:
                        st.warning(f"⚠️ {len(anomalies)} anomalies detected:")
                        st.dataframe(
                            anomalies[["start_date", "value", "change_from_previous"]],
                            use_container_width=True,
                            hide_index=True,
                        )

                    # Full data table
                    with st.expander("View full time series data"):
                        st.dataframe(df_ts, use_container_width=True, hide_index=True)
                else:
                    st.info("No time series data available yet.")

            with tab3:
                st.subheader("Parcel Location")
                # Display map with parcel boundary
                m = visualize_parcel_on_map(parcel)
                st_folium(m, width=700, height=500)

    else:
        # Show all parcels list
        with st.spinner("Loading parcels..."):
            parcels = fetch_parcels()

        if not parcels:
            st.info("No parcels found. Create your first parcel to get started!")
            if st.button("➕ Create New Parcel"):
                st.session_state.page = "Create Parcel"
                st.rerun()
        else:
            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Parcels", len(parcels))
            with col2:
                active_count = sum(1 for p in parcels if p.get("is_active"))
                st.metric("Active", active_count)
            with col3:
                total_area = sum(p.get("area_hectares", 0) for p in parcels)
                st.metric("Total Area", f"{total_area:.2f} ha")
            with col4:
                with_data = sum(1 for p in parcels if p.get("latest_acquisition_date"))
                st.metric("With Data", with_data)

            st.markdown("---")

            # Filter options
            col1, col2 = st.columns([3, 1])
            with col1:
                search = st.text_input(
                    "🔍 Search parcels", placeholder="Enter parcel name..."
                )
            with col2:
                show_inactive = st.checkbox("Show inactive", value=False)

            # Filter parcels
            filtered_parcels = parcels
            if search:
                filtered_parcels = [
                    p
                    for p in filtered_parcels
                    if search.lower() in p.get("name", "").lower()
                ]
            if not show_inactive:
                filtered_parcels = [p for p in filtered_parcels if p.get("is_active")]

            # Display parcels
            if filtered_parcels:
                for parcel in filtered_parcels:
                    display_parcel_card(parcel)
            else:
                st.warning("No parcels match your filters.")

elif page == "Create Parcel":
    st.header("Create New Parcel")

    st.markdown("""
    **Instructions:**
    1. Use the drawing tools on the map to draw your parcel boundary
    2. You can draw a polygon or rectangle
    3. Fill in the parcel details below
    4. Click 'Create Parcel' to save
    """)

    # Map for drawing
    st.subheader("Step 1: Draw Parcel Boundary on Map")

    col1, col2 = st.columns([2, 1])

    with col1:
        # Create map centered on Kigali, Rwanda (you can change this)
        center = st.text_input("Map Center (lat, lon)", value="-1.9441, 30.0619")
        try:
            lat, lon = [float(x.strip()) for x in center.split(",")]
        except:  # noqa
            lat, lon = -1.9441, 30.0619

        m = create_base_map(center=[lat, lon], zoom=12)
        output = st_folium(m, width=700, height=500, key="map")

    with col2:
        st.info(
            "🗺️ **How to draw:**\n\n"
            "1. Click the ⬜ or 🔺 icon on the map\n"
            "2. Click on map to draw points\n"
            "3. Double-click to finish\n"
            "4. Use ✏️ to edit\n"
            "5. Use 🗑️ to delete"
        )

        if output and output.get("all_drawings"):
            st.success("✅ Boundary drawn!")
            drawings = output["all_drawings"]
            st.write(f"**Shapes drawn:** {len(drawings)}")

    st.markdown("---")

    # Parcel details form
    st.subheader("Step 2: Parcel Details")

    with st.form("create_parcel_form"):
        col1, col2 = st.columns(2)

        with col1:
            name = st.text_input("Parcel Name*", placeholder="e.g., North Field")
            crop_type = st.selectbox(
                "Crop Type",
                [
                    "",
                    "Maize",
                    "Wheat",
                    "Rice",
                    "Soybeans",
                    "Potatoes",
                    "Cotton",
                    "Other",
                ],
            )
            soil_type = st.selectbox(
                "Soil Type", ["", "Clay", "Sandy", "Loamy", "Silty", "Peaty", "Other"]
            )

        with col2:
            irrigation_type = st.selectbox(
                "Irrigation Type", ["", "rainfed", "irrigated", "mixed"]
            )
            auto_sync = st.checkbox("Enable automatic data sync", value=True)

        submitted = st.form_submit_button("Create Parcel")

        if submitted:
            if not name:
                st.error("Please provide a parcel name.")
            elif not output or not output.get("all_drawings"):
                st.error("Please draw a parcel boundary on the map first.")
            else:
                # Extract the drawn geometry
                drawings = output["all_drawings"]
                if len(drawings) > 0:
                    geometry = drawings[-1].get("geometry")  # Get last drawn shape

                    if geometry and geometry.get("type") == "Polygon":
                        coordinates = geometry.get("coordinates")
                        if coordinates:
                            # Prepare parcel data
                            parcel_data = {
                                "name": name,
                                "geometry": {
                                    "type": "Polygon",
                                    "coordinates": coordinates,
                                },
                                "crop_type": crop_type if crop_type else None,
                                "soil_type": soil_type if soil_type else None,
                                "irrigation_type": irrigation_type
                                if irrigation_type
                                else None,
                                "auto_sync_enabled": auto_sync,
                            }

                            with st.spinner(
                                "Creating parcel and initiating backfill..."
                            ):
                                result = create_parcel(parcel_data)

                            if result:
                                st.success(f"✅ Parcel '{name}' created successfully!")
                                st.info(
                                    "🔄 Initial data backfill has been triggered. This may take a few minutes."
                                )
                                st.balloons()

                                # Show created parcel info
                                with st.expander("View created parcel details"):
                                    st.json(result)

                                # Button to go to dashboard
                                if st.button(
                                    "Go to Dashboard"
                                ):  # raises streamlit exception
                                    st.session_state.selected_parcel = result.get("uid")
                                    st.rerun()
                        else:
                            st.error("Failed to convert geometry to WKT format.")
                    else:
                        st.error("Please draw a polygon or rectangle on the map.")

elif page == "Analytics":
    st.header("Analytics Overview")

    with st.spinner("Loading analytics..."):
        parcels = fetch_parcels()

    if not parcels:
        st.info("No parcels available for analytics.")
    else:
        st.subheader("Fleet Overview")

        # Overall metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_parcels = len(parcels)
            st.metric("Total Parcels", total_parcels)
        with col2:
            total_area = sum(p.get("area_hectares", 0) for p in parcels)
            st.metric("Total Area", f"{total_area:.2f} ha")
        with col3:
            avg_area = total_area / total_parcels if total_parcels > 0 else 0
            st.metric("Avg Parcel Size", f"{avg_area:.2f} ha")
        with col4:
            active_monitoring = sum(1 for p in parcels if p.get("auto_sync_enabled"))
            st.metric("Auto-Sync Enabled", active_monitoring)

        st.markdown("---")

        # Crop distribution
        st.subheader("Crop Distribution")
        crop_counts = {}
        for p in parcels:
            crop = p.get("crop_type") or "Unknown"
            crop_counts[crop] = crop_counts.get(crop, 0) + 1

        if crop_counts:
            df_crops = pd.DataFrame(
                list(crop_counts.items()), columns=["Crop", "Count"]
            )
            st.bar_chart(df_crops.set_index("Crop"))

        # Recent activity
        st.subheader("Recent Data Updates")
        recent = sorted(
            [p for p in parcels if p.get("last_data_synced_at")],
            key=lambda x: x["last_data_synced_at"],
            reverse=True,
        )[:5]

        if recent:
            for p in recent:
                st.write(f"**{p['name']}** - Last synced: {p['last_data_synced_at']}")
        else:
            st.info("No recent data syncs recorded.")

st.markdown("---")
st.caption("Powered by Sentinel Hub API")
