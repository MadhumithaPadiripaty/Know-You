from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import tempfile, os
from typing import List
import math

app = FastAPI() 

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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
                # print("-->1",col)
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
    # print("-->2 ",col_sample,"-->3",numeric_count)
    return numeric_count / max(1, len(col_sample)) >= threshold

def clean_numeric(col):
    # print("-->5",col)
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
    # print ("-->6",numeric_input_cols)
    # Clean -->unit, cost, quantity columns
    for col in [unit_price_col, cost_col, quantity_col]:
        if col and col in combined_df.columns:
            combined_df[col] = clean_numeric(combined_df[col])
            print("!!",combined_df[col])

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
        # print ("-->0.1",periods,cost_col) 
        if periods:
            for period in periods:
                revenue_col = f"{period} Revenue"
                cost_col_name = f"{period} Cost"
                profit_col = f"{period} Profit"
                # print("---1.2",df[revenue_col].isna())
                # Revenue calculation: only if column exists and is all NaN
                if unit_price_col and quantity_col and revenue_col in df.columns and df[revenue_col].isna().all():
                    df[revenue_col] = df[unit_price_col] * df[quantity_col]
                    print ("-->1",df[revenue_col]) 
                # Cost calculation: only if column exists and is all NaN 
                # print("---1.2",df[cost_col_name].isna())
                if cost_col and quantity_col and cost_col_name in df.columns and df[cost_col_name].isna().all():
                    df[cost_col_name] = df[cost_col] * df[quantity_col]
                    print ("-->2",df[cost_col_name]) 
                # Profit calculation: only if column exists and is all NaN
                
                revenue_exists = revenue_col in df.columns and not df[revenue_col].isna().all()
                cost_exists = cost_col_name in df.columns and not df[cost_col_name].isna().all()
                print("!!!",revenue_exists)
                print("!!!",cost_exists)
                if revenue_exists and cost_exists:
                    df[profit_col] = df[revenue_col].fillna(0) - df[cost_col_name].fillna(0)
                elif revenue_exists:
                    df[profit_col] = df[revenue_col].fillna(0)   
                elif cost_exists:
                    df[profit_col] = -df[cost_col_name].fillna(0)
                    # else: leave Profit as NaN
                    # print ("-->3",df[profit_col]) 

        elif "Profit" not in df.columns and (revenue_col or cost_col_name):
            revenue_exists = revenue_col in df.columns and not df[revenue_col].isna().all()
            cost_exists = cost_col_name in df.columns and not df[cost_col_name].isna().all()
            print("!!!",revenue_exists)
            print("!!!",cost_exists)
            if revenue_exists and cost_exists:
                df[profit_col] = df[revenue_col].fillna(0) - df[cost_col_name].fillna(0)
            elif revenue_exists:
                df[profit_col] = df[revenue_col].fillna(0)   
            elif cost_exists:
                df[profit_col] = -df[cost_col_name].fillna(0)
        return df
    
    combined_df = calculate_financials_dynamic(
    combined_df,
    unit_price_col=unit_price_col,
    cost_col=cost_col,
    quantity_col=quantity_col
)
    print(unit_price_col)
    def drop_all_nan_columns(df):
        """
        Removes columns that are entirely NaN
        """
        return df.dropna(axis=1, how="all")

    combined_df = drop_all_nan_columns(combined_df)
    


    print ("-->8",combined_df)  


    # Column totals for numeric columns
    numeric_cols = [c for c in combined_df.columns if is_numeric_column(combined_df[c])]
    column_totals = {col: float(combined_df[col].sum()) for col in numeric_cols}
 
    # print('-->7',numeric_cols)
    # print('-->8',column_totals)
    # -----------------------------
    # Top N profitable rows
    # -----------------------------
    top_items = []
    if "Profit" in combined_df.columns:
        top_items = combined_df.sort_values(by="Profit", ascending=False).head(top_n).to_dict(orient="records")
    print("-->9",top_items)
    return {
        "rows": len(combined_df),
        "columns": combined_df.columns.tolist(),
        "column_totals": column_totals,
        "top_items": top_items
    }

 







