import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
import tools

load_dotenv()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- 1. The Supervisor (Planner) ---
def supervisor_agent(user_query):
    """
    Analyzes the query and breaks it down into a list of tasks for specific agents.
    """
    system_prompt = (
        f"You are the Lead Coordinator (Supervisor) for a store system.\n"
        f"Your goal is to plan how to answer the user's request by delegating to valid agents:\n"
        f" - 'INVENTORY': For checking stock, prices, or product details.\n"
        f" - 'SHIPPING': For delivery times, shipping costs, or logistics rules.\n"
        f" - 'GENERAL': For simple greetings or questions unrelated to the store.\n"
        f"\n"
        f"RULES:\n"
        f"1. Return a JSON object with a 'plan' key, which is a LIST of tasks.\n"
        f"2. Each task must have:\n"
        f"   - 'agent': One of ['INVENTORY', 'SHIPPING', 'GENERAL']\n"
        f"   - 'instruction': Specific instructions for that agent.\n"
        f"3. Order matters! If the user asks for 'price and shipping', checking inventory (price) should likely happen before shipping (cost depends on price).\n"
        f"4. If 'GENERAL' is used, it should probably be the only task.\n"
        f"5. Return ONLY Raw JSON."
    )
    
    prompt = f"User Request: '{user_query}'"
    
    schema = {
        "type": "OBJECT",
        "properties": {
            "plan": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "agent": {"type": "STRING", "enum": ["INVENTORY", "SHIPPING", "GENERAL"]},
                        "instruction": {"type": "STRING"}
                    }
                }
            }
        }
    }

    try:
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(role="user", parts=[types.Part(text=system_prompt)]),
                types.Content(role="user", parts=[types.Part(text=prompt)])
            ],
            config=types.GenerateContentConfig(
                response_schema=schema,
                response_mime_type="application/json"
            )
        )
        return json.loads(res.text)
    except Exception as e:
        return {"plan": [{"agent": "GENERAL", "instruction": f"Error planning: {e}"}]}

# --- 2. Inventory Expert ---
def inventory_expert(instruction):
    system_prompt = (
        f"You are the Inventory Expert. You have access to `search_inventory`.\n"
        f"Use the tool to find product data requested in the instruction.\n"
        f"Return a summary of what you found (names, prices, stock)."
    )
    
    try:
        # Tool Call Step
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=instruction,
            config=types.GenerateContentConfig(
                tools=[tools.search_inventory],
                system_instruction=system_prompt
            )
        )
        
        if res.function_calls:
            fc = res.function_calls[0]
            if fc.name == 'search_inventory':
                tool_result = tools.search_inventory(**fc.args)
                
                # Final Summary Step
                res2 = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        types.Content(role="user", parts=[types.Part(text=instruction)]),
                        types.Content(role="model", parts=[types.Part(function_call=fc)]),
                        types.Content(role="user", parts=[types.Part(function_response=types.FunctionResponse(name=fc.name, response=tool_result))])
                    ],
                    config=types.GenerateContentConfig(system_instruction=system_prompt)
                )
                return res2.text
        else:
            return res.text
            
    except Exception as e:
        return f"Inventory Error: {e}"

# --- 3. Shipping Specialist ---
def shipping_specialist(instruction, context=""):
    """
    Calculates shipping based on rules and context (like item price).
    """
    system_prompt = (
        f"You are the Shipping Specialist.\n"
        f"RULES:\n"
        f"1. Standard Shipping is $10.\n"
        f"2. Orders over $100 get FREE SHIPPING.\n"
        f"3. Delivery time is 3-5 business days.\n"
        f"4. Use the provided 'Context' (previous agent outputs) to see if the item price qualifies for free shipping.\n"
        f"5. Answer the instruction based on these rules."
    )
    
    prompt = f"Context from other agents: {context}\n\nInstruction: {instruction}"
    
    try:
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(role="user", parts=[types.Part(text=system_prompt)]),
                types.Content(role="user", parts=[types.Part(text=prompt)])
            ]
        )
        return res.text
    except Exception as e:
        return f"Shipping Error: {e}"

# --- 4. Supervisor Synthesis ---
def synthesize_answer(user_query, research_results):
    """
    Combines all agent outputs into a final friendly response.
    """
    system_prompt = "You are the Lead Coordinator. Combine the reports from your agents into a helpful final answer for the user."
    
    prompt = f"User Query: {user_query}\n\nAgent Reports:\n{research_results}"
    
    res = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Content(role="user", parts=[types.Part(text=system_prompt)]),
            types.Content(role="user", parts=[types.Part(text=prompt)])
        ]
    )
    return res.text

# --- Main Orchestration Loop ---
def main():
    print("--- 🧠 Supervisor Agent System Online (Type 'quit' to exit) ---")
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['quit', 'exit']:
            break
            
        print("\n[1] Supervisor is Planning...")
        plan_data = supervisor_agent(user_input)
        plan = plan_data.get('plan', [])
        
        # Visualize the Plan
        print("    📋 Task List:")
        for i, task in enumerate(plan):
            print(f"       {i+1}. [{task['agent']}] {task['instruction']}")
            
        # Execute Plan
        results = []
        context_accumulator = "" # Passed down to subsequent agents
        
        print("\n[2] Executing Tasks...")
        for task in plan:
            agent = task['agent']
            instruction = task['instruction']
            output = ""
            
            if agent == 'INVENTORY':
                output = inventory_expert(instruction)
            elif agent == 'SHIPPING':
                # Pass accumulated context (e.g. price found by inventory)
                output = shipping_specialist(instruction, context=context_accumulator)
            elif agent == 'GENERAL':
                output = "General: I can help with that directly."
            
            print(f"    ✅ {agent} Finished: \"{output.strip()[:60]}...\"")
            context_accumulator += f"[{agent} Report]: {output}\n"
            results.append(f"[{agent}]: {output}")
            
        # Synthesize
        print("\n[3] Synthesizing Final Answer...")
        final_response = synthesize_answer(user_input, "\n".join(results))
        print(f"\n🤖 Supervisor: {final_response}")

if __name__ == "__main__":
    main()
