from database import create_tables, get_db_connection

def init_db():
    create_tables()
    conn = get_db_connection()
    
    # Check if data already exists to avoid duplicates if run multiple times
    cur = conn.cursor()
    cur.execute('SELECT count(*) FROM products')
    count = cur.fetchone()[0]
    
    if count == 0:
        products = [
            ("Google Pixel", 799.00),
            ("Google Nest Hub", 99.99),
            ("Chromecast with Google TV", 49.99),
            ("Fitbit Charge 5", 149.95),
            ("Nest Cam (battery)", 179.99)
        ]
        cur.executemany("INSERT INTO products (name, price) VALUES (?, ?)", products)
        conn.commit()
        print("Database initialized with 5 sample products.")
    else:
        print("Database already contains data.")
        
    conn.close()

if __name__ == '__main__':
    init_db()
