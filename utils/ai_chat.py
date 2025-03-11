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

def format_financial_data_for_context(processed_data: Dict) -> str:
    """
    Format the financial data into a string representation for the AI context.
    
    Args:
        processed_data: Dictionary containing processed financial data
        
    Returns:
        String representation of the financial data
    """
    context = []
    
    # Add income summary
    income_summary = processed_data.get('income_summary', {})
    context.append("## Income Summary")
    for owner, data in income_summary.items():
        if owner != 'Joint':
            context.append(f"{owner}:")
            context.append(f"  - Gross Annual Income: £{data['gross_income']:,.2f}")
            context.append(f"  - Annual Tax: £{data['tax']:,.2f}")
            context.append(f"  - Net Annual Income: £{data['net_income']:,.2f}")
    
    # Add household totals
    context.append("\n## Household Summary")
    context.append(f"Total Net Income: £{processed_data.get('total_net_income', 0):,.2f}")
    context.append(f"Total Annual Expenses: £{processed_data.get('total_expenses', 0):,.2f}")
    
    surplus = processed_data.get('total_net_income', 0) - processed_data.get('total_expenses', 0)
    context.append(f"Annual Surplus/Deficit: £{surplus:,.2f}")
    context.append(f"Monthly Surplus/Deficit: £{surplus/12:,.2f}")
    
    # Add asset information
    assets_df = processed_data.get('assets')
    if assets_df is not None and not assets_df.empty:
        context.append("\n## Assets Information")
        for _, asset in assets_df.iterrows():
            context.append(f"{asset['Description']} ({asset['Owner']}):")
            context.append(f"  - Current Value: £{asset['Capital_Value']:,.2f}")
            context.append(f"  - Monthly Withdrawal: £{asset['Monthly_Value']:,.2f}")
            context.append(f"  - Growth Rate: {asset['Growth_Rate']}")
            context.append(f"  - Years until Depletion: {asset['Depletion_Years']:.2f}")
    
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

When answering questions:
1. Use the provided financial data to give accurate answers
2. You excel at financial calculations - show your calculations step by step
3. Ask for clarity on assumptions before undertaking calculations and use a simpler sanity check to cross check your work
4. You can discuss modifications to withdrawals, expenses, or income to achieve different financial goals
5. Focus on practical, clear advice based on the numbers

If asked about data not provided, politely explain that you don't have access to that information.
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
        "temperature": 0.7,  # Using a slightly higher temperature for more natural responses
        "max_tokens": 2000
    }
    
    try:
        # Make the API request without verbose logging in main app
        with st.spinner("Thinking..."):
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                data=json.dumps(data),
                timeout=30
            )
        
        # Parse the response
        if response.status_code == 200:
            response_json = response.json()
            return response_json['choices'][0]['message']['content']
        else:
            # Show error summary without all debugging details
            error_message = f"API Error (Status {response.status_code})"
            st.error(error_message)
            
            # Simple error message for the user
            return f"""
I'm sorry, I couldn't process your question at this time. 
There was an error connecting to the financial analysis service (Status code: {response.status_code}).
Please try again later or check with the system administrator.
"""
            
    except Exception as e:
        st.error(f"Connection Error: {str(e)}")
        return "I'm sorry, I couldn't connect to the financial analysis service. Please check your internet connection and try again."

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
