from database import get_db_connection

def update_product_price(product_id: int, new_price: float):
    """Updates the price of a product in the database."""
    conn = get_db_connection()
    try:
        conn.execute('UPDATE products SET price = ? WHERE id = ?', (new_price, product_id))
        conn.commit()
        return {"status": "success", "message": f"Updated product {product_id} price to ${new_price}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()

def delete_product(product_id: int):
    """Deletes a product from the database."""
    conn = get_db_connection()
    try:
        conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
        conn.commit()
        return {"status": "success", "message": f"Deleted product {product_id}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()
