import streamlit as st
import pandas as pd
import requests
import json
from typing import Dict, List, Any, Optional

def initialize_perplexity_client():
    """Initialize the Perplexity API client with API key from Streamlit secrets."""
    try:
        # Get API key from Streamlit secrets
        perplexity_api_key = st.secrets["perplexity"]["api_key"]
        return perplexity_api_key
    except Exception as e:
        st.error(f"Failed to initialize Perplexity client: {str(e)}")
        st.error("Please ensure you've set up your Perplexity API key in .streamlit/secrets.toml")
        return None

def format_financial_data_for_context(processed_data):
    """Format the financial data into a text context for the AI."""
    context = []
    
    # Basic income and expenses summary
    total_income = processed_data['total_net_income']
    total_expenses = processed_data['total_expenses']
    net_cash_flow = total_income - total_expenses
    
    context.append(f"## Financial Summary")
    context.append(f"Annual Household Income: £{total_income:,.2f}")
    context.append(f"Annual Household Expenses: £{total_expenses:,.2f}")
    context.append(f"Annual Net Cash Flow: £{net_cash_flow:,.2f}")
    
    # Add income details per person
    context.append(f"\n## Individual Income Details")
    for owner, data in processed_data['income_summary'].items():
        context.append(f"\n### {owner}")
        # Fixed: Access tax details nested structure correctly and handle missing keys
        context.append(f"  - Annual Taxable Income: £{data['taxable_income']:,.2f}")
        context.append(f"  - Annual Tax: £{data['tax']:,.2f}")
        context.append(f"  - Annual Net Income: £{data['net_income']:,.2f}")
        
        # Add tax breakdown if available
        if 'tax_details' in data:
            tax_details = data['tax_details']
            context.append("  - Tax Breakdown:")
            context.append(f"    * Tax-free allowance: £{tax_details.get('tax_free_allowance', 0):,.2f}")
            context.append(f"    * Basic rate amount: £{tax_details.get('basic_rate_amount', 0):,.2f}")
            context.append(f"    * Higher rate amount: £{tax_details.get('higher_rate_amount', 0):,.2f}")
            context.append(f"    * Additional rate amount: £{tax_details.get('additional_rate_amount', 0):,.2f}")
    
    # Add household totals
    context.append("\n## Household Summary")
    context.append(f"Total Net Income: £{processed_data.get('total_net_income', 0):,.2f}")
    context.append(f"Total Annual Expenses: £{processed_data.get('total_expenses', 0):,.2f}")
    
    surplus = processed_data.get('total_net_income', 0) - processed_data.get('total_expenses', 0)
    context.append(f"Annual Surplus/Deficit: £{surplus:,.2f}")
    context.append(f"Monthly Surplus/Deficit: £{surplus/12:,.2f}")
    
    # Add asset information with clearer indication of income-generating assets
    assets_df = processed_data.get('assets')
    if assets_df is not None and not assets_df.empty:
        context.append("\n## Assets Information")
        # First list income-generating assets
        income_assets = assets_df[assets_df['Period_Value'] > 0]
        if not income_assets.empty:
            context.append("\n### Income-Generating Assets")
            for _, asset in income_assets.iterrows():
                context.append(f"{asset['Description']} ({asset['Owner']}):")
                context.append(f"  - Current Value: £{asset['Capital_Value']:,.2f}")
                context.append(f"  - Monthly Income Generated: £{asset['Monthly_Value']:,.2f}")
                context.append(f"  - Annual Income Generated: £{asset['Monthly_Value']*12:,.2f}")
                context.append(f"  - Growth Rate: {asset['Growth_Rate']}")
                context.append(f"  - Years until Depletion: {asset['Depletion_Years']:.2f}")
        
        # Then list non-income assets
        non_income_assets = assets_df[assets_df['Period_Value'] <= 0]
        if not non_income_assets.empty:
            context.append("\n### Non-Income Assets")
            for _, asset in non_income_assets.iterrows():
                context.append(f"{asset['Description']} ({asset['Owner']}):")
                context.append(f"  - Current Value: £{asset['Capital_Value']:,.2f}")
                context.append(f"  - Growth Rate: {asset['Growth_Rate']}")
    
    # Add detailed data summaries
    df = processed_data.get('df')
    if df is not None and not df.empty:
        # Income details
        income_df = df[df['Type'] == 'Income']
        if not income_df.empty:
            context.append("\n## Detailed Income Sources")
            for _, row in income_df.iterrows():
                context.append(f"{row['Description']} ({row['Owner']}): £{row['Monthly_Value']:,.2f}/month")
        
        # Expense details
        expense_df = df[df['Type'] == 'Expense']
        if not expense_df.empty:
            context.append("\n## Detailed Expenses")
            for _, row in expense_df.iterrows():
                context.append(f"{row['Description']} ({row['Owner']}): £{row['Monthly_Value']:,.2f}/month")
    
    # Add the detailed asset projections if available
    if 'asset_projections' in processed_data:
        context.append("\n## Asset Projections (Values in £)")
        asset_projections = processed_data['asset_projections']
        
        # Add a table header for the summary view (years 0, 5, 10, 15, 20, 25)
        context.append("\n### Summary Table (Key Years)")
        context.append("\n| Asset | Current | Growth Rate | Year 5 | Year 10 | Year 15 | Year 20 | Year 25 |")
        context.append("| ----- | ------- | ----------- | ------ | ------- | ------- | ------- | ------- |")
        
        # Add each asset's projections to the summary table
        for asset_key, values in asset_projections.items():
            if asset_key != 'years' and asset_key != 'original_assets':
                # Get growth rate from original assets if available
                growth_rate_display = "Varies"
                if asset_key != 'Total Assets' and 'original_assets' in asset_projections:
                    for _, asset in asset_projections['original_assets'].iterrows():
                        asset_name = asset['Description']
                        owner = asset['Owner']
                        if asset_key == f"{asset_name} ({owner})":
                            growth_rate = asset['Growth_Rate']
                            if isinstance(growth_rate, str):
                                growth_rate = float(growth_rate.strip('%').replace(',', '')) / 100
                            growth_rate_display = f"{growth_rate:.1%}"
                            break
                
                # Format values at key intervals for summary table
                intervals = [0, 5, 10, 15, 20, 25]
                interval_values = []
                for year in intervals:
                    if year < len(values):
                        interval_values.append(f"{values[year]:,.0f}")
                    else:
                        interval_values.append("N/A")
                
                # Add row to summary table
                context.append(
                    f"| {asset_key} | £{interval_values[0]} | {growth_rate_display} | £{interval_values[1]} | £{interval_values[2]} | £{interval_values[3]} | £{interval_values[4]} | £{interval_values[5]} |"
                )
        
        # Add explanation of projections
        context.append("\nThese projections account for both asset growth and withdrawals over time.")
        context.append("The calculations are performed annually, compounding interest and subtracting withdrawals.")
        
        # NEW: Add a reference table with precise values for EVERY year (0-25)
        context.append("\n### REFERENCE: Precise Year-by-Year Asset Values")
        context.append("**IMPORTANT: When asked about values for specific years, use the EXACT values below!**")
        
        # Create a more structured table format for each asset by year
        for asset_key, values in asset_projections.items():
            if asset_key != 'years' and asset_key != 'original_assets':
                context.append(f"\n#### {asset_key}")
                context.append("| Year | Value (£) |")
                context.append("| ---- | --------- |")
                
                # Add each year as its own row for clarity
                for year in range(min(len(values), 26)):
                    context.append(f"| {year} | {values[year]:,.0f} |")
    
    return "\n".join(context)

