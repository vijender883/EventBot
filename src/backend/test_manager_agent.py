# Example usage and testing script
# src/backend/test_manager_agent.py

import asyncio
import os
from dotenv import load_dotenv
from agents.manager_agent import ManagerAgent

load_dotenv()

async def test_manager_agent():
    """Test the Manager Agent with different query types"""
    
    # Initialize ChatbotAgent first (if available)
    chatbot_agent = None
    try:
        from agents.rag_agent import ChatbotAgent
        chatbot_agent = ChatbotAgent()
        print("✅ ChatbotAgent initialized successfully")
    except Exception as e:
        print(f"⚠️  ChatbotAgent initialization failed: {e}")
        print("Will use fallback mode for RAG queries")
    
    # Initialize Manager Agent
    gemini_api_key = os.getenv("GEMINI_API_KEY")
    if not gemini_api_key:
        print("Error: GEMINI_API_KEY not found in environment variables")
        return
    
    manager = ManagerAgent(gemini_api_key, chatbot_agent)
    
    # Test queries
    test_queries = [
        # Should route to RAG only
        "Tell me about Zinedine Zidane",
        "Who is Emmitt Smith?",
        "Describe Walter Payton's career",
        
        # Should route to Table only  
        "How many rushing yards did Emmitt Smith have?",
        "What are the total goals scored in 1986?",
        "Count the number of Super Bowl wins by Dallas Cowboys",
        
        # Should route to both
        "Tell me about Zinedine Zidane and how many goals he scored in 1986",
        "Who is Emmitt Smith and what are his career statistics?",
        "Describe Walter Payton and show me his rushing yards data"
    ]
    
    print("🚀 Testing Manager Agent with LangGraph Workflow")
    print("=" * 60)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 Test {i}: {query}")
        print("-" * 40)
        
        try:
            result = manager.process_query(query)
            
            print(f"✅ Success: {result['success']}")
            print(f"📄 Answer: {result['answer']}")
            
            if result.get('metadata'):
                metadata = result['metadata']
                print(f"🔍 Used Table: {metadata.get('used_table', False)}")
                print(f"🔍 Used RAG: {metadata.get('used_rag', False)}")
                
            if result.get('error'):
                print(f"❌ Error: {result['error']}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")
        
        print("-" * 40)
    
    # Test health check
    print(f"\n🏥 Health Check:")
    health = manager.health_check()
    print(f"Overall Health: {health.get('overall_health', False)}")
    print(f"LLM Connection: {health.get('llm_connection', False)}")
    print(f"Workflow Ready: {health.get('workflow_ready', False)}")

if __name__ == "__main__":
    asyncio.run(test_manager_agent())


# Example FastAPI endpoint usage:
"""
After implementing this, your API calls will work like this:

POST /answer
{
    "query": "Tell me about Zinedine Zidane and how many goals he scored in 1986"
}

Response:
{
    "answer": "RAG processing: Tell me about Zinedine Zidane and how many goals he scored in 1986\n\nTable processing: Tell me about Zinedine Zidane and how many goals he scored in 1986",
    "success": true,
    "error": null
}

The debug output in your console will show:
[DEBUG] Manager Agent processing query: Tell me about Zinedine Zidane and how many goals he scored in 1986
[DEBUG] Manager Node called with query: Tell me about Zinedine Zidane and how many goals he scored in 1986
[DEBUG] Manager decision: both (table: True, rag: True)
[DEBUG] Table Node called with query: Tell me about Zinedine Zidane and how many goals he scored in 1986
[DEBUG] Table Node response: Table processing: Tell me about Zinedine Zidane and how many goals he scored in 1986
[DEBUG] RAG Node called with query: Tell me about Zinedine Zidane and how many goals he scored in 1986
[DEBUG] RAG Node response: RAG processing: Tell me about Zinedine Zidane and how many goals he scored in 1986
[DEBUG] Combiner Node called
[DEBUG] Combiner Node response: RAG processing: Tell me about Zinedine Zidane and how many goals he scored in 1986

Table processing: Tell me about Zinedine Zidane and how many goals he scored in 1986
[DEBUG] Manager Agent final result: RAG processing: Tell me about Zinedine Zidane and how many goals he scored in 1986

Table processing: Tell me about Zinedine Zidane and how many goals he scored in 1986
"""