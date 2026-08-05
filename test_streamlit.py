import streamlit as st

st.title("Streamlit Test App")


name = st.text_input("Enter your name:")

if name:
    st.success(f"Hello {name}! Streamlit is running perfectly.")