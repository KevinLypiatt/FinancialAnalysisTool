"""
Asset Projections component for displaying asset growth charts and projections.
"""
import streamlit as st
from utils.visualizations import create_total_assets_chart, create_projection_chart

def render_asset_projections(processed_data, calculate_projections):
    """
    Render asset projections section with charts.
    
    Args:
        processed_data: Dictionary with processed financial data
        calculate_projections: Function to calculate asset projections
    """
    st.header("Asset Projections")
    
    # Projection period slider
    years = st.slider("Chart Projection Period (Years)", min_value=1, max_value=30, value=20)

    # Calculate projections based on selected years
    projections = calculate_projections(processed_data['df'], years)
    
    # Show the total assets (net worth) chart with the same time scale
    st.plotly_chart(
        create_total_assets_chart(projections),
        use_container_width=True
    )
    
    # Then add the asset selector and individual asset chart
    st.subheader("Individual Asset Projections")
    
    # Get all available asset names (excluding 'months' and 'Total Assets')
    all_assets = [key for key in projections.keys() if key != 'months' and key != 'Total Assets']
    
    # Create asset selection interface
    st.write("Select assets to display:")
    
    # Use columns for a more compact layout suitable for tablets
    asset_columns = st.columns(3)  # 3 columns for tablets, can adjust for mobile later
    
    # If there's no selection in session_state, initialize with no assets selected
    if 'selected_assets' not in st.session_state:
        st.session_state.selected_assets = []
    
    # Add select all / none buttons
    select_col1, select_col2, _ = st.columns([1, 1, 4])
    with select_col1:
        if st.button("Select All"):
            st.session_state.selected_assets = all_assets.copy()
            st.rerun()
    with select_col2:
        if st.button("Select None"):
            st.session_state.selected_assets = []
            st.rerun()
    
    # Create checkboxes for each asset
    selected_assets = []
    for i, asset in enumerate(all_assets):
        col_idx = i % 3  # Distribute across 3 columns
        with asset_columns[col_idx]:
            # Use the current selection state from session_state
            is_selected = st.checkbox(asset, value=asset in st.session_state.selected_assets, key=f"asset_{i}")
            if is_selected:
                selected_assets.append(asset)
    
    # Update session state with current selection
    st.session_state.selected_assets = selected_assets
    
    # Show the chart with only selected assets - using the same time scale as defined by the slider
    st.plotly_chart(
        create_projection_chart(projections, selected_assets),
        use_container_width=True
    )
    
    # Return the projections data for use in other components
    return projections
