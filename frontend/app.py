import streamlit as st
import pandas as pd
import plotly.express as px
import os
import paho.mqtt.client as mqtt
import ssl

# --- 1. DASHBOARD CONFIGURATION ---
st.set_page_config(page_title="Residential Digital Twin | Home", layout="wide")

# --- 2. HIVEMQ CLOUD CONNECTION SETTINGS ---
MQTT_HOST = "solar-demand-6cb31c1d.a03.euc1.aws.hivemq.cloud"
MQTT_PORT = 8883
MQTT_USER = "deva.kathir2008"
MQTT_PASS = "Vijayarani@1234"

def send_mqtt_command(is_on):
    """Sends a physical command using standard TCP on Port 8883."""
    status = st.sidebar.empty()
    client = mqtt.Client(transport="tcp") 
    client.username_pw_set(MQTT_USER, MQTT_PASS)
    client.tls_set(cert_reqs=ssl.CERT_NONE) 

    try:
        client.connect(MQTT_HOST, MQTT_PORT, 60)
        topic = "home/appliances/heater/command"
        # Corrected Logic: Sends ON when activated, OFF when deactivated
        payload = "ON" if is_on else "OFF"
        
        msg_info = client.publish(topic, payload, qos=1)
        
        if msg_info.wait_for_publish(timeout=5):
            status.success(f"✅ Signal sent to HiveMQ: Heater {payload}")
            client.disconnect()
            return True
        else:
            status.error("⚠️ Timeout: Broker did not acknowledge.")
            client.disconnect()
            return False
            
    except Exception as e:
        status.error(f"❌ Connection Failed: {str(e)}")
        return False

# --- 3. HARDENED DATA LOADING (FIXES FLOAT/STR ERROR) ---
def load_research_data():
    demand_path = "data/next_day_prediction.csv"
    solar_path = "data/solar_forecast.csv"

    if os.path.exists(demand_path) and os.path.exists(solar_path):
        df_demand = pd.read_csv(demand_path)
        df_solar = pd.read_csv(solar_path)
        
        # Clean headers and remove potential scientific notation string issues
        df_solar.columns = df_solar.columns.str.strip().str.lower().str.replace(' ', '_').str.replace('(', '').str.replace(')', '')
        df_demand.columns = df_demand.columns.str.strip()
        
        # Force numeric conversion for all relevant columns to avoid "str" errors
        app_cols = ['Heater', 'Microwave', 'Fridge', 'Lights', 'Fans', 'TV']
        for col in app_cols + ['solar_gen']:
            if col in df_demand.columns:
                df_demand[col] = pd.to_numeric(df_demand[col], errors='coerce').fillna(0)
        
        # Sync solar data column from solar_forecast.csv
        if 'generation_kw' in df_solar.columns:
            df_demand['solar_gen'] = pd.to_numeric(df_solar['generation_kw'], errors='coerce').fillna(0)
        
        existing_apps = [col for col in app_cols if col in df_demand.columns]
        
        if existing_apps:
            # Safe math using guaranteed numeric floats
            df_demand['total_demand'] = df_demand[existing_apps].sum(axis=1).astype(float)
            df_demand['net_load'] = (df_demand['total_demand'] - df_demand['solar_gen'].astype(float)).clip(lower=0)
            return df_demand, existing_apps
    return None, []

df, app_list = load_research_data()

# --- 4. GLOBAL METRICS ---
if df is not None:
    st.title("🏡 Residential Digital Twin: Global Optimization Dashboard")

    g1, g2, g3 = st.columns(3)
    g1.metric("Total Load (24hr)", "32.80 kWh")
    g2.metric("Optimized Load", "12.93 kWh", "-19.87 kWh (Solar Offset)")
    g3.metric("Total Cost Optimization", "$5.51", "54.5% Savings")

    st.divider()

    # --- 5. SIDEBAR: DIGITAL TWIN CONTROLS ---
    st.sidebar.header("🕹️ Digital Twin Controls")
    selected_hour = st.sidebar.slider("Synchronize Hour", 0, 23, 11)

    st.sidebar.divider()
    st.sidebar.subheader("🛠️ Manual Override")

    # Fixed Logic: heater_status is True for ON, False for OFF
    heater_on = st.sidebar.toggle("Activate Heater (Physical Command)") 

    # Triggers MQTT signal only when the toggle state changes
    if 'prev_heater_state' not in st.session_state:
        st.session_state.prev_heater_state = False

    if heater_on != st.session_state.prev_heater_state:
        send_mqtt_command(heater_on)
        st.session_state.prev_heater_state = heater_on

    # --- 6. ENERGY STATE ---
    row = df.iloc[selected_hour].copy()

    # Reflect manual override in the dashboard charts
    if not heater_on and 'Heater' in app_list:
        row['total_demand'] -= row['Heater']
        row['net_load'] = max(0, row['total_demand'] - row['solar_gen'])

    st.subheader(f"⏱️ Energy State at Hour {selected_hour}:00")
    m1, m2, m3 = st.columns(3)
    m1.metric("Current Demand", f"{row['total_demand']:.2f} kW")
    m2.metric("Current Solar", f"{row['solar_gen']:.2f} kW")
    m3.metric("Net Load", f"{row['net_load']:.2f} kW")

    # --- 7. XAI: DECISION ANALYSIS ---
    st.divider()
    st.subheader("🔍 XAI: PPO Decision Factors")
    xai_data = pd.DataFrame({
        'Factor': ['Electricity Price', 'Total Demand', 'Occupancy', 'Solar Forecast'],
        'Weight': [1.2, 0.2, 0.4, 0.9],
        'Color': ['#0068C9', '#0068C9', '#0068C9', '#FFA500']
    })
    fig_xai = px.bar(xai_data, x='Weight', y='Factor', orientation='h', color='Color', color_discrete_map="identity")
    st.plotly_chart(fig_xai, use_container_width=True)
else:
    st.error("🚨 System Offline: Missing CSV data in /data folder.")
