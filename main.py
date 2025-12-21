from flask import Flask, jsonify, request
from database import get_db_connection, get_all_inventory_text
from google import genai
import os
import time
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

# Initialize the modern Client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

def call_gemini_with_fallback(prompt):
    try:
        # Primary model
        response = client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt
        )
        return response.text.strip()
    except Exception as e:
        error_str = str(e)
        # Check for 429 (Resource Exhausted) or 404 (Not Found)
        if "429" in error_str or "404" in error_str:
            print(f"Primary model failed (1.5-flash). Error: {error_str[:50]}... Retrying with fallback (gemini-2.5-flash-lite) in 1s...")
            time.sleep(1) # Wait for network/quota to settle
            try:
                # User requested fallback
                response = client.models.generate_content(
                    model="gemini-2.5-flash-lite",
                    contents=prompt
                )
                return response.text.strip()
            except Exception as fallback_error:
                print(f"Fallback (2.5-flash-lite) failed: {str(fallback_error)[:50]}... Retrying with safety net (gemini-flash-latest)...")
                # Ultimate fallback (Safety Net)
                try:
                    response = client.models.generate_content(
                        model="gemini-flash-latest",
                        contents=prompt
                    )
                    return response.text.strip()
                except Exception as final_error:
                    raise Exception(f"All models failed. Final error: {str(final_error)}")
        else:
            raise e

@app.route('/products', methods=['GET'])
def get_products():
    conn = get_db_connection()
    products = conn.execute('SELECT * FROM products').fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in products])

@app.route('/products', methods=['POST'])
def add_product():
    new_product = request.get_json()
    if not new_product or 'name' not in new_product or 'price' not in new_product:
         return jsonify({"error": "Invalid input, 'name' and 'price' required"}), 400
    
    conn = get_db_connection()
    try:
        cur = conn.execute('INSERT INTO products (name, price) VALUES (?, ?)',
                         (new_product['name'], new_product['price']))
        conn.commit()
        new_id = cur.lastrowid
        new_product['id'] = new_id
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()
    
    return jsonify(new_product), 201

@app.route('/search', methods=['GET'])
def search_products():
    query = request.args.get('q', '').lower()
    if not query:
        return jsonify([])
    
    conn = get_db_connection()
    # SQL LIKE for simple search
    results = conn.execute('SELECT * FROM products WHERE lower(name) LIKE ?', ('%' + query + '%',)).fetchall()
    conn.close()
    
    return jsonify([dict(ix) for ix in results])

@app.route('/describe/<int:id>', methods=['POST'])
def describe_product(id):
    conn = get_db_connection()
    product = conn.execute('SELECT * FROM products WHERE id = ?', (id,)).fetchone()
    conn.close()

    if product is None:
        return jsonify({"error": "Product not found"}), 404

    try:
        PROMPT = (
            f"You are an elite e-commerce copywriter for a luxury brand like Apple or Leica. "
            f"Your tone is minimal, sophisticated, and expensive. "
            f"Never use emojis, never use exclamation marks, and keep descriptions under 20 words. "
            f"Write a description for a product named '{product['name']}'."
        )
        description = call_gemini_with_fallback(PROMPT)
        return jsonify({"description": description})
    except Exception as e:
        return jsonify({"error": f"AI generation failed: {str(e)}"}), 500

@app.route('/inventory-chat', methods=['GET'])
def inventory_chat():
    question = request.args.get('q', '')
    if not question:
        return jsonify({"error": "Missing query parameter 'q'"}), 400

    inventory_text = get_all_inventory_text()
    
    try:
        PROMPT = (
            f"You are a store manager. Based on this inventory list: [{inventory_text}], "
            f"answer the user's question: [{question}]."
        )
        answer = call_gemini_with_fallback(PROMPT)
        return jsonify({"answer": answer})
    except Exception as e:
        return jsonify({"error": f"AI generation failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8080)
