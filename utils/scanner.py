import os
import shutil
import re
import io
import json
import xml.etree.ElementTree as ET
import pandas as pd
import numpy as np
import logging
from abc import ABC, abstractmethod
from utils.redaction import scan_and_redact_column_with_count
from utils.constants import SUPPORTED_EXTENSIONS

# -----------------------------------------------------------------------------
#                       Parser Interfaces and Implementations 
# -----------------------------------------------------------------------------
class Parser(ABC):
    @abstractmethod
    def parse(self, blob: bytes) -> pd.DataFrame:
        pass
    
class CsvParser(Parser):
    def parse(self,blob: bytes) -> pd.DataFrame:
        return pd.read_csv(io.BytesIO(blob))
    
class ExcelParser(Parser):
    def parse(self, blob:bytes) -> pd.DataFrame:
        return pd.read_excel(io.BytesIO(blob))
    
class JsonParser(Parser):
    def parse(self, blob:bytes) -> pd.DataFrame:
        data = json.load(io.BytesIO(blob))
        return pd.json_normalize(data)

class TextParser(Parser):
    def parse(self, blob:bytes) -> pd.DataFrame:
        lines = io.BytesIO(blob).read().decode('utf-8').splitlines()
        return pd.DataFrame({'text': lines})
    
class XmlParser(Parser):
    def parse(self, blob: bytes)-> pd.DataFrame:
        tree = ET.parse(io.BytesIO(blob))
        root = tree.getroot()
        return pd.DataFrame([{child.tag: child.text for child in elem} for elem in root])
    
class ParseFactory:
    @staticmethod
    def get_parser(ext: str) -> Parser:
        mapping ={
            ".csv": CsvParser,
            ".xls": ExcelParser,
            "xlsx": ExcelParser,
            ".json": JsonParser,
            ".txt": TextParser,
            ".log": TextParser,
            ".xml": XmlParser
        }
        parser_cls = mapping.get(ext)
        if not parser_cls:
            raise ValueError(f"No Parser for extension: {ext}")
        return parser_cls
    
# -----------------------------------------------------------------------------
#                       Feature Extraction 
# -----------------------------------------------------------------------------
class FeatureExtractor:
    EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")
    PHONE_RE = re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
    SSN_RE   = re.compile(r"\d{3}-\d{2}-\d{4}")
    IP_RE    = re.compile(r"(?:\d{1,3}\.){3}\d{1,3}")
    DOB_RE   = re.compile(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b")
    GENDER_TERMS = {"male","female","man","woman","boy","girl"}
    
    @staticmethod
    def extract_features(df: pd.DataFrame) -> pd.DataFrame:
        cols = df.columns.tolist()
        X = pd.DataFrame({
            "column": cols,
            "length": [len(c) for c in cols],
            "num_underscores": [c.count("_") for c in cols],
            "num_digits": [sum(ch.isdigit() for ch in c) for c in cols],
            "has_at": [int("@" in c) for c in cols],
            "has_email_keyword": [int("email" in c.lower) for c in cols]
        })
        # sample up to 3 values per column
        X["parsed_values"] = [
            df[col].dropna().astype(str).head(3).tolist() for col in cols
        ]

        def pct_match(regex, vals):
            return np.mean([bool(regex.search(v)) for v in vals]) if vals else 0

        X["pct_email_like"] = X["parsed_values"].apply(lambda v: pct_match(FeatureExtractor.EMAIL_RE, v))
        X["pct_phone_like"] = X["parsed_values"].apply(lambda v: pct_match(FeatureExtractor.PHONE_RE, v))
        X["pct_ssn_like"]   = X["parsed_values"].apply(lambda v: pct_match(FeatureExtractor.SSN_RE, v))
        X["pct_ip_like"]    = X["parsed_values"].apply(lambda v: pct_match(FeatureExtractor.IP_RE, v))
        X["has_dob_pattern"]    = X["parsed_values"].apply(lambda v: any(FeatureExtractor.DOB_RE.search(i) for i in v) if v else False)
        X["has_gender_term"]    = X["parsed_values"].apply(lambda v: any(any(term in i.lower() for term in FeatureExtractor.GENDER_TERMS) for i in v) if v else False)
        X["has_street_suffix"]  = X["parsed_values"].apply(lambda v: any(any(suffix in i.lower() for suffix in {"st","street","ave","road","rd","blvd","ln","lane"}) for i in v) if v else False)
        X["has_city_name"]      = X["parsed_values"].apply(lambda v: any(any(city in i.lower() for city in {"new york","los angeles","chicago","houston","phoenix"}) for i in v) if v else False)
        X["has_known_name"]     = X["parsed_values"].apply(lambda v: any(any(name in i.lower() for name in {"john","jane","smith","doe"}) for i in v) if v else False)
        X["has_zip_pattern"]    = X["parsed_values"].apply(lambda v: any(re.compile(r"\b\d{5}(?:-\d{4})?\b").search(i) for i in v) if v else False)
        X["has_phone_pattern"]  = X["parsed_values"].apply(lambda v: any(FeatureExtractor.PHONE_RE.search(i) for i in v) if v else False)

        return X
# -----------------------------------------------------------------------------
# Classification  left off here
# -----------------------------------------------------------------------------
        