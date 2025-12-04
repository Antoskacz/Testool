import streamlit as st
import json
import pandas as pd
from pathlib import Path
import copy
import difflib

st.set_page_config(
    page_title="TestTool - Test Case Management",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme
CUSTOM_CSS = """
<style>
/* Hide the top navigation bar that Streamlit creates for multi-page apps */
[data-testid="stSidebarNav"] {
    display: none;
}

/* Hide any other top navigation elements */
header[data-testid="stHeader"] {
    display: none;
}

[data-testid="stToolbar"] {
    display: none;
}

.css-1d391kg {
    display: none;
}

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

/* Style for diff output */
.diff { border-collapse: collapse; width: 100%; }
.diff_add { background-color: #d4edda; color: #155724; }
.diff_sub { background-color: #f8d7da; color: #721c24; }
.diff_chg { background-color: #fff3cd; color: #856404; }
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ---------- PATHS ----------
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
EXPORTS_DIR = BASE_DIR / "exports"

KROKY_PATH = DATA_DIR / "kroky.json"
PROJECTS_PATH = DATA_DIR / "projects.json"

# Create directories if they don't exist
DATA_DIR.mkdir(exist_ok=True)
EXPORTS_DIR.mkdir(exist_ok=True)

# ---------- HELPER FUNCTIONS ----------
def load_json(filepath):
    """Safe JSON loading"""
    try:
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading {filepath}: {e}")
    return {}

def save_json(filepath, data):
    """Safe JSON saving"""
    try:
        filepath.parent.mkdir(exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving {filepath}: {e}")
        return False

# ---------- PAGE 1: BUILD TEST CASES ----------
def build_test_cases_page():
    st.title("🏗️ Build Test Cases")
    
    # Load data
    projects = load_json(PROJECTS_PATH)
    steps_data = load_json(KROKY_PATH)
    
    # Initialize session state
    if 'projects' not in st.session_state:
        st.session_state.projects = projects
    if 'selected_project' not in st.session_state:
        st.session_state.selected_project = None
    if 'steps_data' not in st.session_state:
        st.session_state.steps_data = steps_data
    
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
                save_json(PROJECTS_PATH, st.session_state.projects)
                st.session_state.selected_project = new_project.strip()
                st.rerun()
            else:
                st.sidebar.error("Project already exists!")
    
    # Project management
    if selected != "— select —" and selected in st.session_state.projects:
        st.session_state.selected_project = selected
    
    # ---------- MAIN CONTENT ----------
    if st.session_state.selected_project is None:
        st.info("Select or create a project in the left panel.")
        return
    
    project_name = st.session_state.selected_project
    project_data = st.session_state.projects[project_name]
    
    # Project info
    st.write(f"**Active Project:** {project_name}")
    st.write(f"**Subject:** {project_data.get('subject', 'UAT2\\Antosova\\')}")
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
                # Simple test case generation
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
                save_json(PROJECTS_PATH, st.session_state.projects)
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

# ---------- PAGE 2: EDIT ACTIONS & STEPS ----------
def edit_actions_page():
    st.title("🔧 Edit Actions & Steps")
    st.markdown("Manage actions and their steps in `kroky.json`")
    
    # Load data
    steps_data = load_json(KROKY_PATH)
    
    # Initialize session state
    if 'steps_data' not in st.session_state:
        st.session_state.steps_data = steps_data
    
    # Add new action
    st.subheader("➕ Add New Action")
    
    with st.expander("Click to add new action"):
        with st.form("new_action_form"):
            action_name = st.text_input("Action Name*", placeholder="e.g.: DSL_Activation")
            action_desc = st.text_input("Action Description*", placeholder="e.g.: DSL service activation")
            
            st.write("**Add Steps:**")
            step_desc = st.text_area("Step Description", placeholder="What to do...")
            step_exp = st.text_area("Expected Result", placeholder="What should happen...")
            
            if st.form_submit_button("💾 Save Action"):
                if action_name.strip() and action_desc.strip():
                    new_action = {
                        action_name.strip(): {
                            "description": action_desc.strip(),
                            "steps": [
                                {
                                    "description": step_desc.strip() if step_desc.strip() else "Step description",
                                    "expected": step_exp.strip() if step_exp.strip() else "Expected result"
                                }
                            ]
                        }
                    }
                    
                    # Update data
                    st.session_state.steps_data.update(new_action)
                    save_json(KROKY_PATH, st.session_state.steps_data)
                    st.success(f"✅ Action '{action_name}' added!")
                    st.rerun()
                else:
                    st.error("Please fill in all required fields.")
    
    st.markdown("---")
    
    # List existing actions
    st.subheader("📝 Existing Actions")
    
    if st.session_state.steps_data:
        for action_name, action_data in st.session_state.steps_data.items():
            with st.expander(f"**{action_name}** - {action_data.get('description', 'No description')}"):
                st.write(f"**Description:** {action_data.get('description', 'No description')}")
                
                if "steps" in action_data and action_data["steps"]:
                    st.write("**Steps:**")
                    for i, step in enumerate(action_data["steps"], 1):
                        st.write(f"{i}. **Do:** {step.get('description', '')}")
                        st.write(f"   **Expect:** {step.get('expected', '')}")
                
                # Delete button
                if st.button(f"Delete {action_name}", key=f"del_{action_name}"):
                    if action_name in st.session_state.steps_data:
                        del st.session_state.steps_data[action_name]
                        save_json(KROKY_PATH, st.session_state.steps_data)
                        st.success(f"✅ Action '{action_name}' deleted!")
                        st.rerun()
    else:
        st.info("No actions yet. Add your first action above.")


# ---------- PAGE 3: TEXT COMPARATOR ----------
def text_comparator_page():
    st.title("📝 Text Comparator")
    st.markdown("Compare two texts with highlighted differences")
    
    # Initialize session state for text inputs
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
    
    # Text transformation functions
    def remove_diacritics(text):
        """Remove diacritics from text"""
        import unicodedata
        if not text:
            return text
        
        # Normalize and remove diacritics
        normalized = unicodedata.normalize('NFKD', text)
        return ''.join(c for c in normalized if not unicodedata.combining(c))
    
    # Text manipulation buttons
    st.markdown("---")
    
    # Create buttons in a row
    col_buttons = st.columns([1, 1, 1, 4])  # 3 buttons + spacer
    
    with col_buttons[0]:
        compare_btn = st.button("🔍 **Compare**", use_container_width=True, type="primary", help="Compare texts and highlight differences")
    
    with col_buttons[1]:
        diacritics_btn = st.button("❌ **Remove Diacritics**", use_container_width=True, help="Remove all accents, háčky and čárky from both texts")
    
    with col_buttons[2]:
        reset_btn = st.button("🔄 **Reset**", use_container_width=True, help="Clear both text fields")
    
    # Button actions
    if diacritics_btn:
        if text1 or text2:
            text1_no_diac = remove_diacritics(text1)
            text2_no_diac = remove_diacritics(text2)
            
            # Store in session state to preserve in text areas
            st.session_state.text1_input = text1_no_diac
            st.session_state.text2_input = text2_no_diac
            
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
            # ========== IMPROVED COMPARISON LOGIC ==========
            st.subheader("📊 Character Comparison")
            
            # Show basic statistics
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("Length Text 1", len(text1))
            with col_stat2:
                st.metric("Length Text 2", len(text2))
            with col_stat3:
                diff_len = abs(len(text1) - len(text2))
                st.metric("Length Difference", diff_len)
            
            # ========== SMART CHARACTER COMPARISON ==========
            st.markdown("---")
            st.subheader("🔍 Character-by-Character Differences")
            
            # Create HTML for highlighted text
            def highlight_differences(text1, text2):
                """Smart comparison that only highlights actually different characters"""
                result = ""
                i, j = 0, 0
                
                while i < len(text1) and j < len(text2):
                    if text1[i] == text2[j]:
                        # Characters match
                        result += text1[i]
                        i += 1
                        j += 1
                    else:
                        # Characters don't match - highlight
                        result += f"<span style='background-color: #ff4444; color: white; font-weight: bold;'>{text1[i] if text1[i] != ' ' else '␣'}</span>"
                        i += 1
                        j += 1
                
                # Handle remaining characters in text1
                while i < len(text1):
                    result += f"<span style='background-color: #ff4444; color: white; font-weight: bold;'>{text1[i] if text1[i] != ' ' else '␣'}</span>"
                    i += 1
                
                return result
            
            # Get highlighted versions
            highlighted1 = highlight_differences(text1, text2)
            highlighted2 = highlight_differences(text2, text1)  # Compare in reverse
            
            # Display side by side
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
            
            # ========== LINE-BY-LINE COMPARISON ==========
            st.markdown("---")
            st.subheader("📝 Line-by-Line Comparison")
            
            lines1 = text1.splitlines()
            lines2 = text2.splitlines()
            
            diff_found = False
            
            for i in range(max(len(lines1), len(lines2))):
                line1 = lines1[i] if i < len(lines1) else ""
                line2 = lines2[i] if i < len(lines2) else ""
                
                if line1 != line2:
                    diff_found = True
                    st.markdown(f"**Line {i+1}:**")
                    
                    col_line1, col_line2 = st.columns(2)
                    
                    with col_line1:
                        # Highlight differences in this line
                        line_diff1 = highlight_differences(line1, line2)
                        st.markdown(
                            f"""<div style='
                                background-color: #2a2a2a; 
                                padding: 10px; 
                                border-radius: 5px; 
                                font-family: "Courier New", monospace;
                                margin-bottom: 5px;
                            '>{line_diff1}</div>""", 
                            unsafe_allow_html=True
                        )
                    
                    with col_line2:
                        line_diff2 = highlight_differences(line2, line1)
                        st.markdown(
                            f"""<div style='
                                background-color: #2a2a2a; 
                                padding: 10px; 
                                border-radius: 5px; 
                                font-family: "Courier New", monospace;
                                margin-bottom: 5px;
                            '>{line_diff2}</div>""", 
                            unsafe_allow_html=True
                        )
            
            if not diff_found:
                st.success("✅ No differences found in line-by-line comparison!")
            
            # ========== SIMILARITY CALCULATION ==========
            st.markdown("---")
            
            # Calculate similarity based on character matches
            matches = 0
            total = min(len(text1), len(text2))
            
            for i in range(total):
                if text1[i] == text2[i]:
                    matches += 1
            
            if total > 0:
                similarity = (matches / total) * 100
            else:
                similarity = 0
            
            # Create a similarity gauge
            st.subheader("📈 Similarity Analysis")
            
            col_sim1, col_sim2, col_sim3 = st.columns([2, 1, 1])
            
            with col_sim1:
                # Progress bar for similarity
                st.progress(similarity/100, text=f"Similarity: {similarity:.1f}%")
            
            with col_sim2:
                st.metric("Matching Chars", matches)
            
            with col_sim3:
                st.metric("Total Compared", total)
            
            # Summary
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
    
    # Quick help
    with st.expander("ℹ️ How to use"):
        st.markdown("""
        **Buttons:**
        
        🔍 **Compare** - Compare texts and highlight differences in red
        ❌ **Remove Diacritics** - Strip all accents, háčky and čárky from both texts
        🔄 **Reset** - Clear both text fields completely
        
        **Features:**
        - Smart character-by-character comparison
        - Only actually different characters are highlighted in red
        - Spaces shown as `␣` when they are different
        - Line-by-line comparison for multi-line texts
        - Similarity percentage with visual gauge
        - Statistics: character counts and matches
        
        **Tip:** For best results, ensure texts are properly aligned before comparing.
        """)

# ---------- MAIN APP ----------
# Title
st.title("🧪 TestTool")
st.markdown("### Professional test case builder and manager")

# Navigation in sidebar ONLY - without any header text
page = st.sidebar.radio(
    " ",
    [
        "🏗️ Build Test Cases",
        "🔧 Edit Actions & Steps", 
        "📝 Text Comparator"
    ]
)

# Page routing
if page == "🏗️ Build Test Cases":
    build_test_cases_page()
elif page == "🔧 Edit Actions & Steps":
    edit_actions_page()
elif page == "📝 Text Comparator":
    text_comparator_page()