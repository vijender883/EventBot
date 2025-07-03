import logging
import json
import mysql.connector
from typing import Dict, Any, List
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from urllib.parse import urlparse, parse_qs
import os

logger = logging.getLogger(__name__)


class TableAgent:
    """
    Agent responsible for generating and executing SQL queries for data processing
    """

    def __init__(self, gemini_api_key: str, schema_path: str = None):
        """
        Initialize the Table Agent with Gemini LLM and schema path

        Args:
            gemini_api_key (str): Google Gemini API key
            schema_path (str, optional): Path to table_schema.json file
        """
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=gemini_api_key,
            temperature=0.1  # Low temperature for precise SQL generation
        )

       # Fix: Use absolute path resolution to avoid working directory issues
        if schema_path:
            self.schema_path = schema_path
        else:
            # Get the project root directory (EventBot/)
            # /path/to/EventBot/src/backend/agents/table_agent.py
            current_file = os.path.abspath(__file__)
            project_root = os.path.dirname(os.path.dirname(
                os.path.dirname(current_file)))  # /path/to/EventBot/
            self.schema_path = os.path.join(
                project_root, 'src', 'backend', 'utils', 'table_schema.json')

        logger.info(f"TableAgent schema path: {self.schema_path}")

        # Load schema during initialization
        self.schema = self._load_schema()
        logger.info("Table Agent initialized successfully")

    def _load_schema(self) -> Dict[str, Any]:
        """
        Load the database schema from table_schema.json

        Returns:
            Dict[str, Any]: Schema data or empty dict on failure
        """
        try:
            # Check if file exists
            if not os.path.exists(self.schema_path):
                logger.error(f"Schema file not found at: {self.schema_path}")
                # Try alternative paths
                alternative_paths = [
                    os.path.join(os.getcwd(), 'src', 'backend',
                                 'utils', 'table_schema.json'),
                    os.path.join(os.path.dirname(__file__), '..',
                                 'utils', 'table_schema.json'),
                    'src/backend/utils/table_schema.json',
                    './src/backend/utils/table_schema.json'
                ]

                for alt_path in alternative_paths:
                    abs_alt_path = os.path.abspath(alt_path)
                    logger.info(f"Trying alternative path: {abs_alt_path}")
                    if os.path.exists(abs_alt_path):
                        self.schema_path = abs_alt_path
                        logger.info(
                            f"Found schema at alternative path: {abs_alt_path}")
                        break
                else:
                    logger.error(
                        "Schema file not found in any expected location")
                    return {}

            with open(self.schema_path, 'r') as f:
                schema = json.load(f)
            logger.info(f"Schema loaded from {self.schema_path}")
            # Extract table names and UUIDs for cleaner logging
            table_info = [(name, info.get('pdf_uuid', 'No UUID'))
                          for name, info in schema.items()]
            logger.debug(f"Schema tables: {table_info}")
            print(f"[DEBUG] Schema loaded successfully: {len(schema)} tables")
            return schema

        except json.JSONDecodeError as e:
            logger.error(
                f"Invalid JSON in schema file {self.schema_path}: {e}")
            return {}
        except Exception as e:
            logger.error(f"Failed to load table_schema.json: {e}")
            return {}

    def process_query(self, query: str, pdf_uuid: str = None) -> str:
        """
        Generate and execute SQL query based on user query

        Args:
            query (str): The user query
            pdf_uuid (str, optional): PDF UUID to filter tables

        Returns:
            str: Formatted query result or error message
        """
        try:
            print(
                f"[DEBUG] Table Agent processing query: {query} with PDF UUID: {pdf_uuid}")

            # Always reload schema to get latest changes
            logger.info("Reloading schema to get latest changes...")
            self.schema = self._load_schema()

            if not self.schema:
                logger.error("No schema available for query processing")
                return f"Error: Could not load schema for query: {query}"

            table_summary = [(name, info.get('pdf_uuid', 'No UUID'))
                             for name, info in self.schema.items()]
            logger.info(
                f"Schema reloaded with {len(self.schema)} tables: {table_summary}")

            # Filter schema by PDF UUID if provided
            filtered_schema = self.schema
            if pdf_uuid:
                filtered_schema = {
                    table_name: table_info for table_name, table_info in self.schema.items()
                    if table_info.get('pdf_uuid') == pdf_uuid
                }
                filtered_tables = [(name, info.get('pdf_uuid', 'No UUID'))
                                   for name, info in filtered_schema.items()]
                logger.info(
                    f"for UUID {pdf_uuid}, filtered tables: {filtered_tables}")
                logger.info(
                    f"Available table names for UUID {pdf_uuid}: {list(filtered_schema.keys())}")
                logger.info(
                    f"All available UUIDs in schema: {[info.get('pdf_uuid') for info in self.schema.values()]}")

                if not filtered_schema:
                    available_uuids = [
                        info.get('pdf_uuid') for info in self.schema.values() if info.get('pdf_uuid')]
                    if available_uuids:
                        logger.warning(
                            f"UUID {pdf_uuid} not found. Available UUIDs: {available_uuids}")
                        logger.info("Using all available tables as fallback")
                        filtered_schema = self.schema
                    else:
                        return f"No tables found for the current document (UUID: {pdf_uuid}). Please upload a PDF first."

            # Generate SQL query with filtered schema
            logger.info(
                f"Passing filtered schema with {len(filtered_schema)} tables to SQL generation")
            sql_query = self._generate_sql_query(query, filtered_schema)

            if "Cannot generate SQL" in sql_query:
                logger.warning(
                    f"LLM could not generate SQL for query: {query}")
                return f"Unable to process data query: {query}. Required tables or columns may be missing. Available tables: {list(filtered_schema.keys())}"

            db_url = os.getenv('database_url')
            parsed_url = urlparse(db_url)
            query_params = parse_qs(parsed_url.query)
            charset = query_params.get('charset', ['utf8mb4'])[0]
            database = parsed_url.path.lstrip('/')

            conn = mysql.connector.connect(
                host=parsed_url.hostname,
                user=parsed_url.username,
                password=parsed_url.password,
                database=database,
                port=parsed_url.port or 3306,
                charset=charset
            )

            # Execute SQL query
            result = self._execute_sql_query(sql_query, query)
            conn.close()
            return result

        except Exception as e:
            logger.error(f"Error in Table Agent: {e}", exc_info=True)
            return f"Error processing query: {query}"

    def _generate_sql_query(self, query: str, schema: dict = None) -> str:
        """
        Generate a MySQL SELECT query using the LLM, supporting dynamic multi-table joins

        Args:
            query (str): User query
            schema (dict): Schema to use (if None, uses self.schema)

        Returns:
            str: Generated SQL query or error message
        """
        if schema is None:
            schema = self.schema

        # Validate that schema is not empty
        if not schema:
            logger.error("Empty schema provided for SQL generation")
            return "Cannot generate SQL for this query - no schema available"
        schema_summary = [(name, info.get('pdf_uuid', 'No UUID'))
                          for name, info in schema.items()]
        logger.info(f"Processing SQL generation with tables: {schema_summary}")

        system_prompt = """
        You are an expert SQL query generator. Based on the provided database schema and user query, generate a valid MySQL SELECT query.
        - Use only the tables and columns defined in the schema.
        - Table names may contain special characters (e.g., `pdf_9aec543c_patient_data`).
        - ALWAYS use backticks around table and column names to handle special characters.
        - When filtering by PDF UUID, only use tables that match the current document context.
        - Map schema data types to MySQL types: "string" to VARCHAR, "integer" to INT, "text" to TEXT.
        - Ensure the query is syntactically correct and optimized for MySQL.
        - Do not include INSERT, UPDATE, or DELETE statements.
        - If the query cannot be answered with the schema (e.g., missing tables or columns), return "Cannot generate SQL for this query."
        - Return only the SQL query, without explanations or additional text.
        - If aggregations (e.g., COUNT, SUM, AVG) are needed, use them appropriately.
        - For queries requiring data from multiple tables, use appropriate JOINs (e.g., LEFT JOIN, INNER JOIN) based on relationships.
        - Relationships: For example, if `pdf_9aec543c_patient_data` has a `Patient ID` column and `pdf_9aec543c_appointments` has a `Patient ID` column, join them on this key.
        - Use LEFT JOIN when data from one table is optional, and INNER JOIN when data must exist in both tables.
        - Only include tables necessary for the query to avoid unnecessary complexity.
        - If the query requires data from multiple tables, ensure to join them correctly based on their relationships.
        - If the query requires data from a single table, use that table directly.
        - Example: For a query like "List patient names and their appointment dates," join `pdf_9aec543c_patient_data` and `pdf_9aec543c_appointments` on `Patient ID`.

        Schema:
        {schema}

        User Query: {query}
        """

        formatted_prompt = system_prompt.format(
            schema=json.dumps(schema, indent=2),
            query=query
        )
        logger.debug(f"Formatted prompt for LLM: {formatted_prompt}")

        messages = [
            SystemMessage(content=formatted_prompt),
            HumanMessage(content=f"Generate SQL for query: {query}")
        ]

        try:
            response = self.llm.invoke(messages)
            sql_query = response.content.strip()
            # Remove Markdown code block markers if present
            if sql_query.startswith('```sql'):
                sql_query = sql_query.replace(
                    '```sql', '').replace('```', '').strip()
            logger.debug(f"Raw LLM response: {response.content}")
            print(f"[DEBUG] Raw LLM response: {response.content}")
            logger.debug(f"Cleaned SQL query: {sql_query}")
            print(f"[DEBUG] Cleaned SQL query: {sql_query}")
            return sql_query
        except Exception as e:
            logger.error(f"Error generating SQL query: {e}")
            return f"Cannot generate SQL for this query"

    def _execute_sql_query(self, sql_query: str, original_query: str) -> str:
        """
        Execute the SQL query on the MySQL database

        Args:
            sql_query (str): SQL query to execute
            original_query (str): Original user query for context

        Returns:
            str: Formatted query result or error message
        """
        try:
            # Database URL (prefer environment variable)
            db_url = os.getenv(
                'database_url'
            )

            # Parse the database URL
            parsed_url = urlparse(db_url)
            query_params = parse_qs(parsed_url.query)
            charset = query_params.get('charset', ['utf8mb4'])[0]
            database = parsed_url.path.lstrip('/')

            # Connect to MySQL
            conn = mysql.connector.connect(
                host=parsed_url.hostname,
                user=parsed_url.username,
                password=parsed_url.password,
                database=database,
                port=parsed_url.port or 3306,
                charset=charset
            )
            cursor = conn.cursor()
            logger.debug(f"Connected to MySQL database: {database}")
            print(f"[DEBUG] Connected to MySQL database: {database}")

            # Execute the query
            cursor.execute(sql_query)
            results = cursor.fetchall()
            column_names = [desc[0]
                            for desc in cursor.description] if cursor.description else []
            logger.debug(f"Query executed successfully. Results: {results}")
            print(f"[DEBUG] Query execution results: {results}")

            # Format the results based on query type
            if results:
                # Check if it's a count/aggregation query
                if len(results) == 1 and len(results[0]) == 1:
                    value = results[0][0]
                    if "count" in original_query.lower() or "number" in original_query.lower():
                        return f"Result: {value}"
                    else:
                        return f"Result: {value}"
                else:
                    # Format as table for multiple results
                    result_text = "Query Results:\n"
                    if column_names:
                        result_text += " | ".join(column_names) + "\n"
                        result_text += "-" * \
                            (len(" | ".join(column_names))) + "\n"

                    for row in results[:10]:  # Limit to first 10 rows
                        result_text += " | ".join(str(cell)
                                                  for cell in row) + "\n"

                    if len(results) > 10:
                        result_text += f"... and {len(results) - 10} more rows"

                    return result_text
            else:
                logger.warning(f"No results returned for query: {sql_query}")
                return f"No results found for query: {original_query}"

        except mysql.connector.Error as db_err:
            logger.error(f"MySQL error: {db_err}")
            return f"Database error while processing query: {original_query}"
        except Exception as e:
            logger.error(f"Error executing SQL query: {e}")
            return f"Error executing query: {original_query}"
        finally:
            if 'cursor' in locals():
                cursor.close()
            if 'conn' in locals():
                conn.close()
            logger.debug("MySQL connection closed")

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check for the Table Agent

        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            # Test LLM connection
            test_response = self.llm.invoke([HumanMessage(content="Hello")])
            # Check schema availability
            schema_loaded = bool(self.schema)
            schema_path_exists = os.path.exists(self.schema_path)

            # Test database connection
            db_url = os.getenv(
                'database_url',
                'mysql+pymysql://admin:AlphaBeta1212@mydb.ch44qeeiq2ju.ap-south-1.rds.amazonaws.com:3306/My_database?charset=utf8mb4'
            )
            parsed_url = urlparse(db_url)
            query_params = parse_qs(parsed_url.query)
            charset = query_params.get('charset', ['utf8mb4'])[0]
            database = parsed_url.path.lstrip('/')

            conn = mysql.connector.connect(
                host=parsed_url.hostname,
                user=parsed_url.username,
                password=parsed_url.password,
                database=database,
                port=parsed_url.port or 3306,
                charset=charset
            )

            conn.close()

            return {
                "table_agent": True,
                "llm_connection": True,
                "schema_loaded": schema_loaded,
                "schema_path_exists": schema_path_exists,
                "schema_path": self.schema_path,
                "db_connection": True,
            }
        except Exception as e:
            logger.error(f"Table Agent health check failed: {e}")
            return {
                "table_agent": False,
                "llm_connection": False,
                "schema_loaded": bool(self.schema),
                "schema_path_exists": os.path.exists(self.schema_path) if hasattr(self, 'schema_path') else False,
                "schema_path": getattr(self, 'schema_path', 'Not set'),
                "db_connection": False,
                "tables_valid": False,
                "missing_tables": [],
                "overall_health": False,
                "error": str(e)
            }

    def _get_table_summary(self, schema_dict: Dict[str, Any]) -> List[tuple]:
        """
        Create a clean summary of tables with just name and UUID

        Args:
            schema_dict: Schema dictionary to summarize

        Returns:
            List of tuples containing (table_name, uuid)
        """
        return [(name, info.get('pdf_uuid', 'No UUID')) for name, info in schema_dict.items()]
