from io import StringIO
from loguru import logger
from pathlib import Path
import numpy as np
import pandas as pd
import requests
import streamlit as st
import tempfile
import time


# Define function to load and cache data from URLs
@st.cache_data
def load_csv_data(url):
    # Define the path for the cached file
    cache_dir = Path(tempfile.gettempdir()) / "shitstar_cache1"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached_file_path = cache_dir / f"{url.split('/')[-1]}"

    # Check if the file exists and is less than an hour old
    if cached_file_path.exists() and (time.time() - cached_file_path.stat().st_mtime) < 3600:
        # Read from cache
        return pd.read_csv(cached_file_path)
    else:
        # Fetch the data and cache it
        response = requests.get(url, timeout=90)
        response.raise_for_status()

        with cached_file_path.open("w") as f:
            f.write(response.text)

        return pd.read_csv(StringIO(response.text))


def calculate_roc(df):
    df["Rate of Change"] = df["Close"].pct_change(periods=30) * 100
    return df


# Load and cache the data
with st.spinner("Downloading coins data..."):
    coins_df = load_csv_data("https://s3.ca-central-1.amazonaws.com/cryptoai.dev/coins.csv")

with st.spinner("Downloading coin candle data..."):
    ohlcv_df = load_csv_data("https://s3.ca-central-1.amazonaws.com/cryptoai.dev/coin_daily_candles.csv")

with st.spinner("Analyzing Data..."):
    ohlcv_df = ohlcv_df.groupby("Abbr").apply(calculate_roc).reset_index(drop=True)

    # Merge the coins data with aggregated OHLCV data
    aggregated_df = coins_df.merge(ohlcv_df.groupby("Abbr")["Rate of Change"].mean().reset_index(), on="Abbr")

    # Ensure the 'Inception Date' column is timezone-naive before comparison
    aggregated_df["Inception Date"] = pd.to_datetime(aggregated_df["Inception Date"]).dt.tz_localize(None)

# Streamlit user interface
logger.debug("Displaying user interface")
st.title("Shitstar 💩")

# Form for filtering data
st.sidebar.header("Filter options")
market_cap_min = st.sidebar.number_input("Min Market Cap", min_value=0)
market_cap_max = st.sidebar.number_input("Max Market Cap", min_value=0, value=int(coins_df["MarketCap"].max()))
volume_min = st.sidebar.number_input("Min Volume", value=0, min_value=0)
percent_change_30d_min = st.sidebar.number_input("Min 30 Day Price Change (%)")
sort_column = st.selectbox("Sort by:", aggregated_df.columns[1:])

# Filter the DataFrame based on user input
filtered_df = aggregated_df[
    (aggregated_df["MarketCap"] >= market_cap_min)
    & (aggregated_df["MarketCap"] <= market_cap_max)
    & (aggregated_df["Volume"] >= volume_min)
    & (aggregated_df["Percent Change 30d"] >= percent_change_30d_min)
]

# Sort the results
filtered_df = filtered_df.sort_values(by=sort_column, ascending=False)

# Paginate the results
results_per_page = 100
total_pages = int(np.ceil(len(filtered_df) / results_per_page))
page = st.sidebar.slider("Page", 1, total_pages, 1)

start_index = (page - 1) * results_per_page
end_index = start_index + results_per_page

# Rename columns before displaying the DataFrame
filtered_df = filtered_df.rename(
    columns={
        "Percent Change 24h": "% 24h",
        "Percent Change 7d": "% 7d",
        "Percent Change 30d": "% 30d",
        "Percent Change 365d": "% Year",
        "Percent of ATH": "% of ATH",
        "Inception Date": "Inception",
        "MarketCap": "Market Cap",
    }
)

# Format the data
formatted_df = filtered_df.copy()


def format_large_number(value):
    if value >= 1_000_000_000_000:
        return f"${value / 1_000_000_000_000:.1f}T"
    elif value >= 1_000_000_000:
        return f"${value / 1_000_000_000:.1f}B"
    elif value >= 1_000_000:
        return f"${value / 1_000_000:.1f}M"
    elif value >= 1_000:
        return f"${value / 1_000:.1f}k"
    else:
        return f"${value:.0f}"


formatted_df["Market Cap"] = formatted_df["Market Cap"].apply(format_large_number)
formatted_df["Volume"] = formatted_df["Volume"].apply(format_large_number)

# Display the filtered DataFrame
st.write(formatted_df.iloc[start_index:end_index].to_html(escape=False, index=False), unsafe_allow_html=True)
