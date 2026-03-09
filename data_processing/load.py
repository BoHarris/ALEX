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


def load_data(filepath: str) -> pd.DataFrame:
    """Load a CSV file into a Dataframe"""
    logging.info(f"Loading data from {filepath}")
    try:
        df = pd.read_csv(filepath)
        logging.info(f"Loaded data with shape: {df.shape}")
        return df
    except Exception as e:
        logging.error(f"Error loading data: {e}")
    return pd.DataFrame()
