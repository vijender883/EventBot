# tests/conftest.py

import pytest
import os
from unittest.mock import MagicMock

# Import necessary components from your application
from src.chatbot_backend import create_app
from src.chatbot_backend.agents.rag_agent import ChatbotAgent
from src.chatbot_backend.config import Config

@pytest.fixture(scope='session', autouse=True)
def setup_test_env_vars():
    """
    Fixture to ensure environment variables for testing are set.
    This helps prevent the actual ChatbotAgent from trying to connect
    to real external services during app client tests where it's mocked.
    For agent tests, we'll mock individual components.
    """
    os.environ['GEMINI_API_KEY'] = 'test_gemini_key'
    os.environ['PINECONE_API_KEY'] = 'test_pinecone_key'
    os.environ['PINECONE_INDEX'] = 'test-index'
    os.environ['FLASK_ENV'] = 'testing'
    
    # Reload Config to pick up the test environment variables
    # This might be needed if Config was loaded before this fixture ran.
    # In practice, for Flask apps initialized *after* fixtures, this is less critical.
    # Config.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
    # Config.PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    # Config.PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX")
    
    # Yield control to tests
    yield
    
    # Clean up environment variables after tests
    del os.environ['GEMINI_API_KEY']
    del os.environ['PINECONE_API_KEY']
    del os.environ['PINECONE_INDEX']
    del os.environ['FLASK_ENV']

@pytest.fixture(scope='function')
def app_client(mocker):
    """
    Fixture for a Flask test client with a mocked ChatbotAgent.
    
    This fixture ensures that when testing Flask routes, the actual
    ChatbotAgent's external dependencies (Gemini, Pinecone) are NOT
    called. Instead, we control its behavior through mocks.
    """
    # Create a mock for the ChatbotAgent instance
    mock_chatbot_agent = mocker.Mock(spec=ChatbotAgent)
    
    # Ensure __init__ doesn't try to connect to real services
    # We mock out the internal initialization methods.
    mock_chatbot_agent._initialize_pinecone = MagicMock()
    mock_chatbot_agent._initialize_gemini = MagicMock()
    mock_chatbot_agent._initialize_embeddings = MagicMock()
    mock_chatbot_agent._validate_credentials = MagicMock() # Mock validation
    mock_chatbot_agent._setup_prompt_template = MagicMock() # Mock prompt setup

    # When create_app is called, we want it to use our mocked agent.
    # We will patch the ChatbotAgent class during app creation.
    mocker.patch('src.chatbot_backend.agents.rag_agent.ChatbotAgent', return_value=mock_chatbot_agent)
    
    # Patch the initialization of ChatbotAgent in __init__.py directly
    # This ensures that `app.chatbot_agent` gets our mock.
    mocker.patch('src.chatbot_backend.__init__.ChatbotAgent', return_value=mock_chatbot_agent)

    app = create_app()
    app.config['TESTING'] = True
    
    # Explicitly assign the mock to the app context if needed (though patching should handle it)
    app.chatbot_agent = mock_chatbot_agent 

    with app.test_client() as client:
        yield client, mock_chatbot_agent

@pytest.fixture
def mock_chatbot_agent_instance(mocker):
    """
    Fixture to provide a mocked ChatbotAgent instance for direct agent testing.
    This fixture is specifically for tests *of the ChatbotAgent itself*,
    where you want to mock its internal dependencies (Pinecone, Gemini, Langchain components)
    rather than mocking the agent itself.
    """
    # Mock external library components that ChatbotAgent depends on
    mocker.patch('pinecone.Pinecone')
    mocker.patch('google.generativeai.configure')
    mocker.patch('google.generativeai.GenerativeModel')
    mocker.patch('langchain_google_genai.GoogleGenerativeAIEmbeddings')
    mocker.patch('langchain_pinecone.PineconeVectorStore')
    mocker.patch('langchain_community.document_loaders.PyPDFLoader')
    mocker.patch('langchain.text_splitter.RecursiveCharacterTextSplitter')
    mocker.patch('langchain.prompts.ChatPromptTemplate')

    # Ensure environment variables are set for the agent's __init__ to pass Config validation
    os.environ['GEMINI_API_KEY'] = 'test_gemini_key'
    os.environ['PINECONE_API_KEY'] = 'test_pinecone_key'
    os.environ['PINECONE_INDEX'] = 'test-index'

    agent = ChatbotAgent()
    
    # Clean up env vars after agent is initialized to prevent side effects in other tests
    del os.environ['GEMINI_API_KEY']
    del os.environ['PINECONE_API_KEY']
    del os.environ['PINECONE_INDEX']

    yield agent

