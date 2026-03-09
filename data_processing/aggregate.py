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


# Aggregate data
def aggregate_data(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Aggregate data by Category, calculating summary statics for each group."""
    # category by the "Category" column and calculate summary stastics for each group.
    return dataframe.groupby("Category").agg({"Age": ["mean", "min", "max", "std"]})
