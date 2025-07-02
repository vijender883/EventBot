# src/frontend/streamlit_app.py
import streamlit as st
import requests
import os
import logging
import traceback
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass
import json
from dotenv import load_dotenv
from datetime import datetime
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('chatbot_app.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

@dataclass
class ChatResponse:
    """Data class for API chat response"""
    answer: str

class AppError(Exception):
    """Base exception class for application errors"""
    def __init__(self, message: str, error_code: str = None, details: Dict = None):
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self.message)

class APIError(AppError):
    """Exception for API-related errors"""
    pass

class ValidationError(AppError):
    """Exception for validation errors"""
    pass

class ConfigurationError(AppError):
    """Exception for configuration errors"""
    pass

class ErrorHandler:
    """Centralized error handling and logging"""
    
    @staticmethod
    def log_error(error: Exception, context: str = "", user_message: str = None):
        """Log error with context and return user-friendly message"""
        error_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        # Log detailed error information
        logger.error(f"Error ID: {error_id}")
        logger.error(f"Context: {context}")
        logger.error(f"Error Type: {type(error).__name__}")
        logger.error(f"Error Message: {str(error)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Display user-friendly error in Streamlit
        if user_message:
            st.error(f"❌ {user_message}")
        else:
            st.error(f"❌ An error occurred. Error ID: {error_id}")
        
        # Show detailed error in debug mode
        if st.session_state.get('debug_mode', False):
            with st.expander(f"🐛 Debug Info (Error ID: {error_id})"):
                st.code(f"Error Type: {type(error).__name__}")
                st.code(f"Error Message: {str(error)}")
                st.code(f"Context: {context}")
                if hasattr(error, 'details') and error.details:
                    st.json(error.details)
        
        return error_id

class APIClient:
    """Handles all API communications with enhanced error handling"""
    
    def __init__(self):
        self.endpoint = self._validate_endpoint()
        self.session = requests.Session()
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'Streamlit-PDF-Chatbot/1.0'
        })
        
        # Test connection on initialization
        self._test_connection()
    
    def _validate_endpoint(self) -> str:
        """Validate and return the API endpoint"""
        endpoint = os.getenv('ENDPOINT')
        
        if not endpoint:
            error = ConfigurationError(
                "ENDPOINT environment variable not set",
                "MISSING_ENDPOINT",
                {"env_file_exists": os.path.exists('.env')}
            )
            ErrorHandler.log_error(
                error, 
                "API Client Initialization",
                "Configuration error: Please check your .env file"
            )
            raise error
        
        # Validate URL format
        if not endpoint.startswith(('http://', 'https://')):
            error = ConfigurationError(
                f"Invalid endpoint format: {endpoint}",
                "INVALID_ENDPOINT_FORMAT",
                {"endpoint": endpoint}
            )
            ErrorHandler.log_error(
                error,
                "API Client Initialization",
                "Invalid endpoint URL format in configuration"
            )
            raise error
        
        logger.info(f"API endpoint configured: {endpoint}")
        return endpoint.rstrip('/')
    
    def _test_connection(self):
        """Test basic connectivity to the API endpoint"""
        try:
            # Try a simple HEAD request to test connectivity
            response = requests.head(self.endpoint, timeout=5)
            logger.info(f"Connection test successful. Status: {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.warning(f"Connection test failed: {str(e)}")
            # Don't raise error here, just log the warning
    
    def send_query(self, query: str, pdf_uuid: str = None) -> Optional[ChatResponse]:
        """Send user query to the answer endpoint with comprehensive error handling"""
        if not query or not query.strip():
            error = ValidationError(
                "Query cannot be empty",
                "EMPTY_QUERY"
            )
            ErrorHandler.log_error(
                error,
                "Query Validation",
                "Please enter a valid question"
            )
            return None
        
        try:
            url = f"{self.endpoint}/answer"
            payload = {"query": query.strip()}
            if pdf_uuid:
                payload["pdf_uuid"] = pdf_uuid
            
            logger.info(f"Sending query to {url}")
            logger.debug(f"Query payload: {payload}")
            
            response = self.session.post(
                url,
                json=payload,
                timeout=30
            )
            
            logger.info(f"Response status: {response.status_code}")
            
            # Handle different HTTP status codes
            if response.status_code == 404:
                raise APIError(
                    "Answer endpoint not found",
                    "ENDPOINT_NOT_FOUND",
                    {"url": url, "status_code": response.status_code}
                )
            elif response.status_code == 500:
                raise APIError(
                    "Server error occurred",
                    "SERVER_ERROR",
                    {"url": url, "status_code": response.status_code}
                )
            elif response.status_code != 200:
                raise APIError(
                    f"Unexpected status code: {response.status_code}",
                    "UNEXPECTED_STATUS",
                    {"url": url, "status_code": response.status_code}
                )
            
            response.raise_for_status()
            
            # Parse JSON response
            try:
                data = response.json()
                logger.debug(f"Response data: {data}")
            except json.JSONDecodeError as e:
                raise APIError(
                    "Invalid JSON response from server",
                    "INVALID_JSON",
                    {"response_text": response.text[:500]}
                )
            
            # Validate response structure
            required_fields = ['answer']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                raise APIError(
                    f"Missing required fields in response: {missing_fields}",
                    "MISSING_RESPONSE_FIELDS",
                    {"missing_fields": missing_fields, "response_data": data}
                )
            
            # Create response object with only the answer field
            chat_response = ChatResponse(
                answer=data.get('answer', '')
            )
            
            logger.info("Query processed successfully")
            return chat_response
            
        except requests.exceptions.Timeout as e:
            error = APIError(
                "Request timed out",
                "TIMEOUT",
                {"timeout": 30, "url": url}
            )
            ErrorHandler.log_error(
                error,
                "API Query Request",
                "The request took too long. Please try again."
            )
            return None
            
        except requests.exceptions.ConnectionError as e:
            error = APIError(
                "Cannot connect to API server",
                "CONNECTION_ERROR",
                {"endpoint": self.endpoint}
            )
            ErrorHandler.log_error(
                error,
                "API Query Request",
                "Cannot connect to the server. Please check your internet connection."
            )
            return None
            
        except APIError:
            # Re-raise API errors as they're already handled
            raise
            
        except Exception as e:
            error = APIError(
                f"Unexpected error during query: {str(e)}",
                "UNEXPECTED_ERROR",
                {"error_type": type(e).__name__}
            )
            ErrorHandler.log_error(
                error,
                "API Query Request",
                "An unexpected error occurred. Please try again."
            )
            return None
    
    def upload_pdf(self, pdf_file) -> dict:
        """Upload PDF file to the server with enhanced error handling"""
        try:
            # Validate file
            if not pdf_file:
                raise ValidationError(
                    "No file provided",
                    "NO_FILE"
                )
            
            if not pdf_file.name.lower().endswith('.pdf'):
                raise ValidationError(
                    "File must be a PDF",
                    "INVALID_FILE_TYPE",
                    {"file_name": pdf_file.name}
                )
            
            file_size = len(pdf_file.getvalue())
            max_size = 2 * 1024 * 1024  # 2MB
            if file_size > max_size:
                raise ValidationError(
                    f"File too large: {file_size / 1024 / 1024:.1f}MB (max: 2MB)",
                    "FILE_TOO_LARGE",
                    {"file_size": file_size, "max_size": max_size}
                )
            
            logger.info(f"Uploading PDF: {pdf_file.name} ({file_size / 1024:.1f}KB)")
            
            url = f"{self.endpoint}/uploadpdf"
            files = {'file': (pdf_file.name, pdf_file.getvalue(), 'application/pdf')}
            
            # Remove Content-Type header for file upload
            headers = {k: v for k, v in self.session.headers.items() if k.lower() != 'content-type'}
            
            response = requests.post(
                url,
                files=files,
                headers=headers,
                timeout=1000
            )
            logger.info(f"the whole result file {response}")
            logger.info(f"Upload response status: {response.status_code}")
            
            if response.status_code == 404:
                raise APIError(
                    "Upload endpoint not found",
                    "UPLOAD_ENDPOINT_NOT_FOUND",
                    {"url": url}
                )
            elif response.status_code == 413:
                raise APIError(
                    "File too large for server",
                    "FILE_TOO_LARGE_SERVER",
                    {"file_size": file_size}
                )
            
            response.raise_for_status()
            
            try:
                data = response.json()
            except json.JSONDecodeError:
                raise APIError(
                    "Invalid JSON response from upload endpoint",
                    "UPLOAD_INVALID_JSON",
                    {"response_text": response.text[:500]}
                )

            success = data.get('success', False)
            logger.info(f"Upload result: {'success' if success else 'failed'}")

            if success:
                logger.info(f"pdf_uuid at upload pdf function: {data.get('pdf_uuid')}")
                logger.info(f"data: {data}")
                return {
                    'success': True,
                    'pdf_uuid': data.get('pdf_uuid'),
                    'pdf_name': data.get('filename'),
                    'filename': data.get('filename'),
                    'display_name': data.get('display_name', f"{data.get('filename', 'Unknown')} ({data.get('pdf_uuid', 'No UUID')[:8]})")
                }
            else:
                return {'success': False, 'error': data.get('message', 'Upload failed')}
            
        except ValidationError as e:
            ErrorHandler.log_error(
                e,
                "PDF Upload Validation",
                e.message
            )
            return {'success': False, 'error': e.message}
            
        except requests.exceptions.Timeout as e:
            error = APIError(
                "Upload timed out",
                "UPLOAD_TIMEOUT",
                {"timeout": 60, "file_name": pdf_file.name if pdf_file else "unknown"}
            )
            ErrorHandler.log_error(
                error,
                "PDF Upload Request",
                "Upload took too long. Please try a smaller file."
            )
            return {'success': False, 'error': 'Upload timed out'}
            
        except requests.exceptions.ConnectionError as e:
            error = APIError(
                "Cannot connect to upload server",
                "UPLOAD_CONNECTION_ERROR",
                {"endpoint": self.endpoint}
            )
            ErrorHandler.log_error(
                error,
                "PDF Upload Request",
                "Cannot connect to the server for upload."
            )
            return {'success': False, 'error': 'Connection failed'}
            
        except Exception as e:
            error = APIError(
                f"Unexpected error during upload: {str(e)}",
                "UPLOAD_UNEXPECTED_ERROR",
                {"error_type": type(e).__name__}
            )
            ErrorHandler.log_error(
                error,
                "PDF Upload Request",
                "An unexpected error occurred during upload."
            )
            return {'success': False, 'error': str(e)}

class ChatUI:
    """Handles chat interface rendering and state management with error handling"""
    
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
        self._initialize_session_state()
    
    def _initialize_session_state(self):
        """Initialize session state variables"""
        try:
            if "messages" not in st.session_state:
                st.session_state.messages = []
            if "suggested_questions" not in st.session_state:
                st.session_state.suggested_questions = []
            if "debug_mode" not in st.session_state:
                st.session_state.debug_mode = False
            if "error_count" not in st.session_state:
                st.session_state.error_count = 0
            if 'current_pdf_uuid' not in st.session_state:
                st.session_state.current_pdf_uuid = None
            if 'current_pdf_name' not in st.session_state:
                st.session_state.current_pdf_name = None
            if 'pdf_display_name' not in st.session_state:
                st.session_state.pdf_display_name = None
                
            logger.info("Session state initialized successfully")
        except Exception as e:
            ErrorHandler.log_error(
                e,
                "Session State Initialization",
                "Failed to initialize application state"
            )
    
    def display_chat_history(self):
        """Display all chat messages with error handling"""
        try:
            for idx, message in enumerate(st.session_state.messages):
                with st.chat_message(message["role"]):
                    st.write(message["content"])
                    
                    # Display enrollment prompt if applicable
                    if message["role"] == "assistant" and message.get("show_enroll"):
                        st.info("💡 Would you like to enroll for more information?")
        except Exception as e:
            ErrorHandler.log_error(
                e,
                "Chat History Display",
                "Error displaying chat history"
            )
    
    def _handle_user_input(self, user_input: str):
        """Process user input and get response with comprehensive error handling"""
        try:
            # Validate input
            if not user_input or not user_input.strip():
                st.warning("Please enter a valid question.")
                return
            
            # Add user message to chat
            st.session_state.messages.append({
                "role": "user", 
                "content": user_input.strip()
            })
            
            # Get response from API
            with st.spinner("Thinking..."):
                response = self.api_client.send_query(user_input.strip(), st.session_state.current_pdf_uuid)
            
            if response:
                # Add assistant response to chat
                assistant_message = {
                    "role": "assistant", 
                    "content": response.answer
                }
                st.session_state.messages.append(assistant_message)
                
                # Reset error count on successful response
                st.session_state.error_count = 0
                
            else:
                # Increment error count
                st.session_state.error_count += 1
                
                # Add error message with helpful suggestions
                error_message = "I'm sorry, I encountered an error while processing your request."
                
                if st.session_state.error_count >= 3:
                    error_message += " Multiple errors detected. Please check your connection and try again later."
                
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": error_message
                })
                
        except Exception as e:
            ErrorHandler.log_error(
                e,
                "User Input Handling",
                "Error processing your message"
            )
    
    def render_chat_interface(self):
        """Render the main chat interface with error boundaries"""
        try:
            st.title("🤖 PDF Assistant Chatbot")
            
            # Display current PDF indicator
            if st.session_state.current_pdf_uuid:
                st.info(f"📄 Currently querying: **{st.session_state.pdf_display_name}**")
            else:
                st.warning("⚠️ No PDF uploaded. Please upload a PDF first for document-specific queries.")
            
            # Display chat history
            self.display_chat_history()
            
            # Chat input
            if prompt := st.chat_input("Ask me anything about your documents..."):
                self._handle_user_input(prompt)
                st.rerun()
            
        except Exception as e:
            ErrorHandler.log_error(
                e,
                "Chat Interface Rendering",
                "Error rendering chat interface"
            )

