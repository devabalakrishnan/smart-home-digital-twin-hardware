import streamlit as st
import pandas as pd
import paho.mqtt.client as mqtt
import ssl
import time
import os
import numpy as np

# --- 1. MQTT CONFIGURATION ---
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

# --- 2. ROBUST DATA LOADING (FIXES KEYERROR) ---
def load_data():
    path = "data/next_day_prediction.csv"
    if os.path.exists(path):
        # Read CSV and immediately strip spaces from column names
        df = pd.read_csv(path)
        df.columns = df.columns.str.strip()
        
        # Define the appliances expected in your CSV
        app_cols = ['Fridge', 'Heater', 'Fans', 'Lights', 'TV', 'Microwave', 'Washing Machine']
        
        # Ensure all columns are numeric to prevent 'str' errors
        for col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        
        # FIX: Explicitly create 'total_demand' if it doesn't exist
        existing_apps = [c for c in app_cols if c in df.columns]
        df['total_demand'] = df[existing_apps].sum(axis=1)
        
        # FIX: Ensure 'solar_gen' exists (matching your previous solar_forecast logic)
        if 'solar_gen' not in df.columns:
            df['solar_gen'] = 0.0 # Default fallback
            
        return df, existing_apps
    return None, []

df, app_list = load_data()

# --- 3. AUTOMATION UI & LOGIC ---
st.title("🏡 Autonomous Digital Twin Dashboard")

if df is not None:
    # Use Session State to track time and auto-mode
    if 'current_hr' not in st.session_state:
        st.session_state.current_hr = 0
    if 'auto_mode' not in st.session_state:
        st.session_state.auto_mode = False

    st.sidebar.header("🤖 Control Center")
    st.session_state.auto_mode = st.sidebar.toggle("Enable AI Auto-Control", value=st.session_state.auto_mode)
    
    if st.session_state.auto_mode:
        row = df.iloc[st.session_state.current_hr]
        
        # AI Decision Logic
        # Automation: If solar surplus exists, activate heater
        ai_should_be_on = float(row['solar_gen']) > float(row['total_demand'])
        
        # Send command to physical hardware
        send_mqtt_command(ai_should_be_on)
        
        st.sidebar.info(f"Auto-Syncing Hour {st.session_state.current_hr}:00")
        st.sidebar.write(f"AI Decision: {'HEATER ON' if ai_should_be_on else 'HEATER OFF'}")
        
        time.sleep(2)
        st.session_state.current_hr = (st.session_state.current_hr + 1) % 24
        st.rerun()
    else:
        st.session_state.current_hr = st.sidebar.slider("Select Hour", 0, 23, st.session_state.current_hr)

    # --- 4. DISPLAY METRICS (SAFE FROM KEYERROR) ---
    row = df.iloc[st.session_state.current_hr]
    
    c1, c2, c3 = st.columns(3)
    # Using .get() or explicit check to ensure app doesn't crash
    val_demand = row['total_demand'] if 'total_demand' in row else 0.0
    val_solar = row['solar_gen'] if 'solar_gen' in row else 0.0
    
    c1.metric("Demand", f"{val_demand:.2f} kW")
    c2.metric("Solar", f"{val_solar:.2f} kW")
    c3.metric("Net Load", f"{(val_demand - val_solar):.2f} kW")

    st.bar_chart(df[app_list].iloc[st.session_state.current_hr])

else:
    st.error("🚨 CSV Data not found! Please check 'data/next_day_prediction.csv'")
