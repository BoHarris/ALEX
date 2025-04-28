#🔐 ALEX – PII Sentinel API
A real-time, machine learning-powered privacy scanner to detect and redact Personally Identifiable Information (PII) from structured datasets.

🚀 Key Features
📁 Upload CSVs and auto-detect sensitive data

🧠 Predict PII columns using an XGBoost classifier trained for high accuracy

✂️ Instantly redact sensitive fields using AI + regex pattern detection

🔎 Covers emails, SSNs, IPs, phone numbers, and more

🪪 Returns a risk score based on detected sensitivity

📊 Feature-rich ML pipeline with custom value-based and metadata engineering

🧰 Built-in CLI tools for terminal use cases

📦 Modular FastAPI setup for rapid integration

🧠 Model Performance
We’ve transitioned to XGBoost with expanded features and a cleaned dataset.

✅ Accuracy
Achieved ~99.7–100% accuracy on internal validation sets with class_weight="balanced"

Optimized for real-world columns using actual PII/non-PII structures

Performance tracked via confusion matrix & prediction heatmaps

📈 API Output (/predict)
Returns:

```
{
  "filename": "example.csv",
  "pii_columns": ["email", "ssn"],
  "risk_score": "67%",
  "redacted_file": "redacted/example.csv"
}
```
🛠️ Usage Guide
1. Train the Model
```
python models/train_xgboost_model.py
Make sure pii_column.csv is present for initial training.
```

2. Start the API
```
uvicorn pii_app:app --reload
Visit: localhost:8000/docs
```

3. Upload & Redact
Upload .csv

View detected columns

Get downloadable redacted file + risk score

📁 Project Structure
```
ALEX/
├── pii_app.py                # FastAPI app
├── models/
│   ├── train_model.py
│   └── pii_features.py
├── utils/
│   └── redaction.py
├── uploads/                 # Raw file uploads
├── redacted/                # Cleaned/redacted CSVs
├── logs/                    # API logs
├── test_user_document.csv   # Sample test file
├── README.md
```
📆 Recent Updates (April 13, 2025)
✅ Switched to XGBoost classifier with enhanced metadata + value feature extraction

✅ Achieved ~100% test accuracy on core test dataset

✅ Device trust token table added for user auth enhancement

✅ Web frontend built using React + Tailwind

✅ Added routing, login/register pages, navbar, and improved UI/UX polish

🧾 Roadmap
```
🔍 UX Features
✅ Redacted preview & download link

🧪 User confirmation on flagged fields

🧠 Feature explanation toggle (why a field was flagged)

⚙️ CLI Tools
✅ --redact flag to batch redact via command line

⏳ --explain and --risk flags for detailed CLI results

📈 Analytics
📊 Log false positive rates and accuracy trends

🧮 Save confusion matrix per retraining session

📋 Dashboard with scan stats and performance metrics

📂 Format Support
✅ CSV support

⏳ XLSX & JSON support coming soon

🔐 Advanced Privacy Modes
⏳ Differential Privacy toggle for pseudonymization

✅ Regex + ML hybrid redaction in production

⏳ Tiered client privacy templates (configurable rules)
```
```
🌲 Custom Real-Time Random Tree Model
ALEX previously leveraged a custom Random Tree (RT) model for real-time PII classification. This lightweight model was optimized for speed and interpretability, making it ideal for early detection use cases and on-device processing.
Key highlights:
🧠 Trained using a curated set of metadata and content-based features
⚡ Ultra-fast inference times suited for real-time scanning
🔍 Clear decision paths to explain why a column was flagged as PII
🧪 Served as a foundation before transitioning to more advanced ensemble models like XGBoost
While ALEX has since upgraded its core model, the RT implementation proved essential for validating key detection strategies and setting the groundwork for more accurate PII protection.
It will continue to evolve as part of a multi-layered, AI-driven pipeline designed to ensure robust, privacy-first data handling.
/model/archive/train_random_forest.py
```

🤝 Contribute
Have an idea, pattern, or feedback?

Open an issue

Suggest a regex rule

Submit training samples or label improvements

👤 Author
Bo Harris
Privacy Engineer | ML Explorer | Ethical Tech Advocate
📫 bo.k.harris@gmail.com

