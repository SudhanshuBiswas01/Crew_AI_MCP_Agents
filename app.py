import streamlit as st
import os
import json
import pandas as pd
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Ensure we read environment variables
load_dotenv()

st.set_page_config(
    page_title="Operations Assistant - CrewAI & MCP",
    page_icon="⚙️",
    layout="wide",
)

# Custom premium styling
st.markdown("""
    <style>
    .main {
        background-color: #0e1117;
        color: #ffffff;
    }
    h1, h2, h3 {
        color: #00f2fe !important;
        font-family: 'Outfit', 'Inter', sans-serif;
    }
    .stButton>button {
        background: linear-gradient(45deg, #00c6ff, #0072ff);
        color: white;
        border: none;
        padding: 10px 24px;
        font-weight: bold;
        border-radius: 8px;
        transition: 0.3s all ease;
    }
    .stButton>button:hover {
        background: linear-gradient(45deg, #00f2fe, #4facfe);
        transform: translateY(-2px);
        box-shadow: 0 4px 15px rgba(0, 242, 254, 0.4);
    }
    .report-card {
        background: rgba(255, 255, 255, 0.05);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 20px;
        margin-top: 20px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚙️ Operations Assistant Dashboard")
st.markdown("### Powered by CrewAI + Model Context Protocol (MCP)")

# Add a sidebar for data visualization and parameters
st.sidebar.title("Configuration & Insights")

# Model configuration
model_name = os.getenv("MODEL_NAME", "ollama/qwen2.5:0.5b")
st.sidebar.metric(label="Active LLM Model", value=model_name.replace("ollama/", ""))

# Show current inventory order status counts from the CSV if exists
csv_path = Path("data/inventory_orders.csv")
if csv_path.exists():
    st.sidebar.markdown("---")
    st.sidebar.markdown("#### Inventory Quick stats")
    try:
        df = pd.read_csv(csv_path)
        st.sidebar.write(f"**Total Registered Orders:** {len(df)}")
        status_counts = df['status'].value_counts()
        st.sidebar.dataframe(status_counts)
    except Exception as e:
        st.sidebar.error(f"Error loading CSV stats: {e}")

# Form to input user question
st.markdown("### Ask a Business Question")
question = st.text_area(
    "Enter your operational query (e.g., about shipping policies, order status, returns, low stock alerts):",
    value="What is the current status of our top 3 orders and what does our return policy say?",
    height=80
)

if st.button("Run Assistant Pipeline"):
    with st.spinner("Executing CrewAI agents (Researcher, Writer, Validator) with MCP Tools..."):
        # Import run_crew dynamically or run it as python subprocess to avoid import collision
        import subprocess
        import sys
        
        # Execute the python entrypoint and capture output
        stdout_val = ""
        stderr_val = ""
        try:
            # Copy environment to pass it explicitly to the subprocess
            env = os.environ.copy()
            
            result = subprocess.run(
                [sys.executable, "-m", "crew.main", "--question", question],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=env
            )
            stdout_val = result.stdout
            stderr_val = result.stderr
            
            if result.returncode == 0:
                st.success("Execution completed successfully!")
            else:
                st.warning(f"Execution finished with non-zero exit code: {result.returncode}")
            
            # Attempt to load the latest trace file for details
            traces_dir = Path("traces")
            research_text = ""
            write_text = ""
            validate_text = ""
            if traces_dir.exists():
                trace_files = sorted(traces_dir.glob("*.json"), key=os.path.getmtime, reverse=True)
                if trace_files:
                    try:
                        with open(trace_files[0], "r", encoding="utf-8") as tf:
                            trace_data = json.load(tf)
                            research_text = trace_data.get("research_output", "")
                            write_text = trace_data.get("write_output", "")
                            validate_text = trace_data.get("validate_output", "")
                    except Exception:
                        pass

            # Create Streamlit tabs for all Agent tasks
            tab1, tab2, tab3, tab4 = st.tabs([
                "🔬 Researcher Agent",
                "✍️ Writer Agent",
                "✅ Validator Agent",
                "💻 Terminal Log"
            ])

            with tab1:
                st.markdown("### Researcher Evidence Gathering Task")
                if research_text:
                    st.info(research_text)
                else:
                    st.warning("No separate researcher evidence output found in trace file. Check terminal logs.")

            with tab2:
                st.markdown("### Writer Sourced Markdown Report Task")
                if write_text:
                    st.success(write_text)
                else:
                    st.warning("No separate writer markdown output found in trace file. Check terminal logs.")

            with tab3:
                st.markdown("### Claim Validator grounding Check Task")
                if validate_text:
                    st.warning(validate_text)
                else:
                    st.warning("No separate validation details found in trace file. Check terminal logs.")

            with tab4:
                st.markdown("### Raw Console Streams")
                if stdout_val:
                    st.markdown("#### Standard Output")
                    st.code(stdout_val, language="bash")
                if stderr_val:
                    st.markdown("#### Error / Debug Stream")
                    st.code(stderr_val, language="bash")
            
            # Scan output directory for any newly written markdown files
            output_dir = Path("output")
            if output_dir.exists():
                reports = sorted(output_dir.glob("*.md"), key=os.path.getmtime, reverse=True)
                if reports:
                    st.markdown("---")
                    st.markdown("## 📝 Persisted Reports (Output Folder)")
                    for report in reports[:2]:
                        with st.expander(f"📄 {report.name}", expanded=True):
                            st.markdown(report.read_text(encoding="utf-8"))
                            
        except Exception as ex:
            st.error(f"An unexpected error occurred running the process: {ex}")
