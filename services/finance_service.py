"""
Finance Service - Handles financial calculations, projections, and analysis.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, Optional, Tuple, List, Union
import sys

sys.path.append('/workspaces/FinancialAnalysisTool')
from config import FINANCE
from utils.visualizations import format_currency
from services.data_service import DataService

class FinanceService:
    """Service for financial calculations and analysis."""
    
    @staticmethod
    def calculate_projections(df: pd.DataFrame, years: int) -> Dict[str, Any]:
        """
        Calculate individual asset projections over specified years.
        
        Args:
            df: DataFrame with financial data
            years: Number of years to project
            
        Returns:
            Dictionary containing projections for all assets
        """
        months = years * 12
        assets = df[df['Type'] == 'Asset'].copy()

        # Initialize projections dictionary
        projections = {
            'months': list(range(months + 1))
        }

        # Create a unique identifier for each asset combining Description and Owner
        for _, asset in assets.iterrows():
            asset_key = f"{asset['Description']} ({asset['Owner']})"
            monthly_withdrawal = DataService.calculate_monthly_value(asset)
            
            # Parse growth rate
            growth_rate = DataService.parse_growth_rate(asset['Growth_Rate'])
                
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
        
        # Calculate total for all months
        total_values = np.zeros(len(projections['months']))
        for key, values in projections.items():
            if key != 'months':
                total_values += np.array(values[:len(total_values)])
        
        projections['Total Assets'] = total_values.tolist()
        
        return projections
    
    @staticmethod
    def calculate_sustainability(
        assets_df: pd.DataFrame, 
        monthly_surplus: float
    ) -> Tuple[float, str, str]:
        """
        Calculate how long the household can sustain spending with current assets if in deficit.
        
        Args:
            assets_df: DataFrame containing asset information
            monthly_surplus: Monthly surplus amount (negative for deficit)
        
        Returns:
            Tuple of (years, formatted_message, detailed_message)
        """
        # Calculate total monthly income from assets that are being withdrawn
        total_monthly_asset_income = assets_df['Monthly_Value'].sum()
        
        if monthly_surplus >= 0:
            # Handle surplus case - calculating how long until assets deplete
            total_assets = assets_df['Capital_Value'].sum()
            
            # Track asset depletion events and their impact on income
            depletion_events = []
            
            # Find all assets with withdrawals and sort by depletion time
            withdrawal_assets = assets_df[assets_df['Monthly_Value'] > 0].copy()
            
            # If there are no assets being withdrawn, handle differently
            if len(withdrawal_assets) == 0:
                return float('inf'), "Your income covers all expenses! 🎉", "With your current surplus and no asset withdrawals, your finances appear sustainable for the long term."
            
            # Sort assets by depletion years to analyze the timeline of impacts
            withdrawal_assets = withdrawal_assets.sort_values('Depletion_Years')
            
            # Calculate when surplus will drop to zero by tracking cumulative asset depletion
            remaining_surplus = monthly_surplus
            years_until_zero_surplus = float('inf')
            zero_surplus_asset = "None"
            
            # Get the earliest depleting asset with a withdrawal
            min_depletion_years = float('inf')
            earliest_depleting_asset = "None"
            
            # Create a copy of assets_df to simulate growth until surplus runs out
            future_assets = assets_df.copy()
            
            current_time = 0
            for _, asset in withdrawal_assets.iterrows():
                depletion_years = asset.get('Depletion_Years', float('inf'))
                monthly_income = asset['Monthly_Value']
                asset_name = f"{asset['Description']} ({asset['Owner']})"
                
                # Track the earliest depleting asset
                if depletion_years < min_depletion_years and depletion_years < float('inf'):
                    min_depletion_years = depletion_years
                    earliest_depleting_asset = asset_name
                
                # Check if this depletion event would cause surplus to go negative
                if depletion_years < float('inf') and remaining_surplus > 0:
                    remaining_surplus -= monthly_income
                    
                    # If this causes surplus to go negative, this is when the household goes into deficit
                    if remaining_surplus <= 0 and years_until_zero_surplus == float('inf'):
                        years_until_zero_surplus = depletion_years
                        zero_surplus_asset = asset_name
                        
                        # Calculate remaining assets at this point
                        for idx, future_asset in future_assets.iterrows():
                            # Get growth rate as a decimal
                            growth_rate = DataService.parse_growth_rate(future_asset['Growth_Rate'])
                            
                            # Calculate future value of this asset at the time surplus runs out
                            monthly_growth_rate = growth_rate / 12
                            
                            if future_asset['Monthly_Value'] > 0:
                                # For assets with withdrawals, calculate their remaining value
                                # For the asset that causes zero surplus, it will be depleted
                                if future_asset['Description'] == asset['Description'] and future_asset['Owner'] == asset['Owner']:
                                    # This is the asset that gets depleted, value becomes zero
                                    future_assets.at[idx, 'Capital_Value'] = 0
                                else:
                                    # For other assets with withdrawals, calculate remaining value
                                    monthly_withdrawal = future_asset['Monthly_Value']
                                    future_value = future_asset['Capital_Value']
                                    
                                    # Simulate growth and withdrawals for the number of months until surplus runs out
                                    months = int(years_until_zero_surplus * 12)
                                    for _ in range(months):
                                        future_value = future_value * (1 + monthly_growth_rate) - monthly_withdrawal
                                        if future_value <= 0:
                                            future_value = 0
                                            break
                                    
                                    future_assets.at[idx, 'Capital_Value'] = max(0, future_value)
                            else:
                                # For assets without withdrawals, just apply growth
                                future_value = future_asset['Capital_Value'] * ((1 + monthly_growth_rate) ** (years_until_zero_surplus * 12))
                                future_assets.at[idx, 'Capital_Value'] = future_value
            
            # Calculate total remaining assets at the time surplus runs out
            remaining_assets_value = future_assets['Capital_Value'].sum()
            
            # Format the zero surplus timeline
            zero_surplus_note = ""
            if years_until_zero_surplus < 100 and years_until_zero_surplus != float('inf'):
                zero_years = int(years_until_zero_surplus)
                zero_months = int((years_until_zero_surplus - zero_years) * 12)
                
                # Add information about remaining assets
                remaining_assets_text = f"At the point you no longer generate a surplus of income over expenses you will need to either reduce expenses or take additional income from remaining assets. Your remaining assets at that point will total {format_currency(remaining_assets_value)}."
                
                if zero_surplus_asset != earliest_depleting_asset:
                    zero_surplus_note = f"\n\n**Surplus Impact:** Your annual surplus of income over expenses will drop to zero in approximately **{zero_years} years and {zero_months} months** when '{zero_surplus_asset}' runs out.\n\n{remaining_assets_text}"
                else:
                    zero_surplus_note = f"\n\n**Surplus Impact:** Your annual surplus of income over expenses will drop to zero when '{zero_surplus_asset}' runs out in approximately **{zero_years} years and {zero_months} months**.\n\n{remaining_assets_text}"
            
            if min_depletion_years == float('inf'):
                return float('inf'), "Your income covers all expenses! 🎉", f"With your current surplus and asset growth, your finances appear sustainable for the long term.{zero_surplus_note}"
            else:
                years = int(min_depletion_years)
                months = int((min_depletion_years - years) * 12)
                
                detailed = f"You're currently running a monthly surplus. The first asset to run out will be '{earliest_depleting_asset}' in approximately {years} years and {months} months (based on current withdrawals).{zero_surplus_note}"
                
                return min_depletion_years, "Your income covers all expenses! 🎉", detailed
        
        # If in deficit, calculate how long assets will last
        monthly_deficit = abs(monthly_surplus)
        
        # Sum up all asset values
        total_assets = assets_df['Capital_Value'].sum()
        
        # Calculate years until depletion (simple calculation)
        years_until_depletion = total_assets / (monthly_deficit * 12) if monthly_deficit > 0 else float('inf')
        
        # Determine if years are "infinite" or long term based on config
        if years_until_depletion > FINANCE['LONG_TERM_YEARS']:
            return float('inf'), "Your assets can cover expenses for over 100 years", "Even with your current deficit, your assets are sufficient to last for generations."
        
        if years_until_depletion > 100:
            return float('inf'), "Your assets can cover expenses for over 100 years", "Even with your current deficit, your assets are sufficient to last for generations."
        
        years = int(years_until_depletion)
        months = int((years_until_depletion - years) * 12)
        
        message = f"Your assets will last approximately {years} years and {months} months at current spending levels"
        detailed = f"With a monthly deficit of {format_currency(monthly_deficit)}, your total assets of {format_currency(total_assets)} will be depleted in {years} years and {months} months if no changes are made to income or expenses."
        
        if years < 5:
            message += " ⚠️"
            detailed += " Consider reducing expenses or finding additional income sources to extend financial sustainability."
        
        return years_until_depletion, message, detailed
