import numpy as np
import gymnasium as gym

class MergedSolarHomeEnv(gym.Env):
    def __init__(self, solar_data, demand_data):
        super(MergedSolarHomeEnv, self).__init__()
        self.solar_profile = solar_data # Linked to solar_forecast.csv
        self.demand_profile = demand_data # Linked to total_demand
        self.current_hour = 0
        
        # State: The current hour (0-23)
        self.observation_space = gym.spaces.Box(low=0, high=23, shape=(1,), dtype=np.float32)
        # Action: 0 (No change), 1 (Activate flexible load)
        self.action_space = gym.spaces.Discrete(2)

    def step(self, action):
        solar_val = self.solar_profile[self.current_hour]
        demand_val = self.demand_profile[self.current_hour]
        
        # Reward Logic based on Net Load
        # If action=1, we add 2kW of shiftable load to match solar peaks
        actual_demand = demand_val + (2.0 if action == 1 else 0.0)
        net = actual_demand - solar_val
        
        # Optimization: Reward for consuming solar, penalize for grid
        reward = 1.0 if net <= 0 else -net
        
        self.current_hour = (self.current_hour + 1) % 24
        return np.array([self.current_hour], dtype=np.float32), reward, False, False, {}
