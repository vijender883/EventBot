import logging
import json
import mysql.connector
from typing import Dict, Any, List
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

        system_prompt = """
        You are a query analyzer. Analyze the user query and determine if it needs:
        1. "table" - for data queries about statistics, numbers, calculations from structured data
        2. "rag" - for general knowledge questions about people, facts, descriptions
        3. "both" - for queries that need both data analysis and general knowledge

        Keywords that suggest table queries: "how many", "statistics", "count", "total", "average", "goals scored", "data", "numbers"
        Keywords that suggest RAG queries: "tell me about", "who is", "biography", "background", "describe"

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
                table_response = self.table_agent.process_query(state.query)
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
                # Use the ChatbotAgent's answer_question function
                response = self.chatbot_agent.answer_question(state.query)
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
    
    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query through the LangGraph workflow
        
        Args:
            query (str): The user's question
            
        Returns:
            Dict[str, Any]: Response containing answer and metadata
        """
        try:
            print(f"[DEBUG] Manager Agent processing query: {query}")
            
            # Create initial state
            initial_state = AgentState(query=query)
            
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