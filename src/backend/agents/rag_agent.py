# src/backend/agents/rag_agent.py

import os
import time
import logging
from typing import Dict, Any, List

import google.generativeai as genai
from pinecone import Pinecone, ServerlessSpec
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain.prompts import ChatPromptTemplate

from ..config import Config # Import Config from the parent package
from .base import BaseChatbotAgent # Import the base agent class

logger = logging.getLogger(__name__)

class ChatbotAgent(BaseChatbotAgent):
    """
    EventBot integration for Flask backend, refactored as a ChatbotAgent.

    This agent handles question answering using RAG and PDF document ingestion.
    """
    
    def __init__(self):
        """
        Initializes the ChatbotAgent with credentials and sets up LLM,
        embeddings, and vector store components.
        """
        # Load configurations from the Config class
        self.gemini_api_key = Config.GEMINI_API_KEY
        self.pinecone_api_key = Config.PINECONE_API_KEY
        self.pinecone_index_name = Config.PINECONE_INDEX_NAME
        self.pinecone_cloud = Config.PINECONE_CLOUD
        self.pinecone_region = Config.PINECONE_REGION
        
        # Validate required credentials before proceeding
        self._validate_credentials()
        
        # Initialize components
        self._initialize_pinecone()
        self._initialize_gemini()
        self._initialize_embeddings()
        self._setup_prompt_template()
        logger.info("ChatbotAgent components initialized.")
        
    def _validate_credentials(self):
        """Validate all required environment variables."""
        Config.validate_required_env_vars() # Use the static method from Config
        
    def _initialize_pinecone(self):
        """Initialize Pinecone client and vector store."""
        try:
            self.pc = Pinecone(api_key=self.pinecone_api_key)
            
            if self.pinecone_index_name not in self.pc.list_indexes().names():
                logger.info(f"Creating Pinecone index: {self.pinecone_index_name}")
                spec = ServerlessSpec(cloud=self.pinecone_cloud, region=self.pinecone_region)
                self.pc.create_index(
                    name=self.pinecone_index_name,
                    dimension=768,  # Dimension for Gemini embedding model
                    metric="cosine",
                    spec=spec
                )
                while not self.pc.describe_index(self.pinecone_index_name).status['ready']:
                    time.sleep(1)
                logger.info(f"Index {self.pinecone_index_name} created and ready.")
            
            self.index = self.pc.Index(self.pinecone_index_name)
            logger.info("Pinecone initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {e}")
            raise # Re-raise to halt startup if critical component fails
    
    def _initialize_gemini(self):
        """Initialize Gemini LLM client."""
        try:
            genai.configure(api_key=self.gemini_api_key)
            self.llm = genai.GenerativeModel("gemini-2.0-flash")
            logger.info("Gemini LLM initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            raise
    
    def _initialize_embeddings(self):
        """Initialize Google embeddings for vector search."""
        try:
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model="models/embedding-001",
                google_api_key=self.gemini_api_key
            )
            
            self.vectorstore = PineconeVectorStore(
                index_name=self.pinecone_index_name,
                embedding=self.embeddings,
                text_key="text"
            )
            logger.info("Embeddings and vector store initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize embeddings: {e}")
            raise
    
    def _setup_prompt_template(self):
        """Setup the prompt template for the chatbot agent."""
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
        Answers a question using RAG (Retrieval-Augmented Generation).
        
        Args:
            question (str): The user's question.
            top_k (int): Number of similar documents to retrieve.
            
        Returns:
            dict: Response containing answer text and metadata.
        """
        try:
            logger.info(f"Processing question: {question[:100]}...")
            
            results = self.vectorstore.similarity_search_with_score(question, k=top_k)
            
            if results:
                context_text = "\n\n --- \n\n".join([doc.page_content for doc, _score in results])
                if not context_text:
                    context_text = "No specific details found in the documents for your query."
            else:
                context_text = "No information found in the knowledge base for your query."
            
            prompt_template_obj = ChatPromptTemplate.from_template(self.prompt_template)
            prompt = prompt_template_obj.format(context=context_text, question=question)
            
            response = self.llm.generate_content(prompt)
            answer_text = response.text
            
            logger.info(f"Successfully answered question with {len(results)} sources.")
            
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
       

    def upload_data(self, file_path: str, user_id: str = None, text_content: str = "", table_count: int = 0) -> bool:
        """
        Uploads and processes a PDF file to the vector database, including extracted text and table metadata.
        Renamed from upload_pdf to be more generic for BaseChatbotAgent interface.

        Args:
            file_path (str): Path to the PDF file.
            user_id (str, optional): User ID for resume files.
            text_content (str, optional): Extracted text content from the PDF.
            table_count (int, optional): Number of tables stored in the database.

        Returns:
            bool: Success status.
        """
        try:
            logger.info(
                f"Processing PDF upload: {file_path}, user_id: {user_id}, table_count: {table_count}")

            # Load PDF using PyPDFLoader
            loader = PyPDFLoader(file_path)
            documents = loader.load()

            if not documents and not text_content:
                logger.warning(f"No content extracted from PDF: {file_path}")
                return False

            # Add extracted text_content as a document if provided
            if text_content:
                from langchain_core.documents import Document
                text_doc = Document(
                    page_content=text_content,
                    metadata={"source": file_path, "document_type": "pdf_text"}
                )
                documents.append(text_doc)
                logger.info(
                    f"Added text_content as document, total documents: {len(documents)}")

            # Add metadata to documents
            for doc in documents:
                # Set userId to empty string if None to satisfy Pinecone metadata requirements
                doc.metadata["userId"] = str(user_id) if user_id else ""
                doc.metadata["document_type"] = "resume" if user_id else "event_document"
                doc.metadata["table_count"] = table_count
                logger.debug(f"Document metadata: {doc.metadata}")

            # Split documents into chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=2000,
                chunk_overlap=800
            )
            chunks = text_splitter.split_documents(documents)

            if not chunks:
                logger.warning(f"No chunks created from PDF: {file_path}")
                return False

            logger.info(f"Split PDF into {len(chunks)} chunks.")

            # Validate metadata for Pinecone
            for chunk in chunks:
                for key, value in chunk.metadata.items():
                    if value is None:
                        logger.error(f"Invalid metadata in chunk: {key} is None")
                        chunk.metadata[key] = ""  # Replace None with empty string
                    elif not isinstance(value, (str, int, float, bool, list)):
                        logger.warning(
                            f"Invalid metadata type for {key}: {type(value)}, converting to string")
                        chunk.metadata[key] = str(value)

            # Add chunks to vectorstore (e.g., Pinecone)
            self.vectorstore.add_documents(chunks)

            logger.info(
                f"Successfully uploaded {len(chunks)} chunks to vector database.")
            return True

        except Exception as e:
            logger.error(f"Error uploading PDF {file_path}: {e}")
            return False

    
    def health_check(self) -> Dict[str, Any]:
        """Checks the health of all components used by the ChatbotAgent."""
        status = {
            "gemini_api": False,
            "pinecone_connection": False,
            "embeddings": False,
            "vector_store": False,
            "overall_health": False
        }
        
        try:
            test_response = self.llm.generate_content("Say 'OK' if you can respond")
            status["gemini_api"] = "OK" in test_response.text
            logger.debug(f"Gemini health check: {status['gemini_api']}")
        except Exception as e:
            logger.error(f"Gemini health check failed: {e}")
            status["gemini_api"] = False
        
        try:
            index_stats = self.index.describe_index_stats()
            status["pinecone_connection"] = True
            logger.debug(f"Pinecone health check: {status['pinecone_connection']}")
        except Exception as e:
            logger.error(f"Pinecone health check failed: {e}")
            status["pinecone_connection"] = False
        
        try:
            test_embedding = self.embeddings.embed_query("test")
            status["embeddings"] = len(test_embedding) > 0
            logger.debug(f"Embeddings health check: {status['embeddings']}")
        except Exception as e:
            logger.error(f"Embeddings health check failed: {e}")
            status["embeddings"] = False
        
        try:
            test_search = self.vectorstore.similarity_search("test", k=1)
            status["vector_store"] = True
            logger.debug(f"Vector store health check: {status['vector_store']}")
        except Exception as e:
            logger.error(f"Vector store health check failed: {e}")
            status["vector_store"] = False
        
        status["overall_health"] = all([
            status["gemini_api"],
            status["pinecone_connection"], 
            status["embeddings"],
            status["vector_store"]
        ])
        
        logger.info(f"ChatbotAgent health status: {status['overall_health']}")
        return status