class PDFUploader:
    """Handles PDF upload functionality with enhanced error handling"""
    
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
    
    def render_upload_interface(self):
        """Render PDF upload interface in sidebar with comprehensive error handling"""
        try:
            st.sidebar.title("📄 Document Upload")
            st.sidebar.markdown("Upload a PDF document to enhance the chatbot's knowledge.")
            
            uploaded_file = st.sidebar.file_uploader(
                "Choose a PDF file",
                type=['pdf'],
                help="Upload a PDF document for the chatbot to analyze"
            )
            
            if uploaded_file is not None:
                # Display file info with validation
                file_size = len(uploaded_file.getvalue())
                file_size_mb = file_size / (1024 * 1024)
                
                # Check file size immediately and show clear feedback
                if file_size_mb > 2.0:
                    st.error(f"File size ({file_size_mb:.1f}MB) exceeds the 2MB limit. Please select a smaller file.")
                    return
                
                st.sidebar.success(f"✅ File accepted: {uploaded_file.name}")
                st.sidebar.info(f"📊 Size: {file_size_mb:.1f} MB (within 2MB limit)")
                
                # Warn if file is large but acceptable
                if file_size_mb > 1:
                    st.sidebar.warning("⚠️ Large file detected. Upload may take longer.")
                
                # Upload button
                if st.sidebar.button("📤 Upload PDF", type="primary"):
                    self._handle_pdf_upload(uploaded_file)
                    
        except Exception as e:
            ErrorHandler.log_error(
                e,
                "PDF Upload Interface",
                "Error in upload interface"
            )








    def _handle_pdf_upload(self, pdf_file):
        """Handle PDF file upload with detailed error handling"""
        try:
            with st.spinner("Uploading PDF..."):
                upload_result = self.api_client.upload_pdf(pdf_file)
            
            if upload_result.get('success'):
                # Store PDF info in session state
                logger.info(f"pdf uuid: {upload_result.get('pdf_uuid')}")
                st.session_state.current_pdf_uuid = upload_result.get('pdf_uuid')
                st.session_state.current_pdf_name = upload_result.get('filename')
                st.session_state.pdf_display_name = upload_result.get('filename')
                
                st.sidebar.success("✅ PDF uploaded successfully!")
                st.sidebar.info(f"📄 Active PDF: **{st.session_state.pdf_display_name}**")
                st.sidebar.balloons()
                logger.info(f"PDF uploaded successfully: {pdf_file.name}")
            else:
                st.sidebar.error(f"❌ Upload failed: {upload_result.get('error', 'Unknown error')}")
                
                # Provide helpful suggestions
                with st.sidebar.expander("💡 Troubleshooting"):
                    st.write("""
                    - Check your internet connection
                    - Ensure the file is a valid PDF
                    - Try a smaller file if possible
                    - Contact support if the problem persists
                    """)
                    
        except Exception as e:
            ErrorHandler.log_error(
                e,
                "PDF Upload Handler",
                "Unexpected error during upload"
            )

