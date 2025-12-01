import streamlit as st
import pandas as pd
from core import (
    load_json, save_json,
    PROJECTS_PATH, KROKY_PATH,
    get_steps_from_action,
    add_new_action, update_action, delete_action
)

def show():
    st.title("✏️ Edit Test Cases & Manage Actions")
    
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
    
    # ---------- SIDEBAR PROJECT SELECTION ----------
    st.sidebar.title("📁 Project")
    
    project_names = list(st.session_state.projects.keys())
    selected = st.sidebar.selectbox(
        "Select Project",
        options=["— select —"] + project_names,
        index=0,
        key="project_select_edit"
    )
    
    if selected != "— select —" and selected in st.session_state.projects:
        st.session_state.selected_project = selected
    
    # ---------- EDIT SCENARIOS ----------
    if st.session_state.selected_project:
        project_name = st.session_state.selected_project
        
        st.subheader(f"📝 Edit Scenarios - {project_name}")
        
        df = make_scenarios_df(project_name)
        if not df.empty:
            # EDIT SCENARIO
            st.write("**Edit Existing Scenario:**")
            selected_row = st.selectbox(
                "Select scenario to edit:",
                options=["— none —"] + [f"{row['Order']} - {row['Test Name']}" for _, row in df.iterrows()],
                index=0
            )
            
            if selected_row != "— none —":
                idx = int(selected_row.split(" - ")[0])
                scenario_list = st.session_state.projects[project_name]["scenarios"]
                scenario_index = next((i for i, t in enumerate(scenario_list) if t["order_no"] == idx), None)
                scenario = scenario_list[scenario_index] if scenario_index is not None else None
                
                if scenario:
                    with st.form("edit_scenario_form"):
                        sentence = st.text_area("Sentence", value=scenario["veta"], height=100)
                        action = st.selectbox("Action", 
                                            options=list(st.session_state.steps_data.keys()),
                                            index=list(st.session_state.steps_data.keys()).index(scenario["akce"]) 
                                                    if scenario["akce"] in st.session_state.steps_data else 0)
                        
                        # Priority and Complexity maps (temporary)
                        PRIORITY_MAP_VALUES = ["1-High", "2-Medium", "3-Low"]
                        COMPLEXITY_MAP_VALUES = ["1-Giant", "2-Huge", "3-Big", "4-Medium", "5-Low"]
                        
                        priority = st.selectbox("Priority", 
                                              options=PRIORITY_MAP_VALUES,
                                              index=PRIORITY_MAP_VALUES.index(scenario["priority"]) 
                                                    if scenario["priority"] in PRIORITY_MAP_VALUES else 1)
                        complexity = st.selectbox("Complexity", 
                                                options=COMPLEXITY_MAP_VALUES,
                                                index=COMPLEXITY_MAP_VALUES.index(scenario["complexity"]) 
                                                      if scenario["complexity"] in COMPLEXITY_MAP_VALUES else 3)
                        
                        if st.form_submit_button("💾 Save Changes"):
                            scenario["veta"] = sentence.strip()
                            scenario["akce"] = action
                            scenario["priority"] = priority
                            scenario["complexity"] = complexity
                            scenario["kroky"] = get_steps_from_action(action, st.session_state.steps_data)
                            
                            # Keep name structure
                            current_name_parts = scenario["test_name"].split("_")
                            if len(current_name_parts) >= 5:
                                new_test_name = f"{current_name_parts[0]}_{current_name_parts[1]}_{current_name_parts[2]}_{current_name_parts[3]}_{sentence.strip()}"
                            else:
                                # Simple update if format is not standard
                                from core import extract_channel, extract_segment, extract_technology
                                segment = extract_segment(sentence.strip())
                                kanal = extract_channel(sentence.strip())
                                technologie = extract_technology(sentence.strip())
                                new_test_name = f"{current_name_parts[0]}_{kanal}_{segment}_{technologie}_{sentence.strip()}"
                            
                            scenario["test_name"] = new_test_name
                            
                            st.session_state.projects[project_name]["scenarios"][scenario_index] = scenario
                            save_projects()
                            st.success("✅ Changes saved and propagated to project.")
                            st.rerun()
            
            st.markdown("---")
            
            # DELETE SCENARIO
            st.write("**Delete Scenario:**")
            to_delete = st.selectbox(
                "Select scenario to delete:",
                options=["— none —"] + [f"{row['Order']} - {row['Test Name']}" for _, row in df.iterrows()],
                index=0,
                key="delete_selector"
            )
            
            if to_delete != "— none —":
                idx = int(to_delete.split(" - ")[0])
                if st.button("🗑️ Confirm Delete Scenario", type="secondary"):
                    scen = [t for t in st.session_state.projects[project_name]["scenarios"] if t.get("order_no") != idx]
                    for i, t in enumerate(scen, start=1):
                        t["order_no"] = i
                    st.session_state.projects[project_name]["scenarios"] = scen
                    save_projects()
                    st.success("Scenario deleted and order recalculated.")
                    st.rerun()
        else:
            st.info("No scenarios to edit.")
    
    st.markdown("---")
    
    # ---------- MANAGE ACTIONS ----------
    st.subheader("🔧 Manage Actions (kroky.json)")
    
    # Add new action button
    if st.button("➕ Add New Action", key="new_action_main", use_container_width=True):
        st.session_state["new_action"] = True
        st.session_state["edit_action"] = None
    
    # NEW ACTION FORM
    if st.session_state.get("new_action", False):
        st.subheader("➕ Add New Action")
        
        with st.form("new_action_form"):
            action_name = st.text_input("Action Name*", placeholder="e.g.: DSL_Activation", key="new_action_name")
            action_desc = st.text_input("Action Description*", placeholder="e.g.: DSL service activation", key="new_action_desc")
            
            st.markdown("---")
            st.write("**Action Steps:**")
            
            # Initialize session state for new steps
            if "new_steps" not in st.session_state:
                st.session_state.new_steps = []
            
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
                        success = add_new_action(
                            action_name.strip(),
                            action_desc.strip(),
                            st.session_state.new_steps.copy()
                        )
                        
                        if success:
                            st.success(f"✅ Action '{action_name}' added to kroky.json!")
                            st.session_state.new_action = False
                            st.session_state.new_steps = []
                            st.session_state.steps_data = load_json(KROKY_PATH)
                            st.rerun()
            
            with col_cancel:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    st.session_state.new_action = False
                    st.session_state.new_steps = []
                    st.rerun()
    
    st.markdown("---")
    
    # EXISTING ACTIONS LIST
    if st.session_state.steps_data:
        st.subheader("📝 Existing Actions")
        
        for action in sorted(st.session_state.steps_data.keys()):
            content = st.session_state.steps_data[action]
            description = content.get("description", "No description") if isinstance(content, dict) else "No description"
            steps = content.get("steps", []) if isinstance(content, dict) else content
            step_count = len(steps)
            
            col_action, col_edit, col_delete = st.columns([3, 1, 1])
            
            with col_action:
                st.write(f"**{action}**")
                st.caption(f"{description} | {step_count} steps")
            
            with col_edit:
                if st.button("✏️", key=f"edit_{action}", help="Edit action", use_container_width=True):
                    st.session_state.edit_action = action
                    st.session_state.new_action = False
                    st.rerun()
            
            with col_delete:
                if st.button("🗑️", key=f"delete_{action}", help="Delete action", use_container_width=True):
                    if st.checkbox(f"Confirm delete '{action}'?", key=f"confirm_{action}"):
                        success = delete_action(action)
                        if success:
                            st.success(f"✅ Action '{action}' deleted from kroky.json!")
                            st.session_state.steps_data = load_json(KROKY_PATH)
                            st.rerun()
            
            st.markdown("---")
    
    # EDIT EXISTING ACTION
    if "edit_action" in st.session_state and st.session_state.edit_action:
        action = st.session_state.edit_action
        content = st.session_state.steps_data.get(action, {})
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
                        st.session_state[f"edit_steps_{action}"].pop(i)
                        st.rerun()
                
                st.markdown("---")
            
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
                        success = update_action(
                            action,
                            new_desc.strip(),
                            st.session_state[f"edit_steps_{action}"].copy()
                        )
                        
                        if success:
                            st.success(f"✅ Action '{action}' updated in kroky.json!")
                            st.session_state.edit_action = None
                            if f"edit_steps_{action}" in st.session_state:
                                del st.session_state[f"edit_steps_{action}"]
                            st.session_state.steps_data = load_json(KROKY_PATH)
                            st.rerun()
            
            with col_cancel:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    st.session_state.edit_action = None
                    if f"edit_steps_{action}" in st.session_state:
                        del st.session_state[f"edit_steps_{action}"]
                    st.rerun()