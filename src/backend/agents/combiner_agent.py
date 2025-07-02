# src/backend/agents/combiner_agent.py

import logging
from typing import Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, SystemMessage

logger = logging.getLogger(__name__)

class CombinerAgent:
    """
    Agent responsible for intelligently combining responses from Table and RAG nodes
    """
    
    def __init__(self, gemini_api_key: str):
        """
        Initialize the Combiner Agent with Gemini LLM
        
        Args:
            gemini_api_key (str): Google Gemini API key
        """
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=gemini_api_key,
            temperature=0.3  # Slightly higher for more creative combinations
        )
        logger.info("Combiner Agent initialized successfully")
    
    def combine_responses(
        self, 
        original_query: str,
        table_response: Optional[str] = None,
        rag_response: Optional[str] = None
    ) -> str:
        """
        Intelligently combine responses from Table and RAG nodes
        
        Args:
            original_query (str): The original user query
            table_response (Optional[str]): Response from table processing
            rag_response (Optional[str]): Response from RAG processing
            
        Returns:
            str: Combined, coherent response
        """
        try:
            print(f"[DEBUG] Combiner Agent processing responses")
            print(f"[DEBUG] Table response present: {table_response is not None}")
            print(f"[DEBUG] RAG response present: {rag_response is not None}")
            
            # Handle single response cases
            if table_response and not rag_response:
                return self._format_single_response(table_response, "data analysis")
            
            if rag_response and not table_response:
                return self._format_single_response(rag_response, "knowledge base")
            
            # Handle combined response case
            if table_response and rag_response:
                return self._create_intelligent_combination(
                    original_query, table_response, rag_response
                )
            
            # Handle no response case
            return "I apologize, but I wasn't able to generate a response to your query. Please try rephrasing your question."
            
        except Exception as e:
            logger.error(f"Error in Combiner Agent: {e}", exc_info=True)
            return "I encountered an error while combining the responses. Please try again."
    
    def _format_single_response(self, response: str, source_type: str) -> str:
        """
        Format a single response with appropriate context
        
        Args:
            response (str): The response to format
            source_type (str): Type of source ("data analysis" or "knowledge base")
            
        Returns:
            str: Formatted response
        """
        if response.strip():
            return response
        else:
            return f"No information available from {source_type} for your query."
    
    def _create_intelligent_combination(
        self, 
        original_query: str, 
        table_response: str, 
        rag_response: str
    ) -> str:
        """
        Use Gemini to create an intelligent combination of both responses
        
        Args:
            original_query (str): Original user query
            table_response (str): Response from table processing
            rag_response (str): Response from RAG processing
            
        Returns:
            str: Intelligently combined response
        """
        try:
            system_prompt = """
            You are an intelligent answer synthesizer that creates clear, informative, and conversational responses by merging two sources:
            1. RAG Response: General knowledge or contextual explanation
            2. Table Response: Factual or data-driven insight (may be raw or terse)

            Your tasks:
            - Always provide a single, coherent, well-written response to the user's query
            - When the table response is raw or minimal (e.g., just a list or tuple), rephrase it into a complete, natural explanation
            - If only one source is useful, use it fully—don’t copy raw outputs verbatim; convert them into clear English
            - Use contextual knowledge from the RAG response to enrich and explain the data when available
            - Avoid redundancy and prioritize relevance to the original query
            - Maintain a friendly, concise, and natural tone
            - Never mention or refer to the source of the response (e.g., don’t say “table says...”)

            Structure:
            - Begin with a short, clear answer to the user’s query
            - Follow with any relevant detail, explanation, or data points
            - If needed, fill in gaps using logical reasoning or domain knowledge
            """
            
            user_prompt = f"""
            Original Query: {original_query}

            General Knowledge Response: {rag_response}

            Data Analysis Response: {table_response}

            Please combine these responses into a single, coherent answer that best addresses the user's query.
            """
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]
            
            response = self.llm.invoke(messages)
            combined_response = response.content.strip()
            
            print(f"[DEBUG] Combiner Agent created intelligent combination")
            return combined_response
            
        except Exception as e:
            logger.error(f"Error creating intelligent combination: {e}")
            # Fallback to simple concatenation
            return self._simple_combination(table_response, rag_response)
    
    def _simple_combination(self, table_response: str, rag_response: str) -> str:
        """
        Fallback method for simple response combination
        
        Args:
            table_response (str): Response from table processing
            rag_response (str): Response from RAG processing
            
        Returns:
            str: Simply combined response
        """
        print(f"[DEBUG] Combiner Agent using simple combination fallback")
        
        parts = []
        
        if rag_response and rag_response.strip():
            parts.append(rag_response.strip())
        
        if table_response and table_response.strip():
            parts.append(table_response.strip())
        
        if parts:
            return "\n\n".join(parts)
        else:
            return "No response could be generated for your query."
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check for the Combiner Agent
        
        Returns:
            Dict[str, Any]: Health status information
        """
        try:
            # Test LLM connection
            test_response = self.llm.invoke([HumanMessage(content="Hello")])
            
            return {
                "combiner_agent": True,
                "llm_connection": True,
                "overall_health": True
            }
        except Exception as e:
            logger.error(f"Combiner Agent health check failed: {e}")
            return {
                "combiner_agent": False,
                "llm_connection": False,
                "overall_health": False,
                "error": str(e)
            }