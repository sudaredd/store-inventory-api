import urllib.request
import json
import urllib.parse
import sys

def test_chat(question):
    print(f"Question: {question}")
    encoded_question = urllib.parse.quote(question)
    url = f'http://127.0.0.1:8080/inventory-chat?q={encoded_question}'
    
    try:
        req = urllib.request.Request(url, method='GET')
        with urllib.request.urlopen(req) as response:
            status = response.status
            print(f"Status: {status}")
            data = json.loads(response.read().decode('utf-8'))
            
            if 'answer' in data:
                print("\n--- AI Answer ---")
                print(data['answer'])
                print("-----------------\n")
            else:
                print("\nResponse:", data)
                
    except urllib.error.HTTPError as e:
        print(f"Error: HTTP {e.code}")
        print(e.read().decode('utf-8'))
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_chat("What is the most expensive item?")
    test_chat("Do you have any pixel devices?")
