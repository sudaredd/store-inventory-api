import sqlite3
import numpy as np
import json
from sentence_transformers import SentenceTransformer
import os
from database import get_db_connection

def ingest_inventory():
    print("Connecting to database...")
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    
    if not products:
        print("No products found in database.")
        return

    print(f"Found {len(products)} products. Loading model...")
    # Initialize Sentence Transformer model
    # Use 'mps' for Apple Silicon acceleration if available, else cpu
    device = "mps"
    print(f"Using device: {device}")
    
    model = SentenceTransformer('all-MiniLM-L6-v2', device=device)
    
    # Prepare data
    documents = []
    metadata = []
    
    print("Generating embeddings...")
    for p in products:
        # Create a rich text representation for embedding
        text_rep = f"Product ID: {p['id']}. Name: {p['name']}. Price: ${p['price']}."
        documents.append(text_rep)
        
        # Store metadata including the original text for retrieval
        metadata.append({
            "id": p['id'],
            "name": p['name'],
            "price": float(p['price']),
            "text": text_rep
        })

    # Generate embeddings (returns numpy array)
    embeddings = model.encode(documents)
    
    # Convert to standard float32 for consistency
    embeddings = embeddings.astype('float32')
    
    print(f"Embeddings shape: {embeddings.shape}")
    
    # Save to disk
    print("Saving to disk...")
    np.save("inventory_embeddings.npy", embeddings)
    
    with open("inventory_metadata.json", "w") as f:
        json.dump(metadata, f, indent=2)
    
    print(f"Successfully ingested {len(products)} items.")
    print("Saved 'inventory_embeddings.npy' and 'inventory_metadata.json'")

if __name__ == "__main__":
    ingest_inventory()
