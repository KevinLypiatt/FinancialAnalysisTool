import plotly.graph_objects as go
import plotly.express as px
import numpy as np

def format_currency(value):
    """Format number as UK currency string."""
    return f"£{value:,.2f}"

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

def create_projection_chart(projections):
    """Create line chart showing individual asset projections."""
    fig = go.Figure()

    # Define a custom color palette with more vibrant, high-contrast colors
    # Avoid light colors like yellow that don't show up well
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

    # Add line for each individual asset
    for i, (key, values) in enumerate(projections.items()):
        if key != 'months':
            fig.add_trace(go.Scatter(
                x=years,
                y=values,
                mode='lines',
                name=key,
                line=dict(
                    width=3,  # Keep the increased line width
                    color=custom_colors[i % len(custom_colors)]
                )
            ))

    fig.update_layout(
        title="Individual Asset Value Projections",
        xaxis_title="Years",
        yaxis_title="Asset Value (£)",
        height=600,
        margin=dict(t=50, l=50, r=20, b=50),
        showlegend=True,
        legend=dict(
            yanchor="top",
            y=0.99,
            xanchor="left",
            x=0.01
        ),
        yaxis_tickformat='£,.0f',
        plot_bgcolor='white',  # White background for better contrast
        paper_bgcolor='white'  # White surrounding area
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