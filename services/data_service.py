"""
Data Service - Handles data loading, validation, and preprocessing.
"""

import pandas as pd
import logging
from typing import Dict, Any, Optional, Tuple, List
import sys

sys.path.append('/workspaces/FinancialAnalysisTool')
from config import DATA, FINANCE
from core.models import normalize_column_names
from core.tax import get_tax_breakdown, calculate_uk_tax
from core.income import Income, IncomeSource
from core.expense import Expense, ExpenseCollection

# Configure logging
logger = logging.getLogger(__name__)

class DataService:
    """Service for loading and processing financial data."""
    
    @staticmethod
    def load_csv(file_obj) -> pd.DataFrame:
        """
        Load data from CSV file.
        
        Args:
            file_obj: File-like object containing CSV data
            
        Returns:
            DataFrame with loaded data
        """
        try:
            # Reset position to start of file
            file_obj.seek(0)
            
            # Try standard CSV reading first
            try:
                df = pd.read_csv(file_obj)
            except Exception as e:
                logger.warning(f"Standard csv parsing failed: {str(e)}, trying with utf-8 encoding")
                file_obj.seek(0)
                df = pd.read_csv(file_obj, encoding='utf-8', engine='python')
            
            logger.info(f"Successfully loaded CSV with shape: {df.shape}")
            return df
            
        except Exception as e:
            logger.error(f"Error loading CSV: {str(e)}")
            raise ValueError(f"Unable to load CSV file: {str(e)}")
    
    @staticmethod
    def validate_data(df: pd.DataFrame) -> pd.DataFrame:
        """
        Validate loaded data and normalize column names.
        
        Args:
            df: DataFrame with raw data
            
        Returns:
            Normalized DataFrame
        """
        # Normalize column names
        df = normalize_column_names(df)
        
        # Check for required columns
        required_columns = DATA['REQUIRED_COLUMNS']
        column_map = {col.lower(): col for col in df.columns}
        
        missing_columns = [col for col in required_columns if col not in column_map]
        if missing_columns:
            raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")
            
        # Convert currency values to float
        for col in ['Capital_Value', 'Period_Value']:
            if col in df.columns:
                df[col] = df[col].apply(DataService.convert_currency_to_float)
                
        # Normalize Taxable field
        if 'Taxable' in df.columns:
            df['Taxable'] = df['Taxable'].astype(str).str.lower()
            
        return df
    
    @staticmethod
    def convert_currency_to_float(value):
        """Convert currency string to float."""
        if isinstance(value, str):
            try:
                return float(value.replace('£', '').replace(',', ''))
            except ValueError:
                return 0.0
        return float(value)
        
    @staticmethod
    def process_data(df: pd.DataFrame) -> Dict[str, Any]:
        """
        Process and calculate all financial metrics from loaded data.
        
        Args:
            df: DataFrame with validated financial data
            
        Returns:
            Dictionary with processed results
        """
        # Make a clean copy
        df = df.copy()
        
        # Normalize and validate data
        df = DataService.validate_data(df)
        
        # Calculate monthly values
        df['Monthly_Value'] = df.apply(DataService.calculate_monthly_value, axis=1)

        # Extract different item types
        incomes = IncomeSource.from_dataframe(df)
        expenses = ExpenseCollection.from_dataframe(df)
        
        # Extract assets and calculate depletion years
        assets = df[df['Type'].str.lower() == 'asset'].copy()
        assets['Generates_Income'] = assets['Period_Value'] > 0
        assets['Income_Description'] = assets.apply(
            lambda x: f"Income from {x['Description']}" if x['Period_Value'] > 0 else "N/A", 
            axis=1
        )
        
        # Calculate depletion years for each asset
        assets['Depletion_Years'] = assets.apply(
            lambda x: DataService.calculate_depletion_years(
                x['Capital_Value'],
                x['Monthly_Value'],
                DataService.parse_growth_rate(x['Growth_Rate'])
            ),
            axis=1
        )

        # Process income summary
        income_summary = incomes.calculate_income_summary()
        
        # Calculate expense summary
        expense_summary = expenses.calculate_expense_summary()
        
        # Get total values
        total_net_income = sum(summary['net_income'] for summary in income_summary.values())
        total_expenses = expense_summary['total']['annual_expenses']

        # Calculate asset projections
        asset_projections = DataService.calculate_detailed_asset_projections(
            assets, FINANCE['DEFAULT_PROJECTION_YEARS']
        )

        # Return comprehensive processed data
        return {
            'income_summary': income_summary,
            'expense_summary': expense_summary,
            'total_net_income': total_net_income,
            'total_expenses': total_expenses,
            'df': df,
            'assets': assets,
            'asset_projections': asset_projections
        }
        
    @staticmethod
    def calculate_monthly_value(row):
        """Calculate monthly value based on frequency."""
        period_value = row['Period_Value'] if 'Period_Value' in row else 0
        
        # Ensure period_value is a float
        if isinstance(period_value, str):
            period_value = DataService.convert_currency_to_float(period_value)
        else:
            period_value = float(period_value)
            
        frequency = row.get('Frequency', FINANCE['DEFAULT_FREQUENCY'])
        
        # Convert frequency to lowercase string for comparison
        if not isinstance(frequency, str):
            frequency = str(frequency)
        
        freq_lower = frequency.lower()
        
        if 'week' in freq_lower:
            return period_value * 52 / 12
        elif 'month' in freq_lower:
            return period_value
        elif 'year' in freq_lower or 'annual' in freq_lower:
            return period_value / 12
        elif 'invest' in freq_lower:
            return 0
        return period_value  # Default to the original value
    
    @staticmethod
    def parse_growth_rate(growth_rate):
        """Parse growth rate from string or number."""
        if isinstance(growth_rate, str):
            try:
                return float(growth_rate.strip('%').replace(',', '')) / 100
            except ValueError:
                return 0.0
        return float(growth_rate)
    
    @staticmethod
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
        max_years = FINANCE['MAX_DEPLETION_YEARS']
        
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
    
    @staticmethod
    def calculate_detailed_asset_projections(assets_df, years=None):
        """
        Calculate detailed year-by-year projections for each asset over the specified period.
        
        Args:
            assets_df: DataFrame containing asset information
            years: Number of years to project (default from config if None)
            
        Returns:
            Dictionary containing annual projections for each asset
        """
        # Use default from config if years not specified
        if years is None:
            years = FINANCE['DEFAULT_PROJECTION_YEARS']
            
        projections = {}
        
        # Initialize with year 0 (current values)
        projections['years'] = list(range(years + 1))
        
        # Process each asset
        for _, asset in assets_df.iterrows():
            asset_key = f"{asset['Description']} ({asset['Owner']})"
            
            # Get initial parameters
            capital = asset['Capital_Value']
            monthly_withdrawal = asset['Monthly_Value']
            
            # Parse growth rate
            growth_rate = DataService.parse_growth_rate(asset['Growth_Rate'])
            
            # Calculate projection for each year
            yearly_values = [capital]  # Start with current value (year 0)
            
            for year in range(1, years + 1):
                # For each year, calculate the new capital considering growth and withdrawals
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
