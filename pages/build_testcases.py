import streamlit as st
import pandas as pd
from pathlib import Path
from core import (
    load_json, save_json,
    PROJECTS_PATH, KROKY_PATH,
    generate_testcase, export_to_excel,
    PRIORITY_MAP, COMPLEXITY_MAP,
    get_steps_from_action, analyze_scenarios,
    get_automatic_complexity
)

def show():
    # ---------- SESSION STATE ----------
    if 'projects' not in st.session_state:
        st.session_state.projects = load_json(PROJECTS_PATH)
    if 'selected_project' not in st.session_state:
        st.session_state.selected_project = None
    if 'steps_data' not in st.session_state:
        st.session_state.steps_data = load_json(KROKY_PATH)
    
    # ---------- HELPER FUNCTIONS ----------
    def save_projects():
        return save_json(PROJECTS_PATH, st.session_state.projects)
    
    def make_scenarios_df(project_name):
        if project_name not in st.session_state.projects:
            return pd.DataFrame()
        
        scenarios = st.session_state.projects[project_name].get("scenarios", [])
        rows = []
        
        for tc in scenarios:
            rows.append({
                "Order": tc.get("order_no"),
                "Test Name": tc.get("test_name"),
                "Action": tc.get("akce"),
                "Segment": tc.get("segment"),
                "Channel": tc.get("kanal"),
                "Priority": tc.get("priority"),
                "Complexity": tc.get("complexity"),
                "Steps": len(tc.get("kroky", []))
            })
        
        df = pd.DataFrame(rows)
        if not df.empty:
            df = df.sort_values(by="Order", ascending=True)
        return df
    
    def renumber_scenarios(project_name):
        if project_name not in st.session_state.projects:
            return
        
        scenarios = st.session_state.projects[project_name]["scenarios"]
        
        for i, tc in enumerate(sorted(scenarios, key=lambda x: x["order_no"]), start=1):
            new_number = f"{i:03d}"
            tc["order_no"] = i
            
            if "_" in tc["test_name"]:
                parts = tc["test_name"].split("_", 1)
                if parts[0].isdigit() and len(parts[0]) <= 3:
                    tc["test_name"] = f"{new_number}_{parts[1]}"
                else:
                    tc["test_name"] = f"{new_number}_{tc['test_name']}"
            else:
                tc["test_name"] = f"{new_number}_{tc['test_name']}"
        
        save_projects()
        st.success("✅ Scenarios have been renumbered.")
        st.rerun()
    
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
    
    if st.sidebar.button("✅ Create Project"):
        if new_project.strip():
            if new_project.strip() not in st.session_state.projects:
                st.session_state.projects[new_project.strip()] = {
                    "next_id": 1,
                    "subject": "UAT2\\Antosova\\",
                    "scenarios": []
                }
                save_projects()
                st.session_state.selected_project = new_project.strip()
                st.rerun()
    
    # Project management
    if selected != "— select —" and selected in st.session_state.projects:
        st.session_state.selected_project = selected
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("⚙️ Project Management")
        
        with st.sidebar.expander("✏️ Edit Project Name"):
            new_name = st.text_input("New Project Name", value=selected)
            if st.button("Save New Name"):
                if new_name.strip() and new_name != selected:
                    st.session_state.projects[new_name] = st.session_state.projects.pop(selected)
                    st.session_state.selected_project = new_name
                    save_projects()
                    st.success("✅ Project name changed")
                    st.rerun()
        
        with st.sidebar.expander("📝 Edit Subject"):
            current_subject = st.session_state.projects[selected].get("subject", "UAT2\\Antosova\\")
            new_subject = st.text_input("New Subject", value=current_subject)
            if st.button("Save Subject"):
                if new_subject.strip():
                    st.session_state.projects[selected]["subject"] = new_subject.strip()
                    save_projects()
                    st.success("✅ Subject changed")
                    st.rerun()
    
    # ---------- MAIN CONTENT ----------
    st.title("🏗️ Build Test Cases")
    
    if st.session_state.selected_project is None:
        st.info("Select or create a project in the left panel.")
        return
    
    project_name = st.session_state.selected_project
    
    # Project overview - OPRAVENÉ (bez backslashu ve f-stringu)
    st.subheader("📊 Project Overview")
    st.write(f"**Active Project:** {project_name}")
    
    # OPRAVA: Bez backslashu ve f-stringu
    subject_value = st.session_state.projects[project_name].get('subject', 'UAT2\\Antosova\\')
    st.write(f"**Subject:** {subject_value}")
    
    st.write(f"**Number of Scenarios:** {len(st.session_state.projects[project_name].get('scenarios', []))}")
    
    st.markdown("---")
    
    # ADD NEW SCENARIO
    st.subheader("➕ Add New Scenario")
    
    # Get available actions
    action_list = list(st.session_state.steps_data.keys())
    
    with st.form("add_scenario_form"):
        sentence = st.text_area("Sentence (requirement)", height=100, 
                              placeholder="e.g.: Activate DSL for B2C via SHOP channel...")
        action = st.selectbox("Action (from kroky.json)", options=action_list)
        
        # Get steps for selected action
        steps_for_action = get_steps_from_action(action, st.session_state.steps_data)
        step_count = len(steps_for_action)
        
        # Automatic complexity
        auto_complexity = get_automatic_complexity(step_count)
        
        col_priority, col_complexity = st.columns(2)
        with col_priority:
            priority = st.selectbox("Priority", options=list(PRIORITY_MAP.values()), index=1)
        with col_complexity:
            complexity = st.selectbox(
                "Complexity", 
                options=list(COMPLEXITY_MAP.values()), 
                index=list(COMPLEXITY_MAP.values()).index(auto_complexity),
                help=f"Automatically set to {auto_complexity} based on {step_count} steps"
            )
        
        if st.form_submit_button("➕ Add Scenario"):
            if not sentence.strip():
                st.error("Sentence cannot be empty.")
            elif not action:
                st.error("Select an action.")
            else:
                tc = generate_testcase(
                    project=project_name,
                    sentence=sentence.strip(),
                    action=action,
                    priority=priority,
                    complexity=complexity,
                    steps_data=st.session_state.steps_data,
                    projects_data=st.session_state.projects
                )
                st.success(f"✅ Scenario added: {tc['test_name']}")
                st.rerun()
    
    st.markdown("---")
    
    # SCENARIO LIST
    st.subheader("📋 Scenario List")
    
    df = make_scenarios_df(project_name)
    if not df.empty:
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
        
        if st.button("🔢 Renumber Scenarios from 001", use_container_width=True):
            renumber_scenarios(project_name)
    else:
        st.info("No scenarios yet. Add your first scenario above.")
    
    st.markdown("---")
    
    # SCENARIO ANALYSIS
    st.subheader("📊 Scenario Analysis")
    
    scenarios = st.session_state.projects[project_name].get("scenarios", [])
    if scenarios:
        segment_data = analyze_scenarios(scenarios)
        
        col_b2c, col_b2b = st.columns(2)
        
        with col_b2c:
            with st.expander("👥 B2C", expanded=True):
                if "B2C" in segment_data and segment_data["B2C"]:
                    for channel in segment_data["B2C"]:
                        st.markdown(f"<h4 style='margin-bottom: 5px;'>{channel}</h4>", unsafe_allow_html=True)
                        
                        for technology in segment_data["B2C"][channel]:
                            st.markdown(f"<strong>{technology}</strong>", unsafe_allow_html=True)
                            
                            for action in segment_data["B2C"][channel][technology]:
                                st.write(f"  • {action}")
                        
                        if channel != list(segment_data["B2C"].keys())[-1]:
                            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                else:
                    st.write("No B2C scenarios")
        
        with col_b2b:
            with st.expander("🏢 B2B", expanded=True):
                if "B2B" in segment_data and segment_data["B2B"]:
                    for channel in segment_data["B2B"]:
                        st.markdown(f"<h4 style='margin-bottom: 5px;'>{channel}</h4>", unsafe_allow_html=True)
                        
                        for technology in segment_data["B2B"][channel]:
                            st.markdown(f"<strong>{technology}</strong>", unsafe_allow_html=True)
                            
                            for action in segment_data["B2B"][channel][technology]:
                                st.write(f"  • {action}")
                        
                        if channel != list(segment_data["B2B"].keys())[-1]:
                            st.markdown("<hr style='margin: 10px 0;'>", unsafe_allow_html=True)
                else:
                    st.write("No B2B scenarios")
    
    st.markdown("---")
    
    # EXPORT
    st.subheader("📤 Export Project")
    
    if st.button("💾 Export to Excel", use_container_width=True, type="primary"):
        with st.spinner("Exporting to Excel..."):
            export_result = export_to_excel(project_name, st.session_state.projects)
            
            if export_result:
                # Create safe filename
                safe_name = "".join(c for c in project_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
                safe_name = safe_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
                filename = f"testcases_{safe_name}.xlsx"
                
                st.success("✅ Export complete! File ready for download.")
                
                st.download_button(
                    label="⬇️ Download Excel File",
                    data=export_result.getvalue(),
                    file_name=filename,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )
            else:
                st.error("❌ No data to export")