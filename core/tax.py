"""
Tax calculation module.
Centralizes all tax logic to ensure consistency across the application.
"""

import sys
sys.path.append('/workspaces/FinancialAnalysisTool')
from config import TAX

def get_tax_breakdown(gross_income):
    """
    Calculate detailed tax breakdown for an individual.
    
    Args:
        gross_income (float): Annual gross income
        
    Returns:
        dict: Dictionary with tax calculation breakdown
    """
    tax_free = TAX['PERSONAL_ALLOWANCE']
    basic_rate_limit = TAX['BASIC_RATE_LIMIT']
    higher_rate_limit = TAX['HIGHER_RATE_LIMIT']

    # Personal allowance taper
    actual_tax_free = tax_free
    if gross_income > TAX['PERSONAL_ALLOWANCE_TAPER_THRESHOLD']:
        reduction = min((gross_income - TAX['PERSONAL_ALLOWANCE_TAPER_THRESHOLD']) / 2, tax_free)
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

    # Tax free allowance
    remaining_income -= max(0, actual_tax_free)

    # Basic rate (20%)
    basic_rate_band = min(max(0, basic_rate_limit - actual_tax_free), remaining_income)
    breakdown['basic_rate_amount'] = basic_rate_band
    breakdown['total_tax'] += basic_rate_band * TAX['BASIC_RATE']
    remaining_income -= basic_rate_band

    # Higher rate (40%)
    higher_rate_band = min(max(0, higher_rate_limit - basic_rate_limit), remaining_income)
    breakdown['higher_rate_amount'] = higher_rate_band
    breakdown['total_tax'] += higher_rate_band * TAX['HIGHER_RATE']
    remaining_income -= higher_rate_band

    # Additional rate (45%)
    if remaining_income > 0:
        breakdown['additional_rate_amount'] = remaining_income
        breakdown['total_tax'] += remaining_income * TAX['ADDITIONAL_RATE']

    return breakdown

def calculate_uk_tax(annual_income):
    """
    Calculate UK tax based on current tax bands.
    
    A simplified version that returns just the necessary tax details.
    For full breakdown, use get_tax_breakdown.
    
    Args:
        annual_income (float): Annual income
        
    Returns:
        dict: Dictionary with tax calculation results
    """
    # We can now simply reuse the get_tax_breakdown function
    breakdown = get_tax_breakdown(annual_income)
    
    return {
        'total_tax': breakdown['total_tax'],
        'tax_free_allowance': breakdown['tax_free_allowance'],
        'original_tax_free_allowance': TAX['PERSONAL_ALLOWANCE'],
        'basic_rate_amount': breakdown['basic_rate_amount'],
        'higher_rate_amount': breakdown['higher_rate_amount'],
        'additional_rate_amount': breakdown['additional_rate_amount']
    }

def describe_tax_bands():
    """
    Return a description of the current tax bands.
    
    Returns:
        str: Description of current UK tax bands
    """
    return f"""
    UK Tax Rates (2024/25 tax year for England, Wales, and Northern Ireland)
    - Personal Allowance: 0% on income up to £{TAX['PERSONAL_ALLOWANCE']:,}
    - Basic Rate: {TAX['BASIC_RATE']*100}% on income from £{TAX['PERSONAL_ALLOWANCE']+1:,} to £{TAX['BASIC_RATE_LIMIT']:,}
    - Higher Rate: {TAX['HIGHER_RATE']*100}% on income from £{TAX['BASIC_RATE_LIMIT']+1:,} to £{TAX['HIGHER_RATE_LIMIT']:,}
    - Additional Rate: {TAX['ADDITIONAL_RATE']*100}% on income over £{TAX['HIGHER_RATE_LIMIT']+1:,}
    """

def format_tax_explanation(tax_details):
    """
    Format tax details into a human-readable explanation.
    
    Args:
        tax_details (dict): Tax calculation details from get_tax_breakdown
        
    Returns:
        dict: Formatted explanation strings for each part of the tax calculation
    """
    gross_income = tax_details.get('gross_income', 0)
    tax_free_allowance = tax_details.get('tax_free_allowance', TAX['PERSONAL_ALLOWANCE'])
    total_tax = tax_details.get('total_tax', 0)
    
    # Calculate effective tax rate if gross income is positive
    effective_tax_rate = (total_tax / gross_income) * 100 if gross_income > 0 else 0
    
    return {
        'bands': {
            'basic_rate': {
                'description': f"Basic Rate ({TAX['BASIC_RATE']*100}%)",
                'amount': tax_details['basic_rate_amount'],
                'tax_paid': tax_details['basic_rate_amount'] * TAX['BASIC_RATE']
            },
            'higher_rate': {
                'description': f"Higher Rate ({TAX['HIGHER_RATE']*100}%)",
                'amount': tax_details['higher_rate_amount'],
                'tax_paid': tax_details['higher_rate_amount'] * TAX['HIGHER_RATE']
            },
            'additional_rate': {
                'description': f"Additional Rate ({TAX['ADDITIONAL_RATE']*100}%)",
                'amount': tax_details['additional_rate_amount'],
                'tax_paid': tax_details['additional_rate_amount'] * TAX['ADDITIONAL_RATE']
            }
        },
        'summary': {
            'gross_income': gross_income,
            'tax_free_allowance': tax_free_allowance,
            'total_tax': total_tax,
            'effective_tax_rate': effective_tax_rate,
            'net_income': gross_income - total_tax
        }
    }
