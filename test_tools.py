from tools import update_product_price, delete_product
from database import get_db_connection

def test_tools():
    print("Testing Tools...")
    
    # Setup: Create a dummy product
    conn = get_db_connection()
    cur = conn.execute("INSERT INTO products (name, price) VALUES ('Test Tool Item', 10.0)")
    conn.commit()
    item_id = cur.lastrowid
    conn.close()
    print(f"Created test item with ID {item_id}")

    # Test Update
    res = update_product_price(item_id, 99.99)
    print(f"Update Result: {res}")
    
    conn = get_db_connection()
    updated_price = conn.execute("SELECT price FROM products WHERE id = ?", (item_id,)).fetchone()['price']
    conn.close()
    
    if updated_price == 99.99:
        print("PASS: Price updated correctly")
    else:
        print(f"FAIL: Price is {updated_price}, expected 99.99")

    # Test Delete
    res = delete_product(item_id)
    print(f"Delete Result: {res}")

    conn = get_db_connection()
    deleted_item = conn.execute("SELECT * FROM products WHERE id = ?", (item_id,)).fetchone()
    conn.close()

    if deleted_item is None:
        print("PASS: Item deleted correctly")
    else:
        print("FAIL: Item still exists")

if __name__ == "__main__":
    test_tools()
