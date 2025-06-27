# src/backend/utils/schema_manager.py
"""
Utility for managing table schemas created by the enhanced PDF processor.
Provides functions to view, export, and manage the src/backend/utils/table_schema.json file.
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class SchemaManager:
    """Manager for table schemas stored in JSON format."""
    
    def __init__(self, schema_file: str = "src/backend/utils/table_schema.json"):
        self.schema_file = Path(schema_file)
        self.schemas = self._load_schemas()
    
    def _load_schemas(self) -> Dict:
        """Load schemas from JSON file."""
        if self.schema_file.exists():
            try:
                with open(self.schema_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Failed to load schemas: {e}")
                return {}
        return {}
    
    def _save_schemas(self):
        """Save schemas to JSON file."""
        try:
            with open(self.schema_file, 'w') as f:
                json.dump(self.schemas, f, indent=2)
            logger.info(f"Saved schemas to {self.schema_file}")
        except Exception as e:
            logger.error(f"Failed to save schemas: {e}")
    
    def get_all_schemas(self) -> Dict:
        """Get all stored schemas."""
        return self.schemas
    
    def get_schema(self, table_name: str) -> Optional[Dict]:
        """Get schema for a specific table."""
        return self.schemas.get(table_name)
    
    def list_tables(self) -> List[str]:
        """Get list of all table names."""
        return list(self.schemas.keys())
    
    def get_tables_by_file(self, file_hash: str) -> List[Dict]:
        """Get all tables created from a specific file."""
        tables = []
        for table_name, schema_info in self.schemas.items():
            if schema_info.get('file_hash') == file_hash:
                tables.append({
                    'table_name': table_name,
                    'description': schema_info.get('description', ''),
                    'schema': schema_info.get('schema', {}),
                    'created_at': schema_info.get('created_at', '')
                })
        return tables
    
    def search_tables(self, keyword: str) -> List[Dict]:
        """Search tables by keyword in name or description."""
        results = []
        keyword_lower = keyword.lower()
        
        for table_name, schema_info in self.schemas.items():
            if (keyword_lower in table_name.lower() or 
                keyword_lower in schema_info.get('description', '').lower()):
                results.append({
                    'table_name': table_name,
                    'description': schema_info.get('description', ''),
                    'schema': schema_info.get('schema', {}),
                    'match_reason': 'name' if keyword_lower in table_name.lower() else 'description'
                })
        return results
    
    def get_schema_summary(self) -> Dict:
        """Get summary statistics about stored schemas."""
        total_tables = len(self.schemas)
        file_hashes = set()
        column_types = {}
        
        for schema_info in self.schemas.values():
            if 'file_hash' in schema_info:
                file_hashes.add(schema_info['file_hash'])
            
            schema = schema_info.get('schema', {})
            for col_type in schema.values():
                column_types[col_type] = column_types.get(col_type, 0) + 1
        
        return {
            'total_tables': total_tables,
            'unique_files': len(file_hashes),
            'column_type_distribution': column_types,
            'schema_file_size': self.schema_file.stat().st_size if self.schema_file.exists() else 0
        }
    
    def export_schema_documentation(self, output_file: str = "schema_documentation.md") -> bool:
        """Export schemas as markdown documentation with enhanced type information."""
        try:
            with open(output_file, 'w') as f:
                f.write("# Table Schema Documentation\n\n")
                f.write(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                summary = self.get_schema_summary()
                f.write("## Summary\n\n")
                f.write(f"- **Total Tables**: {summary['total_tables']}\n")
                f.write(f"- **Unique Files Processed**: {summary['unique_files']}\n")
                f.write(f"- **Schema File Size**: {summary['schema_file_size']} bytes\n\n")
                
                f.write("### Column Type Distribution\n\n")
                type_descriptions = {
                    'string': 'VARCHAR(255) - Text data (up to 255 characters)',
                    'text': 'TEXT - Long text content',
                    'integer': 'INT - Whole numbers',
                    'float': 'FLOAT - Decimal numbers',
                    'currency': 'FLOAT - Monetary values (parsed from $, €, £, etc.)',
                    'percentage': 'FLOAT - Percentage values (stored as decimal: 0.25 for 25%)'
                }
                
                for col_type, count in summary['column_type_distribution'].items():
                    description = type_descriptions.get(col_type, 'Unknown type')
                    f.write(f"- **{col_type}**: {count} columns - {description}\n")
                
                f.write("\n## Data Type Parsing Rules\n\n")
                f.write("The enhanced PDF processor uses intelligent parsing for different data types:\n\n")
                f.write("### Currency\n")
                f.write("- **Symbols supported**: $, €, £, ¥, ₹, and others\n")
                f.write("- **Formats**: `$4.34`, `€1,234.56`, `(£5.99)` for negative\n")
                f.write("- **Storage**: Numeric value only (4.34, 1234.56, -5.99)\n\n")
                
                f.write("### Percentage\n")
                f.write("- **Formats**: `25%`, `12.5%`, or decimal `0.25`\n")
                f.write("- **Storage**: Decimal format (25% → 0.25)\n\n")
                
                f.write("### Numeric with Formatting\n")
                f.write("- **Thousand separators**: Commas and spaces removed\n")
                f.write("- **Formats**: `1,234.56`, `1 234.56`\n")
                f.write("- **Scientific notation**: `1.23e-4` supported\n\n")
                
                f.write("## Table Schemas\n\n")
                
                for table_name, schema_info in self.schemas.items():
                    f.write(f"### {table_name}\n\n")
                    
                    # Write detailed description (which now includes all the comprehensive info)
                    description = schema_info.get('description', 'No description available')
                    f.write(f"{description}\n\n")
                    
                    f.write(f"**Created**: {schema_info.get('created_at', 'Unknown')}\n\n")
                    
                    if 'file_hash' in schema_info:
                        f.write(f"**Source File Hash**: `{schema_info['file_hash']}`\n\n")
                    
                    f.write("**Technical Schema**:\n\n")
                    f.write("| Column Name | Data Type | SQL Type |\n")
                    f.write("|-------------|-----------|----------|\n")
                    
                    schema = schema_info.get('schema', {})
                    for col_name, col_type in schema.items():
                        sql_type = type_descriptions.get(col_type, f'{col_type.upper()} - Custom type').split(' - ')[0]
                        f.write(f"| {col_name} | {col_type} | {sql_type} |\n")
                    
                    f.write("\n---\n\n")
            
            logger.info(f"Enhanced schema documentation exported to {output_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to export documentation: {e}")
            return False
    
    def validate_schemas(self) -> Dict[str, List[str]]:
        """Validate all schemas and return issues found."""
        issues = {
            'missing_fields': [],
            'invalid_types': [],
            'empty_schemas': [],
            'malformed_entries': []
        }
        
        valid_types = {'string', 'integer', 'float', 'text', 'currency', 'percentage'}
        required_fields = {'schema', 'description'}
        
        for table_name, schema_info in self.schemas.items():
            # Check for malformed entries first
            if not isinstance(schema_info, dict):
                issues['malformed_entries'].append(table_name)
                continue  # Skip further validation for malformed entries
            
            # Check for required fields
            missing = required_fields - set(schema_info.keys())
            if missing:
                issues['missing_fields'].append(f"{table_name}: missing {missing}")
            
            # Check schema content
            schema = schema_info.get('schema', {})
            if not schema:
                issues['empty_schemas'].append(table_name)
            else:
                for col_name, col_type in schema.items():
                    if col_type not in valid_types:
                        issues['invalid_types'].append(f"{table_name}.{col_name}: {col_type}")
        
        return issues
    
    def cleanup_schemas(self, file_hashes_to_keep: Optional[List[str]] = None) -> int:
        """Clean up schemas, optionally keeping only specified file hashes."""
        if file_hashes_to_keep is None:
            # Interactive cleanup - remove entries older than 30 days
            cutoff_date = datetime.now().timestamp() - (30 * 24 * 60 * 60)
            to_remove = []
            
            for table_name, schema_info in self.schemas.items():
                created_at = schema_info.get('created_at', '')
                if created_at:
                    try:
                        created_timestamp = datetime.fromisoformat(created_at.replace('Z', '+00:00')).timestamp()
                        if created_timestamp < cutoff_date:
                            to_remove.append(table_name)
                    except ValueError:
                        # If we can't parse the date, keep it
                        pass
        else:
            # Remove schemas not in the keep list
            to_remove = []
            for table_name, schema_info in self.schemas.items():
                file_hash = schema_info.get('file_hash', '')
                if file_hash not in file_hashes_to_keep:
                    to_remove.append(table_name)
        
        # Remove identified schemas
        removed_count = 0
        for table_name in to_remove:
            del self.schemas[table_name]
            removed_count += 1
        
        if removed_count > 0:
            self._save_schemas()
            logger.info(f"Cleaned up {removed_count} schemas")
        
        return removed_count
    
    def backup_schemas(self, backup_file: Optional[str] = None) -> str:
        """Create a backup of the current schemas."""
        if backup_file is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"table_schema_backup_{timestamp}.json"
        
        try:
            with open(backup_file, 'w') as f:
                json.dump(self.schemas, f, indent=2)
            logger.info(f"Schemas backed up to {backup_file}")
            return backup_file
        except Exception as e:
            logger.error(f"Failed to backup schemas: {e}")
            raise
    
    def restore_schemas(self, backup_file: str) -> bool:
        """Restore schemas from a backup file."""
        try:
            with open(backup_file, 'r') as f:
                backup_schemas = json.load(f)
            
            self.schemas = backup_schemas
            self._save_schemas()
            logger.info(f"Schemas restored from {backup_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore schemas: {e}")
            return False


# Convenience functions for common operations
def get_schema_manager() -> SchemaManager:
    """Get a SchemaManager instance."""
    return SchemaManager()

def list_all_tables() -> List[str]:
    """Quick function to list all table names."""
    manager = get_schema_manager()
    return manager.list_tables()

def get_table_schema(table_name: str) -> Optional[Dict]:
    """Quick function to get a table's schema."""
    manager = get_schema_manager()
    return manager.get_schema(table_name)

