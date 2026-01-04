import os
import json
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
import tools

load_dotenv()

client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))

# --- Agent 1: Support Agent ---
def support_agent(user_query, expert_response=None):
    """
    Front-line agent. Decides if it can handle the query or needs the Expert.
    """
    
    context = ""
    if expert_response:
        context = f"Internal Context from Inventory Expert: '{expert_response}'\n\n"

    system_prompt = (
        f"You are a helpful Customer Support Agent for a tech store. "
        f"Your goal is to answer user questions politely.\n"
        f"RULES:\n"
        f"1. If the user asks general questions (greeting, hours, return policy), answer directly.\n"
        f"2. If the user asks about SPECIFIC PRODUCTS (stock, price, searching), you DO NOT have access to the database.\n"
        f"   - You MUST ask the Inventory Expert for help.\n"
        f"   - Return a JSON object: {{ 'target': 'EXPERT', 'request': '...' }}\n"
        f"3. If you have received context from the Inventory Expert, use it to answer the user.\n"
        f"   - Return a JSON object: {{ 'target': 'USER', 'message': '...' }}\n"
        f"4. For general chat, return: {{ 'target': 'USER', 'message': '...' }}\n"
        f"5. Return ONLY Raw JSON."
    )
    
    prompt = f"{context}User Query: '{user_query}'"

    schema = {
        "type": "OBJECT",
        "properties": {
            "target": {"type": "STRING", "enum": ["USER", "EXPERT"]},
            "request": {"type": "STRING", "nullable": True},
            "message": {"type": "STRING", "nullable": True}
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
        return {"target": "USER", "message": f"Error in Support Agent: {e}"}

# --- Agent 2: Inventory Expert ---
def inventory_expert(request):
    """
    Back-end agent. Has access to tools.
    """
    system_prompt = (
        f"You are the Inventory Expert. You have access to the `search_inventory` tool.\n"
        f"Your job is to receive a request from the Support Agent, use the tool to find data, and summarize it for the Support Agent.\n"
        f"You do NOT talk to the user directly."
    )
    
    # Simple tool usage loop (Orchestrated manually for simplicity)
    # 1. Decide if tool is needed
    try:
        # Step 1: Tool Call
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=request, # Treat request as the user prompt for this agent
            config=types.GenerateContentConfig(
                tools=[tools.search_inventory],
                system_instruction=system_prompt
            )
        )
        
        # Check for tool call
        if res.function_calls:
            fc = res.function_calls[0]
            # print(f"  [Expert] DEBUG: Calling Tool {fc.name}...")
            if fc.name == 'search_inventory':
                tool_result = tools.search_inventory(**fc.args)
                
                # Step 2: Final Summary
                res2 = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[
                        types.Content(role="user", parts=[types.Part(text=request)]),
                        types.Content(role="model", parts=[types.Part(function_call=fc)]),
                        types.Content(role="user", parts=[types.Part(function_response=types.FunctionResponse(name=fc.name, response=tool_result))])
                    ],
                    config=types.GenerateContentConfig(system_instruction=system_prompt)
                )
                return res2.text
        else:
            return res.text # Just answer logic
            
    except Exception as e:
        return f"Error in Expert: {e}"

# --- Main Orchestrator ---
def main():
    print("--- Agent System Online (Type 'quit' to exit) ---")
    print("Support Agent: Ready\nInventory Expert: Ready\n")
    
    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ['quit', 'exit']:
            break
            
        # 1. Send to Support Agent
        action = support_agent(user_input)
        
        if action['target'] == 'EXPERT':
            print(f"\n[🔄 Handshake] Support Agent -> Inventory Expert: \"{action['request']}\"")
            
            # 2. Call Expert
            expert_reply = inventory_expert(action['request'])
            
            print(f"[✅ Handshake] Inventory Expert -> Support Agent: \"{expert_reply.strip()[:100]}...\"")
            
            # 3. Support Agent Final Reply
            final_action = support_agent(user_input, expert_response=expert_reply)
            print(f"\nSupport Agent: {final_action.get('message', 'Error')}")
            
        else:
            # Direct reply
            print(f"\nSupport Agent: {action.get('message', 'Error')}")

if __name__ == "__main__":
    main()
