import streamlit as st
import json
import pandas as pd
from pathlib import Path
import difflib
import unicodedata
import copy

st.set_page_config(
    page_title="Tesool Pro",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/your-repo',
        'Report a bug': "https://github.com/your-repo/issues",
        'About': "# Testool Pro\n### Professional test case management"
    }
)

# ---------- MODERNÍ CSS ----------
MODERN_CSS = """
<style>
/* Modern gradient background */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%);
}

/* Glass morphism sidebar */
[data-testid="stSidebar"] {
    background: rgba(25, 25, 35, 0.9) !important;
    backdrop-filter: blur(10px);
    border-right: 1px solid rgba(255, 255, 255, 0.1);
}

/* Modern cards with glass effect */
.custom-card {
    background: rgba(30, 30, 40, 0.7);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    padding: 25px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    transition: all 0.3s ease;
    margin-bottom: 20px;
}

.custom-card:hover {
    transform: translateY(-5px);
    box-shadow: 0 12px 40px rgba(0, 0, 0, 0.4);
    border: 1px solid rgba(100, 100, 255, 0.3);
}

/* Gradient headers */
.gradient-text {
    background: linear-gradient(90deg, #ff6b6b, #feca57, #48dbfb, #ff9ff3);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 800;
}

/* Modern buttons */
.stButton > button {
    border-radius: 12px !important;
    border: none !important;
    transition: all 0.3s ease !important;
    font-weight: 600 !important;
}

.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.2) !important;
}

/* Primary button gradient */
div[data-testid="stFormSubmitButton"] > button,
button[kind="primary"] {
    background: linear-gradient(90deg, #6a11cb 0%, #2575fc 100%) !important;
}

/* Secondary button */
button[kind="secondary"] {
    background: rgba(255, 255, 255, 0.1) !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
}

/* Form inputs */
.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div > select {
    background: rgba(255, 255, 255, 0.05) !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 12px !important;
    color: white !important;
    transition: all 0.3s ease !important;
}

.stTextInput > div > div > input:focus,
.stTextArea > div > div > textarea:focus {
    border-color: #6a11cb !important;
    box-shadow: 0 0 0 2px rgba(106, 17, 203, 0.2) !important;
}

/* Dataframe styling */
.stDataFrame {
    border-radius: 15px !important;
    overflow: hidden !important;
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
}

/* Metric cards */
[data-testid="stMetricValue"] {
    font-size: 2rem !important;
    font-weight: 700 !important;
}

/* Progress bar */
.stProgress > div > div > div {
    background: linear-gradient(90deg, #6a11cb, #2575fc) !important;
}

/* Tab styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 2px;
}

.stTabs [data-baseweb="tab"] {
    border-radius: 10px 10px 0 0 !important;
    padding: 10px 20px !important;
}

/* Radio buttons */
.stRadio > div {
    flex-direction: column;
    gap: 10px;
}

.stRadio > div > label {
    background: rgba(255, 255, 255, 0.05);
    padding: 12px 20px;
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    transition: all 0.3s ease;
}

.stRadio > div > label:hover {
    background: rgba(255, 255, 255, 0.1);
    border-color: rgba(100, 100, 255, 0.3);
}

.stRadio > div > label[data-checked="true"] {
    background: linear-gradient(90deg, rgba(106, 17, 203, 0.3), rgba(37, 117, 252, 0.3)) !important;
    border-color: #6a11cb !important;
}

/* Expanders */
[data-testid="stExpander"] {
    border: 1px solid rgba(255, 255, 255, 0.1) !important;
    border-radius: 15px !important;
}

/* Success/Error messages */
.stAlert {
    border-radius: 12px !important;
    border: none !important;
}

/* Custom scrollbar */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: rgba(255, 255, 255, 0.05);
    border-radius: 10px;
}

::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, #6a11cb, #2575fc);
    border-radius: 10px;
}

::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, #2575fc, #6a11cb);
}
</style>
"""

st.markdown(MODERN_CSS, unsafe_allow_html=True)

# ---------- POMOCNÉ FUNKCE ----------
def load_json(filepath):
    try:
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        st.error(f"Error loading {filepath}: {e}")
    return {}

