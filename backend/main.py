from fastapi import FastAPI, UploadFile, File
from fastapi import FastAPI, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from database import mongo_lifespan 
import logging
import pandas as pd
import tempfile, os
from typing import List
import math
 

app = FastAPI(lifespan=mongo_lifespan) 

logging.basicConfig(level=logging.INFO)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*",
        "https://www.knowyourpay.com",
        "https://know-you-m73y.onrender.com"

    ],
    allow_methods=["*"],
    allow_headers=["*"],
) 

# -------------------- 
# API routes 
# --------------------
@app.get("/health")
def health():
    return {"message": "FastAPI backend is running"}



# Middleware to log visits
@app.middleware("http")
async def log_visits(request: Request, call_next):
    try:
        db = request.app.state.db
        await db.visits.insert_one({
            "ip": request.client.host if request.client else "unknown",
            "url": str(request.url),
            "timestamp": datetime.now(timezone.utc)
        })
    except Exception as e:
        logging.error(f"Visit logging failed: {e}")

    
    response = await call_next(request)
    return response

# Endpoint to submit comment
@app.post("/comment")
async def submit_comment(request: Request,
    username: str = Form(...),
    comment: str = Form(...)
):
    db = request.app.state.db

    doc = {
        "username": username,
        "comment": comment,
        "timestamp": datetime.now(timezone.utc)
    }
    await db.comments.insert_one(doc)
    return JSONResponse({"status": "success", "message": "Comment saved"})

# Endpoint to get stats
@app.get("/stats")
async def get_stats(request: Request):
    db = request.app.state.db

    total_visits = await db.visits.count_documents({})
    unique_visitors = await db.visits.distinct("ip")
    total_unique = len(unique_visitors)

    analyze_count = await db.visits.count_documents({"url": {"$regex": "analyze"}})
    
    return {
        "total_visits": total_visits,
        "unique_visitors": total_unique,
        "analyze_count": analyze_count
    }
  
# Endpoint to get comments
@app.get("/comments")
async def get_comments(request: Request):
    db = request.app.state.db
    comments = await db.comments.find().to_list(length=100)
    return comments


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

def find_column(df, keywords: List[str]):
    for col in df:
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

    # Identify numeric columns
    numeric_input_cols = []
    for col in combined_df.columns:
        if is_numeric_column(combined_df[col]):
            numeric_input_cols.append(col)
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

    def calculate_financials_dynamic(df: pd.DataFrame):
        """

        Dynamically calculate Revenue, Cost, and Profit only for periods present in the DataFrame.
        - Only calculates if column exists and is all NaN.
        - Detects periods from existing columns automatically.
        """
        
        # Detect periods from column names (e.g., Daily Revenue, Weekly Cost, Monthly Profit)
        # pattern = re.compile(r"(\w+)\s+(Revenue|Cost|Profit)", re.IGNORECASE)
        PERIODIC_keywords = ["Daily", "Weekly", "Monthly", "Yearly"]
        periodic = {}
        for period in PERIODIC_keywords:
            period_lower = period.lower()
            for col in df.columns:
                col_lower = col.lower()
                if period_lower in col_lower:
                    if period in periodic:
                        periodic[period]+=[col]
                    else :
                        periodic[period]=[col]
        print(periodic)
        if len(periodic)!=0:
            for period in periodic:
                unit_price_col = find_column(periodic[period], UNIT_PRICE_SYNONYMS)
                cost_col = find_column(periodic[period], COST_SYNONYMS)
                quantity_col = find_column(periodic[period], QUANTITY_SYNONYMS)

                revenue_col = f"{period} Revenue"
                cost_col_name = f"{period} Cost"
                profit_col = f"{period} Profit"

                # -------------------------
                # Revenue
                # -------------------------
                if (
                    unit_price_col
                    and quantity_col
                    and unit_price_col in df.columns
                    and quantity_col in df.columns
                ):
                    df[revenue_col] = (df[unit_price_col] * df[quantity_col]).round(2)
                else:
                    df.drop(columns=[revenue_col], errors="ignore", inplace=True)

                # -------------------------
                # Cost
                # -------------------------
                if (
                    cost_col
                    and quantity_col
                    and cost_col in df.columns
                    and quantity_col in df.columns
                ):
                    df[cost_col_name] = (df[cost_col] * df[quantity_col]).round(2)
                else:
                    df.drop(columns=[cost_col_name], errors="ignore", inplace=True)

                # -------------------------
                # Profit
                # -------------------------
                if revenue_col in df.columns and cost_col_name in df.columns:
                    df[profit_col] = (df[revenue_col] - df[cost_col_name]).round(2)

                elif revenue_col in df.columns:
                    df[profit_col] = df[revenue_col]

                elif cost_col_name in df.columns:
                    df[profit_col] = -df[cost_col_name]

                else:
                    df.drop(columns=[profit_col], errors="ignore", inplace=True)

        # else:
            
        #     unit_exists = unit_price_col in df.columns and not df[unit_price_col].isna().all()
        #     cost_exists = cost_col in df.columns and not df[cost_col].isna().all()
        #     qty_exists = quantity_col in df.columns and not df[quantity_col].isna().all()
        #     profit_col="profit" # create a generic profit column name
        #     if unit_exists and cost_exists and qty_exists:
        #         df[profit_col] = (df[unit_price_col].fillna(0) - df[cost_col].fillna(0)) * df[quantity_col].fillna(0)
 
        #     elif unit_exists and qty_exists:
        #         df[profit_col] = df[unit_price_col].fillna(0) * df[quantity_col].fillna(0)

        #     elif cost_exists and qty_exists:
        #         df[profit_col] = -(df[cost_col].fillna(0) * df[quantity_col].fillna(0))
        #     elif unit_exists :
                # df[profit_col] = df[unit_price_col].fillna(0)
        # logging.info(df)
        return df  
    print("------",combined_df)
    combined_df = calculate_financials_dynamic(
    combined_df
)
    
    # print(combined_df)
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

 
 