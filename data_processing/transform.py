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
import logging
from sklearn.preprocessing import MinMaxScaler, LabelEncoder

logging.basicConfig(level=logging.INFO)


def normalize_column(dataframe: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """Normalize a specific numerical column in the dataframe."""
    if column_name in dataframe.columns:
        scaler = MinMaxScaler()
        dataframe[f"Normalized_{column_name}"] = scaler.fit_transform(
            dataframe[[column_name]]
        )
        logging.info(f"Normalize column: {column_name}")
    else:
        logging.warning(f"Column {column_name} not found in dataframe")
    return dataframe


# function to encode categorical column
def encode_column(dataframe: pd.DataFrame, column_name: str) -> pd.DataFrame:
    """Encode a categorical column in the dataframe for ML compatibility"""
    if column_name in dataframe.columns:
        le = LabelEncoder()
        dataframe[f"{column_name}_Encoded"] = le.fit_transform(dataframe[column_name])
        logging.info(f"Encoded column: {column_name}")
    else:
        logging.warning(f"Column {column_name} not found in dataframe")
    return dataframe


def transform_data(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Apply various transformations to the dataframe"""
    dataframe = normalize_column(dataframe, "Age")  # normalize the "Age" column
    dataframe = encode_column(dataframe, "Category")  # encode the "Category" column
    logging.info("Data transformations complete")
    return dataframe
