# tests/test_routes/test_chat_routes.py

import json
import os
import tempfile
from unittest.mock import patch, MagicMock
from src.chatbot_backend import create_app

# Assuming your conftest.py defines 'app_client' fixture

def test_root_endpoint(app_client):
    """Test the root endpoint for basic info."""
    client, _ = app_client
    response = client.get('/')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == "PDF Assistant Chatbot API"
    assert "version" in data
    assert "endpoints" in data

def test_health_check_success(app_client):
    """Test the /health endpoint when the agent is healthy."""
    client, mock_chatbot_agent = app_client
    mock_chatbot_agent.health_check.return_value = {
        "gemini_api": True,
        "pinecone_connection": True,
        "embeddings": True,
        "vector_store": True,
        "overall_health": True
    }
    response = client.get('/health')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['status'] == "success"
    assert data['healthy'] is True
    assert mock_chatbot_agent.health_check.called

def test_health_check_failure(app_client):
    """Test the /health endpoint when the agent is unhealthy."""
    client, mock_chatbot_agent = app_client
    mock_chatbot_agent.health_check.return_value = {
        "gemini_api": False,
        "pinecone_connection": True,
        "embeddings": True,
        "vector_store": True,
        "overall_health": False
    }
    response = client.get('/health')
    assert response.status_code == 503 # Service Unavailable
    data = json.loads(response.data)
    assert data['status'] == "success" # Still success for the endpoint call, but unhealthy=False
    assert data['healthy'] is False
    assert mock_chatbot_agent.health_check.called

def test_health_check_agent_not_initialized(mocker):
    """Test /health when ChatbotAgent fails to initialize during app creation."""
    mocker.patch('src.chatbot_backend.__init__.ChatbotAgent', side_effect=Exception("Init error"))
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        response = client.get('/health')
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['status'] == "error"
        assert "not initialized" in data['message']

def test_answer_question_success(app_client):
    """Test the /answer endpoint with a valid query."""
    client, mock_chatbot_agent = app_client
    mock_chatbot_agent.answer_question.return_value = {
        "answer": "This is a test answer.",
        "success": True,
        "context_found": True,
        "num_sources": 1,
        "error": None
    }
    response = client.post('/answer', json={'query': 'What is the event?'})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['answer'] == "This is a test answer."
    mock_chatbot_agent.answer_question.assert_called_once_with('What is the event?')

def test_answer_question_empty_query(app_client):
    """Test /answer with an empty query."""
    client, _ = app_client
    response = client.post('/answer', json={'query': ''})
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "provide a valid question" in data['answer']

def test_answer_question_no_json(app_client):
    """Test /answer with no JSON data."""
    client, _ = app_client
    response = client.post('/answer', data='not json') # Send plain text
    assert response.status_code == 400
    data = json.loads(response.data)
    assert "Invalid request format" in data['answer']

def test_answer_question_agent_failure(app_client):
    """Test /answer when the chatbot agent encounters an internal error."""
    client, mock_chatbot_agent = app_client
    mock_chatbot_agent.answer_question.side_effect = Exception("Internal agent error")
    response = client.post('/answer', json={'query': 'What is the event?'})
    assert response.status_code == 500
    data = json.loads(response.data)
    assert "encountered an error" in data['answer']

def test_upload_pdf_success(app_client):
    """Test the /uploadpdf endpoint with a valid PDF file."""
    client, mock_chatbot_agent = app_client
    mock_chatbot_agent.upload_data.return_value = True # Renamed from upload_pdf in the agent

    # Create a dummy PDF file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
        temp_pdf.write(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Count 0>>endobj\nxref\n0 3\n0000000000 65535 f\n0000000009 00000 n\n0000000074 00000 n\ntrailer<</Size 3/Root 1 0 R>>startxref\n106\n%%EOF")
        temp_pdf_path = temp_pdf.name

    try:
        with open(temp_pdf_path, 'rb') as f:
            response = client.post('/uploadpdf', data={
                'file': (f, 'test_document.pdf')
            })
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert "uploaded and processed successfully" in data['message']
        mock_chatbot_agent.upload_data.assert_called_once() # Check if agent method was called
        # You might add checks for the arguments passed to upload_data here
    finally:
        os.unlink(temp_pdf_path) # Clean up the dummy file

def test_upload_pdf_invalid_file_type(app_client):
    """Test /uploadpdf with an invalid file type (e.g., .txt)."""
    client, _ = app_client
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_txt:
        temp_txt.write(b"This is a text file.")
        temp_txt_path = temp_txt.name

    try:
        with open(temp_txt_path, 'rb') as f:
            response = client.post('/uploadpdf', data={
                'file': (f, 'invalid_document.txt')
            })
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['success'] is False
        assert "Only PDF files are allowed" in data['message']
    finally:
        os.unlink(temp_txt_path)

def test_upload_pdf_no_file(app_client):
    """Test /uploadpdf without providing a file."""
    client, _ = app_client
    response = client.post('/uploadpdf') # No file in data
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert "No file provided" in data['message']

def test_upload_pdf_empty_filename(app_client):
    """Test /uploadpdf with an empty filename (e.g., if user selected no file)."""
    client, _ = app_client
    response = client.post('/uploadpdf', data={
        'file': (MagicMock(), '') # Mock file with empty filename
    })
    assert response.status_code == 400
    data = json.loads(response.data)
    assert data['success'] is False
    assert "No file selected" in data['message']

def test_upload_pdf_too_large(mocker, app_client):
    """Test /uploadpdf with a file exceeding the maximum size."""
    client, _ = app_client
    # Patch MAX_FILE_SIZE for this test to a small value
    mocker.patch('src.chatbot_backend.config.Config.MAX_FILE_SIZE', 100) # 100 bytes

    # Create a dummy file larger than 100 bytes
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
        temp_pdf.write(b"a" * 200) # 200 bytes
        temp_pdf_path = temp_pdf.name
    
    try:
        with open(temp_pdf_path, 'rb') as f:
            response = client.post('/uploadpdf', data={
                'file': (f, 'large_doc.pdf')
            })
        assert response.status_code == 413
        data = json.loads(response.data)
        assert data['success'] is False
        assert "File too large" in data['message']
    finally:
        os.unlink(temp_pdf_path)

def test_upload_pdf_agent_processing_failure(app_client):
    """Test /uploadpdf when the agent fails to process the PDF."""
    client, mock_chatbot_agent = app_client
    mock_chatbot_agent.upload_data.return_value = False # Agent signals failure

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_pdf:
        temp_pdf.write(b"%PDF-1.4\n")
        temp_pdf_path = temp_pdf.name

    try:
        with open(temp_pdf_path, 'rb') as f:
            response = client.post('/uploadpdf', data={
                'file': (f, 'fail_doc.pdf')
            })
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['success'] is False
        assert "Failed to process the PDF file" in data['message']
    finally:
        os.unlink(temp_pdf_path)

