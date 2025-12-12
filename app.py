import streamlit as st
import json
import pandas as pd
from pathlib import Path
import difflib
import unicodedata
import copy
import plotly.graph_objects as go
import re

# ================== PAGE CONFIG ==================
st.set_page_config(
    page_title="Testool",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ================== HELPERS ==================
def load_json(filepath):
    try:
        if filepath.exists():
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading {filepath}: {e}")
    return {}

def save_json(filepath, data):
    try:
        filepath.parent.mkdir(exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving {filepath}: {e}")
        return False

def remove_diacritics(text):
    if not text:
        return text
    norm = unicodedata.normalize("NFKD", text)
    return "".join(c for c in norm if not unicodedata.combining(c))

def clean_tc_name(name):
    parts = [p for p in name.split("_") if p != "UNKNOWN"]
    res = "_".join(parts)
    while "__" in res:
        res = res.replace("__", "_")
    return res.strip("_")

def extract_channel(text):
    t = text.lower()
    if "shop" in t:
        return "SHOP"
    if "il" in t:
        return "IL"
    return "UNKNOWN"

def extract_segment(text):
    t = text.lower()
    if "b2c" in t:
        return "B2C"
    if "b2b" in t:
        return "B2B"
    return "UNKNOWN"

def extract_technology(text):
    t = text.lower()
    if "hlas" in t or "voice" in t:
        return "HLAS"
    if "fwa" in t and "bisi" in t:
        return "FWA_BISI"
    if "fwa" in t and "bi" in t:
        return "FWA_BI"
    for k in ["dsl", "fiber", "cable"]:
        if k in t:
            return k.upper()
    if "fwa" in t:
        return "FWA"
    return "UNKNOWN"

# ================== DATA PATHS ==================
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PROJECTS_PATH = DATA_DIR / "projects.json"
KROKY_PATH = DATA_DIR / "kroky.json"

projects = load_json(PROJECTS_PATH)
steps_data = load_json(KROKY_PATH)

if "projects" not in st.session_state:
    st.session_state.projects = projects
if "steps_data" not in st.session_state:
    st.session_state.steps_data = steps_data
if "selected_project" not in st.session_state:
    st.session_state.selected_project = None

# ================== SIDEBAR ==================
with st.sidebar:
    st.title("🧪 Testool")
    page = st.radio(
        "Navigation",
        ["🏗️ Build Test Cases", "🔧 Edit Actions & Steps", "📝 Text Comparator"]
    )

    st.markdown("---")
    st.subheader("📁 Project")

    names = list(st.session_state.projects.keys())
    selected = st.selectbox("Select Project", ["— select —"] + names)

    if selected != "— select —":
        st.session_state.selected_project = selected

    new_project = st.text_input("New Project Name")

    if st.button("✅ Create Project"):
        if new_project and new_project not in st.session_state.projects:
            st.session_state.projects[new_project] = {
                "next_id": 1,
                "subject": "",
                "scenarios": []
            }
            save_json(PROJECTS_PATH, st.session_state.projects)
            st.session_state.selected_project = new_project
            st.rerun()

# ================== PAGE ROUTER ==================

# ======================================================================
# PAGE 1: BUILD TEST CASES
# ======================================================================
if page == "🏗️ Build Test Cases":

    st.title("🏗️ Build Test Cases")

    if not st.session_state.selected_project:
        st.info("Select or create a project.")
        st.stop()

    project_name = st.session_state.selected_project
    project_data = st.session_state.projects[project_name]

    # ---------- OVERVIEW + GRAPH ----------
    col_l, col_r = st.columns([1, 1.5])

    with col_l:
        st.subheader("📊 Project Overview")
        st.write(f"**Project:** {project_name}")
        st.write(f"**Subject:** {project_data.get('subject','')}")

    with col_r:
        st.markdown("<h3 style='text-align:center'>📈 Distribution Analysis</h3>", unsafe_allow_html=True)
        tcs = project_data["scenarios"]
        if tcs:
            b2c = sum(1 for tc in tcs if tc["segment"] == "B2C")
            b2b = sum(1 for tc in tcs if tc["segment"] == "B2B")
            fig = go.Figure(go.Pie(
                labels=["B2C", "B2B"],
                values=[b2c, b2b],
                hole=0.5
            ))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No test cases yet.")

    # ---------- EXPORT ----------
    st.markdown("---")
    st.subheader("💾 Export Test Cases")

    col_exp, _ = st.columns([1, 2])
    with col_exp:
        export = st.button("Export to Excel")

    if export:
        rows = []
        for i, tc in enumerate(project_data["scenarios"], start=1):
            tc["order_no"] = i
            prefix = "_".join(
                p for p in [
                    f"{i:03d}",
                    tc["kanal"],
                    tc["segment"],
                    extract_technology(tc["veta"])
                ] if p != "UNKNOWN"
            )
            tc["test_name"] = clean_tc_name(f"{prefix}_{tc['veta'].capitalize()}")

            for j, step in enumerate(tc.get("kroky", []), start=1):
                rows.append({
                    "Test Name": remove_diacritics(tc["test_name"]),
                    "Step": j,
                    "Description": remove_diacritics(step.get("description","")),
                    "Expected": remove_diacritics(step.get("expected",""))
                })

        df = pd.DataFrame(rows)
        import io
        buf = io.BytesIO()
        df.to_excel(buf, index=False)
        buf.seek(0)

        st.download_button(
            "⬇️ Download Excel",
            buf.getvalue(),
            f"testcases_{project_name}.xlsx"
        )

    # ---------- LIST ----------
    st.markdown("---")
    st.subheader("📋 Test Cases List")

    if project_data["scenarios"]:
        st.dataframe(pd.DataFrame(project_data["scenarios"]))
    else:
        st.info("No test cases.")

    # ---------- ADD ----------
    st.markdown("---")
    st.subheader("➕ Add Test Case")

    with st.form("add_tc"):
        sentence = st.text_area("Requirement sentence")
        action = st.selectbox("Action", list(st.session_state.steps_data.keys()))
        if st.form_submit_button("Add"):
            tc = {
                "order_no": project_data["next_id"],
                "veta": sentence,
                "akce": action,
                "segment": extract_segment(sentence),
                "kanal": extract_channel(sentence),
                "priority": "2-Medium",
                "complexity": "4-Medium",
                "kroky": copy.deepcopy(
                    st.session_state.steps_data[action].get("steps", [])
                )
            }
            project_data["next_id"] += 1
            project_data["scenarios"].append(tc)
            save_json(PROJECTS_PATH, st.session_state.projects)
            st.rerun()

    # ---------- EDIT / DELETE ----------
    st.markdown("---")
    with st.expander("✏️ Edit / Delete Test Cases"):
        if project_data["scenarios"]:
            labels = [
                f"{tc['order_no']:03d} - {tc.get('test_name','')}"
                for tc in project_data["scenarios"]
            ]
            sel = st.selectbox("Select", labels)
            idx = labels.index(sel)

            if st.button("🗑️ Delete"):
                project_data["scenarios"].pop(idx)
                save_json(PROJECTS_PATH, st.session_state.projects)
                st.rerun()

# ======================================================================
# PAGE 2: EDIT ACTIONS & STEPS
# ======================================================================
elif page == "🔧 Edit Actions & Steps":

    st.title("🔧 Edit Actions & Steps")

    steps = st.session_state.steps_data

    action = st.text_input("New Action Name")
    if st.button("Add Action"):
        if action:
            steps[action] = {"description": "", "steps": []}
            save_json(KROKY_PATH, steps)
            st.rerun()

    st.markdown("---")
    for a, content in steps.items():
        st.subheader(a)
        for s in content.get("steps", []):
            st.write(f"- {s['description']}")

# ======================================================================
# PAGE 3: TEXT COMPARATOR
# ======================================================================
elif page == "📝 Text Comparator":

    st.title("📝 Text Comparator")

    col1, col2 = st.columns(2)
    with col1:
        t1 = st.text_area("Text 1", height=300)
    with col2:
        t2 = st.text_area("Text 2", height=300)

    if st.button("Compare"):
        m = difflib.SequenceMatcher(None, t1, t2)
        st.write(f"Similarity: {m.ratio()*100:.1f}%")
