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
    """Analyze scenarios for tree structure display"""
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
        
        # Organize data
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
# Cesty k souborům
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PROJECTS_PATH = DATA_DIR / "projects.json"
KROKY_PATH = DATA_DIR / "kroky.json"

# Načtení dat
projects = load_json(PROJECTS_PATH)
steps_data = load_json(KROKY_PATH)

# Session state
if 'projects' not in st.session_state:
    st.session_state.projects = projects
if 'selected_project' not in st.session_state:
    st.session_state.selected_project = None
if 'steps_data' not in st.session_state:
    st.session_state.steps_data = steps_data
        

# ---------- SIDEBAR ----------
with st.sidebar:
    st.title("🧪 Testool")
    st.markdown("---")

    # Navigation
    page = st.radio(
        "Navigation",
        [
            "🏗️ Build Test Cases",
            "🔧 Edit Actions & Steps",
            "📝 Text Comparator"
        ]
    )

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
                st.session_state.projects[new_project] = {
                    "next_id": 1,
                    "subject": r"UAT2\Antosova\\",
                    "scenarios": []
                }
                save_json(PROJECTS_PATH, st.session_state.projects)
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
                save_json(PROJECTS_PATH, st.session_state.projects)
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
                    save_json(PROJECTS_PATH, st.session_state.projects)
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
                save_json(PROJECTS_PATH, st.session_state.projects)
                st.success("Subject updated.")

        with col_delete:
            if st.button("🧹 Delete subject", use_container_width=True):
                st.session_state.projects[current_project]["subject"] = ""
                save_json(PROJECTS_PATH, st.session_state.projects)
                st.success("Subject cleared.")


    # ---------- STRÁNKA 1: BUILD TEST CASES ----------
