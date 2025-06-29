
# 📦 Retail Inventory Event Analyzer

A containerized Streamlit application that interacts with multiple backend APIs to assist users in analyzing inventory events in a retail environment. Built using LangChain and OpenAI, this app can extract user intents and interact with services like Product Events API, DC Events API, and Stock On Hand API.

---

## 🚀 Features

- Natural language interface to query and manage inventory.
- Uses LangChain and LLMs to extract user intent and parameters.
- Interacts with backend services to:
  - Retrieve product and DC events.
  - Analyze stock-on-hand information.
  - Set stock values based on user input.
- Fully containerized using Docker and orchestrated via Docker Compose.

---

## 🧱 Project Structure

```plaintext
.
├── app.py                  # Streamlit application entry point
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker setup for Streamlit app
├── docker-compose.yml      # Multi-container orchestration
└── .env                    # (Optional) Environment variables file
```

---

## 🐳 Running the Application

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd <your-project-folder>
```

### 2. Prepare Environment

Create a `.env` file if needed for OpenAI authentication

### 3. Launch with Docker Compose

```bash
docker-compose up --build
```

Once containers are running, access the app at: [http://localhost:8501](http://localhost:8501)

---

## ⚙️ Environment Variables

The `docker-compose.yml` file configures the following key environment variables:

- `PRODUCT_EVENTS_API_URL`: URL for the product event service
- `DC_EVENTS_API_URL`: URL for the DC event service
- `SOH_API_URL`: URL for setting stock on hand

---

## 📦 Dependencies

From `requirements.txt`:

- `streamlit`
- `langchain`
- `openai`
- `transformers`
- `requests`
- `langchain_community`
- `tensorflow`

---

## 🔧 Backend Services

This project depends on the following APIs, each defined as services in `docker-compose.yml`:

- **Product Events API** (port 8000)
- **DC Events API** (port 8001)
- **Set Stock On Hand API** (port 8002)

Each of these APIs must be available at the paths specified in `docker-compose.yml`.

---

## 👨‍💻 Author

**Paramasivan Dorai**