# # backend/app.py
# from fastapi import FastAPI, UploadFile, File
# from fastapi.middleware.cors import CORSMiddleware
# import pandas as pd
# import tempfile, os
# import tabula
# from typing import List
# import math

# app = FastAPI()

# # Allow all CORS requests
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # adjust for production
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Column mapping
# COLUMN_ALIASES = {
#     "product_name": ["product", "item", "name", "service"],
#     "type": ["type", "category"],
#     "revenue": ["sales", "revenue", "amount", "total", "price"],
#     "cost": ["cost", "expense"],
#     "profit": ["profit", "margin"],
#     "date": ["date", "day", "datetime"],
#     "customer": ["client", "customer", "buyer"]
# }

# # ----------------------------
# # Helpers
# # ----------------------------
# def normalize_columns(df):
#     df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
#     print(df)
#     return df

# def detect_columns(df):
#     detected = {}
#     for std, keys in COLUMN_ALIASES.items():
#         for col in df.columns:
#             if any(k in col for k in keys):
#                 detected[std] = col
#                 break
#     return detected

# def read_pdf(path):
#     try:
#         dfs = tabula.read_pdf(path, pages="all", multiple_tables=True)
#         if dfs:
#             return pd.concat(dfs, ignore_index=True)
#         return None
#     except Exception as e:
#         print("PDF read error:", e)
#         return None

# async def read_file(file: UploadFile):
#     ext = file.filename.split(".")[-1].lower()
#     with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
#         tmp.write(await file.read())
#         path = tmp.name

#     try:
#         if ext in ["xlsx", "xls"]:
#             df = pd.read_excel(path)
#         elif ext == "csv":
#             df = pd.read_csv(path)
#         elif ext == "pdf":
#             df = read_pdf(path)
#         else:
#             df = None
#     finally:
#         os.remove(path)
#     return df

# def safe_float(val):
#     try:
#         f = float(val)
#         if math.isnan(f) or math.isinf(f):
#             return 0
#         return f
#     except:
#         return 0

# # ----------------------------
# # API

# @app.post("/analyze")
# async def analyze(files: List[UploadFile] = File(...), top_n: int = 10):
#     combined_df = pd.DataFrame()

#     # Read and combine files
#     for file in files:
#         df = await read_file(file)
#         print(f"Read file: {file.filename}, shape: {df.shape if df is not None else 'None'}")
#         if df is not None and not df.empty:
#             combined_df = pd.concat([combined_df, df], ignore_index=True)

#     if combined_df.empty:
#         print("No readable data found")
#         return {"error": "No readable data found"}

#     # Normalize columns
#     combined_df = normalize_columns(combined_df)
#     columns = detect_columns(combined_df)
#     print(f"Detected columns: {columns}")

#     # Numeric columns
#     numeric_cols = {}
#     for key in ["revenue", "cost", "profit"]:
#         if key in columns:
#             numeric_cols[key] = combined_df[columns[key]].apply(safe_float)
#             print(f"Numeric conversion for {key} done, sample values: {numeric_cols[key].head(5)}")

#     # Calculate profit if missing
#     if "profit" not in numeric_cols and "revenue" in numeric_cols and "cost" in numeric_cols:
#         numeric_cols["profit"] = numeric_cols["revenue"] - numeric_cols["cost"]
#         print("Profit calculated from revenue and cost")

#     # Totals
#     totals = {}
#     if "revenue" in numeric_cols:
#         totals["total_revenue"] = float(numeric_cols["revenue"].sum())
#     if "cost" in numeric_cols:
#         totals["total_cost"] = float(numeric_cols["cost"].sum())
#     if "profit" in numeric_cols:
#         totals["total_profit"] = float(numeric_cols["profit"].sum())
#     if "product_name" in columns:
#         totals["total_items"] = int(combined_df[columns["product_name"]].nunique())
#     if "customer" in columns:
#         totals["total_customers"] = int(combined_df[columns["customer"]].nunique())

