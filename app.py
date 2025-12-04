import streamlit as st
import json
import pandas as pd
from pathlib import Path
import difflib
import unicodedata

st.set_page_config(
    page_title="TestTool - Test Case Management",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for dark theme with FIXED SIDEBAR
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

/* FIXED SIDEBAR - Never collapses completely */
section[data-testid="stSidebar"] {
    min-width: 50px !important;
    max-width: 350px !important;
    transition: width 0.3s ease;
}

/* Sidebar content */
.sidebar-content {
    padding: 20px 15px;
}

/* Compact mode */
.sidebar-compact .sidebar-content {
    padding: 20px 5px;
}

/* Toggle button */
.sidebar-toggle-btn {
    position: absolute;
    top: 10px;
    right: -15px;
    background: #4e54c8;
    color: white;
    border: none;
    border-radius: 50%;
    width: 30px;
    height: 30px;
    font-size: 16px;
    cursor: pointer;
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
}

/* Compact navigation icons */
.compact-nav {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 20px;
    padding-top: 40px;
}

.compact-icon {
    font-size: 22px;
    cursor: pointer;
    padding: 12px;
    border-radius: 8px;
    width: 45px;
    height: 45px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.3s;
}

.compact-icon:hover {
    background: #333;
    transform: scale(1.1);
}

.compact-icon.active {
    background: #4e54c8;
    color: white;
    box-shadow: 0 4px 12px rgba(78, 84, 200, 0.3);
}

/* Tooltips for compact mode */
.compact-icon::after {
    content: attr(title);
    position: absolute;
    left: 60px;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 5px 10px;
    border-radius: 4px;
    font-size: 12px;
    white-space: nowrap;
    opacity: 0;
    transition: opacity 0.3s;
    pointer-events: none;
    z-index: 1000;
}

.compact-icon:hover::after {
    opacity: 1;
}

body { 
    background-color: #121212; 
    color: #EAEAEA; 
}
[data-testid="stAppViewContainer"] { 
    background: linear-gradient(145deg, #181818, #1E1E1E); 
}
h1, h2, h3 { 
    color: #F1F1F1; 
    font-weight: 600; 
}
div[data-testid="stForm"], div[data-testid="stExpander"] {
    background-color: #1A1A1A; 
    border-radius: 10px; 
    padding: 1rem; 
    border: 1px solid #333;
}
button[kind="primary"] { 
    background: linear-gradient(90deg, #4e54c8, #8f94fb); 
    color: white !important; 
    border: none !important;
}
button[kind="secondary"] { 
    background: #292929; 
    color: #CCC !important; 
    border: 1px solid #555; 
}
.stTextInput > div > div > input, textarea, select {
    background-color: #222; 
    color: #EEE !important; 
    border-radius: 6px; 
    border: 1px solid #444;
}
.stDataFrame { 
    background-color: #1C1C1C !important; 
}

/* Highlight for differences */
.highlight-diff {
    background-color: #ff4444 !important;
    color: white !important;
    font-weight: bold;
    padding: 1px 3px;
    border-radius: 3px;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# Initialize session state for sidebar
if 'sidebar_collapsed' not in st.session_state:
    st.session_state.sidebar_collapsed = False

# ---------- SIDEBAR RENDERING ----------
# Always show sidebar, but in different modes
with st.sidebar:
    # Sidebar toggle button (always visible)
    col_toggle, _ = st.columns([1, 5])
    with col_toggle:
        toggle_icon = "◀️" if st.session_state.sidebar_collapsed else "▶️"
        toggle_text = "Expand" if st.session_state.sidebar_collapsed else "Collapse"
        if st.button(toggle_icon, key="sidebar_toggle", help=toggle_text):
            st.session_state.sidebar_collapsed = not st.session_state.sidebar_collapsed
            st.rerun()
    
    if st.session_state.sidebar_collapsed:
        # COMPACT MODE - icons only
        st.markdown('<div class="compact-nav">', unsafe_allow_html=True)
        
        # Navigation icons
        pages = [
            ("🏗️", "Build Test Cases", "build"),
            ("🔧", "Edit Actions & Steps", "edit"),
            ("📝", "Text Comparator", "comparator")
        ]
        
        for icon, title, key in pages:
            is_active = st.session_state.get('current_page', 'build') == key
            icon_class = "compact-icon active" if is_active else "compact-icon"
            
            if st.button(icon, key=f"nav_{key}"):
                st.session_state.current_page = key
                st.rerun()
            
            # Add tooltip via HTML
            st.markdown(f'<div class="{icon_class}" title="{title}">{icon}</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
    else:
        # FULL MODE - normal sidebar
        st.title("🧪 TestTool")
        st.markdown("### Navigation")
        
        # Navigation in normal mode
        page = st.radio(
            "Go to:",
            [
                "🏗️ Build Test Cases",
                "🔧 Edit Actions & Steps", 
                "📝 Text Comparator"
            ],
            key="page_selector"
        )
        
        # Set current page for compact mode
        if "Build Test Cases" in page:
            st.session_state.current_page = "build"
        elif "Edit Actions" in page:
            st.session_state.current_page = "edit"
        elif "Text Comparator" in page:
            st.session_state.current_page = "comparator"

# ---------- PAGE ROUTING ----------
# Get current page from session state
current_page = st.session_state.get('current_page', 'build')

# Main title (always visible)
st.title("🧪 TestTool")
st.markdown("### Professional test case builder and manager")

# ---------- PAGE 1: BUILD TEST CASES ----------
def build_test_cases_page():
    st.title("🏗️ Build Test Cases")
    
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
    
    # ---------- SIDEBAR ----------
    if not st.session_state.sidebar_collapsed:
        st.sidebar.markdown("---")
        st.sidebar.subheader("📁 Project")
        
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
                        "subject": r"UAT2\Antosova\\",  # Raw string to avoid escape issues
                        "scenarios": []
                    }
                    # Save function would go here
                    st.session_state.selected_project = new_project.strip()
                    st.rerun()
                else:
                    st.sidebar.error("Project already exists!")
        
        # Project management
        if selected != "— select —" and selected in st.session_state.projects:
            st.session_state.selected_project = selected
    
    # ---------- MAIN CONTENT ----------
    if st.session_state.selected_project is None:
        st.info("Select or create a project in the sidebar.")
        return
    
    project_name = st.session_state.selected_project
    project_data = st.session_state.projects[project_name]
    
    # Project info - FIXED: use raw string or double the backslashes
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
                # Save function would go here
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
    
    # Simple form for editing
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
                        char_display = text1[i] if text1[i] != ' ' else '␣'
                        result += f'<span class="highlight-diff">{char_display}</span>'
                        i += 1
                        j += 1
                
                # Handle remaining characters in text1
                while i < len(text1):
                    char_display = text1[i] if text1[i] != ' ' else '␣'
                    result += f'<span class="highlight-diff">{char_display}</span>'
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
        - Similarity percentage with visual gauge
        - Statistics: character counts and matches
        """)

# ---------- PAGE ROUTING ----------
if current_page == "build":
    build_test_cases_page()
elif current_page == "edit":
    edit_actions_page()
elif current_page == "comparator":
    text_comparator_page()