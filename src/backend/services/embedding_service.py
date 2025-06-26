import logging
import uuid
from typing import List
import google.generativeai as genai
from pinecone import Pinecone, ServerlessSpec

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for handling text embeddings using Google Gemini and Pinecone."""
    
    def __init__(self, gemini_api_key: str, pinecone_config: dict):
        """Initialize the embedding service with Google Gemini and Pinecone."""
        # Configure Google AI
        genai.configure(api_key=gemini_api_key)
        logger.info("Google AI API configured successfully")
        
        # Initialize Pinecone
        try:
            self.pc = Pinecone(api_key=pinecone_config['api_key'])
            
            # Create index if it doesn't exist
            if pinecone_config['index_name'] not in self.pc.list_indexes().names():
                self.pc.create_index(
                    name=pinecone_config['index_name'],
                    dimension=pinecone_config['dimension'],
                    metric='cosine',  # Better for semantic similarity
                    spec=ServerlessSpec(
                        cloud=pinecone_config['cloud'],
                        region=pinecone_config['region']
                    )
                )
                logger.info(f"Created new Pinecone index: {pinecone_config['index_name']}")
            
            self.pinecone_index = self.pc.Index(pinecone_config['index_name'])
            logger.info("Pinecone initialized successfully")
            
            print(f"\n=== Embedding Service Initialization ===")
            print(f"Embedding Model: Google Gemini embedding-001")
            print(f"Pinecone Index: {pinecone_config['index_name']}")
            print(f"Dimension: {pinecone_config['dimension']}")
            print("=======================================\n")
            
        except Exception as e:
            logger.error(f"Failed to initialize Pinecone: {str(e)}")
            print(f"Error: Failed to initialize Pinecone: {str(e)}")
            raise RuntimeError("Pinecone initialization failed")

    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Google Gemini embedding-001 model."""
        try:
            embeddings = []
            batch_size = 100  # Process in batches to avoid rate limits
            
            logger.info(f"Generating embeddings for {len(texts)} text chunks using Google Gemini")
            print(f"Generating embeddings for {len(texts)} text chunks")
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                logger.debug(f"Processing batch {i//batch_size + 1}/{(len(texts) + batch_size - 1)//batch_size}")
                
                batch_embeddings = []
                for text in batch:
                    try:
                        # Use Google Gemini embedding-001 model
                        result = genai.embed_content(
                            model="models/embedding-001",
                            content=text,
                            task_type="retrieval_document"
                        )
                        batch_embeddings.append(result['embedding'])
                    except Exception as e:
                        logger.error(f"Failed to generate embedding for text chunk: {str(e)}")
                        # Use a zero vector as fallback
                        batch_embeddings.append([0.0] * 768)
                
                embeddings.extend(batch_embeddings)
            
            logger.info(f"Successfully generated {len(embeddings)} embeddings")
            print(f"Successfully generated {len(embeddings)} embeddings")
            return embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            print(f"Error: Failed to generate embeddings: {str(e)}")
            raise

    def store_text_embeddings(self, text_chunks: List[str], filename: str) -> int:
        """Store text embeddings in Pinecone using Google Gemini embeddings."""
        try:
            if not text_chunks:
                logger.warning("No text chunks provided for embedding")
                return 0
                
            logger.info(f"Processing {len(text_chunks)} text chunks for storage")
            print(f"\n=== Pinecone Storage ===")
            print(f"Processing {len(text_chunks)} text chunks")
            
            # Generate embeddings using Google Gemini
            embeddings = self.generate_embeddings(text_chunks)
            
            # Prepare vectors for Pinecone
            vectors = [
                (
                    f"{filename}_{uuid.uuid4()}",  # Unique ID
                    embedding,  # Embedding vector
                    {"text": chunk, "filename": filename}  # Metadata
                )
                for chunk, embedding in zip(text_chunks, embeddings)
            ]
            
            logger.info(f"Upserting {len(vectors)} vectors to Pinecone")
            print(f"Upserting {len(vectors)} vectors")
            print(f"Vector Dimension: {len(vectors[0][1]) if vectors else 'N/A'}")
            
            # Store in Pinecone
            self.pinecone_index.upsert(vectors=vectors)
            
            logger.info(f"Successfully stored {len(vectors)} text embeddings in Pinecone")
            print(f"Successfully stored {len(vectors)} text embeddings")
            print("=======================\n")
            
            return len(vectors)
            
        except Exception as e:
            logger.error(f"Failed to store embeddings: {str(e)}")
            print(f"Error: Failed to store embeddings in Pinecone: {str(e)}")
            return 0

    def search_similar_text(self, query: str, top_k: int = 5) -> List[dict]:
        """Search for similar text chunks using semantic similarity."""
        try:
            # Generate embedding for the query
            query_embedding = self.generate_embeddings([query])[0]
            
            # Search in Pinecone
            results = self.pinecone_index.query(
                vector=query_embedding,
                top_k=top_k,
                include_metadata=True
            )
            
            # Extract relevant information
            similar_texts = []
            for match in results['matches']:
                similar_texts.append({
                    'text': match['metadata']['text'],
                    'filename': match['metadata']['filename'],
                    'score': match['score']
                })
            
            logger.info(f"Found {len(similar_texts)} similar text chunks for query")
            return similar_texts
            
        except Exception as e:
            logger.error(f"Failed to search similar text: {str(e)}")
            return []