#     print(f"Totals calculated: {totals}")

#     # Column totals
#     column_totals = {}
#     for col in numeric_cols:
#         column_totals[col] = safe_float(combined_df[col].sum())
#     print(f"Column totals: {column_totals}")

#     # Top N profitable rows
#     top_items = []
#     if "profit" in numeric_cols:
#         combined_df["_profit_sort_"] = numeric_cols["profit"]
#         top_df = combined_df.sort_values(by="_profit_sort_", ascending=False).head(top_n)
#         top_df = top_df.drop(columns=["_profit_sort_"])
#         top_items = top_df.to_dict(orient="records")
#         print(f"Top {top_n} items: {top_items[:5]}")  # print only first 5 rows for debug

#     # Debug print before return
#     print(f"Total rows combined: {len(combined_df)}")

#     return {
#         "rows": len(combined_df),
#         "columns_detected": columns,
#         "totals": totals,
#         "column_totals": column_totals,
#         "top_items": top_items
#     }

# ----------------------------
# @app.post("/analyze")
# async def analyze(files: List[UploadFile] = File(...), top_n: int = 10):
#     combined_df = pd.DataFrame()

#     for file in files:
#         df = await read_file(file)
#         if df is not None and not df.empty:
#             combined_df = pd.concat([combined_df, df], ignore_index=True)

#     if combined_df.empty:
#         return {"error": "No readable data found"}

#     combined_df = normalize_columns(combined_df)
#     columns = detect_columns(combined_df)

#     # Convert numeric columns
#     for key in ["revenue", "cost", "profit"]:
#         if key in columns:
#             combined_df[columns[key]] = pd.to_numeric(
#                 combined_df[columns[key]], errors="coerce"
#             ).fillna(0)

#     # Calculate profit if missing
#     if "profit" not in columns and "revenue" in columns and "cost" in columns:
#         combined_df["__calculated_profit__"] = (
#             combined_df[columns["revenue"]] - combined_df[columns["cost"]]
#         )
#         columns["profit"] = "__calculated_profit__"

#     # ----------------------------
#     # TOTALS
#     # ----------------------------
#     totals = {}
#     if "revenue" in columns:
#         totals["total_revenue"] = safe_float(combined_df[columns["revenue"]].sum())
#     if "cost" in columns:
#         totals["total_cost"] = safe_float(combined_df[columns["cost"]].sum())
#     if "profit" in columns:
#         totals["total_profit"] = safe_float(combined_df[columns["profit"]].sum())
#     if "product_name" in columns:
#         totals["total_items"] = int(combined_df[columns["product_name"]].nunique())
#     if "customer" in columns:
#         totals["total_customers"] = int(combined_df[columns["customer"]].nunique())

#     # Column totals
#     column_totals = {}
#     for col in combined_df.columns:
#         if pd.api.types.is_numeric_dtype(combined_df[col]):
#             column_totals[col] = safe_float(combined_df[col].sum())

#     # Top N profitable items
#     top_items = []
#     if "profit" in columns:
#         top_df = combined_df.sort_values(
#             by=columns["profit"], ascending=False
#         ).head(top_n)
#         # Ensure JSON-safe numeric values
#         for col in top_df.select_dtypes(include="number").columns:
#             top_df[col] = top_df[col].apply(safe_float)
#         top_items = top_df.to_dict(orient="records")

#     return {
#         "rows": len(combined_df),
#         "columns_detected": columns,
#         "totals": totals,
#         "column_totals": column_totals,
#         "top_items": top_items
#     }


# from fastapi import FastAPI, UploadFile, File
# from fastapi.middleware.cors import CORSMiddleware
# import pandas as pd
# import tabula
# import tempfile
# import os
# import aiofiles

