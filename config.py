"""
Configuration settings for the Financial Analysis Tool.
Centralizes constants, tax rates, and other parameters.
"""

# UK Tax Configuration (2024/25 tax year)
TAX = {
    'PERSONAL_ALLOWANCE': 12570,
    'BASIC_RATE_LIMIT': 50270,
    'HIGHER_RATE_LIMIT': 125140,
    'PERSONAL_ALLOWANCE_TAPER_THRESHOLD': 100000,
    'BASIC_RATE': 0.20,
    'HIGHER_RATE': 0.40,
    'ADDITIONAL_RATE': 0.45,
}

# Financial calculation defaults
FINANCE = {
    'DEFAULT_FREQUENCY': 'Monthly',
    'MAX_DEPLETION_YEARS': 100,
    'DEFAULT_PROJECTION_YEARS': 25,
    'PROJECTION_INTERVALS': [5, 10, 15, 20],
    'LONG_TERM_YEARS': 100,  # Years considered "infinite" or "never" depleting
}

# Visualization settings
VISUALIZATION = {
    'COLORS': {
        'INCOME': '#2ecc71',      # Green
        'EXPENSE': '#e74c3c',     # Red
        'ASSET': '#9b59b6',       # Purple
        'CENTRAL': '#3498db',     # Blue
        'ASSET_COLORS': [
            '#1f77b4',  # Strong blue
            '#d62728',  # Brick red
            '#2ca02c',  # Forest green
            '#9467bd',  # Purple
            '#8c564b',  # Brown
            '#e377c2',  # Pink
            '#7f7f7f',  # Gray
            '#17becf',  # Cyan
            '#ff7f0e',  # Dark orange
            '#1a5276',  # Navy blue
            '#a93226',  # Maroon
            '#196f3d'   # Dark green
        ]
    },
    'CHART_HEIGHTS': {
        'SANKEY': 650,
        'PROJECTION': 500,
        'TOTAL_ASSETS': 350,
        'MINI_CHART': 120,
        'SIMPLE_SANKEY': 300
    },
    'SUSTAINABILITY_COLORS': {
        'GOOD': "#1c7ed6",    # Blue for good sustainability (>10 years)
        'WARNING': "#f59f00", # Yellow/orange for warning (5-10 years)
        'DANGER': "#fa5252"   # Red for danger (<5 years)
    }
}

# Currency configuration
CURRENCY = {
    'SYMBOL': '£',
    'FORMAT': '{symbol}{value:,.2f}'  # UK pounds with 2 decimal places
}

# Data processing settings
DATA = {
    'REQUIRED_COLUMNS': ['description', 'type', 'owner', 'period_value']
}
