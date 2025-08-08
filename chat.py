"""
Updated chat.py - ChatbotBackend that accepts API key as parameter
"""

import os
from typing import List, Dict, Any
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.tools import tool
from langchain_core.output_parsers import StrOutputParser

# Load environment variables
load_dotenv()

class ChatbotBackend:
    def __init__(self, api_key: str = None):
        # Use provided API key or get from environment
        if api_key:
            self.api_key = api_key
        else:
            self.api_key = os.getenv("GEMINI_API_KEY")
        
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY must be provided either as parameter or environment variable")
        
        # Initialize the LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            temperature=0.7,
            google_api_key=self.api_key
        )
        
        # Initialize tools
        self.tools = [get_weather_info, calculate_math]
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        
        # Store conversations in memory (in production, use a database)
        self.conversations: Dict[str, List[Dict[str, str]]] = {}
    
    def process_message_sync(self, user_message: str, session_id: str = "default") -> str:
        """Process a user message and return AI response"""
        
        try:
            # Get or create conversation history for this session
            if session_id not in self.conversations:
                self.conversations[session_id] = []
            
            conversation_history = self.conversations[session_id]
            
            # Create system message with clear tool instructions
            system_message = SystemMessage(content="""
            You are a helpful AI assistant with access to tools. When users ask about:
            - Weather in any city: USE the get_weather_info tool
            - Mathematical calculations: USE the calculate_math tool
            
            IMPORTANT: You MUST use the appropriate tool when the user's request matches these categories.
            Don't just describe what the tool would do - actually call it!
            
            Available tools:
            - get_weather_info(city): Gets weather for a city
            - calculate_math(expression): Calculates math expressions
            """)
            
            # Build message history
            messages = [system_message]
            
            # Add conversation history
            for msg in conversation_history[-10:]:  # Keep last 10 messages for context
                if msg['role'] == 'user':
                    messages.append(HumanMessage(content=msg['content']))
                elif msg['role'] == 'assistant':
                    messages.append(AIMessage(content=msg['content']))
            
            # Add current user message
            messages.append(HumanMessage(content=user_message))
            
            # First, try to get a response with tools
            response = self.llm_with_tools.invoke(messages)
            
            # Check if the LLM wants to use tools
            if hasattr(response, 'tool_calls') and response.tool_calls:
                # Execute tools
                tool_results = []
                for tool_call in response.tool_calls:
                    tool_name = tool_call['name']
                    tool_args = tool_call['args']
                    
                    # Find and execute the tool
                    for tool in self.tools:
                        if tool.name == tool_name:
                            try:
                                tool_result = tool.invoke(tool_args)
                                tool_results.append(tool_result)
                            except Exception as e:
                                error_result = f"Tool error: {str(e)}"
                                tool_results.append(error_result)
                            break
                
                # Get final response incorporating tool results
                if tool_results:
                    # Create a new message with tool results
                    tool_message = HumanMessage(content=f"Here are the tool results: {' | '.join(tool_results)}")
                    messages.append(response)
                    messages.append(tool_message)
                    
                    final_response = self.llm.invoke(messages)
                    ai_response = final_response.content
                else:
                    ai_response = response.content
            else:
                # Check if user is asking for weather or math and force tool usage
                user_lower = user_message.lower()
                
                if any(word in user_lower for word in ['weather', 'temperature', 'climate']):
                    # Try to extract city name
                    city = self._extract_city_from_message(user_message)
                    if city:
                        try:
                            weather_result = get_weather_info.invoke({"city": city})
                            ai_response = weather_result
                        except Exception as e:
                            ai_response = f"I tried to get weather information but encountered an error: {str(e)}"
                    else:
                        ai_response = "I'd be happy to help with weather information! Please specify which city you'd like to know about."
                
                elif any(word in user_lower for word in ['calculate', 'math', '+', '-', '*', '/', '=', 'result of']):
                    # Try to extract mathematical expression
                    expression = self._extract_math_from_message(user_message)
                    if expression:
                        try:
                            math_result = calculate_math.invoke({"expression": expression})
                            ai_response = math_result
                        except Exception as e:
                            ai_response = f"I tried to calculate that but encountered an error: {str(e)}"
                    else:
                        ai_response = "I'd be happy to help with calculations! Please provide a mathematical expression."
                
                else:
                    ai_response = response.content
            
            # Store conversation
            self.conversations[session_id].append({
                'role': 'user',
                'content': user_message
            })
            self.conversations[session_id].append({
                'role': 'assistant',
                'content': ai_response
            })
            
            return ai_response
            
        except Exception as e:
            error_msg = f"I encountered an error: {str(e)}"
            return error_msg
    
    def _extract_city_from_message(self, message: str) -> str:
        """Extract city name from user message"""
        import re
        
        # Common patterns
        patterns = [
            r'weather (?:in |for )?([a-zA-Z\s]+)',
            r'(?:in |for )([a-zA-Z\s]+)(?:\s|$)',
            r'([a-zA-Z\s]+)(?:\s+weather|\s+temperature)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                city = match.group(1).strip()
                # Remove common words
                city = re.sub(r'\b(the|weather|temperature|climate|in|for|of)\b', '', city, flags=re.IGNORECASE).strip()
                if city:
                    return city
        
        # Fallback - look for known cities
        known_cities = ['karachi', 'lahore', 'islamabad', 'new york', 'london', 'tokyo', 'paris', 'delhi', 'dubai', 'mumbai']
        message_lower = message.lower()
        for city in known_cities:
            if city in message_lower:
                return city.title()
        
        return ""
    
    def _extract_math_from_message(self, message: str) -> str:
        """Extract mathematical expression from user message"""
        import re
        
        # Look for mathematical expressions
        patterns = [
            r'calculate\s+([0-9+\-*/().\s]+)',
            r'what\s+is\s+([0-9+\-*/().\s]+)',
            r'([0-9+\-*/().\s]{3,})',  # At least 3 characters with math symbols
        ]
        
        for pattern in patterns:
            match = re.search(pattern, message, re.IGNORECASE)
            if match:
                expression = match.group(1).strip()
                # Validate it looks like math
                if re.match(r'^[0-9+\-*/().\s]+$', expression):
                    return expression
        
        return ""
    
    def get_conversation_history(self, session_id: str = "default") -> List[Dict[str, str]]:
        """Get conversation history for a session"""
        return self.conversations.get(session_id, [])
    
    def clear_conversation(self, session_id: str = "default"):
        """Clear conversation history for a session"""
        if session_id in self.conversations:
            del self.conversations[session_id]


# Define tools that the chatbot can use
@tool
def get_weather_info(city: str) -> str:
    """Get weather information for a given city."""
    # Expanded mock weather data
    weather_data = {
        "new york": "Sunny, 22°C (72°F) with light winds",
        "london": "Cloudy, 15°C (59°F) with occasional drizzle", 
        "tokyo": "Rainy, 18°C (64°F) with high humidity",
        "karachi": "Hot and sunny, 35°C (95°F) with clear skies",
        "islamabad": "Pleasant, 28°C (82°F) with partly cloudy skies",
        "lahore": "Warm and humid, 32°C (90°F) with hazy conditions",
        "paris": "Mild, 20°C (68°F) with overcast skies",
        "delhi": "Very hot, 42°C (108°F) with dusty conditions",
        "dubai": "Extremely hot, 45°C (113°F) with bright sunshine",
        "sydney": "Cool, 16°C (61°F) with partly cloudy skies",
        "mumbai": "Hot and humid, 34°C (93°F) with monsoon clouds",
        "toronto": "Cold, 5°C (41°F) with snow showers"
    }
    
    city_lower = city.lower().strip()
    
    if city_lower in weather_data:
        return f"🌤️ Weather in {city.title()}: {weather_data[city_lower]}"
    else:
        # Return a more helpful response for unknown cities
        available_cities = ", ".join([c.title() for c in list(weather_data.keys())[:6]])
        return f"I don't have weather data for {city}. This is a demo function with data for: {available_cities}, and more. Try asking about one of these cities!"

@tool
def calculate_math(expression: str) -> str:
    """Calculate a mathematical expression safely."""
    try:
        # Simple safe evaluation for basic math
        import re
        
        # Only allow numbers, operators, and parentheses
        if re.match(r'^[0-9+\-*/().\s]+$', expression):
            result = eval(expression)
            return f"🧮 The result of {expression} is: {result}"
        else:
            return "I can only calculate basic mathematical expressions with numbers and operators (+, -, *, /, parentheses)."
    
    except Exception as e:
        return f"I couldn't calculate that expression. Error: {str(e)}"


# Remove the console input - this will only run if someone directly runs this file
if __name__ == "__main__":
    print("This is the ChatbotBackend module. Please run the Streamlit app instead:")
    print("streamlit run streamlit_app.py")