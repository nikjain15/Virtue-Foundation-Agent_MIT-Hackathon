"""
Data Loader - Reads Excel files and loads healthcare facility data

Purpose: Read messy Excel data from Ghana healthcare facilities
Input: Excel file path
Output: Clean pandas DataFrame
"""

import pandas as pd
from pathlib import Path


def load_excel_data(file_path: str) -> pd.DataFrame:
    """
    Load healthcare facility data from Excel file
    
    Args:
        file_path: Path to Excel file (e.g., "data/ghana_facilities.xlsx")
    
    Returns:
        DataFrame with all facility data
    
    Example:
        df = load_excel_data("data/ghana_facilities.xlsx")
        print(df.head())  # Show first 5 rows
    """
    # Check if file exists
    if not Path(file_path).exists():
        raise FileNotFoundError(f"Excel file not found: {file_path}")
    
    # Read Excel file - pandas automatically handles .xlsx format
    print(f"📖 Reading Excel file: {file_path}")
    df = pd.read_excel(file_path, engine='openpyxl')
    
    print(f"✅ Loaded {len(df)} rows and {len(df.columns)} columns")
    print(f"📋 Columns: {list(df.columns)}")
    
    return df


def preview_data(df: pd.DataFrame, num_rows: int = 5):
    """
    Show a preview of the data
    
    Args:
        df: DataFrame to preview
        num_rows: Number of rows to show (default: 5)
    """
    print("\n" + "="*50)
    print("DATA PREVIEW")
    print("="*50)
    print(df.head(num_rows))
    print("\n" + "="*50)
    print("DATA INFO")
    print("="*50)
    print(f"Total rows: {len(df)}")
    print(f"Total columns: {len(df.columns)}")
    print(f"Missing values per column:")
    print(df.isnull().sum())


if __name__ == "__main__":
    # Test the loader (only runs when you execute this file directly)
    print("🧪 Testing data loader...")
    print("⚠️  Please place your Excel file in the 'data/' folder")
    print("⚠️  Then update the filename below")
    
    # Example usage:
    # df = load_excel_data("data/ghana_facilities.xlsx")
    # preview_data(df)
