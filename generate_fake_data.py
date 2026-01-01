import sqlite3
import random
from database import get_db_connection

def generate_fake_data(num_items=1000):
    print(f"Generating {num_items} fake products...")
    
    adjectives = ["Professional", "Ergonomic", "Wireless", "Smart", "4K", "Noise-Cancelling", "Portable", "Compact", "Gaming", "Vintage", "Waterproof", "Solar-Powered", "AI-Driven", "Heavy-Duty", "Lightweight", "Premium", "Budget", "Refurbished", "Limited Edition", "Ultra-Slim"]
    brands = ["Logitech", "Sony", "Dell", "Samsung", "Apple", "Canon", "Nike", "Adidas", "Generic", "AmazonBasics", "Razer", "Corsair", "Asus", "HP", "Lenovo", "Microsoft", "Google", "Bose", "JBL", "Anker"]
    nouns = ["Mouse", "Keyboard", "Monitor", "Headphones", "Camera", "Laptop", "Phone", "Charger", "Dock", "Speaker", "Microphone", "Tablet", "Watch", "Drone", "Router", "Hard Drive", "SSD", "Webcam", "Projector", "Backpack"]
    
    products = []
    
    for _ in range(num_items):
        name = f"{random.choice(brands)} {random.choice(adjectives)} {random.choice(nouns)}"
        # Add a random model number suffix sometimes
        if random.random() > 0.5:
            name += f" {random.randint(100, 9000)}{random.choice(['X', 'Pro', 'S', ' Plus', ' Ultra', ''])}"
            
        price = round(random.uniform(10.0, 5000.0), 2)
        products.append((name, price))
        
    conn = get_db_connection()
    try:
        conn.executemany('INSERT INTO products (name, price) VALUES (?, ?)', products)
        conn.commit()
        print(f"Successfully inserted {num_items} products.")
    except Exception as e:
        print(f"Error inserting data: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    generate_fake_data()
