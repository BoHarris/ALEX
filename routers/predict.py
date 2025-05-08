from fastapi import APIRouter, File, UploadFile, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import pandas as pd
import os
import shutil
import uuid
import re
import numpy as np
import logging
import joblib
from utils.redaction import scan_and_redact_column_with_count
from utils.constants import SUPPORTED_EXTENSIONS
import mimetypes
import io
import json
import xml.etree.ElementTree as ET
from PyPDF2 import PdfReader
from dependencies.tier_guard import enforce_tier_limit

router = APIRouter(prefix="/predict", tags=["Prediction"])

xgb_model = joblib.load("models/xgboost_model.pkl")

EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")
PHONE_RE = re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
SSN_RE   = re.compile(r"\d{3}-\d{2}-\d{4}")
IP_RE    = re.compile(r"(?:\d{1,3}\.){3}\d{1,3}")
street_suffixes = {"st","street","ave","road","rd","blvd","ln","lane"}
def contains_dob_pattern(values):
    dob_regex = re.compile(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b")
    return any(dob_regex.search(str(value)) for value in values) if values else False

def contains_gender_term(values):
    gender_terms = {"male", "female", "man", "woman", "boy", "girl"}
    return any(any(term in str(value).lower() for term in gender_terms) for value in values) if values else False

def contains_street_suffix(values):
    return any(any(suffix in str(value).lower() for suffix in street_suffixes) for value in values) if values else False

def contains_city_name(values):
    city_names = {"new york", "los angeles", "chicago", "houston", "phoenix"}  # Example city names
    return any(any(city in str(value).lower() for city in city_names) for value in values) if values else False

def contains_known_name(values):
    known_names = {"john", "jane", "smith", "doe"}  # Example known names
    return any(any(name in str(value).lower() for name in known_names) for value in values) if values else False

def contains_zip_code_pattern(values):
    zip_regex = re.compile(r"\b\d{5}(?:-\d{4})?\b")
    return any(zip_regex.search(str(value)) for value in values) if values else False

def contains_phone_pattern(values):
    return any(PHONE_RE.search(str(value)) for value in values) if values else False

class PredictionResult(BaseModel):
    filename: str
    pii_columns: list[str]
    redacted_file: str
    risk_score: float
    redacted_count: int
    total_values: int

@router.post("/", response_model=PredictionResult)
async def predict(file: UploadFile = File(...), 
                  user_info:dict = Depends(enforce_tier_limit)):
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]
    if ext.lower() not in SUPPORTED_EXTENSIONS:
        return JSONResponse(status_code=400, content={"error":"Unsupported file type."})

    
    os.makedirs("uploads", exist_ok=True)
    os.makedirs("redacted", exist_ok=True)
    os.makedirs("static/redacted", exist_ok=True)

    file_path = f"uploads/{file_id}{ext}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    
    # Guess the file format
    file_format, _ = mimetypes.guess_type(file.filename)
    file_format = file_format or ""

    try:
        # — PDF support first —
        if ext.lower() == ".pdf":
            reader = PdfReader(io.BytesIO(file_bytes))
            if reader.is_encrypted:
                try:
                    reader.decrypt("")   # try empty password
                except Exception:
                    return JSONResponse(400, {"error":"PDF is encrypted or requires a password."})
            texts = [page.extract_text() or "" for page in reader.pages]
            parsed = pd.DataFrame({"text": texts})

        # — then CSV —
        elif "csv" in file_format or ext.lower() == ".csv":
            parsed = pd.read_csv(io.BytesIO(file_bytes))

        # — then Excel —
        elif "excel" in file_format or ext.lower() in {".xls", ".xlsx"}:
            parsed = pd.read_excel(io.BytesIO(file_bytes))

        # — then JSON —
        elif "json" in file_format or ext.lower() == ".json":
            data = json.load(io.BytesIO(file_bytes))
            parsed = pd.json_normalize(data)

        # — then plain text / logs —
        elif "plain" in file_format or ext.lower() in {".txt", ".log"}:
            lines = io.BytesIO(file_bytes).read().decode("utf-8").splitlines()
            parsed = pd.DataFrame({"text": lines})

        # — then XML —
        elif "xml" in file_format or ext.lower() == ".xml":
            tree = ET.parse(io.BytesIO(file_bytes))
            root = tree.getroot()
            parsed = pd.DataFrame([
                {child.tag: child.text for child in elem}
                for elem in root
            ])

        else:
            # nothing matched
            raise ValueError(f"Unsupported format: {file_format} / {ext}")

    except Exception as e:
        return JSONResponse(status_code=400, content={"error":f"Parsing error: {e}"})

    # build DataFrame if needed
    df = parsed if isinstance(parsed, pd.DataFrame) else pd.DataFrame({"text":parsed})
    if df.empty:
        return JSONResponse(status_code=400, content={"error":"File is empty or not supported."})

    # feature extraction, prediction, redaction loop...
    features = df.columns.tolist()
    X = pd.DataFrame(features, columns=["column"])
    X["length"] = X["column"].apply(len)
    X["num_underscores"] = X["column"].apply(lambda x: x.count("_"))
    X["num_digits"] = X["column"].apply(lambda x: sum(c.isdigit() for c in x))
    X["has_at"] = X["column"].apply(lambda x: int("@" in x))
    X["has_email_keyword"] = X["column"].apply(lambda x: int("email" in x.lower()))
    value_samples = [df[col].dropna().astype(str).head(3).tolist() for col in df.columns]
    X["parsed_values"] = value_samples

    def pct_match(regex, vals):
        return np.mean([bool(regex.search(str(v))) for v in vals]) if vals else 0

    X["pct_email_like"] = X["parsed_values"].apply(lambda v: pct_match(EMAIL_RE, v))
    X["pct_phone_like"] = X["parsed_values"].apply(lambda v: pct_match(PHONE_RE, v))
    X["pct_ssn_like"] = X["parsed_values"].apply(lambda v: pct_match(SSN_RE, v))
    X["pct_ip_like"] = X["parsed_values"].apply(lambda v: pct_match(IP_RE, v))
    X["avg_digits_per_val"] = X["parsed_values"].apply(lambda v: np.mean([sum(c.isdigit() for c in str(i)) for i in v]) if v else 0)
    X["avg_val_len"] = X["parsed_values"].apply(lambda v: np.mean([len(str(i)) for i in v]) if v else 0)
    X["has_dob_pattern"]    = X["parsed_values"].apply(contains_dob_pattern)
    
    
    X["has_gender_term"]    = X["parsed_values"].apply(contains_gender_term)
    X["has_street_suffix"]  = X["parsed_values"].apply(contains_street_suffix)
    X["has_city_name"]      = X["parsed_values"].apply(contains_city_name)
    X["has_known_name"]     = X["parsed_values"].apply(contains_known_name)
    X["has_zip_pattern"]    = X["parsed_values"].apply(contains_zip_code_pattern)
    X["has_phone_pattern"]  = X["parsed_values"].apply(contains_phone_pattern)



    predictions = xgb_model.predict(X[[
        "length","num_underscores","num_digits","has_at","has_email_keyword",
        "pct_email_like","pct_phone_like","pct_ssn_like","pct_ip_like",
        "avg_digits_per_val","avg_val_len",
        "has_dob_pattern","has_gender_term","has_street_suffix",
        "has_city_name","has_known_name","has_zip_pattern","has_phone_pattern"
    ]])
    pii_columns = [col for col,is_pii in zip(features,predictions) if is_pii==0]

    redacted_df = df.copy()
    total_redacted = total_values = 0
    for col in pii_columns:
        redacted_col, redacted_count, col_total, _ = scan_and_redact_column_with_count(df[col])
        redacted_df[col] = redacted_col
        total_redacted += redacted_count
        total_values += col_total

    redacted_path = os.path.join("redacted", f"redacted_{file_id}{ext}")

    # write out according to extension
    if ext.lower() in {".csv", ".txt", ".log"}:
        redacted_df.to_csv(redacted_path, index=False)
    elif ext.lower() in {".xlsx", ".xls"}:
        redacted_df.to_excel(redacted_path, index=False)
    elif ext.lower() == ".json":
        redacted_df.to_json(redacted_path, orient="records", lines=True)
    elif ext.lower() == ".xml":
        root = ET.Element("root")
        for _, row in redacted_df.iterrows():
            item = ET.SubElement(root, "item")
            for c, v in row.items():
                ch = ET.SubElement(item, c)
                ch.text = str(v)
        ET.ElementTree(root).write(redacted_path)
    else:
        # fallback for PDF & others
        redacted_df.to_csv(redacted_path, index=False)

    
    public_redacted_path = os.path.join("static","redacted", os.path.basename(redacted_path))
    shutil.copyfile(redacted_path, public_redacted_path)

    try:
        os.remove(file_path)
    except Exception:
        logging.error(f"Error deleting {file_path}")

    risk_score = round(total_redacted/total_values, 2) if total_values>0 else 0.0
    logging.info(f"Processed {file.filename} | PII columns: {pii_columns} | Saved to {redacted_path}")

    return PredictionResult(
        filename=file.filename,
        pii_columns=pii_columns,
        redacted_file=public_redacted_path,
        risk_score=risk_score,
        redacted_count=total_redacted,
        total_values=total_values
    )
