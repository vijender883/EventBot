import logging
import os
import tempfile
from typing import Dict, List, Any
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Request
from pydantic import BaseModel
from sqlalchemy import create_engine, MetaData, Table, Column, String, Float, Integer, insert
from sqlalchemy.exc import SQLAlchemyError
import pdfplumber
import pandas as pd
from sentence_transformers import SentenceTransformer
from pinecone import Pinecone, ServerlessSpec
from werkzeug.utils import secure_filename
import re
import hashlib
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FastAPI router
router = APIRouter(tags=["pdf_processing"])

# Configuration


class Config:
    def __init__(self):
        self.ALLOWED_EXTENSIONS = os.getenv(
            "ALLOWED_EXTENSIONS", "pdf").split(",")
        self.MAX_FILE_SIZE = int(
            os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))  # 10MB
        self.DATABASE_USER = os.getenv("DATABASE_USER", "admin")
        self.DATABASE_PASSWORD = os.getenv(
            "DATABASE_PASSWORD", "AlphaBeta1212")
        self.DATABASE_HOST = os.getenv(
            "DATABASE_HOST", "testdb.cz60eacw4gt2.ap-south-1.rds.amazonaws.com")
        self.DATABASE_PORT = os.getenv("DATABASE_PORT", "3306")
        self.DATABASE_NAME = os.getenv("DATABASE_NAME", "pdf_db")
        self.PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", None)
        self.PINECONE_INDEX_NAME = os.getenv(
            "PINECONE_INDEX_NAME", "pdf-assistant-index")
        self.PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
        self.PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")
        self.PINECONE_DIMENSION = 768  # Matches all-mpnet-base-v2

        # Validate environment variables
        if not self.DATABASE_PORT.isdigit():
            logger.error(f"Invalid DATABASE_PORT: {self.DATABASE_PORT}")
            raise ValueError("DATABASE_PORT must be a valid integer")
        if not all([self.DATABASE_USER, self.DATABASE_PASSWORD, self.DATABASE_HOST, self.DATABASE_NAME]):
            logger.error("Missing required database environment variables")
            raise ValueError("All database environment variables must be set")
        if not self.PINECONE_API_KEY:
            logger.error("PINECONE_API_KEY environment variable is not set")
            raise ValueError("PINECONE_API_KEY is required")

        # Construct DATABASE_URL
        self.DATABASE_URL = f"mysql+pymysql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}?charset=utf8mb4"
        logger.info(f"Database URL: {self.DATABASE_URL}")


config = Config()

# Initialize Pinecone
try:
    pc = Pinecone(api_key=config.PINECONE_API_KEY)
    if config.PINECONE_INDEX_NAME not in pc.list_indexes().names():
        pc.create_index(
            name=config.PINECONE_INDEX_NAME,
            dimension=config.PINECONE_DIMENSION,
            metric='euclidean',
            spec=ServerlessSpec(
                cloud=config.PINECONE_CLOUD,
                region=config.PINECONE_REGION
            )
        )
    pinecone_index = pc.Index(config.PINECONE_INDEX_NAME)
    logger.info("Pinecone initialized successfully")
    print(f"\n=== Pinecone Initialization ===")
    print(f"Index: {config.PINECONE_INDEX_NAME}")
    print(f"Dimension: {config.PINECONE_DIMENSION}")
    print("==============================\n")
except Exception as e:
    logger.error(f"Failed to initialize Pinecone: {str(e)}")
    print(f"Error: Failed to initialize Pinecone: {str(e)}")
    raise RuntimeError("Pinecone initialization failed")

# Initialize Sentence Transformer
try:
    embedder = SentenceTransformer('all-mpnet-base-v2')
    logger.info("SentenceTransformer initialized successfully")
    print(f"\n=== SentenceTransformer Initialization ===")
    print(f"Model: all-mpnet-base-v2")
    print(
        f"Embedding Dimension: {embedder.get_sentence_embedding_dimension()}")
    print("=========================================\n")
except Exception as e:
    logger.error(f"Failed to load SentenceTransformer: {str(e)}")
    print(f"Error: Failed to load SentenceTransformer: {str(e)}")
    raise RuntimeError("SentenceTransformer initialization failed")

# Pydantic models


class QueryRequest(BaseModel):
    query: str


class AnswerResponse(BaseModel):
    answer: str
    success: bool
    error: str = None


