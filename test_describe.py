import urllib.request
import json
import sys

try:
    product_id = 1
    url = f'http://127.0.0.1:8080/describe/{product_id}'

    print(f"Requesting description for Product ID {product_id}...")
    
    req = urllib.request.Request(
        url,
        data=b'', 
        headers={'Content-Type': 'application/json'},
        method='POST'
    )

    with urllib.request.urlopen(req) as response:
        status = response.status
        print(f"Status: {status}")
        data = json.loads(response.read().decode('utf-8'))
        
        if 'description' in data:
            print(data['description'])
        else:
            print(data)

except urllib.error.HTTPError as e:
    print(f"Error: HTTP {e.code}")
    error_content = e.read().decode('utf-8')
    print(error_content)
    with open('error.log', 'w') as f:
        f.write(error_content)
except Exception as e:
    print(f"An error occurred: {e}")
