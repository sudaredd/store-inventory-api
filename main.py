from flask import Flask, jsonify, request, render_template, session
from database import get_db_connection, get_all_inventory_text
from google import genai
from google.genai import types
import os
import time
from dotenv import load_dotenv
import tools 
import uuid
import json 

load_dotenv()

app = Flask(__name__)
app.secret_key = os.urandom(24)


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
                    if match_msg:
                        wait_time = float(match_msg.group(1)) + 1.0

                    print(f"429 Hit. API asked to wait {wait_time}s. Sleeping...")
                    time.sleep(wait_time)
                    continue
                else:
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
    start_time = time.time() # Start Latency Timer

    question = request.args.get('q', '')
    if not question:
        return jsonify({"error": "Missing query parameter 'q'"}), 400

    # --- Day 11: Chat Persistence ---
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    session_id = session['session_id']
    
    # Save User Context
    tools.save_chat_message(session_id, 'user', question)

    # --- Day 9: Human-in-the-Loop ---
    if 'pending_delete' in session:
        end_time = time.time()
        latency = round(end_time - start_time, 2)
        # Check if user approved (flexible match)
        if 'YES' in question.upper():
            product_id = session['pending_delete']['product_id']
            result = tools.delete_product(product_id=product_id)
            session.pop('pending_delete', None)
            return jsonify({
                "answer": f"Okay, I have deleted the item. {result['message']}",
                "model": "System-Interceptor",
                "latency": latency,
                "category": "DELETE-CONFIRMED"
            })
        else:
             session.pop('pending_delete', None)
             return jsonify({
                 "answer": "Okay, I have cancelled the deletion.",
                 "model": "System-Interceptor",
                 "latency": latency,
                 "category": "DELETE-CANCELLED"
             })

    inventory_text = get_all_inventory_text()
    
    # 2. System/Context Prompt
    system_instruction = (
        f"You are a Senior Store Manager. You have access to a database of products and you can use tools to manage it. "
        f"You ALSO have a memory of the conversation. You should remember user details (name, preferences) if they were mentioned previously. "
        f"For every request, you MUST think step-by-step using this exact structure:\n\n"
        f"1. Analysis: Restate what the user wants in your own words. If calculation is needed, show math here.\n"
        f"2. Inventory Check: Search the provided inventory text for relevant products and IDs.\n"
        f"3. Action Plan: Decide if you need to call a tool or just provide info. Explain your logic. If you need to call a tool, you must call it.\n"
        f"4. Final Answer: Provide the conclusion to the user.\n\n"
        f"CRITICAL RULES:\n"
        f"- You CANNOT update, delete, or modify the database with words alone.\n"
        f"- If your Action Plan says to delete or update, you MUST emit a tool call. Do not just say you did it.\n"
        f"- Never assume an action is complete until the tool has returned a result.\n\n"
        f"EXAMPLE OF CORRECT BEHAVIOR:\n"
        f"User: 'Delete Product 1'\n"
        f"You:\n"
        f"1. Analysis: User wants to delete Product 1.\n"
        f"2. Inventory Check: Product 1 is 'Widget'.\n"
        f"3. Action Plan: I must call the tool.\n"
        f"4. Final Answer: I am calling the tool now.\n"
        f"(Tools: function_call('delete_product', {{'product_id': 1}}))\n\n"
        f"Inventory: [{inventory_text}].\n"
        f"User Question: {question}"
    )

    try:
        # --- Day 8: Multi-Model Router ---
        def classify_query(q):
            """Classifies query as SIMPLE, COMPLEX, or DELETE."""
            # PRE-FILTER: Explicitly catch delete intent to force strict tool usage
            if "delete" in q.lower() or "remove" in q.lower():
                return "DELETE"

            try:
                router_prompt = (
                    f"Classify this query as 'SIMPLE' or 'COMPLEX'.\n"
                    f"Query: '{q}'\n"
                    f"Rules:\n"
                    f"- SIMPLE: Greetings, price checks, single item updates, simple factual questions.\n"
                    f"- COMPLEX: Math, multi-item reasoning, strategy, discounts, 'what if' scenarios.\n"
                    f"Return ONLY the word SIMPLE or COMPLEX."
                )
                # Use the ONLY available model
                res = generate_response_safe(router_prompt, model="gemini-2.5-flash")
                return (res.text or "").strip().upper()
            except Exception:
                return "COMPLEX" # Fallback to smart model on error

        category = classify_query(question)
        
        if category == "DELETE":
            # DETERMINISTIC FLOW: Do not trust the chat model to pause.
            # 1. Extract intent
            extraction_prompt = (
                f"Extract the specific Product Name or details the user wants to remove from: '{question}'. "
                f"Return ONLY the extracted text. If multiple, return the most specific one."
            )
            target_str_res = generate_response_safe(extraction_prompt, model="gemini-2.5-flash")
            target_str = (target_str_res.text or "").strip()
            
            # 2. Find it in DB manually (simple fuzzy match)
            conn = get_db_connection()
            # Try to match ID first if it's a number
            product = None
            import re
            id_match = re.search(r'\b\d+\b', target_str)
            if id_match:
                 pid = int(id_match.group(0))
                 product = conn.execute('SELECT * FROM products WHERE id = ?', (pid,)).fetchone()
            
            # If no ID match, try name match
            if not product:
                # Safe parameterized search
                product = conn.execute('SELECT * FROM products WHERE lower(name) LIKE ?', ('%' + target_str.lower() + '%',)).fetchone()

            conn.close()

            end_time = time.time()
            latency = round(end_time - start_time, 2)

            # 3. Force Confirmation or Report Not Found
            if product:
                session['pending_delete'] = {'product_id': product['id']}
                return jsonify({
                    "answer": f"⚠️ SAFETY CHECK: I found '{product['name']}' (ID: {product['id']}). Are you sure you want to DELETE it? (Reply YES)",
                    "model": "System-Interceptor",
                    "latency": latency,
                    "category": "DELETE-SAFETY"
                })
            else:
                 return jsonify({
                     "answer": f"I couldn't find a product matching '{target_str}' to delete. Please be more specific.",
                     "model": "System-Interceptor",
                     "latency": latency,
                     "category": "DELETE-FAILED"
                 })

        elif "SIMPLE" in category:
            selected_model = "gemini-2.5-flash"
        else:
            selected_model = "gemini-2.5-flash" # No experimental model available apparently
            
        print(f"[ROUTER] Routing to {selected_model} because task is {category}")

        # Manual Loop Implementation using Safe Generator
        messages = [system_instruction]
        
        # Load History
        history = tools.get_recent_history(session_id)
        
        for msg in history:
            messages.append(types.Content(role=msg['role'], parts=[types.Part.from_text(text=msg['parts'][0])]))
            
        turn_count = 0
        
        while turn_count < 5:
            turn_count += 1
            # Generate content with robust 429 handling
            res = generate_response_safe(
                prompt=messages,
                model=selected_model,
                tools_list=[tools.update_product_price, tools.delete_product]
            )
            
            # DEBUG: Print raw response to trace tool behavior
            print(f"DEBUG RESPONSE: {res.candidates[0].content}")

            # Check for function calls
            if res.function_calls:
                # Add the model's request to history
                messages.append(res.candidates[0].content)
                
                parts = []
                for fc in res.function_calls:
                    fn_name = fc.name
                    fn_args = fc.args
                    print(f"Calling tool: {fn_name} with {fn_args}")
                    
                    # --- Day 9: Human-in-the-Loop ---
                    if fn_name == 'delete_product':
                         # With Deterministic Flow, this code path might become redundant for initial delete, 
                         # but keeping it as a fallback if the model decides to delete internally.
                         pass 

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
                end_time = time.time()
                latency = round(end_time - start_time, 2)
                answer_text = res.text.strip() if res.text else "I completed the action."
                
                # Save AI Context
                tools.save_chat_message(session_id, 'model', answer_text)
                
                return jsonify({
                    "answer": answer_text,
                    "model": selected_model,
                    "latency": latency,
                    "category": category
                })
        
        end_time = time.time()
        latency = round(end_time - start_time, 2)
        return jsonify({
            "answer": "I'm thinking too hard about this! Please try a simpler request.",
            "model": selected_model,
            "latency": latency,
            "category": "TIMEOUT"
        })

    except Exception as e:
        print(f"Error: {e}")
        return jsonify({"error": f"AI generation failed: {str(e)}"}), 500

@app.route('/')
def home():
    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True, port=8080)
