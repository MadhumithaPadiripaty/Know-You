from celery_app import celery
from splitter import split_and_upload
from s3_client import download_bytes
import polars as pl
from io import BytesIO
from celery import group, chord


# -----------------------------
# STEP 1: SPLIT
# -----------------------------
@celery.task(bind=True)
def split_file(self, file_bytes: bytes):
    return split_and_upload(file_bytes)


# -----------------------------
# STEP 2: PROCESS CHUNK
# -----------------------------
@celery.task(
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_kwargs={"max_retries": 3},
)
def process_chunk(self, key: str):
    content = download_bytes(key)
    df = pl.read_csv(BytesIO(content))

    def find_col(keys):
        for col in df.columns:
            if any(k in col.lower() for k in keys):
                return col
        return None

    price = find_col(["price", "sales"])
    cost = find_col(["cost"])
    qty = find_col(["qty", "quantity"])

    if price and qty:
        df = df.with_columns((pl.col(price) * pl.col(qty)).alias("Revenue"))

    if cost and qty:
        df = df.with_columns((pl.col(cost) * pl.col(qty)).alias("Cost"))

    if "Revenue" in df.columns and "Cost" in df.columns:
        df = df.with_columns((pl.col("Revenue") - pl.col("Cost")).alias("Profit"))

    return {
        "rows": df.height,
        "revenue": float(df["Revenue"].sum()) if "Revenue" in df.columns else 0,
        "cost": float(df["Cost"].sum()) if "Cost" in df.columns else 0,
        "profit": float(df["Profit"].sum()) if "Profit" in df.columns else 0,
    }


# -----------------------------
# STEP 3: AGGREGATE
# -----------------------------
@celery.task
def aggregate(results):
    total = {"rows": 0, "revenue": 0, "cost": 0, "profit": 0}

    for r in results:
        total["rows"] += r["rows"]
        total["revenue"] += r["revenue"]
        total["cost"] += r["cost"]
        total["profit"] += r["profit"]

    return total


# -----------------------------
# STEP 4: FULL PIPELINE
# -----------------------------
@celery.task
def process_pipeline(chunk_keys):
    tasks = [process_chunk.s(k) for k in chunk_keys]
    return chord(group(tasks))(aggregate.s())
