import unittest
import json
from main import app
from database import get_all_inventory_text

class StoreApiTests(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_get_products(self):
        response = self.app.get('/products')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(isinstance(data, list))
        self.assertTrue(len(data) >= 2) # Should have initial data

    def test_add_product(self):
        new_product = {"name": "Test Item", "price": 10.50}
        response = self.app.post('/products', json=new_product)
        self.assertEqual(response.status_code, 201)
        data = json.loads(response.data)
        self.assertEqual(data['name'], "Test Item")
        self.assertIn('id', data)

    def test_search_product(self):
        # Add a unique item to search for
        import time
        unique_name = f"UniqueWidget_{int(time.time())}"
        self.app.post('/products', json={"name": unique_name, "price": 50.0})
        
        response = self.app.get(f'/search?q={unique_name}')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], unique_name)

    def test_search_empty(self):
        response = self.app.get('/search?q=NonExistentThing')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(len(data), 0)

    def test_context_dumper(self):
        """Test that the context dumper returns a string containing seed data."""
        text = get_all_inventory_text()
        self.assertIsInstance(text, str)
        self.assertIn("Google Pixel", text)

if __name__ == '__main__':
    unittest.main()
