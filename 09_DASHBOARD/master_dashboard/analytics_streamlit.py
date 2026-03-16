import json
from pathlib import Path
import pandas as pd
import streamlit as st

CACHE_DIR = Path("/mnt/sdcard/AA_MY_DRIVE/.aa_dashboard_cache")

st.set_page_config(page_title="AA Analytics", layout="wide")
st.title("AA File Analytics")

index_files = sorted(CACHE_DIR.glob("index_*.json"))
if not index_files:
    st.warning("No index found. Run the dashboard once to build the index.")
    st.stop()

index_path = index_files[0]
index = json.loads(index_path.read_text())
items = index.get("items", [])

if not items:
    st.warning("Index is empty.")
    st.stop()

_df = pd.DataFrame(items)
_df["size_mb"] = _df["size"] / (1024 * 1024)
_df["ext"] = _df["ext"].fillna("")
_df["group"] = _df["group"].fillna("other")

col1, col2, col3 = st.columns(3)
col1.metric("Files", f"{len(_df):,}")
col2.metric("Total Size (GB)", f"{_df['size'].sum() / (1024**3):.2f}")
col3.metric("Avg Size (MB)", f"{_df['size_mb'].mean():.2f}")

st.subheader("By Category")
cat = _df.groupby("group").size().reset_index(name="count")
st.bar_chart(cat, x="group", y="count")

st.subheader("Size by Category (GB)")
cat_size = _df.groupby("group")["size"].sum().reset_index()
cat_size["size_gb"] = cat_size["size"] / (1024**3)
st.bar_chart(cat_size, x="group", y="size_gb")

st.subheader("Top Extensions")
ext = _df.groupby("ext").size().reset_index(name="count").sort_values("count", ascending=False).head(20)
st.bar_chart(ext, x="ext", y="count")

st.subheader("Largest Files")
st.dataframe(_df.sort_values("size", ascending=False).head(50)[["name", "path", "size", "group", "ext"]])
