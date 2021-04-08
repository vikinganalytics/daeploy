import streamlit as st
from daeploy.communication import call_service

st.title("Die App")

roll = st.button("Roll")

if roll:
    data = call_service(service_name="die_roller", entrypoint_name="roll_die")

    st.header("Roll:")
    st.write(data)
