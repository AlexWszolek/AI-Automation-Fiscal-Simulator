"""Redirect stub for the retired Streamlit prototype.

The tool now lives at aifiscalimpacts.alexwszolek.com; the URL query format is identical by
design (the golden-pinned codec), so every old shared link resolves on the new site with its
full configuration intact. To retire the prototype WITHOUT breaking those links, point the
Streamlit Community Cloud app's "Main file path" at THIS file (Settings → Main file path →
app/redirect_stub.py) — app/streamlit_app.py stays in the repo untouched, because it is the
source of truth the web copy extractor (scripts/extract_web_copy.py) reads.

The meta-refresh fires immediately; the visible page is the fallback for anything that
blocks it."""
from urllib.parse import urlencode

import streamlit as st

TARGET = "https://aifiscalimpacts.alexwszolek.com"


def forward_url(params: dict) -> str:
    """The new-site URL carrying the visitor's full configuration (identical query format)."""
    qs = urlencode(params, doseq=True)
    return f"{TARGET}/?{qs}" if qs else f"{TARGET}/"


url = forward_url(st.query_params.to_dict())
st.set_page_config(page_title="Moved — AI Automation Fiscal Simulator")
st.markdown(f'<meta http-equiv="refresh" content="0; url={url}">', unsafe_allow_html=True)
st.title("This tool has moved")
st.write(f"The AI Automation Fiscal Simulator now lives at **{TARGET}** — "
         "your shared settings carry over automatically.")
st.link_button("Open the simulator", url)
