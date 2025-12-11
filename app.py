import streamlit as st
import json
import os
import copy
import re
from datetime import datetime
from pathlib import Path

# ---------- CONFIG ----------
PROJECTS_PATH = "projects.json"
STEPS_PATH = "kroky.json"

# ---------- FUNCTIONS ----------
def load_json(filepath):
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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

def extract_channel(sentence):
    sentence_lower = sentence.lower()
    if "shop" in sentence_lower:
        return "SHOP"
    elif "admin" in sentence_lower:
        return "ADMIN"
    elif "crm" in sentence_lower:
        return "CRM"
    elif "api" in sentence_lower:
        return "API"
    elif "bulk" in sentence_lower:
        return "BULK"
    return "UNKNOWN"

def extract_segment(sentence):
    sentence_lower = sentence.lower()
    if "b2c" in sentence_lower:
        return "B2C"
    elif "b2b" in sentence_lower:
        return "B2B"
    elif "hgu" in sentence_lower:
        return "HGU"
    elif "soho" in sentence_lower:
        return "SOHO"
    return "UNKNOWN"

def extract_technology(sentence):
    sentence_lower = sentence.lower()
    if "dsl" in sentence_lower:
        return "DSL"
    elif "fiber" in sentence_lower or "optika" in sentence_lower:
        return "FIBER"
    elif "4g" in sentence_lower or "lte" in sentence_lower:
        return "4G"
    elif "5g" in sentence_lower:
        return "5G"
    elif "tv" in sentence_lower or "televize" in sentence_lower:
        return "TV"
    return "UNKNOWN"

def remove_diacritics(text):
    """Remove Czech diacritics from text."""
    replacements = {
        'á': 'a', 'č': 'c', 'ď': 'd', 'é': 'e', 'ě': 'e',
        'í': 'i', 'ň': 'n', 'ó': 'o', 'ř': 'r', 'š': 's',
        'ť': 't', 'ú': 'u', 'ů': 'u', 'ý': 'y', 'ž': 'z',
        'Á': 'A', 'Č': 'C', 'Ď': 'D', 'É': 'E', 'Ě': 'E',
        'Í': 'I', 'Ň': 'N', 'Ó': 'O', 'Ř': 'R', 'Š': 'S',
        'Ť': 'T', 'Ú': 'U', 'Ů': 'U', 'Ý': 'Y', 'Ž': 'Z'
    }
    for orig, repl in replacements.items():
        text = text.replace(orig, repl)
    return text

# ---------- PAGE CONFIG ----------
st.set_page_config(
    page_title="Test Case Manager",
    page_icon="🧪",
    layout="wide"
)

# ---------- INIT SESSION STATE ----------
if "projects" not in st.session_state:
    st.session_state.projects = load_json(PROJECTS_PATH)

if "steps_data" not in st.session_state:
    st.session_state.steps_data = load_json(STEPS_PATH)

# ---------- NAVIGATION ----------
# Page selection in sidebar
st.sidebar.title("🧪 Test Case Manager")

# Add page selection radio
page = st.sidebar.radio(
    "Select Page:",
    ["📋 Test Cases", "🔧 Edit Actions & Steps", "📝 Text Comparator"],
    index=0
)

# ---------- PROJECT SELECTION (COMMON FOR ALL PAGES) ----------
with st.sidebar:
    project_names = list(st.session_state.projects.keys())
    
    if not project_names:
        st.warning("No projects found. Create a new project.")
        new_project_name = st.text_input("New Project Name")
        if st.button("Create Project"):
            if new_project_name:
                st.session_state.projects[new_project_name] = {
                    "created": datetime.now().strftime("%Y-%m-%d"),
                    "next_id": 1,
                    "scenarios": []
                }
                save_json(PROJECTS_PATH, st.session_state.projects)
                st.success(f"Project '{new_project_name}' created!")
                st.rerun()
    else:
        selected_project = st.selectbox("Select Project", project_names, key="project_select")
        
        # Create new project
        st.markdown("---")
        st.subheader("New Project")
        new_project = st.text_input("Project Name", key="new_project_name")
        if st.button("Create New Project"):
            if new_project and new_project not in st.session_state.projects:
                st.session_state.projects[new_project] = {
                    "created": datetime.now().strftime("%Y-%m-%d"),
                    "next_id": 1,
                    "scenarios": []
                }
                save_json(PROJECTS_PATH, st.session_state.projects)
                st.success(f"Project '{new_project}' created!")
                st.rerun()
            elif new_project in st.session_state.projects:
                st.error("Project already exists!")
        
        # Delete project
        st.markdown("---")
        st.subheader("Delete Project")
        project_to_delete = st.selectbox("Select to delete", [""] + project_names, key="delete_project_select")
        if project_to_delete and st.button("Delete Project", type="secondary"):
            del st.session_state.projects[project_to_delete]
            save_json(PROJECTS_PATH, st.session_state.projects)
            st.success(f"Project '{project_to_delete}' deleted!")
            st.rerun()

