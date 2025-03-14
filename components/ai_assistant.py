"""
AI Assistant component for interacting with financial data.
"""
import streamlit as st
from utils.ai_chat import render_chat_interface

def render_ai_assistant(processed_data):
    """
    Render AI assistant interface.
    
    Args:
        processed_data: Dictionary with processed financial data
    """
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
