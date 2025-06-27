# ./clear_data_script.py
"""
Clear Data Script
================

Root-level script to interact with the FastAPI endpoints for data management.
This script calls the /datasummary and /clearalldata endpoints.

Usage:
    python clear_data.py                    # Interactive mode
    python clear_data.py --summary          # Just show data summary
    python clear_data.py --clear            # Clear data with confirmation
    python clear_data.py --clear --force    # Clear data without confirmation
    python clear_data.py --help             # Show help
"""

import asyncio
import argparse
import json
import sys
from typing import Dict, Any, Optional
import os
from pathlib import Path

# Add the src directory to Python path to import config
sys.path.insert(0, str(Path(__file__).parent / "src"))

try:
    import aiohttp
    import requests
except ImportError:
    print("❌ Required packages not installed. Please install them:")
    print("pip install aiohttp requests")
    sys.exit(1)

# Import config to get the endpoint URL
try:
    from src.backend.config import config
    API_BASE_URL = config.ENDPOINT
except ImportError:
    # Fallback to environment variable or default
    API_BASE_URL = os.getenv("ENDPOINT", "http://localhost:5000")

# ANSI color codes for better output
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'


class DataManager:
    """Manages data operations via FastAPI endpoints."""
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip('/')
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=300)  # 5 minute timeout
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def check_server_health(self) -> bool:
        """Check if the FastAPI server is running and healthy."""
        try:
            url = f"{self.base_url}/health"
            async with self.session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("status") in ["healthy", "degraded"]
                return False
        except Exception as e:
            print(f"{Colors.RED}❌ Server health check failed: {e}{Colors.END}")
            return False
    
    async def get_data_summary(self) -> Dict[str, Any]:
        """Get data summary from the API."""
        try:
            url = f"{self.base_url}/datasummary"
            print(f"{Colors.BLUE}📊 Fetching data summary from {url}...{Colors.END}")
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")
                    
        except Exception as e:
            raise Exception(f"Failed to get data summary: {e}")
    
    async def clear_all_data(self) -> Dict[str, Any]:
        """Clear all data via the API."""
        try:
            url = f"{self.base_url}/clearalldata"
            print(f"{Colors.YELLOW}🗑️  Sending clear data request to {url}...{Colors.END}")
            
            async with self.session.post(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")
                    
        except Exception as e:
            raise Exception(f"Failed to clear data: {e}")


def print_data_summary(summary_data: Dict[str, Any]):
    """Print formatted data summary."""
    print(f"\n{Colors.BOLD}{Colors.CYAN}📊 DATA SUMMARY{Colors.END}")
    print("=" * 50)
    
    if not summary_data.get("success", False):
        print(f"{Colors.RED}❌ Failed to get data summary: {summary_data.get('message', 'Unknown error')}{Colors.END}")
        return
    
    data = summary_data.get("data", {})
    totals = summary_data.get("totals", {})
    
    # Pinecone summary
    pinecone = data.get("pinecone", {})
    print(f"\n{Colors.BOLD}🔍 Pinecone Vector Database:{Colors.END}")
    if pinecone.get("available", False):
        if pinecone.get("index_exists", False):
            vectors = pinecone.get("vector_count", 0)
            color = Colors.GREEN if vectors > 0 else Colors.YELLOW
            print(f"  Status: {Colors.GREEN}✅ Available{Colors.END}")
            print(f"  Vectors: {color}{vectors:,}{Colors.END}")
        else:
            print(f"  Status: {Colors.YELLOW}⚠️  Index does not exist{Colors.END}")
            print(f"  Vectors: {Colors.YELLOW}0{Colors.END}")
    else:
        print(f"  Status: {Colors.RED}❌ Not available/configured{Colors.END}")
        print(f"  Vectors: {Colors.RED}0{Colors.END}")
    
    # MySQL summary
    mysql = data.get("mysql", {})
    print(f"\n{Colors.BOLD}🗄️  MySQL Database:{Colors.END}")
    if mysql.get("available", False):
        tables = mysql.get("tables", [])
        table_count = mysql.get("table_count", 0)
        color = Colors.GREEN if table_count > 0 else Colors.YELLOW
        print(f"  Status: {Colors.GREEN}✅ Available{Colors.END}")
        print(f"  Tables: {color}{table_count}{Colors.END}")
        
        if tables:
            print(f"  Table List:")
            for table in tables:
                print(f"    • {table}")
    else:
        print(f"  Status: {Colors.RED}❌ Not available/configured{Colors.END}")
        print(f"  Tables: {Colors.RED}0{Colors.END}")
    
    # Totals
    print(f"\n{Colors.BOLD}📈 TOTALS:{Colors.END}")
    print(f"  Total Vectors: {Colors.CYAN}{totals.get('pinecone_vectors', 0):,}{Colors.END}")
    print(f"  Total Tables: {Colors.CYAN}{totals.get('mysql_tables', 0)}{Colors.END}")
    
    timestamp = summary_data.get("timestamp", "Unknown")
    print(f"\n{Colors.PURPLE}🕐 Last Updated: {timestamp}{Colors.END}")


def print_clear_results(clear_data: Dict[str, Any]):
    """Print formatted clear data results."""
    print(f"\n{Colors.BOLD}{Colors.RED}🗑️  CLEAR DATA RESULTS{Colors.END}")
    print("=" * 50)
    
    success = clear_data.get("success", False)
    summary = clear_data.get("summary", "No summary available")
    
    # Overall status
    if success:
        print(f"\n{Colors.GREEN}✅ SUCCESS: {summary}{Colors.END}")
    else:
        print(f"\n{Colors.RED}❌ FAILED: {summary}{Colors.END}")
    
    # Individual operation results
    operations = clear_data.get("operations", {})
    
    for operation_name, operation_data in operations.items():
        op_success = operation_data.get("success", False)
        op_message = operation_data.get("message", "No message")
        details = operation_data.get("details", {})
        
        print(f"\n{Colors.BOLD}{operation_name.upper()}:{Colors.END}")
        
        status_icon = "✅" if op_success else "❌"
        status_color = Colors.GREEN if op_success else Colors.RED
        print(f"  Status: {status_color}{status_icon} {op_message}{Colors.END}")
        
        # Print details
        if details:
            for key, value in details.items():
                if isinstance(value, list) and value:
                    print(f"  {key.replace('_', ' ').title()}:")
                    for item in value:
                        if isinstance(item, dict):
                            print(f"    • {item}")
                        else:
                            print(f"    • {item}")
                else:
                    print(f"  {key.replace('_', ' ').title()}: {value}")
    
    # Before/After comparison if available
    pre_summary = clear_data.get("pre_clear_summary")
    post_summary = clear_data.get("post_clear_summary")
    
    if pre_summary and post_summary:
        print(f"\n{Colors.BOLD}{Colors.YELLOW}📊 BEFORE/AFTER COMPARISON:{Colors.END}")
        
        pre_vectors = pre_summary.get("pinecone", {}).get("vector_count", 0)
        post_vectors = post_summary.get("pinecone", {}).get("vector_count", 0)
        pre_tables = pre_summary.get("mysql", {}).get("table_count", 0)
        post_tables = post_summary.get("mysql", {}).get("table_count", 0)
        
        print(f"  Pinecone Vectors: {pre_vectors:,} → {post_vectors:,}")
        print(f"  MySQL Tables: {pre_tables} → {post_tables}")


def confirm_deletion() -> bool:
    """Get user confirmation for deletion."""
    print(f"\n{Colors.BOLD}{Colors.RED}⚠️  WARNING: DESTRUCTIVE OPERATION{Colors.END}")
    print(f"{Colors.RED}This will permanently delete ALL data from:{Colors.END}")
    print(f"{Colors.RED}  • All vectors in your Pinecone index{Colors.END}")
    print(f"{Colors.RED}  • All tables in your MySQL database{Colors.END}")
    print(f"{Colors.RED}  • This action CANNOT be undone!{Colors.END}")
    print()
    
    confirmation = input(f"{Colors.YELLOW}Type 'DELETE ALL' to confirm: {Colors.END}")
    return confirmation == "DELETE ALL"


async def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Manage data in Pinecone and MySQL via FastAPI endpoints",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python clear_data.py                    # Interactive mode
  python clear_data.py --summary          # Show data summary only
  python clear_data.py --clear            # Clear data with confirmation
  python clear_data.py --clear --force    # Clear data without confirmation
        """
    )
    
    parser.add_argument("--summary", action="store_true", 
                       help="Show data summary only")
    parser.add_argument("--clear", action="store_true",
                       help="Clear all data")
    parser.add_argument("--force", action="store_true",
                       help="Skip confirmation (use with --clear)")
    parser.add_argument("--url", default=API_BASE_URL,
                       help=f"API base URL (default: {API_BASE_URL})")
    
    args = parser.parse_args()
    
    print(f"{Colors.BOLD}{Colors.BLUE}🚀 EventBot Data Manager{Colors.END}")
    print(f"API Endpoint: {args.url}")
    print("=" * 50)
    
    async with DataManager(args.url) as manager:
        # Check server health
        print(f"{Colors.BLUE}🔍 Checking server health...{Colors.END}")
        if not await manager.check_server_health():
            print(f"{Colors.RED}❌ Server is not healthy or not running.{Colors.END}")
            print(f"{Colors.YELLOW}💡 Make sure your FastAPI server is running on {args.url}{Colors.END}")
            sys.exit(1)
        
        print(f"{Colors.GREEN}✅ Server is healthy{Colors.END}")
        
        try:
            # Handle different modes
            if args.summary:
                # Summary only mode
                summary = await manager.get_data_summary()
                print_data_summary(summary)
                
            elif args.clear:
                # Clear data mode
                # First show summary
                print(f"{Colors.BLUE}📊 Getting current data summary...{Colors.END}")
                summary = await manager.get_data_summary()
                print_data_summary(summary)
                
                # Confirm deletion unless --force is used
                if not args.force:
                    if not confirm_deletion():
                        print(f"\n{Colors.YELLOW}❌ Operation cancelled by user.{Colors.END}")
                        sys.exit(0)
                else:
                    print(f"\n{Colors.RED}⚠️  --force flag used, skipping confirmation{Colors.END}")
                
                # Perform clearing
                print(f"\n{Colors.RED}🗑️  Clearing all data...{Colors.END}")
                result = await manager.clear_all_data()
                print_clear_results(result)
                
            else:
                # Interactive mode
                while True:
                    print(f"\n{Colors.BOLD}Choose an option:{Colors.END}")
                    print(f"1. {Colors.CYAN}Show data summary{Colors.END}")
                    print(f"2. {Colors.RED}Clear all data{Colors.END}")
                    print(f"3. {Colors.YELLOW}Exit{Colors.END}")
                    
                    choice = input(f"\n{Colors.WHITE}Enter choice (1-3): {Colors.END}").strip()
                    
                    if choice == "1":
                        summary = await manager.get_data_summary()
                        print_data_summary(summary)
                        
                    elif choice == "2":
                        # Show summary first
                        summary = await manager.get_data_summary()
                        print_data_summary(summary)
                        
                        # Confirm deletion
                        if confirm_deletion():
                            print(f"\n{Colors.RED}🗑️  Clearing all data...{Colors.END}")
                            result = await manager.clear_all_data()
                            print_clear_results(result)
                        else:
                            print(f"\n{Colors.YELLOW}❌ Operation cancelled.{Colors.END}")
                            
                    elif choice == "3":
                        print(f"\n{Colors.GREEN}👋 Goodbye!{Colors.END}")
                        break
                        
                    else:
                        print(f"{Colors.RED}❌ Invalid choice. Please enter 1, 2, or 3.{Colors.END}")
        
        except KeyboardInterrupt:
            print(f"\n\n{Colors.YELLOW}⚠️  Operation interrupted by user.{Colors.END}")
            sys.exit(0)
        except Exception as e:
            print(f"\n{Colors.RED}❌ Error: {e}{Colors.END}")
            sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())