if page == "🏗️ Build Test Cases":
    st.title("🏗️ Build Test Cases")
    
    if st.session_state.selected_project is None:
        st.info("Select or create a project in the sidebar.")
        st.stop()
    
    project_name = st.session_state.selected_project
    project_data = st.session_state.projects[project_name]
    
    # ---------- ROW 1: PROJECT OVERVIEW + ANALYSIS ----------
    col_overview, col_analysis = st.columns([1, 1.5])  # Pravá část (graf) větší
    
    with col_overview:
        st.subheader("📊 Project Overview")
        subject_value = project_data.get('subject', r'UAT2\Antosova\\')
        st.write(f"**Active Project:** {project_name}")
        st.write(f"**Subject:** {subject_value}")
        
        # Actions by Segment - přesunuto sem
        st.markdown("---")
        st.subheader("📋 Actions by Segment")
        
        testcases = project_data.get("scenarios", [])
        if testcases:
            # Statistiky pro expandery
            b2c_count = sum(1 for tc in testcases if tc.get("segment") == "B2C")
            b2b_count = sum(1 for tc in testcases if tc.get("segment") == "B2B")
            
            # Vytvořit strukturovaná data pro akce
            segment_data = {"B2C": {}, "B2B": {}}
            for tc in testcases:
                segment = tc.get("segment", "UNKNOWN")
                action = tc.get("akce", "UNKNOWN")
                
                if segment in ["B2C", "B2B"]:
                    if action not in segment_data[segment]:
                        segment_data[segment][action] = 0
                    segment_data[segment][action] += 1
            
            # Dva expandery vedle sebe
            col_b2c, col_b2b = st.columns(2)
            
            with col_b2c:
                with st.expander(f"👥 B2C ({b2c_count})", expanded=True):
                    if segment_data["B2C"]:
                        # Seřadit akce podle počtu test cases (nejvíc první)
                        sorted_actions = sorted(
                            segment_data["B2C"].items(), 
                            key=lambda x: x[1], 
                            reverse=True
                        )
                        for action, count in sorted_actions:
                            st.write(f"**{action}:** {count}")
                    else:
                        st.write("No test cases")
            
            with col_b2b:
                with st.expander(f"🏢 B2B ({b2b_count})", expanded=True):
                    if segment_data["B2B"]:
                        # Seřadit akce podle počtu test cases (nejvíc první)
                        sorted_actions = sorted(
                            segment_data["B2B"].items(), 
                            key=lambda x: x[1], 
                            reverse=True
                        )
                        for action, count in sorted_actions:
                            st.write(f"**{action}:** {count}")
                    else:
                        st.write("No test cases")
        else:
            st.info("No test cases yet")
    
    # ----------------------------GRAF---------------------------
    with col_analysis:
        st.markdown("<h3 style='text-align: center;'>📈 Distribution Analysis</h3>", unsafe_allow_html=True)
        testcases = project_data.get("scenarios", [])
        
        if testcases:
            # Základní statistiky
            testcase_count = len(testcases)
            b2c_count = sum(1 for tc in testcases if tc.get("segment") == "B2C")
            b2b_count = sum(1 for tc in testcases if tc.get("segment") == "B2B")
            
            # Vytvoři donut graf s hodnotami uvnitř
            fig_segment = go.Figure(data=[go.Pie(
                labels=[f'B2C: {b2c_count}', f'B2B: {b2b_count}'],  # Hodnoty v labelu
                values=[b2c_count, b2b_count],
                hole=0.5,  # Větší díra uprostřed
                marker_colors=["#16FF1EE5", "#FF0084"],  # Zelená a tmavá magenta
                textinfo='label',  # Zobrazí pouze label s hodnotou
                textposition='inside',  # Text uvnitř segmentů
                textfont=dict(size=16, color='white'),
                hoverinfo='label+percent',
                hovertemplate='<b>%{label}</b><br>Percentage: %{percent}<extra></extra>',
                insidetextorientation='horizontal'
            )])
            
            fig_segment.update_layout(
                showlegend=False,  # Bez legendy
                height=400,
                margin=dict(t=20, b=20, l=20, r=20),
                annotations=[
                    dict(
                        text=f"Total<br>{testcase_count}",
                        x=0.5, y=0.5,
                        font_size=24,
                        showarrow=False,
                        font=dict(color='#333333', family="Arial Black")
                    )
                ]
            )
            
            st.plotly_chart(fig_segment, use_container_width=True)
            
        else:
            # Prázdný graf placeholder
            fig_empty = go.Figure()
            fig_empty.update_layout(
                xaxis=dict(visible=False),
                yaxis=dict(visible=False),
                annotations=[
                    dict(
                        text="No test cases yet",
                        x=0.5,
                        y=0.5,
                        showarrow=False,
                        font=dict(size=16)
                    )
                ],
                height=400,
                margin=dict(t=20, b=20, l=20, r=20)
            )
            st.plotly_chart(fig_empty, use_container_width=True)


    # ------------------------------------ ROW 2: EXPORT SECTION ------------------------------------
    st.markdown("---")
    st.markdown("### 💾 Export Test Cases")
    st.write("Generate clean, renumbered & diacritics-free test cases Excel file.")

    col_export, col_future = st.columns([1, 2])

    with col_export:
        export_button = st.button(
            "💾 Export Test Cases to Excel",
            use_container_width=True
        )

    if export_button:
        # 1) Reindex test cases
        project_data = st.session_state.projects[project_name]

        project_data["scenarios"] = sorted(
            project_data["scenarios"],
            key=lambda x: x.get("order_no", 0)
        )

        for i, tc in enumerate(project_data["scenarios"], start=1):
            tc["order_no"] = i

            channel = tc["kanal"]
            segment = tc["segment"]
            technology = extract_technology(tc["veta"])
            sentence = tc["veta"].strip()

            prefix = "_".join(
                p for p in [f"{i:03d}", channel, segment, technology]
                if p and p != "UNKNOWN"
            )

            tc["test_name"] = clean_tc_name(
                f"{prefix}_{sentence.capitalize()}"
            )

        save_json(PROJECTS_PATH, st.session_state.projects)

        # 2) Build export data
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

    # ------------------------------------ ROW 3: TEST CASES LIST ------------------------------------
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

    

    # ------------------------------- ROW 4: ADD NEW TEST CASE ----------------------------------
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
                
                # Build test name
                channel = extract_channel(sentence)
                segment = extract_segment(sentence)
                technology = extract_technology(sentence)

                # Sestavíme prefix a vyčistíme UNKNOWN části
                prefix_parts = [f"{order:03d}", channel, segment, technology]
                # Filtrujeme UNKNOWN a prázdné hodnoty
                filtered_parts = [p for p in prefix_parts if p and p != "UNKNOWN"]
                prefix = "_".join(filtered_parts)

                # Ošetříme případ, že by po filtraci zůstalo jen číslo (např. ["009"])

                test_name = f"{prefix}_{sentence.strip().capitalize()}"

                # Ještě jednou vyčistíme (pro jistotu, pokud by sentence začínalo UNKNOWN apod.)
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


st.markdown("---")

