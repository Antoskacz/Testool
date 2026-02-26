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

def save_and_update_projects(data):
    """Uloží projekty do souboru a aktualizuje session_state"""
    base_dir = Path(__file__).resolve().parent
    projects_path = base_dir / "data" / "projects.json"
    success = save_json(projects_path, data)
    if success:
        st.session_state.projects = copy.deepcopy(data)
    return success

def save_and_update_steps(data):
    """Uloží kroky do souboru a aktualizuje session_state.

    Tries to save to kroky.json first (original file). If that fails,
    falls back to kroky_custom.json. On startup, both files are loaded
    and merged so users never lose data.
    """
    base_dir = Path(__file__).resolve().parent
    kroky_path = base_dir / "data" / "kroky.json"
    kroky_custom_path = base_dir / "data" / "kroky_custom.json"

    # sort keys so file is alphabetical
    ordered = dict(sorted(data.items(), key=lambda kv: kv[0].lower()))
    
    # Try primary file first
    success = save_json(kroky_path, ordered)
    saved_to = "kroky.json"
    
    # If primary fails, fallback to custom file
    if not success:
        st.warning(
            "⚠️ Could not write to kroky.json. "
            "Saving to kroky_custom.json instead. Your data is safe!"
        )
        success = save_json(kroky_custom_path, ordered)
        saved_to = "kroky_custom.json"
        if success:
            st.info(
                "ℹ️ Next app restart will automatically merge "
                "kroky_custom.json into kroky.json"
            )
    else:
        # Also keep custom file in sync if it exists
        if kroky_custom_path.exists():
            save_json(kroky_custom_path, ordered)
            saved_to = "both kroky.json and kroky_custom.json"
    
    if success:
        st.session_state.steps_data = copy.deepcopy(ordered)
        # Add subtle debug info if in dev mode
        st.toast(f"✅ Saved to {saved_to}", icon="💾")
    else:
        st.error("❌ Failed to save actions. Please contact admin.")
    
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

# ---------- HLAVNÍ APLIKACE ----------
st.title("🧪 Testool")
st.markdown("### Professional test case builder and manager")

# ---------- SIDEBAR ----------
# Cesty k souborům
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
PROJECTS_PATH = DATA_DIR / "projects.json"
KROKY_PATH = DATA_DIR / "kroky.json"
KROKY_CUSTOM_PATH = DATA_DIR / "kroky_custom.json"  # fallback file for custom actions

# Inicializace datových souborů až budou existovat
DATA_DIR.mkdir(exist_ok=True)

# Načtení dat
projects = load_json(PROJECTS_PATH)
steps_data = load_json(KROKY_PATH)

# Load custom actions (fallback file) and merge them with primary
custom_steps = load_json(KROKY_CUSTOM_PATH)
if custom_steps:
    # Merge custom actions into primary
    steps_data.update(custom_steps)
    # optionally log that we found custom actions


# Zajistíme, aby se prázdné soubory inicializovaly s minimem dat
if not projects or projects == {}:
    projects = {}
    save_json(PROJECTS_PATH, projects)

if not steps_data or steps_data == {}:
    steps_data = {}
    save_json(KROKY_PATH, steps_data)

# Session state - vždy načteme čerstvá data ze souborů
# To zajistí, že se neutrácejí změny mezi restarty aplikace
if 'projects' not in st.session_state:
    st.session_state.projects = copy.deepcopy(projects)
else:
    # Při každém novém spuštění znovu načteme data ze souboru
    # aby se neztratily žádné změny mezi restarty
    st.session_state.projects = copy.deepcopy(projects)

if 'selected_project' not in st.session_state:
    st.session_state.selected_project = None

if 'steps_data' not in st.session_state:
    st.session_state.steps_data = copy.deepcopy(steps_data)