def get_ai_response(
    api_key, 
    financial_data_context: str,
    user_query: str, 
    message_history: Optional[List[Dict[str, str]]] = None
) -> str:
    """
    Get a response from Perplexity API based on the financial data and user query.
    """
    if api_key is None:
        return "Error: Perplexity API key not initialized. Please check your API key configuration."
    
    if not message_history:
        message_history = []
    
    # Create system prompt with financial data context
    system_prompt = f"""You are a helpful financial assistant analyzing personal financial data.
    
You have access to the following financial data:

{financial_data_context}

CRITICAL INSTRUCTION FOR ASSET PROJECTIONS:
1. DO NOT CALCULATE or ESTIMATE asset values yourself - use the pre-calculated exact values
2. DO NOT INTERPOLATE between years - look up the EXACT value in the "Precise Year-by-Year Asset Values" reference tables
3. Every year from 0 to 25 has an exact pre-calculated value in the reference tables
4. Check each reference table carefully for the specific year number requested
5. Double-check the value before responding

Example: If asked "What will Asset X be worth in Year 7?", find the "Asset X" section in the "Precise Year-by-Year Asset Values" reference tables, look for the row with "Year | 7" and use that exact value.

When answering financial questions:
1. For questions about specific years, always reference the exact pre-calculated data
2. For calculations involving multiple years, use the exact values from the reference tables
3. Focus on practical, clear advice based on the numbers provided
4. Explain your reasoning clearly, but don't perform projections yourself

If asked about data beyond year 25 or other data not provided, explain that you only have access to projections up to year 25.
"""
    
    # Format the message history for Perplexity API
    formatted_messages = [{"role": "system", "content": system_prompt}]
    
    # Add conversation history
    for message in message_history:
        formatted_messages.append({"role": message["role"], "content": message["content"]})
    
    # Add the current user query
    formatted_messages.append({"role": "user", "content": user_query})
    
    # Prepare the API request - using the exact same format that worked in the test script
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    data = {
        "model": "sonar",
        "messages": formatted_messages,
        "temperature": 0.7,
        "max_tokens": 2000
    }
    
    try:
        # Make the API request with increased timeout (120 seconds instead of 30)
        with st.spinner("Analyzing financial data..."):
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                data=json.dumps(data),
                timeout=120  # Increased timeout to 120 seconds for complex financial calculations
            )
        
        # Parse the response
        if response.status_code == 200:
            response_json = response.json()
            return response_json['choices'][0]['message']['content']
        else:
            # Enhanced error handling
            error_message = f"API Error (Status {response.status_code})"
            st.error(error_message)
            
            return f"""
I'm sorry, I couldn't process your question at this time due to a connection issue.

Please try one of these options:
1. Break your question into smaller, simpler parts
2. Try again in a few minutes (the service might be temporarily busy)
3. Ask a different question about your financial data
"""
            
    except requests.exceptions.ReadTimeout:
        st.warning("The request took too long to process. This might be due to the complexity of your question.")
        return """
The financial analysis is taking longer than expected. To get a response more quickly:

1. Try asking a simpler question
2. Break your question into smaller parts
3. Specifically mention which part of your financial data you're interested in

For example, instead of asking about multiple scenarios, focus on one specific aspect of your finances.
"""
    except requests.exceptions.RequestException as e:
        st.error(f"Connection Error: {str(e)}")
        return "I'm sorry, I couldn't connect to the financial analysis service. Please check your internet connection and try again."
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        return "I'm sorry, an unexpected error occurred while analyzing your financial data. Please try again with a different question."