class UploadResponse(BaseModel):
    success: bool
    message: str
    filename: str = None
    tables_stored: int = None
    text_chunks_stored: int = None
    error: str = None


class IndexResponse(BaseModel):
    message: str
    version: str
    endpoints: Dict[str, str]

# Dependency to get ChatbotAgent


def get_chatbot_agent(request: Request):
    chatbot_agent = getattr(request.app.state, "chatbot_agent", None)
    if not chatbot_agent:
        logger.error("ChatbotAgent not found in application state")
        raise HTTPException(
            status_code=500, detail="ChatbotAgent not initialized")
    logger.info("ChatbotAgent retrieved successfully")
    return chatbot_agent

# Helper functions


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


def validate_file_size(file: UploadFile) -> bool:
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)
    logger.info(
        f"File size: {size} bytes, Max allowed: {config.MAX_FILE_SIZE} bytes")
    print(
        f"File size: {size} bytes, Max allowed: {config.MAX_FILE_SIZE} bytes")
    return size <= config.MAX_FILE_SIZE

# PDF Processing Agent


class PDFProcessor:
    def __init__(self, database_url: str):
        try:
            self.engine = create_engine(database_url)
            self.metadata = MetaData()
            with self.engine.connect() as conn:
                logger.info("Successfully connected to MySQL RDS")
                print("Successfully connected to MySQL RDS")
        except SQLAlchemyError as e:
            logger.error(f"Database connection failed: {str(e)}")
            print(f"Error: Database connection failed: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Database connection error: {str(e)}")

    def extract_content(self, pdf_path: str) -> Dict[str, Any]:
        """Extract text and tables from PDF, handling multi-page tables."""
        text_chunks = []
        tables = []
        table_names = []
        current_table = None
        previous_row_count = None
        # Generate a unique prefix based on file content
        with open(pdf_path, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()[:8]
        table_prefix = f"pdf_{file_hash}"

        logger.info(f"Starting PDF extraction for file: {pdf_path}")
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract text
                    text = page.extract_text()
                    if text:
                        logger.debug(
                            f"Extracted text from page {page_num}: {text[:100]}...")
                        sentences = re.split(r'(?<=[.!?])\s+', text)
                        chunk = ""
                        for sentence in sentences:
                            if len(chunk) + len(sentence) < 400:
                                chunk += sentence + " "
                            else:
                                if chunk.strip():
                                    text_chunks.append(chunk.strip())
                                chunk = sentence + " "
                        if chunk.strip():
                            text_chunks.append(chunk.strip())

                    # Extract tables
                    page_tables = page.extract_tables()
                    logger.info(
                        f"Found {len(page_tables)} tables on page {page_num}")
                    for table_idx, table in enumerate(page_tables, 1):
                        if not table or not table[0]:
                            logger.warning(
                                f"Empty table {table_idx} on page {page_num}")
                            continue

                        cleaned_table = [
                            [str(cell) if cell is not None else "" for cell in row]
                            for row in table if any(cell.strip() for cell in row if cell is not None)
                        ]

                        if not cleaned_table:
                            logger.warning(
                                f"Cleaned table {table_idx} on page {page_num} is empty")
                            continue

                        # Check for transposition
                        if len(cleaned_table) < len(cleaned_table[0]):
                            logger.warning(
                                f"Possible transposed table detected on page {page_num}, table {table_idx}")
                            cleaned_table = list(
                                map(list, zip(*cleaned_table)))

                        # Detect if this table continues from previous page
                        table_name = f"{table_prefix}_table_{len(tables) + 1}"
                        if current_table and len(cleaned_table[0]) == previous_row_count:
                            if not self._is_header_row(cleaned_table[0]):
                                logger.debug(
                                    f"Appending table {table_idx} on page {page_num} to current table '{table_name}'")
                                current_table.extend(cleaned_table)
                            else:
                                logger.debug(
                                    f"Skipping header row in table {table_idx} on page {page_num}")
                                current_table.extend(cleaned_table[1:])
                        else:
                            if current_table:
                                logger.info(
                                    f"Finalizing table '{table_names[-1]}' with {len(current_table)} rows")
                                tables.append(current_table)
                                table_names.append(table_names[-1])
                            current_table = cleaned_table
                            previous_row_count = len(cleaned_table[0])
                            table_names.append(table_name)
                            logger.debug(
                                f"New table '{table_name}' started on page {page_num}, table {table_idx}")

                if current_table:
                    logger.info(
                        f"Finalizing last table '{table_names[-1] if table_names else table_name}' with {len(current_table)} rows")
                    tables.append(current_table)
                    if not table_names:
                        table_names.append(table_name)

            logger.info(
                f"Extracted {len(text_chunks)} text chunks and {len(tables)} tables")
            print(f"\n=== PDF Extraction Summary ===")
            print(f"File: {Path(pdf_path).name}")
            print(f"Total Text Chunks Extracted: {len(text_chunks)}")
            print(f"Sample Text Chunks (first 3):")
            for i, chunk in enumerate(text_chunks[:3], 1):
                print(f"  Chunk {i}: {chunk[:100]}...")
            print(f"Total Tables Extracted: {len(tables)}")
            print(f"Extracted Tables: {table_names}")
            print("=============================\n")

            return {"text_chunks": text_chunks, "tables": tables, "table_names": table_names}

        except Exception as e:
            logger.error(f"PDF extraction failed: {str(e)}")
            print(f"Error: Failed to extract content from PDF: {str(e)}")
            raise ValueError(f"PDF extraction error: {str(e)}")

    def _is_header_row(self, row: List[str]) -> bool:
        """Determine if a row is likely a header based on content."""
        is_header = all(cell.strip() and not cell.replace(
            ".", "").isdigit() for cell in row if cell)
        logger.debug(f"Row {row[:50]} is {'header' if is_header else 'data'}")
        return is_header

    def infer_schema(self, table_data: List[List[str]], table_name: str) -> tuple[List[Column], List[str]]:
        """Infer schema for a single table dynamically, without predefined columns."""
        if not table_data or not table_data[0]:
            logger.error(
                f"Invalid table data provided for schema inference for {table_name}")
            print(f"\n=== Schema Inference for Table '{table_name}' ===")
            print("Error: Invalid or empty table data")
            print("================================\n")
            raise ValueError("Invalid table data")

        headers = table_data[0]
        logger.info(
            f"Inferring schema for table '{table_name}' with headers: {headers}")
        print(f"\n=== Schema Inference for Table '{table_name}' ===")
        print(f"Headers: {headers}")
        print(f"Number of Rows (excluding header): {len(table_data) - 1}")

        df = pd.DataFrame(table_data[1:], columns=headers)
        columns = []
        seen = set()

        for idx, col in enumerate(df.columns):
            clean_col = str(col).lower().replace(" ", "_").replace(
                ".", "_").replace(",", "").replace("`", "")
            if not clean_col or clean_col in ["table", "index", "select", "from"]:
                clean_col = f"col_{idx}"

            count = 1
            original = clean_col
            while clean_col in seen:
                clean_col = f"{original}_{count}"
                count += 1
            seen.add(clean_col)

            sample = df[col].dropna().head(5)
            print(f"\nColumn: {clean_col}")
            print(f"Sample Data: {list(sample)}")

            if sample.empty:
                col_type = String(255)
                print(f"Inferred Type: String(255) (empty sample)")
            else:
                try:
                    pd.to_numeric(sample, errors='raise')
                    if all(sample.apply(lambda x: float(x).is_integer() if pd.notnull(x) else True)):
                        col_type = Integer
                        print(
                            f"Inferred Type: Integer (all values are whole numbers)")
                    else:
                        col_type = Float
                        print(f"Inferred Type: Float (contains decimal values)")
                except (ValueError, TypeError):
                    col_type = String(255)
                    print(f"Inferred Type: String(255) (non-numeric values)")

            columns.append(Column(clean_col, col_type))
            logger.info(
                f"Inferred column {clean_col}: {col_type.__class__.__name__}")
            print(
                f"Final Column Name: {clean_col}, Type: {col_type.__class__.__name__}")

        schema_str = [
            f"{c.name}: {c.type.__class__.__name__}" for c in columns]
        print(f"\nFinal Schema for '{table_name}':")
        print(schema_str)
        print("================================\n")

        return columns, schema_str

    def store_table(self, table_data: List[List[str]], table_name: str) -> bool:
        """Store a table in MySQL RDS using SQLAlchemy insert construct."""
        if not table_data or not table_data[0]:
            logger.error(f"No valid data to store for table {table_name}")
            print(f"Error: No valid data to store for table {table_name}")
            return False

        try:
            # Sanitize table name
            table_name = table_name.replace(
                " ", "_").replace(".", "_").replace("`", "")
            base_table_name = table_name
            count = 1
            while self._table_exists(table_name):
                table_name = f"{base_table_name}_{count}"
                count += 1
            logger.info(f"Using table name: {table_name}")
            print(f"\n=== Storing Table '{table_name}' ===")

            # Infer schema
            columns, schema_str = self.infer_schema(table_data, table_name)
            table = Table(table_name, self.metadata, *columns)
            self.metadata.create_all(self.engine)
            logger.info(
                f"Created table {table_name} with schema: {schema_str}")
            print(f"Table Created with Schema: {schema_str}")

            # Log data to be inserted
            data_rows = table_data[1:]  # Skip header
            logger.info(
                f"Preparing to insert {len(data_rows)} rows into {table_name}")
            print(f"Number of Rows to Insert: {len(data_rows)}")
            print(
                f"Sample Data (first 2 rows): {data_rows[:2] if data_rows else 'No data'}")
            print(
                f"Raw Table Data (first 3 rows including header): {table_data[:3] if table_data else 'Empty'}")

            # Collect rows for insertion
            rows_to_insert = []
            for row_idx, row in enumerate(data_rows):
                # Ensure row length matches headers
                row = row + [""] * (len(columns) - len(row)
                                    ) if len(row) < len(columns) else row[:len(columns)]
                # Convert data types
                converted_row = {}
                for col, val in zip(columns, row):
                    if isinstance(col.type, Integer):
                        try:
                            converted_row[col.name] = int(
                                float(val)) if val.strip() else None
                        except (ValueError, TypeError) as e:
                            logger.warning(
                                f"Row {row_idx+1}: Failed to convert value '{val}' to Integer for column {col.name}: {e}")
                            converted_row[col.name] = None
                    elif isinstance(col.type, Float):
                        try:
                            converted_row[col.name] = float(
                                val) if val.strip() else None
                        except (ValueError, TypeError) as e:
                            logger.warning(
                                f"Row {row_idx+1}: Failed to convert value '{val}' to Float for column {col.name}: {e}")
                            converted_row[col.name] = None
                    else:
                        converted_row[col.name] = val if val.strip() else None
                rows_to_insert.append(converted_row)

            # Insert data using SQLAlchemy insert construct
            if rows_to_insert:
                with self.engine.connect() as conn:
                    conn.execute(insert(table), rows_to_insert)
                    conn.commit()
                logger.info(
                    f"Successfully inserted {len(rows_to_insert)} rows into {table_name}")
                print(
                    f"Successfully inserted {len(rows_to_insert)} rows into '{table_name}'")
            else:
                logger.warning(f"No valid rows to insert into {table_name}")
                print(f"Warning: No valid rows to insert into '{table_name}'")

            print("================================\n")
            return True

        except SQLAlchemyError as e:
            logger.error(f"SQL error storing table {table_name}: {str(e)}")
            print(f"Error: SQL error storing table {table_name}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error storing table {table_name}: {str(e)}")
            print(f"Error: Failed to store table {table_name}: {str(e)}")
            return False

    def _table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        try:
            Table(table_name, self.metadata, autoload_with=self.engine)
            logger.debug(f"Table {table_name} exists")
            return True
        except SQLAlchemyError:
            logger.debug(f"Table {table_name} does not exist")
            return False

    def store_text_embeddings(self, text_chunks: List[str], filename: str) -> int:
        """Store text embeddings in Pinecone."""
        try:
            logger.info(
                f"Encoding {len(text_chunks)} text chunks for embeddings")
            print(f"\n=== Pinecone Storage ===")
            print(f"Encoding {len(text_chunks)} text chunks")
            embeddings = embedder.encode(text_chunks, convert_to_numpy=True)
            vectors = [
                (f"{filename}_{uuid.uuid4()}", embedding.tolist(),
                 {"text": chunk, "filename": filename})
                for chunk, embedding in zip(text_chunks, embeddings)
            ]
            logger.info(
                f"Upserting {len(vectors)} vectors to Pinecone index {config.PINECONE_INDEX_NAME}")
            print(f"Upserting {len(vectors)} vectors")
            print(
                f"Vector Dimension: {len(vectors[0][1]) if vectors else 'N/A'}")
            print(f"Index: {config.PINECONE_INDEX_NAME}")
            pinecone_index.upsert(vectors=vectors)
            logger.info(f"Stored {len(vectors)} text embeddings in Pinecone")
            print(f"Successfully stored {len(vectors)} text embeddings")
            print("=======================\n")
            return len(vectors)
        except Exception as e:
            logger.error(f"Failed to store embeddings: {str(e)}")
            print(f"Error: Failed to store embeddings in Pinecone: {str(e)}")
            return 0

# Endpoints


@router.get("/", response_model=IndexResponse)
@router.head("/")
async def index():
    """Root endpoint for the API."""
    logger.info("Accessed root endpoint")
    print("Accessed root endpoint")
    return {
        "message": "PDF Assistant Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "/": "GET, HEAD - Root endpoint",
            "/answer": "POST - Answer questions",
            "/uploadpdf": "POST - Upload PDF files"
        }
    }


