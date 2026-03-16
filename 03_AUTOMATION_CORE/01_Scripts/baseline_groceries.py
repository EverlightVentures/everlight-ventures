import streamlit as st
import pandas as pd
import os

# Define the file path to the CSV file
csv_file_path = os.path.expanduser("~/Documents/baseline_expense.csv")

# Load the CSV file function
def load_data(file_path):
    try:
        data = pd.read_csv(file_path)
        return data
    except FileNotFoundError:
        st.error("The file was not found. Please check the file path.")
        return None

# Main function for the Streamlit app
def main():
    st.title("Baseline Grocery Data Viewer")

    # Load data
    data = load_data(csv_file_path)
    
    if data is not None:
        st.write("### Data Preview:")
        st.dataframe(data)  # Display the data in table format
        st.write("### Descriptive Statistics:")
        st.write(data.describe())  # Display basic statistics
    else:
        st.error("Could not load data from the specified file.")

if __name__ == "__main__":
    main()


