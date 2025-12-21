import urllib.request
import json

url = 'http://127.0.0.1:8080/products'
data = {
    'name': 'Demo Product',
    'price': 42.99
}

req = urllib.request.Request(
    url,
    data=json.dumps(data).encode('utf-8'),
    headers={'Content-Type': 'application/json'},
    method='POST'
)

with urllib.request.urlopen(req) as response:
    print(response.status)
    print(response.read().decode('utf-8'))
