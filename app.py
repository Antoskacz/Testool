import streamlit as st

st.set_page_config(
    page_title="TestTool - Test Case Management",
    page_icon="🧪",
    layout="wide"
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

# Title
st.title("🧪 TestTool")
st.markdown("### Professional test case builder and manager")

# Navigation in sidebar
st.sidebar.title("🔧 Navigation")
page = st.sidebar.radio(
    "Go to:",
    [
        "🏗️ Build Test Cases",
        "🔧 Edit Actions & Steps", 
        "📤 Import from Excel",
        "📝 Text Comparator"
    ]
)

# Page routing
if page == "🏗️ Build Test Cases":
    from pages.build_testcases import show
    show()
elif page == "🔧 Edit Actions & Steps":
    from pages.edit_testcases import show
    show()
elif page == "📤 Import from Excel":
    st.info("🚧 Excel Import - Coming Soon!")
    st.write("This feature will allow importing test cases from Excel files.")
elif page == "📝 Text Comparator":
    st.info("🚧 Text Comparator - Coming Soon!")
    st.write("This feature will allow comparing two texts with highlighting differences.")