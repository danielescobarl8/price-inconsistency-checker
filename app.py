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

if file is not None:
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
        
        # Save output file
        output_txt = io.StringIO()
        output_df.to_csv(output_txt, sep="|", index=False)
        output_content = output_txt.getvalue()
        
        # Allow download
        st.download_button(
            label="Download Price Inconsistency Report",
            data=output_content,
            file_name=f"{price_list_prefix}_Price_Inconsistencies.txt",
            mime="text/plain"
        )
        
        # Display summary table
        st.dataframe(output_df[["PID", "COLOR_ID", "CONSUMERPRICE", "Issue"]])
        
        st.success("✅ Price inconsistency report generated successfully!")
    else:
        st.info("No price inconsistencies found.")