def initialize_chat_history():
    """Initialize chat history in session state if it doesn't exist."""
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []

def add_message_to_history(role: str, content: str):
    """Add a message to the chat history in session state."""
    st.session_state.chat_history.append({"role": role, "content": content})

def render_chat_interface(processed_data: Dict):
    """
    Render the chat interface and handle interactions.
    
    Args:
        processed_data: Dictionary containing processed financial data
    """
    st.header("Financial Adviser Discussion")
    
    # Simple user instructions without unnecessary warnings
    st.markdown("""
    Ask questions about your financial data. No information is retained.
    """)
    
    # Initialize chat history
    initialize_chat_history()
    
    # Format financial data for AI context
    financial_data_context = format_financial_data_for_context(processed_data)
    
    # Initialize Perplexity client
    api_key = initialize_perplexity_client()
    
    # Add a button to clear chat history
    if st.session_state.chat_history and st.button("Clear Chat History"):
        st.session_state.chat_history = []
        st.rerun()
    
    # Display chat history
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Get user input
    user_query = st.chat_input("Ask a question about your financial data...")
    
    if user_query:
        # Display user message
        with st.chat_message("user"):
            st.markdown(user_query)
        
        # Add user message to history
        add_message_to_history("user", user_query)
        
        # Get AI response
        with st.chat_message("assistant"):
            message_history = [
                {"role": m["role"], "content": m["content"]} 
                for m in st.session_state.chat_history[:-1]  # Exclude the most recent user message
            ]
            
            response = get_ai_response(api_key, financial_data_context, user_query, message_history)
            st.markdown(response)
        
        # Add assistant response to history
        add_message_to_history("assistant", response)
