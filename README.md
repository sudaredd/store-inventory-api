# Store Inventory API

A Flask-based API for managing store inventory, powered by SQLite and Google Gemini AI.

## Features
- **Persistent Storage**: Uses SQLite (`inventory.db`) to store products.
- **AI Descriptions**: Generates high-end marketing copy for products using Google Gemini AI.
- **Inventory Chat**: Ask questions about your entire stock context.
- **Smart Fallback**: Reliable AI generation that automatically handles rate limits (429) and missing models (404) by retrying with alternative models (`gemini-1.5-flash` → `gemini-2.5-flash-lite` → `models/gemini-flash-latest`), with a 1-second delay for stability.
- **RESTful Endpoints**: Standard GET/POST endpoints for management.

## Setup

### 1. Install Dependencies
The project uses the modern `google-genai` SDK.
```bash
pip install -r requirements.txt
```

### 2. Configure API Key
1.  Copy `.env.example` to `.env`.
2.  Add your Google Gemini API key to `.env`:
    ```ini
    GEMINI_API_KEY=your_key_here
    ```
    [Get your API key here](https://aistudio.google.com/api-keys).

### 3. Initialize Database
Run the initialization script to create the database and seed it with sample data:
```bash
python init_db.py
```

### 4. Run the Application
```bash
python main.py
```
The server will start on `http://127.0.0.1:8080`.

## API Endpoints

### 1. List Products
**GET** `/products`

```bash
curl http://127.0.0.1:8080/products
```

### 2. Add Product
**POST** `/products`

```bash
curl -X POST -H "Content-Type: application/json" -d "{\"name\": \"Pixel Watch\", \"price\": 349.99}" http://127.0.0.1:8080/products
```

### 3. Search Products
**GET** `/search?q=name`

```bash
curl "http://127.0.0.1:8080/search?q=pixel"
```

### 4. Generate AI Description
**POST** `/describe/<id>`

Generates a luxury marketing description for the product.

```bash
curl -X POST http://127.0.0.1:8080/describe/1
```

### 5. Inventory Chat
**GET** `/inventory-chat?q=question`

Ask questions about the current stock.

```bash
curl "http://127.0.0.1:8080/inventory-chat?q=What+is+the+cheapest+item"
```
