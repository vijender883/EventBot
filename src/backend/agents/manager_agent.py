import logging
import json
import mysql.connector
from typing import Dict, Any, List, Optional
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel
import os
try:
    from urllib.parse import urlparse, parse_qs
except ImportError as e:
    logging.error(f"Failed to import urllib.parse: {e}")
    raise

logger = logging.getLogger(__name__)


class AgentState(BaseModel):
    """State object for the LangGraph workflow"""
    query: str
    response: str = ""
    needs_table: bool = False
    needs_rag: bool = False
    table_response: str = ""
    rag_response: str = ""
    pdf_uuid: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class ManagerAgent:
    """
    Manager Agent using LangGraph to orchestrate between Table and RAG nodes
    """

    def __init__(self, gemini_api_key: str, chatbot_agent=None):
        """Initialize the Manager Agent with Gemini LLM and optional ChatbotAgent"""
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=gemini_api_key,
            temperature=0.1
        )
        self.chatbot_agent = chatbot_agent

        # Initialize Combiner Agent
        try:
            from .combiner_agent import CombinerAgent
            self.combiner_agent = CombinerAgent(gemini_api_key)
            logger.info(
                "Combiner Agent initialized successfully in Manager Agent")
        except Exception as e:
            logger.error(f"Failed to initialize Combiner Agent: {e}")
            self.combiner_agent = None

        self.workflow = self._create_workflow()
        try:
            from .table_agent import TableAgent
            if not os.path.exists(os.path.join(os.path.dirname(__file__), 'table_agent.py')):
                raise FileNotFoundError("table_agent.py not found in agents directory")
            self.table_agent = TableAgent(gemini_api_key)
            logger.info("Table Agent initialized successfully in Manager Agent")

        except ImportError as e:
            logger.error(f"Failed to import TableAgent: {e}", exc_info=True)
            self.table_agent = None
        except FileNotFoundError as e:
            logger.error(f"TableAgent file error: {e}", exc_info=True)
            self.table_agent = None
        except Exception as e:
            logger.error(f"Failed to initialize TableAgent: {e}", exc_info=True)
            self.table_agent = None

    def _create_workflow(self) -> StateGraph:
        """Create the LangGraph workflow"""
        workflow = StateGraph(AgentState)

        # Add nodes
        workflow.add_node("manager", self._manager_node)
        workflow.add_node("table", self._table_node)
        workflow.add_node("rag", self._rag_node)
        workflow.add_node("combiner", self._combiner_node)

        # Add edges
        workflow.set_entry_point("manager")
        workflow.add_conditional_edges(
            "manager",
            self._decide_route,
            {
                "table_only": "table",
                "rag_only": "rag",
                "both": "table",  # Start with table, then go to RAG
                "end": END
            }
        )

        workflow.add_conditional_edges(
            "table",
            self._after_table_route,
            {
                "to_rag": "rag",
                "to_combiner": "combiner",
                "end": END
            }
        )

        workflow.add_edge("rag", "combiner")
        workflow.add_edge("combiner", END)

        return workflow.compile()

    def _manager_node(self, state: AgentState) -> Dict[str, Any]:
        """Manager node that analyzes the query and decides routing"""
        print(f"[DEBUG] Manager Node called with query: {state.query}")

        schema_info = self._load_table_schema(state.pdf_uuid)
        system_prompt = f"""
        You are a query analyzer that routes queries based on available data sources.

        AVAILABLE DATABASE SCHEMA:
        {schema_info}

        ROUTING RULES:
        Analyze the user query and determine the appropriate route:

        1. "table" - Use when the query can be answered using the database tables above
        - Queries about specific data fields (ID, Name, Age, City, Occupation, Salary, Product, Category, Price, Stock, etc.)
        - Statistical queries (count, sum, average, min, max)
        - Data filtering and aggregation queries
        - Comparative analysis using table data

        2. "rag" - Use for general knowledge queries not answerable from the database
        - Biographical information not in tables
        - Historical facts and general knowledge
        - Explanations of concepts or definitions
        - Questions about entities not present in the database

        3. "both" - Use when query needs database data AND external knowledge
        - Questions requiring data analysis plus contextual explanation
        - Queries needing database facts supplemented with general knowledge

        DECISION PROCESS:
        1. First check if the query asks for data that exists in the schema columns
        2. If yes and no external knowledge needed → "table"
        3. If no database data needed → "rag" 
        4. If both database data and general knowledge needed → "both"

        Respond with only one word: "table", "rag", or "both"
        """

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Query: {state.query}")
        ]

        try:
            response = self.llm.invoke(messages)
            decision = response.content.strip().lower()

            # Set flags based on decision
            if decision == "table":
                state.needs_table = True
                state.needs_rag = False
            elif decision == "rag":
                state.needs_table = False
                state.needs_rag = True
            elif decision == "both":
                state.needs_table = True
                state.needs_rag = True
            else:
                # Default to RAG for unknown cases
                state.needs_table = False
                state.needs_rag = True

            print(
                f"[DEBUG] Manager decision: {decision} (table: {state.needs_table}, rag: {state.needs_rag})")

        except Exception as e:
            logger.error(f"Error in manager node: {e}")
            # Default to RAG on error
            state.needs_table = False
            state.needs_rag = True

        return {"needs_table": state.needs_table, "needs_rag": state.needs_rag}

    def _table_node(self, state: AgentState) -> Dict[str, Any]:
        """Table node for handling data queries using TableAgent"""
        print(f"[DEBUG] Table Node called with query: {state.query}")

        try:
            if self.table_agent:
                table_response = self.table_agent.process_query(state.query, state.pdf_uuid)
                print(
                    f"[DEBUG] Table Node response from TableAgent: {table_response}")
            else:
                logger.error("TableAgent not initialized")
                table_response = f"Error: Table processing unavailable for query: {state.query}"
                print(f"[DEBUG] Table Node error: TableAgent not initialized")
        except Exception as e:
            logger.error(f"Error in table node: {e}")
            table_response = f"Error processing data query: {state.query}"
            print(f"[DEBUG] Table Node error response: {table_response}")

        return {"table_response": table_response}

    def _rag_node(self, state: AgentState) -> Dict[str, Any]:
        """RAG node for handling knowledge queries using ChatbotAgent"""
        print(f"[DEBUG] RAG Node called with query: {state.query}")
        
        try:
            if self.chatbot_agent:
                # Use the ChatbotAgent's answer_question function with PDF UUID
                response = self.chatbot_agent.answer_question(state.query, pdf_uuid=state.pdf_uuid)
                rag_response = response.get("answer", f"RAG processing: {state.query}")
                print(f"[DEBUG] RAG Node response from ChatbotAgent: {rag_response}")
            else:
                # Fallback if no ChatbotAgent is available
                rag_response = f"RAG processing: {state.query}"
                print(f"[DEBUG] RAG Node response (fallback): {rag_response}")
        except Exception as e:
            logger.error(f"Error in RAG node: {e}")
            rag_response = f"RAG processing error: {state.query}"
            print(f"[DEBUG] RAG Node error response: {rag_response}")
        
        return {"rag_response": rag_response}
    
    def _combiner_node(self, state: AgentState) -> Dict[str, Any]:
        """Combiner node to merge responses from Table and RAG nodes using CombinerAgent"""
        print(f"[DEBUG] Combiner Node called")
        
        try:
            if self.combiner_agent:
                # Use the intelligent CombinerAgent
                combined_response = self.combiner_agent.combine_responses(
                    original_query=state.query,
                    table_response=state.table_response if state.table_response else None,
                    rag_response=state.rag_response if state.rag_response else None
                )
                print(f"[DEBUG] Combiner Node using CombinerAgent: {combined_response[:100]}...")
            else:
                # Fallback to simple combination
                combined_response = ""
                
                if state.table_response and state.rag_response:
                    combined_response = f"{state.rag_response}\n\n{state.table_response}"
                elif state.table_response:
                    combined_response = state.table_response
                elif state.rag_response:
                    combined_response = state.rag_response
                else:
                    combined_response = "No response generated"
                
                print(f"[DEBUG] Combiner Node using fallback combination: {combined_response}")
        
        except Exception as e:
            logger.error(f"Error in combiner node: {e}")
            # Simple fallback on error
            combined_response = state.rag_response or state.table_response or "Error generating response"
            print(f"[DEBUG] Combiner Node error fallback: {combined_response}")
        
        return {"response": combined_response}
    
    def _decide_route(self, state: AgentState) -> str:
        """Decide which route to take based on manager analysis"""
        if state.needs_table and state.needs_rag:
            return "both"
        elif state.needs_table:
            return "table_only"
        elif state.needs_rag:
            return "rag_only"
        else:
            return "end"
    
    def _after_table_route(self, state: AgentState) -> str:
        """Decide route after table processing"""
        if state.needs_rag:
            return "to_rag"
        else:
            return "to_combiner"
    
    def process_query(self, query: str, pdf_uuid: str = None) -> Dict[str, Any]:
        """
        Process a user query through the LangGraph workflow
        
        Args:
            query (str): The user's question
            pdf_uuid (str, optional): UUID of the PDF being queried
            
        Returns:
            Dict[str, Any]: Response containing answer and metadata
        """
        try:
            print(f"[DEBUG] Manager Agent processing query: {query} for PDF: {pdf_uuid}")
            
            # Create initial state
            initial_state = AgentState(query=query, pdf_uuid=pdf_uuid)
            
            # Run the workflow
            result = self.workflow.invoke(initial_state)
            
            # Extract values from the AddableValuesDict result
            final_response = result.get("response", "No response generated")
            needs_table = result.get("needs_table", False)
            needs_rag = result.get("needs_rag", False)
            
            print(f"[DEBUG] Manager Agent final result: {final_response}")
            
            return {
                "answer": final_response,
                "success": True,
                "error": None,
                "metadata": {
                    "used_table": needs_table,
                    "used_rag": needs_rag
                }
            }
            
        except Exception as e:
            logger.error(f"Error in Manager Agent: {e}", exc_info=True)
            return {
                "answer": "I encountered an error while processing your question. Please try again.",
                "success": False,
                "error": str(e),
                "metadata": {}
            }
    
    def health_check(self) -> Dict[str, Any]:
        """Health check for the Manager Agent"""
        try:
            # Test LLM connection
            test_response = self.llm.invoke([HumanMessage(content="Hello")])
            
            # Check combiner agent health
            combiner_health = True
            if self.combiner_agent:
                combiner_status = self.combiner_agent.health_check()
                combiner_health = combiner_status.get("overall_health", False)
            
            return {
                "manager_agent": True,
                "llm_connection": True,
                "workflow_ready": self.workflow is not None,
                "combiner_agent": combiner_health,
                "chatbot_agent_available": self.chatbot_agent is not None,
                "overall_health": True
            }
        except Exception as e:
            logger.error(f"Manager Agent health check failed: {e}")
            return {
                "manager_agent": False,
                "llm_connection": False,
                "workflow_ready": False,
                "combiner_agent": False,
                "chatbot_agent_available": False,
                "overall_health": False,
                "error": str(e)
            }
    

    def _load_table_schema(self, pdf_uuid: str = None) -> str:
        """Load table schema from JSON file with better error handling and path resolution"""
        try:
            # Try multiple possible paths for the schema file
            possible_paths = [
                os.path.join(os.path.dirname(__file__), '..', 'utils', 'table_schema.json'),
                os.path.join(os.getcwd(), 'src', 'backend', 'utils', 'table_schema.json'),
                'src/backend/utils/table_schema.json',
                './src/backend/utils/table_schema.json'
            ]
            
            schema_path = None
            for path in possible_paths:
                abs_path = os.path.abspath(path)
                logger.debug(f"Checking schema path: {abs_path}")
                if os.path.exists(abs_path):
                    schema_path = abs_path
                    logger.info(f"Found schema file at: {schema_path}")
                    break
            
            if not schema_path:
                logger.error("Schema file not found in any expected location")
                logger.error(f"Searched paths: {[os.path.abspath(p) for p in possible_paths]}")
                return "Database schema not available - file not found"
            
            with open(schema_path, 'r') as f:
                schema_data = json.load(f)
            
            if not schema_data:
                logger.warning("Schema file is empty")
                return "Database schema not available - empty schema"
            
            # Filter by PDF UUID if provided
            if pdf_uuid:
                filtered_schema = {
                    table_name: table_info for table_name, table_info in schema_data.items()
                    if table_info.get('pdf_uuid') == pdf_uuid
                }
                schema_data = filtered_schema
                
                if not schema_data:
                    logger.info(f"No schemas found for PDF UUID: {pdf_uuid}")
                    return f"No database schemas available for the current document (UUID: {pdf_uuid})"
            
            # Convert schema to detailed readable format for the LLM
            schema_info = ""
            for table_name, table_info in schema_data.items():
                schema_info += f"\nTable: {table_name}\n"
                schema_info += f"Description: {table_info.get('description', 'No description')}\n"
                schema_info += f"Columns:\n"
                
                if 'schema' in table_info:
                    for column_name, column_type in table_info['schema'].items():
                        schema_info += f"  - {column_name} ({column_type})\n"
                
                schema_info += f"Created: {table_info.get('created_at', 'Unknown')}\n"
                schema_info += "-" * 50 + "\n"
            
            logger.info(f"Successfully loaded schema with {len(schema_data)} tables")
            return schema_info
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in schema file: {e}")
            return "Database schema not available - invalid JSON format"
        except Exception as e:
            logger.error(f"Failed to load table schema: {e}")
            return "Database schema not available"