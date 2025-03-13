import pandas as pd
import numpy as np

def convert_currency_to_float(value):
    """Convert currency string to float."""
    if isinstance(value, str):
        return float(value.replace('£', '').replace(',', ''))
    return float(value)

def calculate_monthly_value(row):
    """Calculate monthly value based on frequency."""
    period_value = row['Period_Value'] if 'Period_Value' in row else 0
    # Ensure period_value is a float before mathematical operations
    if isinstance(period_value, str):
        period_value = convert_currency_to_float(period_value)
    else:
        period_value = float(period_value)
        
    frequency = row.get('Frequency', 'Monthly')
    
    # Convert frequency to string if it's not already
    if not isinstance(frequency, str):
        frequency = str(frequency)
    
    # Normalize frequency to lowercase for case-insensitive comparison
    freq_lower = frequency.lower()
    
    if 'week' in freq_lower:
        return period_value * 52 / 12
    elif 'month' in freq_lower:
        return period_value
    elif 'year' in freq_lower or 'annual' in freq_lower:
        return period_value / 12
    elif 'invest' in freq_lower:
        return 0
    return period_value  # Default to the original value if frequency not recognized

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

def calculate_detailed_asset_projections(assets_df, years=25):
    """
    Calculate detailed year-by-year projections for each asset over the specified period.
    
    Args:
        assets_df: DataFrame containing asset information
        years: Number of years to project (default: 25)
        
    Returns:
        Dictionary containing annual projections for each asset
    """
    projections = {}
    
    # Initialize with year 0 (current values)
    projections['years'] = list(range(years + 1))
    
    # Process each asset
    for _, asset in assets_df.iterrows():
        asset_key = f"{asset['Description']} ({asset['Owner']})"
        
        # Get initial parameters
        capital = asset['Capital_Value']
        monthly_withdrawal = asset['Monthly_Value']
        annual_withdrawal = monthly_withdrawal * 12
        
        # Convert growth rate from string/percentage to decimal
        growth_rate = asset['Growth_Rate']
        if isinstance(growth_rate, str):
            growth_rate = float(growth_rate.strip('%').replace(',', '')) / 100
        
        # Calculate projection for each year
        yearly_values = [capital]  # Start with current value (year 0)
        
        for year in range(1, years + 1):
            # For each year, calculate the new capital considering growth and withdrawals
            # Using the compound interest formula with regular withdrawals
            if monthly_withdrawal > 0:
                # For assets with withdrawals, simulate month by month
                monthly_growth_rate = growth_rate / 12
                current_capital = capital
                
                for _ in range(12):
                    # Apply monthly growth
                    current_capital *= (1 + monthly_growth_rate)
                    # Subtract withdrawal
                    current_capital -= monthly_withdrawal
                    # Ensure non-negative values
                    current_capital = max(0, current_capital)
                
                capital = current_capital
            else:
                # For assets without withdrawals, use compound interest formula
                capital = capital * (1 + growth_rate) ** 1
            
            yearly_values.append(capital)
            
        # Store this asset's projection
        projections[asset_key] = yearly_values
    
    # Add a "Total Assets" projection
    total_projections = [0] * (years + 1)
    
    # Calculate the sum for each year
    for asset_key, values in projections.items():
        if asset_key != 'years':
            for i, value in enumerate(values):
                total_projections[i] += value
    
    projections['Total Assets'] = total_projections
    
    return projections

def process_data(df):
    """
    Process financial data and calculate key metrics.
    
    Args:
        df: pandas DataFrame with expected columns like Description, Type, Owner, etc.
    
    Returns:
        Dictionary with processed results
    """
    # Make a copy of the original dataframe to avoid modifying the input
    df = df.copy()
    
    # Normalize column names for case-insensitive matching
    column_map = {col.lower(): col for col in df.columns}
    
    # Check for required columns (case-insensitive)
    required_columns = ['description', 'type', 'owner', 'period_value']
    missing_columns = [col for col in required_columns if col not in column_map]
    
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
    
    # Add taxable column if missing with default values
    if 'taxable' not in column_map:
        df['Taxable'] = 'no'
        # Set default to 'yes' for Income items
        df.loc[df[column_map.get('type')].str.lower() == 'income', 'Taxable'] = 'yes'
    else:
        # Ensure Taxable column exists with proper name
        taxable_col = column_map['taxable']
        df['Taxable'] = df[taxable_col]
    
    # Clean currency values
    if 'capital_value' in column_map:
        capital_value_col = column_map['capital_value']
        df['Capital_Value'] = df[capital_value_col].apply(convert_currency_to_float)
    else:
        df['Capital_Value'] = 0.0
        
    if 'period_value' in column_map:
        period_value_col = column_map['period_value']
        df['Period_Value'] = df[period_value_col].apply(convert_currency_to_float)
    else:
        df['Period_Value'] = 0.0
    
    # Ensure standard column names exist for processing
    df['Description'] = df[column_map['description']]
    df['Type'] = df[column_map['type']]
    df['Owner'] = df[column_map['owner']]
    
    # Handle Growth_Rate column
    if 'growth_rate' in column_map:
        df['Growth_Rate'] = df[column_map['growth_rate']]
    else:
        df['Growth_Rate'] = 0
    
    # Handle Frequency column (used in calculate_monthly_value)
    if 'frequency' in column_map:
        df['Frequency'] = df[column_map['frequency']]
    else:
        df['Frequency'] = 'Monthly'  # Default to monthly if missing
    
    # Normalize taxable field to lowercase for comparison
    df['Taxable'] = df['Taxable'].astype(str).str.lower()
    
    # Calculate monthly values
    df['Monthly_Value'] = df.apply(calculate_monthly_value, axis=1)

    # Add an explicit column to indicate if an asset generates income
    assets = df[df['Type'].str.lower() == 'asset'].copy()
    assets['Generates_Income'] = assets['Period_Value'] > 0
    assets['Income_Description'] = assets.apply(
        lambda x: f"Income from {x['Description']}" if x['Period_Value'] > 0 else "N/A", 
        axis=1
    )
    
    # Calculate depletion years for each asset
    assets['Depletion_Years'] = assets.apply(
        lambda x: calculate_depletion_years(
            x['Capital_Value'],
            x['Monthly_Value'],  # Use the already calculated monthly value
            float(str(x['Growth_Rate']).strip('%').replace(',', '')) / 100 if isinstance(x['Growth_Rate'], str) else x['Growth_Rate']
        ),
        axis=1
    )

    # Process income per person
    income_summary = calculate_income_by_owner(df)

    total_net_income = sum(summary['net_income'] for summary in income_summary.values())
    total_expenses = df[df['Type'].str.lower() == 'expense']['Monthly_Value'].sum() * 12

    # Calculate detailed asset projections for 25 years
    asset_projections = calculate_detailed_asset_projections(assets, 25)

    # Return enhanced processed data
    return {
        'income_summary': income_summary,
        'total_net_income': total_net_income,
        'total_expenses': total_expenses,
        'df': df,
        'assets': assets,
        'asset_projections': asset_projections
    }

