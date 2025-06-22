import pymysql
from sqlalchemy.exc import SQLAlchemyError, ProgrammingError
from sqlalchemy import create_engine, Table, Column, MetaData, String, Float, Integer
import pandas as pd
import pdfplumber
from werkzeug.utils import secure_filename
from typing import Dict, Any, List
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Depends
from pathlib import Path
import logging
import tempfile
import os


logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

# FastAPI router
router = APIRouter(tags=["chat"])

# Configuration


class Config:
    def __init__(self):
        self.ALLOWED_EXTENSIONS = os.getenv(
            "ALLOWED_EXTENSIONS", "pdf").split(",")
        self.MAX_FILE_SIZE = int(
            os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))  # 10MB
        self.DATABASE_USER = os.getenv("DATABASE_USER", "pdf_user")
        self.DATABASE_PASSWORD = os.getenv(
            "DATABASE_PASSWORD", "your_password")
        self.DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
        self.DATABASE_PORT = os.getenv("DATABASE_PORT", "3306")
        self.DATABASE_NAME = os.getenv("DATABASE_NAME", "pdf_assistant")
        self.DATABASE_URL = f"mysql+pymysql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}?charset=utf8mb4"
        logger.info(f"Database URL: {self.DATABASE_URL}")


config = Config()

# Dependency to get ChatbotAgent


def get_chatbot_agent(request: Request):
    chatbot_agent = getattr(request.app.state, "chatbot_agent", None)
    if not chatbot_agent:
        raise HTTPException(
            status_code=500, detail="ChatbotAgent not initialized")
    return chatbot_agent

# Helper functions


