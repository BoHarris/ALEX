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


def create_compliance_lables(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Generate lables for compliance based on given rules"""
    # Define compliance based rule
    if "sensitive_data" in dataframe.columns:
        dataframe["compliance_label"] = dataframe["sensitive_data"].apply(
            lambda x: 1 if x == "high" else 0
        )
    else:
        print("Warning: 'Sensitive_data' column not found for labeling compliance.")
    return dataframe
