from fastapi import FastAPI, UploadFile, File
from fastapi import FastAPI, Request, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from datetime import datetime, timezone
from database import mongo_lifespan 
import logging
import pandas as pd
from typing import List
import math
import hashlib
import asyncio
from io import BytesIO
 
ANALYZE_CACHE = {}
app = FastAPI(lifespan=mongo_lifespan) 

logging.basicConfig(level=logging.INFO)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://knowyourpay.com",
        "https://www.knowyourpay.com",
        "https://know-you-m73y.onrender.com"

    ],
    allow_credentials=True,
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
    contents = file.file.read()

    try:
        if ext in ["xlsx", "xls"]:
            return pd.read_excel(BytesIO(contents), engine="openpyxl")

        elif ext == "csv":
            return pd.read_csv(BytesIO(contents))

        elif ext == "pdf":
            import tabula
            dfs = tabula.read_pdf(BytesIO(contents), pages="all", multiple_tables=True)
            return pd.concat(dfs, ignore_index=True) if dfs else None

        return None
    except:
        return None
 
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

def find_column(columns, keywords: List[str]):
    keywords = [kw.lower() for kw in keywords]
    for col in columns:
        col_lower = col.lower()
        if any(kw in col_lower for kw in keywords):
            return col
    return None


def is_numeric_column(col, sample_size=10, threshold=0.6):
    sample = col.dropna().head(sample_size).astype(str)

    if sample.empty:
        return False

    cleaned = sample.str.replace(r"[^\d\.\-]", "", regex=True)
    numeric = pd.to_numeric(cleaned, errors="coerce")

    return numeric.notna().mean() >= threshold


def clean_numeric(col):
    cleaned = col.astype(str).str.replace(r"[^\d\.\-]", "", regex=True)
    return pd.to_numeric(cleaned, errors="coerce").fillna(0)


# -----------------------------
# API
# -----------------------------
@app.post("/analyze")
async def analyze(files: List[UploadFile] = File(...), 
    top_n: int = 10,order: str = "desc"):
    # combined_df = pd.DataFrame()
     # -----------------------------
    # 0️⃣ Generate Cache Key
    # -----------------------------
    file_hash = hashlib.md5()

    for file in files:
        contents = await file.read()
        file_hash.update(contents)
        file.file.seek(0)  # VERY IMPORTANT: reset pointer

    cache_key = f"{file_hash.hexdigest()}_{top_n}_{order.lower()}"

    if cache_key in ANALYZE_CACHE:
        return ANALYZE_CACHE[cache_key]
    

    # -----------------------------
    # 1️⃣ Read & Combine (FASTER CONCAT)
    # -----------------------------
    combined_list = []
    for file in files:
        df = read_file(file)
        if df is not None and not df.empty:
            combined_list.append(df)

    if not combined_list:
        return {"error": "No readable data found"}

    combined_df = pd.concat(combined_list, ignore_index=True)

    # -----------------------------
    # 2️⃣ Clean Numeric Columns (VECTOR DETECTION)
    # -----------------------------
    object_cols = combined_df.select_dtypes(include="object").columns

    for col in object_cols:
        if is_numeric_column(combined_df[col]):
            combined_df[col] = clean_numeric(combined_df[col])

    # -----------------------------
    # 3️⃣ Fast NaN Handling (VECTORISED)
    # -----------------------------
    numeric_cols = combined_df.select_dtypes(include="number").columns
    object_cols = combined_df.select_dtypes(include="object").columns

    combined_df[numeric_cols] = combined_df[numeric_cols].fillna(0)
    combined_df[object_cols] = combined_df[object_cols].fillna("none")

    def calculate_financials_dynamic(df: pd.DataFrame):
        """

        Dynamically calculate Revenue, Cost, and Profit only for periods present in the DataFrame.
        - Only calculates if column exists and is all NaN.
        - Detects periods from existing columns automatically.
        """
        
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
                    df[profit_col] = df[revenue_col].round(2)

                elif cost_col_name in df.columns:
                    df[profit_col] = -df[cost_col_name].round(2)

                else:
                    df.drop(columns=[profit_col], errors="ignore", inplace=True)

        else:
            if (any('profit' in col.lower() for col in df.columns)) != True:
                unit_price_col = find_column(df, UNIT_PRICE_SYNONYMS)
                cost_col = find_column(df, COST_SYNONYMS)
                quantity_col = find_column(df, QUANTITY_SYNONYMS)      
                profit_col="Profit" # create a generic profit column name

                if unit_price_col and cost_col and quantity_col:
                    df[profit_col] = (df[unit_price_col] - df[cost_col]) * df[quantity_col]

                elif unit_price_col and quantity_col:
                    df[profit_col] = (df[unit_price_col] * df[quantity_col]).round(2)

                elif cost_col and quantity_col:
                    df[profit_col] = -(df[cost_col] * df[quantity_col]).round(2)

                elif unit_price_col:
                    df[profit_col] = (df[unit_price_col]).round(2)

                else:
                    PROFIT_SYNONYMS = ["profit", "net profit", "gross profit", "margin", "earnings",
                   "sales", "revenue", "total sales", "sales amount", "amount", "turnover"]
                    profit_col=(find_column(df,PROFIT_SYNONYMS)).round(2)


        return df  
    # -----------------------------
    # 4️⃣ Financial Calculations 
    # -----------------------------
    profit_exists = any("profit" in col.lower() for col in combined_df.columns)

    if not profit_exists:
        loop = asyncio.get_running_loop()
        combined_df = await loop.run_in_executor(
            None,
            calculate_financials_dynamic,
            combined_df
        )

    # -----------------------------
    # 5️⃣ Drop Fully Empty Columns (Pandas Optimized)
    # -----------------------------
    combined_df = combined_df.dropna(axis=1, how="all")

    # -----------------------------
    # 6️⃣ Column Totals (FAST)
    # -----------------------------
    numeric_cols = combined_df.select_dtypes(include="number").columns
    column_totals = combined_df[numeric_cols].sum().to_dict()

    # Convert numpy types to float
    column_totals = {k: float(v) for k, v in column_totals.items()}

    # -----------------------------
    # 7️⃣ Top N
    # -----------------------------
    top_items = []
    profit_col = next(
        (col for col in combined_df.columns if "profit" in col.lower()),
        None
    )

    if profit_col and profit_col in combined_df.columns:

        descending = order.lower() == "desc"

        if pd.api.types.is_numeric_dtype(combined_df[profit_col]):

            if descending:
                top_df = combined_df.nlargest(top_n, profit_col)
            else:
                top_df = combined_df.nsmallest(top_n, profit_col)

        else:
            top_df = combined_df.sort_values(
                by=profit_col,
                ascending=not descending
            ).head(top_n)

        top_items = top_df.to_dict(orient="records")


    response_data = {
    "rows": len(combined_df),
    "columns": combined_df.columns.tolist(),
    "column_totals": column_totals,
    "top_items": top_items
}

    ANALYZE_CACHE[cache_key] = response_data

    return response_data
