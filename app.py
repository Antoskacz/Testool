import streamlit as st
import json
import pandas as pd
from pathlib import Path
import difflib
import unicodedata
import copy

st.set_page_config(
    page_title="Testool",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

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

def validate_kroky_structure(steps_data):
    """Validate kroky.json structure"""
    if not isinstance(steps_data, dict):
        return False
    
    for action, content in steps_data.items():
        if isinstance(content, dict):
            if "steps" not in content:
                return False
            if not isinstance(content["steps"], list):
                return False
        elif isinstance(content, list):
            # Starší formát - převedeme na nový
            steps_data[action] = {
                "description": f"Action: {action}",
                "steps": content
            }
        else:
            return False
    
    return True

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
    """Analyze scenarios for tree structure display - CLEAN VERSION"""
    segment_data = {"B2C": {}, "B2B": {}}
    
    for scenario in scenarios:
        segment = scenario.get("segment", "UNKNOWN")
        channel = scenario.get("kanal", "UNKNOWN")
        test_name = scenario.get("test_name", "")
        action = scenario.get("akce", "UNKNOWN")
        
        # Detect technology from test name
        technology = "DSL"
        tech_keywords = {
            "FIBER": "FIBER",
            "FWA_BISI": "FWA BISI", 
            "FWA_BI": "FWA BI",
            "CABLE": "CABLE",
            "HLAS": "HLAS",
            "DSL": "DSL"
        }
        
        for keyword, tech in tech_keywords.items():
            if keyword in test_name.upper():
                technology = tech
                break
        
        # Organize data - only if segment is B2C or B2B
        if segment in ["B2C", "B2B"]:
            if segment not in segment_data:
                segment_data[segment] = {}
            
            if channel not in segment_data[segment]:
                segment_data[segment][channel] = {}
                
            if technology not in segment_data[segment][channel]:
                segment_data[segment][channel][technology] = []
                
            if action not in segment_data[segment][channel][technology]:
                segment_data[segment][channel][technology].append(action)
    
    return segment_data

def remove_diacritics(text):
    """Remove diacritics from text"""
    if not text:
        return text
    normalized = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in normalized if not unicodedata.combining(c))


# ---------- HLAVNÍ APLIKACE ----------
st.title("🧪 Testool")
st.markdown("### Professional test case builder and manager")

# ---------- SIDEBAR ----------
with st.sidebar:
    st.title("🧪 Testool")
    st.markdown("---")
    
    # Navigace
    page = st.radio(
        "Navigation",
        [
            "🏗️ Build Test Cases",
            "🔧 Edit Actions & Steps", 
            "📝 Text Comparator"
        ]
    )

