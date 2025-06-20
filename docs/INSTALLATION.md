# Installation Guide for PDF Assistant Chatbot (Flask Backend)

This guide will walk you through the process of setting up and running the PDF Assistant Chatbot Flask backend locally.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

* **Python 3.8 or higher**: You can download it from [python.org](https://www.python.org/downloads/).
* **Git**: For cloning the repository. You can download it from [git-scm.com](https://git-scm.com/downloads).
* **Google AI Studio account**: For obtaining a Gemini API key.
* **Pinecone account**: For obtaining a Pinecone API key and setting up an index.

## 🛠️ Installation & Setup

### 1. Clone the Repository

Open your terminal or command prompt and clone the repository:

```bash
git clone [https://github.com/vijender883/Chatbot_Pinecone_flask_backend](https://github.com/vijender883/Chatbot_Pinecone_flask_backend)
cd Chatbot_Pinecone_flask_backend
```

2. Create and Activate a Virtual Environment

It's highly recommended to use a virtual environment to manage dependencies and avoid conflicts with other Python projects.
Windows Command Prompt
DOS

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Verify activation (you should see "(venv)" at the beginning of your prompt)

Windows PowerShell
PowerShell

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\Activate.ps1

# If you encounter an execution policy error, run this command first and then try activation again:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Verify activation (you should see "(venv)" at the beginning of your prompt)

macOS/Linux
```bash

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Verify activation (you should see "(venv)" at the beginning of your prompt)
```
3. Install Dependencies

Once your virtual environment is activated, install the required Python packages:
```bash

pip install -r requirements.txt
```
This command will install all the necessary libraries listed in your requirements.txt file, including Flask, Google Generative AI, Pinecone, and LangChain components. 

🔑 API Keys Setup

The PDF Assistant Chatbot requires API keys for Google Gemini and Pinecone.
Get Google Gemini API Key

    Visit Google AI Studio: Go to https://makersuite.google.com/app/apikey.
    Sign in: Use your Google account.
    Create API Key: Click "Create API Key" and choose to create a key in a new or existing project.
    Copy the generated API key.

Get Pinecone API Key and Create Index

    Sign up for Pinecone: Go to https://www.pinecone.io/ and create a free account.
    Get API Key: Log into the Pinecone console, go to the "API Keys" section, and copy your API key.
    Create a New Index:
        In the Pinecone console, click "Create Index".
        Index Name: Choose a name (e.g., pdf-assistant-index).
        Dimensions: Set to 768 (required for Gemini embeddings).
        Metric: Select cosine.
        Cloud Provider: Choose AWS or GCP.
        Region: Select the region closest to your location (e.g., us-east-1).
        Click "Create Index".

⚙️ Environment Configuration
1. Create .env File

Copy the template and create your environment file:
```bash

cp .env.template .env
```
2. Configure .env File

Open .env file and update with your actual values:
Code snippet

# Flask Configuration
FLASK_ENV=development
PORT=5000

# API Keys (Replace with your actual keys)
GEMINI_API_KEY=AIzaSyC...your_actual_gemini_key
PINECONE_API_KEY=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx

# Pinecone Configuration
PINECONE_INDEX=pdf-assistant-index
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1

# Optional: Logging
LOG_LEVEL=INFO

🚀 Running Locally
1. Start the Flask Server
```bash

# Make sure virtual environment is activated
python app.py
```
The server will start on http://localhost:5000.
2. Test the API
Health Check
```bash

curl http://localhost:5000/health
```
Upload a PDF
```bash

curl -X POST -F "file=@your_document.pdf" http://localhost:5000/uploadpdf
```
Ask a Question
```bash

curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this document about?"}' \
  http://localhost:5000/answer
```