else:
    # Znovu načteme aktuální data ze souboru
    st.session_state.steps_data = copy.deepcopy(steps_data)
        

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


    # ------------------------------------ EXPORT SECTION ------------------------------------
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

        save_and_update_projects(st.session_state.projects)

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
        st.error("❌ No actions found! Please add actions in 'Edit Actions & Steps' page first.")
        st.stop()
    
    action_list = sorted(list(st.session_state.steps_data.keys()))
    
    with st.form("add_testcase_form"):
        sentence = st.text_area("Requirement Sentence", height=100, 
                              placeholder="e.g.: Activate DSL for B2C via SHOP channel...")
        action = st.selectbox("Action (from kroky.json)", options=action_list)
        
        # Priority, Complexity, Segment, Kanal - 4 columns
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
                # Generování test case
                order = project_data["next_id"]
                
                # Build test name
                # Používáme vybrané hodnoty z dropdownů, ne extrahování z textu
                technology = extract_technology(sentence)

                # Sestavíme prefix a vyčistíme UNKNOWN části
                prefix_parts = [f"{order:03d}", kanal, segment, technology]
                # Filtrujeme UNKNOWN a prázdné hodnoty
                filtered_parts = [p for p in prefix_parts if p and p != "UNKNOWN"]
                prefix = "_".join(filtered_parts)

                test_name = f"{prefix}_{sentence.strip().capitalize()}"

                # Vyčistíme název
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

    # ---------- ROW 4: EDIT EXISTING TEST CASE ----------
    # ---------- ROW 4: EDIT EXISTING TEST CASE ----------
    # no wrapper, styling applied inside expander
    with st.expander("✏️ Edit Existing Test Case", expanded=False):
    
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
                # Initialize edit sentence only when testcase changes
                if "edit_sentence_value" not in st.session_state or \
                st.session_state.get("edit_sentence_tc") != testcase_to_edit["order_no"]:
                    st.session_state.edit_sentence_value = testcase_to_edit["veta"]
                    st.session_state.edit_sentence_tc = testcase_to_edit["order_no"]

                
                with st.form("edit_testcase_form"):
                    # Zobrazíme aktuální hodnoty
                    st.write(f"**Currently editing:** {testcase_to_edit['test_name']}")
                    
                    sentence = st.text_area(
                        "Requirement Sentence",
                        value=st.session_state.edit_sentence_value,
                        height=100,
                        key=f"edit_sentence_{testcase_to_edit['order_no']}"
                    )

                    
                    action = st.selectbox(
                        "Action (from kroky.json)", 
                        options=action_list,
                        index=action_list.index(testcase_to_edit["akce"]) if testcase_to_edit["akce"] in action_list else 0,
                        key="edit_action"
                    )
                    
                    # Priority, Complexity, Segment, Kanal - 4 columns
                    SEGMENT_OPTIONS = ["B2C", "B2B"]
                    KANAL_OPTIONS = ["SHOP", "IL"]
                    
                    col_priority, col_complexity, col_segment, col_kanal = st.columns(4)
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
                    with col_segment:
                        segment = st.selectbox(
                            "Segment",
                            options=SEGMENT_OPTIONS,
                            index=SEGMENT_OPTIONS.index(testcase_to_edit["segment"]) if testcase_to_edit["segment"] in SEGMENT_OPTIONS else 0,
                            key="edit_segment"
                        )
                    with col_kanal:
                        kanal = st.selectbox(
                            "Kanál",
                            options=KANAL_OPTIONS,
                            index=KANAL_OPTIONS.index(testcase_to_edit["kanal"]) if testcase_to_edit["kanal"] in KANAL_OPTIONS else 0,
                            key="edit_kanal"
                        )
                    
                    if st.form_submit_button("💾 Save Changes"):
                        if not sentence.strip():
                            st.error("Requirement sentence cannot be empty.")
                        elif not action:
                            st.error("Select an action.")
                        else:
                            # Re-generate test name with updated values
                            order = testcase_to_edit["order_no"]
                            
                            # Build test name - Používáme vybrané hodnoty z dropdownů
                            technology = extract_technology(sentence)
                            
                            # Sestavíme prefix a vyčistíme UNKNOWN části
                            prefix_parts = [f"{order:03d}", kanal, segment, technology]
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

                            st.session_state.edit_sentence_value = sentence.strip()

                            # Update the test case
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

    # ---------- ROW 5: DELETE TEST CASE ----------
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

                # Přečíslujeme všechny zbývající test case tak, aby šly za sebou od 1
                for idx, tc in enumerate(project_data["scenarios"], start=1):
                    tc["order_no"] = idx
                    # Také aktualizujeme test_name aby odrážel nové pořadové číslo
                    # Nahradíme původní 3-místné číslo na začátku (XXX_) novým
                    if tc["test_name"].startswith(f"{idx-1:03d}_"):
                        # Pokud se číslo změnilo, aktualizuj ho
                        tc["test_name"] = f"{idx:03d}_" + tc["test_name"][4:]
                    elif "_" in tc["test_name"]:
                        # Fallback: pokud format není očekávaný, zkus najít a nahradit 3-místné číslo
                        parts = tc["test_name"].split("_", 1)
                        if len(parts[0]) == 3 and parts[0].isdigit():
                            tc["test_name"] = f"{idx:03d}_" + parts[1]

                # Aktualizujeme next_id tak, aby nový TC dostal další pořadové číslo
                project_data["next_id"] = len(project_data["scenarios"]) + 1

                # Uložíme
                save_and_update_projects(st.session_state.projects)
                st.success(f"🗑️ Test case deleted: {deleted_tc['test_name']}")
                st.rerun()
        else:
            st.info("No test cases available to delete.")
    # end delete expander
            

