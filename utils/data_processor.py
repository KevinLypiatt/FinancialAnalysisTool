import pandas as pd
import numpy as np

def convert_currency_to_float(value):
    """Convert currency string to float."""
    if isinstance(value, str):
        return float(value.replace('£', '').replace(',', ''))
    return float(value)

def calculate_monthly_value(row):
    """Calculate monthly value based on frequency."""
    period_value = convert_currency_to_float(row['Period_Value'])

    if row['Frequency'] == 'Weekly':
        return period_value * 52 / 12
    elif row['Frequency'] == 'Monthly':
        return period_value
    elif row['Frequency'] == 'Investment':
        return 0
    return 0

def calculate_depletion_years(capital, monthly_withdrawal, growth_rate=0):
    """
    Calculate years until asset depletes, accounting for growth rate.
    
    Args:
        capital: Initial capital value
        monthly_withdrawal: Monthly withdrawal amount
        growth_rate: Annual growth rate as decimal (e.g., 0.04 for 4%)
    """
    if monthly_withdrawal <= 0:
        return float('inf')
    
    # For zero growth rate, use simple division
    if growth_rate == 0:
        annual_withdrawal = monthly_withdrawal * 12
        return capital / annual_withdrawal if annual_withdrawal > 0 else float('inf')
    
    # For non-zero growth rate, simulate year-by-year
    monthly_growth_rate = growth_rate / 12
    years = 0
    current_capital = capital
    
    # Maximum years to prevent infinite loops for cases where growth > withdrawal
    max_years = 100
    
    while current_capital > 0 and years < max_years:
        # Simulate one year of monthly withdrawals with growth
        for _ in range(12):
            # Apply monthly growth
            current_capital *= (1 + monthly_growth_rate)
            # Subtract withdrawal
            current_capital -= monthly_withdrawal
            
            if current_capital <= 0:
                break
                
        years += 1
    
    return years if years < max_years else float('inf')

def process_data(df):
    """Process the financial data and return summary statistics."""
    # Clean currency values
    df['Capital_Value'] = df['Capital_Value'].apply(convert_currency_to_float)
    df['Period_Value'] = df['Period_Value'].apply(convert_currency_to_float)
    df['Monthly_Value'] = df.apply(calculate_monthly_value, axis=1)

    # Calculate depletion years for each asset
    assets = df[df['Type'] == 'Asset'].copy()
    assets['Depletion_Years'] = assets.apply(
        lambda x: calculate_depletion_years(
            x['Capital_Value'],
            calculate_monthly_value(x),
            float(str(x['Growth_Rate']).strip('%').replace(',', '')) / 100 if isinstance(x['Growth_Rate'], str) else x['Growth_Rate']
        ),
        axis=1
    )

    # Process income per person
    income_summary = {}
    for owner in df['Owner'].unique():
        if owner != 'Joint':
            regular_income = df[(df['Type'] == 'Income') & (df['Owner'] == owner)]['Monthly_Value'].sum() * 12
            asset_income = df[(df['Type'] == 'Asset') & (df['Owner'] == owner) & (df['Period_Value'] > 0)]['Monthly_Value'].sum() * 12

            total_income = regular_income + asset_income
            tax_details = calculate_uk_tax(total_income)
            tax = tax_details['total_tax']
            net_income = total_income - tax

            income_summary[owner] = {
                'gross_income': total_income,
                'tax': tax,
                'net_income': net_income,
                'tax_details': tax_details
            }

    total_net_income = sum(summary['net_income'] for summary in income_summary.values())
    total_expenses = df[df['Type'] == 'Expense']['Monthly_Value'].sum() * 12

    return {
        'income_summary': income_summary,
        'total_net_income': total_net_income,
        'total_expenses': total_expenses,
        'df': df,
        'assets': assets
    }

def calculate_uk_tax(annual_income):
    """Calculate UK tax based on 2024/25 tax bands."""
    tax_free = 12570  # Personal Allowance
    basic_rate_limit = 50270
    higher_rate_limit = 125140

    # Personal allowance taper for income over £100,000
    if annual_income > 100000:
        reduction = min((annual_income - 100000) / 2, tax_free)
        tax_free -= reduction

    # Store the original tax-free allowance for record-keeping
    original_tax_free = 12570
    actual_tax_free = tax_free

    remaining_income = annual_income
    tax = 0

    # Tax free allowance
    remaining_income = max(0, remaining_income - tax_free)

    # Basic rate (20%): £12,571 to £50,270
    basic_rate_band = min(max(0, basic_rate_limit - tax_free), remaining_income)
    tax += basic_rate_band * 0.20
    remaining_income -= basic_rate_band

    # Higher rate (40%): £50,271 to £125,140
    higher_rate_band = min(max(0, higher_rate_limit - basic_rate_limit), remaining_income)
    tax += higher_rate_band * 0.40
    remaining_income -= higher_rate_band

    # Additional rate (45%): Over £125,140
    if remaining_income > 0:
        tax += remaining_income * 0.45

    return {
        'total_tax': tax,
        'tax_free_allowance': actual_tax_free,
        'original_tax_free_allowance': original_tax_free,
        'basic_rate_amount': basic_rate_band,
        'higher_rate_amount': higher_rate_band,
        'additional_rate_amount': remaining_income if remaining_income > 0 else 0
    }

def calculate_projections(df, years):
    """Calculate individual asset projections over specified years."""
    months = years * 12
    assets = df[df['Type'] == 'Asset'].copy()

    # Initialize projections dictionary
    projections = {
        'months': list(range(months + 1))
    }

    # Create a unique identifier for each asset combining Description and Owner
    for _, asset in assets.iterrows():
        asset_key = f"{asset['Description']} ({asset['Owner']})"
        monthly_withdrawal = calculate_monthly_value(asset)
        
        # Convert growth rate from string/percentage to decimal
        growth_rate = asset['Growth_Rate']
        if isinstance(growth_rate, str):
            growth_rate = float(growth_rate.strip('%').replace(',', '')) / 100
            
        monthly_growth_rate = growth_rate / 12
        projections[asset_key] = []

        # Calculate projection for each month
        current_value = asset['Capital_Value']
        projections[asset_key].append(current_value)  # Initial value
        
        for i in range(1, months + 1):
            # Apply monthly growth/interest
            current_value *= (1 + monthly_growth_rate)
            
            # Subtract withdrawal
            current_value -= monthly_withdrawal
            
            # Store the value (minimum 0)
            projections[asset_key].append(max(0, current_value))
    
    return projections