# ---------- PAGE 1: TEST CASES ----------
if page == "📋 Test Cases":
    if not project_names:
        st.title("Welcome to Test Case Manager 👋")
        st.info("Create your first project using the sidebar.")
        st.stop()
    
    project_data = st.session_state.projects[selected_project]
    
    # ---------- AUTOMATIC RENUMBERING (RUNS EVERY TIME PAGE LOADS) ----------
    if "scenarios" in project_data and project_data["scenarios"]:
        # Kontrola, zda je číslování v pořádku
        orders = [tc["order_no"] for tc in project_data["scenarios"]]
        expected_orders = list(range(1, len(orders) + 1))
        
        # Pokud číslování není v pořádku, přečíslujeme
        if orders != expected_orders:
            # Seřadíme podle aktuálního order_no
            scenarios_sorted = sorted(project_data["scenarios"], key=lambda x: x["order_no"])
            
            for i, tc in enumerate(scenarios_sorted, 1):
                old_order = tc["order_no"]
                old_name = tc["test_name"]
                
                # Pokud se číslo změnilo, aktualizujeme
                if old_order != i:
                    tc["order_no"] = i
                    
                    # Aktualizujeme název - nahradíme staré číslo novým
                    parts = old_name.split('_', 1)
                    if len(parts) > 1:
                        rest_of_name = parts[1]
                        new_name = f"{i:03d}_{rest_of_name}"
                        tc["test_name"] = new_name
            
            project_data["scenarios"] = scenarios_sorted
            project_data["next_id"] = len(scenarios_sorted) + 1
            save_json(PROJECTS_PATH, st.session_state.projects)
            st.rerun()

    # ---------- HEADER ----------
    st.title(f"🧪 {selected_project}")
    st.caption(f"Created: {project_data.get('created', 'N/A')} | Next ID: {project_data.get('next_id', 1)}")

    # ---------- ROW 1: TEST CASE LIST ----------
    st.subheader("📋 Test Cases")
    if project_data["scenarios"]:
        for tc in project_data["scenarios"]:
            with st.expander(f"{tc['order_no']:03d} - {tc['test_name']}"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.write(f"**Action:** {tc['akce']}")
                    st.write(f"**Channel:** {tc['kanal']}")
                with col2:
                    st.write(f"**Segment:** {tc['segment']}")
                    st.write(f"**Tech:** {tc.get('technology', 'N/A')}")
                with col3:
                    st.write(f"**Priority:** {tc['priority']}")
                    st.write(f"**Complexity:** {tc['complexity']}")
                
                st.write(f"**Requirement:** {tc['veta']}")
                
                if tc.get('kroky'):
                    st.write("**Steps:**")
                    for i, step in enumerate(tc['kroky'], 1):
                        st.write(f"{i}. {step}")
    else:
        st.info("No test cases yet. Add your first one below!")

    # ---------- ROW 2: ADD NEW TEST CASE ----------
    st.subheader("➕ Add New Test Case")

    if not st.session_state.steps_data:
        st.error("❌ No actions found! Please add actions in 'Edit Actions & Steps' page first.")
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
                
                # Build test name - NOVÁ LOGIKA BEZ UNKNOWN
                channel = extract_channel(sentence)
                segment = extract_segment(sentence)
                technology = extract_technology(sentence)
                
                # Sestavíme prefix a vyčistíme UNKNOWN části
                prefix_parts = [f"{order:03d}", channel, segment, technology]
                # Filtrujeme UNKNOWN a prázdné hodnoty
                filtered_parts = [p for p in prefix_parts if p and p != "UNKNOWN"]
                prefix = "_".join(filtered_parts)
                
                # Ošetříme případ duplicitních podtržítek v prefixu
                while '__' in prefix:
                    prefix = prefix.replace('__', '_')
                prefix = prefix.strip('_')
                
                test_name = f"{prefix}_{sentence.strip().capitalize()}"
                
                # Ještě jednou vyčistíme celý název pro jistotu
                test_name = clean_tc_name(test_name)
                
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

    # ---------- ROW 3: EDIT TEST CASE (IN EXPANDER) ----------
    with st.expander("✏️ Edit Test Case", expanded=False):
        if project_data["scenarios"]:
            testcase_options = {f"{tc['order_no']:03d} - {tc['test_name']}": tc for tc in project_data["scenarios"]}
            selected_testcase_key = st.selectbox(
                "Select Test Case to Edit",
                options=list(testcase_options.keys()),
                index=0,
                key="edit_testcase_select"
            )
            
            if selected_testcase_key:
                testcase_to_edit = testcase_options[selected_testcase_key]
                
                with st.form("edit_testcase_form"):
                    # Předvyplníme aktuální větu z test case
                    sentence = st.text_area(
                        "Requirement Sentence", 
                        value=testcase_to_edit["veta"],
                        height=100,
                        key="edit_sentence"
                    )
                    
                    action = st.selectbox(
                        "Action (from kroky.json)", 
                        options=action_list,
                        index=action_list.index(testcase_to_edit["akce"]) if testcase_to_edit["akce"] in action_list else 0,
                        key="edit_action"
                    )
                    
                    col_priority, col_complexity = st.columns(2)
                    with col_priority:
                        priority = st.selectbox(
                            "Priority", 
                            options=PRIORITY_MAP_VALUES,
                            index=PRIORITY_MAP_VALUES.index(testcase_to_edit["priority"]) if testcase_to_edit["priority"] in PRIORITY_MAP_VALUES else 1,
                            key="edit_priority"
                        )
                    with col_complexity:
                        complexity = st.selectbox(
                            "Complexity", 
                            options=COMPLEXITY_MAP_VALUES,
                            index=COMPLEXITY_MAP_VALUES.index(testcase_to_edit["complexity"]) if testcase_to_edit["complexity"] in COMPLEXITY_MAP_VALUES else 3,
                            key="edit_complexity"
                        )
                    
                    if st.form_submit_button("💾 Save Changes"):
                        if not sentence.strip():
                            st.error("Requirement sentence cannot be empty.")
                        elif not action:
                            st.error("Select an action.")
                        else:
                            # Re-generate test name with updated values
                            order = testcase_to_edit["order_no"]
                            
                            # Build test name - S NOVOU LOGIKOU BEZ UNKNOWN
                            channel = extract_channel(sentence)
                            segment = extract_segment(sentence)
                            technology = extract_technology(sentence)
                            
                            # Sestavíme prefix a vyčistíme UNKNOWN části
                            prefix_parts = [f"{order:03d}", channel, segment, technology]
                            # Filtrujeme UNKNOWN a prázdné hodnoty
                            filtered_parts = [p for p in prefix_parts if p and p != "UNKNOWN"]
                            prefix = "_".join(filtered_parts)
                            
                            # Ošetříme případ duplicitních podtržítek v prefixu
                            while '__' in prefix:
                                prefix = prefix.replace('__', '_')
                            prefix = prefix.strip('_')
                            
                            new_test_name = f"{prefix}_{sentence.strip().capitalize()}"
                            new_test_name = clean_tc_name(new_test_name)
                            
                            # Get steps for the new action
                            kroky_pro_akci = []
                            if action in st.session_state.steps_data:
                                action_data = st.session_state.steps_data[action]
                                if isinstance(action_data, dict) and "steps" in action_data:
                                    kroky_pro_akci = copy.deepcopy(action_data["steps"])
                                elif isinstance(action_data, list):
                                    kroky_pro_akci = copy.deepcopy(action_data)
                            
                            # Update the test case
                            testcase_to_edit.update({
                                "test_name": new_test_name,
                                "akce": action,
                                "segment": segment,
                                "kanal": channel,
                                "priority": priority,
                                "complexity": complexity,
                                "veta": sentence.strip(),
                                "kroky": kroky_pro_akci
                            })
                            
                            save_json(PROJECTS_PATH, st.session_state.projects)
                            st.success(f"✅ Test case updated: {new_test_name}")
                            st.rerun()
        else:
            st.info("No test cases available to edit. Add a test case first.")

    # ---------- ROW 4: DELETE TEST CASE (IN EXPANDER) ----------
    with st.expander("🗑️ Delete Test Case", expanded=False):
        if project_data["scenarios"]:
            delete_options = [f"{tc['order_no']:03d} - {tc['test_name']}" for tc in project_data["scenarios"]]
            testcase_to_delete = st.selectbox(
                "Select Test Case to Delete",
                options=delete_options,
                index=0,
                key="delete_testcase_select"
            )
            
            if st.button("⚠️ Delete Selected Test Case", type="secondary"):
                # Najdeme index test case k smazání
                index_to_delete = delete_options.index(testcase_to_delete)
                
                # Odstraníme
                deleted_tc = project_data["scenarios"].pop(index_to_delete)
                
                # AUTOMATICKÉ PŘEČÍSLOVÁNÍ
                # Seřadíme podle aktuálního order_no
                scenarios_sorted = sorted(project_data["scenarios"], key=lambda x: x["order_no"])
                
                for i, tc in enumerate(scenarios_sorted, 1):
                    old_order = tc["order_no"]
                    old_name = tc["test_name"]
                    
                    # Pokud se číslo změnilo, aktualizujeme
                    if old_order != i:
                        tc["order_no"] = i
                        
                        # Aktualizujeme název
                        parts = old_name.split('_', 1)
                        if len(parts) > 1:
                            rest_of_name = parts[1]
                            new_name = f"{i:03d}_{rest_of_name}"
                            tc["test_name"] = new_name
                
                project_data["scenarios"] = scenarios_sorted
                project_data["next_id"] = len(scenarios_sorted) + 1
                
                # Uložíme
                save_json(PROJECTS_PATH, st.session_state.projects)
                st.success(f"🗑️ Test case deleted: {deleted_tc['test_name']}")
                st.success(f"📝 Test cases renumbered from 001")
                st.rerun()
        else:
            st.info("No test cases available to delete.")

    # ---------- ROW 5: MANUAL RENUMBERING (OPTIONAL SAFETY) ----------
    with st.expander("🔢 Manual Renumbering (Safety)", expanded=False):
        st.warning("Use this if automatic renumbering didn't work correctly.")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Check & Renumber All"):
                if "scenarios" in project_data and project_data["scenarios"]:
                    orders = [tc["order_no"] for tc in project_data["scenarios"]]
                    expected_orders = list(range(1, len(orders) + 1))
                    
                    if orders == expected_orders:
                        st.success("✅ Test cases are already correctly numbered!")
                    else:
                        # Přečíslujeme
                        scenarios_sorted = sorted(project_data["scenarios"], key=lambda x: x["order_no"])
                        
                        for i, tc in enumerate(scenarios_sorted, 1):
                            old_order = tc["order_no"]
                            old_name = tc["test_name"]
                            
                            if old_order != i:
                                tc["order_no"] = i
                                
                                parts = old_name.split('_', 1)
                                if len(parts) > 1:
                                    rest_of_name = parts[1]
                                    new_name = f"{i:03d}_{rest_of_name}"
                                    tc["test_name"] = new_name
                        
                        project_data["scenarios"] = scenarios_sorted
                        project_data["next_id"] = len(scenarios_sorted) + 1
                        save_json(PROJECTS_PATH, st.session_state.projects)
                        st.success(f"✅ Renumbered {len(scenarios_sorted)} test cases from 001 to {len(scenarios_sorted):03d}")
                        st.rerun()
                else:
                    st.info("No test cases to renumber.")
        
        with col2:
            if st.button("📊 Show Numbering Status"):
                if "scenarios" in project_data and project_data["scenarios"]:
                    orders = [tc["order_no"] for tc in project_data["scenarios"]]
                    expected_orders = list(range(1, len(orders) + 1))
                    
                    st.write(f"**Current orders:** {orders}")
                    st.write(f"**Expected orders:** {expected_orders}")
                    
                    if orders == expected_orders:
                        st.success("✅ Numbering is correct!")
                    else:
                        st.error("❌ Numbering is incorrect!")
                        
                        # Najdi chyby
                        errors = []
                        for i, (actual, expected) in enumerate(zip(orders, expected_orders), 1):
                            if actual != expected:
                                errors.append(f"Position {i}: Expected {expected}, got {actual}")
                        
                        if errors:
                            st.write("**Errors found:**")
                            for error in errors:
                                st.write(f"- {error}")
                else:
                    st.info("No test cases to check.")

    # ---------- FOOTER ----------
    st.markdown("---")
    st.caption(f"Project: {selected_project} | Total Test Cases: {len(project_data.get('scenarios', []))}")

# ---------- PAGE 2: EDIT ACTIONS & STEPS ----------
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

# ---------- PAGE 3: TEXT COMPARATOR ----------
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