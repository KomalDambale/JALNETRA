import os
import pandas as pd

from xgboost import XGBRegressor, XGBClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, accuracy_score
from joblib import dump

print("=" * 50)
print("JALNETRA MODEL TRAINING")
print("=" * 50)

# Create models folder
os.makedirs("models", exist_ok=True)

# Load dataset
DATA_PATH = "data/groundwater_data.csv"

print(f"Loading Dataset: {DATA_PATH}")

df = pd.read_csv(DATA_PATH)

# Clean column names
df.columns = df.columns.str.strip()

print("\nColumns Found:")
print(df.columns.tolist())

# -----------------------------------
# Clean Extraction Stage
# -----------------------------------

df["Extraction Stage (%)"] = (
    df["Extraction Stage (%)"]
    .astype(str)
    .str.replace("%", "", regex=False)
    .str.strip()
)

# -----------------------------------
# Numeric Columns
# -----------------------------------

numeric_cols = [
    "Year",
    "Pre-Monsoon Level (mbgl)",
    "Post-Monsoon Level (mbgl)",
    "Annual Recharge (MCM)",
    "Extractable Resource (MCM)",
    "Total Extraction (MCM)",
    "Extraction Stage (%)"
]

for col in numeric_cols:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Fill missing numeric values

for col in numeric_cols:
    df[col] = df[col].fillna(df[col].median())

# Fill category nulls

df["Groundwater Category"] = (
    df["Groundwater Category"]
    .fillna("Safe")
    .astype(str)
    .str.strip()
)
bad_values = [
    "Groundwater Category",
    "Semi-Critical [1.33]",
    "Safe [1.33]",
    "Critical [1.33]",
    "Over-Exploited [1.33]"
]

df = df[
    ~df["Groundwater Category"].isin(bad_values)
]

# -----------------------------------
# Remove Rare Categories
# -----------------------------------

category_counts = df["Groundwater Category"].value_counts()

valid_categories = category_counts[
    category_counts >= 2
].index

df = df[
    df["Groundwater Category"].isin(valid_categories)
]

print("\nGroundwater Category Counts:")
print(df["Groundwater Category"].value_counts())
print("\nRecords after cleaning:", len(df))

# -----------------------------------
# Features
# -----------------------------------

FEATURES = [
    "Year",
    "Pre-Monsoon Level (mbgl)",
    "Post-Monsoon Level (mbgl)",
    "Annual Recharge (MCM)",
    "Extractable Resource (MCM)",
    "Total Extraction (MCM)"
]

X = df[FEATURES]

# ==================================================
# STAGE MODEL
# ==================================================

print("\nTraining Stage Model...")

y_stage = df["Extraction Stage (%)"]

X_train_s, X_test_s, y_train_s, y_test_s = train_test_split(
    X,
    y_stage,
    test_size=0.20,
    random_state=42
)

stage_model = XGBRegressor(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=5,
    subsample=0.8,
    colsample_bytree=0.8,
    random_state=42
)

stage_model.fit(X_train_s, y_train_s)

stage_pred = stage_model.predict(X_test_s)

mae = mean_absolute_error(
    y_test_s,
    stage_pred
)

print("Stage MAE:", round(mae, 2))

dump(
    stage_model,
    "models/xgb_stage.pkl"
)

print("Saved: models/xgb_stage.pkl")

# ==================================================
# CATEGORY MODEL
# ==================================================

print("\nTraining Category Model...")

encoder = LabelEncoder()

y_category = encoder.fit_transform(
    df["Groundwater Category"]
)

X_train_c, X_test_c, y_train_c, y_test_c = train_test_split(
    X,
    y_category,
    test_size=0.20,
    random_state=42
)

num_classes = len(
    encoder.classes_
)

category_model = XGBClassifier(
    n_estimators=300,
    learning_rate=0.05,
    max_depth=5,
    random_state=42,
    objective="multi:softmax",
    num_class=num_classes,
    eval_metric="mlogloss"
)

category_model.fit(
    X_train_c,
    y_train_c
)

category_pred = category_model.predict(
    X_test_c
)

accuracy = accuracy_score(
    y_test_c,
    category_pred
)

print(
    "Category Accuracy:",
    round(accuracy * 100, 2),
    "%"
)

dump(
    category_model,
    "models/xgb_category.pkl"
)

dump(
    encoder,
    "models/label_encoder.pkl"
)

print("Saved: models/xgb_category.pkl")
print("Saved: models/label_encoder.pkl")

print("=" * 50)
print("TRAINING COMPLETED SUCCESSFULLY")
print("=" * 50)