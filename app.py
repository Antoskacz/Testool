import streamlit as st
import json
import pandas as pd
from pathlib import Path
import difflib
import unicodedata
import copy
import plotly.graph_objects as go  # zobrazeni grafu
import plotly.express as px        # volitelny
import re
from datetime import datetime

# define base directory as the location of this script. This is
# stable even when Streamlit copies the code to /tmp or the current
# working directory changes during execution.
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PROJECTS_PATH = DATA_DIR / "projects.json"
KROKY_PATH = DATA_DIR / "kroky.json"
KROKY_CUSTOM_PATH = DATA_DIR / "kroky_custom.json"  # fallback file for custom actions

# ensure data directory exists as early as possible
DATA_DIR.mkdir(exist_ok=True)


st.set_page_config(
    page_title="Testool",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------- GLOBAL THEME ----------
st.markdown("""
<style>
:root {
    --bg: #08111f;
    --bg-2: #0b1730;
    --panel: rgba(14, 24, 46, 0.88);
    --panel-strong: rgba(17, 29, 54, 0.96);
    --border: rgba(107, 152, 255, 0.22);
    --text: #edf4ff;
    --muted: #93a7c8;
    --accent: #3ad7ff;
    --accent-2: #6b8cff;
    --pink: #ff1fae;
}

.stApp {
    background:
        radial-gradient(circle at top center, rgba(56, 120, 255, 0.14), transparent 28%),
        radial-gradient(circle at right top, rgba(255, 0, 170, 0.08), transparent 20%),
        linear-gradient(180deg, var(--bg) 0%, #06101f 100%);
    color: var(--text);
}

.block-container {
    max-width: 1450px !important;
    padding-top: 2.0rem !important;
    padding-bottom: 2rem !important;
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(24,28,43,0.98) 0%, rgba(17,22,37,0.98) 100%);
    border-right: 1px solid rgba(255,255,255,0.06);
}
section[data-testid="stSidebar"] .block-container {
    padding-top: 1rem !important;
}

/* keep sidebar toggle visible */
[data-testid="collapsedControl"] {
    display: flex !important;
    opacity: 1 !important;
    visibility: visible !important;
}

h1, h2, h3 {
    letter-spacing: -0.02em;
}

.stTextInput > div > div > input,
.stTextArea textarea,
.stSelectbox [data-baseweb="select"] > div,
.stMultiSelect [data-baseweb="select"] > div {
    background: rgba(10, 15, 30, 0.85) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 12px !important;
}

.stButton > button,
.stDownloadButton > button,
button[kind="secondary"] {
    background: linear-gradient(180deg, rgba(25,36,66,0.95), rgba(17,26,49,0.95)) !important;
    border: 1px solid rgba(112,156,255,0.36) !important;
    color: #ebf3ff !important;
    border-radius: 12px !important;
    min-height: 44px !important;
    font-weight: 700 !important;
    box-shadow: 0 10px 24px rgba(0,0,0,0.18);
}

.stButton > button:hover,
.stDownloadButton > button:hover {
    border-color: rgba(58,215,255,0.55) !important;
}

.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #188dff, #6b5cff) !important;
    border: none !important;
}

[data-testid="stMetric"] {
    background: transparent !important;
    border: none !important;
}

[data-testid="stDataFrame"] {
    background: rgba(17, 23, 41, 0.78) !important;
    border: 1px solid var(--border) !important;
    border-radius: 16px !important;
    overflow: hidden !important;
}

.streamlit-expanderHeader {
    background: rgba(17, 23, 41, 0.72) !important;
    border: 1px solid var(--border) !important;
    border-radius: 12px !important;
}

.tt-header {
    text-align: center;
    padding: 2.2rem 0 0.8rem 0;
}
.tt-logo {
    font-size: 3rem;
    font-weight: 800;
    color: #3ad7ff;
    margin: 0;
}
.tt-subtitle {
    color: var(--muted);
    margin-top: 0.2rem;
    margin-bottom: 1.2rem;
}
.tt-card {
    background: linear-gradient(180deg, rgba(20, 28, 50, 0.78), rgba(14, 20, 38, 0.9));
    border: 1px solid var(--border);
    border-radius: 18px;
    padding: 20px 22px;
    box-shadow: 0 18px 45px rgba(0,0,0,0.16);
    margin-bottom: 18px;
}
.tt-metric {
    background: linear-gradient(180deg, rgba(16, 26, 48, 0.88), rgba(10, 18, 36, 0.96));
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 14px 16px;
    min-height: 92px;
}
.tt-metric-label {
    color: #dfe9ff;
    font-size: 0.92rem;
    font-weight: 700;
    margin-bottom: 0.45rem;
}
.tt-metric-value {
    color: #ffffff;
    font-size: 2rem;
    font-weight: 800;
    line-height: 1;
}
.tt-empty {
    display:flex;
    align-items:center;
    justify-content:center;
    min-height: 320px;
    color: var(--muted);
    background: linear-gradient(180deg, rgba(13, 20, 38, 0.72), rgba(10, 16, 30, 0.84));
    border: 1px dashed rgba(111,153,255,0.24);
    border-radius: 16px;
    text-align:center;
    padding: 1rem;
}
.tt-note {
    background: linear-gradient(90deg, rgba(85,95,0,0.55), rgba(70,80,0,0.35));
    border: 1px solid rgba(189, 200, 70, 0.18);
    color: #f6f3c7;
    padding: 0.9rem 1rem;
    border-radius: 12px;
    margin: 1rem 0 1.4rem 0;
}
.tt-muted { color: var(--muted); }
hr {
    border-color: rgba(255,255,255,0.08) !important;
}
#MainMenu, footer { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# Debug information to determine where the script is actually running.
# Streamlit often copies the Python file to /tmp, which makes __file__ and
# cwd point to a temporary location. We need to know the original workspace
# path so that data files are stored persistently.
import sys
print(f"[INIT] cwd={Path.cwd()}")
print(f"[INIT] __file__={__file__}")
print(f"[INIT] sys.argv={sys.argv}")
print(f"[INIT] argv[0] resolved={Path(sys.argv[0]).resolve()}")


# ---------- POMOCNÉ FUNKCE ----------
def load_json(filepath):
    """Safe JSON loading"""
    try:
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading {filepath}: {e}")
    return {}

def save_json(filepath, data):
    """Safe JSON saving"""
    try:
        filepath.parent.mkdir(exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving {filepath}: {e}")
        return False

def save_and_update_projects(data):
    """Uloží projekty do souboru a aktualizuje session_state"""
    # use fixed workspace path; not cwd, because Streamlit may run
    # from a temp directory
    projects_path = PROJECTS_PATH
    success = save_json(projects_path, data)
    if success:
        st.session_state.projects = copy.deepcopy(data)
    return success

def normalize_action_payload(action_data):
    """Return canonical action structure."""
    if isinstance(action_data, dict):
        return {
            "description": action_data.get("description", "").strip(),
            "steps": copy.deepcopy(action_data.get("steps", []))
        }
    elif isinstance(action_data, list):
        return {
            "description": "",
            "steps": copy.deepcopy(action_data)
        }
    return {"description": "", "steps": []}


def action_payload_equal(a, b):
    return normalize_action_payload(a) == normalize_action_payload(b)


def load_base_steps():
    data = load_json(KROKY_PATH)
    return data if isinstance(data, dict) else {}


def load_custom_overrides():
    data = load_json(KROKY_CUSTOM_PATH)
    return data if isinstance(data, dict) else {}


def load_effective_steps():
    """Base kroky.json + overrides from kroky_custom.json"""
    base_steps = load_base_steps()
    overrides = load_custom_overrides()
    effective = copy.deepcopy(base_steps)

    for action_name, override_data in overrides.items():
        if not isinstance(override_data, dict):
            continue

        status = override_data.get("_status")

        if status == "deleted":
            effective.pop(action_name, None)
        elif status in ("added", "modified"):
            effective[action_name] = {
                "description": override_data.get("description", "").strip(),
                "steps": copy.deepcopy(override_data.get("steps", []))
            }

    return effective


def build_overrides_from_effective(base_steps, effective_steps):
    """
    Compare current effective state with immutable base and produce override-only kroky_custom.json.
    """
    overrides = {}

    all_action_names = sorted(set(base_steps.keys()) | set(effective_steps.keys()), key=str.lower)

    for action_name in all_action_names:
        in_base = action_name in base_steps
        in_effective = action_name in effective_steps

        if in_base and not in_effective:
            overrides[action_name] = {"_status": "deleted"}
            continue

        if not in_base and in_effective:
            payload = normalize_action_payload(effective_steps[action_name])
            overrides[action_name] = {
                "_status": "added",
                "description": payload["description"],
                "steps": payload["steps"]
            }
            continue

        if in_base and in_effective:
            base_payload = normalize_action_payload(base_steps[action_name])
            eff_payload = normalize_action_payload(effective_steps[action_name])

            if base_payload != eff_payload:
                overrides[action_name] = {
                    "_status": "modified",
                    "description": eff_payload["description"],
                    "steps": eff_payload["steps"]
                }

    return dict(sorted(overrides.items(), key=lambda kv: kv[0].lower()))


def save_ui_overrides(effective_steps):
    """
    Save only UI changes to kroky_custom.json.
    kroky.json remains untouched.
    """
    base_steps = load_base_steps()
    overrides = build_overrides_from_effective(base_steps, effective_steps)

    success = save_json(KROKY_CUSTOM_PATH, overrides)

    if success:
        refreshed_effective = load_effective_steps()
        st.session_state.steps_data = copy.deepcopy(refreshed_effective)
        st.session_state.edit_steps_data = copy.deepcopy(refreshed_effective)
        st.toast("✅ UI overrides saved to kroky_custom.json", icon="💾")
    else:
        st.error("❌ Failed to save UI overrides.")

    return success
	
    
def clean_tc_name(name: str) -> str:
    """
    Odstraní části 'UNKNOWN' z názvu ticketu a opraví duplicitní podtržítka.
    """
    if not name or not isinstance(name, str):
        return name
    
    parts = name.split('_')
    cleaned_parts = [p for p in parts if p != 'UNKNOWN']
    result = '_'.join(cleaned_parts)
    
    # Opravit případné duplicitní podtržítka
    while '__' in result:
        result = result.replace('__', '_')
    
    # Odebrat podtržítka na začátku/konci
    result = result.strip('_')
    
    return result

def extract_channel(text: str) -> str:
    """Extract channel from text"""
    t = text.lower()
    if "shop" in t:
        return "SHOP"
    if "il" in t:
        return "IL"
    return "UNKNOWN"

def extract_segment(text: str) -> str:
    """Extract segment from text"""
    t = text.lower()
    if "b2c" in t:
        return "B2C"
    if "b2b" in t:
        return "B2B"
    return "UNKNOWN"

def extract_technology(text: str) -> str:
    """Extract technology from text"""
    t = text.lower()
    if "hlas" in t or "voice" in t:
        return "HLAS"
    if "fwa" in t and "bisi" in t:
        return "FWA_BISI"
    if "fwa" in t and "bi" in t:
        return "FWA_BI"
    for key in ["dsl", "fiber", "cable"]:
        if key in t:
            return key.upper()
    if "fwa" in t:
        return "FWA"
    return "UNKNOWN"

def analyze_scenarios(scenarios: list):
    """Count scenarios by segment -> channel -> action"""
    segment_data = {"B2C": {"SHOP": {}, "IL": {}}, "B2B": {"SHOP": {}, "IL": {}}}

    for scenario in scenarios:
        segment = scenario.get("segment", "UNKNOWN")
        channel = scenario.get("kanal", "UNKNOWN")
        action = scenario.get("akce", "UNKNOWN")

        if segment not in segment_data:
            segment_data[segment] = {}

        if channel not in segment_data[segment]:
            segment_data[segment][channel] = {}

        if action not in segment_data[segment][channel]:
            segment_data[segment][channel][action] = 0

        segment_data[segment][channel][action] += 1

    return segment_data

def remove_diacritics(text):
    """Remove diacritics from text"""
    if not text:
        return text
    normalized = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in normalized if not unicodedata.combining(c))

def update_scenarios_with_action_steps(projects_data: dict, steps_data: dict, action_name: str):
    """
    Update all scenarios that use a specific action with the latest steps from kroky.json
    Propagates changes to all test cases that use this action
    """
    updated_count = 0
    for project_key, project_data in projects_data.items():
        if not isinstance(project_data, dict) or "scenarios" not in project_data:
            continue
        
        for scenario in project_data.get("scenarios", []):
            if scenario.get("akce") == action_name:
                # Get updated steps from kroky.json
                if action_name in steps_data:
                    action_data = steps_data[action_name]
                    if isinstance(action_data, dict) and "steps" in action_data:
                        scenario["kroky"] = copy.deepcopy(action_data["steps"])
                        updated_count += 1
                    elif isinstance(action_data, list):
                        scenario["kroky"] = copy.deepcopy(action_data)
                        updated_count += 1
    
    return updated_count


def render_metric_card(title: str, value: int):
    st.markdown(
        f"""<div class="tt-metric">
            <div class="tt-metric-label">{title}</div>
            <div class="tt-metric-value">{value}</div>
        </div>""",
        unsafe_allow_html=True,
    )


def render_empty_panel(message: str, height: int = 320):
    st.markdown(
        f"<div class='tt-empty' style='min-height:{height}px'>{message}</div>",
        unsafe_allow_html=True,
    )


def render_section_intro(title: str, subtitle: str):
    st.markdown(f"### {title}")
    st.markdown(f"<div class='tt-muted'>{subtitle}</div>", unsafe_allow_html=True)


# ---------- HLAVNÍ APLIKACE ----------
# Top nav handles title + tabs, žáden repeating headings zde

# ---------- SIDEBAR ----------
# paths (BASE_DIR, DATA_DIR, PROJECTS_PATH, KROKY_PATH, KROKY_CUSTOM_PATH)
# are defined at the top of the module. We rely on those constants rather
# than recalculating them here, ensuring the workspace location is always


# used regardless of streamlit's working directory.

# (DATA_DIR already created by module-level code.)

# Načtení dat
projects = load_json(PROJECTS_PATH)
steps_data = load_effective_steps()


# Zajistíme, aby se prázdné soubory inicializovaly s minimem dat
if not projects or projects == {}:
    projects = {}
    save_json(PROJECTS_PATH, projects)

if not steps_data or steps_data == {}:
    steps_data = {}
    save_json(KROKY_PATH, steps_data)

# Session state initialization:
# IMPORTANT: We initialize ONLY on first run (no 'in st.session_state'),
# and then PRESERVE the in-memory copy across st.rerun() calls.
# This allows temporary changes (new actions) to persist within the session
# until the app is fully restarted.
if 'projects' not in st.session_state:
    st.session_state.projects = copy.deepcopy(projects)

if 'selected_project' not in st.session_state:
    st.session_state.selected_project = None

if 'steps_data' not in st.session_state:
    st.session_state.steps_data = copy.deepcopy(steps_data)
    print(f"[DEBUG] INIT: steps_data first initialization from disk")

# Initialize selected tab
if 'selected_tab' not in st.session_state:
    st.session_state.selected_tab = 'build'

# ---------- SIDEBAR: LOGO + PROJECT MANAGEMENT ----------
with st.sidebar:    
    st.subheader("📁 Project")

    project_names = list(st.session_state.projects.keys())
    selected = st.selectbox(
        "Select Project",
        options=["— select —"] + project_names,
        index=0,
        key="project_select"
    )

    new_project = st.text_input("New Project Name", placeholder="e.g.: CCCTR-XXXX – Name")

    if st.button("✅ Create Project", use_container_width=True):
        if new_project.strip():
            if new_project.strip() not in st.session_state.projects:
                st.session_state.projects[new_project] = {
                    "next_id": 1,
                    "subject": r"UAT2\Antosova\\",
                    "scenarios": []
                }
                save_and_update_projects(st.session_state.projects)
                st.session_state.selected_project = new_project
                st.success("Project created.")
                st.rerun()
            else:
                st.error("Project already exists.")
        else:
            st.error("Project name cannot be empty.")

    if selected != "— select —":
        st.session_state.selected_project = selected

    current_project = st.session_state.get("selected_project")

    if current_project:
        st.markdown("---")
        st.subheader("🛠️ Project Settings")

        # Rename project
        rename_val = st.text_input("Rename project", value=current_project)

        if st.button("✏️ Rename project", use_container_width=True):
            new_name = rename_val.strip()
            if not new_name:
                st.error("Project name cannot be empty.")
            elif new_name in st.session_state.projects:
                st.error("A project with this name already exists.")
            else:
                st.session_state.projects[new_name] = st.session_state.projects[current_project]
                del st.session_state.projects[current_project]
                save_and_update_projects(st.session_state.projects)
                st.session_state.selected_project = new_name
                st.success("Project renamed.")
                st.rerun()

        # Delete project (two-step)
        if "project_to_delete" not in st.session_state:
            st.session_state.project_to_delete = None

        if st.button("🗑️ Delete project", use_container_width=True):
            st.session_state.project_to_delete = current_project

        if st.session_state.project_to_delete == current_project:
            st.warning(f'Are you sure you want to delete "{current_project}"?')
            col_yes, col_no = st.columns(2)

            with col_yes:
                if st.button("Yes, delete", use_container_width=True):
                    del st.session_state.projects[current_project]
                    save_and_update_projects(st.session_state.projects)
                    st.session_state.selected_project = None
                    st.session_state.project_to_delete = None
                    st.success("Project deleted.")
                    st.rerun()

            with col_no:
                if st.button("Cancel", use_container_width=True):
                    st.session_state.project_to_delete = None

        # Subject settings
        st.markdown("---")
        st.subheader("📨 Subject Settings")

        subject_val = st.session_state.projects[current_project].get("subject", "")
        subject_input = st.text_input("Subject", value=subject_val)

        col_save, col_delete = st.columns(2)

        with col_save:
            if st.button("💾 Save subject", use_container_width=True):
                st.session_state.projects[current_project]["subject"] = subject_input.strip()
                save_and_update_projects(st.session_state.projects)
                st.success("Subject updated.")

        with col_delete:
            if st.button("🧹 Delete subject", use_container_width=True):
                st.session_state.projects[current_project]["subject"] = ""
                save_and_update_projects(st.session_state.projects)
                st.success("Subject cleared.")

# ---------- MAIN CONTENT: STICKY TOP NAV ----------
if 'selected_tab' not in st.session_state:
    st.session_state.selected_tab = 'build'

selected_tab = st.session_state.selected_tab

# Top navigation - centered logo without boxed background
st.markdown("""
<div class="tt-header">
    <div class="tt-logo">🧪 Testool</div>
    <div class="tt-subtitle">Professional test case builder and manager</div>
</div>
""", unsafe_allow_html=True)

col_space1, tab_col1, tab_col2, tab_col3, col_space2 = st.columns([1, 1, 1, 1, 1])

with tab_col1:
    if st.button("Test Cases", use_container_width=True, key="nav_build", type=("primary" if selected_tab == "build" else "secondary")):
        st.session_state.selected_tab = "build"
        st.rerun()

with tab_col2:
    if st.button("Actions & Steps", use_container_width=True, key="nav_edit", type=("primary" if selected_tab == "edit" else "secondary")):
        st.session_state.selected_tab = "edit"
        st.rerun()

with tab_col3:
    if st.button("Text Comparator", use_container_width=True, key="nav_text", type=("primary" if selected_tab == "text" else "secondary")):
        st.session_state.selected_tab = "text"
        st.rerun()

st.markdown("""
<div style="
    text-align: center;
    color: #5D6980;
    font-size: 0.98rem;
    margin-top: 0.4rem;
    margin-bottom: 0.1rem;
">
    Create test cases and export them to an Excel format ready for direct HPQC upload.
</div>
""", unsafe_allow_html=True)

# Content separator
st.markdown("---")

# ---------- TAB 1: BUILD TEST CASES ----------
if selected_tab == "build":
    project_name = st.session_state.selected_project
    if project_name is None:
        project_data = {"subject": "", "scenarios": [], "next_id": 1}
        project_exists = False
    else:
        project_data = st.session_state.projects[project_name]
        project_exists = True

    testcases = project_data.get("scenarios", [])
    testcase_count = len(testcases)
    b2b_count = sum(1 for tc in testcases if tc.get("segment") == "B2B")
    b2c_count = sum(1 for tc in testcases if tc.get("segment") == "B2C")

    if not project_exists:
        st.markdown("<div class='tt-note'>Select or create a project in the sidebar to work with test cases.</div>", unsafe_allow_html=True)

    col_overview, col_analysis = st.columns([1, 1.15])

    with col_overview:
        st.subheader("📊 Project Overview")
        display_project_name = project_name if project_name else "— no project selected —"
        st.write(f"**Active Project:** {display_project_name}")
        st.write(f"**Subject:** {project_data.get('subject', '')}")

        st.markdown("---")
        st.subheader("📋 Actions by Segment")

        if testcases:
            nested_segment_data = analyze_scenarios(testcases)
            segment_columns = st.columns(2)
            segment_config = [
                ("B2C", "👥", segment_columns[0]),
                ("B2B", "🏢", segment_columns[1]),
            ]

            for segment_name, icon, target_col in segment_config:
                with target_col:
                    segment_channels = nested_segment_data.get(segment_name, {})
                    segment_total = sum(
                        sum(action_map.values())
                        for action_map in segment_channels.values()
                    )

                    with st.expander(f"{icon} {segment_name} ({segment_total})", expanded=True):
                        if not segment_channels:
                            st.write("No test cases")
                        else:
                            for channel_name in ["SHOP", "IL"]:
                                action_map = segment_channels.get(channel_name, {})
                                channel_total = sum(action_map.values())

                                st.markdown(f"**{channel_name} ({channel_total})**")

                                if action_map:
                                    for action, count in sorted(action_map.items(), key=lambda x: (-x[1], x[0])):
                                        st.write(f"- {action}: {count}")
                                else:
                                    st.caption("No test cases")

                                st.markdown("")
        else:
            st.info("No test cases yet")

    with col_analysis:
        st.markdown("<h3 style='text-align:center;'>📈 Distribution Analysis</h3>", unsafe_allow_html=True)
        st.markdown("<div class='tt-muted' style='text-align:center; margin-top:-0.35rem; margin-bottom:0.8rem;'>Distribution by test complexity</div>", unsafe_allow_html=True)
        if testcase_count > 0:
            complexity_order = ["1-Giant", "2-Huge", "3-Big", "4-Medium", "5-Low"]
            complexity_counts = {label: 0 for label in complexity_order}
            for tc in testcases:
                value = tc.get("complexity", "UNKNOWN")
                if value in complexity_counts:
                    complexity_counts[value] += 1
                else:
                    complexity_counts[value] = complexity_counts.get(value, 0) + 1

            filtered_items = [(label, count) for label, count in complexity_counts.items() if count > 0]
            labels = [label.split('-', 1)[1] if '-' in label else label for label, _ in filtered_items]
            values = [count for _, count in filtered_items]
            colors = ["#ff4fbf", "#8b5cf6", "#35d6ff", "#22c55e", "#f59e0b"][:len(values)]

            fig_complexity = go.Figure(data=[go.Pie(
                labels=labels,
                values=values,
                hole=0.58,
                marker_colors=colors,
                textinfo='label+value',
                textposition='inside',
                textfont=dict(size=14, color='white'),
                hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>',
                sort=False,
                direction='clockwise'
            )])
            fig_complexity.update_layout(
                showlegend=True,
                legend=dict(
                    orientation='h',
                    yanchor='bottom',
                    y=-0.08,
                    xanchor='center',
                    x=0.5,
                    font=dict(color='#dfe9ff', size=12)
                ),
                height=420,
                margin=dict(t=10, b=60, l=10, r=10),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                annotations=[dict(text=f"<b>Total</b><br>{testcase_count}", x=0.5, y=0.5, font_size=26, showarrow=False, font=dict(color='#dfe9ff'))]
            )
            st.plotly_chart(fig_complexity, use_container_width=True)
        else:
            render_empty_panel("No test cases yet", height=360)
    st.markdown("---")
    st.markdown("### 💾 Export Test Cases")
    st.write("Generate clean, renumbered & diacritics-free test cases Excel file.")
    export_button = st.button("💾 Export Test Cases to Excel", use_container_width=False, disabled=(not project_exists or not testcases))

    if export_button:
        project_data = st.session_state.projects[project_name]
        project_data["scenarios"] = sorted(project_data["scenarios"], key=lambda x: x.get("order_no", 0))

        for i, tc in enumerate(project_data["scenarios"], start=1):
            tc["order_no"] = i
            channel = tc["kanal"]
            segment = tc["segment"]
            technology = extract_technology(tc["veta"])
            sentence = tc["veta"].strip()
            prefix = "_".join(p for p in [f"{i:03d}", channel, segment, technology] if p and p != "UNKNOWN")
            tc["test_name"] = clean_tc_name(f"{prefix}_{sentence.capitalize()}")

        save_and_update_projects(st.session_state.projects)

        rows = []
        for tc in project_data["scenarios"]:
            for i, step in enumerate(tc.get("kroky", []), start=1):
                rows.append({
                    "Project": project_name,
                    "Subject": project_data.get("subject", ""),
                    "System/Application": "Siebel_CZ",
                    "Description": f"Segment: {tc['segment']}\nChannel: {tc['kanal']}\nAction: {tc['akce']}",
                    "Type": "Manual",
                    "Test Phase": "4-User Acceptance",
                    "Test: Test Phase": "4-User Acceptance",
                    "Test Priority": tc["priority"],
                    "Test Complexity": tc["complexity"],
                    "Test Name": remove_diacritics(tc["test_name"]),
                    "Step Name (Design Steps)": str(i),
                    "Description (Design Steps)": remove_diacritics(step.get("description", "")),
                    "Expected (Design Steps)": remove_diacritics(step.get("expected", ""))
                })

        df = pd.DataFrame(rows)
        import io
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Test Cases")
        output.seek(0)

        safe_name = project_name.replace(" ", "_").replace("/", "_").replace("\\", "_")
        st.success("Export successful. File is ready for download.")
        st.download_button(
            "⬇️ Download Excel file",
            data=output.getvalue(),
            file_name=f"testcases_{safe_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=False
        )
    st.markdown("---")
    st.subheader("📋 Test Cases List")
    if project_data.get("scenarios"):
        df_data = []
        for tc in project_data["scenarios"]:
            df_data.append({
                "Order": tc.get("order_no"),
                "Test Name": tc.get("test_name"),
                "Action": tc.get("akce"),
                "Segment": tc.get("segment"),
                "Channel": tc.get("kanal"),
                "Priority": tc.get("priority"),
                "Complexity": tc.get("complexity"),
                "Steps": len(tc.get("kroky", [])) if "kroky" in tc else 0
            })

        df = pd.DataFrame(df_data)
        if not df.empty:
            df = df.sort_values(by="Order", ascending=True)

        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Order": st.column_config.NumberColumn("No.", width="small"),
                "Test Name": st.column_config.TextColumn("Test Name", width="large"),
                "Action": st.column_config.TextColumn("Action", width="medium"),
                "Segment": st.column_config.TextColumn("Segment", width="small"),
                "Channel": st.column_config.TextColumn("Channel", width="small"),
                "Priority": st.column_config.TextColumn("Priority", width="small"),
                "Complexity": st.column_config.TextColumn("Complexity", width="small"),
                "Steps": st.column_config.NumberColumn("Steps", width="small")
            }
        )
    else:
        st.info("No test cases yet. Add your first test case below.")
    st.markdown("---")
    st.subheader("➕ Add New Test Case")

    if not project_exists:
        st.info("Create a project first to add test cases.")
        st.stop()

    if not st.session_state.steps_data:
        st.error("❌ No actions found! Please add actions in 'Edit Actions & Steps' page first.")
        st.stop()

    action_list = sorted(list(st.session_state.steps_data.keys()))

    with st.form("add_testcase_form"):
        sentence = st.text_area("Requirement Sentence", height=100, placeholder="e.g.: Activate DSL for B2C via SHOP channel...")
        action = st.selectbox("Action (from kroky.json)", options=action_list)

        PRIORITY_MAP_VALUES = ["1-High", "2-Medium", "3-Low"]
        COMPLEXITY_MAP_VALUES = ["1-Giant", "2-Huge", "3-Big", "4-Medium", "5-Low"]
        SEGMENT_OPTIONS = ["B2C", "B2B"]
        KANAL_OPTIONS = ["SHOP", "IL"]

        col_priority, col_complexity, col_segment, col_kanal = st.columns(4)
        with col_priority:
            priority = st.selectbox("Priority", options=PRIORITY_MAP_VALUES, index=1)
        with col_complexity:
            complexity = st.selectbox("Complexity", options=COMPLEXITY_MAP_VALUES, index=3)
        with col_segment:
            segment = st.selectbox("Segment", options=SEGMENT_OPTIONS, index=0)
        with col_kanal:
            kanal = st.selectbox("Kanál", options=KANAL_OPTIONS, index=0)

        if st.form_submit_button("➕ Add Test Case"):
            if not sentence.strip():
                st.error("Requirement sentence cannot be empty.")
            elif not action:
                st.error("Select an action.")
            else:
                order = project_data["next_id"]
                technology = extract_technology(sentence)
                prefix_parts = [f"{order:03d}", kanal, segment, technology]
                filtered_parts = [p for p in prefix_parts if p and p != "UNKNOWN"]
                prefix = "_".join(filtered_parts)
                test_name = clean_tc_name(f"{prefix}_{sentence.strip().capitalize()}")

                kroky_pro_akci = []
                if action in st.session_state.steps_data:
                    action_data = st.session_state.steps_data[action]
                    if isinstance(action_data, dict) and "steps" in action_data:
                        kroky_pro_akci = copy.deepcopy(action_data["steps"])
                    elif isinstance(action_data, list):
                        kroky_pro_akci = copy.deepcopy(action_data)

                new_testcase = {
                    "order_no": order,
                    "test_name": test_name,
                    "akce": action,
                    "segment": segment,
                    "kanal": kanal,
                    "priority": priority,
                    "complexity": complexity,
                    "veta": sentence.strip(),
                    "kroky": kroky_pro_akci
                }

                project_data["next_id"] += 1
                project_data["scenarios"].append(new_testcase)
                save_and_update_projects(st.session_state.projects)
                st.success(f"✅ Test case added: {test_name}")
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    with st.expander("✏️ Edit Existing Test Case", expanded=False):
        if project_data["scenarios"]:
            testcase_options = {f"{tc['order_no']:03d} - {tc['test_name']}": tc for tc in project_data["scenarios"]}
            selected_testcase_key = st.selectbox("Select Test Case to Edit", options=list(testcase_options.keys()), index=0, key="edit_testcase_select")

            if selected_testcase_key:
                testcase_to_edit = testcase_options[selected_testcase_key]
                if "edit_sentence_value" not in st.session_state or st.session_state.get("edit_sentence_tc") != testcase_to_edit["order_no"]:
                    st.session_state.edit_sentence_value = testcase_to_edit["veta"]
                    st.session_state.edit_sentence_tc = testcase_to_edit["order_no"]

                with st.form("edit_testcase_form"):
                    st.write(f"**Currently editing:** {testcase_to_edit['test_name']}")
                    sentence = st.text_area("Requirement Sentence", value=st.session_state.edit_sentence_value, height=100, key=f"edit_sentence_{testcase_to_edit['order_no']}")
                    action = st.selectbox("Action (from kroky.json)", options=action_list, index=action_list.index(testcase_to_edit["akce"]) if testcase_to_edit["akce"] in action_list else 0, key="edit_action")

                    SEGMENT_OPTIONS = ["B2C", "B2B"]
                    KANAL_OPTIONS = ["SHOP", "IL"]

                    col_priority, col_complexity, col_segment, col_kanal = st.columns(4)
                    with col_priority:
                        priority = st.selectbox("Priority", options=PRIORITY_MAP_VALUES, index=PRIORITY_MAP_VALUES.index(testcase_to_edit["priority"]) if testcase_to_edit["priority"] in PRIORITY_MAP_VALUES else 1, key="edit_priority")
                    with col_complexity:
                        complexity = st.selectbox("Complexity", options=COMPLEXITY_MAP_VALUES, index=COMPLEXITY_MAP_VALUES.index(testcase_to_edit["complexity"]) if testcase_to_edit["complexity"] in COMPLEXITY_MAP_VALUES else 3, key="edit_complexity")
                    with col_segment:
                        segment = st.selectbox("Segment", options=SEGMENT_OPTIONS, index=SEGMENT_OPTIONS.index(testcase_to_edit["segment"]) if testcase_to_edit["segment"] in SEGMENT_OPTIONS else 0, key="edit_segment")
                    with col_kanal:
                        kanal = st.selectbox("Kanál", options=KANAL_OPTIONS, index=KANAL_OPTIONS.index(testcase_to_edit["kanal"]) if testcase_to_edit["kanal"] in KANAL_OPTIONS else 0, key="edit_kanal")

                    if st.form_submit_button("💾 Save Changes"):
                        if not sentence.strip():
                            st.error("Requirement sentence cannot be empty.")
                        elif not action:
                            st.error("Select an action.")
                        else:
                            order = testcase_to_edit["order_no"]
                            technology = extract_technology(sentence)
                            prefix_parts = [f"{order:03d}", kanal, segment, technology]
                            filtered_parts = [p for p in prefix_parts if p and p != "UNKNOWN"]
                            prefix = "_".join(filtered_parts)
                            while '__' in prefix:
                                prefix = prefix.replace('__', '_')
                            prefix = prefix.strip('_')
                            new_test_name = clean_tc_name(f"{prefix}_{sentence.strip().capitalize()}")

                            kroky_pro_akci = []
                            if action in st.session_state.steps_data:
                                action_data = st.session_state.steps_data[action]
                                if isinstance(action_data, dict) and "steps" in action_data:
                                    kroky_pro_akci = copy.deepcopy(action_data["steps"])
                                elif isinstance(action_data, list):
                                    kroky_pro_akci = copy.deepcopy(action_data)

                            st.session_state.edit_sentence_value = sentence.strip()
                            testcase_to_edit.update({
                                "test_name": new_test_name,
                                "akce": action,
                                "segment": segment,
                                "kanal": kanal,
                                "priority": priority,
                                "complexity": complexity,
                                "veta": sentence.strip(),
                                "kroky": kroky_pro_akci
                            })

                            save_and_update_projects(st.session_state.projects)
                            st.success(f"✅ Test case updated: {new_test_name}")
                            st.rerun()
        else:
            st.info("No test cases available to edit. Add a test case first.")

    with st.expander("🗑️ Delete Test Case", expanded=False):
        if project_data["scenarios"]:
            delete_options = [f"{tc['order_no']:03d} - {tc['test_name']}" for tc in project_data["scenarios"]]
            testcase_to_delete = st.selectbox("Select Test Case to Delete", options=delete_options, index=0, key="delete_testcase_select")

            if st.button("⚠️ Delete Selected Test Case", type="secondary"):
                index_to_delete = delete_options.index(testcase_to_delete)
                deleted_tc = project_data["scenarios"].pop(index_to_delete)
                for idx, tc in enumerate(project_data["scenarios"], start=1):
                    tc["order_no"] = idx
                    if tc["test_name"].startswith(f"{idx-1:03d}_"):
                        tc["test_name"] = f"{idx:03d}_" + tc["test_name"][4:]
                    elif "_" in tc["test_name"]:
                        parts = tc["test_name"].split("_", 1)
                        if len(parts[0]) == 3 and parts[0].isdigit():
                            tc["test_name"] = f"{idx:03d}_" + parts[1]

                project_data["next_id"] = len(project_data["scenarios"]) + 1
                save_and_update_projects(st.session_state.projects)
                st.success(f"🗑️ Test case deleted: {deleted_tc['test_name']}")
                st.rerun()
        else:
            st.info("No test cases available to delete.")

# ---------- TAB 2: EDIT ACTIONS & STEPS ----------
if selected_tab == "edit":
    # 🔧 Edit Actions & Steps
    
    # Load current data from disk to ensure we always have the latest
    disk_steps = load_effective_steps()
    
    # Initialize edit_steps_data: combine disk data with any session state data
    # This handles the case where session_state was reset on F5 refresh
    if "edit_steps_data" not in st.session_state:
        # First visit to this page (no prior session state)
        st.session_state.edit_steps_data = copy.deepcopy(disk_steps)
        print(f"[DEBUG] INIT edit_steps_data: Created from disk. Keys: {sorted(st.session_state.edit_steps_data.keys())[:3]}...")
    else:
        # Session state exists - merge disk data with session data
        # Preserve any new actions that user added but not yet saved
        print(f"[DEBUG] RESTORE edit_steps_data from session")
        print(f"[DEBUG]   Session has ({len(st.session_state.edit_steps_data)}): {sorted(st.session_state.edit_steps_data.keys())[:3]}...")
        print(f"[DEBUG]   Disk has ({len(disk_steps)}): {sorted(disk_steps.keys())[:3]}...")
        # Keep any actions from session that are not on disk (new unsaved actions)
        for action_name, action_data in st.session_state.edit_steps_data.items():
            # Don't overwrite session data with disk data - keep the session version
            # This preserves new actions user added
            if action_name not in disk_steps:
                print(f"[DEBUG]   Keeping unsaved action from session: {action_name}")
    
    if "editing_action" not in st.session_state:
        st.session_state.editing_action = None

    # layout top row: left shows counts+action list, right has small commit button
    # main row: left panel action list, tiny separator, right panel commit + counts
    left, sep, right = st.columns([3, 0.05, 2])
    
    # Calculate correct counts: disk = what's in kroky.json, non-committed = what's in memory but NOT on disk
    base_steps = load_base_steps()
    committed_overrides = load_custom_overrides()
    committed_effective = load_effective_steps()
    current_effective = st.session_state.edit_steps_data if st.session_state.edit_steps_data else {}

    base_count = len(base_steps)
    override_count = len(committed_overrides)

    pending_overrides = build_overrides_from_effective(base_steps, current_effective)
    pending_count = len(pending_overrides)
    
    # DEBUG: Log what we see
    print(f"[DEBUG] EDIT_ACTIONS_PAGE disk_data keys ({disk_count}): {sorted(disk_action_names)}")
    print(f"[DEBUG] EDIT_ACTIONS_PAGE edit_steps_data keys: {sorted(mem_action_names)}")
    print(f"[DEBUG] EDIT_ACTIONS_PAGE non_committed ({mem_count}): {non_committed}")
    
    with left:
        st.text_area("All actions:", value="\n".join(sorted(st.session_state.edit_steps_data.keys())), height=150, disabled=True)
    with sep:
        st.markdown("<div style='border-left:1px solid gray;height:100%'></div>", unsafe_allow_html=True)
    with right:
        st.write(f"**Actions in kroky.json:** {base_count}")
        st.write(f"**Committed UI overrides:** {override_count}")
        st.write(f"**Pending UI changes:** {pending_count}")

        if st.button("💾 Commit", help="Save UI changes to kroky_custom.json", use_container_width=True):
            save_ui_overrides(st.session_state.edit_steps_data)
            st.success("All UI changes saved to kroky_custom.json")
    
    # the initialization and controls above already handle everything;
    # drop the duplicated commit/count/debugging section to keep UI clean.
    if "new_steps" not in st.session_state:
        st.session_state.new_steps = []

    if "new_action" not in st.session_state:
        st.session_state.new_action = False

    if "delete_action" not in st.session_state:
        st.session_state.delete_action = None

    st.markdown("---")
    
    if st.button("➕ **Add New Action**", key="new_action_main", use_container_width=True):
        st.session_state.new_action = True
        st.session_state.editing_action = None
    
    # NEW ACTION FORM - show only when button clicked
    if st.session_state.get("new_action", False):
        with st.form("new_action_form"):
            action_name = st.text_input("Action Name*", placeholder="e.g.: DSL_Activation", key="new_action_name")
            action_desc = st.text_input("Action Description*", placeholder="e.g.: DSL service activation", key="new_action_desc")
            
            st.markdown("---")
            st.write("**Action Steps:**")
            
            # Display existing steps
            if st.session_state.new_steps:
                st.write("**Added Steps:**")
                
                for i, step in enumerate(st.session_state.new_steps):
                    col_step, col_delete = st.columns([4, 1])
                    
                    with col_step:
                        st.text_input(f"Step {i+1} - Description", 
                                    value=step['description'], 
                                    key=f"view_desc_{i}", 
                                    disabled=True)
                        st.text_input(f"Step {i+1} - Expected", 
                                    value=step['expected'], 
                                    key=f"view_exp_{i}", 
                                    disabled=True)
                    
                    with col_delete:
                        if st.form_submit_button("🗑️", key=f"del_new_{i}", use_container_width=True):
                            st.session_state.new_steps.pop(i)
                            st.rerun()
                    
                    st.markdown("---")
            
            # Add new step
            st.write("**Add New Step:**")
            new_desc = st.text_area("Description*", key="new_step_desc", height=60, 
                                  placeholder="Step description - what to do")
            new_exp = st.text_area("Expected*", key="new_step_exp", height=60, 
                                 placeholder="Expected result - what should happen")
            
            if st.form_submit_button("➕ Add Step", key="add_step_btn"):
                if new_desc.strip() and new_exp.strip():
                    st.session_state.new_steps.append({
                        "description": new_desc.strip(),
                        "expected": new_exp.strip()
                    })
                    st.rerun()
            
            st.markdown("---")
            
            # Save/Cancel buttons
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.form_submit_button("💾 Save New Action", use_container_width=True, type="primary"):
                    if not action_name.strip():
                        st.error("Enter action name")
                    elif not action_desc.strip():
                        st.error("Enter action description")
                    elif not st.session_state.new_steps:
                        st.error("Add at least one step")
                    else:
                        # Save to kroky.json IMMEDIATELY before page refresh
                        action_key = action_name.strip()
                        st.session_state.edit_steps_data[action_key] = {
                            "description": action_desc.strip(),
                            "steps": st.session_state.new_steps.copy()
                        }
                        # CRITICAL: Save to disk BEFORE st.rerun()
                        # This ensures data persists even if session_state resets
                        save_ui_overrides(st.session_state.edit_steps_data)
                        
                        st.success(f"✅ Action '{action_name}' saved to UI overrides!")
                        st.session_state.new_action = False
                        st.session_state.new_steps = []
                        st.rerun()
            
            with col_cancel:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    st.session_state.new_action = False
                    st.session_state.new_steps = []
                    st.rerun()
    
    st.markdown("---")
    
    # ---------- EXISTING ACTIONS LIST ----------
    st.subheader("📝 Existing Actions")
    
    if st.session_state.edit_steps_data:
        for action in sorted(st.session_state.edit_steps_data.keys()):
            content = st.session_state.edit_steps_data[action]
            description = content.get("description", "No description") if isinstance(content, dict) else "No description"
            steps = content.get("steps", []) if isinstance(content, dict) else content
            step_count = len(steps)
            
            col_action, col_edit, col_delete = st.columns([3, 1, 1])
            
            with col_action:
                st.write(f"**{action}**")
                st.caption(f"{description} | {step_count} steps")
            
            with col_edit:
                if st.button("✏️", key=f"edit_{action}", help="Edit action", use_container_width=True):
                    st.session_state.editing_action = action
                    st.session_state.new_action = False
                    st.rerun()
            
            with col_delete:
                if st.button("🗑️", key=f"delete_{action}", help="Delete action", use_container_width=True):
                    st.session_state.delete_action = action
                    st.rerun()
            
            # Delete confirmation
            if st.session_state.get("delete_action") == action:
                # Count scenarios using this action
                affected_count = 0
                for project_data in st.session_state.projects.values():
                    if isinstance(project_data, dict) and "scenarios" in project_data:
                        for scenario in project_data["scenarios"]:
                            if scenario.get("akce") == action:
                                affected_count += 1
                
                if affected_count > 0:
                    st.warning(f"⚠️ {affected_count} test case(s) use this action! Deleting will remove their steps.")
                
                st.warning(f"Are you sure you want to delete action '{action}'?")
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("Yes, delete", key=f"confirm_del_{action}"):
                        # Remove action from kroky.json
                        del st.session_state.edit_steps_data[action]
                        # use helper to persist steps data
                        save_ui_overrides(st.session_state.edit_steps_data)
                        
                        # Clear steps from all affected scenarios
                        for project_data in st.session_state.projects.values():
                            if isinstance(project_data, dict) and "scenarios" in project_data:
                                for scenario in project_data["scenarios"]:
                                    if scenario.get("akce") == action:
                                        scenario["kroky"] = []
                        save_and_update_projects(st.session_state.projects)
                        
                        st.success(f"✅ Action '{action}' updated in UI overrides!")
                        if affected_count > 0:
                            st.info(f"📊 Cleared steps from {affected_count} test case(s)")
                        st.session_state.delete_action = None
                        st.rerun()
                with col_cancel:
                    if st.button("Cancel", key=f"cancel_del_{action}"):
                        st.session_state.delete_action = None
                        st.rerun()
            
            st.markdown("---")
    
    # ---------- EDIT EXISTING ACTION ----------
    if st.session_state.editing_action:
        action = st.session_state.editing_action
        content = st.session_state.edit_steps_data.get(action, {})
        description = content.get("description", "") if isinstance(content, dict) else ""
        steps = content.get("steps", []) if isinstance(content, dict) else content
        
        st.subheader(f"✏️ Edit Action: {action}")
        
        # Initialize session state for editing
        if f"edit_steps_{action}" not in st.session_state:
            st.session_state[f"edit_steps_{action}"] = steps.copy()
        
        with st.form(f"edit_action_{action}"):
            new_desc = st.text_input("Action Description*", value=description, key=f"desc_{action}")
            
            st.markdown("---")
            st.write("**Action Steps:**")
            
            # Display steps for editing
            steps_to_delete = []
            for i, step in enumerate(st.session_state[f"edit_steps_{action}"]):
                col_step, col_delete = st.columns([4, 1])
                
                with col_step:
                    if isinstance(step, dict):
                        desc = st.text_area(f"Step {i+1} - Description", 
                                          value=step.get('description', ''),
                                          key=f"desc_{action}_{i}",
                                          height=60)
                        exp = st.text_area(f"Step {i+1} - Expected", 
                                         value=step.get('expected', ''),
                                         key=f"exp_{action}_{i}",
                                         height=60)
                        st.session_state[f"edit_steps_{action}"][i] = {"description": desc, "expected": exp}
                
                with col_delete:
                    if st.form_submit_button("🗑️", key=f"del_{action}_{i}", use_container_width=True):
                        steps_to_delete.append(i)
                
                st.markdown("---")
            
            # Delete marked steps
            for index in sorted(steps_to_delete, reverse=True):
                if index < len(st.session_state[f"edit_steps_{action}"]):
                    st.session_state[f"edit_steps_{action}"].pop(index)
                    st.rerun()
            
            # Add new step
            st.write("**Add New Step:**")
            new_desc_input = st.text_area("Description*", key=f"new_desc_{action}", height=60, placeholder="Step description...")
            new_exp_input = st.text_area("Expected*", key=f"new_exp_{action}", height=60, placeholder="Expected result...")
            
            if st.form_submit_button("➕ Add Step", key=f"add_{action}"):
                if new_desc_input.strip() and new_exp_input.strip():
                    st.session_state[f"edit_steps_{action}"].append({
                        "description": new_desc_input.strip(),
                        "expected": new_exp_input.strip()
                    })
                    st.rerun()
            
            st.markdown("---")
            
            # Save/Cancel buttons
            col_save, col_cancel = st.columns(2)
            with col_save:
                if st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary"):
                    if not new_desc.strip():
                        st.error("Enter action description")
                    elif not st.session_state[f"edit_steps_{action}"]:
                        st.error("Action must have at least one step")
                    else:
                        st.session_state.edit_steps_data[action] = {
                            "description": new_desc.strip(),
                            "steps": st.session_state[f"edit_steps_{action}"].copy()
                        }
                        # helper updates file and session_state
                        save_ui_overrides(st.session_state.edit_steps_data)
                        
                        # 🔄 Propagate changes to all scenarios using this action
                        updated = update_scenarios_with_action_steps(st.session_state.projects, st.session_state.steps_data, action)
                        save_and_update_projects(st.session_state.projects)
                        
                        st.success(f"✅ Action '{action}' deleted from UI overrides!")
                        if updated > 0:
                            st.info(f"📊 Updated {updated} test case(s) with new steps")
                        
                        st.session_state.editing_action = None
                        if f"edit_steps_{action}" in st.session_state:
                            del st.session_state[f"edit_steps_{action}"]
                        st.rerun()
            
            with col_cancel:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    st.session_state.editing_action = None
                    if f"edit_steps_{action}" in st.session_state:
                        del st.session_state[f"edit_steps_{action}"]
                    st.rerun()

# ---------- TAB 3: TEXT COMPARATOR ----------
if selected_tab == "text":
    # 📝 Text Comparator
    st.markdown("Compare two texts with highlighted differences")
    
    if 'text1_area' not in st.session_state:
        st.session_state.text1_area = ""
    if 'text2_area' not in st.session_state:
        st.session_state.text2_area = ""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Text 1")
        text1 = st.text_area(
            "Enter first text:", 
            height=300, 
            key="text1_area",
            value=st.session_state.text1_area,
            help="Enter or paste your first text here"
        )
    
    with col2:
        st.subheader("Text 2")
        text2 = st.text_area(
            "Enter second text:", 
            height=300, 
            key="text2_area",
            value=st.session_state.text2_area,
            help="Enter or paste your second text here"
        )
    
    st.markdown("---")
    
    # Create buttons in a row
    col_buttons = st.columns([1, 1, 1, 4])

    def remove_diacritics_action():
        st.session_state.text1_area = remove_diacritics(st.session_state.get('text1_area', ''))
        st.session_state.text2_area = remove_diacritics(st.session_state.get('text2_area', ''))
        st.session_state.comparator_message = '✅ Diacritics removed from both texts'

    def reset_action():
        st.session_state.text1_area = ''
        st.session_state.text2_area = ''
        st.session_state.comparator_message = '✅ Texts cleared'

    with col_buttons[0]:
        compare_btn = st.button("🔍 **Compare**", use_container_width=True, type="primary", help="Compare texts and highlight differences")

    with col_buttons[1]:
        diacritics_btn = st.button(
            "❌ **Remove Diacritics**", 
            use_container_width=True,
            help="Remove all accents, háčky and čárky from both texts",
            on_click=remove_diacritics_action
        )

    with col_buttons[2]:
        reset_btn = st.button(
            "🔄 **Reset**", 
            use_container_width=True,
            help="Clear both text fields",
            on_click=reset_action
        )

    if 'comparator_message' not in st.session_state:
        st.session_state.comparator_message = ''

    if st.session_state.comparator_message:
        st.success(st.session_state.comparator_message)
        st.session_state.comparator_message = ''
    
    if compare_btn:
        if text1.strip() and text2.strip():
            st.subheader("📊 Character Comparison")
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("Length Text 1", len(text1))
            with col_stat2:
                st.metric("Length Text 2", len(text2))
            with col_stat3:
                diff_len = abs(len(text1) - len(text2))
                st.metric("Length Difference", diff_len)
            
            st.markdown("---")
            st.subheader("🔍 Character-by-Character Differences")
            
            def format_segment(text: str, start: int, end: int, highlight: bool):
                segment = text[start:end]
                if not segment:
                    return ""
                if not highlight:
                    return segment

                displayed = ''.join('␣' if ch == ' ' else ch for ch in segment)
                return f'<span style="background-color: #ff4444; color: white; font-weight: bold; padding: 1px 3px; border-radius: 3px;">{displayed}</span>'

            def highlight_differences(text1: str, text2: str, side: str) -> str:
                sm = difflib.SequenceMatcher(None, text1, text2)
                html = ''

                for tag, i1, i2, j1, j2 in sm.get_opcodes():
                    if side == 'left':
                        if tag == 'equal':
                            html += format_segment(text1, i1, i2, False)
                        elif tag in ('replace', 'delete'):
                            html += format_segment(text1, i1, i2, True)
                        elif tag == 'insert':
                            # text1 has no chars for the inserted block from text2
                            # we still keep the alignment meaning by showing nothing here
                            pass
                    else:
                        if tag == 'equal':
                            html += format_segment(text2, j1, j2, False)
                        elif tag in ('replace', 'insert'):
                            html += format_segment(text2, j1, j2, True)
                        elif tag == 'delete':
                            # text2 has no chars for the deleted block from text1
                            pass

                return html

            highlighted1 = highlight_differences(text1, text2, 'left')
            highlighted2 = highlight_differences(text1, text2, 'right')
            
            col_diff1, col_diff2 = st.columns(2)
            
            with col_diff1:
                st.markdown("**Text 1:**")
                st.markdown(
                    f"""<div style='
                        background-color: #2a2a2a; 
                        padding: 15px; 
                        border-radius: 5px; 
                        font-family: "Courier New", monospace; 
                        white-space: pre-wrap;
                        line-height: 1.5;
                        font-size: 14px;
                    '>{highlighted1}</div>""", 
                    unsafe_allow_html=True
                )
            
            with col_diff2:
                st.markdown("**Text 2:**")
                st.markdown(
                    f"""<div style='
                        background-color: #2a2a2a; 
                        padding: 15px; 
                        border-radius: 5px; 
                        font-family: "Courier New", monospace; 
                        white-space: pre-wrap;
                        line-height: 1.5;
                        font-size: 14px;
                    '>{highlighted2}</div>""", 
                    unsafe_allow_html=True
                )
            
            sm = difflib.SequenceMatcher(None, text1, text2)
            matches = sum(block.size for block in sm.get_matching_blocks())
            total = max(len(text1), len(text2)) if max(len(text1), len(text2)) > 0 else 1
            similarity = sm.ratio() * 100
            
            st.markdown("---")
            st.subheader("📈 Similarity Analysis")
            
            col_sim1, col_sim2, col_sim3 = st.columns([2, 1, 1])
            
            with col_sim1:
                st.progress(similarity/100, text=f"Similarity: {similarity:.1f}%")
            
            with col_sim2:
                st.metric("Matching Chars", matches)
            
            with col_sim3:
                st.metric("Total Compared", total)
            
            if similarity == 100:
                st.success("🎉 Texts are identical!")
            elif similarity > 90:
                st.info(f"Texts are very similar ({similarity:.1f}% match)")
            elif similarity > 70:
                st.info(f"Texts are somewhat similar ({similarity:.1f}% match)")
            elif similarity > 50:
                st.warning(f"Texts have significant differences ({similarity:.1f}% match)")
            else:
                st.error(f"Texts are very different ({similarity:.1f}% match)")
            
        else:
            st.warning("Please enter text in both fields to compare.")