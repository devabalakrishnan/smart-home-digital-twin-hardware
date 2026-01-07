import streamlit as st
import pandas as pd
import paho.mqtt.client as mqtt
import ssl
import time
import os

# --- 1. MQTT & DATA CONFIGURATION ---
MQTT_HOST = "cyanqueen-29ab69cf.a01.euc1.aws.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "hivemq.client.1766925863216"
MQTT_PASS = "6<9SwUoy#0D8*dI:CNir"

def send_mqtt_command(is_on):
    client = mqtt.Client(transport="tcp") 
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set(cert_reqs=ssl.CERT_NONE) 
    try:
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        topic = "home/appliances/heater/command"
        payload = "ON" if is_on else "OFF"
        client.publish(topic, payload, qos=1)
        client.disconnect()
        return True
    except:
        return False

# Hardened Data Loading
def load_data():
    if os.path.exists("data/next_day_prediction.csv"):
        df = pd.read_csv("data/next_day_prediction.csv")
        # Fix the "float and str" error by forcing numeric types
        for col in df.columns:
            if col != 'Timestamp':
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
        return df
    return None

df = load_data()

# --- 2. AUTOMATION UI ---
st.title("🏡 Autonomous Digital Twin Dashboard")

if df is not None:
    st.sidebar.header("🤖 Automation Settings")
    auto_mode = st.sidebar.toggle("Enable AI Auto-Control")
    
    # Session state to keep track of the current simulation hour
    if 'current_hr' not in st.session_state:
        st.session_state.current_hr = 0

    if auto_mode:
        st.sidebar.info(f"AI is controlling hardware for Hour {st.session_state.current_hr}:00")
        
        # --- AI DECISION LOGIC (AUTOMATIC) ---
        row = df.iloc[st.session_state.current_hr]
        # Logic: If solar is high (>1.5kW) and price is low, turn on heater
        ai_should_be_on = row['solar_gen'] > 1.5 
        
        # Send command to HiveMQ automatically
        success = send_mqtt_command(ai_should_be_on)
        
        if success:
            st.sidebar.success(f"✅ Auto-Sent: {'ON' if ai_should_be_on else 'OFF'}")
        
        # Advance simulation time
        time.sleep(2) # 2 seconds per hour for demo
        st.session_state.current_hr = (st.session_state.current_hr + 1) % 24
        st.rerun()
    else:
        # Manual slider if Auto is OFF
        st.session_state.current_hr = st.sidebar.slider("Manual Hour Select", 0, 23, st.session_state.current_hr)

    # --- DISPLAY METRICS ---
    row = df.iloc[st.session_state.current_hr]
    c1, c2, c3 = st.columns(3)
    c1.metric("Demand", f"{row['total_demand']:.2f} kW")
    c2.metric("Solar", f"{row['solar_gen']:.2f} kW")
    c3.metric("Grid State", "Exporting" if row['solar_gen'] > row['total_demand'] else "Importing")
