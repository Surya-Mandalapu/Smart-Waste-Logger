import csv

WASTE_LOG_PATH = "waste_log.csv"

def log_item(filename, label, material, recyclable, co2_kg):
    with open(WASTE_LOG_PATH, mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([filename, label, material, recyclable, co2_kg])

def read_log():
    with open(WASTE_LOG_PATH, newline="") as file:
        reader = csv.DictReader(file)
        return list(reader)