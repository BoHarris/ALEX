# ──────────────────────────────────────────────────────────────────────
# © 2025 PII Sentinel™
# Proprietary & Confidential – All Rights Reserved
#
# This software is the confidential and proprietary information of
# PII Sentinel™ ("Confidential Information"). You shall not disclose
# such Confidential Information and shall use it only in accordance
# with the terms of a binding agreement or license.
#
# Unauthorized reproduction, modification, or distribution of this
# software or its components, in whole or in part, is strictly prohibited.
#
# For licensing, partnership, or commercial use, contact:
# Bo.k.harris@gmail.com
# ──────────────────────────────────────────────────────────────────────

import pandas as pd
import numpy as np
import re
import ast

#Patterns
EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")
PHONE_RE = re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
SSN_RE = re.compile(r"\d{3}-\d{2}-\d{4}")
IP_RE = re.compile(r"(?:\d{1,3}\.){3}\d{1,3}")


def extract_column_features(df):
    df["length"] = df["column"].apply(len)
    df["num_underscores"] = df["column"].apply(lambda x: x.count("_"))
    df["num_digits"] = df["column"].apply(lambda x: sum(c.isdigit() for c in x))
    df["has_at"] = df["column"].apply(lambda x: int("@" in x))
    df["has_email_keyword"] = df["column"].apply(lambda x: int("email" in x.lower()))
    df["parsed_values"] = df["value_samples"].apply(ast.literal_eval)
    
    def pct_match(regex, values):
        return np.mean([bool(regex.search(str(v))) for v in values])
    
    df["pct_email_like"] = df["parsed_values"].apply(lambda v: pct_match(EMAIL_RE, v))
    df["pct_phone_like"] = df["parsed_values"].apply(lambda v: pct_match(PHONE_RE, v))
    df["pct_ssn_like"] = df["parsed_values"].apply(lambda v: pct_match(SSN_RE, v))
    df["pct_ip_like"] = df["parsed_values"].apply(lambda v: pct_match(IP_RE,v ))
    df["avg_digits_per_val"] = df["parsed_values"].apply(lambda v: np.mean([sum(c.isdigit() for c in str(i))for i in v]))
    df["avg_val_len"] = df["parsed_values"].apply(lambda v: np.mean([len(str(i)) for i in v]))
    return df