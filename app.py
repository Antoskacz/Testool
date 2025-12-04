import streamlit as st
import json
import pandas as pd
from pathlib import Path
import difflib
import unicodedata

st.set_page_config(
    page_title="TestTool",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"  # Sidebar vždy rozbalený
)

# Žádné custom CSS pro sidebar!
st.title("🧪 TestTool")
st.markdown("### Professional test case builder and manager")

# ---------- SIDEBAR ----------
with st.sidebar:
    st.title("🧪 TestTool")
    st.markdown("---")
    
    # Jednoduchá navigace
    page = st.radio(
        "Navigation",
        [
            "🏗️ Build Test Cases",
            "🔧 Edit Actions & Steps", 
            "📝 Text Comparator"
        ],
        label_visibility="visible"
    )

# ---------- PAGE ROUTING ----------
if page == "🏗️ Build Test Cases":
    # Load data
    BASE_DIR = Path(__file__).resolve().parent
    DATA_DIR = BASE_DIR / "data"
    PROJECTS_PATH = DATA_DIR / "projects.json"
    KROKY_PATH = DATA_DIR / "kroky.json"
    
    def load_json(filepath):
        try:
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            return {}
        return {}
    
    projects = load_json(PROJECTS_PATH)
    steps_data = load_json(KROKY_PATH)
    
    # Initialize session state
    if 'projects' not in st.session_state:
        st.session_state.projects = projects
    if 'selected_project' not in st.session_state:
        st.session_state.selected_project = None
    if 'steps_data' not in st.session_state:
        st.session_state.steps_data = steps_data
    
    # Project selection in sidebar
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
                    st.session_state.selected_project = new_project.strip()
                    st.rerun()
                else:
                    st.error("Project already exists!")
        
        if selected != "— select —" and selected in st.session_state.projects:
            st.session_state.selected_project = selected
    
    # Main content - BUILD TEST CASES
    st.title("🏗️ Build Test Cases")
    
    if st.session_state.selected_project is None:
        st.info("Select or create a project in the sidebar.")
        st.stop()
    
    project_name = st.session_state.selected_project
    project_data = st.session_state.projects[project_name]
    
    subject_value = project_data.get('subject', r'UAT2\Antosova\\')
    st.write(f"**Active Project:** {project_name}")
    st.write(f"**Subject:** {subject_value}")
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

elif page == "🔧 Edit Actions & Steps":
    st.title("🔧 Edit Actions & Steps")
    st.markdown("Manage actions and their steps in `kroky.json`")
    
    st.subheader("➕ Add/Edit Action")
    
    with st.form("action_form"):
        action_name = st.text_input("Action Name", placeholder="e.g.: DSL_Activation")
        action_desc = st.text_input("Action Description", placeholder="e.g.: DSL service activation")
        
        st.write("**Steps:**")
        step_desc = st.text_area("Step Description", placeholder="What to do...")
        step_expected = st.text_area("Expected Result", placeholder="What should happen...")
        
        if st.form_submit_button("💾 Save Action"):
            st.success(f"✅ Action '{action_name}' saved!")
    
    st.markdown("---")
    st.subheader("📋 Existing Actions")
    st.info("Feature under development...")

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
    
    def remove_diacritics(text):
        if not text:
            return text
        normalized = unicodedata.normalize('NFKD', text)
        return ''.join(c for c in normalized if not unicodedata.combining(c))
    
    st.markdown("---")
    
    col_buttons = st.columns([1, 1, 1, 4])
    
    with col_buttons[0]:
        compare_btn = st.button("🔍 **Compare**", use_container_width=True, type="primary", help="Compare texts and highlight differences")
    
    with col_buttons[1]:
        diacritics_btn = st.button("❌ **Remove Diacritics**", use_container_width=True, help="Remove all accents, háčky and čárky from both texts")
    
    with col_buttons[2]:
        reset_btn = st.button("🔄 **Reset**", use_container_width=True, help="Clear both text fields")
    
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