class StreamlitApp:
    """Main application class with comprehensive error handling"""
    
    def __init__(self):
        self._configure_page()
        self._setup_error_handling()
        self.api_client = self._initialize_api_client()
        if self.api_client:
            self.chat_ui = ChatUI(self.api_client)
            self.pdf_uploader = PDFUploader(self.api_client)
    
    def _configure_page(self):
        """Configure Streamlit page settings"""
        try:
            st.set_page_config(
                page_title="PDF Assistant Chatbot",
                page_icon="🤖",
                layout="wide",
                initial_sidebar_state="expanded"
            )
            logger.info("Streamlit page configured successfully")
        except Exception as e:
            logger.error(f"Failed to configure Streamlit page: {str(e)}")
    
    def _setup_error_handling(self):
        """Setup global error handling"""
        try:
            # Create logs directory if it doesn't exist
            os.makedirs('logs', exist_ok=True)
            logger.info("Error handling setup completed")
        except Exception as e:
            logger.error(f"Failed to setup error handling: {str(e)}")
    
    def _initialize_api_client(self) -> Optional[APIClient]:
        """Initialize API client with error handling"""
        try:
            return APIClient()
        except ConfigurationError as e:
            # Configuration errors are already handled by ErrorHandler
            st.info("Please check the troubleshooting guide below:")
            with st.expander("🔧 Configuration Help"):
                st.markdown("""
                **Setup Steps:**
                1. Create a `.env` file in your project directory
                2. Add your endpoint: `ENDPOINT=https://your-api-endpoint.com`
                3. Restart the application
                
                **File Structure:**
                ```
                your-project/
                ├── app.py
                ├── .env          ← Create this file
                ├── requirements.txt
                └── README.md
                ```
                """)
            st.stop()
        except Exception as e:
            ErrorHandler.log_error(
                e,
                "API Client Initialization",
                "Failed to initialize the application"
            )
            st.stop()
    
    def run(self):
        """Run the main application with error boundaries"""
        try:
            # Add this CSS block here - at the very start
            st.markdown("""
            <style>
                .css-1d391kg {
                    width: 350px;
                }
                section[data-testid="stSidebar"] {
                    width: 350px !important;
                }
            </style>
            """, unsafe_allow_html=True)
            
            # Render sidebar (PDF upload)
            self.pdf_uploader.render_upload_interface()
            
            # Add sidebar info
            with st.sidebar:
                st.markdown("---")
                st.markdown("### ℹ️ How to use")
                st.markdown("""
                1. **Upload a PDF** using the file uploader above
                2. **Ask questions** about your document in the chat
                3. **Click suggested questions** for quick interactions
                4. **View enrollment prompts** when available
                """)
                
                # Add connection status
                self._display_connection_status()
            
            # Render main chat interface
            self.chat_ui.render_chat_interface()
            
        except Exception as e:
            ErrorHandler.log_error(
                e,
                "Main Application",
                "Critical application error"
            )
            st.error("A critical error occurred. Please refresh the page.")
    
    def _display_connection_status(self):
        """Display API connection status in sidebar"""
        try:
            with st.sidebar:
                st.markdown("### 🔗 Connection Status")
                
                # Test connection button
                if st.button("Test Connection", help="Test API connectivity"):
                    with st.spinner("Testing connection..."):
                        try:
                            response = requests.head(self.api_client.endpoint, timeout=5)
                            if response.status_code < 500:
                                st.success("✅ Connected")
                            else:
                                st.warning(f"⚠️ Server issues (Status: {response.status_code})")
                        except requests.exceptions.RequestException:
                            st.error("❌ Connection failed")
                        except Exception as e:
                            st.error(f"❌ Test failed: {str(e)}")
        except Exception as e:
            logger.error(f"Error displaying connection status: {str(e)}")

def main():
    """Application entry point with top-level error handling"""
    try:
        logger.info("Starting PDF Assistant Chatbot application")
        app = StreamlitApp()
        app.run()
    except Exception as e:
        logger.critical(f"Critical application failure: {str(e)}")
        logger.critical(f"Traceback: {traceback.format_exc()}")
        st.error("🚨 Critical application error. Please check the logs and restart.")

if __name__ == "__main__":
    main()