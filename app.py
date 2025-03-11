import streamlit as st
import pandas as pd
from utils.data_processor import process_data, calculate_projections
from utils.visualizations import (
    create_projection_chart,
    create_income_summary_table,
    create_cashflow_summary,
    create_cashflow_sankey,
    format_currency,
    create_asset_projection_table  # Add this import
)
from utils.ai_chat import render_chat_interface  # Add this import

st.set_page_config(page_title="Financial Analysis Tool", layout="wide")

# Add custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stPlotlyChart {
        background-color: white;
        border-radius: 5px;
        padding: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }
    .income-table {
        font-size: 1.2rem !important;
    }
    .income-table th {
        font-size: 1.1rem !important;
        font-weight: bold !important;
        padding: 10px !important;
    }
    .income-table td {
        padding: 10px !important;
    }
    </style>
""", unsafe_allow_html=True)

def show_tax_details(tax_details):
    """Display tax calculation explanation."""
    st.markdown("""
    ## Individual Tax Calculation Breakdown

    ### 2024/25 Tax Year Rates (England, Wales, and Northern Ireland)
    - Personal Allowance: 0% on income up to £12,570
    - Basic Rate: 20% on income from £12,571 to £50,270
    - Higher Rate: 40% on income from £50,271 to £125,140
    - Additional Rate: 45% on income over £125,140

    Below is a detailed breakdown of how the tax is calculated:
    """)

    # Get the correct tax-free allowance to display
    tax_free_allowance = tax_details.get('tax_free_allowance', 12570)
    
    # Calculate gross income if not present
    if 'gross_income' not in tax_details and 'total_tax' in tax_details:
        # Estimate gross income from other fields
        basic_amount = tax_details.get('basic_rate_amount', 0)
        higher_amount = tax_details.get('higher_rate_amount', 0)
        additional_amount = tax_details.get('additional_rate_amount', 0)
        gross_income = tax_free_allowance + basic_amount + higher_amount + additional_amount
    else:
        gross_income = tax_details.get('gross_income', 0)
        
    total_tax = tax_details.get('total_tax', 0)
    
    st.markdown(f"""
    ### 📊 Income Breakdown

    **Total Gross Income:** {format_currency(gross_income)}

    **Personal Allowance:** {format_currency(tax_free_allowance)}

    ### 💷 Tax Bands

    **Basic Rate (20%):**
    - Amount in band: {format_currency(tax_details['basic_rate_amount'])}
    - Tax paid: {format_currency(tax_details['basic_rate_amount'] * 0.20)}

    **Higher Rate (40%):**
    - Amount in band: {format_currency(tax_details['higher_rate_amount'])}
    - Tax paid: {format_currency(tax_details['higher_rate_amount'] * 0.40)}

    **Additional Rate (45%):**
    - Amount in band: {format_currency(tax_details['additional_rate_amount'])}
    - Tax paid: {format_currency(tax_details['additional_rate_amount'] * 0.45)}

    ### 📈 Summary
    **Total Tax Paid:** {format_currency(total_tax)}
    **Net Income:** {format_currency(gross_income - total_tax)}
    """)

def calculate_monthly_value(asset):
    """Calculates the monthly withdrawal amount from an asset."""
    capital_value = asset['Capital_Value']
    growth_rate = asset['Growth_Rate']
    years_until_depletion = asset['Depletion_Years']

    if years_until_depletion <=0 or years_until_depletion == float('inf'):
        return 0  # Avoid division by zero or infinity

    # Simple calculation, assuming constant withdrawals. More sophisticated models could be used.
    total_withdrawal = capital_value * (1 + growth_rate * years_until_depletion)
    monthly_withdrawal = total_withdrawal / (years_until_depletion * 12)

    return monthly_withdrawal

def calculate_sustainability(assets_df, monthly_surplus):
    """
    Calculate how long the household can sustain spending with current assets if in deficit.
    
    Args:
        assets_df: DataFrame containing asset information
        monthly_surplus: Monthly surplus amount (negative for deficit)
    
    Returns:
        Tuple of (years, formatted_message, detailed_message)
    """
    # Calculate total monthly income from assets that are being withdrawn
    total_monthly_asset_income = assets_df['Monthly_Value'].sum()
    
    if monthly_surplus >= 0:
        # For surplus situations, calculate how long until assets are depleted
        total_assets = assets_df['Capital_Value'].sum()
        
        # Track asset depletion events and their impact on income
        depletion_events = []
        
        # Find all assets with withdrawals and sort by depletion time
        withdrawal_assets = assets_df[assets_df['Monthly_Value'] > 0].copy()
        
        # If there are no assets being withdrawn, handle differently
        if len(withdrawal_assets) == 0:
            return float('inf'), "Your income covers all expenses! 🎉", "With your current surplus and no asset withdrawals, your finances appear sustainable for the long term."
        
        # Sort assets by depletion years to analyze the timeline of impacts
        withdrawal_assets = withdrawal_assets.sort_values('Depletion_Years')
        
        # Calculate when surplus will drop to zero by tracking cumulative asset depletion
        remaining_surplus = monthly_surplus
        years_until_zero_surplus = float('inf')
        zero_surplus_asset = "None"
        
        # Get the earliest depleting asset with a withdrawal
        min_depletion_years = float('inf')
        earliest_depleting_asset = "None"
        
        # Create a copy of assets_df to simulate growth until surplus runs out
        future_assets = assets_df.copy()
        
        current_time = 0
        for _, asset in withdrawal_assets.iterrows():
            depletion_years = asset.get('Depletion_Years', float('inf'))
            monthly_income = asset['Monthly_Value']
            asset_name = f"{asset['Description']} ({asset['Owner']})"
            
            # Track the earliest depleting asset
            if depletion_years < min_depletion_years and depletion_years < float('inf'):
                min_depletion_years = depletion_years
                earliest_depleting_asset = asset_name
            
            # Check if this depletion event would cause surplus to go negative
            if depletion_years < float('inf') and remaining_surplus > 0:
                remaining_surplus -= monthly_income
                
                # If this causes surplus to go negative, this is when the household goes into deficit
                if remaining_surplus <= 0 and years_until_zero_surplus == float('inf'):
                    years_until_zero_surplus = depletion_years
                    zero_surplus_asset = asset_name
                    
                    # Calculate remaining assets at this point
                    for idx, future_asset in future_assets.iterrows():
                        # Get growth rate as a decimal
                        growth_rate = future_asset['Growth_Rate']
                        if isinstance(growth_rate, str):
                            growth_rate = float(growth_rate.strip('%').replace(',', '')) / 100
                        
                        # Calculate future value of this asset at the time surplus runs out
                        monthly_growth_rate = growth_rate / 12
                        
                        if future_asset['Monthly_Value'] > 0:
                            # For assets with withdrawals, calculate their remaining value
                            # For the asset that causes zero surplus, it will be depleted
                            if future_asset['Description'] == asset['Description'] and future_asset['Owner'] == asset['Owner']:
                                # This is the asset that gets depleted, value becomes zero
                                future_assets.at[idx, 'Capital_Value'] = 0
                            else:
                                # For other assets with withdrawals, calculate remaining value
                                monthly_withdrawal = future_asset['Monthly_Value']
                                future_value = future_asset['Capital_Value']
                                
                                # Simulate growth and withdrawals for the number of months until surplus runs out
                                months = int(years_until_zero_surplus * 12)
                                for _ in range(months):
                                    future_value = future_value * (1 + monthly_growth_rate) - monthly_withdrawal
                                    if future_value <= 0:
                                        future_value = 0
                                        break
                                
                                future_assets.at[idx, 'Capital_Value'] = max(0, future_value)
                        else:
                            # For assets without withdrawals, just apply growth
                            future_value = future_asset['Capital_Value'] * ((1 + monthly_growth_rate) ** (years_until_zero_surplus * 12))
                            future_assets.at[idx, 'Capital_Value'] = future_value
        
        # Calculate total remaining assets at the time surplus runs out
        remaining_assets_value = future_assets['Capital_Value'].sum()
        
        # Format the zero surplus timeline
        zero_surplus_note = ""
        if years_until_zero_surplus < 100 and years_until_zero_surplus != float('inf'):
            zero_years = int(years_until_zero_surplus)
            zero_months = int((years_until_zero_surplus - zero_years) * 12)
            
            # Add information about remaining assets
            remaining_assets_text = f"At the point you no longer generate a surplus of income over expenses you will need to either reduce expenses or take additional income from remaining assets. Your remaining assets at that point will total {format_currency(remaining_assets_value)}."
            
            if zero_surplus_asset != earliest_depleting_asset:
                zero_surplus_note = f"\n\n**Surplus Impact:** Your annual surplus will drop to zero in approximately **{zero_years} years and {zero_months} months** when '{zero_surplus_asset}' depletes.\n\n{remaining_assets_text}"
            else:
                zero_surplus_note = f"\n\n**Surplus Impact:** Your annual surplus will drop to zero when '{zero_surplus_asset}' depletes in approximately **{zero_years} years and {zero_months} months**.\n\n{remaining_assets_text}"
        
        if min_depletion_years == float('inf'):
            return float('inf'), "Your income covers all expenses! 🎉", f"With your current surplus and asset growth, your finances appear sustainable for the long term.{zero_surplus_note}"
        else:
            years = int(min_depletion_years)
            months = int((min_depletion_years - years) * 12)
            
            detailed = f"While you're currently running a surplus, the earliest asset to deplete will be '{earliest_depleting_asset}' in approximately {years} years and {months} months based on scheduled withdrawals.{zero_surplus_note}"
            
            return min_depletion_years, "Your income covers all expenses! 🎉", detailed
    
    # If in deficit, calculate how long assets will last
    monthly_deficit = abs(monthly_surplus)
    
    # Sum up all asset values
    total_assets = assets_df['Capital_Value'].sum()
    
    # Calculate years until depletion (simple calculation)
    years_until_depletion = total_assets / (monthly_deficit * 12) if monthly_deficit > 0 else float('inf')
    
    if years_until_depletion > 100:
        return float('inf'), "Your assets can cover expenses for over 100 years", "Even with your current deficit, your assets are sufficient to last for generations."
    
    years = int(years_until_depletion)
    months = int((years_until_depletion - years) * 12)
    
    message = f"Your assets will last approximately {years} years and {months} months at current spending levels"
    detailed = f"With a monthly deficit of {format_currency(monthly_deficit)}, your total assets of {format_currency(total_assets)} will be depleted in {years} years and {months} months if no changes are made to income or expenses."
    
    if years < 5:
        message += " ⚠️"
        detailed += " Consider reducing expenses or finding additional income sources to extend financial sustainability."
    
    return years_until_depletion, message, detailed

def main():
    # Initialize session state for navigation and data
    if 'page' not in st.session_state:
        st.session_state.page = 'main'
        st.session_state.tax_details = None
        st.session_state.processed_data = None
        st.session_state.uploaded_file = None
        st.session_state.df = None
        
    # Initialize chat history if it doesn't exist
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

    if st.session_state.page == 'tax_details':
        st.button("← Back to Dashboard", on_click=lambda: setattr(st.session_state, 'page', 'main'))
        show_tax_details(st.session_state.tax_details)
        return

    st.title("Financial Analysis Dashboard")

    # File upload with delete functionality
    col1, col2 = st.columns([3, 1])
    with col1:
        uploaded_file = st.file_uploader("Upload your financial data CSV", type="csv")
    
    # Add a reset button next to the file uploader
    with col2:
        if st.session_state.uploaded_file is not None:
            if st.button("Reset Data", help="Clear uploaded data and reset the dashboard"):
                # Reset all session state variables including chat history
                st.session_state.processed_data = None
                st.session_state.uploaded_file = None
                st.session_state.df = None
                st.session_state.chat_history = []  # Clear the chat history when resetting data
                st.session_state.show_chat = False  # Hide the chat interface after reset
                st.rerun()  # Force page refresh

    if uploaded_file is not None or st.session_state.processed_data is not None:
        try:
            if uploaded_file is not None:
                # New file uploaded, process it
                df = pd.read_csv(uploaded_file)
                processed_data = process_data(df)
                st.session_state.processed_data = processed_data
                st.session_state.uploaded_file = uploaded_file
                st.session_state.df = df  # Store the dataframe in session state
            else:
                # Use existing processed data
                processed_data = st.session_state.processed_data
                # Ensure df is available (load it from session state)
                if st.session_state.df is None and st.session_state.uploaded_file is not None:
                    # Reload the data if necessary
                    df = pd.read_csv(st.session_state.uploaded_file)
                    st.session_state.df = df
                df = st.session_state.df  # Use df from session state

            # Individual income summaries
            st.header("Individual Financial Summary")
            income_summary_table = create_income_summary_table(processed_data['income_summary'])

            # Create table headers
            col1, col2, col3, col4, col5 = st.columns([0.2, 0.3, 0.2, 0.2, 0.1])
            with col1:
                st.markdown("<b>Person</b>", unsafe_allow_html=True)
            with col2:
                st.markdown("<b>Gross Annual Income</b>", unsafe_allow_html=True)
            with col3:
                st.markdown("<b>Estimated Tax</b>", unsafe_allow_html=True)
            with col4:
                st.markdown("<b>Net Annual Income</b>", unsafe_allow_html=True)
            with col5:
                st.markdown("<b>Details</b>", unsafe_allow_html=True)

            # Create table rows
            for row in income_summary_table:
                col1, col2, col3, col4, col5 = st.columns([0.2, 0.3, 0.2, 0.2, 0.1])
                with col1:
                    st.markdown(f"<div class='income-table'>{row['Owner']}</div>", unsafe_allow_html=True)
                with col2:
                    st.markdown(f"<div class='income-table'>{row['Gross Annual Income']}</div>", unsafe_allow_html=True)
                with col3:
                    st.markdown(f"<div class='income-table'>{row['Estimated Tax']}</div>", unsafe_allow_html=True)
                with col4:
                    st.markdown(f"<div class='income-table'>{row['Net Annual Income']}</div>", unsafe_allow_html=True)
                with col5:
                    if st.button("ℹ️", key=f"info_{row['Owner']}", help=f"Show tax calculation details for {row['Owner']}"):
                        st.session_state.page = 'tax_details'
                        st.session_state.tax_details = row['tax_details']
                        st.rerun()

            # Household totals
            st.header("Household Summary")
            col1, col2, col3 = st.columns(3)
            cashflow_summary = create_cashflow_summary(
                processed_data['total_net_income'],
                processed_data['total_expenses']
            )

            # Calculate monthly surplus or deficit
            monthly_surplus = cashflow_summary['Monthly Surplus']
            
            col1.metric("Annual Net Income", cashflow_summary['Total Net Income'])
            col2.metric("Annual Expenses", cashflow_summary['Total Expenses'])
            col3.metric("Annual Surplus/Deficit", cashflow_summary['Annual Surplus/Deficit'])
            
            # Add sustainability callout
            st.markdown("---")
            
            # Calculate sustainability metrics
            assets_df = processed_data['assets']
            years_sustainable, sustainability_message, detailed_message = calculate_sustainability(assets_df, monthly_surplus)
            
            # Format the message in a callout box
            message_color = "#1c7ed6" if years_sustainable > 10 else "#f59f00" if years_sustainable > 5 else "#fa5252"
            
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

            # Add Sankey diagram
            st.subheader("Cash Flow Visualization")
            
            # Create a modified dataframe with adjusted net income values
            if df is not None:  # Add check to ensure df is available
                net_income_df = df.copy()
                
                # For each person, calculate their effective tax rate and apply it to income sources
                for owner, summary in processed_data['income_summary'].items():
                    if owner == 'Joint':
                        continue
                        
                    # Calculate the effective tax rate for this owner
                    gross_income = summary['gross_income']
                    net_income = summary['net_income']
                    
                    if gross_income > 0:
                        effective_tax_rate = 1 - (net_income / gross_income)
                        
                        # Apply the tax rate to each income source for this owner
                        income_mask = (net_income_df['Type'] == 'Income') & (net_income_df['Owner'] == owner)
                        asset_income_mask = (net_income_df['Type'] == 'Asset') & (net_income_df['Owner'] == owner) & (net_income_df['Period_Value'] > 0)
                        
                        # Apply to regular income sources
                        for idx in net_income_df.index[income_mask]:
                            gross_monthly = net_income_df.at[idx, 'Monthly_Value']
                            net_income_df.at[idx, 'Monthly_Value'] = gross_monthly * (1 - effective_tax_rate)
                        
                        # Apply to asset income sources
                        for idx in net_income_df.index[asset_income_mask]:
                            gross_monthly = net_income_df.at[idx, 'Monthly_Value']
                            net_income_df.at[idx, 'Monthly_Value'] = gross_monthly * (1 - effective_tax_rate)

                # Pass the modified dataframe with net income values and the total net income
                st.plotly_chart(
                    create_cashflow_sankey(net_income_df, processed_data['total_net_income']),
                    use_container_width=True
                )
            else:
                # Fallback for when df is not available
                st.plotly_chart(
                    create_cashflow_sankey(processed_data['df'], processed_data['total_net_income']),
                    use_container_width=True
                )

            # Asset projections section
            st.header("Asset Projections")
            years = st.slider("Chart Projection Period (Years)", min_value=1, max_value=30, value=20)  # Changed default from 10 to 20

            projections = calculate_projections(processed_data['df'], years)
            st.plotly_chart(
                create_projection_chart(projections),
                use_container_width=True
            )
            
            # Add the new asset projection table
            st.subheader("Asset Value Forecast Table")
            
            # Create the projection table if available
            if 'asset_projections' in processed_data:
                # Get the asset projections
                asset_projections = processed_data['asset_projections']
                
                # Store original assets for reference in the table creation
                asset_projections['original_assets'] = processed_data['assets']
                
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
            else:
                st.info("Detailed asset projections not available.")

            # Asset depletion analysis
            st.subheader("Asset Depletion Analysis")
            assets = processed_data['assets']

            # Create and display the asset depletion table
            depletion_data = []
            for _, asset in assets.iterrows():
                monthly_value = asset['Monthly_Value']
                depletion_data.append({
                    'Asset': f"{asset['Description']} ({asset['Owner']})",
                    'Starting Value': format_currency(asset['Capital_Value']),
                    'Monthly Withdrawal': format_currency(monthly_value),
                    'Annual Withdrawal': format_currency(monthly_value * 12),
                    'Years until Depletion': f"{asset['Depletion_Years']:.2f}" if asset['Depletion_Years'] < 100 else "Never"
                })

            st.dataframe(
                pd.DataFrame(depletion_data),
                use_container_width=True,
                hide_index=True
            )

            # Data tables
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

            # Add AI Chat Interface with collapsible section
            st.markdown("---")
            
            # Initialize the chat display state if it doesn't exist
            if 'show_chat' not in st.session_state:
                st.session_state.show_chat = False
            
            # Create a button to reveal the chat interface
            col1, col2 = st.columns([2, 1])
            with col1:
                st.subheader("AI Financial Assistant")
            with col2:
                if not st.session_state.show_chat:
                    st.button("Ask Questions About Your Data", 
                              on_click=lambda: setattr(st.session_state, 'show_chat', True),
                              use_container_width=True)
                else:
                    st.button("Hide Assistant", 
                              on_click=lambda: setattr(st.session_state, 'show_chat', False),
                              use_container_width=True)
            
            # Only show the chat interface if the user has clicked to reveal it
            if st.session_state.show_chat:
                render_chat_interface(processed_data)

        except Exception as e:
            st.error(f"Error processing file: {str(e)}")
            # Add more detailed error information in development
            import traceback
            st.error(traceback.format_exc())
    else:
        st.info("Please upload a CSV file to begin the analysis.")

if __name__ == "__main__":
    main()