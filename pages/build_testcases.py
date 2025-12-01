import streamlit as st
import pandas as pd
from pathlib import Path
from core import (
    load_json, save_json,
    PROJECTS_PATH, KROKY_PATH,
    generate_testcase, export_to_excel,
    PRIORITY_MAP, COMPLEXITY_MAP,
    get_steps_from_action, analyze_scenarios,
    get_automatic_complexity,
    parse_veta, extract_channel, extract_segment, extract_technology
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
    
    def make_testcases_df(project_name):
        """Create DataFrame of test cases for display"""
        if project_name not in st.session_state.projects:
            return pd.DataFrame()
        
        testcases = st.session_state.projects[project_name].get("scenarios", [])
        rows = []
        
        for tc in testcases:
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
    
    def renumber_testcases(project_name):
        """Renumber test cases starting from 001"""
        if project_name not in st.session_state.projects:
            return
        
        testcases = st.session_state.projects[project_name]["scenarios"]
        
        for i, tc in enumerate(sorted(testcases, key=lambda x: x["order_no"]), start=1):
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
        st.success("✅ Test cases have been renumbered.")
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
    
    if st.sidebar.button("✅ Create Project", use_container_width=True):
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
            else:
                st.sidebar.error("Project already exists!")
    
    # Project management
    if selected != "— select —" and selected in st.session_state.projects:
        st.session_state.selected_project = selected
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("⚙️ Project Management")
        
        with st.sidebar.expander("✏️ Edit Project Name"):
            new_name = st.text_input("New Project Name", value=selected)
            if st.button("Save New Name", key="save_name_btn"):
                if new_name.strip() and new_name != selected:
                    st.session_state.projects[new_name] = st.session_state.projects.pop(selected)
                    st.session_state.selected_project = new_name
                    save_projects()
                    st.success("✅ Project name changed")
                    st.rerun()
        
        with st.sidebar.expander("📝 Edit Subject"):
            current_subject = st.session_state.projects[selected].get("subject", "UAT2\\Antosova\\")
            new_subject = st.text_input("New Subject", value=current_subject)
            if st.button("Save Subject", key="save_subject_btn"):
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
    
    # ---------- ROW 1: PROJECT OVERVIEW + ANALYSIS ----------
    col_overview, col_analysis = st.columns([1, 1])
    
    with col_overview:
        st.subheader("📊 Project Overview")
        st.write(f"**Active Project:** {project_name}")
        
        subject_value = st.session_state.projects[project_name].get('subject', 'UAT2\\Antosova\\')
        st.write(f"**Subject:** {subject_value}")
        
        testcase_count = len(st.session_state.projects[project_name].get('scenarios', []))
        st.write(f"**Number of Test Cases:** {testcase_count}")
        
        # Quick stats
        if testcase_count > 0:
            testcases = st.session_state.projects[project_name]["scenarios"]
            b2c_count = sum(1 for tc in testcases if tc.get("segment") == "B2C")
            b2b_count = sum(1 for tc in testcases if tc.get("segment") == "B2B")
            st.write(f"**B2C:** {b2c_count} | **B2B:** {b2b_count}")
    
    with col_analysis:
        st.subheader("📈 Analysis")
        
        testcases = st.session_state.projects[project_name].get("scenarios", [])
        if testcases:
            segment_data = analyze_scenarios(testcases)
            
            # Compact analysis view
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
            st.info("No test cases for analysis")
    
    st.markdown("---")
    
    # ---------- ROW 2: TEST CASES LIST ----------
    st.subheader("📋 Test Cases List")
    
    df = make_testcases_df(project_name)
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
        
        # Actions for all test cases
        col_renumber, col_export = st.columns([1, 1])
        with col_renumber:
            if st.button("🔢 Renumber Test Cases from 001", use_container_width=True):
                renumber_testcases(project_name)
        with col_export:
            if st.button("💾 Export to Excel", use_container_width=True, type="primary"):
                with st.spinner("Exporting to Excel..."):
                    export_result = export_to_excel(project_name, st.session_state.projects)
                    
                    if export_result:
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
    else:
        st.info("No test cases yet. Add your first test case below.")
    
    st.markdown("---")
    
    # ---------- ROW 3: ADD NEW TEST CASE ----------
    col_add, col_import = st.columns([3, 1])
    
    with col_add:
        st.subheader("➕ Add New Test Case")
    
    with col_import:
        st.write("")  # Spacer
        if st.button("📤 Import from Excel", help="Import test cases from Excel file", use_container_width=True):
            st.info("🚧 Excel Import - Coming Soon!")
            st.write("This feature will be available in the next update.")
    
    # Check if we have actions available
    if not st.session_state.steps_data:
        st.error("❌ No actions found! Please add actions in 'Edit Actions & Steps' page first.")
        return
    
    action_list = list(st.session_state.steps_data.keys())
    
    with st.form("add_testcase_form"):
        sentence = st.text_area("Requirement Sentence", height=100, 
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
        
        if st.form_submit_button("➕ Add Test Case"):
            if not sentence.strip():
                st.error("Requirement sentence cannot be empty.")
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
                st.success(f"✅ Test case added: {tc['test_name']}")
                st.rerun()
    
    st.markdown("---")
    
    # ---------- ROW 4: EDIT & DELETE TEST CASES ----------
    st.subheader("✏️ Edit & Delete Test Cases")
    
    if not df.empty:
        # EDIT TEST CASE
        st.write("**Edit Existing Test Case:**")
        selected_row = st.selectbox(
            "Select test case to edit:",
            options=["— none —"] + [f"{row['Order']} - {row['Test Name']}" for _, row in df.iterrows()],
            index=0,
            key="edit_testcase_select"
        )
        
        if selected_row != "— none —":
            idx = int(selected_row.split(" - ")[0])
            testcase_list = st.session_state.projects[project_name]["scenarios"]
            testcase_index = next((i for i, t in enumerate(testcase_list) if t["order_no"] == idx), None)
            testcase = testcase_list[testcase_index] if testcase_index is not None else None
            
            if testcase:
                with st.form("edit_testcase_form"):
                    sentence = st.text_area("Requirement Sentence", value=testcase["veta"], height=100)
                    action = st.selectbox("Action", 
                                        options=list(st.session_state.steps_data.keys()),
                                        index=list(st.session_state.steps_data.keys()).index(testcase["akce"]) 
                                                if testcase["akce"] in st.session_state.steps_data else 0)
                    
                    # Priority and Complexity maps
                    PRIORITY_MAP_VALUES = ["1-High", "2-Medium", "3-Low"]
                    COMPLEXITY_MAP_VALUES = ["1-Giant", "2-Huge", "3-Big", "4-Medium", "5-Low"]
                    
                    priority = st.selectbox("Priority", 
                                          options=PRIORITY_MAP_VALUES,
                                          index=PRIORITY_MAP_VALUES.index(testcase["priority"]) 
                                                if testcase["priority"] in PRIORITY_MAP_VALUES else 1)
                    complexity = st.selectbox("Complexity", 
                                            options=COMPLEXITY_MAP_VALUES,
                                            index=COMPLEXITY_MAP_VALUES.index(testcase["complexity"]) 
                                                  if testcase["complexity"] in COMPLEXITY_MAP_VALUES else 3)
                    
                    if st.form_submit_button("💾 Save Changes"):
                        testcase["veta"] = sentence.strip()
                        testcase["akce"] = action
                        testcase["priority"] = priority
                        testcase["complexity"] = complexity
                        testcase["kroky"] = get_steps_from_action(action, st.session_state.steps_data)
                        
                        # Update test name while keeping structure
                        current_name_parts = testcase["test_name"].split("_")
                        if len(current_name_parts) >= 5:
                            new_test_name = f"{current_name_parts[0]}_{current_name_parts[1]}_{current_name_parts[2]}_{current_name_parts[3]}_{sentence.strip()}"
                        else:
                            segment, kanal, technologie = parse_veta(sentence.strip())
                            new_test_name = f"{current_name_parts[0]}_{kanal}_{segment}_{technologie}_{sentence.strip()}"
                        
                        testcase["test_name"] = new_test_name
                        
                        st.session_state.projects[project_name]["scenarios"][testcase_index] = testcase
                        save_projects()
                        st.success("✅ Changes saved and propagated to project.")
                        st.rerun()
        
        st.markdown("---")
        
        # DELETE TEST CASE
        st.write("**Delete Test Case:**")
        to_delete = st.selectbox(
            "Select test case to delete:",
            options=["— none —"] + [f"{row['Order']} - {row['Test Name']}" for _, row in df.iterrows()],
            index=0,
            key="delete_testcase_select"
        )
        
        if to_delete != "— none —":
            idx = int(to_delete.split(" - ")[0])
            if st.button("🗑️ Confirm Delete Test Case", type="secondary", use_container_width=True):
                testcases_filtered = [t for t in st.session_state.projects[project_name]["scenarios"] if t.get("order_no") != idx]
                for i, t in enumerate(testcases_filtered, start=1):
                    t["order_no"] = i
                st.session_state.projects[project_name]["scenarios"] = testcases_filtered
                save_projects()
                st.success("Test case deleted and order recalculated.")
                st.rerun()
    else:
        st.info("No test cases to edit or delete.")