# ---------- STRÁNKA 1: BUILD TEST CASES ----------
if page == "🏗️ Build Test Cases":
    # Cesty k souborům
    BASE_DIR = Path(__file__).resolve().parent
    DATA_DIR = BASE_DIR / "data"
    PROJECTS_PATH = DATA_DIR / "projects.json"
    KROKY_PATH = DATA_DIR / "kroky.json"
    
    # Načtení dat
    projects = load_json(PROJECTS_PATH)
    steps_data = load_json(KROKY_PATH)
    
    #validace struktury
    if steps_data:
        if not validate_kroky_structure(steps_data):
            st.error("❌ Invalid kroky.json structure! Please fix or recreate the file.")
            steps_data = {}  # Reset na prázdný slovník
        
    
    # Session state
    if 'projects' not in st.session_state:
        st.session_state.projects = projects
    if 'selected_project' not in st.session_state:
        st.session_state.selected_project = None
    if 'steps_data' not in st.session_state:
        st.session_state.steps_data = steps_data
    
    # Výběr projektu v sidebaru
    with st.sidebar:
        st.markdown("---")
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
                    st.session_state.projects[new_project.strip()] = {
                        "next_id": 1,
                        "subject": r"UAT2\Antosova\\",
                        "scenarios": []
                    }
                    save_json(PROJECTS_PATH, st.session_state.projects)
                    st.session_state.selected_project = new_project.strip()
                    st.rerun()
                else:
                    st.error("Project already exists!")
        
        if selected != "— select —" and selected in st.session_state.projects:
            st.session_state.selected_project = selected
    
    # Hlavní obsah
    st.title("🏗️ Build Test Cases")
    
    if st.session_state.selected_project is None:
        st.info("Select or create a project in the sidebar.")
        st.stop()
    
    project_name = st.session_state.selected_project
    project_data = st.session_state.projects[project_name]
    
    # ---------- ROW 1: PROJECT OVERVIEW + ANALYSIS ----------
    col_overview, col_analysis = st.columns([1, 2])  # Zvětšíme Analysis na 2/3
    
    with col_overview:
        st.subheader("📊 Project Overview")
        subject_value = project_data.get('subject', r'UAT2\Antosova\\')
        st.write(f"**Active Project:** {project_name}")
        st.write(f"**Subject:** {subject_value}")
    
    with col_analysis:
        st.subheader("📈 Analysis")
        testcases = project_data.get("scenarios", [])
        
        if testcases:
            # Statistiky
            testcase_count = len(testcases)
            b2c_count = sum(1 for tc in testcases if tc.get("segment") == "B2C")
            b2b_count = sum(1 for tc in testcases if tc.get("segment") == "B2B")
            
            # Zobraz statistiky
            st.write("**📊 Statistics:**")
            st.write(f"- **Total Test Cases:** {testcase_count}")
            st.write(f"- **B2C:** {b2c_count} test cases")
            st.write(f"- **B2B:** {b2b_count} test cases")
            
            # Analýza struktury
            segment_data = analyze_scenarios(testcases)
            
            # CSS pro lepší zobrazení
            st.markdown("""
            <style>
            div[data-testid="stExpander"] details summary {
                font-size: 14px;
                font-weight: bold;
            }
            div[data-testid="stExpander"] details div {
                font-family: 'Segoe UI', Tahoma, sans-serif;
                font-size: 13px;
                line-height: 1.5;
                padding: 10px 15px;
            }
            </style>
            """, unsafe_allow_html=True)
            
            with st.expander("👥 B2C Analysis", expanded=True):
                if "B2C" in segment_data and segment_data["B2C"]:
                    for channel in segment_data["B2C"]:
                        st.write(f"**{channel}:**")
                        for technology in segment_data["B2C"][channel]:
                            action_count = len(segment_data["B2C"][channel][technology])
                            st.write(f"  {technology}: {action_count} actions")
                else:
                    st.write("No B2C test cases")
            
            with st.expander("🏢 B2B Analysis", expanded=True):
                if "B2B" in segment_data and segment_data["B2B"]:
                    for channel in segment_data["B2B"]:
                        st.write(f"**{channel}:**")
                        for technology in segment_data["B2B"][channel]:
                            action_count = len(segment_data["B2B"][channel][technology])
                            st.write(f"  {technology}: {action_count} actions")
                else:
                    st.write("No B2B test cases")
        else:
            st.info("No test cases for analysis. Add your first test case below.")
    
    st.markdown("---")
        
    
    # ---------- ROW 2: TEST CASES LIST ----------
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
            # Reset index pro lepší zobrazení
            df = df.reset_index(drop=True)
        
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
    
    # ---------- ROW 3: ADD NEW TEST CASE ----------
    st.subheader("➕ Add New Test Case")
    

    if not st.session_state.steps_data:
    # Zkontroluj, zda soubor existuje
        if KROKY_PATH.exists():
            st.error("❌ kroky.json exists but is empty or invalid. Please add actions first.")
        else:
            st.error(f"❌ File {KROKY_PATH} not found! Please create it first.")
        st.stop()

    
    action_list = sorted(list(st.session_state.steps_data.keys()))
    
    with st.form("add_testcase_form"):
        sentence = st.text_area("Requirement Sentence", height=100, 
                              placeholder="e.g.: Activate DSL for B2C via SHOP channel...")
        action = st.selectbox("Action (from kroky.json)", options=action_list)
        
        # Priority a Complexity
        PRIORITY_MAP_VALUES = ["1-High", "2-Medium", "3-Low"]
        COMPLEXITY_MAP_VALUES = ["1-Giant", "2-Huge", "3-Big", "4-Medium", "5-Low"]
        
        col_priority, col_complexity = st.columns(2)
        with col_priority:
            priority = st.selectbox("Priority", options=PRIORITY_MAP_VALUES, index=1)
        with col_complexity:
            complexity = st.selectbox("Complexity", options=COMPLEXITY_MAP_VALUES, index=3)
        
        if st.form_submit_button("➕ Add Test Case"):
            if not sentence.strip():
                st.error("Requirement sentence cannot be empty.")
            elif not action:
                st.error("Select an action.")
            else:
                # Generování test case
                order = project_data["next_id"]
                
                # Build test name
                channel = extract_channel(sentence)
                segment = extract_segment(sentence)
                technology = extract_technology(sentence)
                prefix = f"{order:03d}_{channel}_{segment}_{technology}"
                test_name = f"{prefix}_{sentence.strip().capitalize()}"
                
                # Get steps for action
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
                    "kanal": channel,
                    "priority": priority,
                    "complexity": complexity,
                    "veta": sentence.strip(),
                    "kroky": kroky_pro_akci
                }
                
                project_data["next_id"] += 1
                project_data["scenarios"].append(new_testcase)
                save_json(PROJECTS_PATH, st.session_state.projects)
                st.success(f"✅ Test case added: {test_name}")
                st.rerun()

