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
if 'current_view_path' not in st.session_state:
    st.session_state['current_view_path'] = st.session_state['root_path']

# Input Section
path_input = st.text_input("Directory Path:", value=st.session_state['root_path'])

if st.button("Analyze"):
    if os.path.exists(path_input) and os.path.isdir(path_input):
        st.session_state['root_path'] = path_input
        st.session_state['current_view_path'] = path_input
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
            height=700,
        )

        # Capture selection from the chart
        event = st.plotly_chart(fig, use_container_width=True, on_select="rerun")

        # Update view path based on chart selection
        if event and 'selection' in event and event['selection']['points']:
            try:
                # Get the ID of the clicked sector (which is the file path)
                clicked_id = event['selection']['points'][0]['id']
                st.session_state['current_view_path'] = clicked_id
            except (IndexError, KeyError):
                pass

        # Data Table for Management
        st.divider()
        st.subheader("Manage Files")
        st.caption(f"Current Path: {st.session_state['current_view_path']}")

        # Filter to show only immediate children of the current view path
        root_children = df[df['parent'] == st.session_state['current_view_path']].copy()
        root_children['formatted_size'] = root_children['value'].apply(format_bytes)
        root_children = root_children.sort_values('value', ascending=False)

        # Dataframe with selection
        selection = st.dataframe(
            root_children[['label', 'formatted_size', 'id']],
            use_container_width=True,
            column_config={
                "id": "Full Path",
                "label": "Name",
                "formatted_size": "Size"
            },
            on_select="rerun",
            selection_mode="single-row"
        )

        # Handle Dataframe Selection to update Delete Dropdown
        # If a row is selected, we update the session_state for the selectbox key
        if selection and "selection" in selection and selection.selection.rows:
            selected_row_idx = selection.selection.rows[0]
            # Map index back to the ID in the sorted dataframe
            if selected_row_idx < len(root_children):
                selected_id_from_table = root_children.iloc[selected_row_idx]['id']
                st.session_state['delete_selector'] = selected_id_from_table

        # Deletion Interaction
        st.subheader("Delete Item")

        # Selection
        options = root_children['id'].tolist()

        # Helper to safely format labels even if the list update lags slightly (though rerun handles it)
        def format_func(x):
            matches = root_children[root_children['id']==x]
            if not matches.empty:
                val = matches['value'].values[0]
                return f"{os.path.basename(x)} ({format_bytes(val)})"
            return os.path.basename(x)

        # We use a key to allow programmatic update from the table selection
        selected_path = st.selectbox(
            "Select item to delete:",
            options,
            format_func=format_func,
            key="delete_selector"
        )

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
