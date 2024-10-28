import streamlit as st
import plotly.express as px
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import os
from dotenv import load_dotenv
from datetime import datetime

# Load data from Google Sheets and handle expected headers
try:
    expected_headers = ["ProductID", "SalesRepID", "Location", "Date", "Units", "PercentOfStandardCost", "RevenueDiscount", "Year"]
    data = pd.DataFrame(sheet.get_all_records(expected_headers=expected_headers))
except Exception as e:
    st.error(f"Error loading data from Google Sheets: {e}")
    st.stop()

# Convert 'Date' column to datetime
data['Date'] = pd.to_datetime(data['Date'], errors='coerce', dayfirst=True)
data['Month'] = data['Date'].dt.month_name()
data['Quarter'] = data['Date'].dt.quarter
data['Year'] = data['Date'].dt.year

# Sidebar Filters
st.sidebar.title("Filters")
location_options = data['Location'].unique().tolist()
selected_location = st.sidebar.selectbox("Select Location", options=["All"] + location_options)
start_date = st.sidebar.date_input("Start Date", value=data['Date'].min())
end_date = st.sidebar.date_input("End Date", value=data['Date'].max())
month_options = data['Month'].unique().tolist()
selected_month = st.sidebar.multiselect("Select Month", options=month_options, default=month_options)
quarter_options = [1, 2, 3, 4]
selected_quarter = st.sidebar.multiselect("Select Quarter", options=quarter_options, default=quarter_options)
year_options = data['Year'].unique().tolist()
selected_year = st.sidebar.multiselect("Select Year", options=year_options, default=year_options)

# Function to filter data
def filter_data():
    filtered_data = data.copy()
    if selected_location != "All":
        filtered_data = filtered_data[filtered_data['Location'] == selected_location]
    filtered_data = filtered_data[(filtered_data['Date'] >= pd.to_datetime(start_date)) & 
                                  (filtered_data['Date'] <= pd.to_datetime(end_date))]
    if selected_month:
        filtered_data = filtered_data[filtered_data['Month'].isin(selected_month)]
    if selected_quarter:
        filtered_data = filtered_data[filtered_data['Quarter'].isin(selected_quarter)]
    if selected_year:
        filtered_data = filtered_data[filtered_data['Year'].isin(selected_year)]
    return filtered_data

# Filter the data
filtered_data = filter_data()

# Ensure there is data after filtering
if not filtered_data.empty:
    total_units = filtered_data['Units'].sum()
    st.title("HP Laptop Sales Analysis and Prediction")
    st.markdown(f"### Total Units Sold: {total_units}")

    # 1. Revenue by Subcategory Name (Pie Chart)
    subcategory_sales = filtered_data.groupby('SalesRepID')['Units'].sum().reset_index()
    fig1 = px.pie(subcategory_sales, values='Units', names='SalesRepID', title="Revenue by Subcategory Name")
    st.plotly_chart(fig1)

    # 2. Revenue by Year and Product Name (Bar Chart)
    numeric_columns = filtered_data.select_dtypes(include=['number']).columns

    # Group by Year and ProductID, summing numeric columns
    year_product_sales = filtered_data.groupby(['Year', 'ProductID'])[numeric_columns].sum()

    if 'Year' in year_product_sales.columns or 'ProductID' in year_product_sales.columns:
        year_product_sales = year_product_sales.drop(columns=['Year', 'ProductID'], errors='ignore')

    year_product_sales = year_product_sales.reset_index()

    # Plot bar chart for Revenue by Year and Product Name
    fig2 = px.bar(year_product_sales, x='Year', y='RevenueDiscount', color='ProductID', 
                title="Revenue by Year and Product Name")
    st.plotly_chart(fig2)

    # 3. Revenue by Product Name and Subcategory Name (Bar Chart)
    revenue_product_subcategory = filtered_data.groupby(['ProductID', 'SalesRepID'])['RevenueDiscount'].sum().reset_index()
    fig3 = px.bar(revenue_product_subcategory, x='ProductID', y='RevenueDiscount', color='SalesRepID', 
                title="Revenue by Product Name and Subcategory Name", barmode='group')
    st.plotly_chart(fig3)

    # 4. Gross Profit and MoM Growth by Month (Line Plot)
    month_sales = filtered_data.groupby('Month')['Units'].sum().reindex(
        ['January', 'February', 'March', 'April', 'May', 'June', 
         'July', 'August', 'September', 'October', 'November', 'December']).reset_index()
    fig4 = px.line(month_sales, x='Month', y='Units', title="Gross Profit and MoM Growth by Month")
    st.plotly_chart(fig4)

    # 5. Revenue and QoQ Growth by Quarter (Line Plot)
    quarter_sales = filtered_data.groupby('Quarter')['Units'].sum().reset_index()
    fig5 = px.line(quarter_sales, x='Quarter', y='Units', title="Revenue and QoQ Growth by Quarter")
    st.plotly_chart(fig5)

else:
    st.error("No data available for the selected filters.")

# --- CRUD Operations --- 
st.sidebar.title("CRUD Operations")
crud_options = ['Show Dataset', 'Add Row', 'Update Row', 'Delete Row']
selected_crud = st.sidebar.selectbox("Select CRUD Operation", options=crud_options)

# Show Dataset
if selected_crud == 'Show Dataset':
    st.write("### Current Dataset")
    st.dataframe(data)

# Add Row
if selected_crud == 'Add Row':
    st.write("### Add New Row")
    new_row = {}
    for col in expected_headers:  
        if col == "Date":
            new_row[col] = st.date_input(f"Enter {col}").strftime('%Y-%m-%d')
        else:
            new_row[col] = st.text_input(f"Enter {col}")
    if st.button("Add Row"):
        sheet.append_row(list(new_row.values()))
        st.success("Row added successfully.")
        st.experimental_set_query_params()

# Update Row
if selected_crud == 'Update Row':
    st.write("### Update Row")
    row_number = st.number_input("Enter the row number to update", min_value=2, step=1)
    row_data = sheet.row_values(row_number)
    st.write(f"Current Data for Row {row_number}: {row_data}")
    updated_values = {}
    for idx, key in enumerate(expected_headers):
        updated_value = st.text_input(f"Update {key}", row_data[idx] if idx < len(row_data) else "")
        updated_values[key] = updated_value
    if st.button("Update Row"):
        for idx, key in enumerate(expected_headers):
            if idx < len(row_data):
                row_data[idx] = updated_values[key]
            else:
                row_data.append(updated_values[key])
        sheet.update(f'A{row_number}:H{row_number}', [row_data])  
        st.success(f"Row {row_number} updated successfully.")
    st.experimental_set_query_params()

# Delete Row
if selected_crud == 'Delete Row':
    st.write("### Delete Row")
    row_number = st.number_input("Enter the row number to delete", min_value=2, step=1)
    if st.button("Delete Row"):
        sheet.delete_rows(row_number)
        st.success(f"Row {row_number} deleted successfully.")
    st.experimental_set_query_params()
