import os
import shutil
import pandas as pd
import streamlit as st
import plotly.express as px
from typing import List, Dict, Optional
from utils import get_dir_size, format_bytes, scan_directory

# --- UI Layout ---

st.set_page_config(page_title="Disk Usage Analyzer", layout="wide")
st.title("📂 Disk Usage Analyzer")

# Initialize Session State
if 'scanned_data' not in st.session_state:
    st.session_state['scanned_data'] = None
if 'root_path' not in st.session_state:
    st.session_state['root_path'] = os.getcwd()

# Input Section
path_input = st.text_input("Directory Path:", value=st.session_state['root_path'])

if st.button("Analyze"):
    if os.path.exists(path_input) and os.path.isdir(path_input):
        st.session_state['root_path'] = path_input
        progress_bar = st.progress(0, text="Starting scan...")

        # We'll use a slightly different scanning approach for the main loop to ensure we capture the root children correctly
        # The `scan_directory` function above was a bit mixed. Let's refine it.
        # Actually, let's rewrite the scanner to be simpler and more robust for the chart.
        # We need a flat list of all nodes.

        with st.spinner('Scanning...'):
             # Reset data
             # Use the shared scanner logic from utils
            raw_data = scan_directory(path_input, progress_bar.progress)
            st.session_state['scanned_data'] = raw_data

        progress_bar.empty()
    else:
        st.error("Invalid Directory Path")

# Visualization Section
if st.session_state['scanned_data']:
    df = pd.DataFrame(st.session_state['scanned_data'])

    # Handle case where value is 0 (Plotly doesn't like 0 values in Sunburst sometimes, or they just disappear)
    df = df[df['value'] > 0]

    if not df.empty:
        fig = px.sunburst(
            df,
            names='label',
            parents='parent',
            values='value',
            branchvalues='total',
            ids='id',
        )
        st.plotly_chart(fig, use_container_width=True)

        # Data Table for Management
        st.divider()
        st.subheader("Manage Files")

        # Filter to show only immediate children of the root path for easier management
        root_children = df[df['parent'] == st.session_state['root_path']].copy()
        root_children['formatted_size'] = root_children['value'].apply(format_bytes)
        root_children = root_children.sort_values('value', ascending=False)

        st.dataframe(
            root_children[['label', 'formatted_size', 'id']],
            use_container_width=True,
            column_config={
                "id": "Full Path",
                "label": "Name",
                "formatted_size": "Size"
            }
        )

        # Deletion Interaction
        st.subheader("Delete Item")

        # Selection
        options = root_children['id'].tolist()
        # Map full path to readable label for dropdown
        format_func = lambda x: f"{os.path.basename(x)} ({format_bytes(root_children[root_children['id']==x]['value'].values[0])})"

        selected_path = st.selectbox("Select item to delete:", options, format_func=format_func)

        # Delete State Management
        if 'confirm_stage' not in st.session_state:
            st.session_state['confirm_stage'] = 0
            st.session_state['target_to_delete'] = None

        def reset_delete_state():
            st.session_state['confirm_stage'] = 0
            st.session_state['target_to_delete'] = None

        if st.button("Delete Selected"):
            st.session_state['target_to_delete'] = selected_path
            st.session_state['confirm_stage'] = 1

        if st.session_state['confirm_stage'] == 1 and st.session_state['target_to_delete'] == selected_path:
            target = st.session_state['target_to_delete']
            cmd = f"rm -rf '{target}'"
            st.warning(f"⚠️ Are you sure? This will execute the following command:")
            st.code(cmd, language="bash")
            st.write("This action cannot be undone.")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("Yes, I am sure (Execute)"):
                    try:
                        if os.path.isdir(target):
                            shutil.rmtree(target)
                        else:
                            os.remove(target)
                        st.success(f"Deleted: {target}")
                        reset_delete_state()
                        # Rerun analysis to update view
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting file: {e}")
            with col2:
                if st.button("Cancel"):
                    reset_delete_state()

    else:
        st.info("No data to display (Folder might be empty).")