# app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ------------------------
# # Column detection
# # ------------------------
# COLUMN_ALIASES = {
#     "product": ["product", "item", "name", "product_name", "service"],
#     "sales": ["sales", "revenue", "amount", "total", "price"],
#     "quantity": ["quantity", "qty", "units", "count"],
#     "stock": ["stock", "inventory", "available"],
#     "min_stock": ["min_stock", "minimum", "reorder", "threshold"],
#     "cost": ["cost", "expense"],
#     "profit": ["profit", "margin"],
#     "client": ["client", "customer", "buyer"],
#     "date": ["date", "day", "datetime", "transaction_date"]
# }

# def normalize_columns(df):
#     df.columns = [str(c).lower().replace(" ", "_") for c in df.columns]
#     return df

# def detect_columns(df):
#     detected = {}
#     for std_col, keywords in COLUMN_ALIASES.items():
#         for col in df.columns:
#             if any(k in col for k in keywords):
#                 detected[std_col] = col
#                 break
#     return detected

# def read_pdf(path):
#     try:
#         dfs = tabula.read_pdf(path, pages="all", multiple_tables=True)
#         return pd.concat(dfs, ignore_index=True) if dfs else None
#     except:
#         return None

# async def read_file(file: UploadFile):
#     ext = file.filename.split(".")[-1].lower()
#     with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
#         content = await file.read()
#         tmp.write(content)
#         path = tmp.name

#     if ext in ["xlsx", "xls"]:
#         df = pd.read_excel(path)
#     elif ext == "csv":
#         df = pd.read_csv(path)
#     elif ext == "pdf":
#         df = read_pdf(path)
#     else:
#         df = None

#     os.remove(path)
#     return df

# # ------------------------
# # API endpoint
# # ------------------------
# @app.post("/analyze")
# async def analyze(file: UploadFile = File(...)):
#     df = await read_file(file)
#     if df is None or df.empty:
#         return {"error": "Unsupported or empty file"}

#     df = normalize_columns(df)
#     columns = detect_columns(df)

#     # Convert numeric columns
#     for col in ["sales", "profit", "cost", "quantity"]:
#         if col in columns:
#             df[columns[col]] = pd.to_numeric(df[columns[col]], errors="coerce").fillna(0)

#     # Convert date column if exists
#     date_col = columns.get("date")
#     if date_col:
#         df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

#     # Prepare results
#     result = {
#         "rows": len(df),
#         "columns_detected": columns,
#         "totals": {}
#     }

#     # Totals
#     for col in ["sales", "profit", "cost", "quantity"]:
#         if col in columns:
#             result["totals"][col] = float(df[columns[col]].sum())

#     # Revenue / Cost per day/week/month
#     if date_col:
#         df_dates = df.dropna(subset=[columns[date_col]])
#         if not df_dates.empty:
#             for col in ["sales", "cost", "profit"]:
#                 if col in columns:
#                     s = df_dates.groupby(pd.Grouper(key=columns[date_col], freq="D"))[columns[col]].sum()
#                     result[f"{col}_per_day"] = s.reset_index().rename(columns={columns[date_col]:"date", columns[col]:col}).to_dict(orient="records")
#                     s = df_dates.groupby(pd.Grouper(key=columns[date_col], freq="W"))[columns[col]].sum()
#                     result[f"{col}_per_week"] = s.reset_index().rename(columns={columns[date_col]:"week", columns[col]:col}).to_dict(orient="records")
#                     s = df_dates.groupby(pd.Grouper(key=columns[date_col], freq="M"))[columns[col]].sum()
#                     result[f"{col}_per_month"] = s.reset_index().rename(columns={columns[date_col]:"month", columns[col]:col}).to_dict(orient="records")

#     return result




# from fastapi import FastAPI, UploadFile, File
# from fastapi.middleware.cors import CORSMiddleware
# import pandas as pd
# import tabula
# import tempfile
# import aiofiles
# import os

# app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # ------------------------
# # Helpers
# # ------------------------

# COLUMN_ALIASES = {
#     "product": ["product", "item", "item_name", "product_name"],
#     "sales": ["sales", "revenue", "amount", "total", "price"],
#     "quantity": ["quantity", "qty", "units", "count"],
#     "stock": ["stock", "inventory", "available"],
#     "min_stock": ["min_stock", "minimum", "reorder", "threshold"],
#     "client": ["client", "customer", "buyer"]
# }

