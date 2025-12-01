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
    add_new_action, update_action, delete_action
)

# ---------- CONFIGURATION ----------
st.set_page_config(
    page_title="TestCase Builder",
    layout="wide",
    page_icon="🧪"
)

# Custom CSS for dark theme
CUSTOM_CSS = """
<style>
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
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------- SESSION STATE ----------
if 'projects' not in st.session_state:
    st.session_state.projects = load_json(PROJECTS_PATH)
if 'selected_project' not in st.session_state:
    st.session_state.selected_project = None
if 'steps_data' not in st.session_state:
    st.session_state.steps_data = load_json(KROKY_PATH)

# ---------- HELPER FUNCTIONS ----------
def save_projects():
    """Save projects to JSON"""
    return save_json(PROJECTS_PATH, st.session_state.projects)

def make_scenarios_df(project_name):
    """Create DataFrame of scenarios for display"""
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
    """Renumber scenarios starting from 001"""
    if project_name not in st.session_state.projects:
        return
    
    scenarios = st.session_state.projects[project_name]["scenarios"]
    
    for i, tc in enumerate(sorted(scenarios, key=lambda x: x["order_no"]), start=1):
        new_number = f"{i:03d}"
        tc["order_no"] = i
        
        # Update test name with new number
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

# ---------- ACTION MANAGEMENT PAGE ----------
def manage_actions():
    """Page for managing actions and steps"""
    st.title("🔧 Action Management")
    
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
                        # Update step in session state
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

# ---------- MAIN APPLICATION ----------
def main():
    # SIDEBAR
    st.sidebar.title("📁 Project")
    
    # Project selection
    project_names = list(st.session_state.projects.keys())
    selected = st.sidebar.selectbox(
        "Select Project",
        options=["— select —"] + project_names,
        index=0,
        key="project_select"
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
    
    # MAIN CONTENT
    st.title("🧪 TestCase Builder")
    
    if st.session_state.selected_project is None:
        st.info("Select or create a project in the left panel.")
        return
    
    project_name = st.session_state.selected_project
    
    # Project overview
    st.subheader("📊 Project Overview")
    st.write(f"**Active Project:** {project_name}")
    subject = st.session_state.projects[project_name].get('subject', 'UAT2\\Antosova\\')
    st.write(f"**Subject:** {subject}")
    st.write(f"**Number of Scenarios:** {len(st.session_state.projects[project_name].get('scenarios', []))}")
    
    st.markdown("---")
    
    # TABS
    tab1, tab2, tab3 = st.tabs(["➕ Add Scenarios", "🔧 Manage Actions", "📤 Export"])
    
    with tab1:
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
    
    with tab2:
        manage_actions()
    
    with tab3:
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

# ---------- RUN APPLICATION ----------
if __name__ == "__main__":
    main()