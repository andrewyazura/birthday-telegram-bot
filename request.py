import requests

response = requests.get("http://127.0.0.1:8080/birthdays/incoming")
if response.status_code != 200:
    print(f"Failed to get incoming birthdays. {response.status_code}")
    exit(1)
data = response.json() #type - list
print(data)