# def normalize_columns(df):
#     df.columns = [c.lower().replace(" ", "_") for c in df.columns]
#     return df

# def detect_columns(df):
#     detected = {}

#     for std_col, keywords in COLUMN_ALIASES.items():
#         for col in df.columns:
#             if any(k in col for k in keywords):
#                 detected[std_col] = col
#                 break

#     return detected

# def read_pdf(path):
#     try:
#         dfs = tabula.read_pdf(path, pages="all", multiple_tables=True)
#         return pd.concat(dfs, ignore_index=True) if dfs else None
#     except:
#         return None

# async def read_file(file: UploadFile):
#     ext = file.filename.split(".")[-1].lower()

#     with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as tmp:
#         content = await file.read()
#         tmp.write(content)
#         path = tmp.name

#     if ext in ["xlsx", "xls"]:
#         df = pd.read_excel(path)
#     elif ext == "csv":
#         df = pd.read_csv(path)
#     elif ext == "pdf":
#         df = read_pdf(path)
#     else:
#         df = None

#     os.remove(path)
#     return df

# # ------------------------
# # API
# # ------------------------

# @app.post("/analyze")
# async def analyze(file: UploadFile = File(...)):
#     df = await read_file(file)
#     if df is None or df.empty:
#         return {"error": "Unsupported or empty file"}

#     df = normalize_columns(df)
#     columns = detect_columns(df)

#     for col in columns.values():
#         df[col] = pd.to_numeric(df[col], errors="ignore")

#     sales_col = columns.get("sales")
#     product_col = columns.get("product")
#     client_col = columns.get("client")
#     stock_col = columns.get("stock")
#     min_stock_col = columns.get("min_stock")

#     result = {
#         "rows": len(df),
#         "columns_detected": columns,
#         "total_sales": float(df[sales_col].sum()) if sales_col else 0,
#         "total_products": int(df[product_col].nunique()) if product_col else 0,
#         "total_clients": int(df[client_col].nunique()) if client_col else 0,
#         "top_products": [],
#         "unsold_products": [],
#         "low_stock": []
#     }

#     if product_col and sales_col:
#         result["top_products"] = (
#             df.groupby(product_col)[sales_col]
#             .sum().sort_values(ascending=False)
#             .head(5).reset_index()
#             .rename(columns={product_col: "product", sales_col: "sales"})
#             .to_dict(orient="records")
#         )

#         result["unsold_products"] = (
#             df[df[sales_col] == 0][product_col].dropna().unique().tolist()
#         )

#     if stock_col and min_stock_col and product_col:
#         low = df[df[stock_col] <= df[min_stock_col]]
#         result["low_stock"] = low[
#             [product_col, stock_col, min_stock_col]
#         ].rename(columns={
#             product_col: "product",
#             stock_col: "stock",
#             min_stock_col: "min_stock"
#         }).to_dict(orient="records")

#     return result


# from flask import Flask, request, jsonify
# from flask_sqlalchemy import SQLAlchemy
# from flask_cors import CORS
# from datetime import datetime, timedelta
# import threading
# import smtplib
# from email.mime.text import MIMEText
# import time

# app = Flask(__name__)
# CORS(app)  # Enable CORS for all origins
# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///pms.db'
# app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
# db = SQLAlchemy(app)

# # Models
# class Task(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     description = db.Column(db.String, nullable=False)
#     deadline = db.Column(db.DateTime, nullable=False)
#     completed = db.Column(db.Boolean, default=False)

# class Invoice(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
#     amount = db.Column(db.Float, nullable=False)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)

# class Sale(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     amount = db.Column(db.Float, nullable=False)
#     date = db.Column(db.DateTime, nullable=False)

# class Expense(db.Model):
#     id = db.Column(db.Integer, primary_key=True)
#     amount = db.Column(db.Float, nullable=False)
#     date = db.Column(db.DateTime, nullable=False)

