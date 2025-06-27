# src/backend/services/clear_data_service.py
import logging
import traceback
from typing import Dict, Any
import asyncio
from contextlib import asynccontextmanager

# Database imports
import pymysql
from sqlalchemy import create_engine, text, MetaData
from sqlalchemy.exc import SQLAlchemyError

# Pinecone imports
try:
    from pinecone import Pinecone
except ImportError:
    Pinecone = None
import os
import json
from pathlib import Path
from ..config import config

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DataClearService:
    """Service for clearing all data from Pinecone and MySQL database."""
    
    def __init__(self):
        self.config = config
        # Path to table schema file
        self.table_schema_path = Path(__file__).parent.parent / "utils" / "table_schema.json"
        
    async def clear_all_data(self) -> Dict[str, Any]:
        """
        Clear all data from both Pinecone index and MySQL database.
        
        Returns:
            Dict containing success status and details of operations
        """
        logger.info("Starting complete data clearing operation")
        
        results = {
            "success": True,
            "operations": {
                "pinecone": {"success": False, "message": "", "details": {}},
                "mysql": {"success": False, "message": "", "details": {}}
            },
            "summary": ""
        }
        
        # Clear Pinecone data
        pinecone_result = await self._clear_pinecone_data()
        results["operations"]["pinecone"] = pinecone_result
        
        # Clear MySQL data
        mysql_result = await self._clear_mysql_data()
        results["operations"]["mysql"] = mysql_result

        # Clear table schema file
        schema_result = await self._clear_table_schema()
        results["operations"]["table_schema"] = schema_result
        
        # Determine overall success
        overall_success = (
            results["operations"]["pinecone"]["success"] and 
            results["operations"]["mysql"]["success"] and
            results["operations"]["table_schema"]["success"]
        )
        results["success"] = overall_success
        
        # Create summary
        if overall_success:
            results["summary"] = "All data successfully cleared from both Pinecone and MySQL"
            logger.info("Data clearing operation completed successfully")
        else:
            failed_ops = []
            if not results["operations"]["pinecone"]["success"]:
                failed_ops.append("Pinecone")
            if not results["operations"]["mysql"]["success"]:
                failed_ops.append("MySQL")
            if not results["operations"]["table_schema"]["success"]:
                failed_ops.append("Table Schema")
            results["summary"] = f"Data clearing failed for: {', '.join(failed_ops)}"
            logger.error(f"Data clearing operation failed for: {', '.join(failed_ops)}")
        
        return results
    
    async def _clear_pinecone_data(self) -> Dict[str, Any]:
        """Clear all vectors from Pinecone index."""
        logger.info("Starting Pinecone data clearing")
        
        result = {
            "success": False,
            "message": "",
            "details": {
                "vectors_deleted": 0,
                "index_name": self.config.PINECONE_INDEX_NAME
            }
        }
        
        try:
            # Validate Pinecone configuration
            if not self.config.PINECONE_API_KEY:
                result["message"] = "Pinecone API key not configured"
                logger.error("Pinecone API key not found in configuration")
                return result
            
            if not Pinecone:
                result["message"] = "Pinecone library not available"
                logger.error("Pinecone library not installed")
                return result
            
            # Initialize Pinecone
            pc = Pinecone(api_key=self.config.PINECONE_API_KEY)
            
            # Check if index exists
            indexes = pc.list_indexes()
            index_names = [idx.name for idx in indexes]
            
            if self.config.PINECONE_INDEX_NAME not in index_names:
                result["success"] = True
                result["message"] = f"Index '{self.config.PINECONE_INDEX_NAME}' does not exist - nothing to clear"
                logger.info(f"Pinecone index '{self.config.PINECONE_INDEX_NAME}' does not exist")
                return result
            
            # Get index
            index = pc.Index(self.config.PINECONE_INDEX_NAME)
            
            # Get index stats before deletion
            stats = index.describe_index_stats()
            total_vectors = stats.get('total_vector_count', 0)
            logger.info(f"Found {total_vectors} vectors in index '{self.config.PINECONE_INDEX_NAME}'")
            
            if total_vectors == 0:
                result["success"] = True
                result["message"] = "Pinecone index is already empty"
                logger.info("Pinecone index is already empty")
                return result
            
            # Delete all vectors by clearing the entire namespace
            # First, try to delete all vectors in the default namespace
            try:
                index.delete(delete_all=True)
                logger.info("Successfully deleted all vectors from default namespace")
            except Exception as e:
                logger.warning(f"Error deleting from default namespace: {e}")
                # Try alternative method - get all namespaces and delete each
                try:
                    namespaces = stats.get('namespaces', {})
                    for namespace in namespaces.keys():
                        if namespace:  # Don't delete empty string namespace yet
                            index.delete(delete_all=True, namespace=namespace)
                            logger.info(f"Deleted all vectors from namespace: {namespace}")
                    
                    # Delete from default namespace (empty string)
                    index.delete(delete_all=True)
                    logger.info("Deleted all vectors from default namespace")
                    
                except Exception as inner_e:
                    raise Exception(f"Failed to delete vectors: {str(inner_e)}")
            
            # Wait a moment for deletion to propagate
            await asyncio.sleep(2)
            
            # Verify deletion
            final_stats = index.describe_index_stats()
            remaining_vectors = final_stats.get('total_vector_count', 0)
            
            if remaining_vectors == 0:
                result["success"] = True
                result["message"] = f"Successfully cleared {total_vectors} vectors from Pinecone index"
                result["details"]["vectors_deleted"] = total_vectors
                logger.info(f"Successfully cleared {total_vectors} vectors from Pinecone")
            else:
                result["message"] = f"Partial deletion: {remaining_vectors} vectors still remain"
                result["details"]["vectors_deleted"] = total_vectors - remaining_vectors
                logger.warning(f"Partial deletion: {remaining_vectors} vectors still remain")
            
        except Exception as e:
            error_msg = f"Error clearing Pinecone data: {str(e)}"
            result["message"] = error_msg
            logger.error(f"Pinecone clearing failed: {e}", exc_info=True)
        
        return result
    
    async def _clear_mysql_data(self) -> Dict[str, Any]:
        """Clear all tables from MySQL database."""
        logger.info("Starting MySQL data clearing")
        
        result = {
            "success": False,
            "message": "",
            "details": {
                "tables_dropped": [],
                "tables_failed": [],
                "database_name": self.config.DATABASE_NAME
            }
        }
        
        try:
            # Validate database configuration
            try:
                self.config.validate_database_config()
            except ValueError as e:
                result["message"] = f"Database configuration invalid: {str(e)}"
                logger.error(f"Database configuration validation failed: {e}")
                return result
            
            # Create database connection
            engine = create_engine(
                self.config.database_url,
                pool_pre_ping=True,
                pool_recycle=300
            )
            
            # Get all table names
            with engine.connect() as connection:
                # Disable foreign key checks temporarily
                connection.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
                
                # Get all table names
                tables_query = text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = :db_name
                    AND table_type = 'BASE TABLE'
                """)
                
                tables_result = connection.execute(
                    tables_query, 
                    {"db_name": self.config.DATABASE_NAME}
                )
                table_names = [row[0] for row in tables_result.fetchall()]
                
                if not table_names:
                    result["success"] = True
                    result["message"] = "No tables found in database - nothing to clear"
                    logger.info("No tables found in MySQL database")
                    # Re-enable foreign key checks
                    connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                    connection.commit()
                    return result
                
                logger.info(f"Found {len(table_names)} tables to drop: {table_names}")
                
                # Drop each table
                dropped_tables = []
                failed_tables = []
                
                for table_name in table_names:
                    try:
                        drop_query = text(f"DROP TABLE IF EXISTS `{table_name}`")
                        connection.execute(drop_query)
                        dropped_tables.append(table_name)
                        logger.info(f"Successfully dropped table: {table_name}")
                    except Exception as e:
                        failed_tables.append({"table": table_name, "error": str(e)})
                        logger.error(f"Failed to drop table {table_name}: {e}")
                
                # Re-enable foreign key checks
                connection.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
                connection.commit()
                
                # Update results
                result["details"]["tables_dropped"] = dropped_tables
                result["details"]["tables_failed"] = failed_tables
                
                if failed_tables:
                    result["message"] = f"Dropped {len(dropped_tables)} tables, {len(failed_tables)} failed"
                    logger.warning(f"Partial success: {len(failed_tables)} tables failed to drop")
                else:
                    result["success"] = True
                    result["message"] = f"Successfully dropped all {len(dropped_tables)} tables"
                    logger.info(f"Successfully dropped all {len(dropped_tables)} tables")
        
        except SQLAlchemyError as e:
            error_msg = f"Database error while clearing MySQL data: {str(e)}"
            result["message"] = error_msg
            logger.error(f"MySQL clearing failed with database error: {e}", exc_info=True)
        except Exception as e:
            error_msg = f"Error clearing MySQL data: {str(e)}"
            result["message"] = error_msg
            logger.error(f"MySQL clearing failed: {e}", exc_info=True)
        
        return result
    
    async def _clear_table_schema(self) -> Dict[str, Any]:
        """Clear the table schema JSON file."""
        logger.info("Starting table schema file clearing")
        
        result = {
            "success": False,
            "message": "",
            "details": {
                "file_path": str(self.table_schema_path),
                "file_existed": False,
                "schemas_cleared": 0
            }
        }
        
        try:
            # Check if file exists
            if not self.table_schema_path.exists():
                result["success"] = True
                result["message"] = "Table schema file does not exist - nothing to clear"
                logger.info(f"Table schema file does not exist: {self.table_schema_path}")
                return result
            
            # Read current content to get count
            try:
                with open(self.table_schema_path, 'r', encoding='utf-8') as f:
                    current_data = json.load(f)
                
                if isinstance(current_data, dict):
                    schema_count = len(current_data)
                elif isinstance(current_data, list):
                    schema_count = len(current_data)
                else:
                    schema_count = 1 if current_data else 0
                    
                result["details"]["file_existed"] = True
                result["details"]["schemas_cleared"] = schema_count
                logger.info(f"Found {schema_count} schemas in table schema file")
                
            except (json.JSONDecodeError, UnicodeDecodeError) as e:
                logger.warning(f"Could not read existing schema file: {e}")
                result["details"]["file_existed"] = True
                result["details"]["schemas_cleared"] = 0
            
            # Clear the file by writing an empty object
            with open(self.table_schema_path, 'w', encoding='utf-8') as f:
                json.dump({}, f, indent=2)
            
            result["success"] = True
            result["message"] = f"Successfully cleared table schema file ({result['details']['schemas_cleared']} schemas removed)"
            logger.info(f"Successfully cleared table schema file: {self.table_schema_path}")
            
        except PermissionError as e:
            error_msg = f"Permission denied accessing table schema file: {str(e)}"
            result["message"] = error_msg
            logger.error(f"Permission error clearing table schema: {e}")
        except Exception as e:
            error_msg = f"Error clearing table schema file: {str(e)}"
            result["message"] = error_msg
            logger.error(f"Table schema clearing failed: {e}", exc_info=True)
        
        return result


    async def get_data_summary(self) -> Dict[str, Any]:
        """Get summary of current data in both systems."""
        logger.info("Getting data summary")
        
        summary = {
            "pinecone": {"available": False, "vector_count": 0, "index_exists": False},
            "mysql": {"available": False, "table_count": 0, "tables": []},
            "table_schema": {"available": False, "schema_count": 0, "file_exists": False}
        }
        
        # Get Pinecone summary
        try:
            if self.config.PINECONE_API_KEY and Pinecone:
                pc = Pinecone(api_key=self.config.PINECONE_API_KEY)
                indexes = pc.list_indexes()
                index_names = [idx.name for idx in indexes]
                
                if self.config.PINECONE_INDEX_NAME in index_names:
                    summary["pinecone"]["index_exists"] = True
                    index = pc.Index(self.config.PINECONE_INDEX_NAME)
                    stats = index.describe_index_stats()
                    summary["pinecone"]["vector_count"] = stats.get('total_vector_count', 0)
                
                summary["pinecone"]["available"] = True
        except Exception as e:
            logger.error(f"Error getting Pinecone summary: {e}")
        
        # Get MySQL summary
        try:
            self.config.validate_database_config()
            engine = create_engine(self.config.database_url)
            
            with engine.connect() as connection:
                tables_query = text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = :db_name
                    AND table_type = 'BASE TABLE'
                """)
                
                tables_result = connection.execute(
                    tables_query, 
                    {"db_name": self.config.DATABASE_NAME}
                )
                tables = [row[0] for row in tables_result.fetchall()]
                
                summary["mysql"]["available"] = True
                summary["mysql"]["table_count"] = len(tables)
                summary["mysql"]["tables"] = tables
                
        except Exception as e:
            logger.error(f"Error getting MySQL summary: {e}")
        # Get table schema summary
        try:
            if self.table_schema_path.exists():
                summary["table_schema"]["file_exists"] = True
                try:
                    with open(self.table_schema_path, 'r', encoding='utf-8') as f:
                        schema_data = json.load(f)
                    
                    if isinstance(schema_data, dict):
                        schema_count = len(schema_data)
                    elif isinstance(schema_data, list):
                        schema_count = len(schema_data)
                    else:
                        schema_count = 1 if schema_data else 0
                        
                    summary["table_schema"]["schema_count"] = schema_count
                    summary["table_schema"]["available"] = True
                    
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    logger.error(f"Error reading table schema file: {e}")
                    summary["table_schema"]["available"] = True  # File exists but corrupted
                    
        except Exception as e:
            logger.error(f"Error checking table schema file: {e}")
        return summary


