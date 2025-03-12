import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import pandas as pd
import logging
import traceback

# Configure logging
logger = logging.getLogger(__name__)

def format_currency(value):
    """Format number as UK currency string."""
    try:
        return f"£{value:,.2f}"
    except Exception as e:
        logger.error(f"Error formatting currency: {str(e)}")
        return f"£{value}"

def get_tax_breakdown(gross_income):
    """Calculate detailed tax breakdown for an individual."""
    tax_free = 12570
    basic_rate_limit = 50270
    higher_rate_limit = 125140

    # Personal allowance taper
    actual_tax_free = tax_free
    if gross_income > 100000:
        reduction = min((gross_income - 100000) / 2, tax_free)
        actual_tax_free -= reduction

    remaining_income = gross_income
    breakdown = {
        'gross_income': gross_income,
        'tax_free_allowance': actual_tax_free,
        'basic_rate_amount': 0,
        'higher_rate_amount': 0,
        'additional_rate_amount': 0,
        'total_tax': 0
    }

    # Tax free
    remaining_income -= max(0, actual_tax_free)

    # Basic rate (20%)
    basic_rate_band = min(max(0, basic_rate_limit - actual_tax_free), remaining_income)
    breakdown['basic_rate_amount'] = basic_rate_band
    breakdown['total_tax'] += basic_rate_band * 0.20
    remaining_income -= basic_rate_band

    # Higher rate (40%)
    higher_rate_band = min(max(0, higher_rate_limit - basic_rate_limit), remaining_income)
    breakdown['higher_rate_amount'] = higher_rate_band
    breakdown['total_tax'] += higher_rate_band * 0.40
    remaining_income -= higher_rate_band

    # Additional rate (45%)
    if remaining_income > 0:
        breakdown['additional_rate_amount'] = remaining_income
        breakdown['total_tax'] += remaining_income * 0.45

    return breakdown

def create_income_summary_table(income_summary):
    """Create a formatted table of income and tax per person."""
    rows = []
    for owner, summary in income_summary.items():
        if owner != 'Joint':  # Exclude Joint entries
            # Use the tax details directly from the income_summary if available
            tax_details = summary.get('tax_details', get_tax_breakdown(summary['gross_income']))
            
            # Make sure gross_income is included in tax_details
            if 'gross_income' not in tax_details:
                tax_details['gross_income'] = summary['gross_income']
            
            rows.append({
                'Owner': owner,
                'Gross Annual Income': format_currency(summary['gross_income']),
                'Estimated Tax': format_currency(summary['tax']),
                'Net Annual Income': format_currency(summary['net_income']),
                'tax_details': tax_details
            })
    return rows

