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
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import joblib
import os
import sys
import matplotlib.pylab as plt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models.pii_features import extract_column_features

#Step 1: load the column level dataset
df = pd.read_csv("../pii_column.csv")

#step 2 map PII to numeric values
df["is_pii"] = df["pii"].map({"yes": 0, "no": 1}) #note 0 =PII

#Step 3: Extract features from column name
df = extract_column_features(df)

#add features
features = ["length", "num_underscores", "num_digits", "has_at",
            "has_email_keyword", "pct_email_like", "pct_phone_like", 
            "pct_ssn_like", "pct_ip_like", "avg_digits_per_val","avg_val_len"]

X=df[features]
y=df["is_pii"]

#Step 5: Split into train and test sets
X_train, X_test, y_train, y_test = train_test_split(
    X,y, test_size=0.2,random_state=45
)

#Step 6 Train Random Forest model
model = RandomForestClassifier(n_estimators=100,random_state=42, class_weight="balanced")
model.fit(X_train, y_train)

#Step 7: Evaluate and save
y_pred = model.predict(X_test)
print(classification_report(y_test, y_pred, target_names=["PII", "Non-PII"]))

#Step 8: save model to disk
os.makedirs("models", exist_ok=True)
joblib.dump(model,"models/pii_classifier.pkl" )
print("Model saved to models/pii_classifier.pkl")