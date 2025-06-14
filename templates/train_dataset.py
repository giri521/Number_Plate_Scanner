import pandas as pd

# Load dataset
df = pd.read_excel("vehicle_registration_data_complete.xlsx")

# Convert 'Plate Number' column to uppercase for consistency
df["Plate Number"] = df["Plate Number"].str.upper()

# Save back to ensure clean dataset
df.to_excel("vehicle_data_cleaned.xlsx", index=False)

print("Dataset is ready for number plate matching!")