def create_total_assets_chart(projections):
    """Create line chart showing only the total assets (net worth) over time."""
    try:
        logger.info("Creating total assets chart")
        fig = go.Figure()

        # Convert months to years for x-axis
        years = [m/12 for m in projections['months']]
        
        # If Total Assets key doesn't exist, calculate it from all other assets
        if "Total Assets" not in projections:
            logger.info("Total Assets key not found, calculating from individual assets")
            # Get all asset keys (excluding 'months' and any other non-asset keys)
            asset_keys = [key for key in projections.keys() if key != 'months' and key != 'original_assets']
            
            # Initialize total_values with zeros
            total_values = np.zeros(len(projections['months']))
            
            # Sum up all asset values
            for key in asset_keys:
                total_values += np.array(projections[key])
                
            # Add Total Assets to the projections dictionary
            projections["Total Assets"] = total_values.tolist()
            logger.info(f"Created Total Assets with first value: {total_values[0]}")
        
        # Get total values
        total_values = projections["Total Assets"]
        
        # Add the total assets line
        fig.add_trace(go.Scatter(
            x=years,
            y=total_values,
            mode='lines',
            name="Total Assets",
            line=dict(
                width=4,  # Slightly thicker for emphasis
                color='#2c3e50'  # Dark blue for the total line
            ),
            fill='tozeroy',  # Add area fill below the line
            fillcolor='rgba(44, 62, 80, 0.1)'  # Light fill color
        ))
        
        # Add markers at key year points (0, 5, 10, 15, 20, 25)
        year_markers = [0, 5, 10, 15, 20, 25]
        marker_years = []
        marker_values = []
        
        for year in year_markers:
            if year * 12 < len(projections['months']):
                marker_years.append(year)
                month_index = year * 12
                marker_values.append(total_values[month_index])
        
        # Add markers at key years
        fig.add_trace(go.Scatter(
            x=marker_years,
            y=marker_values,
            mode='markers',
            name='Key Years',
            marker=dict(
                size=10,
                color='#2c3e50',
                line=dict(width=2, color='white')
            ),
            hovertemplate='Year %{x}<br>Value: £%{y:,.0f}<extra></extra>'
        ))

        fig.update_layout(
            title="Net Worth Projection",
            xaxis_title="Years",
            yaxis_title="Total Asset Value (£)",
            height=350,  # Smaller height than the detailed chart
            margin=dict(t=50, l=50, r=20, b=20),
            showlegend=False,  # No legend needed for a single line
            yaxis_tickformat='£,.0f',
            yaxis=dict(rangemode='tozero'),  # Force y-axis to start at zero
            plot_bgcolor='white',
            paper_bgcolor='white',
            hovermode='x unified'
        )
        
        # Add gridlines for better readability
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')

        return fig
        
    except Exception as e:
        logger.error(f"Error creating total assets chart: {str(e)}")
        logger.error(traceback.format_exc())
        # Return a fallback figure with an error message
        fig = go.Figure()
        fig.add_annotation(
            x=0.5, y=0.5,
            text=f"Error creating chart: {str(e)}",
            showarrow=False,
            font=dict(size=14, color="red")
        )
        return fig

def create_projection_chart(projections, selected_assets=None):
    """
    Create line chart showing individual asset projections.
    
    Args:
        projections: Dictionary containing asset projections
        selected_assets: List of asset names to display (None for all assets)
    """
    fig = go.Figure()

    # Define a custom color palette with more vibrant, high-contrast colors
    custom_colors = [
        '#1f77b4',  # Strong blue
        '#d62728',  # Brick red
        '#2ca02c',  # Forest green
        '#9467bd',  # Purple
        '#8c564b',  # Brown
        '#e377c2',  # Pink
        '#7f7f7f',  # Gray
        '#17becf',  # Cyan
        '#ff7f0e',  # Dark orange
        '#1a5276',  # Navy blue
        '#a93226',  # Maroon
        '#196f3d'   # Dark green
    ]

    # Convert months to years for x-axis
    years = [m/12 for m in projections['months']]

    # Collect all available asset keys (excluding 'months' and 'Total Assets')
    all_asset_keys = [key for key in projections.keys() 
                     if key != 'months' and key != 'Total Assets' and key != 'original_assets']
    
    # Normalize selected_assets handling to ensure consistent behavior
    if selected_assets is None or not isinstance(selected_assets, list) or len(selected_assets) == 0:
        # Always treat empty/None as an empty selection
        valid_selected_assets = []
    else:
        # Filter out any assets that don't exist in the data
        valid_selected_assets = [asset for asset in selected_assets if asset in all_asset_keys]
    
    # Add line for each selected asset (using valid selections only)
    for i, key in enumerate(all_asset_keys):
        if key in valid_selected_assets:
            fig.add_trace(go.Scatter(
                x=years,
                y=projections[key],
                mode='lines',
                name=key,
                line=dict(
                    width=3,
                    color=custom_colors[i % len(custom_colors)]
                )
            ))

    # Update layout with empty placeholder when no assets selected
    if not valid_selected_assets:
        fig.add_annotation(
            x=0.5,
            y=0.5,
            text="No assets selected. Use the checkboxes above to select assets to display.",
            showarrow=False,
            font=dict(size=14, color="#7f7f7f"),
            xref="paper",
            yref="paper"
        )
    
    fig.update_layout(
        title="Individual Asset Value Projections",
        xaxis_title="Years",
        yaxis_title="Asset Value (£)",
        height=500,
        margin=dict(t=50, l=50, r=20, b=50),
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="right",
            x=0.99
        ),
        yaxis_tickformat='£,.0f',
        plot_bgcolor='white',
        paper_bgcolor='white'
    )
    
    # Add gridlines for better readability
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='lightgray')

    return fig