def allowed_file(filename: str) -> bool:
    """Check if the uploaded file is allowed based on its extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


def validate_request_size(file: UploadFile) -> bool:
    """Validate file size against MAX_FILE_SIZE."""
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)
    return size <= config.MAX_FILE_SIZE

# Pydantic models


class QueryRequest(BaseModel):
    query: str


class HealthResponse(BaseModel):
    status: str
    message: str = None
    healthy: bool
    health: Dict[str, Any] = None


class AnswerResponse(BaseModel):
    answer: str
    success: bool
    error: str = None


class UploadResponse(BaseModel):
    success: bool
    message: str
    filename: str = None
    error: str = None
    tables_stored: int = None


class IndexResponse(BaseModel):
    message: str
    version: str
    endpoints: Dict[str, str]

# PDF Extractor Agent


class PDFExtractorAgent:
    def extract_content(self, pdf_path: str) -> Dict[str, Any]:
        """Extract unstructured text and tables from a PDF."""
        try:
            text_content = []
            tables = []
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    # Extract unstructured text
                    text = page.extract_text()
                    if text:
                        text_content.append(text)
                    # Extract tables
                    page_tables = page.extract_tables()
                    for table in page_tables:
                        # Convert table to list of lists, handling None values
                        cleaned_table = [
                            [str(cell) if cell is not None else "" for cell in row] for row in table]
                        tables.append(cleaned_table)
            return {
                "text": "\n".join(text_content),
                "tables": tables
            }
        except Exception as e:
            logger.error(f"Error extracting PDF content: {e}")
            raise ValueError(f"Failed to extract PDF content: {str(e)}")

# Table Extractor & Schema Inference Agent


class TableExtractorAgent:
    def __init__(self, database_url: str):
        try:
            self.engine = create_engine(database_url)
            self.metadata = MetaData()
            # Test connection
            with self.engine.connect() as connection:
                logger.info("Successfully connected to MySQL database")
        except SQLAlchemyError as e:
            logger.error(f"Failed to connect to MySQL database: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Database connection error: {str(e)}"
            )

    def infer_schema(self, table_data: List[List[str]], table_name: str) -> List[Column]:
        """Infer schema for a table based on its data."""
        if not table_data or not table_data[0]:
            logger.error(
                f"Empty or invalid table data provided for table {table_name}")
            raise ValueError("Empty table data provided")

        # Convert to DataFrame for analysis
        try:
            df = pd.DataFrame(table_data[1:], columns=table_data[0])
        except Exception as e:
            logger.error(
                f"Failed to create DataFrame for table {table_name}: {str(e)}")
            raise ValueError(f"Invalid table data format: {str(e)}")

        columns = []
        seen = set()

        for idx, col in enumerate(df.columns):
            # Sample non-empty values
            sample = df[col].dropna().head(5)
            if sample.empty:
                col_type = String(255)  # MySQL requires length for VARCHAR
            else:
                try:
                    # Try converting to numeric
                    pd.to_numeric(sample, errors='raise')
                    col_type = Integer if all(sample.apply(
                        lambda x: float(x).is_integer())) else Float
                except (ValueError, TypeError):
                    col_type = String(255)  # MySQL requires length for VARCHAR

            # Clean column name for MySQL
            clean_col = str(col).lower().replace(" ", "_").replace(".", "_").replace(
                ",", "").replace("`", "").replace("$", "").replace("'", "").replace("\"", "")
            # Handle empty or reserved names
            if not clean_col or clean_col in ["table", "index", "select", "from"]:
                clean_col = f"col_{idx}"

            # Ensure uniqueness
            original = clean_col
            count = 1
            while clean_col in seen:
                clean_col = f"{original}_{count}"
                count += 1
            seen.add(clean_col)

            columns.append(Column(clean_col, col_type))
            logger.debug(
                f"Inferred column {clean_col} as {col_type.__class__.__name__} for table {table_name}")

        if not columns:
            logger.error(f"No columns inferred for table {table_name}")
            raise ValueError("No valid columns inferred from table data")

        return columns

    def store_table(self, table_data: List[List[str]], table_name: str) -> bool:
        """Store a table in the MySQL database with inferred schema."""
        # Validate table data
        if not table_data or len(table_data) < 2 or not table_data[0]:
            logger.warning(f"Skipping empty or invalid table {table_name}")
            return False

        try:
            # Sanitize table name for MySQL
            table_name = table_name.replace(" ", "_").replace(
                ".", "_").replace("`", "").replace("\"", "")
            if not table_name or table_name.lower() in ["table", "index", "select", "from"]:
                table_name = f"tbl_{pd.util.hash_pandas_object(pd.Series(table_data)).sum()}"

            # Ensure table name is unique
            base_table_name = table_name
            count = 1
            while self._table_exists(table_name):
                table_name = f"{base_table_name}_{count}"
                count += 1

            # Infer schema
            columns = self.infer_schema(table_data, table_name)

            # Create table in database
            table = Table(table_name, self.metadata, *columns)
            self.metadata.create_all(self.engine)

            # Convert to DataFrame for storage
            df = pd.DataFrame(table_data[1:], columns=table_data[0])
            # Rename columns to match schema
            df.columns = [col.name for col in columns]

            # Store data
            df.to_sql(table_name, self.engine,
                      if_exists='replace', index=False)
            logger.info(f"Successfully stored table {table_name}")
            return True
        except ProgrammingError as e:
            logger.error(f"Schema error for table {table_name}: {str(e)}")
            return False
        except SQLAlchemyError as e:
            logger.error(f"Error storing table {table_name}: {str(e)}")
            return False

    def _table_exists(self, table_name: str) -> bool:
        """Check if a table exists in the database."""
        try:
            Table(table_name, self.metadata, autoload_with=self.engine)
            return True
        except SQLAlchemyError:
            return False

# Endpoints


@router.get("/health", response_model=HealthResponse)
async def health_check(chatbot_agent=Depends(get_chatbot_agent)):
    """Health check endpoint for the chatbot service."""
    try:
        health_status = chatbot_agent.health_check()
        return {
            "status": "success",
            "health": health_status,
            "healthy": health_status["overall_health"]
        }
    except Exception as e:
        logger.error(f"Health check endpoint error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": str(e),
                "healthy": False
            }
        )


@router.post("/answer", response_model=AnswerResponse)
async def answer_question(request: QueryRequest, chatbot_agent=Depends(get_chatbot_agent)):
    """Endpoint to receive a user question and return an answer."""
    try:
        query = request.query.strip()
        if not query:
            raise HTTPException(
                status_code=400,
                detail={
                    "answer": "Please provide a valid question.",
                    "success": False,
                    "error": "Empty query provided"
                }
            )
        result = chatbot_agent.answer_question(query)
        return {
            "answer": result["answer"],
            "success": True
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in answer endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "answer": "An error occurred while processing your question.",
                "success": False,
                "error": str(e)
            }
        )


@router.post("/uploadpdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...), chatbot_agent=Depends(get_chatbot_agent)):
    """Endpoint to upload and process a PDF file."""
    try:
        if not validate_request_size(file):
            raise HTTPException(
                status_code=413,
                detail={
                    "success": False,
                    "message": f"File too large. Maximum size is {config.MAX_FILE_SIZE // (1024*1024)}MB",
                    "error": "File size exceeded"
                }
            )

        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "message": "No file selected",
                    "error": "Empty filename"
                }
            )

        if not allowed_file(file.filename):
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "message": "Only PDF files are allowed",
                    "error": "Invalid file type"
                }
            )

        filename = secure_filename(file.filename)
        if not filename:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "message": "Invalid filename",
                    "error": "Filename not secure"
                }
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        try:
            user_id = None
            if 'resume' in filename.lower() or 'cv' in filename.lower():
                user_id = Path(filename).stem

            # Initialize agents
            pdf_extractor = PDFExtractorAgent()
            table_extractor = TableExtractorAgent(config.DATABASE_URL)

            # Extract content
            content = pdf_extractor.extract_content(temp_file_path)

            # Process tables
            tables_stored = 0
            for i, table_data in enumerate(content["tables"]):
                table_name = f"{Path(filename).stem}_table_{i+1}"
                logger.debug(
                    f"Processing table {table_name} with {len(table_data)} rows")
                if table_extractor.store_table(table_data, table_name):
                    tables_stored += 1

            # Pass text and table metadata to ChatbotAgent
            success = chatbot_agent.upload_data(
                temp_file_path,
                user_id,
                text_content=content["text"],
                table_count=tables_stored
            )

            if success:
                logger.info(f"Successfully processed PDF upload: {filename}")
                return {
                    "success": True,
                    "message": f"PDF '{filename}' uploaded and processed successfully",
                    "filename": filename,
                    "tables_stored": tables_stored
                }
            else:
                logger.warning(f"Failed to process PDF upload: {filename}")
                raise HTTPException(
                    status_code=500,
                    detail={
                        "success": False,
                        "message": "Failed to process the PDF file",
                        "error": "Processing failed",
                        "tables_stored": tables_stored
                    }
                )

        finally:
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(
                    f"Failed to delete temporary file {temp_file_path}: {e}")

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in upload endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": "An error occurred while processing your upload",
                "error": str(e)
            }
        )


@router.get("/", response_model=IndexResponse)
@router.head("/")
async def index():
    """Root endpoint for the API."""
    return {
        "message": "PDF Assistant Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "/health": "GET - Health check",
            "/answer": "POST - Answer questions",
            "/uploadpdf": "POST - Upload PDF files"
        }
    }