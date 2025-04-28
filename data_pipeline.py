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

from data_processing.load import load_data
from data_processing.clean import clean_data
from data_processing.transform import normalize_column, encode_column
from data_processing.aggregate import aggregate_data
from data_processing.categorize import categorize_age

# from ml.features import prepare_features
# from ml.labels import create_compliance_labels
import pandas as pd
import logging

import os

logging.basicConfig(level=logging.INFO)


# consolidate the pipeline to lead data, clean it, transform specific columns, categorize and export
def complete_pipeline(
    filepath: str,
    export_directory: str,
    filename: str = "processed_train.csv",
    clean: bool = True,
    transform: bool = True,
    categorize: bool = True,
) -> pd.DataFrame:
    logging.info("Starting pipeline")
    # load and clean
    try:
        df = load_data(filepath)
    except Exception as e:
        logging.error(f"Error Loading Data: {e}")
        return None, None
    if clean:
        try:
            df = clean_data(df)
            logging.info("Data cleaned successfully")
        except Exception as e:
            logging.error(f"Error cleaning data: {e}")
    if transform:
        # transform data
        if "Age" in df.columns:
            try:
                df = normalize_column(df, "Age")
                logging.info("Age column normalized successfully")
            except Exception as e:
                logging.error(f"Error normalizing Age column: {e}")
                return None, None
        else:
            logging.warning("Column 'age' not found in dataframe")
    if "Category" in df.columns:
        try:
            df = encode_column(df, "Category")
            logging.info("Category column encoded successfully")
        except Exception as e:
            logging.error(f"Error encoding Category column: {e}")
            return None, None
        logging.warning("Column 'Category' not found in dataframe")
    if categorize:
        # Categorize age groups
        try:
            df = categorize_age(df)
            logging.info("Age categorization completed successfully")
        except Exception as e:
            logging.error(f"Error categorizing Age: {e}")
            return None, None

    # Aggregate data by category
    try:
        aggregated_df = aggregate_data(df)
        logging.info("Data Aggregation completed successfully")
    except Exception as e:
        logging.info(f"Error aggregating data: {e}")
        return None, None

    # Ensure the export directory exists
    os.makedirs(export_directory, exist_ok=True)
    # construct paths for files
    processed_path = os.path.join(export_directory, filename)
    aggregated_path = os.path.join(export_directory, "aggregated_" + filename)

    # export both processed and aggregated data
    try:
        df.to_csv(processed_path, index=False)
        aggregated_df.to_csv(aggregated_path, index=False)
        logging.info(
            f"Data exported successfully to {processed_path} and aggregated_{aggregated_path}"
        )
    except Exception as e:
        logging.error(f"Error Exporting data: {e}")
        return None, None

    logging.info("Pipeline completed and exported")
    return df, aggregated_df


# usage

filepath = (
    "c:/Users/Bokha/OneDrive/Desktop/privacy-AI/DataOps Hub/resources/raw/train.csv"
)
export_directory = (
    "c:/Users/Bokha/OneDrive/Desktop/privacy-AI/DataOps Hub/resources/processed"
)
filename = "processed_train.csv"
processed_data, aggregated_data = complete_pipeline(
    filepath, export_directory, filename
)