def create_cashflow_summary(total_net_income, total_expenses):
    """Create summary metrics for household cashflow."""
    monthly_net = total_net_income / 12
    monthly_expenses = total_expenses / 12
    monthly_surplus = monthly_net - monthly_expenses

    return {
        'Total Net Income': format_currency(total_net_income),
        'Total Expenses': format_currency(total_expenses),
        'Annual Surplus/Deficit': format_currency(total_net_income - total_expenses),
        'Monthly Surplus': monthly_surplus
    }

def create_cashflow_sankey(df, total_net_income=None):
    """
    Create a Sankey diagram showing cash flows between income, expenses, and assets.
    Uses a central 'bucket' approach: all income flows into a central pot, then out to expenses.
    
    Args:
        df: DataFrame containing financial data with net income values
        total_net_income: Optional total net income value to display (for consistency with dashboard)
    """
    # Process data for Sankey diagram
    income_data = df[df['Type'] == 'Income']
    expense_data = df[df['Type'] == 'Expense']
    asset_data = df[df['Type'] == 'Asset']
    
    # Get withdrawals from assets (assets with positive Monthly_Value)
    asset_withdrawals = asset_data[asset_data['Monthly_Value'] > 0]

    # Create nodes for the diagram
    income_sources = [f"{row['Description']} ({row['Owner']})" for _, row in income_data.iterrows()]
    expense_categories = [f"{row['Description']} ({row['Owner']})" for _, row in expense_data.iterrows()]
    asset_categories = [f"{row['Description']} ({row['Owner']})" for _, row in asset_withdrawals.iterrows()]
    
    # Add a central "Household Budget" node between income and expense
    central_node = ["Household Budget"]
    
    # Create the complete nodes list - order matters for the layout
    all_nodes = income_sources + asset_categories + central_node + expense_categories
    
    # Create node indices dictionary
    node_indices = {node: idx for idx, node in enumerate(all_nodes)}
    central_index = node_indices["Household Budget"]

    # Calculate totals for display
    regular_income_monthly = sum(row['Monthly_Value'] for _, row in income_data.iterrows())
    asset_withdrawals_monthly = sum(row['Monthly_Value'] for _, row in asset_withdrawals.iterrows())
    expenses_monthly = sum(row['Monthly_Value'] for _, row in expense_data.iterrows())
    surplus_monthly = (regular_income_monthly + asset_withdrawals_monthly) - expenses_monthly
    
    # Annual values
    annual_regular_income = regular_income_monthly * 12
    annual_asset_income = asset_withdrawals_monthly * 12
    annual_expenses = expenses_monthly * 12
    
    # If specific net income provided, adjust calculations
    if total_net_income is not None:
        annual_total_income = total_net_income
    else:
        annual_total_income = annual_regular_income + annual_asset_income
        
    annual_surplus = annual_total_income - annual_expenses
    
    # Prepare data for the links (connections between nodes)
    source_indices = []
    target_indices = []
    link_values = []
    
    # 1. Connect all income sources to central node
    for _, income in income_data.iterrows():
        income_node = f"{income['Description']} ({income['Owner']})"
        monthly_value = income['Monthly_Value']
        
        if monthly_value > 0:
            source_indices.append(node_indices[income_node])
            target_indices.append(central_index)
            link_values.append(monthly_value)
    
    # 2. Connect all asset withdrawals to central node
    for _, asset in asset_withdrawals.iterrows():
        asset_node = f"{asset['Description']} ({asset['Owner']})"
        monthly_value = asset['Monthly_Value']
        
        if monthly_value > 0:
            source_indices.append(node_indices[asset_node])
            target_indices.append(central_index)
            link_values.append(monthly_value)
    
    # 3. Connect central node to all expenses
    for _, expense in expense_data.iterrows():
        expense_node = f"{expense['Description']} ({expense['Owner']})"
        monthly_value = expense['Monthly_Value']
        
        if monthly_value > 0:
            source_indices.append(central_index)
            target_indices.append(node_indices[expense_node])
            link_values.append(monthly_value)

    # Create the Sankey diagram
    fig = go.Figure(data=[go.Sankey(
        arrangement="freeform",  # Allow more natural arrangement
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=all_nodes,
            # Color scheme: green for income, blue for central, red for expenses, purple for assets
            color=[
                "#2ecc71" if i < len(income_sources) else  # Green for income
                "#9b59b6" if i < len(income_sources) + len(asset_categories) else  # Purple for assets
                "#3498db" if i == len(income_sources) + len(asset_categories) else  # Blue for central node
                "#e74c3c"  # Red for expenses
                for i in range(len(all_nodes))
            ]
        ),
        link=dict(
            source=source_indices,
            target=target_indices,
            value=link_values,
            color="rgba(169, 169, 169, 0.3)"
        )
    )])

    # Add annotations for the totals with accurate values
    fig.add_annotation(
        x=0.15,
        y=-0.12,
        text=f"Total Net Income: {format_currency(annual_total_income)}",  # Changed from "Total Annual Income"
        showarrow=False,
        font=dict(size=14, color="#2ecc71"),
        xref="paper",
        yref="paper"
    )
    
    fig.add_annotation(
        x=0.5,
        y=-0.12,
        text=f"Total Annual Expenses: {format_currency(annual_expenses)}",
        showarrow=False,
        font=dict(size=14, color="#e74c3c"),
        xref="paper",
        yref="paper"
    )
    
    fig.add_annotation(
        x=0.85,
        y=-0.12,
        text=f"Annual Surplus: {format_currency(annual_surplus)}",
        showarrow=False,
        font=dict(size=14, color="#3498db"),
        xref="paper",
        yref="paper"
    )

    fig.update_layout(
        title="Household Cash Flow",
        font_size=10,
        height=650,
        margin=dict(t=50, l=50, r=50, b=80),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )

    return fig

