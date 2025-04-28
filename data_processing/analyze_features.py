import pandas as pd
import numpy as np
import seaborn as sns
import matplotlib.pyplot as plt
import ast
import re

#load dataset
df = pd.read_csv("pii_column.csv")
df["is_pii"] = df["pii"].map({"yes":0, "no": 1})
def safe_parse(val):
    try:
        return ast.literal_eval(val)
    except(ValueError, SyntaxError):
        return[]

df["parsed_values"] = df["value_samples"].apply(safe_parse)

# Value-based features
EMAIL_RE = re.compile(r"[^@]+@[^@]+\.[^@]+")
SSN_RE = re.compile(r"\d{3}-\d{2}-\d{4}")
IP_RE = re.compile(r"(?:\d{1,3}\.){3}\d{1,3}")

def pct_match(regex, values):
    return np.mean([bool(regex.search(str(v))) for v in values])

df["pct_email_like"] = df["parsed_values"].apply(lambda v: pct_match(EMAIL_RE, v))
df["pct_ssn_like"] = df["parsed_values"].apply(lambda v: pct_match(SSN_RE, v))
df["pct_ip_like"] = df["parsed_values"].apply(lambda v: pct_match(IP_RE, v))
df["avg_digits_per_val"] = df["parsed_values"].apply(lambda v: np.mean([sum(c.isdigit() for c in str(i)) for i in v]))
df["avg_val_len"] = df["parsed_values"].apply(lambda v: np.mean([len(str(i)) for i in v]))

#histogram: one email
sns.histplot(data=df, x="pct_email_like", hue="is_pii", multiple="stack", bins=10)
plt.title("Distribution of pct_email_like by PII Label")
plt.show()

#pairplot
sns.pairplot(df[["pct_email_like", "pct_ssn_like", "pct_ip_like", "avg_val_len", "avg_digits_per_val", "is_pii"]],
             hue="is_pii")
plt.suptitle("Feature Interactions by PII Label", y=1.02)
plt.show()

#Correlation Heatmap
plt.figure(figsize=(10,6))
sns.heatmap(df.corr(numeric_only=True), annot=True, fmt=".2f",cmap="coolwarm")
plt.title("Feature Correlation Matrix")
plt.show()
