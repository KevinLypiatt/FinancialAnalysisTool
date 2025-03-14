"""
AI Service - Handles all AI-related functionality and API integrations.
"""

import requests
import json
import logging
import streamlit as st
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)

class AIService:
    """Service for AI-related functionality and API integrations."""
    
    @staticmethod
    def initialize_perplexity_client() -> Optional[str]:
        """
        Initialize the Perplexity API client with API key from Streamlit secrets.
        
        Returns:
            API key if successful, None otherwise
        """
        try:
            # Get API key from Streamlit secrets
            perplexity_api_key = st.secrets["perplexity"]["api_key"]
            return perplexity_api_key
        except Exception as e:
            logger.error(f"Failed to initialize Perplexity client: {str(e)}")
            return None
    
    @staticmethod
    def format_financial_data_for_context(
        processed_data: Dict[str, Any]
    ) -> str:
        """
        Format the financial data into a text context for the AI.
        
        Args:
            processed_data: Dictionary with processed financial data
            
        Returns:
            Formatted context string
        """
        # Format financial data similar to the original function in ai_chat.py
        # This will be a more structured and comprehensive version
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
        
        # Add more detailed context sections here...
        # Include asset information, projections, etc.
        
        # Just a sample for brevity - in the full implementation, include all the sections 
        # from the original format_financial_data_for_context function
        
        return "\n".join(context)
    
    @staticmethod
    def get_ai_response(
        api_key: str, 
        financial_data_context: str,
        user_query: str, 
        message_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """
        Get response from Perplexity API based on financial data and user query.
        
        Args:
            api_key: Perplexity API key
            financial_data_context: Formatted financial data context
            user_query: User's question
            message_history: Optional list of previous messages
            
        Returns:
            AI response text
        """
        if api_key is None:
            return "Error: AI service not configured properly. Please check API key."
        
        if not message_history:
            message_history = []
        
        # Create system prompt with financial data context
        system_prompt = f"""You are a helpful financial assistant analyzing personal financial data.
        
You have access to the following financial data:

{financial_data_context}

When answering financial questions:
1. Focus on practical, clear advice based on the numbers provided
2. Explain your reasoning clearly
3. If asked about data not provided, explain the limitations

For asset projections, reference the exact pre-calculated values and avoid making your own projections.
"""
        
        # Format the message history for the API
        formatted_messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history
        for message in message_history:
            formatted_messages.append({"role": message["role"], "content": message["content"]})
        
        # Add the current user query
        formatted_messages.append({"role": "user", "content": user_query})
        
        # Prepare the API request
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
            # Make the API request with increased timeout (120 seconds)
            response = requests.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                data=json.dumps(data),
                timeout=120
            )
            
            # Parse the response
            if response.status_code == 200:
                response_json = response.json()
                return response_json['choices'][0]['message']['content']
            else:
                logger.error(f"API Error (Status {response.status_code}): {response.text}")
                return f"I'm sorry, I couldn't process your question (Error {response.status_code})."
                
        except requests.exceptions.ReadTimeout:
            logger.warning("Request timed out")
            return "The financial analysis is taking longer than expected. Please try a simpler question."
        except requests.exceptions.RequestException as e:
            logger.error(f"Request exception: {str(e)}")
            return f"Connection error: {str(e)}"
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return f"An unexpected error occurred: {str(e)}"
