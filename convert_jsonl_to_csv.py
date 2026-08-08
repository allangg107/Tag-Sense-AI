import json
import csv
import os

input_file = 'test_results.jsonl'
output_file = 'test_results.csv'

if not os.path.exists(input_file):
    print(f"Error: {input_file} not found.")
    exit(1)

data = []
with open(input_file, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip():
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Skipping invalid line: {e}")

if not data:
    print("No data found.")
    exit(1)

# Get headers from all keys present in the data to handle potential schema variations
headers = set()
for row in data:
    headers.update(row.keys())
headers = sorted(list(headers))

with open(output_file, 'w', newline='', encoding='utf-8') as f:
    writer = csv.DictWriter(f, fieldnames=headers)
    writer.writeheader()
    for row in data:
        # Convert list to string for CSV compatibility
        if isinstance(row.get('tags'), list):
            row['tags'] = '; '.join(row['tags'])
        writer.writerow(row)

print(f"Successfully converted {len(data)} rows to {output_file}")
