"""
Cash Flow component for displaying Sankey diagrams.
"""
import streamlit as st
import pandas as pd
from utils.visualizations import create_cashflow_sankey

def render_cash_flow(df, processed_data, calculate_monthly_value):
    """
    Render cash flow visualization with Sankey diagram.
    
    Args:
        df: Raw DataFrame with financial data
        processed_data: Dictionary with processed financial data
        calculate_monthly_value: Function to calculate monthly values
    """
    st.subheader("Cash Flow Visualization")
    
    # Create a modified dataframe with adjusted net income values
    if df is not None:  # Add check to ensure df is available
        net_income_df = df.copy()
        
        # First, we need to calculate monthly values without relying on Depletion_Years
        # Use the modified version of calculate_monthly_value that doesn't depend on Depletion_Years
        net_income_df['Monthly_Value'] = net_income_df.apply(calculate_monthly_value, axis=1)
        
        # For each person, calculate their effective tax rate and apply it to income sources
        for owner, summary in processed_data['income_summary'].items():
            if owner == 'Joint':
                continue
                
            # Calculate the effective tax rate for this owner
            taxable_income = summary['taxable_income']
            
            if taxable_income > 0:
                # Calculate effective tax rate on the taxable portion
                effective_tax_rate = summary['tax'] / taxable_income if taxable_income > 0 else 0
                
                # Apply the tax rate to each income source for this owner
                income_mask = (net_income_df['Type'] == 'Income') & (net_income_df['Owner'] == owner) & (net_income_df['Taxable'].str.lower() == 'yes')
                asset_income_mask = (net_income_df['Type'] == 'Asset') & (net_income_df['Owner'] == owner) & (net_income_df['Monthly_Value'] > 0) & (net_income_df['Taxable'].str.lower() == 'yes')
                
                # Apply to regular taxable income sources
                for idx in net_income_df.index[income_mask]:
                    gross_monthly = net_income_df.at[idx, 'Monthly_Value']
                    net_income_df.at[idx, 'Monthly_Value'] = gross_monthly * (1 - effective_tax_rate)
                
                # Apply to taxable asset income sources
                for idx in net_income_df.index[asset_income_mask]:
                    gross_monthly = net_income_df.at[idx, 'Monthly_Value']
                    net_income_df.at[idx, 'Monthly_Value'] = gross_monthly * (1 - effective_tax_rate)

        # Pass the modified dataframe with net income values and the total net income
        st.plotly_chart(
            create_cashflow_sankey(net_income_df, processed_data['total_net_income']),
            use_container_width=True
        )
    else:
        # Fallback for when df is not available - use the processed data which already has Monthly_Value
        st.plotly_chart(
            create_cashflow_sankey(processed_data['df'], processed_data['total_net_income']),
            use_container_width=True
        )
