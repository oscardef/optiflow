import streamlit as st
import pandas as pd
import sqlite3

st.title("ESP32 Live Data Dashboard")

conn = sqlite3.connect("esp32_data.db")
data = pd.read_sql_query("SELECT * FROM messages ORDER BY id DESC LIMIT 50", conn)
st.dataframe(data)
