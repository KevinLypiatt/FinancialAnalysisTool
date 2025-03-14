"""
Core data models for financial analysis.
"""
import pandas as pd
from enum import Enum
from typing import Dict, List, Optional, Union, Any
import sys
sys.path.append('/workspaces/FinancialAnalysisTool')
from config import FINANCE
from utils.visualizations import format_currency

class FinancialItemType(Enum):
    """Types of financial items"""
    INCOME = "Income"
    EXPENSE = "Expense"
    ASSET = "Asset"

class Frequency(Enum):
    """Frequency of financial items"""
    WEEKLY = "Weekly"
    MONTHLY = "Monthly"
    QUARTERLY = "Quarterly"
    ANNUALLY = "Annually" 
    INVESTMENT = "Investment"
    
    @classmethod
    def from_string(cls, value: str) -> 'Frequency':
        """Convert string to Frequency enum"""
        value = value.lower()
        if 'week' in value:
            return cls.WEEKLY
        elif 'month' in value:
            return cls.MONTHLY
        elif 'quarter' in value:
            return cls.QUARTERLY
        elif 'year' in value or 'annual' in value:
            return cls.ANNUALLY
        elif 'invest' in value:
            return cls.INVESTMENT
        else:
            return cls.MONTHLY  # Default

    def get_monthly_factor(self) -> float:
        """Return factor to convert to monthly value"""
        if self == Frequency.WEEKLY:
            return 52 / 12  # Weekly to monthly
        elif self == Frequency.MONTHLY:
            return 1.0
        elif self == Frequency.QUARTERLY:
            return 1 / 3  # Quarterly to monthly
        elif self == Frequency.ANNUALLY:
            return 1 / 12  # Annual to monthly
        elif self == Frequency.INVESTMENT:
            return 0.0  # Investments don't provide regular income
        return 1.0  # Default

class FinancialItem:
    """Base class for all financial items"""
    
    def __init__(
        self, 
        description: str,
        item_type: FinancialItemType,
        owner: str,
        period_value: float,
        frequency: Union[str, Frequency],
        taxable: bool = False,
        capital_value: float = 0.0,
        growth_rate: float = 0.0,
        **kwargs
    ):
        self.description = description
        self.item_type = item_type if isinstance(item_type, FinancialItemType) else FinancialItemType(item_type)
        self.owner = owner
        self.period_value = float(period_value)
        
        # Convert frequency string to enum
        if isinstance(frequency, str):
            self.frequency = Frequency.from_string(frequency)
        else:
            self.frequency = frequency
        
        # Convert taxable string to bool if needed
        if isinstance(taxable, str):
            self.taxable = taxable.lower() in ('yes', 'true', '1', 'y')
        else:
            self.taxable = bool(taxable)
        
        self.capital_value = float(capital_value)
        
        # Handle growth rate as string or float
        if isinstance(growth_rate, str) and '%' in growth_rate:
            self.growth_rate = float(growth_rate.strip('%').replace(',', '')) / 100
        else:
            self.growth_rate = float(growth_rate)
        
        # Additional properties from kwargs
        self.properties = kwargs
    
    @property
    def monthly_value(self) -> float:
        """Calculate monthly value based on period value and frequency"""
        return self.period_value * self.frequency.get_monthly_factor()
    
    @property
    def annual_value(self) -> float:
        """Calculate annual value"""
        return self.monthly_value * 12
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'Description': self.description,
            'Type': self.item_type.value,
            'Owner': self.owner,
            'Period_Value': self.period_value,
            'Frequency': self.frequency.value,
            'Taxable': 'yes' if self.taxable else 'no',
            'Capital_Value': self.capital_value,
            'Growth_Rate': self.growth_rate,
            'Monthly_Value': self.monthly_value,
            **self.properties
        }
    
    def __str__(self) -> str:
        """String representation"""
        main_attrs = [
            f"{self.item_type.value}: {self.description}",
            f"Owner: {self.owner}",
            f"Monthly Value: {format_currency(self.monthly_value)}"
        ]
        return ", ".join(main_attrs)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'FinancialItem':
        """Create instance from dictionary"""
        # Extract known attributes
        item_type = data.get('Type', 'Income')
        description = data.get('Description', '')
        owner = data.get('Owner', '')
        period_value = data.get('Period_Value', 0)
        frequency = data.get('Frequency', 'Monthly')
        taxable = data.get('Taxable', 'no')
        capital_value = data.get('Capital_Value', 0)
        growth_rate = data.get('Growth_Rate', 0)
        
        # Get additional properties (exclude known ones)
        known_keys = {'Type', 'Description', 'Owner', 'Period_Value', 'Frequency', 
                      'Taxable', 'Capital_Value', 'Growth_Rate', 'Monthly_Value'}
        extra_props = {k: v for k, v in data.items() if k not in known_keys}
        
        # Create appropriate subclass based on type
        if item_type.lower() == 'income':
            from core.income import Income
            return Income(description, owner, period_value, frequency, taxable, **extra_props)
        elif item_type.lower() == 'expense':
            from core.expense import Expense
            return Expense(description, owner, period_value, frequency, **extra_props)
        elif item_type.lower() == 'asset':
            from core.asset import Asset
            return Asset(description, owner, capital_value, period_value, frequency, taxable, growth_rate, **extra_props)
        else:
            return cls(description, item_type, owner, period_value, frequency, taxable, capital_value, growth_rate, **extra_props)

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> List['FinancialItem']:
        """Create instances from DataFrame"""
        items = []
        for _, row in df.iterrows():
            items.append(cls.from_dict(row.to_dict()))
        return items

def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize column names in DataFrame to standard format"""
    # Make a copy to avoid modifying the original
    df = df.copy()
    
    # Create mapping of lowercase column names to original names
    column_map = {col.lower(): col for col in df.columns}
    
    # Define standard column names and their lowercase versions
    standard_columns = {
        'description': 'Description',
        'type': 'Type',
        'owner': 'Owner',
        'period_value': 'Period_Value',
        'frequency': 'Frequency',
        'taxable': 'Taxable',
        'capital_value': 'Capital_Value', 
        'growth_rate': 'Growth_Rate'
    }
    
    # Replace columns with standard names where they exist
    for lower_name, std_name in standard_columns.items():
        if lower_name in column_map:
            # Column exists with different case, rename it
            df = df.rename(columns={column_map[lower_name]: std_name})
        elif std_name not in df.columns:
            # Column doesn't exist, add it with default value
            if std_name == 'Type':
                df[std_name] = 'Income'  # Default type
            elif std_name == 'Frequency':
                df[std_name] = FINANCE['DEFAULT_FREQUENCY']
            elif std_name == 'Taxable':
                # Default taxable: yes for income, no for others
                df[std_name] = df['Type'].apply(lambda x: 'yes' if x.lower() == 'income' else 'no')
            elif std_name in ['Capital_Value', 'Growth_Rate', 'Period_Value']:
                df[std_name] = 0.0
            else:
                df[std_name] = ''
    
    return df
