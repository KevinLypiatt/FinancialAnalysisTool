"""
Data Tables component for displaying detailed data in tabbed interface.
"""
import streamlit as st
import pandas as pd

def render_data_tables(processed_data):
    """
    Render detailed data tables in a tabbed interface.
    
    Args:
        processed_data: Dictionary with processed financial data
    """
    st.header("Detailed Data")
    tabs = st.tabs(["Income", "Expenses", "Assets"])

    with tabs[0]:
        # Create a copy of the dataframe with rounded Monthly_Value
        income_df = processed_data['df'][processed_data['df']['Type'] == 'Income'].copy()
        income_df['Monthly_Value'] = income_df['Monthly_Value'].round(0)
        st.dataframe(income_df)

    with tabs[1]:
        # Create a copy of the dataframe with rounded Monthly_Value
        expense_df = processed_data['df'][processed_data['df']['Type'] == 'Expense'].copy()
        expense_df['Monthly_Value'] = expense_df['Monthly_Value'].round(0)
        st.dataframe(expense_df)

    with tabs[2]:
        # Create a copy of the dataframe with rounded Monthly_Value
        asset_df = processed_data['df'][processed_data['df']['Type'] == 'Asset'].copy()
        asset_df['Monthly_Value'] = asset_df['Monthly_Value'].round(0)
        st.dataframe(asset_df)
