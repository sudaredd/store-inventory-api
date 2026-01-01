from database import get_db_connection
import numpy as np
import json
import os
from sentence_transformers import SentenceTransformer
from numpy.linalg import norm

# Initialize models globally for the tool
print("Loading Search Models...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2', device="mps") # Use MPS or CPU
print("Search Models Loaded.")

def get_inventory_data():
    """Loads embeddings and metadata from disk."""
    if not os.path.exists("inventory_embeddings.npy") or not os.path.exists("inventory_metadata.json"):
        return None, None
    
    embeddings = np.load("inventory_embeddings.npy")
    with open("inventory_metadata.json", "r") as f:
        metadata = json.load(f)
    return embeddings, metadata

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

def search_inventory(query: str):
    """
    Performs a semantic search on the inventory to find relevant products.
    Returns the top 3 matches.
    """
    try:
        embeddings, metadata = get_inventory_data()
        if embeddings is None or metadata is None:
            return ["Error: Inventory index not found. Please run vector_store.py first."]

        # Generate embedding for the query
        query_embedding = embedding_model.encode([query])[0]
        
        # Calculate Cosine Similarity
        # Cosine Sim(A, B) = (A . B) / (||A|| * ||B||)
        scores = np.dot(embeddings, query_embedding) / (norm(embeddings, axis=1) * norm(query_embedding))
        
        # Get top 3 indices
        top_k_indices = np.argsort(scores)[-3:][::-1]
        
        matches = []
        for idx in top_k_indices:
            item = metadata[idx]
            # Construct rich object
            matches.append({
                "id": item['id'],
                "name": item['name'],
                "price": item['price'],
                "description": item['text'], # Keep text for AI context
                "image_url": "https://placehold.co/300x200/png?text=Product", # Placeholder
                "quantity": 10 # Mock quantity
            })
            
        return matches
    except Exception as e:
        return [f"Error searching inventory: {str(e)}"]
