#!/usr/bin/env python3
"""
Flask Backend for PDF Assistant Chatbot
Integrates with EventBot for question answering and PDF document upload
"""

import os
import time
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, List
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.utils import secure_filename
from dotenv import load_dotenv

# Import EventBot and related components
import google.generativeai as genai
from pinecone import Pinecone, ServerlessSpec
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.prompts import ChatPromptTemplate

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for Streamlit integration

# Configuration
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {'pdf'}
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class EventBot:
    """
    EventBot integration for Flask backend
    """
    
    def __init__(self):
        """Initialize the Event Bot with environment variables"""
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_index_name = os.getenv("PINECONE_INDEX")
        self.pinecone_cloud = os.getenv("PINECONE_CLOUD", "aws")
        self.pinecone_region = os.getenv("PINECONE_REGION", "us-east-1")
        
        # Validate required credentials
        self._validate_credentials()
        
        # Initialize components
        self._initialize_pinecone()
        self._initialize_gemini()
        self._initialize_embeddings()
        self._setup_prompt_template()
        
    def _validate_credentials(self):
        """Validate all required environment variables"""
        required_vars = {
            "GEMINI_API_KEY": self.gemini_api_key,
            "PINECONE_API_KEY": self.pinecone_api_key,
            "PINECONE_INDEX": self.pinecone_index_name
        }
        
        missing_vars = [var for var, value in required_vars.items() if not value]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        
    def _initialize_pinecone(self):
        """Initialize Pinecone client and vector store"""
        try:
            self.pc = Pinecone(api_key=self.pinecone_api_key)
            
            # Check if index exists, create if not
            if self.pinecone_index_name not in self.pc.list_indexes().names():
                logger.info(f"Creating Pinecone index: {self.pinecone_index_name}")
                spec = ServerlessSpec(cloud=self.pinecone_cloud, region=self.pinecone_region)
                self.pc.create_index(
                    name=self.pinecone_index_name,
                    dimension=768,  # Dimension for Gemini embedding model
                    metric="cosine",
                    spec=spec
                )
                # Wait for index to be ready
                while not self.pc.describe_index(self.pinecone_index_name).status['ready']:
                    time.sleep(1)
                logger.info(f"Index {self.pinecone_index_name} created and ready")
            
            self.index = self.pc.Index(self.pinecone_index_name)
            logger.info("Pinecone initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            raise
    
    def _initialize_gemini(self):
        """Initialize Gemini LLM client"""
        try:
            genai.configure(api_key=self.gemini_api_key)
            self.llm = genai.GenerativeModel("gemini-2.0-flash")
            logger.info("Gemini LLM initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise
    
    def _initialize_embeddings(self):
        """Initialize Google embeddings for vector search"""
        try:
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=self.gemini_api_key
            )
            
            # Create vector store
            self.vectorstore = PineconeVectorStore(
                index_name=self.pinecone_index_name,
                embedding=self.embeddings,
                text_key="text"
            )
            logger.info("Embeddings and vector store initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            raise
    
    def _setup_prompt_template(self):
        """Setup the prompt template for the event bot"""
        self.prompt_template = """
You are a friendly Event Information Assistant named "Event Bot". Your primary purpose is to answer questions about the event described in the provided context. You can also answer questions based on user-submitted resumes if they have been provided. Follow these guidelines:

1. You can respond to basic greetings like "hi", "hello", or "how are you" in a warm, welcoming manner
2. For event information or resume content, only provide details that are present in the context
3. If information is not in the context, politely say "I'm sorry, I don't have that specific information" (for event) or "I'm sorry, I don't have that information from the resume" (for resume).
4. Keep responses concise but conversational
5. Do not make assumptions beyond what's explicitly stated in the context
6. Always prioritize factual accuracy while maintaining a helpful tone
7. Do not introduce information that isn't in the context
8. If unsure about any information, acknowledge uncertainty rather than guess
9. You may suggest a few general questions users might want to ask about the event
10. Remember to maintain a warm, friendly tone in all interactions
11. You should refer to yourself as "Event Bot"
12. You should not greet if the user has not greeted to you
13. Format and structure the answer properly.

Remember: While you can be conversational, your primary role is providing accurate information based on the context provided (event details and/or resume content).

Context information (event details and/or resume content):
{context}
--------

Now, please answer this question: {question}
"""

    def answer_question(self, question: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Answer a question using RAG (Retrieval-Augmented Generation)
        
        Args:
            question (str): The user's question
            top_k (int): Number of similar documents to retrieve
            
        Returns:
            dict: Response containing answer text and metadata
        """
        try:
            logger.info(f"Processing question: {question[:100]}...")
            
            # Retrieve relevant documents from vector store
            results = self.vectorstore.similarity_search_with_score(question, k=top_k)
            
            # Process search results to create context
            if results:
                context_text = "\n\n --- \n\n".join([doc.page_content for doc, _score in results])
                if not context_text:
                    context_text = "No specific details found in the documents for your query."
            else:
                context_text = "No information found in the knowledge base for your query."
            
            # Create prompt using template
            prompt_template_obj = ChatPromptTemplate.from_template(self.prompt_template)
            prompt = prompt_template_obj.format(context=context_text, question=question)
            
            # Generate response using Gemini
            response = self.llm.generate_content(prompt)
            answer_text = response.text
            
            logger.info(f"Successfully answered question with {len(results)} sources")
            
            return {
                "answer": answer_text,
                "context_found": len(results) > 0,
                "num_sources": len(results),
                "success": True,
                "error": None
            }
            
        except Exception as e:
            error_message = f"Error answering question: {str(e)}"
            logger.error(f"Error processing question: {e}")
            
            return {
                "answer": "I'm sorry, I encountered an error while processing your question. Please try again.",
                "context_found": False,
                "num_sources": 0,
                "success": False,
                "error": str(e)
            }
    
    def _generate_suggested_questions(self, context: str, current_question: str) -> List[str]:
        """Generate suggested questions based on context"""
        # Suggested questions functionality removed
        return []
    
    def _should_show_enrollment(self, answer: str, question: str) -> bool:
        """Determine if enrollment prompt should be shown"""
        # Show enrollment functionality removed
        return False
    
    def upload_pdf(self, file_path: str, user_id: str = None) -> bool:
        """
        Upload and process a PDF file to the vector database
        
        Args:
            file_path (str): Path to the PDF file
            user_id (str): Optional user ID for resume files
            
        Returns:
            bool: Success status
        """
        try:
            logger.info(f"Processing PDF upload: {file_path}")
            
            # Load the PDF document
            loader = PyPDFLoader(file_path)
            documents = loader.load()
            
            if not documents:
                logger.warning(f"No content extracted from PDF: {file_path}")
                return False
            
            # Add metadata if user_id is provided (for resume files)
            if user_id:
                for doc in documents:
                    doc.metadata["userId"] = user_id
                    doc.metadata["document_type"] = "resume"
            else:
                for doc in documents:
                    doc.metadata["document_type"] = "event_document"
            
            # Split documents into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=2000, 
                chunk_overlap=800
            )
            chunks = text_splitter.split_documents(documents)
            
            if not chunks:
                logger.warning(f"No chunks created from PDF: {file_path}")
                return False
            
            logger.info(f"Split PDF into {len(chunks)} chunks")
            
            # Add chunks to vector store (without deleting existing data)
            self.vectorstore.add_documents(chunks)
            
            logger.info(f"Successfully uploaded {len(chunks)} chunks to vector database")
            return True
            
        except Exception as e:
            logger.error(f"Error uploading PDF {file_path}: {e}")
            return False
    
    def health_check(self) -> Dict[str, Any]:
        """Check the health of all components"""
        status = {
            "gemini_api": False,
            "pinecone_connection": False,
            "embeddings": False,
            "vector_store": False,
            "overall_health": False
        }
        
        # Test Gemini
        try:
            test_response = self.llm.generate_content("Say 'OK' if you can respond")
            status["gemini_api"] = "OK" in test_response.text
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            status["gemini_api"] = False
        
        # Test Pinecone
        try:
            index_stats = self.index.describe_index_stats()
            status["pinecone_connection"] = True
        except Exception as e:
            logger.error(f"Pinecone health check failed: {e}")
            status["pinecone_connection"] = False
        
        # Test Embeddings
        try:
            test_embedding = self.embeddings.embed_query("test")
            status["embeddings"] = len(test_embedding) > 0
        except Exception as e:
            logger.error(f"Embeddings health check failed: {e}")
            status["embeddings"] = False
        
        # Test Vector Store
        try:
            test_search = self.vectorstore.similarity_search("test", k=1)
            status["vector_store"] = True
        except Exception as e:
            logger.error(f"Vector store health check failed: {e}")
            status["vector_store"] = False
        
        # Overall health
        status["overall_health"] = all([
            status["gemini_api"],
            status["pinecone_connection"], 
            status["embeddings"],
            status["vector_store"]
        ])
        
        return status

# Initialize EventBot instance
try:
    event_bot = EventBot()
    logger.info("EventBot initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize EventBot: {e}")
    event_bot = None

def allowed_file(filename):
    """Check if the uploaded file is allowed"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def validate_request_size():
    """Validate request content length"""
    if request.content_length and request.content_length > MAX_FILE_SIZE:
        return False
    return True

# Flask Routes

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        if not event_bot:
            return jsonify({
                "status": "error",
                "message": "EventBot not initialized",
                "healthy": False
            }), 500
        
        health_status = event_bot.health_check()
        
        return jsonify({
            "status": "success",
            "health": health_status,
            "healthy": health_status["overall_health"]
        }), 200 if health_status["overall_health"] else 503
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "healthy": False
        }), 500

@app.route('/answer', methods=['POST'])
def answer_question():
    """Answer endpoint for processing user questions"""
    try:
        # Check if EventBot is initialized
        if not event_bot:
            return jsonify({
                "answer": "Service temporarily unavailable. Please try again later.",
                "success": False,
                "error": "EventBot not initialized"
            }), 500
        
        # Get JSON data
        data = request.get_json()
        if not data:
            return jsonify({
                "answer": "Invalid request format. Please provide a valid JSON request.",
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        # Extract and validate query
        query = data.get('query', '').strip()
        if not query:
            return jsonify({
                "answer": "Please provide a valid question.",
                "success": False,
                "error": "Empty query provided"
            }), 400
        
        # Process the question
        result = event_bot.answer_question(query)
        
        # Return response in the expected format
        return jsonify({
            "answer": result["answer"]
        }), 200
        
    except Exception as e:
        logger.error(f"Error in answer endpoint: {e}")
        return jsonify({
            "answer": "I apologize, but I encountered an error while processing your question. Please try again.",
            "success": False,
            "error": str(e)
        }), 500

@app.route('/uploadpdf', methods=['POST'])
def upload_pdf():
    """PDF upload endpoint"""
    try:
        # Check if EventBot is initialized
        if not event_bot:
            return jsonify({
                "success": False,
                "message": "Service temporarily unavailable",
                "error": "EventBot not initialized"
            }), 500
        
        # Validate request size
        if not validate_request_size():
            return jsonify({
                "success": False,
                "message": f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB",
                "error": "File size exceeded"
            }), 413
        
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "message": "No file provided",
                "error": "No file in request"
            }), 400
        
        file = request.files['file']
        
        # Check if file was actually selected
        if file.filename == '':
            return jsonify({
                "success": False,
                "message": "No file selected",
                "error": "Empty filename"
            }), 400
        
        # Validate file type
        if not allowed_file(file.filename):
            return jsonify({
                "success": False,
                "message": "Only PDF files are allowed",
                "error": "Invalid file type"
            }), 400
        
        # Secure the filename
        filename = secure_filename(file.filename)
        if not filename:
            return jsonify({
                "success": False,
                "message": "Invalid filename",
                "error": "Filename not secure"
            }), 400
        
        # Create temporary file to save the upload
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            # Extract user_id from filename if it looks like a resume
            user_id = None
            if 'resume' in filename.lower() or 'cv' in filename.lower():
                # Extract user ID from filename (without extension)
                user_id = Path(filename).stem
            
            # Process the PDF
            success = event_bot.upload_pdf(temp_file_path, user_id)
            
            if success:
                logger.info(f"Successfully processed PDF upload: {filename}")
                return jsonify({
                    "success": True,
                    "message": f"PDF '{filename}' uploaded and processed successfully",
                    "filename": filename
                }), 200
            else:
                logger.warning(f"Failed to process PDF upload: {filename}")
                return jsonify({
                    "success": False,
                    "message": "Failed to process the PDF file",
                    "error": "Processing failed"
                }), 500
                
        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {temp_file_path}: {e}")
        
    except Exception as e:
        logger.error(f"Error in upload endpoint: {e}")
        return jsonify({
            "success": False,
            "message": "An error occurred while processing your upload",
            "error": str(e)
        }), 500

@app.route('/', methods=['GET'])
def index():
    """Root endpoint"""
    return jsonify({
        "message": "PDF Assistant Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "/health": "GET - Health check",
            "/answer": "POST - Answer questions",
            "/uploadpdf": "POST - Upload PDF files"
        }
    })

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        "error": "Endpoint not found",
        "message": "The requested endpoint does not exist"
    }), 404

@app.errorhandler(405)
def method_not_allowed(error):
    """Handle 405 errors"""
    return jsonify({
        "error": "Method not allowed",
        "message": "The HTTP method is not allowed for this endpoint"
    }), 405

@app.errorhandler(413)
def payload_too_large(error):
    """Handle file too large errors"""
    return jsonify({
        "success": False,
        "message": f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB",
        "error": "Payload too large"
    }), 413

if __name__ == '__main__':
    # Development server
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_ENV') == 'development'
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )
