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


# add logic to export automate data export based on category and condition (senior)
def export_category_subset(dataframe: pd.DataFrame, category: str, export_path: str):
    """Export subset of the data based on category to a new CSV"""
    subset = dataframe[dataframe["Category"] == category]
    subset.to_csv(export_path, index=False)
    print(f"{category} data exported to {export_path}")
