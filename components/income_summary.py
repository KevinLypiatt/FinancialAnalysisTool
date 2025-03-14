"""
Income Summary component for displaying individual financial summaries.
"""
import streamlit as st
from utils.visualizations import format_currency

def render_income_summary(income_summary_table):
    """
    Render individual financial summaries.
    
    Args:
        income_summary_table: List of dictionaries with income summary data
    """
    st.header("Individual Financial Summary")
    
    # Create a column for each person
    person_cols = st.columns(len(income_summary_table))
    
    # Populate each column with a person's detailed financial summary
    for i, row in enumerate(income_summary_table):
        with person_cols[i]:
            st.subheader(row['Owner'])
            
            # Show detailed financial breakdown with more explicit categories
            st.markdown(f"**Annual Taxable Income:** {row['Taxable Annual Income']}")
            st.markdown(f"**Estimated Tax:** {row['Estimated Tax']}")
            st.markdown(f"**Annual Net Income (after tax):** {row['Annual Net Income']}")
            st.markdown(f"**Annual Untaxed Income:** {row['Annual Untaxed Income']}")
            st.markdown(f"**Total Annual Income:** {row['Total Annual Income']}")
            
            if st.button("📊 Tax Breakdown", key=f"info_{row['Owner']}", help=f"Show tax calculation details for {row['Owner']}"):
                st.session_state.page = 'tax_details'
                st.session_state.tax_details = row['tax_details']
                st.rerun()
