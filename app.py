import streamlit as st
import pandas as pd
import io

# Set up the app title
st.title("Price Inconsistency Checker")

# Country selection dropdown
st.subheader("Select Country")
country_options = {"Colombia": "CO", "Mexico": "MX", "Chile": "CL", "Argentina": "AR", "Brasil": "BR"}
selected_country = st.selectbox("Choose a country:", list(country_options.keys()))
price_list_prefix = country_options[selected_country] + "PriceList"

# File uploader
st.subheader("Upload Data Feed (TXT file, pipe-separated)")
file = st.file_uploader("Choose a TXT file", type=["txt"])

# Button to run the analysis
if file is not None:
    if st.button("Run Analysis"):
        # Read the data file
        df = pd.read_csv(file, delimiter="|", dtype=str)
        
        # Ensure required columns exist
        required_columns = {"PID", "COLOR_ID", "CONSUMERPRICE", "BASE_APPROVED", "COLOR_APPROVED", "SKU_APPROVED", "ECOM_ENABLED"}
        if not required_columns.issubset(df.columns):
            st.error(f"Missing required columns: {required_columns - set(df.columns)}")
            st.stop()
        
        # Convert approval columns to boolean
        approval_columns = ["BASE_APPROVED", "COLOR_APPROVED", "SKU_APPROVED", "ECOM_ENABLED"]
        df[approval_columns] = df[approval_columns].applymap(lambda x: str(x).strip().lower() == "true")
        
        # Convert CONSUMERPRICE to numeric, treating empty values as NaN
        df["CONSUMERPRICE"] = pd.to_numeric(df["CONSUMERPRICE"], errors='coerce')
        
        # Filter COLOR_IDs where at least one SKU meets approval criteria
        approved_colors = df[df[approval_columns].all(axis=1)]
        
        # Identify inconsistencies: different prices within the same COLOR_ID or missing prices
        inconsistent_prices = approved_colors.groupby("COLOR_ID").filter(
            lambda x: x["CONSUMERPRICE"].nunique() > 1 or x["CONSUMERPRICE"].isna().any()
        )
        
        # Prepare output
        if not inconsistent_prices.empty:
            inconsistent_prices["Issue"] = inconsistent_prices.groupby("COLOR_ID")["CONSUMERPRICE"].transform(
                lambda group: "No Price and Different Price" if group.isna().any() and group.nunique() > 1
                else "No Price" if group.isna().any()
                else "Different Price"
            )
            
            output_df = inconsistent_prices[["PID", "COLOR_ID", "CONSUMERPRICE", "Issue"]].copy()
            output_df.insert(0, "PRICE_LIST", price_list_prefix)
            output_df["CURRENCY_CODE"] = ""
            output_df["SCALE"] = ""
            output_df["UNIT_FACTOR"] = ""
            output_df["PRICE_START"] = ""
            output_df["PRICE_END"] = ""
            
            # Save output files
            price_impex_path = f"{price_list_prefix}_Price_Impex.xlsx"
            reason_report_path = f"{price_list_prefix}_Price_Issues.xlsx"
            
            with pd.ExcelWriter(price_impex_path) as writer:
                output_df.drop(columns=["Issue"]).to_excel(writer, index=False, sheet_name="Price Impex")
            with pd.ExcelWriter(reason_report_path) as writer:
                output_df.to_excel(writer, index=False, sheet_name="Price Issues")
            
            # Allow downloads
            with open(price_impex_path, "rb") as file:
                st.download_button("Download Price Impex File", file, file_name=price_impex_path)
            with open(reason_report_path, "rb") as file:
                st.download_button("Download Price Issue Report", file, file_name=reason_report_path)
            
            # Display summary table
            st.dataframe(output_df[["PID", "COLOR_ID", "CONSUMERPRICE", "Issue"]])
            
            st.success("✅ Price inconsistency reports generated successfully!")
        else:
            st.info("No price inconsistencies found.")

# Footer Explanation
st.markdown("""
### Explanation of the App Logic:
This tool checks for price inconsistencies within product color variations. It analyzes if all SKUs under the same COLOR_ID have the same price. If any SKU has a missing or different price, it is flagged and included in the output files.

### Input File Requirements:
- The file must be a **TXT file** separated by **pipes (|)**.
- It must include the following required columns:
  - **PID** (Product ID)
  - **COLOR_ID** (Color Variation ID)
  - **CONSUMERPRICE** (Product Price)
  - **BASE_APPROVED**, **COLOR_APPROVED**, **SKU_APPROVED**, **ECOM_ENABLED** (All must be "True" for the product to be considered)
- Only products that have at least one SKU approved for e-commerce are analyzed.
""")