def calculate_income_by_owner(df):
    """
    Calculate income, taxes, and net income for each person with clearer separation
    between taxable and untaxed income.
    """
    result = {}
    
    # Get all unique owners from income sources
    owners = df[df['Type'].str.lower() == 'income']['Owner'].unique()
    
    for owner in owners:
        # 1. Annual Taxable Income - from both regular income and asset withdrawals
        taxable_income = df[(df['Type'].str.lower() == 'income') & 
                          (df['Owner'] == owner) & 
                          (df['Taxable'] == 'yes')]['Monthly_Value'].sum() * 12
        
        taxable_asset_income = df[(df['Type'].str.lower() == 'asset') & 
                               (df['Owner'] == owner) & 
                               (df['Monthly_Value'] > 0) & 
                               (df['Taxable'] == 'yes')]['Monthly_Value'].sum() * 12
        
        # Total taxable income from all sources
        total_taxable_income = taxable_income + taxable_asset_income
        
        # 2. Estimated Tax - calculated based on UK tax rules
        tax_details = get_tax_breakdown(total_taxable_income)
        tax = tax_details['total_tax']
        
        # 3. Annual Net Income (already calculated as taxable income minus tax)
        net_taxable_income = total_taxable_income - tax
        
        # 4. Annual Untaxed Income - from both regular income and asset withdrawals
        untaxed_income = df[(df['Type'].str.lower() == 'income') & 
                          (df['Owner'] == owner) & 
                          (df['Taxable'] != 'yes')]['Monthly_Value'].sum() * 12
                          
        untaxed_asset_income = df[(df['Type'].str.lower() == 'asset') & 
                               (df['Owner'] == owner) & 
                               (df['Monthly_Value'] > 0) & 
                               (df['Taxable'] != 'yes')]['Monthly_Value'].sum() * 12
        
        total_untaxed_income = untaxed_income + untaxed_asset_income
        
        # 5. Total Annual Income - net taxable income plus untaxed income
        total_annual_income = net_taxable_income + total_untaxed_income
        
        # Store all these values in the result dictionary
        result[owner] = {
            'taxable_income': total_taxable_income,
            'tax': tax,
            'net_taxable_income': net_taxable_income,
            'non_taxable_income': total_untaxed_income,
            'net_income': total_annual_income,  # Total income including taxed and untaxed
            'tax_details': tax_details
        }
    
    # Add joint income if present
    joint_income = df[(df['Type'].str.lower() == 'income') & (df['Owner'] == 'Joint')]['Monthly_Value'].sum() * 12
    joint_asset_income = df[(df['Type'].str.lower() == 'asset') & (df['Owner'] == 'Joint') & (df['Monthly_Value'] > 0)]['Monthly_Value'].sum() * 12
    
    if joint_income > 0 or joint_asset_income > 0:
        total_joint_income = joint_income + joint_asset_income
        result['Joint'] = {
            'taxable_income': 0,  # Joint income isn't directly taxed
            'tax': 0,
            'net_taxable_income': 0,
            'non_taxable_income': total_joint_income,  # All joint income is treated as untaxed
            'net_income': total_joint_income,
            'tax_details': {'gross_income': 0, 'tax_free_allowance': 0, 'total_tax': 0, 
                          'basic_rate_amount': 0, 'higher_rate_amount': 0, 'additional_rate_amount': 0}
        }
    
    return result

def get_tax_breakdown(gross_income):
    """Calculate detailed tax breakdown for an individual."""
    tax_free = 12570
    basic_rate_limit = 50270
    higher_rate_limit = 125140

    # Personal allowance taper
    actual_tax_free = tax_free
    if (gross_income > 100000):
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