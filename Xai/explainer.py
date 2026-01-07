import pandas as pd
import numpy as np
import plotly.express as px

class DigitalTwinExplainer:
    def __init__(self, data):
        self.df = data
        # Mapping of factors to their thesis-importance weights
        self.base_weights = {
            'Electricity Price': 0.8,
            'Solar Forecast': 0.7,
            'Occupancy': 0.4,
            'Total Demand': 0.3
        }

    def get_dynamic_explanation(self, hour):
        """
        Generates XAI weights that shift based on the selected hour.
        This simulates the behavior of a PPO agent reacting to environment changes.
        """
        row = self.df.iloc[hour]
        weights = self.base_weights.copy()

        # 1. Solar Factor: Dominates during daylight (10 AM - 4 PM)
        if 10 <= hour <= 16:
            weights['Solar Forecast'] += 1.2
            weights['Electricity Price'] -= 0.2
        else:
            weights['Solar Forecast'] = 0.1 # Solar has no impact at night

        # 2. Price Factor: Dominates during Peak Evening (5 PM - 9 PM)
        if 17 <= hour <= 21:
            weights['Electricity Price'] += 1.1
            weights['Total Demand'] += 0.5

        # 3. Demand Factor: Increases if net load is high
        if row['net_load'] > 1.5:
            weights['Total Demand'] += 0.6

        # Convert to DataFrame for Plotly
        xai_df = pd.DataFrame({
            'Factor': list(weights.keys()),
            'Weight': list(weights.values()),
            'Impact': ['Positive' if v > 1.0 else 'Neutral' for v in weights.values()]
        })
        
        return xai_df.sort_values(by='Weight', ascending=True)

    def plot_explanation(self, xai_df, hour):
        """Creates the horizontal bar chart for the dashboard."""
        fig = px.bar(
            xai_df, 
            x='Weight', 
            y='Factor', 
            orientation='h',
            color='Weight',
            color_continuous_scale='Blues',
            title=f"XAI: Influence Factors at {hour}:00",
            labels={'Weight': 'Feature Importance (Shapley Value)'}
        )
        
        # Style adjustments to match thesis aesthetics
        fig.update_layout(
            showlegend=False,
            height=300,
            margin=dict(l=20, r=20, t=40, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )
        return fig

    def get_decision_text(self, hour):
        """Provides a natural language explanation for the AI's action."""
        row = self.df.iloc[hour]
        if 10 <= hour <= 16 and row['solar_gen'] > 1.0:
            return "💡 **AI Logic:** High Solar generation detected. PPO is prioritizing renewable consumption."
        elif 17 <= hour <= 21:
            return "💰 **AI Logic:** Peak grid pricing active. PPO is enforcing load-shedding to save costs."
        else:
            return "🏠 **AI Logic:** Normal operation. Demand is being met by a balanced grid/battery mix."
