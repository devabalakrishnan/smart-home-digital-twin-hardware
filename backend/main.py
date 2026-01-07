from fastapi import FastAPI
import pandas as pd

app = FastAPI()

@app.get("/sync")
async def sync_twin():
    df = pd.read_csv("data/solar_forecast.csv")
    peak_solar = df['generation_kw'].max()
    return {
        "status": "Online",
        "peak_forecast": f"{peak_solar} kW",
        "optimization_engine": "PPO Agent Active"
    }