@router.post("/answer", response_model=AnswerResponse)
async def answer_question(request: QueryRequest, chatbot_agent=Depends(get_chatbot_agent)):
    """Endpoint to receive a user question and return an answer."""
    try:
        query = request.query.strip()
        if not query:
            logger.warning("Empty query provided")
            print("Error: Empty query provided")
            raise HTTPException(
                status_code=400,
                detail={
                    "answer": "Please provide a valid question.",
                    "success": False,
                    "error": "Empty query provided"
                }
            )
        result = chatbot_agent.answer_question(query)
        logger.info(f"Answered query: {query}")
        print(f"Answered query: {query}")
        return {
            "answer": result["answer"],
            "success": True
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in answer endpoint: {str(e)}")
        print(f"Error: Answer endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "answer": "An error occurred while processing your question.",
                "success": False,
                "error": str(e)
            }
        )


@router.post("/uploadpdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload and process a PDF file, storing text in Pinecone and tables in MySQL."""
    filename = "unknown"  # Default value to avoid UnboundLocalError
    try:
        if not validate_file_size(file):
            logger.warning(
                f"File size exceeds limit: {config.MAX_FILE_SIZE // (1024*1024)}MB")
            print(
                f"Error: File size exceeds limit: {config.MAX_FILE_SIZE // (1024*1024)}MB")
            raise HTTPException(status_code=413, detail={
                "success": False,
                "message": f"File size exceeds {config.MAX_FILE_SIZE // (1024*1024)}MB",
                "error": "File too large"
            })

        if not file.filename:
            logger.warning("No file selected")
            print("Error: No file selected")
            raise HTTPException(status_code=400, detail={
                "success": False,
                "message": "No file selected",
                "error": "Empty filename"
            })

        if not allowed_file(file.filename):
            logger.warning(f"Invalid file type: {file.filename}")
            print(f"Error: Invalid file type: {file.filename}")
            raise HTTPException(status_code=400, detail={
                "success": False,
                "message": "Only PDF files are allowed",
                "error": "Invalid file type"
            })

        filename = secure_filename(file.filename)
        logger.info(f"Processing uploaded file: {filename}")
        print(f"Processing uploaded file: {filename}")
        processor = PDFProcessor(config.DATABASE_URL)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name
            logger.info(f"Temporary file created: {temp_file_path}")
            print(f"Temporary file created: {temp_file_path}")

        try:
            # Extract content
            content = processor.extract_content(temp_file_path)

            # Store text embeddings in Pinecone
            text_chunks_stored = processor.store_text_embeddings(
                content["text_chunks"], filename)

            # Store tables in MySQL
            tables_stored = 0
            for i, table in enumerate(content["tables"], 1):
                table_name = content["table_names"][i-1]
                logger.info(f"Attempting to store table {table_name}")
                print(
                    f"Raw Table Data (first 3 rows): {table[:3] if table else 'Empty'}")
                if processor.store_table(table, table_name):
                    tables_stored += 1

            return {
                "success": True,
                "message": "PDF tables stored in MySQL and text stored in Pinecone successfully",
                "filename": filename,
                "tables_stored": tables_stored,
                "text_chunks_stored": text_chunks_stored
            }

        finally:
            try:
                os.unlink(temp_file_path)
                logger.info(f"Deleted temporary file: {temp_file_path}")
                print(f"Deleted temporary file: {temp_file_path}")
            except Exception as e:
                logger.warning(
                    f"Failed to delete temporary file {temp_file_path}: {str(e)}")
                print(
                    f"Error: Failed to delete temporary file {temp_file_path}: {str(e)}")

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        print(f"Error: Failed to process PDF '{filename}': {str(e)}")
        raise HTTPException(status_code=500, detail={
            "success": False,
            "message": "Failed to process PDF",
            "error": str(e)
        })