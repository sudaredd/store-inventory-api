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

def save_chat_message(session_id: str, role: str, content: str):
    """Saves a chat message to the history."""
    conn = get_db_connection()
    try:
        conn.execute('INSERT INTO chat_history (session_id, role, content) VALUES (?, ?, ?)', 
                     (session_id, role, content))
        conn.commit()
    except Exception as e:
        print(f"Error saving chat message: {e}")
    finally:
        conn.close()

def get_recent_history(session_id: str, limit: int = 10):
    """Retrieves the most recent chat history for a session."""
    conn = get_db_connection()
    try:
        messages = conn.execute('''
            SELECT role, content 
            FROM chat_history 
            WHERE session_id = ? 
            ORDER BY timestamp DESC 
            LIMIT ?
        ''', (session_id, limit)).fetchall()
        
        # Reverse to return in chronological order (oldest -> newest)
        return [{"role": m["role"], "parts": [m["content"]]} for m in reversed(messages)]
    except Exception as e:
        print(f"Error retrieving chat history: {e}")
        return []
    finally:
        conn.close()
