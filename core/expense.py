"""
Expense model and related calculations.
"""
from typing import Dict, Optional, Any, List, Union
import pandas as pd
from core.models import FinancialItem, FinancialItemType, Frequency

class Expense(FinancialItem):
    """Expense model for regular expense entries"""
    
    def __init__(
        self, 
        description: str,
        owner: str,
        period_value: float,
        frequency: Union[str, Frequency],
        **kwargs
    ):
        super().__init__(
            description=description,
            item_type=FinancialItemType.EXPENSE,
            owner=owner,
            period_value=period_value,
            frequency=frequency,
            taxable=False,  # Expenses are never taxable
            **kwargs
        )

class ExpenseCollection:
    """Collection of expenses for analysis"""
    
    def __init__(self, items: List[Expense] = None):
        self.items = items or []
    
    def add_item(self, item: Expense) -> None:
        """Add expense item to collection"""
        if not isinstance(item, Expense):
            raise TypeError("Item must be an Expense instance")
        self.items.append(item)
    
    def get_by_owner(self, owner: str) -> List[Expense]:
        """Get expense items for a specific owner"""
        return [item for item in self.items if item.owner == owner]
    
    def get_by_category(self, category: str) -> List[Expense]:
        """Get expense items for a specific category"""
        return [item for item in self.items if item.properties.get('Category') == category]
    
    def get_total_monthly(self, owner: Optional[str] = None) -> float:
        """Get total monthly expenses for all or specific owner"""
        if owner:
            items = self.get_by_owner(owner)
        else:
            items = self.items
        
        return sum(item.monthly_value for item in items)
    
    def get_total_annual(self, owner: Optional[str] = None) -> float:
        """Get total annual expenses for all or specific owner"""
        return self.get_total_monthly(owner) * 12
    
    def get_owners(self) -> List[str]:
        """Get list of unique owners"""
        return list(set(item.owner for item in self.items))
    
    def get_categories(self) -> List[str]:
        """Get list of unique categories"""
        categories = set()
        for item in self.items:
            if 'Category' in item.properties:
                categories.add(item.properties['Category'])
        return list(categories)
    
    def calculate_expense_summary(self) -> Dict[str, Dict[str, Any]]:
        """Calculate expense summary by owner"""
        summary = {}
        for owner in self.get_owners():
            summary[owner] = {
                'monthly_expenses': self.get_total_monthly(owner),
                'annual_expenses': self.get_total_annual(owner),
                'expense_count': len(self.get_by_owner(owner))
            }
        
        # Add overall total
        summary['total'] = {
            'monthly_expenses': self.get_total_monthly(),
            'annual_expenses': self.get_total_annual(),
            'expense_count': len(self.items)
        }
        
        return summary
    
    @classmethod
    def from_dataframe(cls, df: pd.DataFrame) -> 'ExpenseCollection':
        """Create expense collection from DataFrame"""
        # Filter for expense type rows
        expense_df = df[df['Type'].str.lower() == 'expense']
        
        # Create expense items
        expense_items = []
        for _, row in expense_df.iterrows():
            # Extract known fields
            expense = Expense(
                description=row['Description'],
                owner=row['Owner'],
                period_value=row['Period_Value'],
                frequency=row['Frequency']
            )
            
            # Add any additional columns as properties
            for col in expense_df.columns:
                if col not in ['Description', 'Type', 'Owner', 'Period_Value', 'Frequency']:
                    expense.properties[col] = row.get(col)
            
            expense_items.append(expense)
        
        return cls(expense_items)
