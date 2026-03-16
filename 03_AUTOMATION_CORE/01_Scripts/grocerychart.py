import streamlit as st
import pandas as pd

# Load CSV data with correct delimiter for tab-separated format
try:
    df = pd.read_csv("grocery_budget.csv", delimiter="\t", engine="python", skipinitialspace=True)
    df.columns = df.columns.str.strip()  # Remove any leading/trailing spaces in column names
except Exception as e:
    st.error(f"Error loading CSV file: {e}")

# Display column names to verify they loaded correctly
st.write("Columns in DataFrame:", df.columns.tolist())

# Display the first few rows to confirm the data loaded properly
st.write("First few rows of the DataFrame:")
st.write(df.head())

# Streamlit app title and description
st.title("Grocery Budget and Nutrition Data")
st.write("**Interactive View of Grocery Expenses and Nutritional Values**")

# Sidebar: Display Key Metrics if columns are available
try:
    st.sidebar.write("## Key Metrics")
    st.sidebar.write(f"**Total Monthly Cost:** ${df['Monthly Cost ($)'].sum():.2f}")
    st.sidebar.write(f"**Average Daily Cost:** ${df['Price per Day ($)'].mean():.2f}")
    st.sidebar.write(f"**Total Protein (g):** {df['Protein (g)'].sum()}g")
    st.sidebar.write(f"**Total Carbs (g):** {df['Carbs (g)'].sum()}g")
    st.sidebar.write(f"**Total Fat (g):** {df['Fat (g)'].sum()}g")
except KeyError as e:
    st.error(f"KeyError - check column names: {e}")

# Display the entire data table
st.write("### Grocery Items Table")
st.dataframe(df)

# Data filter for specific items
item_filter = st.multiselect("Select items to display", options=df["Item"].unique() if "Item" in df else [], default=df["Item"].unique() if "Item" in df else [])
filtered_df = df[df["Item"].isin(item_filter)] if "Item" in df else df

# Display filtered data table
st.write("### Filtered Grocery Items Table")
st.dataframe(filtered_df)

# Download button for filtered data
@st.cache
def convert_df(dataframe):
    return dataframe.to_csv(index=False).encode("utf-8")

if not filtered_df.empty:
    csv_data = convert_df(filtered_df)
    st.download_button(
        label="Download Filtered Data as CSV",
        data=csv_data,
        file_name="filtered_grocery_budget.csv",
        mime="text/csv"
    )

# Additional notes section
st.write("""
**Notes**:
- The total monthly cost, average daily cost, and nutrient totals are displayed in the sidebar.
- Use the filter to view specific items, and download filtered data if needed.
""")

