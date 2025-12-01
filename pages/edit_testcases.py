import streamlit as st
from core import (
    load_json, save_json,
    KROKY_PATH,
    add_new_action, update_action, delete_action
)

def show():
    st.title("🔧 Edit Actions & Steps")
    st.markdown("Manage actions and their steps in `kroky.json`")
    
    # ---------- SESSION STATE ----------
    if 'steps_data' not in st.session_state:
        st.session_state.steps_data = load_json(KROKY_PATH)
    
    # Check if kroky.json exists and is loaded
    if not st.session_state.steps_data:
        st.warning("No actions found in kroky.json. The file may be empty or missing.")
        st.info("You can add your first action below.")
    
    # ---------- ADD NEW ACTION ----------
    st.subheader("➕ Add New Action")
    
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
    
    # ---------- EXISTING ACTIONS LIST ----------
    st.subheader("📝 Existing Actions")
    
    if st.session_state.steps_data:
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
                    st.session_state.delete_action = action
                    st.rerun()
            
            # Delete confirmation
            if st.session_state.get("delete_action") == action:
                st.warning(f"Are you sure you want to delete action '{action}'?")
                col_confirm, col_cancel = st.columns(2)
                with col_confirm:
                    if st.button("Yes, delete", key=f"confirm_del_{action}"):
                        success = delete_action(action)
                        if success:
                            st.success(f"✅ Action '{action}' deleted from kroky.json!")
                            st.session_state.steps_data = load_json(KROKY_PATH)
                            st.session_state.delete_action = None
                            st.rerun()
                with col_cancel:
                    if st.button("Cancel", key=f"cancel_del_{action}"):
                        st.session_state.delete_action = None
                        st.rerun()
            
            st.markdown("---")
    
    # ---------- EDIT EXISTING ACTION ----------
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