with st.expander("✏️ Edit / Delete Test Cases", expanded=False):


    # ----------------------------------- ROW 5: EDIT EXISTING TEST CASE ---------------------------------
    st.subheader("✏️ Edit Existing Test Case")

    if project_data["scenarios"]:
        testcase_options = {
            f"{tc['order_no']:03d} - {tc['test_name']}": tc
            for tc in project_data["scenarios"]
        }

        selected_testcase_key = st.selectbox(
            "Select Test Case to Edit",
            options=list(testcase_options.keys()),
            index=0,
            key="edit_testcase_select"
        )

        testcase_to_edit = testcase_options[selected_testcase_key]

        with st.form("edit_testcase_form"):

            # ✅ FIX 1: sentence se správně propíše
            sentence = st.text_area(
                "Requirement Sentence",
                value=testcase_to_edit.get("veta", ""),
                height=100
            )

            action_list = sorted(list(st.session_state.steps_data.keys()))
            action = st.selectbox(
                "Action",
                options=action_list,
                index=action_list.index(testcase_to_edit["akce"])
                if testcase_to_edit["akce"] in action_list else 0
            )

            col_priority, col_complexity = st.columns(2)
            with col_priority:
                priority = st.selectbox(
                    "Priority",
                    PRIORITY_MAP_VALUES,
                    index=PRIORITY_MAP_VALUES.index(testcase_to_edit["priority"])
                )
            with col_complexity:
                complexity = st.selectbox(
                    "Complexity",
                    COMPLEXITY_MAP_VALUES,
                    index=COMPLEXITY_MAP_VALUES.index(testcase_to_edit["complexity"])
                )

            if st.form_submit_button("💾 Save Changes"):

                action_changed = action != testcase_to_edit["akce"]

                channel = extract_channel(sentence)
                segment = extract_segment(sentence)
                technology = extract_technology(sentence)

                prefix = "_".join(
                    p for p in [
                        f"{testcase_to_edit['order_no']:03d}",
                        channel, segment, technology
                    ]
                    if p and p != "UNKNOWN"
                )

                testcase_to_edit.update({
                    "test_name": clean_tc_name(
                        f"{prefix}_{sentence.strip().capitalize()}"
                    ),
                    "veta": sentence.strip(),
                    "akce": action,
                    "segment": segment,
                    "kanal": channel,
                    "priority": priority,
                    "complexity": complexity
                })

                # ✅ FIX 2: kroky se přepíší JEN při změně akce
                if action_changed:
                    action_data = st.session_state.steps_data.get(action, {})
                    testcase_to_edit["kroky"] = copy.deepcopy(
                        action_data.get("steps", action_data)
                    )

                save_json(PROJECTS_PATH, st.session_state.projects)
                st.success("Test case updated.")
                st.rerun()

    else:
        st.info("No test cases available.")

    st.markdown("---")

    # -------------------------------- DELETE TEST CASE ---------------------------------
    st.subheader("🗑️ Delete Test Case")

    delete_options = list(testcase_options.keys())

    testcase_to_delete = st.selectbox(
        "Select Test Case to Delete",
        options=delete_options,
        key="delete_testcase_select"
    )

    if st.button("⚠️ Delete Selected Test Case"):
        idx = delete_options.index(testcase_to_delete)
        deleted = project_data["scenarios"].pop(idx)
        save_json(PROJECTS_PATH, st.session_state.projects)
        st.success(f"Deleted: {deleted['test_name']}")
        st.rerun()
        

