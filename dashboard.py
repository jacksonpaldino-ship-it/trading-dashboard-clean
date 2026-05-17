import streamlit as st
import pandas as pd

st.set_page_config(layout="wide")

st.title("📈 Trading Dashboard")

st.success("Dashboard Online")

# =====================================
# FAKE TEST DATA
# =====================================

data = pd.DataFrame({
    "Equity": [2000, 2020, 2010, 2055]
})

st.line_chart(data)
