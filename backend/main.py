from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import tempfile, os
from typing import List
import math

app = FastAPI() 

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://know-you-eta.vercel.app",
        "https://know-you-m73y.onrender.com"

    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

# -----------------------------
# Helpers
# -----------------------------
def read_file(file: UploadFile):
    ext = file.filename.split(".")[-1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
        tmp.write(file.file.read())
        path = tmp.name
    try:
        if ext in ["xlsx", "xls"]:
            df = pd.read_excel(path,
                engine="openpyxl")
        elif ext == "csv":
            df = pd.read_csv(path)
        elif ext == "pdf":
            import tabula
            dfs = tabula.read_pdf(path, pages="all", multiple_tables=True)
            df = pd.concat(dfs, ignore_index=True) if dfs else None
        else:
            df = None
    finally:
        os.remove(path)
    return df
 
def safe_float(val):
    try:
        f = float(val)
        if math.isinf(f) or math.isnan(f):
            return 0
        return f
    except:
        return 0

# -----------------------------
# Column identification
# -----------------------------
UNIT_PRICE_SYNONYMS = ["unit price", "rate", "list price", "price per", "fee", "charge", "tag price","sale price","sales"]
COST_SYNONYMS = ["unit cost","cost per unit", "cogs", "cost of goods sold", "standard cost", "production cost", "rate"]
QUANTITY_SYNONYMS = ["quantity", "qty", "sold", "amount","units sold","units"]

def find_column(df: pd.DataFrame, keywords: List[str]):
    for col in df.columns:
        col_lower = col.lower()
        for kw in keywords:
            if kw in col_lower:
                return col
    return None

def is_numeric_column(col, sample_size=5, threshold=0.6):
    col_sample = col.dropna().head(sample_size).astype(str)

    def check_numeric(val):
        # strip symbols but keep digits, . and -
        cleaned = "".join(c for c in val if c.isdigit() or c in ".-")
        # if any letter in original value, not numeric
        if any(c.isalpha() for c in val):
            return False
        return cleaned.replace(".", "", 1).replace("-", "", 1).isdigit() if cleaned else False

    numeric_count = col_sample.apply(check_numeric).sum()
    return numeric_count / max(1, len(col_sample)) >= threshold

def clean_numeric(col):
    return col.astype(str).str.replace(r"[^\d\.\-]", "", regex=True).replace("", 0).astype(float)

# -----------------------------
# API
# -----------------------------
@app.post("/analyze")
async def analyze(files: List[UploadFile] = File(...), top_n: int = 10):
    combined_df = pd.DataFrame()

    # Read all files
    for file in files:
        df = read_file(file)
        if df is not None and not df.empty:
            combined_df = pd.concat([combined_df, df], ignore_index=True)

    if combined_df.empty:
        return {"error": "No readable data found"}

    # Identify key columns
    unit_price_col = find_column(combined_df, UNIT_PRICE_SYNONYMS)
    cost_col = find_column(combined_df, COST_SYNONYMS)
    quantity_col = find_column(combined_df, QUANTITY_SYNONYMS)

    # Identify numeric columns
    numeric_input_cols = []
    for col in combined_df.columns:
        if col not in [unit_price_col, cost_col, quantity_col] and is_numeric_column(combined_df[col]):
            numeric_input_cols.append(col)
            combined_df[col] = clean_numeric(combined_df[col])
    # Clean -->unit, cost, quantity columns
    for col in [unit_price_col, cost_col, quantity_col]:
        if col and col in combined_df.columns:
            combined_df[col] = clean_numeric(combined_df[col])

    # Replace NaN values ONLY in partially-filled columns        
    for col in combined_df.columns:
    # Numeric columns → fill partial NaN with 0
        if pd.api.types.is_numeric_dtype(combined_df[col]):
            if combined_df[col].notna().any() and combined_df[col].isna().any():
                combined_df[col] = combined_df[col].fillna(0)

        # Object / string columns → fill partial NaN with "none"
        elif pd.api.types.is_object_dtype(combined_df[col]):
            if combined_df[col].notna().any() and combined_df[col].isna().any():
                combined_df[col] = combined_df[col].fillna("none")

    import re

    def calculate_financials_dynamic(df: pd.DataFrame, unit_price_col=None, cost_col=None, quantity_col=None):
        """
        Dynamically calculate Revenue, Cost, and Profit only for periods present in the DataFrame.
        - Only calculates if column exists and is all NaN.
        - Detects periods from existing columns automatically.
        """
        # Detect periods from column names (e.g., Daily Revenue, Weekly Cost, Monthly Profit)
        pattern = re.compile(r"(\w+)\s+(Revenue|Cost|Profit)", re.IGNORECASE)
        periods = set()

        for col in df.columns:
            match = pattern.match(col) 
            if match:
                periods.add(match.group(1).title())  # Capture 'Daily', 'Weekly', etc.
        profit_in_table = any('profit' in col.lower() for col in combined_df.columns)

        if periods:
            for period in periods:
                # create a generic column name
                revenue_col = f"{period} Revenue"
                cost_col_name = f"{period} Cost"
                profit_col = f"{period} Profit"
                # Revenue calculation: only if column exists and is all NaN
                if unit_price_col and quantity_col and revenue_col in df.columns and df[revenue_col].isna().all():
                    df[revenue_col] = df[unit_price_col] * df[quantity_col]
                # Cost calculation: only if column exists and is all NaN 
                if cost_col and quantity_col and cost_col_name in df.columns and df[cost_col_name].isna().all():
                    df[cost_col_name] = df[cost_col] * df[quantity_col]
                # Profit calculation: only if column exists and is all NaN
                
                revenue_exists = revenue_col in df.columns and not df[revenue_col].isna().all()
                cost_exists = cost_col_name in df.columns and not df[cost_col_name].isna().all()
                if revenue_exists and cost_exists:
                    df[profit_col] = df[revenue_col].fillna(0) - df[cost_col_name].fillna(0)
                elif revenue_exists:
                    df[profit_col] = df[revenue_col].fillna(0)   
                elif cost_exists:
                    df[profit_col] = -df[cost_col_name].fillna(0)
                    # else: leave Profit as NaN

        elif profit_in_table==False:
            
            unit_exists = unit_price_col in df.columns and not df[unit_price_col].isna().all()
            cost_exists = cost_col in df.columns and not df[cost_col].isna().all()
            qty_exists = quantity_col in df.columns and not df[quantity_col].isna().all()
            profit_col="profit" # create a generic profit column name
            if unit_exists and cost_exists and qty_exists:
                df[profit_col] = (df[unit_price_col].fillna(0) - df[cost_col].fillna(0)) * df[quantity_col].fillna(0)

            elif unit_exists and qty_exists:
                df[profit_col] = df[unit_price_col].fillna(0) * df[quantity_col].fillna(0)

            elif cost_exists and qty_exists:
                df[profit_col] = -(df[cost_col].fillna(0) * df[quantity_col].fillna(0))
            elif unit_exists :
                df[profit_col] = df[unit_price_col].fillna(0)

        return df
    combined_df = calculate_financials_dynamic(
    combined_df,
    unit_price_col=unit_price_col,
    cost_col=cost_col,
    quantity_col=quantity_col
)
    def drop_all_nan_columns(df):
        """
        Removes columns that are entirely NaN
        """
        return df.dropna(axis=1, how="all")

    combined_df = drop_all_nan_columns(combined_df) 
    
    # Column totals for numeric columns
    numeric_cols = [c for c in combined_df.columns if is_numeric_column(combined_df[c])]
    column_totals = {col: float(combined_df[col].sum()) for col in numeric_cols}
 
    # -----------------------------
    # Top N profitable rows
    # -----------------------------
    top_items = []
    profit_in_table =  next(
            (col for col in combined_df.columns if 'profit' in col.lower()),
            None
        )
    if profit_in_table in combined_df.columns:
        top_items = combined_df.sort_values(by=profit_in_table, ascending=False).head(top_n).to_dict(orient="records")
    return {
        "rows": len(combined_df), 
        "columns": combined_df.columns.tolist(),
        "column_totals": column_totals,
        "top_items": top_items
    }

 

