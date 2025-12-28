import urllib.request
import json
import time

BASE_URL = "http://127.0.0.1:8080/products"

products = [
    {"name": "MacBook Pro M3 Max", "price": 3199.00},
    {"name": "Dell XPS 15 OLED", "price": 2499.00},
    {"name": "Sony Alpha a7 IV", "price": 2498.00},
    {"name": "Canon EOS R5", "price": 3899.00},
    {"name": "DJI Mini 4 Pro", "price": 759.00},
    {"name": "GoPro Hero 12 Black", "price": 399.00},
    {"name": "iPad Pro 13-inch", "price": 1299.00},
    {"name": "Samsung Odyssey G9 Monitor", "price": 1799.00},
    {"name": "Herman Miller Aeron Chair", "price": 1695.00},
    {"name": "Logitech MX Master 3S", "price": 99.00}
]

def add_product(product):
    try:
        data = json.dumps(product).encode('utf-8')
        req = urllib.request.Request(
            BASE_URL, 
            data=data, 
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req) as response:
            if response.status == 201:
                print(f"[SUCCESS] Added: {product['name']}")
            else:
                print(f"[FAILED] Could not add: {product['name']} (Status: {response.status})")
    except Exception as e:
        print(f"[ERROR] Adding {product['name']}: {e}")

if __name__ == "__main__":
    print(f"Starting insertion of {len(products)} products...")
    for p in products:
        add_product(p)
        time.sleep(0.5) # Gentle pace
    print("Done!")
