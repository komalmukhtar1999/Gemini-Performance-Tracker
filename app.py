import os
import textwrap
import traceback
from datetime import datetime
from typing import Optional

from flask import Flask, request, jsonify
from dotenv import load_dotenv
import pandas as pd
import google.generativeai as genai

# =========================
# Setup & Configuration
# =========================
load_dotenv()

GOOGLE_API_KEY = "AIzaSyDq3DMTv1-BdMc_l0u4MaqXqnCiIxjsssc"
SALES_CSV = r"E:\assignment\sales_performance_data.csv"

#if not GOOGLE_API_KEY:
    #print("[WARN] GOOGLE_API_KEY is missing. LLM insights will fail until provided in .env")

# Configure Gemini (will raise later if key missing)
if GOOGLE_API_KEY:
    genai.configure(api_key=GOOGLE_API_KEY)

# Load data once
def _load_sales_df(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Normalize/prepare columns expected by the notebook
    # dated -> datetime; revenue_total = confirmed + pending (when available)
    if "dated" in df.columns:
        df["dated"] = pd.to_datetime(df["dated"], errors="coerce")
    if {"revenue_confirmed", "revenue_pending"}.issubset(df.columns):
        df["revenue_total"] = df["revenue_confirmed"] + df["revenue_pending"]
    # Some datasets have "employee_id" and/or "employee_name"
    return df

try:
    DF = _load_sales_df(SALES_CSV)
except FileNotFoundError:
    print(f"[ERROR] Could not find CSV at {SALES_CSV}. Set SALES_CSV in .env.")
    DF = pd.DataFrame()  # keep app bootable; endpoints will 400

# =========================
# Core LLM helpers (from your notebook, adapted)
# =========================
def _llm_generate(prompt: str) -> str:
    """
    Calls Gemini and returns raw text. If key is missing or call fails,
    returns a helpful fallback note instead of crashing.
    """
    if not GOOGLE_API_KEY:
        return "LLM not configured. Please set GOOGLE_API_KEY in .env."
    try:
        model = genai.GenerativeModel("gemini-1.5-flash")
        resp = model.generate_content(prompt)
        return resp.text.strip()
    except Exception as e:
        return f"LLM error: {e}"

def analyze_sales_performance(data_str: str, analysis_type: str = "individual") -> str:
    if analysis_type == "individual":
        prompt = f"""
ROLE: Senior Sales Coach
TASK: Analyze sales representative performance and provide:
- 2 key strengths
- 2 critical weaknesses
- 2 actionable suggestions
- 1 quick win opportunity

SALES DATA:
{data_str}

RESPONSE FORMAT:
### Strengths
[bullet points]

### Weaknesses
[bullet points]

### Actionable Suggestions
[numbered list]

### Quick Win
[one short, concrete win]
""".strip()
    elif analysis_type == "team":
        prompt = f"""
ROLE: VP Sales
TASK: Provide a concise performance summary for the sales team, including:
- 3 top observations
- 2 risks
- 3 recommendations

TEAM SUMMARY (stats or aggregates):
{data_str}

RESPONSE FORMAT:
### Observations
[bulleted]

### Risks
[bulleted]

### Recommendations
[numbered]
""".strip()
    else:
        prompt = f"Summarize this sales data:\n\n{data_str}"

    raw = _llm_generate(prompt)
    return textwrap.indent(raw, "> ")

def analyze_trends(df: pd.DataFrame, time_period: str = "monthly") -> str:
    # Prepare period column
    dft = df.copy()
    if "dated" not in dft.columns:
        return "> No 'dated' column found. Cannot compute trends."

    if time_period.lower() == "weekly":
        dft["period"] = dft["dated"].dt.to_period("W")
    else:
        dft["period"] = dft["dated"].dt.to_period("M")

    # Aggregate common metrics when available
    agg_fields = {}
    for col in ["lead_taken", "tours_booked", "applications", "revenue_total"]:
        if col in dft.columns:
            agg_fields[col] = "sum"

    if not agg_fields:
        # Fallback: count records per period
        agg = dft.groupby("period").size().rename("records").to_frame()
    else:
        agg = dft.groupby("period").agg(agg_fields)

    trends_table = agg.to_string()

    prompt = f"""
ROLE: Sales Operations Analyst
TASK: Analyze historical sales trends and forecast the next period. Keep it crisp.

TRENDS TABLE (grouped by {time_period}):
{trends_table}

RESPONSE FORMAT:
### Trend Summary
[2–3 bullets on key movements]

### Forecast
[next-period prediction with a short justification]

### Growth Opportunities
[2 short bullets]
""".strip()

    raw = _llm_generate(prompt)
    return textwrap.indent(raw, "> ")

# =========================
# Flask App
# =========================
app = Flask(__name__)

def _ensure_df_loaded():
    if DF.empty:
        return None, ("Sales dataset is empty or missing. "
                      "Check SALES_CSV path and file contents."), 400
    return DF, None, None

def _find_rep_rows(df: pd.DataFrame, rep_id: str) -> pd.DataFrame:
    """
    Tries to resolve rep_id against common columns:
    - employee_id (exact match)
    - employee_name (case-insensitive exact match)
    If neither present, returns empty.
    """
    if "employee_id" in df.columns:
        m1 = df[df["employee_id"].astype(str) == str(rep_id)]
        if not m1.empty:
            return m1
    if "employee_name" in df.columns:
        m2 = df[df["employee_name"].astype(str).str.casefold() == str(rep_id).casefold()]
        if not m2.empty:
            return m2
    return pd.DataFrame()

@app.route("/api/rep_performance", methods=["GET"])
def rep_performance():
    df, msg, code = _ensure_df_loaded()
    if msg:
        return jsonify({"ok": False, "error": msg}), code

    rep_id = request.args.get("rep_id", "").strip()
    if not rep_id:
        return jsonify({"ok": False, "error": "Missing required query param: rep_id"}), 400

    rows = _find_rep_rows(df, rep_id)
    if rows.empty:
        return jsonify({"ok": False, "error": f"No records found for rep_id='{rep_id}'"}), 404

    # Use the most recent row if dates exist, else first row
    use_row = rows.sort_values("dated").iloc[-1] if "dated" in rows.columns else rows.iloc[0]
    record = use_row.to_dict()

    insights = analyze_sales_performance(record, analysis_type="individual")

    return jsonify({
        #"ok": True,
        #"rep_id": rep_id,
        #"used_record": record,
        "insights": insights
    }), 200

@app.route("/api/team_performance", methods=["GET"])
def team_performance():
    df, msg, code = _ensure_df_loaded()
    if msg:
        return jsonify({"ok": False, "error": msg}), code

    # High-level stats similar to your notebook
    summary = df.describe(include="all").to_string()
    insights = analyze_sales_performance(summary, analysis_type="team")

    return jsonify({
        #"ok": True,
        #"summary_stats": summary,
        "insights": insights
    }), 200

@app.route("/api/performance_trends", methods=["GET"])
def performance_trends():
    df, msg, code = _ensure_df_loaded()
    if msg:
        return jsonify({"ok": False, "error": msg}), code

    time_period = (request.args.get("time_period", "monthly") or "monthly").lower()
    if time_period not in {"monthly", "weekly"}:
        return jsonify({"ok": False, "error": "time_period must be 'monthly' or 'weekly'"}), 400

    insights = analyze_trends(df, time_period=time_period)

    return jsonify({
        #"ok": True,
        "time_period": time_period,
        "insights": insights
    }), 200

# Health check
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "time": datetime.utcnow().isoformat() + "Z"}), 200

if __name__ == "__main__":
    # FLASK_RUN_PORT or default 8000
    port = int(os.getenv("PORT", "8000"))
    app.run(host="0.0.0.0", port=port, debug=True)
