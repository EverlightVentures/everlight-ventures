To build a basic backend web application using Kivy and Streamlit that retrieves data from a spreadsheet, you can follow these general steps:

1. Install Dependencies: Make sure you have Python installed on your system. Install the necessary packages by running the following commands:
```shell
pip install kivy
pip install streamlit
pip install pandas
```

2. Prepare the Spreadsheet: Create or prepare a spreadsheet containing the data you want to retrieve. Save it in a compatible format, such as CSV or Excel (XLSX).

3. Kivy Backend:
   - Create a Python script and import the required modules:
   ```python
   import kivy
   from kivy.app import App
   from kivy.uix.label import Label
   ```
   - Create a class that inherits from `App` and defines the user interface:
   ```python
   class KivyApp(App):
       def build(self):
           return Label(text="Hello from Kivy!")
   ```
   - Instantiate and run the Kivy application:
   ```python
   if __name__ == '__main__':
       KivyApp().run()
   ```
   Running the script should display a basic Kivy app with a label showing "Hello from Kivy!".

4. Streamlit Backend:
   - Create another Python script and import the necessary modules:
   ```python
   import streamlit as st
   import pandas as pd
   ```
   - Load the spreadsheet data using Pandas:
   ```python
   @st.cache  # Caches the data to avoid loading it on every run
   def load_data():
       data = pd.read_csv('path/to/your/spreadsheet.csv')  # Replace with the path to your spreadsheet
       return data
   ```
   - Create the Streamlit app and retrieve the data:
   ```python
   def main():
       st.title('Backend Web App')
       data = load_data()
       st.write(data)  # Display the data in the app
   if __name__ == '__main__':
       main()
   ```
   Running this script should launch the Streamlit app in your browser, displaying the loaded data from the spreadsheet.

5. Run the Applications: Open two terminal windows, navigate to the directory containing the Kivy and Streamlit scripts, and run them simultaneously:
   ```shell
   python kivy_app.py
   ```
   ```shell
   streamlit run streamlit_app.py
   ```
   The Kivy app should display the Kivy interface, while the Streamlit app should show the loaded spreadsheet data.

You can further customize the user interface and data manipulation based on your specific requirements. Remember to replace `'path/to/your/spreadsheet.csv'` with the actual path to your spreadsheet file.