def create_asset_projection_table(asset_projections, intervals=[5, 10, 15, 20]):
    """
    Create a table showing asset projections at specified year intervals.
    
    Args:
        asset_projections: Dictionary containing asset projections
        intervals: List of year intervals to display (default: [5, 10, 15, 20])
        
    Returns:
        DataFrame containing the projection table
    """
    # Create a list to hold table rows
    table_data = []
    
    # Process each asset
    for asset_key, values in asset_projections.items():
        if asset_key != 'years' and asset_key != 'original_assets':
            # Get current value (year 0)
            current_value = values[0]
            
            # Determine if this is an asset or the total
            is_total = (asset_key == 'Total Assets')
            
            # Calculate growth rate and withdrawal rate
            if not is_total:
                # Extract asset name and owner from the key
                parts = asset_key.split(' (')
                asset_name = parts[0]
                owner = parts[1].rstrip(')')
                
                # Find this asset in the original data
                asset_found = False
                for _, asset in asset_projections.get('original_assets', pd.DataFrame()).iterrows():
                    if asset['Description'] == asset_name and asset['Owner'] == owner:
                        growth_rate = asset['Growth_Rate']
                        if isinstance(growth_rate, str):
                            growth_rate = float(growth_rate.strip('%').replace(',', '')) / 100
                            growth_rate_display = f"{growth_rate:.1%}"
                        else:
                            growth_rate_display = f"{growth_rate:.1%}"
                        
                        monthly_withdrawal = asset['Monthly_Value']
                        annual_withdrawal = monthly_withdrawal * 12
                        annual_withdrawal_rate = annual_withdrawal / current_value if current_value > 0 else 0
                        withdrawal_rate_display = f"{annual_withdrawal_rate:.1%}" if annual_withdrawal_rate > 0 else "0.0%"
                        
                        asset_found = True
                        break
                
                if not asset_found:
                    growth_rate_display = "N/A"
                    withdrawal_rate_display = "N/A"
            else:
                growth_rate_display = "Varies"
                withdrawal_rate_display = "Varies"
            
            # Get values at each interval
            interval_values = []
            for year in intervals:
                if year < len(values):
                    interval_values.append(values[year])
                else:
                    # If projection doesn't go this far, use the last available value
                    interval_values.append(values[-1])
            
            # Create a row for this asset
            row = {
                'Asset': asset_key,
                'Current Value': current_value,
                'Growth Rate': growth_rate_display,
                'Withdrawal Rate': withdrawal_rate_display
            }
            
            # Add interval values
            for i, year in enumerate(intervals):
                row[f'Year {year}'] = interval_values[i]
            
            table_data.append(row)
    
    # Create the DataFrame
    table_df = pd.DataFrame(table_data)
    
    # No longer adding 'Total Portfolio' row since we already have 'Total Assets'
    
    # Sort so that Total Assets appears at the bottom
    if 'Asset' in table_df.columns and not table_df.empty:
        # Create a custom sort key
        def sort_key(asset_name):
            if asset_name == 'Total Assets':
                return 2  # Last
            else:
                return 1  # Regular assets
                
        # Apply the custom sort
        table_df['sort_order'] = table_df['Asset'].apply(sort_key)
        table_df = table_df.sort_values('sort_order').drop('sort_order', axis=1)
    
    return table_df

