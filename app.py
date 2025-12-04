import streamlit as st
import json
import pandas as pd
from pathlib import Path
import copy
import difflib

st.set_page_config(
    page_title="TestTool - Test Case Management",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme
CUSTOM_CSS = """
<style>
/* Hide the top navigation bar that Streamlit creates for multi-page apps */
[data-testid="stSidebarNav"] {
    display: none;
}

/* Hide any other top navigation elements */
header[data-testid="stHeader"] {
    display: none;
}

[data-testid="stToolbar"] {
    display: none;
}

.css-1d391kg {
    display: none;
}

body { background-color: #121212; color: #EAEAEA; }
[data-testid="stAppViewContainer"] { background: linear-gradient(145deg, #181818, #1E1E1E); }
[data-testid="stSidebar"] { background: linear-gradient(180deg, #1C1C1C, #181818); border-right: 1px solid #333; }
h1, h2, h3 { color: #F1F1F1; font-weight: 600; }
div[data-testid="stForm"], div[data-testid="stExpander"] {
    background-color: #1A1A1A; border-radius: 10px; padding: 1rem; border: 1px solid #333;
}
button[kind="primary"] { background: linear-gradient(90deg, #4e54c8, #8f94fb); color: white !important; }
button[kind="secondary"] { background: #292929; color: #CCC !important; border: 1px solid #555; }
.stTextInput > div > div > input, textarea, select {
    background-color: #222; color: #EEE !important; border-radius: 6px; border: 1px solid #444;
}
.stDataFrame { background-color: #1C1C1C !important; }

/* Style for diff output */
.diff { border-collapse: collapse; width: 100%; }
.diff_add { background-color: #d4edda; color: #155724; }
.diff_sub { background-color: #f8d7da; color: #721c24; }
.diff_chg { background-color: #fff3cd; color: #856404; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------- PATHS ----------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = BASE_DIR / "exports"

KROKY_PATH = DATA_DIR / "kroky.json"
PROJECTS_PATH = DATA_DIR / "projects.json"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)

# ---------- HELPER FUNCTIONS ----------
def load_json(filepath):
    """Safe JSON loading"""
    try:
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
    return {}

def save_json(filepath, data):
    """Safe JSON saving"""
    try:
        filepath.parent.mkdir(exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving {filepath}: {e}")
        return False

# ---------- PAGE 1: BUILD TEST CASES ----------
def build_test_cases_page():
    st.title("🏗️ Build Test Cases")
    
    # Load data
    projects = load_json(PROJECTS_PATH)
    steps_data = load_json(KROKY_PATH)
    
    # Initialize session state
    if 'projects' not in st.session_state:
        st.session_state.projects = projects
    if 'selected_project' not in st.session_state:
        st.session_state.selected_project = None
    if 'steps_data' not in st.session_state:
        st.session_state.steps_data = steps_data
    
    # ---------- SIDEBAR ----------
    st.sidebar.title("📁 Project")
    
    # Project selection
    project_names = list(st.session_state.projects.keys())
    selected = st.sidebar.selectbox(
        "Select Project",
        options=["— select —"] + project_names,
        index=0,
        key="project_select_build"
    )
    
    # Create new project
    new_project = st.sidebar.text_input("New Project Name", placeholder="e.g.: CCCTR-XXXX – Name")
    
    if st.sidebar.button("✅ Create Project", use_container_width=True):
        if new_project.strip():
            if new_project.strip() not in st.session_state.projects:
                st.session_state.projects[new_project.strip()] = {
                    "next_id": 1,
                    "subject": "UAT2\\Antosova\\",
                    "scenarios": []
                }
                save_json(PROJECTS_PATH, st.session_state.projects)
                st.session_state.selected_project = new_project.strip()
                st.rerun()
            else:
                st.sidebar.error("Project already exists!")
    
    # Project management
    if selected != "— select —" and selected in st.session_state.projects:
        st.session_state.selected_project = selected
    
    # ---------- MAIN CONTENT ----------
    if st.session_state.selected_project is None:
        st.info("Select or create a project in the left panel.")
        return
    
    project_name = st.session_state.selected_project
    project_data = st.session_state.projects[project_name]
    
    # Project info
    st.write(f"**Active Project:** {project_name}")
    st.write(f"**Subject:** {project_data.get('subject', 'UAT2\\Antosova\\')}")
    st.write(f"**Number of Test Cases:** {len(project_data.get('scenarios', []))}")
    
    st.markdown("---")
    
    # Add new test case
    st.subheader("➕ Add New Test Case")
    
    with st.form("add_testcase_form"):
        sentence = st.text_area("Requirement Sentence", height=100, 
                              placeholder="e.g.: Activate DSL for B2C via SHOP channel...")
        
        if st.session_state.steps_data:
            action_list = list(st.session_state.steps_data.keys())
            action = st.selectbox("Action", options=action_list)
        else:
            st.warning("No actions available. Add actions in Edit Actions & Steps first.")
            action = None
        
        col_priority, col_complexity = st.columns(2)
        with col_priority:
            priority = st.selectbox("Priority", options=["1-High", "2-Medium", "3-Low"], index=1)
        with col_complexity:
            complexity = st.selectbox("Complexity", options=["1-Giant", "2-Huge", "3-Big", "4-Medium", "5-Low"], index=3)
        
        if st.form_submit_button("➕ Add Test Case"):
            if not sentence.strip():
                st.error("Requirement sentence cannot be empty.")
            elif not action:
                st.error("Select an action.")
            else:
                # Simple test case generation
                order = project_data["next_id"]
                test_name = f"{order:03d}_Test_{sentence[:50]}"
                
                new_testcase = {
                    "order_no": order,
                    "test_name": test_name,
                    "akce": action,
                    "priority": priority,
                    "complexity": complexity,
                    "veta": sentence.strip()
                }
                
                project_data["next_id"] += 1
                project_data["scenarios"].append(new_testcase)
                save_json(PROJECTS_PATH, st.session_state.projects)
                st.success(f"✅ Test case added: {test_name}")
                st.rerun()
    
    st.markdown("---")
    
    # List test cases
    st.subheader("📋 Test Cases List")
    
    if project_data.get("scenarios"):
        df_data = []
        for tc in project_data["scenarios"]:
            df_data.append({
                "Order": tc.get("order_no"),
                "Test Name": tc.get("test_name"),
                "Action": tc.get("akce"),
                "Priority": tc.get("priority"),
                "Complexity": tc.get("complexity"),
                "Sentence": tc.get("veta", "")[:100] + "..." if len(tc.get("veta", "")) > 100 else tc.get("veta", "")
            })
        
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No test cases yet.")

# ---------- PAGE 2: EDIT ACTIONS & STEPS ----------
def edit_actions_page():
    st.title("🔧 Edit Actions & Steps")
    st.markdown("Manage actions and their steps in `kroky.json`")
    
    # Load data
    steps_data = load_json(KROKY_PATH)
    
    # Initialize session state
    if 'steps_data' not in st.session_state:
        st.session_state.steps_data = steps_data
    
    # Add new action
    st.subheader("➕ Add New Action")
    
    with st.expander("Click to add new action"):
        with st.form("new_action_form"):
            action_name = st.text_input("Action Name*", placeholder="e.g.: DSL_Activation")
            action_desc = st.text_input("Action Description*", placeholder="e.g.: DSL service activation")
            
            st.write("**Add Steps:**")
            step_desc = st.text_area("Step Description", placeholder="What to do...")
            step_exp = st.text_area("Expected Result", placeholder="What should happen...")
            
            if st.form_submit_button("💾 Save Action"):
                if action_name.strip() and action_desc.strip():
                    new_action = {
                        action_name.strip(): {
                            "description": action_desc.strip(),
                            "steps": [
                                {
                                    "description": step_desc.strip() if step_desc.strip() else "Step description",
                                    "expected": step_exp.strip() if step_exp.strip() else "Expected result"
                                }
                            ]
                        }
                    }
                    
                    # Update data
                    st.session_state.steps_data.update(new_action)
                    save_json(KROKY_PATH, st.session_state.steps_data)
                    st.success(f"✅ Action '{action_name}' added!")
                    st.rerun()
                else:
                    st.error("Please fill in all required fields.")
    
    st.markdown("---")
    
    # List existing actions
    st.subheader("📝 Existing Actions")
    
    if st.session_state.steps_data:
        for action_name, action_data in st.session_state.steps_data.items():
            with st.expander(f"**{action_name}** - {action_data.get('description', 'No description')}"):
                st.write(f"**Description:** {action_data.get('description', 'No description')}")
                
                if "steps" in action_data and action_data["steps"]:
                    st.write("**Steps:**")
                    for i, step in enumerate(action_data["steps"], 1):
                        st.write(f"{i}. **Do:** {step.get('description', '')}")
                        st.write(f"   **Expect:** {step.get('expected', '')}")
                
                # Delete button
                if st.button(f"Delete {action_name}", key=f"del_{action_name}"):
                    if action_name in st.session_state.steps_data:
                        del st.session_state.steps_data[action_name]
                        save_json(KROKY_PATH, st.session_state.steps_data)
                        st.success(f"✅ Action '{action_name}' deleted!")
                        st.rerun()
    else:
        st.info("No actions yet. Add your first action above.")

# ---------- PAGE 3: TEXT COMPARATOR ----------
def text_comparator_page():
    st.title("📝 Text Comparator")
    st.markdown("Compare two texts with highlighted differences")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Text 1")
        text1 = st.text_area("Enter first text:", height=300, key="text1")
    
    with col2:
        st.subheader("Text 2")
        text2 = st.text_area("Enter second text:", height=300, key="text2")
    
    st.markdown("---")
    
    if st.button("🔍 Compare Texts", use_container_width=True, type="primary"):
        if text1.strip() and text2.strip():
            # Split into lines for better comparison
            lines1 = text1.splitlines()
            lines2 = text2.splitlines()
            
            # Create HTML diff
            differ = difflib.HtmlDiff()
            diff_html = differ.make_file(lines1, lines2, fromdesc="Text 1", todesc="Text 2")
            
            # Display the diff
            st.subheader("📊 Differences")
            st.markdown(diff_html, unsafe_allow_html=True)
            
            # Show statistics
            seq = difflib.SequenceMatcher(None, text1, text2)
            similarity = seq.ratio() * 100
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("Similarity", f"{similarity:.1f}%")
            with col_stat2:
                st.metric("Characters Text 1", len(text1))
            with col_stat3:
                st.metric("Characters Text 2", len(text2))
            
        else:
            st.warning("Please enter text in both fields to compare.")

# ---------- MAIN APP ----------
# Title
st.title("🧪 TestTool")
st.markdown("### Professional test case builder and manager")

# Navigation in sidebar ONLY - without any header text
page = st.sidebar.radio(
    " ",
    [
        "🏗️ Build Test Cases",
        "🔧 Edit Actions & Steps", 
        "📝 Text Comparator"
    ]
)

# Page routing
if page == "🏗️ Build Test Cases":
    build_test_cases_page()
elif page == "🔧 Edit Actions & Steps":
    edit_actions_page()
elif page == "📝 Text Comparator":
    text_comparator_page()