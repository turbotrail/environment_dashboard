import requests
import json

BASE_URL = "https://www.ngdc.noaa.gov/hazel/hazard-service/api/v1/volcanoes"
all_volcanoes = []

page = 1
while True:
    print(f"Fetching page {page}...")
    response = requests.get(BASE_URL, params={"page": page})
    if response.status_code != 200:
        print(f"Failed at page {page} with status code: {response.status_code}")
        break

    data = response.json()
    all_volcanoes.extend(data.get("items", []))

    if page >= data.get("totalPages", 1):
        break
    page += 1

# Save the complete dataset to a file
with open("noaa_volcanoes.json", "w") as f:
    json.dump(all_volcanoes, f, indent=2)

print(f"Saved {len(all_volcanoes)} volcanoes to noaa_volcanoes.json")