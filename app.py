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

# Navigation in sidebar ONLY
st.sidebar.title("Navigation")
page = st.sidebar.radio(
    "",
    [
        "🏗️ Build Test Cases",
        "🔧 Edit Actions & Steps", 
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
elif page == "📝 Text Comparator":
    # Integrated Text Comparator code
    st.title("📝 Text Comparator")
    st.markdown("Compare two texts with highlighted differences")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Text 1")
        text1 = st.text_area("Enter first text:", height=300, key="text1")
    
    with col2:
        st.subheader("Text 2")
        text2 = st.text_area("Enter second text:", height=300, key="text2")
    
    st.markdown("---")
    
    if st.button("🔍 Compare Texts", use_container_width=True, type="primary"):
        if text1.strip() and text2.strip():
            import difflib
            
            # Split into lines for better comparison
            lines1 = text1.splitlines()
            lines2 = text2.splitlines()
            
            # Create HTML diff
            differ = difflib.HtmlDiff()
            diff_html = differ.make_file(lines1, lines2, fromdesc="Text 1", todesc="Text 2")
            
            # Display the diff
            st.subheader("📊 Differences")
            st.markdown(diff_html, unsafe_allow_html=True)
            
            # Show statistics
            seq = difflib.SequenceMatcher(None, text1, text2)
            similarity = seq.ratio() * 100
            
            col_stat1, col_stat2, col_stat3 = st.columns(3)
            with col_stat1:
                st.metric("Similarity", f"{similarity:.1f}%")
            with col_stat2:
                st.metric("Characters Text 1", len(text1))
            with col_stat3:
                st.metric("Characters Text 2", len(text2))
            
        else:
            st.warning("Please enter text in both fields to compare.")