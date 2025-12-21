# Store Inventory API

A Flask-based API for managing store inventory, powered by SQLite and Google Gemini AI.

## Features
- **Persistent Storage**: Uses SQLite (`inventory.db`) to store products.
- **AI Descriptions**: Generates high-end marketing copy for products using Google Gemini AI.
- **RESTful Endpoints**: Standard GET/POST endpoints for management.

## Setup

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API Key
You need a Google Gemini API key to use the AI features. [Get your API key here](https://aistudio.google.com/api-keys).

Set it as an environment variable:

**PowerShell (Windows):**
```powershell
$env:GEMINI_API_KEY = "your_api_key_here"
```

**Bash (Linux/Mac/Git Bash):**
```bash
export GEMINI_API_KEY="your_api_key_here"
```

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
