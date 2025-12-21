from flask import Flask, jsonify, request
from database import get_db_connection
import google.generativeai as genai
import os

app = Flask(__name__)

# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

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
        model = genai.GenerativeModel("gemini-flash-latest")
        PROMPT = (
            f"You are an elite e-commerce copywriter for a luxury brand like Apple or Leica. "
            f"Your tone is minimal, sophisticated, and expensive. "
            f"Never use emojis, never use exclamation marks, and keep descriptions under 20 words. "
            f"Write a description for a product named '{product['name']}'."
        )
        response = model.generate_content(PROMPT)
        return jsonify({"description": response.text.strip()})
    except Exception as e:
        return jsonify({"error": f"AI generation failed: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=8080)
