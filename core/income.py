"""
Income model and related calculations.
"""
from typing import Dict, Optional, Any, List, Union
import pandas as pd
from core.models import FinancialItem, FinancialItemType, Frequency
from core.tax import get_tax_breakdown

class Income(FinancialItem):
    """Income model for regular income entries"""
    
    def __init__(
        self, 
        description: str,
        owner: str,
        period_value: float,
        frequency: Union[str, Frequency],
        taxable: bool = True,
        **kwargs
    ):
        super().__init__(
            description=description,
            item_type=FinancialItemType.INCOME,
            owner=owner,
            period_value=period_value,
            frequency=frequency,
            taxable=taxable,
            **kwargs
        )
    
    @property
    def is_taxable(self) -> bool:
        """Return if income is taxable"""
        return self.taxable
    
    @property 
    def after_tax_monthly_value(self, effective_tax_rate: float = 0.0) -> float:
        """Calculate after-tax monthly value"""
        if self.is_taxable:
            return self.monthly_value * (1 - effective_tax_rate)
        return self.monthly_value

class IncomeSource:
    """Collection of income sources for analysis"""
    
    def __init__(self, items: List[Income] = None):
        self.items = items or []
    
    def add_item(self, item: Income) -> None:
        """Add income item to collection"""
        if not isinstance(item, Income):
            raise TypeError("Item must be an Income instance")
        self.items.append(item)
    
    def get_by_owner(self, owner: str) -> List[Income]:
        """Get income items for a specific owner"""
        return [item for item in self.items if item.owner == owner]
    
    def get_total_monthly(self, owner: Optional[str] = None) -> float:
        """Get total monthly income for all or specific owner"""
        if owner:
            items = self.get_by_owner(owner)
        else:
            items = self.items
        
        return sum(item.monthly_value for item in items)
    
    def get_total_annual(self, owner: Optional[str] = None) -> float:
        """Get total annual income for all or specific owner"""
        return self.get_total_monthly(owner) * 12
    
    def get_taxable_annual(self, owner: str) -> float:
        """Get annual taxable income for a specific owner"""
        taxable_income = sum(
            item.annual_value for item in self.get_by_owner(owner)
            if item.is_taxable
        )
        return taxable_income
    
    def get_nontaxable_annual(self, owner: str) -> float:
        """Get annual non-taxable income for a specific owner"""
        nontaxable_income = sum(
            item.annual_value for item in self.get_by_owner(owner)
            if not item.is_taxable
        )
        return nontaxable_income
    
    def calculate_tax(self, owner: str) -> Dict[str, Any]:
        """Calculate taxes for a specific owner"""
        taxable_income = self.get_taxable_annual(owner)
        tax_details = get_tax_breakdown(taxable_income)
        tax = tax_details['total_tax']
        
        return {
            'taxable_income': taxable_income,
            'tax': tax,
            'net_taxable_income': taxable_income - tax,
            'non_taxable_income': self.get_nontaxable_annual(owner),
            'tax_details': tax_details
        }
    
    def get_owners(self) -> List[str]:
        """Get list of unique owners"""
        return list(set(item.owner for item in self.items))
    
    def calculate_income_summary(self) -> Dict[str, Dict[str, Any]]:
        """Calculate income summary for all owners"""
        summary = {}
        for owner in self.get_owners():
            tax_info = self.calculate_tax(owner)
            
            # Calculate total annual income (after tax + non-taxable)
            net_income = tax_info['net_taxable_income'] + tax_info['non_taxable_income']
            tax_info['net_income'] = net_income
            
            summary[owner] = tax_info
        
        return summary
    
    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> 'IncomeSource':
        """Create income source from DataFrame"""
        # Filter for income type rows
        income_df = df[df['Type'].str.lower() == 'income']
        
        # Create income items
        income_items = []
        for _, row in income_df.iterrows():
            income = Income(
                description=row['Description'],
                owner=row['Owner'],
                period_value=row['Period_Value'],
                frequency=row['Frequency'],
                taxable=row['Taxable']
            )
            income_items.append(income)
        
        return cls(income_items)
