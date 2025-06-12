#!/usr/bin/env python3
"""
Flask Backend for PDF Assistant Chatbot with Agentic AI
Integrates with EventBot for question answering, PDF document upload, and web search fallback
"""

import os
import time
import tempfile
import logging
import re
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

# Import for web search
import requests
from urllib.parse import quote_plus
import json

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

class WebSearchAgent:
    """
    Web search agent using DuckDuckGo for fallback searches
    """
    
    def __init__(self, gemini_api_key: str):
        """Initialize web search agent with Gemini for summarization"""
        self.gemini_api_key = gemini_api_key
        genai.configure(api_key=self.gemini_api_key)
        self.llm = genai.GenerativeModel("gemini-2.0-flash")
        
    def _ensure_concise_answer(self, answer: str, query: str) -> str:
        """
        Ensure the answer is concise and remove unnecessary verbosity
        
        Args:
            answer (str): The generated answer
            query (str): Original query
            
        Returns:
            str: Processed concise answer
        """
        # Remove common verbose phrases
        verbose_phrases = [
            "Based on the search results,",
            "According to the information found,",
            "From the search results,",
            "The search results indicate that",
            "Based on the information provided,",
            "According to the sources,",
            "From what I found,",
            "The information shows that",
            "Based on my search,"
        ]
        
        # Clean up the answer
        cleaned_answer = answer
        for phrase in verbose_phrases:
            cleaned_answer = cleaned_answer.replace(phrase, "").strip()
        
        # Remove extra spaces and ensure proper capitalization
        cleaned_answer = " ".join(cleaned_answer.split())
        if cleaned_answer and not cleaned_answer[0].isupper():
            cleaned_answer = cleaned_answer[0].upper() + cleaned_answer[1:]
        
        # For very simple factual questions, try to extract just the core answer
        simple_question_patterns = [
            "what is the capital of",
            "who is the",
            "when was",
            "where is",
            "how many",
            "what year"
        ]
        
        if any(pattern in query.lower() for pattern in simple_question_patterns):
            # Try to extract the most relevant sentence
            sentences = cleaned_answer.split('.')
            if sentences:
                # Return the first meaningful sentence
                first_sentence = sentences[0].strip()
                if len(first_sentence) > 10:  # Ensure it's not just a fragment
                    return first_sentence + "."
        return cleaned_answer



    def search_duckduckgo(self, query: str, num_results: int = 5) -> List[Dict[str, str]]:
        """
        Search DuckDuckGo for results
        
        Args:
            query (str): Search query
            num_results (int): Number of results to return
            
        Returns:
            List[Dict]: List of search results with title, snippet, and URL
        """
        try:
            # DuckDuckGo Instant Answer API
            url = "https://api.duckduckgo.com/"
            params = {
                'q': query,
                'format': 'json',
                'pretty': '1',
                'no_redirect': '1',
                'no_html': '1',
                'skip_disambig': '1'
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            results = []
            
            # Get instant answer if available
            if data.get('Abstract'):
                results.append({
                    'title': data.get('AbstractText', 'Instant Answer'),
                    'snippet': data.get('Abstract', ''),
                    'url': data.get('AbstractURL', '')
                })
            
            # Get related topics
            for topic in data.get('RelatedTopics', [])[:num_results]:
                if isinstance(topic, dict) and topic.get('Text'):
                    results.append({
                        'title': topic.get('Text', '').split(' - ')[0] if ' - ' in topic.get('Text', '') else topic.get('Text', ''),
                        'snippet': topic.get('Text', ''),
                        'url': topic.get('FirstURL', '')
                    })
            
            # If we don't have enough results, try to get more from other sources
            if len(results) < 2:
                # Fallback to a simple web search (this is a simplified approach)
                fallback_results = self._fallback_search(query, num_results)
                results.extend(fallback_results)
            
            return results[:num_results]
            
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")
            return self._fallback_search(query, num_results)
    
    def _fallback_search(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """
        Fallback search method - returns a generic response
        """
        return [{
            'title': f"Search Results for: {query}",
            'snippet': f"I searched for '{query}' but couldn't retrieve specific web results at the moment. Please try rephrasing your question or check online resources directly.",
            'url': f"https://duckduckgo.com/?q={quote_plus(query)}"
        }]
    
    def summarize_search_results(self, query: str, search_results: List[Dict[str, str]]) -> str:
        """
        Summarize search results using Gemini with concise output
        
        Args:
            query (str): Original search query
            search_results (List[Dict]): Search results to summarize
            
        Returns:
            str: Summarized response
        """
        try:
            if not search_results:
                return "I couldn't find relevant information for your query."
            
            # Prepare context from search results
            context = "\n\n".join([
                f"Source: {result['title']}\nContent: {result['snippet']}"
                for result in search_results if result['snippet']
            ])
            
            if not context:
                return "I found some search results but they don't contain enough information to answer your question."
            
            prompt = f"""Based on the search results below, provide a direct and concise answer to the user's question. 

            IMPORTANT GUIDELINES:
            - Give only the essential information that directly answers the question
            - Keep your response to 1-2 sentences maximum for simple factual questions
            - Be precise and avoid unnecessary background information
            - If it's a simple fact (like "What is the capital of X"), just state the answer clearly
            - Only include additional context if the question specifically asks for it

            User Question: {query}

            Search Results:
            {context}

            Provide a brief, direct answer:"""
            
            response = self.llm.generate_content(prompt)
            answer = response.text.strip()
            
            # Post-process to ensure conciseness
            return self._ensure_concise_answer(answer, query)
            
        except Exception as e:
            logger.error(f"Error summarizing search results: {e}")
            return f"I found information about '{query}' but encountered an error while processing it."

class QueryRewriter:
    """
    Query rewriting agent to improve search effectiveness
    """
    
    def __init__(self, gemini_api_key: str):
        """Initialize query rewriter with Gemini"""
        self.gemini_api_key = gemini_api_key
        genai.configure(api_key=self.gemini_api_key)
        self.llm = genai.GenerativeModel("gemini-2.0-flash")
    
    def rewrite_query(self, original_query: str) -> str:
        """
        Rewrite query to be more specific and search-friendly
        
        Args:
            original_query (str): Original user query
            
        Returns:
            str: Rewritten query
        """
        try:
            prompt = f"""Rewrite this query to be more specific and search-friendly while keeping it concise.

    Rules:
    1. Expand acronyms if needed
    2. Make the query more specific
    3. Keep it under 10 words
    4. Focus on the core information needed
    5. Return ONLY the rewritten query

    Original: "{original_query}"
    Rewritten:"""
            
            response = self.llm.generate_content(prompt)
            rewritten = response.text.strip()
            
            # Remove quotes if present
            rewritten = rewritten.strip('"\'')
            
            # Fallback to original if rewriting fails or is too long
            if not rewritten or len(rewritten) < 3 or len(rewritten.split()) > 12:
                return original_query
                
            return rewritten
            
        except Exception as e:
            logger.error(f"Error rewriting query: {e}")
            return original_query

class EventBot:
    """
    Enhanced EventBot integration with Agentic AI capabilities
    """
    
    def __init__(self):
        """Initialize the Event Bot with environment variables"""
        self.gemini_api_key = os.getenv("GEMINI_API_KEY")
        self.pinecone_api_key = os.getenv("PINECONE_API_KEY")
        self.pinecone_index_name = os.getenv("PINECONE_INDEX")
        self.pinecone_cloud = os.getenv("PINECONE_CLOUD", "aws")
        self.pinecone_region = os.getenv("PINECONE_REGION", "us-east-1")
        
        # Configuration for agentic behavior
        self.similarity_threshold = float(os.getenv("SIMILARITY_THRESHOLD", "0.7"))
        self.enable_web_search = os.getenv("ENABLE_WEB_SEARCH", "true").lower() == "true"
        
        # Validate required credentials
        self._validate_credentials()
        
        # Initialize components
        self._initialize_pinecone()
        self._initialize_gemini()
        self._initialize_embeddings()
        self._setup_prompt_template()
        
        # Initialize agentic components
        self.query_rewriter = QueryRewriter(self.gemini_api_key)
        self.web_search_agent = WebSearchAgent(self.gemini_api_key)
        


    # Add this method to your EventBot class
    def _limit_response_length(self, response: str, max_sentences: int = 3) -> str:
        """
        Limit response length to keep answers concise
        
        Args:
            response (str): The original response
            max_sentences (int): Maximum number of sentences to keep
            
        Returns:
            str: Truncated response if necessary
        """
        # Split into sentences
        sentences = response.split('.')
        sentences = [s.strip() for s in sentences if s.strip()]
        
        # If response is already short, return as is
        if len(sentences) <= max_sentences:
            return response
        
        # Take only the first few sentences
        limited = '. '.join(sentences[:max_sentences])
        if limited and not limited.endswith('.'):
            limited += '.'
        
        return limited



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

    def _is_insufficient_answer(self, answer: str) -> bool:
        """
        Check if the RAG answer indicates insufficient information
        
        Args:
            answer (str): The generated answer
            
        Returns:
            bool: True if answer indicates lack of information
        """
        insufficient_phrases = [
            "i don't have that specific information",
            "i don't have that information",
            "i'm sorry, i don't have",
            "no specific details found",
            "no information found",
            "not in the context",
            "i don't have enough information",
            "cannot find",
            "unable to find",
            "no relevant information"
        ]
        
        answer_lower = answer.lower()
        return any(phrase in answer_lower for phrase in insufficient_phrases)

    def answer_question(self, question: str, top_k: int = 5) -> Dict[str, Any]:
        """
        Answer a question using Agentic RAG (Retrieval-Augmented Generation)
        
        Args:
            question (str): The user's question
            top_k (int): Number of similar documents to retrieve
            
        Returns:
            dict: Response containing answer text and metadata
        """
        try:
            logger.info(f"Processing question: {question[:100]}...")
            
            # Step 1: Rewrite the query for better retrieval
            rewritten_query = self.query_rewriter.rewrite_query(question)
            logger.info(f"Rewritten query: {rewritten_query[:100]}...")
            
            # Step 2: Try RAG with similarity threshold
            results = self.vectorstore.similarity_search_with_score(rewritten_query, k=top_k)
            
            # Filter results based on similarity threshold
            filtered_results = [(doc, score) for doc, score in results if score >= self.similarity_threshold]
            
            context_text = ""
            rag_answer = ""
            used_web_search = False
            
            if filtered_results:
                # Step 3: Generate answer using RAG
                context_text = "\n\n --- \n\n".join([doc.page_content for doc, _score in filtered_results])
                
                # Create prompt using template
                prompt_template_obj = ChatPromptTemplate.from_template(self.prompt_template)
                prompt = prompt_template_obj.format(context=context_text, question=question)
                
                # Generate response using Gemini
                response = self.llm.generate_content(prompt)
                rag_answer = response.text
                
                # Limit response length for conciseness
                rag_answer = self._limit_response_length(rag_answer)
                
                logger.info(f"RAG answered with {len(filtered_results)} sources")
                
                # Step 4: Check if RAG answer is sufficient
                if not self._is_insufficient_answer(rag_answer):
                    return {
                        "answer": rag_answer,
                        "context_found": True,
                        "num_sources": len(filtered_results),
                        "success": True,
                        "used_web_search": False,
                        "rewritten_query": rewritten_query,
                        "error": None
                    }
            
            # Step 5: Fallback to web search if enabled and RAG was insufficient
            if self.enable_web_search:
                logger.info("RAG insufficient, falling back to web search...")
                
                search_results = self.web_search_agent.search_duckduckgo(rewritten_query, num_results=3)  # Reduced from 5 to 3
                web_answer = self.web_search_agent.summarize_search_results(rewritten_query, search_results)
                
                # Limit web search response length
                web_answer = self._limit_response_length(web_answer, max_sentences=2)
                used_web_search = True
                
                final_answer = web_answer  # Remove the "Based on web search results:" prefix
                
                return {
                    "answer": final_answer,
                    "context_found": len(search_results) > 0,
                    "num_sources": len(search_results),
                    "success": True,
                    "used_web_search": True,
                    "rewritten_query": rewritten_query,
                    "error": None
    }
            
            # Step 6: If web search is disabled, return the RAG answer or a fallback
            if rag_answer:
                return {
                    "answer": rag_answer,
                    "context_found": len(filtered_results) > 0,
                    "num_sources": len(filtered_results),
                    "success": True,
                    "used_web_search": False,
                    "rewritten_query": rewritten_query,
                    "error": None
                }
            else:
                return {
                    "answer": "I'm sorry, I don't have enough information to answer your question. Please try rephrasing or asking about something else.",
                    "context_found": False,
                    "num_sources": 0,
                    "success": True,
                    "used_web_search": False,
                    "rewritten_query": rewritten_query,
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
                "used_web_search": False,
                "rewritten_query": question,
                "error": str(e)
            }
    
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
            "web_search": False,
            "query_rewriter": False,
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
        
        # Test Web Search
        try:
            test_results = self.web_search_agent.search_duckduckgo("test", num_results=1)
            status["web_search"] = len(test_results) > 0
        except Exception as e:
            logger.error(f"Web search health check failed: {e}")
            status["web_search"] = False
        
        # Test Query Rewriter
        try:
            test_rewrite = self.query_rewriter.rewrite_query("test")
            status["query_rewriter"] = len(test_rewrite) > 0
        except Exception as e:
            logger.error(f"Query rewriter health check failed: {e}")
            status["query_rewriter"] = False
        
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
    logger.info("EventBot with Agentic AI initialized successfully")
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
    """Enhanced answer endpoint with Agentic AI capabilities"""
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
        
        # Process the question with Agentic AI
        result = event_bot.answer_question(query)
        
        # Return response in the expected format with additional metadata
        response_data = {
            "answer": result["answer"],
            "success": result["success"],
            "metadata": {
                "context_found": result["context_found"],
                "num_sources": result["num_sources"],
                "used_web_search": result["used_web_search"],
                "rewritten_query": result["rewritten_query"]
            }
        }
        
        if result["error"]:
            response_data["error"] = result["error"]
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error in answer endpoint: {e}")
        return jsonify({
            "answer": "I apologize, but I encountered an error while processing your question. Please try again.",
            "success": False,
            "error": str(e),
            "metadata": {
                "context_found": False,
                "num_sources": 0,
                "used_web_search": False,
                "rewritten_query": ""
            }
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
        "message": "PDF Assistant Chatbot API with Agentic AI",
        "version": "2.0.0",
        "features": [
            "RAG-based document search",
            "Query rewriting for better search",
            "Web search fallback with DuckDuckGo",
            "Intelligent answer validation",
            "PDF document processing"
        ],
        "endpoints": {
            "/health": "GET - Health check with component status",
            "/answer": "POST - Answer questions with RAG + web search fallback",
            "/uploadpdf": "POST - Upload PDF files"
        }
    })

@app.route('/config', methods=['GET'])
def get_config():
    """Get current configuration"""
    try:
        if not event_bot:
            return jsonify({
                "status": "error",
                "message": "EventBot not initialized"
            }), 500
        
        return jsonify({
            "similarity_threshold": event_bot.similarity_threshold,
            "web_search_enabled": event_bot.enable_web_search,
            "pinecone_index": event_bot.pinecone_index_name,
            "max_file_size_mb": MAX_FILE_SIZE // (1024*1024)
        })
        
    except Exception as e:
        logger.error(f"Error getting config: {e}")
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

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
    
    logger.info(f"Starting Flask server on port {port}")
    logger.info(f"Web search enabled: {os.getenv('ENABLE_WEB_SEARCH', 'true')}")
    logger.info(f"Similarity threshold: {os.getenv('SIMILARITY_THRESHOLD', '0.7')}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )