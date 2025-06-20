# tests/test_agents/test_chatbot_agent.py

import pytest
import os
from unittest.mock import MagicMock, patch, mock_open

# Import the ChatbotAgent and Config directly for testing
from src.chatbot_backend.agents.rag_agent import ChatbotAgent
from src.chatbot_backend.config import Config

# The 'mock_chatbot_agent_instance' fixture from conftest.py will mock external dependencies
# and provide a ChatbotAgent instance ready for testing its methods.

def test_chatbot_agent_initialization_success(mocker):
    """Test ChatbotAgent initializes successfully when all dependencies are mocked."""
    # Mock all external dependencies to ensure __init__ runs without actual calls
    mocker.patch('pinecone.Pinecone')
    mocker.patch('google.generativeai.configure')
    mocker.patch('google.generativeai.GenerativeModel')
    mocker.patch('langchain_google_genai.GoogleGenerativeAIEmbeddings')
    mocker.patch('langchain_pinecone.PineconeVectorStore')
    mocker.patch('src.chatbot_backend.config.Config.validate_required_env_vars') # Mock this too

    # Temporarily set dummy env vars for initialization
    os.environ['GEMINI_API_KEY'] = 'dummy_gemini'
    os.environ['PINECONE_API_KEY'] = 'dummy_pinecone'
    os.environ['PINECONE_INDEX'] = 'dummy-index'

    try:
        agent = ChatbotAgent()
        assert agent is not None
        # Verify that the mocked initialization methods were called
        agent._validate_credentials.assert_called_once()
        agent._initialize_pinecone.assert_called_once()
        agent._initialize_gemini.assert_called_once()
        agent._initialize_embeddings.assert_called_once()
        agent._setup_prompt_template.assert_called_once()
    finally:
        del os.environ['GEMINI_API_KEY']
        del os.environ['PINECONE_API_KEY']
        del os.environ['PINECONE_INDEX']

def test_chatbot_agent_initialization_missing_env_vars(mocker):
    """Test ChatbotAgent raises ValueError if required env vars are missing."""
    # Unset critical env vars for this specific test
    if 'GEMINI_API_KEY' in os.environ: del os.environ['GEMINI_API_KEY']
    if 'PINECONE_API_KEY' in os.environ: del os.environ['PINECONE_API_KEY']
    if 'PINECONE_INDEX' in os.environ: del os.environ['PINECONE_INDEX']

    # We need to explicitly re-patch validate_required_env_vars if it's already been loaded.
    # For a clean test, it's better if this test runs before other modules requiring it.
    # Or, you can patch the specific methods within _validate_credentials if it uses them.
    mocker.patch('src.chatbot_backend.agents.rag_agent.Config.validate_required_env_vars', 
                 side_effect=ValueError("Missing required environment variables"))

    with pytest.raises(ValueError, match="Missing required environment variables"):
        ChatbotAgent()

def test_answer_question_with_context(mock_chatbot_agent_instance, mocker):
    """Test answer_question when relevant context is found."""
    agent = mock_chatbot_agent_instance
    
    # Mock similarity_search_with_score to return dummy documents
    mock_doc1 = MagicMock()
    mock_doc1.page_content = "The event is a tech conference."
    mock_doc2 = MagicMock()
    mock_doc2.page_content = "It will be held in New York."
    agent.vectorstore.similarity_search_with_score.return_value = [
        (mock_doc1, 0.9), (mock_doc2, 0.8)
    ]

    # Mock generate_content call
    mock_response = MagicMock()
    mock_response.text = "The tech conference will be held in New York."
    agent.llm.generate_content.return_value = mock_response

    result = agent.answer_question("Where is the conference?")

    assert result['success'] is True
    assert "tech conference will be held in New York" in result['answer']
    assert result['context_found'] is True
    assert result['num_sources'] == 2
    agent.vectorstore.similarity_search_with_score.assert_called_once_with("Where is the conference?", k=5)
    agent.llm.generate_content.assert_called_once() # We don't check prompt content here, that's integration

def test_answer_question_no_context(mock_chatbot_agent_instance, mocker):
    """Test answer_question when no context is found."""
    agent = mock_chatbot_agent_instance
    agent.vectorstore.similarity_search_with_score.return_value = [] # No results

    mock_response = MagicMock()
    mock_response.text = "I'm sorry, I don't have that specific information."
    agent.llm.generate_content.return_value = mock_response

    result = agent.answer_question("What is the secret ingredient?")

    assert result['success'] is True
    assert "I'm sorry, I don't have that specific information" in result['answer']
    assert result['context_found'] is False
    assert result['num_sources'] == 0
    agent.vectorstore.similarity_search_with_score.assert_called_once()
    agent.llm.generate_content.assert_called_once()

def test_answer_question_agent_error(mock_chatbot_agent_instance, mocker):
    """Test answer_question when an error occurs during processing."""
    agent = mock_chatbot_agent_instance
    agent.vectorstore.similarity_search_with_score.side_effect = Exception("DB connection error")

    result = agent.answer_question("Any question.")

    assert result['success'] is False
    assert "encountered an error" in result['answer']
    assert result['error'] == "DB connection error"
    assert result['context_found'] is False
    assert result['num_sources'] == 0

def test_upload_data_success(mock_chatbot_agent_instance, mocker):
    """Test upload_data successfully processes a PDF."""
    agent = mock_chatbot_agent_instance
    
    # Mock PyPDFLoader and its load method
    mock_pdf_loader = MagicMock()
    mock_doc = MagicMock()
    mock_doc.page_content = "PDF content chunk."
    mock_pdf_loader.load.return_value = [mock_doc]
    mocker.patch('langchain_community.document_loaders.PyPDFLoader', return_value=mock_pdf_loader)

    # Mock RecursiveCharacterTextSplitter and its split_documents method
    mock_splitter = MagicMock()
    mock_chunk = MagicMock()
    mock_chunk.page_content = "Split chunk."
    mock_splitter.split_documents.return_value = [mock_chunk]
    mocker.patch('langchain.text_splitter.RecursiveCharacterTextSplitter', return_value=mock_splitter)
    
    # Mock add_documents to vectorstore
    agent.vectorstore.add_documents.return_value = None # Doesn't return anything significant

    # Create a dummy file
    temp_file_path = "dummy.pdf"
    with patch('builtins.open', mock_open(read_data='dummy pdf data')), \
         patch('os.path.exists', return_value=True): # Simulate file existence
        success = agent.upload_data(temp_file_path, user_id="test_user")

    assert success is True
    mock_pdf_loader.load.assert_called_once()
    mock_splitter.split_documents.assert_called_once()
    agent.vectorstore.add_documents.assert_called_once()
    # Check metadata on the mocked chunk
    assert mock_chunk.metadata["userId"] == "test_user"
    assert mock_chunk.metadata["document_type"] == "resume"

def test_upload_data_no_content_from_pdf(mock_chatbot_agent_instance, mocker):
    """Test upload_data when PDF loader extracts no content."""
    agent = mock_chatbot_agent_instance
    mock_pdf_loader = MagicMock()
    mock_pdf_loader.load.return_value = [] # No documents loaded
    mocker.patch('langchain_community.document_loaders.PyPDFLoader', return_value=mock_pdf_loader)

    temp_file_path = "empty.pdf"
    with patch('builtins.open', mock_open(read_data='dummy pdf data')), \
         patch('os.path.exists', return_value=True):
        success = agent.upload_data(temp_file_path)

    assert success is False
    mock_pdf_loader.load.assert_called_once()
    agent.vectorstore.add_documents.assert_not_called() # Should not proceed to add documents

def test_upload_data_no_chunks_created(mock_chatbot_agent_instance, mocker):
    """Test upload_data when text splitter creates no chunks."""
    agent = mock_chatbot_agent_instance
    mock_pdf_loader = MagicMock()
    mock_doc = MagicMock()
    mock_doc.page_content = "Some content."
    mock_pdf_loader.load.return_value = [mock_doc]
    mocker.patch('langchain_community.document_loaders.PyPDFLoader', return_value=mock_pdf_loader)

    mock_splitter = MagicMock()
    mock_splitter.split_documents.return_value = [] # No chunks created
    mocker.patch('langchain.text_splitter.RecursiveCharacterTextSplitter', return_value=mock_splitter)

    temp_file_path = "no_chunks.pdf"
    with patch('builtins.open', mock_open(read_data='dummy pdf data')), \
         patch('os.path.exists', return_value=True):
        success = agent.upload_data(temp_file_path)

    assert success is False
    mock_pdf_loader.load.assert_called_once()
    mock_splitter.split_documents.assert_called_once()
    agent.vectorstore.add_documents.assert_not_called()

def test_upload_data_exception(mock_chatbot_agent_instance, mocker):
    """Test upload_data when an exception occurs during processing."""
    agent = mock_chatbot_agent_instance
    # Simulate an error during PDF loading
    mocker.patch('langchain_community.document_loaders.PyPDFLoader', side_effect=Exception("PDF parsing error"))

    temp_file_path = "error.pdf"
    with patch('builtins.open', mock_open(read_data='dummy pdf data')), \
         patch('os.path.exists', return_value=True):
        success = agent.upload_data(temp_file_path)

    assert success is False
    agent.vectorstore.add_documents.assert_not_called()

def test_health_check_all_healthy(mock_chatbot_agent_instance, mocker):
    """Test health_check when all components are healthy."""
    agent = mock_chatbot_agent_instance
    
    # Mock responses for internal health checks
    mock_gemini_response = MagicMock()
    mock_gemini_response.text = "OK"
    agent.llm.generate_content.return_value = mock_gemini_response
    
    agent.index.describe_index_stats.return_value = {} # Any non-error return indicates success
    agent.embeddings.embed_query.return_value = [0.1, 0.2] # Non-empty list
    agent.vectorstore.similarity_search.return_value = [MagicMock()] # Some result

    status = agent.health_check()

    assert status["gemini_api"] is True
    assert status["pinecone_connection"] is True
    assert status["embeddings"] is True
    assert status["vector_store"] is True
    assert status["overall_health"] is True

def test_health_check_gemini_unhealthy(mock_chatbot_agent_instance, mocker):
    """Test health_check when Gemini API fails."""
    agent = mock_chatbot_agent_instance
    agent.llm.generate_content.side_effect = Exception("Gemini down")

    # Ensure other components would pass if called
    agent.index.describe_index_stats.return_value = {}
    agent.embeddings.embed_query.return_value = [0.1, 0.2]
    agent.vectorstore.similarity_search.return_value = [MagicMock()]

    status = agent.health_check()

    assert status["gemini_api"] is False
    assert status["overall_health"] is False # Overall should be false if any component fails

