import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Define the path to your CSV file
csv_file_path = "~/Documents/baseline_grocery.csv"  # Update with your actual path

# Load the data
@st.cache_data
def load_data(file_path):
    return pd.read_csv(file_path)

data = load_data(csv_file_path)

# Define average American data (as an example)
average_data = {
    'Category': ['Food', 'Utilities', 'Rent', 'Entertainment', 'Transportation'],
    'Average_American_Spend': [500, 150, 1000, 200, 300]  # Example average values
}
average_df = pd.DataFrame(average_data)

# Streamlit app layout
st.title("Comparison of Your Spending Data with Average American Data")
st.write("### Your Data")
st.dataframe(data)  # Display your data as a table

# Merge your data with average data for comparison
merged_data = pd.merge(data, average_df, on='Category', how='left')

# Bar Chart: Your Data vs Average American Data
st.write("## Bar Chart: Your Spending vs Average American Spending")
fig_bar = go.Figure()
fig_bar.add_trace(go.Bar(
    x=merged_data['Category'],
    y=merged_data['Your_Spend'],  # Update to match your actual column name
    name='Your Spend'
))
fig_bar.add_trace(go.Bar(
    x=merged_data['Category'],
    y=merged_data['Average_American_Spend'],
    name='Average American Spend'
))
fig_bar.update_layout(barmode='group', title="Spending Comparison")
st.plotly_chart(fig_bar)

# Pie Chart: Distribution of Your Spending
st.write("## Pie Chart: Distribution of Your Spending")
fig_pie = px.pie(data, names='Category', values='Your_Spend', title="Your Spending Distribution")  # Update column names
st.plotly_chart(fig_pie)

# Line Chart: Cumulative Spending Over Categories (Example)
st.write("## Line Chart: Cumulative Spending Comparison")
fig_line = go.Figure()
fig_line.add_trace(go.Scatter(
    x=merged_data['Category'],
    y=merged_data['Your_Spend'].cumsum(),  # Cumulative sum of your spending
    mode='lines+markers',
    name='Your Cumulative Spend'
))
fig_line.add_trace(go.Scatter(
    x=merged_data['Category'],
    y=merged_data['Average_American_Spend'].cumsum(),
    mode='lines+markers',
    name='Average American Cumulative Spend'
))
fig_line.update_layout(title="Cumulative Spending Comparison")
st.plotly_chart(fig_line)

# Summary Stats and Analysis
st.write("## Summary Statistics")
st.write("Difference Between Your Spending and Average American Spending:")
merged_data['Difference'] = merged_data['Your_Spend'] - merged_data['Average_American_Spend']
st.dataframe(merged_data[['Category', 'Your_Spend', 'Average_American_Spend', 'Difference']])

# Additional Insights
st.write("### Additional Insights")
st.write("Categories where your spending exceeds the average:")
over_spend = merged_data[merged_data['Difference'] > 0]
st.dataframe(over_spend[['Category', 'Difference']])

st.write("Categories where your spending is below the average:")
under_spend = merged_data[merged_data['Difference'] < 0]
st.dataframe(under_spend[['Category', 'Difference']])

