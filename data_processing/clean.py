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
import matplotlib.pyplot as plt
import logging

logging.basicConfig(level=logging.INFO)


def clean_data(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Clean the data handling missing values, removing duplicates and parsing dates"""
    # Handle missing values in Age column
    if "Age" in dataframe.columns:
        median_age = dataframe["Age"].median()
        dataframe["Age"] = dataframe["Age"].fillna(median_age)
        # Ensure ages are within a reasonable range
        dataframe["Age"] = dataframe["Age"].apply(
            lambda x: x if 0 <= x <= 120 else None
        )
        dataframe.drop_duplicates(inplace=True)
        return dataframe