# Replace the Dash-specific mobile visualization functions with Streamlit-compatible versions
def create_single_asset_chart(projections, asset_name):
    """Create a small line chart for a single asset with fixed 20-year scale."""
    fig = go.Figure()
    
    # Only show data up to 20 years (240 months) if available
    max_months = min(240, len(projections['months']))
    years = [m/12 for m in projections['months'][:max_months]]
    
    if asset_name in projections:
        values = projections[asset_name][:max_months]
        
        fig.add_trace(go.Scatter(
            x=years,
            y=values,
            mode='lines',
            name=asset_name,
            line=dict(width=2),
            fill='tozeroy'
        ))
    
    # Simplified layout for small chart
    fig.update_layout(
        margin=dict(t=10, l=10, r=10, b=10),
        height=120,
        showlegend=False,
        xaxis=dict(
            showticklabels=False,
            showgrid=False,
            range=[0, 20]  # Fixed 20-year scale
        ),
        yaxis=dict(
            showticklabels=False,
            showgrid=False
        ),
        plot_bgcolor='white'
    )
    
    return fig

# Replace Dash HTML components with Streamlit compatible function
def create_asset_card_data(asset_name, asset_data, projections):
    """
    Create data for a single asset card for small screen display.
    
    Args:
        asset_name: Name of the asset
        asset_data: Dictionary of asset data (current value, growth rate, etc.)
        projections: Dictionary with projection data for this asset
        
    Returns:
        Dictionary with asset data ready for display
    """
    return {
        'name': asset_name,
        'current_value': format_currency(asset_data["Current Value"]),
        'growth_rate': asset_data["Growth Rate"],
        'withdrawal_rate': asset_data["Withdrawal Rate"],
        'chart': create_single_asset_chart(projections, asset_name)
    }

def create_simplified_sankey(df, total_net_income, total_expenses):
    """Create simplified Sankey diagram for small screens showing just totals."""
    fig = go.Figure(data=[go.Sankey(
        arrangement="snap",
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color="black", width=0.5),
            label=["Total Income", "Household Budget", "Total Expenses"],
            color=["#2ecc71", "#3498db", "#e74c3c"]
        ),
        link=dict(
            source=[0, 1],  # Total Income → Budget → Expenses
            target=[1, 2],
            value=[total_net_income/12, total_expenses/12],  # Using monthly values for better scale
            color=["rgba(46, 204, 113, 0.3)", "rgba(231, 76, 60, 0.3)"]
        )
    )])
    
    surplus = total_net_income - total_expenses
    
    fig.update_layout(
        title="Simplified Cash Flow",
        height=300,
        margin=dict(t=30, l=10, r=10, b=60),
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
    )
    
    # Add annotation for surplus/deficit
    fig.add_annotation(
        x=0.5, 
        y=-0.1,
        text=f"Annual Surplus/Deficit: {format_currency(surplus)}",
        showarrow=False,
        font=dict(size=14, color="#3498db" if surplus >= 0 else "#e74c3c"),
        xref="paper",
        yref="paper"
    )
    
    return fig