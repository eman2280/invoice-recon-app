import streamlit as st
import pandas as pd
import fitz  # PyMuPDF
import re
import io

st.title("Vendor Invoice Reconciliation Tool")

# --- File Uploads ---
vendor_file = st.file_uploader("Upload Vendor Statement (PDF)", type=["pdf"])
ap_file = st.file_uploader("Upload Accounts Payable Ledger (Excel)", type=["xlsx"])

if vendor_file and ap_file:
    st.success("Files uploaded. Processing...")

    # --- Process Vendor Statement ---
    pdf_doc = fitz.open(stream=vendor_file.read(), filetype="pdf")
    vendor_text = "\n".join([page.get_text() for page in pdf_doc])

    invoice_pattern = re.compile(r"(\d{2}/\d{2}/\d{4})\s+Invoice\s+#(\d+)[^\d]*(\d{1,3}(?:,\d{3})*(?:\.\d{2}))")
    matches = invoice_pattern.findall(vendor_text)

    vendor_df = pd.DataFrame(matches, columns=["Date", "Invoice #", "Amount"])
    vendor_df["Invoice #"] = vendor_df["Invoice #"].astype(str)
    vendor_df["Amount"] = vendor_df["Amount"].str.replace(",", "").astype(float)

    # --- Process AP Ledger ---
    xls = pd.ExcelFile(ap_file)
    ap_df = xls.parse(xls.sheet_names[0], skiprows=4)
    ap_df.columns = ["Payable Name", "Invoice #", "Amount", "RO #", "Posted", "G/L Acct #"]
    ap_df = ap_df.dropna(subset=["Invoice #", "Amount"])
    ap_df["Invoice #"] = ap_df["Invoice #"].astype(str).str.strip()

    # --- Reconcile ---
    merged_df = pd.merge(
        vendor_df,
        ap_df[["Invoice #", "Amount"]],
        on="Invoice #",
        how="left",
        suffixes=("_Vendor", "_AP")
    )

    def classify(row):
        if pd.isna(row["Amount_AP"]):
            return "Missing in AP"
        elif abs(row["Amount_Vendor"] - row["Amount_AP"]) > 0.01:
            return "Amount Mismatch"
        else:
            return "Matched"

    merged_df["Match Status"] = merged_df.apply(classify, axis=1)

    st.subheader("Reconciliation Result")
    st.dataframe(merged_df)

    # --- Download Option ---
    towrite = io.BytesIO()
    merged_df.to_excel(towrite, index=False, engine='openpyxl')
    towrite.seek(0)
    st.download_button(
        label="📥 Download Reconciliation Report",
        data=towrite,
        file_name="reconciliation_report.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
