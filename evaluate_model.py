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
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
)
import seaborn as sns
from sklearn.model_selection import cross_val_score
import matplotlib.pyplot as plt
import os


def evaluate_model(y_true, y_pred):
    """Calculate and print basic evaluation metrics"""
    accuracy = accuracy_score(y_true, y_pred)
    precision = precision_score(y_true, y_pred)
    recall = recall_score(y_true, y_pred)
    f1 = f1_score(y_true, y_pred)

    print(f"Accuracy: {accuracy: .2f}")
    print(f"Precision: {precision: .2f}")
    print(f"Recall: {recall:.2f}")
    print(f"F1 Score: {f1: .2f}")

    return accuracy, precision, recall, f1


def plot_confusion_matrix(
    y_true,
    y_pred,
    save=True,
    path="C:/Users/Bokha/OneDrive/Desktop/privacy-AI/DataOps Hub/ml/",
):
    """Plot the confusion matrix"""
    cm = confusion_matrix(y_true, y_pred)
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=["Non-Compliant", "Compliant"],
        yticklabels=["Non-Compliant", "Compliant"],
    )
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.title("Confusion Matrix")

    # Check if `save` is true, then save the plot as an image
    if save:
        save_path = os.path.join(path, "confusion_matrix.png")
        plt.savefig(save_path)  # save the plat as a png
        print("Confusion matrix saved as a PNG at {save_path}")
    else:
        plt.show()


def cross_validate_model(model, X, y, cv=5):
    """Perform cross-validation and print the average accuracy"""
    scores = cross_val_score(model, X, y, cv=cv, scoring="accuracy")
    print(f"Cross-Validation Accuracy (average of {cv} fold): {scores.mean(): .2f}")
    return scores


# Dummy test values
y_test = [0, 1, 0, 1, 1]  # replace with actual test result labels
y_pred = [0, 1, 0, 0, 1]  # replace with model predictions

# Calculate metrics and plot confusion matrix
evaluate_model(y_test, y_pred)
plot_confusion_matrix(y_test, y_pred)