def export_documentation(output_file: str = "schema_documentation.md") -> bool:
    """Quick function to export schema documentation."""
    manager = get_schema_manager()
    return manager.export_schema_documentation(output_file)

def validate_all_schemas() -> Dict[str, List[str]]:
    """Quick function to validate all schemas."""
    manager = get_schema_manager()
    return manager.validate_schemas()


# CLI interface for the schema manager
if __name__ == "__main__":
    import sys
    
    manager = SchemaManager()
    
    if len(sys.argv) < 2:
        print("Usage: python schema_manager.py <command> [args]")
        print("Commands:")
        print("  list                    - List all tables")
        print("  summary                 - Show schema summary")
        print("  export [file]           - Export documentation")
        print("  validate                - Validate schemas")
        print("  search <keyword>        - Search tables")
        print("  backup [file]           - Backup schemas")
        print("  cleanup                 - Remove old schemas")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "list":
        tables = manager.list_tables()
        print(f"Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table}")
    
    elif command == "summary":
        summary = manager.get_schema_summary()
        print("Schema Summary:")
        print(f"  Total tables: {summary['total_tables']}")
        print(f"  Unique files: {summary['unique_files']}")
        print(f"  Schema file size: {summary['schema_file_size']} bytes")
        print("  Column types:")
        for col_type, count in summary['column_type_distribution'].items():
            print(f"    {col_type}: {count}")
    
    elif command == "export":
        output_file = sys.argv[2] if len(sys.argv) > 2 else "schema_documentation.md"
        if manager.export_schema_documentation(output_file):
            print(f"Documentation exported to {output_file}")
        else:
            print("Failed to export documentation")
    
    elif command == "validate":
        issues = manager.validate_schemas()
        total_issues = sum(len(issue_list) for issue_list in issues.values())
        if total_issues == 0:
            print("All schemas are valid!")
        else:
            print(f"Found {total_issues} issues:")
            for issue_type, issue_list in issues.items():
                if issue_list:
                    print(f"  {issue_type}:")
                    for issue in issue_list:
                        print(f"    - {issue}")
    
    elif command == "search":
        if len(sys.argv) < 3:
            print("Please provide a search keyword")
            sys.exit(1)
        keyword = sys.argv[2]
        results = manager.search_tables(keyword)
        print(f"Found {len(results)} tables matching '{keyword}':")
        for result in results:
            print(f"  - {result['table_name']} ({result['match_reason']})")
            print(f"    {result['description']}")
    
    elif command == "backup":
        backup_file = sys.argv[2] if len(sys.argv) > 2 else None
        try:
            backup_file = manager.backup_schemas(backup_file)
            print(f"Schemas backed up to {backup_file}")
        except Exception as e:
            print(f"Backup failed: {e}")
    
    elif command == "cleanup":
        removed = manager.cleanup_schemas()
        print(f"Removed {removed} old schema entries")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)