def save_json(filepath, data):
    try:
        filepath.parent.mkdir(exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        st.error(f"Error saving {filepath}: {e}")
        return False

def extract_channel(text: str) -> str:
    t = text.lower()
    if "shop" in t:
        return "SHOP"
    if "il" in t:
        return "IL"
    return "UNKNOWN"

def extract_segment(text: str) -> str:
    t = text.lower()
    if "b2c" in t:
        return "B2C"
    if "b2b" in t:
        return "B2B"
    return "UNKNOWN"

def extract_technology(text: str) -> str:
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
    segment_data = {"B2C": {}, "B2B": {}}
    
    for scenario in scenarios:
        segment = scenario.get("segment", "UNKNOWN")
        channel = scenario.get("kanal", "UNKNOWN")
        test_name = scenario.get("test_name", "")
        action = scenario.get("akce", "UNKNOWN")
        
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
    if not text:
        return text
    normalized = unicodedata.normalize('NFKD', text)
    return ''.join(c for c in normalized if not unicodedata.combining(c))

# ---------- CUSTOM COMPONENTS ----------
def metric_card(title, value, icon="📊", change=None):
    """Modern metric card component"""
    col1, col2 = st.columns([1, 3])
    with col1:
        st.markdown(f"<h1 style='font-size: 2.5rem; margin: 0;'>{icon}</h1>", unsafe_allow_html=True)
    with col2:
        st.markdown(f"<h3 style='margin: 0; color: #aaa;'>{title}</h3>", unsafe_allow_html=True)
        st.markdown(f"<h1 style='margin: 0; font-size: 2rem;'>{value}</h1>", unsafe_allow_html=True)
        if change:
            color = "🟢" if change >= 0 else "🔴"
            st.markdown(f"<p style='margin: 0; color: {'#4CAF50' if change >= 0 else '#F44336'};'>{color} {abs(change)}%</p>", unsafe_allow_html=True)

def feature_card(title, description, icon="✨"):
    """Feature highlight card"""
    with st.container():
        st.markdown(f"""
        <div class='custom-card'>
            <div style='display: flex; align-items: center; gap: 15px; margin-bottom: 15px;'>
                <h2 style='font-size: 2rem; margin: 0;'>{icon}</h2>
                <h3 style='margin: 0;'>{title}</h3>
            </div>
            <p style='color: #ccc; line-height: 1.6;'>{description}</p>
        </div>
        """, unsafe_allow_html=True)

# ---------- SIDEBAR ----------
with st.sidebar:
    st.markdown("""
    <div style='text-align: center; padding: 20px 0;'>
        <h1 style='font-size: 2.5rem; margin: 0;'>⚡</h1>
        <h2 class='gradient-text' style='margin: 10px 0;'>Testool Pro</h2>
        <p style='color: #aaa; margin: 0;'>Professional test case management</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Navigation with icons
    page_options = {
        "🏗️ Build Test Cases": "build",
        "🔧 Edit Actions & Steps": "edit", 
        "📝 Text Comparator": "comparator"
    }
    
    selected_option = st.radio(
        "Navigation",
        list(page_options.keys()),
        label_visibility="collapsed"
    )
    
    page = page_options[selected_option]
    
    st.markdown("---")
    
    # Quick stats in sidebar
    if page == "build":
        st.markdown("### 📈 Quick Stats")
        st.metric("Active Projects", "3", "+1")
        st.metric("Total Test Cases", "42", "12%")
        st.metric("Automation Rate", "75%", "5%")

# ---------- HEADER ----------
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    st.markdown("<h1 class='gradient-text'>Testool Pro</h1>", unsafe_allow_html=True)
    st.markdown("<p style='font-size: 1.2rem; color: #aaa;'>Streamline your test case management workflow</p>", unsafe_allow_html=True)

with col2:
    st.markdown("""
    <div style='text-align: center;'>
        <div style='font-size: 2rem;'>🚀</div>
        <div style='font-size: 0.9rem; color: #aaa;'>v2.0</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown("""
    <div style='text-align: center;'>
        <div style='font-size: 2rem;'>⚡</div>
        <div style='font-size: 0.9rem; color: #4CAF50;'>Online</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# ---------- PAGE CONTENT ----------
if page == "build":
    # Load data
    BASE_DIR = Path(__file__).resolve().parent
    DATA_DIR = BASE_DIR / "data"
    PROJECTS_PATH = DATA_DIR / "projects.json"
    KROKY_PATH = DATA_DIR / "kroky.json"
    
    projects = load_json(PROJECTS_PATH)
    steps_data = load_json(KROKY_PATH)
    
    if 'projects' not in st.session_state:
        st.session_state.projects = projects
    if 'selected_project' not in st.session_state:
        st.session_state.selected_project = None
    if 'steps_data' not in st.session_state:
        st.session_state.steps_data = steps_data
    
    # Project selection in sidebar
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📁 Project Management")
        
        project_names = list(st.session_state.projects.keys())
        selected = st.selectbox(
            "Select Project",
            options=["— select —"] + project_names,
            index=0,
            key="project_select"
        )
        
        new_project = st.text_input("New Project Name", placeholder="e.g.: CCCTR-XXXX – Name")
        
        if st.button("🚀 Create Project", use_container_width=True, type="primary"):
            if new_project.strip():
                if new_project.strip() not in st.session_state.projects:
                    st.session_state.projects[new_project.strip()] = {
                        "next_id": 1,
                        "subject": r"UAT2\Antosova\\",
                        "scenarios": []
                    }
                    save_json(PROJECTS_PATH, st.session_state.projects)
                    st.session_state.selected_project = new_project.strip()
                    st.rerun()
                else:
                    st.error("Project already exists!")
        
        if selected != "— select —" and selected in st.session_state.projects:
            st.session_state.selected_project = selected
    
    # Main content
    if st.session_state.selected_project is None:
        feature_card(
            "Welcome to Testool Pro", 
            "Select or create a project to start managing your test cases. Build, edit, and compare with our powerful tools.",
            icon="🚀"
        )
        
        col1, col2, col3 = st.columns(3)
        with col1:
            feature_card("Build", "Create structured test cases from requirements", "🏗️")
        with col2:
            feature_card("Edit", "Manage actions and steps efficiently", "🔧")
        with col3:
            feature_card("Compare", "Advanced text comparison tools", "📝")
        
        st.stop()
    
    project_name = st.session_state.selected_project
    project_data = st.session_state.projects[project_name]
    
    # Project header with metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        metric_card("Project", project_name, "📁")
    with col2:
        metric_card("Test Cases", len(project_data.get('scenarios', [])), "📋")
    with col3:
        b2c_count = sum(1 for tc in project_data.get("scenarios", []) if tc.get("segment") == "B2C")
        metric_card("B2C", b2c_count, "👥")
    with col4:
        b2b_count = sum(1 for tc in project_data.get("scenarios", []) if tc.get("segment") == "B2B")
        metric_card("B2B", b2b_count, "🏢")
    
    # Analysis cards
    st.markdown("### 📊 Analysis")
    testcases = project_data.get("scenarios", [])
    
    if testcases:
        segment_data = analyze_scenarios(testcases)
        
        tab1, tab2 = st.tabs(["👥 B2C Analysis", "🏢 B2B Analysis"])
        
        with tab1:
            if "B2C" in segment_data and segment_data["B2C"]:
                for channel in segment_data["B2C"]:
                    with st.expander(f"**{channel}** Channel", expanded=True):
                        cols = st.columns(3)
                        for idx, (technology, actions) in enumerate(segment_data["B2C"][channel].items()):
                            with cols[idx % 3]:
                                st.metric(technology, f"{len(actions)} actions")
            else:
                st.info("No B2C test cases")
        
        with tab2:
            if "B2B" in segment_data and segment_data["B2B"]:
                for channel in segment_data["B2B"]:
                    with st.expander(f"**{channel}** Channel", expanded=True):
                        cols = st.columns(3)
                        for idx, (technology, actions) in enumerate(segment_data["B2B"][channel].items()):
                            with cols[idx % 3]:
                                st.metric(technology, f"{len(actions)} actions")
            else:
                st.info("No B2B test cases")
    
    # Test Cases List
    st.markdown("### 📋 Test Cases")
    
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
    
    # Add New Test Case
    st.markdown("### ➕ Add New Test Case")
    
    with st.container():
        st.markdown('<div class="custom-card">', unsafe_allow_html=True)
        
        if not st.session_state.steps_data:
            st.error("❌ No actions found! Please add actions first.")
        else:
            action_list = list(st.session_state.steps_data.keys())
            
            with st.form("add_testcase_form"):
                sentence = st.text_area(
                    "**Requirement Sentence**", 
                    height=100, 
                    placeholder="Describe your requirement here...",
                    help="Enter the requirement sentence that describes the test case"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    action = st.selectbox("**Action**", options=action_list, help="Select the action from kroky.json")
                with col2:
                    st.write("**Step Count**")
                    step_count = len(st.session_state.steps_data.get(action, {}).get("steps", []))
                    st.markdown(f"<h3>{step_count} steps</h3>", unsafe_allow_html=True)
                
                col3, col4 = st.columns(2)
                with col3:
                    priority = st.selectbox("**Priority**", options=["1-High", "2-Medium", "3-Low"], index=1)
                with col4:
                    complexity = st.selectbox("**Complexity**", options=["1-Giant", "2-Huge", "3-Big", "4-Medium", "5-Low"], index=3)
                
                if st.form_submit_button("🚀 Add Test Case", use_container_width=True, type="primary"):
                    if not sentence.strip():
                        st.error("Requirement sentence cannot be empty.")
                    elif not action:
                        st.error("Select an action.")
                    else:
                        order = project_data["next_id"]
                        channel = extract_channel(sentence)
                        segment = extract_segment(sentence)
                        technology = extract_technology(sentence)
                        prefix = f"{order:03d}_{channel}_{segment}_{technology}"
                        test_name = f"{prefix}_{sentence.strip().capitalize()}"
                        
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
                        st.success(f"✅ Test case **{test_name}** added successfully!")
                        st.balloons()
                        st.rerun()
        
        st.markdown('</div>', unsafe_allow_html=True)

# [Pokračování s dalšími stránkami...]
# Pro zkrácení kódu pokračuj s Edit Actions a Text Comparator podobným stylem

st.markdown("""
<div style='text-align: center; margin-top: 50px; color: #666;'>
    <p>Testool Pro v2.0 • Built with ❤️ using Streamlit</p>
</div>
""", unsafe_allow_html=True)