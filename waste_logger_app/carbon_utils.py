import pandas as pd
import os

CARBON_TABLE_PATH = os.path.join(os.path.dirname(__file__), "carbon_table.csv")


def load_carbon_table():
    return pd.read_csv(CARBON_TABLE_PATH)

def estimate_impact(label, carbon_df):
    row = carbon_df[carbon_df["label"] == label]
    if row.empty:
        return ("unknown", False, 0.05)
    material = row.iloc[0]["material"]
    recyclable = row.iloc[0]["recyclable"]
    co2_kg = row.iloc[0]["co2_kg"]
    return material, recyclable, co2_kg

def get_item_data(label):
    carbon_df = load_carbon_table()
    material, recyclable, co2_kg = estimate_impact(label, carbon_df)
    return {
        "material": material,
        "recyclable": recyclable,
        "co2_kg": co2_kg
    }