# ---------- STRÁNKA 2: EDIT ACTIONS & STEPS ----------
elif page == "🔧 Edit Actions & Steps":
    st.title("🔧 Edit Actions & Steps")
    st.markdown("Manage actions and their steps in `kroky.json` and `kroky_custom.json`")
    
    # Display status of custom file if it exists
    if KROKY_CUSTOM_PATH.exists():
        custom_data = load_json(KROKY_CUSTOM_PATH)
        if custom_data:
            st.info(
                f"ℹ️ Found {len(custom_data)} custom action(s) in `kroky_custom.json`. "
                "These will be merged with the main file on startup."
            )

    # Use global steps_data which already includes merged custom actions
    # NOT local load of just kroky.json
    # init session state ONLY ONCE
    if "edit_steps_data" not in st.session_state:
        st.session_state.edit_steps_data = st.session_state.steps_data.copy()

    if "editing_action" not in st.session_state:
        st.session_state.editing_action = None

    if "new_steps" not in st.session_state:
        st.session_state.new_steps = []

    if "new_action" not in st.session_state:
        st.session_state.new_action = False

    if "delete_action" not in st.session_state:
        st.session_state.delete_action = None

    
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
                        # helper will save file and update session_state automatically
                        save_and_update_steps(st.session_state.edit_steps_data)
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
                        save_and_update_steps(st.session_state.edit_steps_data)
                        
                        # Clear steps from all affected scenarios
                        for project_data in st.session_state.projects.values():
                            if isinstance(project_data, dict) and "scenarios" in project_data:
                                for scenario in project_data["scenarios"]:
                                    if scenario.get("akce") == action:
                                        scenario["kroky"] = []
                        save_and_update_projects(st.session_state.projects)
                        
                        st.success(f"✅ Action '{action}' deleted from kroky.json!")
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
                        save_and_update_steps(st.session_state.edit_steps_data)
                        
                        # 🔄 Propagate changes to all scenarios using this action
                        updated = update_scenarios_with_action_steps(st.session_state.projects, st.session_state.steps_data, action)
                        save_and_update_projects(st.session_state.projects)
                        
                        st.success(f"✅ Action '{action}' updated in kroky.json!")
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

    # ---------- MANAGEMENT OF CUSTOM FILE ----------
    st.markdown("---")
    st.subheader("📁 File Management")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("**Primary File (kroky.json):**")
        primary_count = len(load_json(KROKY_PATH))
        st.metric("Actions", primary_count)
    
    with col2:
        st.write("**Custom File (kroky_custom.json):**")
        custom_count = len(load_json(KROKY_CUSTOM_PATH)) if KROKY_CUSTOM_PATH.exists() else 0
        st.metric("Actions", custom_count)
    
    if custom_count > 0:
        st.info(f"ℹ️ Found {custom_count} custom action(s). They are automatically merged with primary on startup.")
        
        col_merge, col_clear = st.columns(2)
        with col_merge:
            if st.button("🔄 Merge Custom → Primary", use_container_width=True):
                # Load both files
                primary = load_json(KROKY_PATH)
                custom = load_json(KROKY_CUSTOM_PATH)
                
                # Merge custom into primary
                primary.update(custom)
                
                # Save merged result back to primary
                save_and_update_steps(primary)
                
                # Clear custom file
                KROKY_CUSTOM_PATH.unlink()
                
                st.success("✅ Merged! Custom file deleted.")
                st.rerun()
        
        with col_clear:
            if st.button("🗑️ Clear Custom File", use_container_width=True):
                KROKY_CUSTOM_PATH.unlink()
                st.success("✅ Custom file deleted.")
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