# ---------- STRÁNKA 2: EDIT ACTIONS & STEPS ----------
elif page == "🔧 Edit Actions & Steps":
    st.title("🔧 Edit Actions & Steps")
    st.markdown("Manage actions and their steps in `kroky.json`")
    
    # Cesty
    BASE_DIR = Path(__file__).resolve().parent
    DATA_DIR = BASE_DIR / "data"
    KROKY_PATH = DATA_DIR / "kroky.json"
    
    # Načtení dat
    steps_data = load_json(KROKY_PATH)
    
    # Session state
    if 'edit_steps_data' not in st.session_state:
        st.session_state.edit_steps_data = steps_data
    if 'editing_action' not in st.session_state:
        st.session_state.editing_action = None
    if 'new_steps' not in st.session_state:
        st.session_state.new_steps = []
    
    # ---------- ADD NEW ACTION ----------
    st.subheader("➕ Add New Action")
    
    if st.button("➕ Add New Action", key="new_action_main", use_container_width=True):
        st.session_state.new_action = True
        st.session_state.editing_action = None
    
    # NEW ACTION FORM
    if st.session_state.get("new_action", False):
        st.subheader("➕ Add New Action")
        
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
                        # Save to kroky.json
                        st.session_state.edit_steps_data[action_name.strip()] = {
                            "description": action_desc.strip(),
                            "steps": st.session_state.new_steps.copy()
                        }
                        save_json(KROKY_PATH, st.session_state.edit_steps_data)
                        st.success(f"✅ Action '{action_name}' added to kroky.json!")
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
                st.warning(f"Are you sure you want to delete action '{action}'?")
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("Yes, delete", key=f"confirm_del_{action}"):
                        del st.session_state.edit_steps_data[action]
                        save_json(KROKY_PATH, st.session_state.edit_steps_data)
                        st.success(f"✅ Action '{action}' deleted from kroky.json!")
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
                        save_json(KROKY_PATH, st.session_state.edit_steps_data)
                        st.success(f"✅ Action '{action}' updated in kroky.json!")
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

# ---------- STRÁNKA 3: TEXT COMPARATOR ----------
elif page == "📝 Text Comparator":
    st.title("📝 Text Comparator")
    st.markdown("Compare two texts with highlighted differences")
    
    if 'text1_input' not in st.session_state:
        st.session_state.text1_input = ""
    if 'text2_input' not in st.session_state:
        st.session_state.text2_input = ""
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Text 1")
        text1 = st.text_area(
            "Enter first text:", 
            height=300, 
            key="text1_area",
            value=st.session_state.text1_input,
            help="Enter or paste your first text here"
        )
    
    with col2:
        st.subheader("Text 2")
        text2 = st.text_area(
            "Enter second text:", 
            height=300, 
            key="text2_area",
            value=st.session_state.text2_input,
            help="Enter or paste your second text here"
        )
    
    st.markdown("---")
    
    # Create buttons in a row
    col_buttons = st.columns([1, 1, 1, 4])
    
    with col_buttons[0]:
        compare_btn = st.button("🔍 **Compare**", use_container_width=True, type="primary", help="Compare texts and highlight differences")
    
    with col_buttons[1]:
        diacritics_btn = st.button("❌ **Remove Diacritics**", use_container_width=True, help="Remove all accents, háčky and čárky from both texts")
    
    with col_buttons[2]:
        reset_btn = st.button("🔄 **Reset**", use_container_width=True, help="Clear both text fields")
    
    # Button actions
    if diacritics_btn:
        if text1 or text2:
            st.session_state.text1_input = remove_diacritics(text1)
            st.session_state.text2_input = remove_diacritics(text2)
            st.success("✅ Diacritics removed from both texts")
            st.rerun()
        else:
            st.warning("Enter text in at least one field to remove diacritics")
    
    if reset_btn:
        st.session_state.text1_input = ""
        st.session_state.text2_input = ""
        st.success("✅ Texts cleared")
        st.rerun()
    
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
            
            def highlight_differences(text1, text2):
                result = ""
                i, j = 0, 0
                
                while i < len(text1) and j < len(text2):
                    if text1[i] == text2[j]:
                        result += text1[i]
                        i += 1
                        j += 1
                    else:
                        char_display = text1[i] if text1[i] != ' ' else '␣'
                        result += f'<span style="background-color: #ff4444; color: white; font-weight: bold; padding: 1px 3px; border-radius: 3px;">{char_display}</span>'
                        i += 1
                        j += 1
                
                while i < len(text1):
                    char_display = text1[i] if text1[i] != ' ' else '␣'
                    result += f'<span style="background-color: #ff4444; color: white; font-weight: bold; padding: 1px 3px; border-radius: 3px;">{char_display}</span>'
                    i += 1
                
                return result
            
            highlighted1 = highlight_differences(text1, text2)
            highlighted2 = highlight_differences(text2, text1)
            
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
            
            matches = 0
            total = min(len(text1), len(text2))
            
            for i in range(total):
                if text1[i] == text2[i]:
                    matches += 1
            
            if total > 0:
                similarity = (matches / total) * 100
            else:
                similarity = 0
            
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