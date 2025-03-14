"""
Asset Details component for displaying asset forecasts and depletion analysis.
"""
import streamlit as st
import pandas as pd
from utils.visualizations import create_asset_projection_table, create_asset_cards, format_currency

def render_asset_details(processed_data, projections):
    """
    Render asset details including forecast tables and depletion analysis.
    
    Args:
        processed_data: Dictionary with processed financial data
        projections: Dictionary with asset projection data
    """
    # Move card view toggle from sidebar to main page
    is_mobile = st.checkbox("Card View", value=False)
    
    # Asset Value Forecast Table - either cards or table based on mobile view
    st.subheader("Asset Value Forecast")
    
    if 'asset_projections' in processed_data:
        # Get the asset projections
        asset_projections = processed_data['asset_projections']
        
        # Store original assets for reference in the table creation
        asset_projections['original_assets'] = processed_data['assets']
        
        if is_mobile:
            _render_asset_cards(projections, processed_data['assets'])
        else:
            _render_asset_table(asset_projections)
    
    # Asset depletion analysis - only show in regular view
    if not is_mobile:
        _render_depletion_analysis(processed_data['assets'])

def _render_asset_cards(projections, assets_df):
    """Render asset cards for mobile view."""
    # Generate cards with tables instead of charts
    asset_cards = create_asset_cards(projections, assets_df)
    
    # Add custom CSS for better card styling
    st.markdown("""
    <style>
    .asset-card-title {
        font-size: 1.5rem;
        font-weight: bold;
        padding-bottom: 12px;
        margin-top: 0;
    }
    .card-column-header {
        font-size: 1.1rem;  /* Increased font size for Projections header */
        font-weight: 600;
        color: #555;
        margin-bottom: 8px;
    }
    /* Hide index column and remove borders */
    .stTable div[data-testid="stTable"] table {
        border-collapse: collapse;
    }
    .stTable div[data-testid="stTable"] table thead tr:first-child {
        display: none;
    }
    .stTable div[data-testid="stTable"] table tbody tr td {
        border: none;
        padding: 4px 8px 4px 0;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Display cards in a 1-column layout
    for card in asset_cards:
        with st.expander("", expanded=True):  # Remove the small asset name
            # Display only the asset name in large bold font
            st.markdown(f"<div class='asset-card-title'>{card['name']}</div>", unsafe_allow_html=True)
            
            # Create two columns for the card content
            col1, col2 = st.columns(2)
            
            # Left column - metrics with smaller header
            with col1:
                st.markdown("<div class='card-column-header'>Key Metrics</div>", unsafe_allow_html=True)
                # Apply the stTable class to enable CSS targeting
                st.markdown("<div class='stTable'>", unsafe_allow_html=True)
                st.table(pd.DataFrame(card['metrics'].items(), columns=["Metric", "Value"]).set_index("Metric"))
                st.markdown("</div>", unsafe_allow_html=True)
            
            # Right column - projections with larger header
            with col2:
                st.markdown("<div class='card-column-header'>Projections</div>", unsafe_allow_html=True)
                # Apply the stTable class to enable CSS targeting
                st.markdown("<div class='stTable'>", unsafe_allow_html=True)
                # Explicitly define column names when creating the DataFrame
                st.table(pd.DataFrame(card['projections'].items(), columns=["Year", "Value"]).set_index("Year"))
                st.markdown("</div>", unsafe_allow_html=True)

def _render_asset_table(asset_projections):
    """Render asset projection table for desktop view."""
    # Create the table with intervals at 5, 10, 15, and 20 years
    projection_table = create_asset_projection_table(asset_projections)
    
    # Format the currency columns
    for col in projection_table.columns:
        if col not in ['Asset', 'Growth Rate', 'Withdrawal Rate']:
            projection_table[col] = projection_table[col].apply(lambda x: f"£{x:,.0f}")
    
    # Display the table
    st.dataframe(
        projection_table,
        use_container_width=True,
        hide_index=True
    )
    
    # Add a note about the projections
    st.caption("""
    This table shows projected asset values at 5-year intervals based on current growth rates and withdrawal levels.
    The 'Withdrawal Rate' is calculated as annual withdrawals divided by current value.
    """)

def _render_depletion_analysis(assets):
    """Render asset depletion analysis table."""
    st.subheader("Asset Depletion Analysis")
    
    # Create and display the asset depletion table
    depletion_data = []
    for _, asset in assets.iterrows():
        monthly_value = asset['Monthly_Value']
        # Handle growth rate formatting safely whether it's a string or numeric
        if isinstance(asset['Growth_Rate'], str):
            growth_rate_display = asset['Growth_Rate']  # Already formatted as string
        else:
            growth_rate_display = f"{asset['Growth_Rate'] * 100:.2f}%"  # Format numeric value
            
        depletion_data.append({
            'Asset': f"{asset['Description']} ({asset['Owner']})",
            'Starting Value': format_currency(asset['Capital_Value']),
            'Growth Rate': growth_rate_display,
            'Monthly Withdrawal': format_currency(monthly_value),
            'Annual Withdrawal': format_currency(monthly_value * 12),
            'Years until Depletion': f"{asset['Depletion_Years']:.2f}" if asset['Depletion_Years'] < 100 else "Never"
        })

    st.dataframe(
        pd.DataFrame(depletion_data),
        use_container_width=True,
        hide_index=True
    )
