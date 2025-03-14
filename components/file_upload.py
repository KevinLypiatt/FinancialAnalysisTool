"""
File Upload component for handling file uploads and data processing.
"""
import streamlit as st
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def render_file_uploader():
    """
    Render file upload interface and handle file processing.
    
    Returns:
        tuple: (uploaded_file, df) where df is None if no file was uploaded
    """
    # File upload with delete functionality
    col1, col2 = st.columns([3, 1])
    
    with col1:
        try:
            # Add more robust error handling for file uploads
            uploaded_file = st.file_uploader("Upload your financial data CSV", type="csv", 
                                           accept_multiple_files=False, 
                                           key="csv_uploader")
            
            # Log information about the uploaded file
            if uploaded_file is not None:
                logger.info(f"File uploaded: {uploaded_file.name}, size: {uploaded_file.size} bytes")
                # Force buffer position to start to ensure proper reading
                uploaded_file.seek(0)
        except Exception as e:
            logger.error(f"Error during file upload: {str(e)}")
            logger.error("Exception details:", exc_info=True)
            st.error(f"Error processing uploaded file: {str(e)}")
            uploaded_file = None
    
    # Add a reset button next to the file uploader
    with col2:
        if st.session_state.get('uploaded_file') is not None:
            if st.button("Reset Data", help="Clear uploaded data and reset the dashboard"):
                # Reset all session state variables including chat history
                st.session_state.processed_data = None
                st.session_state.uploaded_file = None
                st.session_state.df = None
                st.session_state.chat_history = []  # Clear the chat history when resetting data
                st.session_state.show_chat = False  # Hide the chat interface after reset
                st.rerun()  # Force page refresh
    
    return uploaded_file