# # Email sending helper (configure your email credentials here)
# def send_email(subject, body, to_email):
#     sender_email = "your_email@example.com"
#     sender_password = "your_password"
#     msg = MIMEText(body)
#     msg['Subject'] = subject
#     msg['From'] = sender_email
#     msg['To'] = to_email
#     try:
#         with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
#             server.login(sender_email, sender_password)
#             server.send_message(msg)
#     except Exception as e:
#         print("Email send failed:", e)

# # Deadline reminder worker thread
# def deadline_reminder_worker():
#     while True:
#         with app.app_context():
#             now = datetime.utcnow()
#             reminder_threshold = now + timedelta(hours=24)
#             tasks = Task.query.filter(
#                 Task.completed == False,
#                 Task.deadline <= reminder_threshold,
#                 Task.deadline > now
#             ).all()
#             for task in tasks:
#                 send_email(
#                     subject="Task Deadline Reminder",
#                     body=f"Task '{task.description}' is due by {task.deadline.isoformat()} UTC.",
#                     to_email="notify@example.com"
#                 )
#         time.sleep(3600)

# # Routes

# @app.route('/tasks', methods=['GET'])
# def get_tasks():
#     tasks = Task.query.all()
#     return jsonify([
#         {
#             'id': t.id,
#             'description': t.description,
#             'deadline': t.deadline.isoformat(),
#             'completed': t.completed
#         } for t in tasks
#     ])

# @app.route('/tasks', methods=['POST'])
# def create_task():
#     data = request.json
#     task = Task(description=data['description'], deadline=datetime.fromisoformat(data['deadline']))
#     db.session.add(task)
#     db.session.commit()
#     return jsonify({'id': task.id}), 201

# @app.route('/tasks/<int:task_id>/complete', methods=['POST'])
# def complete_task(task_id):
#     task = Task.query.get_or_404(task_id)
#     if task.completed:
#         return jsonify({'error': 'Task already completed'}), 400
#     task.completed = True
#     db.session.commit()
#     amount = request.json.get('amount', 100.0)
#     invoice = Invoice(task_id=task.id, amount=amount)
#     db.session.add(invoice)
#     db.session.commit()
#     send_email(
#         subject=f"Invoice Created for Task {task.id}",
#         body=f"Invoice #{invoice.id} created for task '{task.description}' with amount ${amount:.2f}.",
#         to_email="notify@example.com"
#     )
#     return jsonify({'invoice_id': invoice.id})

# @app.route('/import/sales', methods=['POST'])
# def import_sales():
#     entries = request.json
#     for e in entries:
#         sale = Sale(amount=e['amount'], date=datetime.fromisoformat(e['date']))
#         db.session.add(sale)
#     db.session.commit()
#     return jsonify({'imported': len(entries)})

# @app.route('/import/expenses', methods=['POST'])
# def import_expenses():
#     entries = request.json
#     for e in entries:
#         expense = Expense(amount=e['amount'], date=datetime.fromisoformat(e['date']))
#         db.session.add(expense)
#     db.session.commit()
#     return jsonify({'imported': len(entries)})

# @app.route('/cashflow/projection', methods=['GET'])
# def cashflow_projection():
#     today = datetime.utcnow().date()
#     past_days = 30
#     start_date = today - timedelta(days=past_days)

#     sales_sum = db.session.query(db.func.sum(Sale.amount)).filter(Sale.date >= start_date).scalar() or 0
#     expenses_sum = db.session.query(db.func.sum(Expense.amount)).filter(Expense.date >= start_date).scalar() or 0

#     avg_daily_net = (sales_sum - expenses_sum) / past_days

#     projection = []
#     current_balance = 0
#     for i in range(1, 31):
#         current_balance += avg_daily_net
#         projection.append({'day': i, 'projected_balance': round(current_balance, 2)})

#     return jsonify(projection)

# if __name__ == '__main__':
#     with app.app_context():
#         db.create_all()  # create tables before starting any threads
#     threading.Thread(target=deadline_reminder_worker, daemon=True).start()
#     app.run(debug=True)








# uvicorn main:app --reload
