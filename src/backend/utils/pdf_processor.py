# src/backend/utils/pdf_processor.py

import json
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass

import pdfplumber
import pandas as pd
import google.generativeai as genai
from pydantic import BaseModel, Field, create_model
from sqlalchemy import create_engine, MetaData, Table, Column, String, Float, Integer, insert, Text
from sqlalchemy.exc import SQLAlchemyError
from fastapi import HTTPException

logger = logging.getLogger(__name__)

@dataclass
class TableInfo:
    """Data class to hold table information."""
    name: str
    schema: Dict[str, str]
    description: str
    data: List[List[str]]
    column_count: int
    context: Optional[Dict[str, str]] = None

class TableSchema(BaseModel):
    """Pydantic model for table schema from Gemini."""
    table_name: str = Field(..., description="Name of the table")
    table_schema: Dict[str, str] = Field(..., description="Column name to type mapping")
    description: str = Field(..., description="Description of the table content")

class PDFProcessor:
    """Enhanced utility class for processing PDF files with Gemini-powered schema inference."""
    
    def __init__(self, database_url: str = None, gemini_api_key: str = None):
        try:
            # Database setup
            if database_url is None:
                from ..config import config
                database_url = config.database_url
                
            self.engine = create_engine(database_url)
            self.metadata = MetaData()
            
            # Gemini setup
            if gemini_api_key is None:
                from ..config import config
                gemini_api_key = config.GEMINI_API_KEY
                
            genai.configure(api_key=gemini_api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Schema storage
            self.schema_file = Path("src/backend/utils/table_schema.json")
            self.schemas = self._load_schemas()
            
            with self.engine.connect() as conn:
                logger.info("Successfully connected to MySQL RDS and Gemini")
                print("Successfully connected to MySQL RDS and Gemini")
        except SQLAlchemyError as e:
            logger.error(f"Database connection failed: {str(e)}")
            print(f"Error: Database connection failed: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Database connection error: {str(e)}")
        except Exception as e:
            logger.error(f"Gemini configuration failed: {str(e)}")
            print(f"Error: Gemini configuration failed: {str(e)}")
            raise HTTPException(
                status_code=500, detail=f"Gemini configuration error: {str(e)}")

    def _load_schemas(self) -> Dict:
        """Load existing table schemas from JSON file."""
        if self.schema_file.exists():
            try:
                with open(self.schema_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load schemas: {e}")
                return {}
        return {}

    def _save_schemas(self):
        """Save table schemas to JSON file."""
        try:
            with open(self.schema_file, 'w') as f:
                json.dump(self.schemas, f, indent=2)
            logger.info(f"Saved schemas to {self.schema_file}")
        except Exception as e:
            logger.error(f"Failed to save schemas: {e}")

    def _get_context_text(self, pdf_path: str, page_num: int, table_position: int) -> dict:
        """Extract 400 characters of text before and after the table for context."""
        try:
            with pdfplumber.open(pdf_path) as pdf:
                page = pdf.pages[page_num - 1]
                text = page.extract_text() or ""
                
                # Simple heuristic: split text around table position
                # This is approximate since we don't have exact table positions
                mid_point = len(text) // 2
                
                # Extract 400 chars before and after the estimated table position
                before_start = max(0, mid_point - 400)
                before_text = text[before_start:mid_point].strip()
                
                after_end = min(len(text), mid_point + 400)
                after_text = text[mid_point:after_end].strip()
                
                return {
                    "before": before_text,
                    "after": after_text
                }
        except Exception as e:
            logger.warning(f"Failed to extract context text: {e}")
            return {"before": "", "after": ""}



    def _generate_detailed_description(self, table_info: TableInfo, stored_row_count: int) -> str:
        """Generate detailed table description after data is stored."""
        # Get context text if available
        context_before = table_info.context.get("before", "") if table_info.context else ""
        context_after = table_info.context.get("after", "") if table_info.context else ""
        
        # Prepare full table preview (first 3 rows + last 2 rows if more than 5 total)
        headers = list(table_info.schema.keys())
        data_rows = table_info.data[1:]  # Skip header
        
        preview_data = []
        if len(data_rows) <= 5:
            preview_data = data_rows
        else:
            preview_data = data_rows[:3] + ["..."] + data_rows[-2:]
        
        # Format table for display
        table_display = []
        table_display.append(headers)
        for row in preview_data:
            if row == "...":
                table_display.append(["..."] * len(headers))
            else:
                # Ensure row matches header length
                formatted_row = row + [""] * (len(headers) - len(row)) if len(row) < len(headers) else row[:len(headers)]
                table_display.append(formatted_row)
        
        table_preview = "\n".join(["\t".join([str(cell) for cell in row]) for row in table_display])
        
        # Create schema summary
        schema_summary = []
        for col_name, col_type in table_info.schema.items():
            type_desc = {
                'string': 'VARCHAR(255) - Text data',
                'text': 'TEXT - Long text content', 
                'integer': 'INT - Whole numbers',
                'float': 'FLOAT - Decimal numbers',
                'currency': 'FLOAT - Monetary values (parsed from currency symbols)',
                'percentage': 'FLOAT - Percentage values (stored as decimal: 0.25 for 25%)'
            }.get(col_type.lower(), f'{col_type.upper()} - Custom type')
            schema_summary.append(f"- {col_name}: {type_desc}")
        
        schema_text = "\n".join(schema_summary)
        
        # Add context section to prompt
        context_section = ""
        if context_before or context_after:
            context_section = f"""
        SURROUNDING CONTEXT:
        Text before table: {context_before[:200]}{'...' if len(context_before) > 200 else ''}
        Text after table: {context_after[:200]}{'...' if len(context_after) > 200 else ''}
        """

        prompt = f"""
        Generate a comprehensive table description for database query generation. This description will help an LLM choose the correct table and generate accurate SQL queries.

        TABLE INFORMATION:
        Table Name: {table_info.name}
        Total Rows Stored: {stored_row_count}
        Column Count: {len(headers)}

        SCHEMA DETAILS:
        {schema_text}

        SAMPLE DATA:
        {table_preview}

        {context_section}

        Provide a clear, concise and simple description that would help an LLM understand when and how to use this table for query generation:
    """

        try:
            response = self.model.generate_content(prompt)
            detailed_description = response.text.strip()
            
            # Clean up any markdown formatting if present
            if "```" in detailed_description:
                detailed_description = detailed_description.replace("```", "").strip()
                
            return detailed_description
            
        except Exception as e:
            logger.error(f"Failed to generate detailed description: {e}")
            # Fallback to basic description
            return f"""Table: {table_info.name}
    Columns: {', '.join(headers)}
    Total Rows: {stored_row_count}
    Purpose: Data table with {len(headers)} columns containing structured information.
    Schema: {dict(table_info.schema)}"""



    def _query_gemini_for_schema(self, table_data: List[List[str]], context_dict: dict, pdf_uuid: str, table_index: int = 1) -> TableSchema:
        """Query Gemini for table schema only (description will be generated later with full data)."""
        # Prepare the table preview (top 3 rows)
        preview_rows = table_data[:3]
        table_preview = "\n".join(["\t".join(row) for row in preview_rows])
        
        prompt = f"""
    Analyze this table data and provide schema information in JSON format.

    Table Preview (first 3 rows):
    {table_preview}

    Please provide a JSON response with:
    1. table_name: A descriptive name for this table (use format: pdf_{pdf_uuid}_descriptive_name)
    2. table_schema: Object mapping column names to SQL types (use: "string", "integer", "float", "text", "currency", "percentage")
    3. description: "TBD" (will be generated later with full data)

Schema type guidelines:
- "currency": For monetary values (e.g., $4.34, €10.50, ¥1000)
- "percentage": For percentage values (e.g., 25%, 0.15%)
- "float": For plain decimal numbers
- "integer": For whole numbers
- "string": For text data
- "text": For longer text content

Example response:
{{
    "table_name": "pdf_{pdf_uuid}_financial_summary",
    "table_schema": {{
        "year": "integer",
        "revenue": "currency",
        "profit_margin": "percentage",
        "description": "text"
    }},
    "description": "Financial summary table showing yearly revenue and profit margins"
}}

Respond with valid JSON only:
"""

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean up the response to extract JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            schema_data = json.loads(response_text)
            return TableSchema(**schema_data)
            
        except Exception as e:
            logger.error(f"Failed to query Gemini for schema: {e}")
            # Fallback to basic schema
            headers = table_data[0] if table_data else []
            fallback_schema = {
                header.lower().replace(" ", "_"): "string" 
                for header in headers
            }
            return TableSchema(
                table_name=f"pdf_{pdf_uuid}_table_{table_index}",
                table_schema=fallback_schema,
                description="Auto-generated table schema"
            )

    def _query_gemini_for_continuation(self, current_table_headers: List[str], new_table_preview: List[List[str]], current_table_data: List[List[str]] = None) -> bool:
        """Query Gemini to check if a table is a continuation of the previous one."""
        current_headers_str = "\t".join(current_table_headers)
        new_preview_str = "\n".join(["\t".join(row) for row in new_table_preview[:3]])
        
        # Include current table context with headers and top 3 data rows
        current_table_context = ""
        if current_table_data and len(current_table_data) > 1:
            # Format: headers + top 3 data rows (skip the header row which is at index 0)
            current_preview_rows = [current_table_headers] + current_table_data[1:4]  # headers + top 3 data rows
            current_table_context = "\n".join(["\t".join(row) for row in current_preview_rows])
        else:
            # Fallback to just headers if no data available
            current_table_context = current_headers_str
        
        prompt = f"""
    Determine if this new table data is a continuation of the previous table.

    Current table (headers + top 3 data rows):
    {current_table_context}

    New table preview (first 3 rows):
    {new_preview_str}

    Analyze if this is a continuation (same structure, no headers) or a new table.

    Respond with JSON only:
    - If it's a continuation: {{"status": true}}
    - If it's a new table: {{"status": false, "reason": "explain why it's not a continuation"}}

    Examples:
    - Same column count, data rows only: {{"status": true}}
    - Different column count: {{"status": false, "reason": "Column count mismatch"}}
    - Different data structure: {{"status": false, "reason": "Data structure differs from previous table"}}

    JSON response:
    """

        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Clean up the response to extract JSON
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]
            
            result = json.loads(response_text)
            
            # Log the reason if it's not a continuation
            if not result.get("status", False):
                reason = result.get("reason", "No reason provided")
                logger.info(f"Table not a continuation: {reason}")
                print(f"  → Not a continuation: {reason}")
            else:
                print(f"  → Confirmed continuation")
                
            return result.get("status", False)
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response for continuation: {e}")
            print(f"  → JSON parsing failed, assuming new table")
            return False
        except Exception as e:
            logger.error(f"Failed to query Gemini for continuation: {e}")
            print(f"  → Query failed, assuming new table")
            return False

    def _parse_numeric_value(self, value: str, expected_type: str) -> Optional[float]:
        """
        Parse numeric values with units (currency, percentages, etc.) into clean numbers.
        
        Args:
            value: The string value to parse
            expected_type: The expected data type (currency, percentage, float, integer)
            
        Returns:
            Parsed numeric value or None if parsing fails
        """
        if not value or not value.strip():
            return None
            
        # Clean the value
        cleaned_value = value.strip()
        
        try:
            # Handle currency values
            if expected_type == "currency":
                # Remove currency symbols and common formatting
                import re
                # Common currency symbols: $, €, £, ¥, ₹, etc.
                currency_pattern = r'[\$€£¥₹₽₩¢₦₨₪₫₡₲₴₸₵₶₷₹₺₻₼₽₾₿]'
                cleaned_value = re.sub(currency_pattern, '', cleaned_value)
                # Remove commas used as thousands separators
                cleaned_value = cleaned_value.replace(',', '')
                # Remove spaces
                cleaned_value = cleaned_value.replace(' ', '')
                # Handle parentheses for negative values (accounting format)
                if cleaned_value.startswith('(') and cleaned_value.endswith(')'):
                    cleaned_value = '-' + cleaned_value[1:-1]
                return float(cleaned_value) if cleaned_value else None
                
            # Handle percentage values
            elif expected_type == "percentage":
                if '%' in cleaned_value:
                    cleaned_value = cleaned_value.replace('%', '').strip()
                    # Convert percentage to decimal (25% -> 0.25)
                    return float(cleaned_value) / 100 if cleaned_value else None
                else:
                    # Assume it's already in decimal format
                    return float(cleaned_value) if cleaned_value else None
                    
            # Handle regular numeric values with potential formatting
            elif expected_type in ["float", "integer"]:
                # Remove common formatting characters
                import re
                # Remove everything except digits, decimal points, minus signs, and 'e' for scientific notation
                cleaned_value = re.sub(r'[^\d\.\-e]', '', cleaned_value)
                
                if expected_type == "integer":
                    # For integers, convert to float first then to int to handle decimal formatting
                    float_val = float(cleaned_value) if cleaned_value else None
                    return int(float_val) if float_val is not None else None
                else:
                    return float(cleaned_value) if cleaned_value else None
                    
            # If not a numeric type, return None
            else:
                return None
                
        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to parse '{value}' as {expected_type}: {e}")
            return None

    def _create_pydantic_model(self, schema_info: TableSchema) -> type:
        """Create a Pydantic model from the schema information with custom validators."""
        from pydantic import BaseModel, Field, field_validator
        from typing import Optional, Any
        
        type_mapping = {
            "string": (str, Field(default="")),
            "integer": (Optional[int], Field(default=None)),
            "float": (Optional[float], Field(default=None)),
            "text": (str, Field(default="")),
            "currency": (Optional[float], Field(default=None, description="Monetary value parsed from currency format")),
            "percentage": (Optional[float], Field(default=None, description="Percentage value as decimal (0.25 for 25%)"))
        }
        
        # Create field annotations dictionary
        annotations = {}
        field_defaults = {}
        
        for col_name, col_type in schema_info.table_schema.items():
            python_type, field_info = type_mapping.get(col_type.lower(), (str, Field(default="")))
            annotations[col_name] = python_type
            field_defaults[col_name] = field_info
        
        # Create a base class with the static method
        class BaseTableModel(BaseModel):
            @staticmethod
            def _parse_numeric_value(value: str, expected_type: str) -> Optional[float]:
                """Parse numeric values with units (currency, percentages, etc.) into clean numbers."""
                if not value or not value.strip():
                    return None
                    
                # Clean the value
                cleaned_value = value.strip()
                
                try:
                    # Handle currency values
                    if expected_type == "currency":
                        # Remove currency symbols and common formatting
                        import re
                        # Common currency symbols: $, €, £, ¥, ₹, etc.
                        currency_pattern = r'[\$€£¥₹₽₩¢₦₨₪₫₡₲₴₸₵₶₷₹₺₻₼₽₾₿]'
                        cleaned_value = re.sub(currency_pattern, '', cleaned_value)
                        # Remove commas used as thousands separators
                        cleaned_value = cleaned_value.replace(',', '')
                        # Remove spaces
                        cleaned_value = cleaned_value.replace(' ', '')
                        # Handle parentheses for negative values (accounting format)
                        if cleaned_value.startswith('(') and cleaned_value.endswith(')'):
                            cleaned_value = '-' + cleaned_value[1:-1]
                        return float(cleaned_value) if cleaned_value else None
                        
                    # Handle percentage values
                    elif expected_type == "percentage":
                        if '%' in cleaned_value:
                            cleaned_value = cleaned_value.replace('%', '').strip()
                            # Convert percentage to decimal (25% -> 0.25)
                            return float(cleaned_value) / 100 if cleaned_value else None
                        else:
                            # Assume it's already in decimal format
                            return float(cleaned_value) if cleaned_value else None
                            
                    # Handle regular numeric values with potential formatting
                    elif expected_type in ["float", "integer"]:
                        # Remove common formatting characters
                        import re
                        # Remove everything except digits, decimal points, minus signs, and 'e' for scientific notation
                        cleaned_value = re.sub(r'[^\d\.\-e]', '', cleaned_value)
                        
                        if expected_type == "integer":
                            # For integers, convert to float first then to int to handle decimal formatting
                            float_val = float(cleaned_value) if cleaned_value else None
                            return int(float_val) if float_val is not None else None
                        else:
                            return float(cleaned_value) if cleaned_value else None
                            
                    # If not a numeric type, return None
                    else:
                        return None
                        
                except (ValueError, TypeError):
                    return None
        
        # Create validators dictionary for numeric fields
        validators = {}
        
        for col_name, col_type in schema_info.table_schema.items():
            if col_type.lower() in ["currency", "percentage", "float", "integer"]:
                # Create a closure to capture the column type
                def make_validator(column_type: str):
                    @field_validator(col_name, mode='before')
                    @classmethod
                    def validate_field(cls, v: Any) -> Any:
                        if v is None or v == "":
                            return None
                        if isinstance(v, (int, float)):
                            return v
                        if isinstance(v, str):
                            parsed = cls._parse_numeric_value(v, column_type)
                            if parsed is not None:
                                return parsed
                            # If parsing fails, try basic float conversion
                            try:
                                return float(v)
                            except (ValueError, TypeError):
                                return None
                        return v
                    return validate_field
                
                validator_func = make_validator(col_type.lower())
                # Use a unique name for each validator
                validators[f'validate_{col_name.replace(" ", "_").replace("-", "_")}'] = validator_func
        
        # Create the model class dynamically
        model_attrs = {
            '__annotations__': annotations,
            **field_defaults,
            **validators
        }
        
        # Create the final model class
        DynamicModel = type(
            f"{schema_info.table_name}Model",
            (BaseTableModel,),
            model_attrs
        )
        
        return DynamicModel

    def _convert_schema_to_sqlalchemy(self, schema_info: TableSchema) -> List[Column]:
        """Convert Gemini schema to SQLAlchemy columns."""
        type_mapping = {
            "string": String(255),
            "integer": Integer,
            "float": Float,
            "text": Text,
            "currency": Float,  # Store currency as float (numeric value only)
            "percentage": Float  # Store percentage as float (decimal format)
        }
        
        columns = []
        for col_name, col_type in schema_info.table_schema.items():
            sqlalchemy_type = type_mapping.get(col_type.lower(), String(255))
            columns.append(Column(col_name, sqlalchemy_type))
        
        return columns

    def extract_and_store_content(self, pdf_path: str) -> Dict[str, Any]:
        """
        Enhanced content extraction with Gemini-powered schema inference.
        Combines extraction and storage into a single intelligent process.
        """
        text_chunks = []
        stored_tables = []
        current_table_info: Optional[TableInfo] = None


        # Generate UUID for unique table naming
        pdf_uuid = str(uuid.uuid4())[:8] 

        logger.info(f"Starting enhanced PDF extraction for file: {pdf_path}")
        print(f"\n=== Enhanced PDF Processing ===")
        print(f"File: {Path(pdf_path).name}")
        print(f"File UUID: {pdf_uuid}")

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    # Extract text for chunks
                    text = page.extract_text()
                    if text:
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

                    # Extract and process tables
                    page_tables = page.extract_tables()
                    logger.info(f"Found {len(page_tables)} tables on page {page_num}")
                    
                    for table_idx, table in enumerate(page_tables, 1):
                        if not table or not table[0]:
                            continue

                        cleaned_table = [
                            [str(cell) if cell is not None else "" for cell in row]
                            for row in table if any(cell.strip() for cell in row if cell is not None)
                        ]

                        if not cleaned_table:
                            continue

                        # Check for transposition
                        if len(cleaned_table) < len(cleaned_table[0]):
                            cleaned_table = list(map(list, zip(*cleaned_table)))

                        print(f"\nProcessing table {table_idx} on page {page_num}")
                        print(f"Table dimensions: {len(cleaned_table)} rows x {len(cleaned_table[0])} columns")

                        # Check if this continues the previous table
                        if (current_table_info and 
                            len(cleaned_table[0]) == current_table_info.column_count):
                            
                            print("Checking if table continues previous one...")
                            is_continuation = self._query_gemini_for_continuation(
                                list(current_table_info.schema.keys()),
                                cleaned_table
                            )
                            
                            if is_continuation:
                                print("✓ Continuing previous table")
                                current_table_info.data.extend(cleaned_table)
                                continue

                        # Finalize previous table if exists
                        if current_table_info:
                            print(f"Finalizing table: {current_table_info.name}")
                            success = self._store_table_with_schema(current_table_info)
                            if success:
                                # Get updated description from schemas
                                updated_schema = self.schemas.get(current_table_info.name, {})
                                stored_tables.append({
                                    "name": current_table_info.name,
                                    "rows": len(current_table_info.data) - 1,  # Exclude header
                                    "description": updated_schema.get('description', current_table_info.description)
                                })

                        # Process new table with Gemini
                        print("Analyzing new table with Gemini...")
                        context_dict = self._get_context_text(pdf_path, page_num, table_idx)
                        # Generate unique table index across all pages
                        global_table_index = len(stored_tables) + 1
                        schema_info = self._query_gemini_for_schema(cleaned_table, context_dict, pdf_uuid, global_table_index)
                        
                        print(f"✓ Gemini analysis complete:")
                        print(f"  Table name: {schema_info.table_name}")
                        print(f"  Schema: {schema_info.table_schema}")
                        print(f"  Description: {schema_info.description}")

                        # Save initial schema to file (description will be updated after storage)
                        self.schemas[schema_info.table_name] = {
                            "schema": schema_info.table_schema,
                            "description": schema_info.description,
                            "pdf_uuid": pdf_uuid,
                            "created_at": pd.Timestamp.now().isoformat(),
                            "status": "processing"
                        }
                        self._save_schemas()
                        print(f"✓ Saved initial schema for {schema_info.table_name}")

                        # Create new table info
                        current_table_info = TableInfo(
                            name=schema_info.table_name,
                            schema=schema_info.table_schema,
                            description=schema_info.description,
                            data=cleaned_table,
                            column_count=len(cleaned_table[0])
                        )
                        # Store context for later use in description generation
                        current_table_info.context = context_dict

                # Finalize the last table
                if current_table_info:
                    print(f"Finalizing last table: {current_table_info.name}")
                    success = self._store_table_with_schema(current_table_info)
                    if success:
                        # Get updated description from schemas
                        updated_schema = self.schemas.get(current_table_info.name, {})
                        stored_tables.append({
                            "name": current_table_info.name,
                            "rows": len(current_table_info.data) - 1,
                            "description": updated_schema.get('description', current_table_info.description)
                        })

            print(f"\n=== Processing Complete ===")
            print(f"Text chunks extracted: {len(text_chunks)}")
            print(f"Tables stored: {len(stored_tables)}")
            for table in stored_tables:
                print(f"  - {table['name']}: {table['rows']}")
            print("===============================\n")

            return {
                "text_chunks": text_chunks,
                "tables_info": stored_tables,
                "schemas_saved": len(stored_tables),
                "pdf_name": Path(pdf_path).stem,
                "pdf_uuid": pdf_uuid
            }

        except Exception as e:
            logger.error(f"Enhanced PDF extraction failed: {str(e)}")
            print(f"Error: Enhanced PDF extraction failed: {str(e)}")
            raise ValueError(f"Enhanced PDF extraction error: {str(e)}")

    def _store_table_with_schema(self, table_info: TableInfo) -> bool:
        """Store table using Gemini-generated schema and Pydantic validation with enhanced numeric parsing."""
        try:
            print(f"\nStoring table: {table_info.name}")
            
            # Create Pydantic model for validation
            schema_info = TableSchema(
                table_name=table_info.name,
                table_schema=table_info.schema,
                description=table_info.description
            )
            pydantic_model = self._create_pydantic_model(schema_info)
            
            # Create SQLAlchemy table
            columns = self._convert_schema_to_sqlalchemy(schema_info)
            table = Table(table_info.name, self.metadata, *columns)
            self.metadata.create_all(self.engine)
            
            print(f"Created table with schema: {table_info.schema}")

            # Process and validate data with enhanced numeric parsing
            headers = list(table_info.schema.keys())
            data_rows = table_info.data[1:]  # Skip header row
            
            validated_rows = []
            parsing_stats = {"success": 0, "failed": 0, "warnings": []}
            
            for row_idx, row in enumerate(data_rows):
                try:
                    # Ensure row length matches headers
                    row = row + [""] * (len(headers) - len(row)) if len(row) < len(headers) else row[:len(headers)]
                    
                    # Pre-process data with custom parsing for numeric types
                    processed_row_dict = {}
                    for header, value in zip(headers, row):
                        col_type = table_info.schema.get(header, "string").lower()
                        cleaned_value = value.strip() if value else ""
                        
                        if col_type in ["currency", "percentage", "float", "integer"] and cleaned_value:
                            # Use enhanced numeric parsing
                            parsed_value = self._parse_numeric_value(cleaned_value, col_type)
                            if parsed_value is not None:
                                processed_row_dict[header] = parsed_value
                                if row_idx < 5:  # Log first 5 successful conversions for debugging
                                    print(f"  ✓ Parsed '{cleaned_value}' → {parsed_value} ({col_type})")
                            else:
                                # If enhanced parsing fails, try basic conversion
                                try:
                                    if col_type == "integer":
                                        processed_row_dict[header] = int(float(cleaned_value.replace(',', '')))
                                    else:
                                        processed_row_dict[header] = float(cleaned_value.replace(',', ''))
                                    parsing_stats["warnings"].append(f"Row {row_idx+1}: Basic parsing used for '{cleaned_value}' in {header}")
                                except (ValueError, TypeError):
                                    processed_row_dict[header] = None
                                    parsing_stats["warnings"].append(f"Row {row_idx+1}: Failed to parse '{cleaned_value}' in {header}, set to NULL")
                        else:
                            # Non-numeric types or empty values
                            processed_row_dict[header] = cleaned_value if cleaned_value else None
                    
                    # Validate with Pydantic (should pass since we pre-processed)
                    try:
                        validated_row = pydantic_model(**processed_row_dict)
                        validated_rows.append(validated_row.model_dump())
                        parsing_stats["success"] += 1
                    except Exception as pydantic_error:
                        logger.warning(f"Row {row_idx + 1} Pydantic validation failed: {pydantic_error}")
                        parsing_stats["failed"] += 1
                        # Try to salvage the row by setting problematic fields to None
                        salvaged_row = {}
                        for header in headers:
                            try:
                                # Test each field individually
                                test_dict = {header: processed_row_dict.get(header)}
                                pydantic_model(**{h: None for h in headers if h != header}, **test_dict)
                                salvaged_row[header] = processed_row_dict.get(header)
                            except:
                                salvaged_row[header] = None
                                parsing_stats["warnings"].append(f"Row {row_idx+1}: Set {header} to NULL due to validation error")
                        
                        try:
                            validated_row = pydantic_model(**salvaged_row)
                            validated_rows.append(validated_row.model_dump())
                            parsing_stats["success"] += 1
                        except:
                            parsing_stats["failed"] += 1
                            continue
                    
                except Exception as e:
                    logger.warning(f"Row {row_idx + 1} processing failed: {e}")
                    parsing_stats["failed"] += 1
                    continue

            # Report parsing statistics
            total_rows = len(data_rows)
            print(f"\nParsing Statistics:")
            print(f"  Total rows processed: {total_rows}")
            print(f"  Successfully validated: {parsing_stats['success']}")
            print(f"  Failed validation: {parsing_stats['failed']}")
            print(f"  Success rate: {(parsing_stats['success']/total_rows*100):.1f}%")
            
            if parsing_stats["warnings"]:
                print(f"  Warnings: {len(parsing_stats['warnings'])}")
                # Show first 5 warnings
                for warning in parsing_stats["warnings"][:5]:
                    print(f"    - {warning}")
                if len(parsing_stats["warnings"]) > 5:
                    print(f"    ... and {len(parsing_stats['warnings']) - 5} more warnings")

            # Insert validated data
            if validated_rows:
                with self.engine.connect() as conn:
                    conn.execute(insert(table), validated_rows)
                    conn.commit()
                
                print(f"✓ Successfully stored {len(validated_rows)} validated rows")
                logger.info(f"Successfully stored {len(validated_rows)} rows in {table_info.name}")

                # Generate detailed description after successful storage
                print("Generating detailed table description...")
                detailed_description = self._generate_detailed_description(table_info, len(validated_rows))
                print(f"✓ Generated detailed description ({len(detailed_description)} characters)")

                # Update schema with detailed description and mark as complete
                if table_info.name in self.schemas:
                    self.schemas[table_info.name]['description'] = detailed_description
                    self.schemas[table_info.name]['status'] = 'complete'
                    self.schemas[table_info.name]['rows_stored'] = len(validated_rows)
                    self._save_schemas()
                    print(f"✓ Updated schema file with detailed description")
                else:
                    logger.warning(f"Table {table_info.name} not found in schemas when updating description")

                return True
            else:
                print("✗ No valid rows to store")
                logger.warning(f"No valid rows to store in {table_info.name}")
                return False

        except Exception as e:
            logger.error(f"Error storing table {table_info.name}: {str(e)}")
            print(f"✗ Error storing table {table_info.name}: {str(e)}")
            return False

    def get_stored_schemas(self) -> Dict:
        """Get all stored table schemas."""
        return self.schemas

    def get_table_info(self, table_name: str) -> Optional[Dict]:
        """Get information about a specific table."""
        return self.schemas.get(table_name)

    # Backward compatibility methods
    def extract_content(self, pdf_path: str) -> Dict[str, Any]:
        """Legacy method for backward compatibility."""
        result = self.extract_and_store_content(pdf_path)
        # Convert to legacy format
        return {
            "text_chunks": result["text_chunks"],
            "tables": [],  # Tables are now stored directly
            "table_names": [info["name"] for info in result["tables_info"]]
        }

    def store_table(self, table_data: List[List[str]], table_name: str) -> bool:
        """Legacy method for backward compatibility."""
        logger.warning("Using legacy store_table method. Consider using extract_and_store_content instead.")
        
        if not table_data:
            return False
            
        # Create basic table info for legacy support
        basic_schema = {f"col_{i}": "string" for i in range(len(table_data[0]))}
        table_info = TableInfo(
            name=table_name,
            schema=basic_schema,
            description="Legacy table",
            data=table_data,
            column_count=len(table_data[0])
        )
        
        return self._store_table_with_schema(table_info)