# --------------------------------------- PAGE 2: EDIT ACTIONS & STEPS ---------------------------------------
elif page == "🔧 Edit Actions & Steps":

    st.title("🔧 Edit Actions & Steps")
    st.markdown("Manage actions and their steps in `kroky.json`")

    BASE_DIR = Path(__file__).resolve().parent
    DATA_DIR = BASE_DIR / "data"
    KROKY_PATH = DATA_DIR / "kroky.json"

    steps_data = load_json(KROKY_PATH)

    if "edit_steps_data" not in st.session_state:
        st.session_state.edit_steps_data = steps_data
    if "editing_action" not in st.session_state:
        st.session_state.editing_action = None
    if "new_action" not in st.session_state:
        st.session_state.new_action = False
    if "new_steps" not in st.session_state:
        st.session_state.new_steps = []
    if "delete_action" not in st.session_state:
        st.session_state.delete_action = None

    # ---------- ADD NEW ACTION ----------
    st.subheader("➕ Add New Action")

    if st.button("➕ Add New Action", use_container_width=True):
        st.session_state.new_action = True
        st.session_state.editing_action = None

    if st.session_state.new_action:

        with st.form("new_action_form"):
            action_name = st.text_input("Action Name*", placeholder="e.g.: DSL_Activation")
            action_desc = st.text_input("Action Description*", placeholder="e.g.: DSL service activation")

            st.markdown("---")
            st.write("**Action Steps:**")

            for i, step in enumerate(st.session_state.new_steps):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.text_input("Description", value=step["description"], disabled=True, key=f"desc_view_{i}")
                    st.text_input("Expected", value=step["expected"], disabled=True, key=f"exp_view_{i}")
                with col2:
                    if st.form_submit_button("🗑️", key=f"del_new_step_{i}"):
                        st.session_state.new_steps.pop(i)
                        st.rerun()

            st.markdown("---")
            new_desc = st.text_area("New Step Description*", height=60)
            new_exp = st.text_area("New Step Expected*", height=60)

            if st.form_submit_button("➕ Add Step"):
                if new_desc.strip() and new_exp.strip():
                    st.session_state.new_steps.append({
                        "description": new_desc.strip(),
                        "expected": new_exp.strip()
                    })
                    st.rerun()

            st.markdown("---")
            col_save, col_cancel = st.columns(2)

            with col_save:
                if st.form_submit_button("💾 Save Action"):
                    if not action_name or not action_desc or not st.session_state.new_steps:
                        st.error("Fill all fields and add at least one step.")
                    else:
                        st.session_state.edit_steps_data[action_name] = {
                            "description": action_desc,
                            "steps": st.session_state.new_steps.copy()
                        }
                        save_json(KROKY_PATH, st.session_state.edit_steps_data)
                        st.session_state.new_action = False
                        st.session_state.new_steps = []
                        st.success("Action created.")
                        st.rerun()

            with col_cancel:
                if st.form_submit_button("❌ Cancel"):
                    st.session_state.new_action = False
                    st.session_state.new_steps = []
                    st.rerun()

    st.markdown("---")

    # ---------- EXISTING ACTIONS ----------
    st.subheader("📝 Existing Actions")

    for action, content in st.session_state.edit_steps_data.items():

        steps = content.get("steps", [])
        col1, col2, col3 = st.columns([3, 1, 1])

        with col1:
            st.write(f"**{action}**")
            st.caption(f"{len(steps)} steps")

        with col2:
            if st.button("✏️", key=f"edit_{action}"):
                st.session_state.editing_action = action

        with col3:
            if st.button("🗑️", key=f"delete_{action}"):
                st.session_state.delete_action = action

        if st.session_state.delete_action == action:
            st.warning(f"Delete action '{action}'?")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("Yes", key=f"confirm_{action}"):
                    del st.session_state.edit_steps_data[action]
                    save_json(KROKY_PATH, st.session_state.edit_steps_data)
                    st.session_state.delete_action = None
                    st.success("Action deleted.")
                    st.rerun()
            with c2:
                if st.button("Cancel", key=f"cancel_{action}"):
                    st.session_state.delete_action = None

        st.markdown("---")

    # ---------- EDIT ACTION ----------
    if st.session_state.editing_action:
        action = st.session_state.editing_action
        content = st.session_state.edit_steps_data[action]

        st.subheader(f"✏️ Edit Action: {action}")

        if f"edit_steps_{action}" not in st.session_state:
            st.session_state[f"edit_steps_{action}"] = copy.deepcopy(content["steps"])

        with st.form("edit_action_form"):
            desc = st.text_input("Action Description", value=content["description"])

            for i, step in enumerate(st.session_state[f"edit_steps_{action}"]):
                st.text_area(f"Step {i+1} Description", value=step["description"], key=f"e_desc_{i}")
                st.text_area(f"Step {i+1} Expected", value=step["expected"], key=f"e_exp_{i}")

            if st.form_submit_button("💾 Save Changes"):
                st.session_state.edit_steps_data[action] = {
                    "description": desc,
                    "steps": st.session_state[f"edit_steps_{action}"]
                }
                save_json(KROKY_PATH, st.session_state.edit_steps_data)
                st.session_state.editing_action = None
                st.success("Action updated.")
                st.rerun()


# --------------------------------------- PAGE 3: TEXT COMPARATOR ---------------------------------------
elif page == "📝 Text Comparator":

    st.title("📝 Text Comparator")
    st.markdown("Compare two texts")

    col1, col2 = st.columns(2)

    with col1:
        text1 = st.text_area("Text 1", height=300)
    with col2:
        text2 = st.text_area("Text 2", height=300)

    st.markdown("---")

    if st.button("❌ Remove Diacritics"):
        text1 = remove_diacritics(text1)
        text2 = remove_diacritics(text2)
        st.success("Diacritics removed.")

    if st.button("🔍 Compare"):
        matcher = difflib.SequenceMatcher(None, text1, text2)
        st.write(f"Similarity: {matcher.ratio() * 100:.1f}%")
