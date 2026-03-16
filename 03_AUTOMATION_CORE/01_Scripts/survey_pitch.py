import streamlit as st
import streamlit.components.v1 as components

# Read the HTML file from the specified path
html_file_path = "/home/richgee/Documents/survey_pitch.html"

# Open and read the HTML content from the file
with open(html_file_path, "r") as f:
    html_content = f.read()

# Display the HTML content in Streamlit
components.html(html_content, height=600)

