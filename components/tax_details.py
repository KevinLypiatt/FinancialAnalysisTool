"""
Tax Details component for displaying tax breakdown.
"""
import streamlit as st
from utils.visualizations import format_currency
from core.tax import describe_tax_bands, format_tax_explanation

def render_tax_details(tax_details):
    """
    Display detailed tax breakdown for an individual.
    
    Args:
        tax_details: Dictionary with tax breakdown data
    """
    st.button("← Back to Dashboard", on_click=lambda: setattr(st.session_state, 'page', 'main'))
    
    # Use the tax description from the centralized tax module
    st.markdown(f"""
    ## Individual Tax Calculation Breakdown

    {describe_tax_bands()}
    """)

    # Get the formatted tax explanation
    tax_explanation = format_tax_explanation(tax_details)
    summary = tax_explanation['summary']
    bands = tax_explanation['bands']
    
    st.markdown(f"""
    ### 📊 Taxable Income Breakdown

    **Total Taxable Income:** {format_currency(summary['gross_income'])}

    **Personal Allowance:** {format_currency(summary['tax_free_allowance'])}

    ### 💷 Tax Bands

    **{bands['basic_rate']['description']}:**
    - Amount in band: {format_currency(bands['basic_rate']['amount'])}
    - Tax paid: {format_currency(bands['basic_rate']['tax_paid'])}

    **{bands['higher_rate']['description']}:**
    - Amount in band: {format_currency(bands['higher_rate']['amount'])}
    - Tax paid: {format_currency(bands['higher_rate']['tax_paid'])}

    **{bands['additional_rate']['description']}:**
    - Amount in band: {format_currency(bands['additional_rate']['amount'])}
    - Tax paid: {format_currency(bands['additional_rate']['tax_paid'])}

    ### 📈 Summary
    **Total Tax Due:** {format_currency(summary['total_tax'])}
    **Effective Tax Rate:** {summary['effective_tax_rate']:.2f}%
    """)
