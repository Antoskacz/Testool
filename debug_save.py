import streamlit as st
from app import save_and_update_steps

# simple script to trigger save_and_update_steps under Streamlit

def main():
    st.write("Debug save script running")
    data = {"debug_action": {"description": "desc", "steps": []}}
    save_and_update_steps(data)

if __name__ == "__main__":
    main()
