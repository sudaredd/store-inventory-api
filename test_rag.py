from tools import search_inventory
import json

def test_rag():
    print("Testing RAG Search...")
    query = "cheap professional laptop"
    print(f"Query: '{query}'")
    
    results = search_inventory(query)
    
    print(f"\nFound {len(results)} results:")
    for res in results:
        print(f"- {res}")

if __name__ == "__main__":
    test_rag()
