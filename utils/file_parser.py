from fastapi import APIRouter, File, UploadFile
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
from PyPDF2 import PdfReader

import mimetypes
import io
import json
import xml.etree.ElementTree as ET

router = APIRouter(prefix="/predict", tags=["Prediction"])

xgb_model = joblib.load("models/xgboost_model.pkl")

EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")
PHONE_RE = re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
SSN_RE = re.compile(r"\d{3}-\d{2}-\d{4}")
IP_RE = re.compile(r"(?:\d{1,3}\.){3}\d{1,3}")
street_suffixes = {"st", "street", "ave", "road", "rd", "blvd", "ln", "lane"}

os.makedirs("uploads", exist_ok=True)
os.makedirs("redacted", exist_ok=True)
os.makedirs("static/redacted", exist_ok=True)

class PredictionResult(BaseModel):
    filename: str
    pii_columns: list[str]
    redacted_file: str
    risk_score: float
    redacted_count: int
    total_values: int

@router.post("/", response_model=PredictionResult)
async def predict(file: UploadFile = File(...)):
    file_id = str(uuid.uuid4())
    ext = os.path.splitext(file.filename)[1]
    if ext.lower() not in SUPPORTED_EXTENSIONS:
        return JSONResponse(status_code=400, content={"error": "Unsupported file type."})

    file_path = f"uploads/{file_id}{ext}"
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    with open(file_path, "rb") as f:
        file_bytes = f.read()

    try:
        file_format, _ = mimetypes.guess_type(file.filename)
        file_format = file_format or ""
        if ext.lower() == ".pdf":
            reader = PdfReader(io.BytesIO(file_bytes))
            if reader.is_encrypted:
                reader.decrypt("")
            texts = [page.extract_text() or "" for page in reader.pages]
        elif "csv" in file_format:
            parsed = pd.read_csv(io.BytesIO(file_bytes))
        elif "excel" in file_format or "xlsx" in file_format:
            parsed = pd.read_excel(io.BytesIO(file_bytes))
        elif "json" in file_format:
            data = json.load(io.BytesIO(file_bytes))
            parsed = pd.json_normalize(data)
        elif "plain" in file_format or ext in [".txt", ".log"]:
            parsed = io.BytesIO(file_bytes).read().decode("utf-8").splitlines()
        elif "xml" in file_format or ext == ".xml":
            tree = ET.parse(io.BytesIO(file_bytes))
            root = tree.getroot()
            parsed = pd.DataFrame([{child.tag: child.text for child in elem} for elem in root])
        else:
            raise ValueError("Unsupported or unrecognized file format.")
    except Exception as e:
        return JSONResponse(status_code=400, content={"error": f"Parsing error: {str(e)}"})

    df = parsed if isinstance(parsed, pd.DataFrame) else pd.DataFrame({"text": parsed})
    if df.empty:
        return JSONResponse(status_code=400, content={"error": "File is empty or not supported."})

    features = df.columns.tolist()
    X = pd.DataFrame(features, columns=["column"])
    X["length"] = X["column"].apply(len)
    X["num_underscores"] = X["column"].apply(lambda x: x.count("_"))
    X["num_digits"] = X["column"].apply(lambda x: sum(c.isdigit() for c in x))
    X["has_at"] = X["column"].apply(lambda x: int("@" in x))
    X["has_email_keyword"] = X["column"].apply(lambda x: int("email" in x.lower()))

    value_samples = [df[col].dropna().astype(str).head(3).tolist() for col in df.columns]
    X["parsed_values"] = value_samples

    def pct_match(regex, values):
        return np.mean([bool(regex.search(str(v))) for v in values]) if values else 0

    X["pct_email_like"] = X["parsed_values"].apply(lambda v: pct_match(EMAIL_RE, v))
    X["pct_phone_like"] = X["parsed_values"].apply(lambda v: pct_match(PHONE_RE, v))
    X["pct_ssn_like"] = X["parsed_values"].apply(lambda v: pct_match(SSN_RE, v))
    X["pct_ip_like"] = X["parsed_values"].apply(lambda v: pct_match(IP_RE, v))
    X["avg_digits_per_val"] = X["parsed_values"].apply(lambda v: np.mean([sum(c.isdigit() for c in str(i)) for i in v]) if v else 0)
    X["avg_val_len"] = X["parsed_values"].apply(lambda v: np.mean([len(str(i)) for i in v]) if v else 0)

    def contains_dob_pattern(values):
        dob_re = re.compile(r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})|(\d{4}[/-]\d{1,2}[/-]\d{1,2})")
        return any(bool(dob_re.search(str(v))) for v in values)

    def contains_gender_term(values):
        gender_terms = {"male", "female", "nonbinary", "trans", "woman", "man"}
        return any(str(v).strip().lower() in gender_terms for v in values)

    def contains_street_suffix(values):
        return any((words := str(v).strip().lower().split()) and words[-1] in street_suffixes for v in values)

    def contains_city_name(values):
        cities = {"new york", "los angeles", "miami"}
        return any(str(v).lower() in cities for v in values)

    def contains_known_name(values):
        names = {"alice", "bob", "charlie", "john", "jane"}
        return any(any(word.lower() in names for word in str(v).split()) for v in values)

    def contains_zip_code_pattern(values):
        zip_code_re = re.compile(r"\b\d{5}(?:-\d{4})?\b")
        return any(bool(zip_code_re.search(str(v))) for v in values)

    def contains_phone_pattern(values):
        phone_patterns = [
            re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}"),
            re.compile(r"\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
        ]
        return any(any(p.search(str(v)) for p in phone_patterns) for v in values)

    X["has_dob_pattern"] = X["parsed_values"].apply(contains_dob_pattern)
    X["has_gender_term"] = X["parsed_values"].apply(contains_gender_term)
    X["has_street_suffix"] = X["parsed_values"].apply(contains_street_suffix)
    X["has_city_name"] = X["parsed_values"].apply(contains_city_name)
    X["has_known_name"] = X["parsed_values"].apply(contains_known_name)
    X["has_zip_pattern"] = X["parsed_values"].apply(contains_zip_code_pattern)
    X["has_phone_pattern"] = X["parsed_values"].apply(contains_phone_pattern)

    feature_columns = [
        "length", "num_underscores", "num_digits", "has_at",
        "has_email_keyword", "pct_email_like", "pct_phone_like",
        "pct_ssn_like", "pct_ip_like", "avg_digits_per_val", "avg_val_len",
        "has_dob_pattern", "has_gender_term", "has_street_suffix",
        "has_city_name", "has_known_name", "has_zip_pattern", "has_phone_pattern"
    ]

    predictions = xgb_model.predict(X[feature_columns])
    pii_columns = [col for col, is_pii in zip(features, predictions) if is_pii == 0]

    redacted_df = df.copy()
    total_redacted = 0
    total_values = 0
    for col in pii_columns:
        redacted_col, redacted_count, col_total = scan_and_redact_column_with_count(df[col])
        redacted_df[col] = redacted_col
        total_redacted += redacted_count
        total_values += col_total

    redacted_path = f"redacted/redacted_{file_id}{ext}"
   
    if ext.lower() in [".csv", ".txt", ".log"]:
        redacted_df.to_csv(redacted_path, index=False)
    elif ext.lower() in [".xlsx", ".xls"]:
        redacted_df.to_excel(redacted_path, index=False)
    elif ext.lower() == ".json":
        redacted_df.to_json(redacted_path, orient="records", lines=True)
    elif ext.lower() == ".xml":
        root = ET.Element("root")
        for _, row in redacted_df.iterrows():
            item = ET.SubElement(root, "item")
            for col, val in row.items():
                child = ET.SubElement(item, col)
                child.text = str(val)
        tree = ET.ElementTree(root)
        tree.write(redacted_path)
    else:
        redacted_df.to_csv(redacted_path, index=False)  # Default fallback

    
    
    
    
    
    
    

    public_redacted_path = f"static/redacted/{os.path.basename(redacted_path)}"
    shutil.copyfile(redacted_path, public_redacted_path)

    try:
        os.remove(file_path)
    except Exception as e:
        logging.error(f"Error deleting file {file_path}: {e}")

    risk_score = round(total_redacted / total_values, 2) if total_values > 0 else 0.
    logging.info(f"Processed file: {file.filename} | PII Columns: {pii_columns}")
    logging.info(f"Parsed file type: {ext}, Rows: {len(df)}")
    logging.info(f"Redacted file saved at: {public_redacted_path}")

    return PredictionResult(
        filename=file.filename,
        pii_columns=pii_columns,
        redacted_file=public_redacted_path,
        risk_score=risk_score,
        redacted_count=total_redacted,
        total_values=total_values
    )