# Global service instance
clear_data_service = DataClearService()


async def clear_all_data() -> Dict[str, Any]:
    """Convenience function to clear all data."""
    return await clear_data_service.clear_all_data()


async def get_data_summary() -> Dict[str, Any]:
    """Convenience function to get data summary."""
    return await clear_data_service.get_data_summary()


# CLI functionality
async def main():
    """Main function for CLI usage."""
    print("🚨 WARNING: This will permanently delete ALL data from Pinecone and MySQL!")
    print("This action cannot be undone.")
    print()
    
    # Show current data summary
    print("Current data summary:")
    summary = await get_data_summary()
    
    print(f"Pinecone Index ({config.PINECONE_INDEX_NAME}):")
    if summary["pinecone"]["available"]:
        if summary["pinecone"]["index_exists"]:
            print(f"  - Vectors: {summary['pinecone']['vector_count']}")
        else:
            print("  - Index does not exist")
    else:
        print("  - Not available/configured")
    
    print(f"MySQL Database ({config.DATABASE_NAME}):")
    if summary["mysql"]["available"]:
        print(f"  - Tables: {summary['mysql']['table_count']}")
        if summary["mysql"]["tables"]:
            for table in summary["mysql"]["tables"]:
                print(f"    • {table}")
    else:
        print("  - Not available/configured")
    
    print()
    
    # Confirm deletion
    confirm = input("Are you sure you want to delete ALL data? Type 'DELETE ALL' to confirm: ")
    
    if confirm != "DELETE ALL":
        print("Operation cancelled.")
        return
    
    print("\nStarting data deletion...")
    result = await clear_all_data()
    
    print(f"\nOperation completed. Success: {result['success']}")
    print(f"Summary: {result['summary']}")
    
    print("\nDetailed results:")
    for operation, details in result["operations"].items():
        print(f"{operation.upper()}:")
        print(f"  - Success: {details['success']}")
        print(f"  - Message: {details['message']}")
        if details.get("details"):
            for key, value in details["details"].items():
                print(f"  - {key}: {value}")


if __name__ == "__main__":
    asyncio.run(main())