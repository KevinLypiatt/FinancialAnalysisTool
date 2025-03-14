"""
Household Summary component for displaying household-level metrics and sustainability.
"""
import streamlit as st
from utils.visualizations import format_currency
from config import VISUALIZATION

def render_household_summary(cashflow_summary, sustainability_data):
    """
    Render household summary including metrics and sustainability analysis.
    
    Args:
        cashflow_summary: Dictionary with household cashflow metrics
        sustainability_data: Tuple of (years, message, detailed_message)
    """
    st.header("Household Summary")
    
    # Create a single column for household summary
    household_col = st.columns(1)[0]
    with household_col:
        st.metric("Annual Household Income", cashflow_summary['Total Net Income'])
        st.metric("Annual Household Expenses", cashflow_summary['Total Expenses'])
        st.metric("Annual Surplus/Deficit", cashflow_summary['Annual Surplus/Deficit'])
    
    # Add sustainability callout
    st.markdown("---")
    
    # Unpack sustainability data
    years_sustainable, sustainability_message, detailed_message = sustainability_data
    
    # Format the message in a callout box
    message_color = (
        VISUALIZATION['SUSTAINABILITY_COLORS']['GOOD'] if years_sustainable > 10 else 
        VISUALIZATION['SUSTAINABILITY_COLORS']['WARNING'] if years_sustainable > 5 else 
        VISUALIZATION['SUSTAINABILITY_COLORS']['DANGER']
    )
    
    st.markdown(
        f"""
        <div style="
            background-color: {message_color}15; 
            border-left: 4px solid {message_color}; 
            padding: 15px; 
            border-radius: 5px; 
            margin: 10px 0;">
            <h3 style="margin-top:0; color: {message_color}">Financial Sustainability</h3>
            <p style="font-size: 1.1rem; margin-bottom: 10px;"><strong>{sustainability_message}</strong></p>
            <div style="font-size: 0.95rem; color: #333;">{detailed_message}</div>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    st.markdown("---")
