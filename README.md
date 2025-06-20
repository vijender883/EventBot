# PDF Assistant Chatbot - Flask Backend

A Flask-based backend service that integrates with Google Gemini AI and Pinecone vector database to create an intelligent PDF document assistant. Users can upload PDF files and ask questions about their content using natural language.

## 🚀 Features

- **PDF Document Processing**: Upload and process PDF files into searchable vectors
- **AI-Powered Q&A**: Ask questions about uploaded PDFs using Google Gemini AI
- **Vector Search**: Efficient document retrieval using Pinecone vector database
- **Resume Support**: Special handling for resume/CV documents
- **RESTful API**: Clean REST endpoints for integration with frontend applications
- **Health Monitoring**: Built-in health checks and logging

## 📋 Prerequisites

- Python 3.8 or higher
- Google AI Studio account (for Gemini API)
- Pinecone account
- Git

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/vijender883/Chatbot_Pinecone_flask_backend
cd Chatbot_Pinecone_flask_backend
```

### 2. Create and Activate Virtual Environment

#### Windows Command Prompt
```cmd
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Verify activation (should show (venv) in prompt)
```

#### Windows PowerShell
```powershell
# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\Activate.ps1

# If you get execution policy error, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Then try activation again
venv\Scripts\Activate.ps1

# Verify activation (should show (venv) in prompt)
```

#### macOS/Linux
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Verify activation (should show (venv) in prompt)
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## 🔑 API Keys Setup

### Get Google Gemini API Key

1. **Visit Google AI Studio**
   - Go to [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey)
   - Sign in with your Google account

2. **Create API Key**
   - Click "Create API Key"
   - Choose "Create API key in new project" or select existing project
   - Copy the generated API key

3. **Important Notes**
   - Keep your API key secure and never commit it to version control
   - The API key format looks like: `AIzaSyC...`
   - Free tier includes generous usage limits

### Get Pinecone API Key and Create Index

1. **Sign up for Pinecone**
   - Go to [https://www.pinecone.io/](https://www.pinecone.io/)
   - Create a free account
   - Verify your email

2. **Get API Key**
   - Log into Pinecone console
   - Go to "API Keys" section
   - Copy your API key (format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

3. **Create a New Index**
   - In Pinecone console, click "Create Index"
   - **Index Name**: Choose a name (e.g., `pdf-assistant-index`)
   - **Dimensions**: Set to `768` (required for Gemini embeddings)
   - **Metric**: Select `cosine`
   - **Cloud Provider**: Choose `AWS` or `GCP`
   - **Region**: Select closest to your location (e.g., `us-east-1`)
   - Click "Create Index"

4. **Note Your Settings**
   - Index name
   - Cloud provider
   - Region

## ⚙️ Environment Configuration

### 1. Create .env File

Copy the template and create your environment file:

```bash
cp .env.template .env
```

### 2. Configure .env File

Open `.env` file and update with your actual values:

```env
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
```

### 3. Verify Configuration

```bash
# Test your configuration
python -c "
from dotenv import load_dotenv
import os
load_dotenv()
print('GEMINI_API_KEY:', 'Set' if os.getenv('GEMINI_API_KEY') else 'Missing')
print('PINECONE_API_KEY:', 'Set' if os.getenv('PINECONE_API_KEY') else 'Missing')
print('PINECONE_INDEX:', os.getenv('PINECONE_INDEX'))
"
```

## 🚀 Running Locally

### 1. Start the Flask Server

```bash
# Make sure virtual environment is activated
python app.py
```

The server will start on `http://localhost:5000`

### 2. Test the API

#### Health Check
```bash
curl http://localhost:5000/health
```

#### Upload a PDF
```bash
curl -X POST -F "file=@your_document.pdf" http://localhost:5000/uploadpdf
```

#### Ask a Question
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "What is this document about?"}' \
  http://localhost:5000/answer
```

## 📡 API Endpoints

| Endpoint | Method | Description |
|----------|---------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/uploadpdf` | POST | Upload PDF file |
| `/answer` | POST | Ask questions about uploaded content |

### Upload PDF Example

```bash
curl -X POST \
  -F "file=@document.pdf" \
  http://localhost:5000/uploadpdf
```

### Question Example

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the main topics covered?"}' \
  http://localhost:5000/answer
```

## 🌐 Deploy to Render.com

### 1. Prepare for Deployment

Ensure your code is in a GitHub repository:

```bash
git add .
git commit -m "Ready for deployment"
git push origin main
```

### 2. Create Render Account

1. Go to [render.com](https://render.com)
2. Sign up using GitHub
3. Connect your GitHub account

### 3. Create Web Service

1. Click "New +" → "Web Service"
2. Connect your GitHub repository
3. Select your repository

### 4. Configure Service

**Basic Settings:**
- **Name**: `pdf-assistant-backend`
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app`

### 5. Set Environment Variables

In Render dashboard, go to "Environment" and add:

```
GEMINI_API_KEY=your_actual_gemini_key
PINECONE_API_KEY=your_actual_pinecone_key
PINECONE_INDEX=your_index_name
PINECONE_CLOUD=aws
PINECONE_REGION=us-east-1
FLASK_ENV=production
```

### 6. Deploy

1. Click "Create Web Service"
2. Wait for deployment (5-10 minutes)
3. Your app will be available at: `https://your-service-name.onrender.com`

### 7. Test Deployment

```bash
# Test health endpoint
curl https://your-service-name.onrender.com/health

# Test with your frontend application
```

## 🔧 Development

### Project Structure

```
pdf-assistant-backend/
├── app.py              # Main Flask application
├── requirements.txt    # Python dependencies
├── .env.template      # Environment template
├── .env               # Your environment variables (not in git)
├── .gitignore         # Git ignore file
├── start.sh           # Render start script
└── README.md          # This file
```

### Key Components

- **EventBot Class**: Core AI functionality
- **Flask Routes**: API endpoints
- **PDF Processing**: Document chunking and embedding
- **Vector Search**: Pinecone integration
- **Error Handling**: Comprehensive error management

## 🛠️ Troubleshooting

### Common Issues

**1. Import Errors**
```bash
# Ensure virtual environment is activated
# Reinstall dependencies
pip install -r requirements.txt
```

**2. API Key Issues**
```bash
# Verify .env file exists and has correct values
# Check for extra spaces or quotes around keys
```

**3. Pinecone Connection**
```bash
# Verify index name, region, and cloud provider
# Check if index exists in Pinecone console
```

**4. PDF Processing Fails**
```bash
# Ensure PDF is not corrupted
# Check file size (max 50MB)
# Verify PDF contains extractable text
```

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python app.py
```

## 📊 Monitoring

### Health Checks

The `/health` endpoint provides system status:

```json
{
  "status": "success",
  "health": {
    "gemini_api": true,
    "pinecone_connection": true,
    "embeddings": true,
    "vector_store": true,
    "overall_health": true
  },
  "healthy": true
}
```

### Logs

Monitor application logs for:
- PDF upload status
- Question processing
- API errors
- Performance metrics

## 🔒 Security

- API keys stored in environment variables
- File upload validation
- Secure filename handling
- CORS configuration
- Request size limits

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📞 Support

For issues and questions:
- Create an issue on GitHub
- Check the troubleshooting section
- Review Render.com documentation for deployment issues

---

**Happy coding! 🚀**