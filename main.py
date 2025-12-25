from flask import Flask, jsonify, request, render_template
from database import get_db_connection, get_all_inventory_text
from google import genai
from google.genai import types
import os
import time
from dotenv import load_dotenv
import tools 

load_dotenv()

app = Flask(__name__)

# Initialize the modern Client
client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# Create a tool dictionary for easy lookup
available_tools = {
    'update_product_price': tools.update_product_price,
    'delete_product': tools.delete_product
}

def generate_response_safe(prompt, model="gemini-2.5-flash", tools_list=None, response_schema=None, response_mime_type=None):
    """
    Generates content with robust 429 handling. Returns full response object.
    Supports optional tools list and structured output schema.
    """
    import re
    max_retries = 3
    base_delay = 5
    
    config = None
    if tools_list or response_schema or response_mime_type:
        config = types.GenerateContentConfig(
            tools=tools_list,
            response_schema=response_schema,
            response_mime_type=response_mime_type
        )

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model,
                contents=prompt,
                config=config
            )
            return response
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                if attempt < max_retries:
                    wait_time = base_delay * (2 ** attempt)
                    match_delay = re.search(r"retryDelay['\"]?:\s*['\"]?([\d\.]+)s", error_str)
                    match_msg = re.search(r"retry in ([\d\.]+)s", error_str)
                    
                    if match_delay:
                        wait_time = float(match_delay.group(1)) + 1.0
                    elif match_msg:
                        wait_time = float(match_msg.group(1)) + 1.0
                        
                    print(f"429 Hit. API asked to wait {wait_time}s. Sleeping...")
                    time.sleep(wait_time)
                    continue
                else:
                    if model == "gemini-2.5-flash":
                        print("Retry limit reached. Swapping to gemini-2.0-flash-exp for fallback...")
                        return generate_response_safe(
                            prompt, 
                            model="gemini-2.0-flash-exp", 
                            tools_list=tools_list,
                            response_schema=response_schema,
                            response_mime_type=response_mime_type
                        )
                    raise e
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
        # Use simple generation for description (no tools needed)
        PROMPT = (
            f"You are an elite e-commerce copywriter. Write a description for: '{product['name']}'."
            f"Strictly limit your response to maximum 30 words. Do not use Markdown formatting like bold or headers."
            f"Keep it one single sophisticated sentence."
        )
        response = generate_response_safe(PROMPT)
        return jsonify({"description": response.text.strip()})
    except Exception as e:
        return jsonify({"error": f"AI generation failed: {str(e)}"}), 500

@app.route('/inventory-report', methods=['GET'])
def inventory_report():
    inventory_text = get_all_inventory_text()
    
    # Define the schema for the report
    # Schema: Array<Object {name: str, price: float, is_luxury: bool}>
    report_schema = {
        "type": "ARRAY",
        "items": {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING"},
                "price": {"type": "NUMBER"},
                "is_luxury": {"type": "BOOLEAN"}
            },
            "required": ["name", "price", "is_luxury"]
        }
    }

    try:
        PROMPT = (
            f"Analyze this inventory: {inventory_text}. "
            f"Return a JSON array categorizing each item. "
            f"Mark as 'is_luxury' if price > 100."
        )
        
        # Use safe wrapper with schema
        response = generate_response_safe(
            PROMPT, 
            model="gemini-2.5-flash",
            response_schema=report_schema,
            response_mime_type="application/json"
        )
        
        # Parse the JSON string from the response
        import json
        return jsonify(json.loads(response.text))
        
    except Exception as e:
        return jsonify({"error": f"Report generation failed: {str(e)}"}), 500

@app.route('/inventory-chat', methods=['GET'])
def inventory_chat():
    question = request.args.get('q', '')
    if not question:
        return jsonify({"error": "Missing query parameter 'q'"}), 400

    inventory_text = get_all_inventory_text()
    
    # 2. System/Context Prompt
    system_instruction = (
        f"You are a store manager. You can update prices and delete products. "
        f"Inventory: [{inventory_text}]. "
        f"User Question: {question}"
    )

    try:
        # Manual Loop Implementation using Safe Generator
        messages = [system_instruction]
        turn_count = 0
        
        while turn_count < 5:
            turn_count += 1
            # Generate content with robust 429 handling
            res = generate_response_safe(
                prompt=messages,
                model="gemini-2.5-flash",
                tools_list=[tools.update_product_price, tools.delete_product]
            )
            
            # Check for function calls
            if res.function_calls:
                # Add the model's request to history
                messages.append(res.candidates[0].content)
                
                parts = []
                for fc in res.function_calls:
                     fn_name = fc.name
                     fn_args = fc.args
                     print(f"Calling tool: {fn_name} with {fn_args}")
                     
                     if fn_name in available_tools:
                         result = available_tools[fn_name](**fn_args)
                         # Create FunctionResponse part
                         parts.append(types.Part.from_function_response(
                             name=fn_name,
                             response=result
                         ))
                
                # Add function response to history
                messages.append(types.Content(role="user", parts=parts))
                # Loop continues to send this back to model
            else:
                # No function call, just text response
                return jsonify({"answer": res.text.strip()})
        
        return jsonify({"answer": "I'm thinking too hard about this! Please try a simpler request."})

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": f"AI generation failed: {str(e)}"}), 500

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=8080)
