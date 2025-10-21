from langchain_ollama import ChatOllama
from langchain.tools import tool, BaseTool
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from pymongo import MongoClient
from langchain.agents import AgentType, tool, initialize_agent, AgentExecutor

# Import Utils
from utils.callback_handler import PrintCallbackHandler
from utils.conversation_buffer_safe import SafeConversationMemory
from utils.model_schema import HelpPost
from utils.mongo import get_help_posts_collection


class HelpPostAgent:
    def __init__(self, model: str):
        self.llm = ChatOllama(model, temperature = 0, verbose = True, streaming = True, callbacks = [PrintCallbackHandler()])
        self.memory = SafeConversationMemory(
            memory_key = "chat_history",
            return_messages = True
        )
        self.parser = PydanticOutputParser(pydantic_object = HelpPost)
        
        #MongoDB Store
        self.collection = get_help_posts_collection()
        self.agent = self.build_agent()
    
    def build_agent(self) -> AgentExecutor:
        """Builds a REACT Agent"""
        system_template = """
        You are a helper agent expert in handling posts of the users. 
        Your responsibilities:
        1. Use the 'create_post' tool when a user submits a new request/offer.
            - Extract role (elderly/youth), text, interests, and location.
            - Store it in the database with embedding an
        2. Use the 'edit_post' tool when a user wants to update their existing post.
            - Identify the post by user_id and edit the relevant fields (text, interests, or location).
            - Ensures changes are saved correctly.
        3. Use the 'delete_post' tool when a user requests removal of their post.
            - Identify the post by user_id and remove it from the database. 
        
        Rules:
        - Always confirm after create, edit, or delete with a short, friendly message.
        - Never skip calling the correct tool - always use the tools for database operations.
        - When creating or editing, infer interests if not provided.
        - Only one operation shnould be executed per user request. 
        """

        return initialize_agent(
            llm = self.llm,
            tools = self.get_tools(),
            agent = AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
            memory = self.memory,
            verbose = True, 
            agent_kwargs = {"system_message" : system_template}
        )
    
    def get_tools(self) -> list[BaseTool]:
        @tool("create_post")
        def create_post(self, inputs: dict) -> str:
            """Creates a structured help post from a user's query and inserts into DB"""
            query = inputs['query']

            # Parse Query
            template = """
            Extract structured help post info from the following user query.
            Query = "{query}".

            Return JSON with:
            - query : original request/offer
            - interests : list of keywords (tech, errands, care, social, etc) that best matches with the query.
            """

            prompt = PromptTemplate.from_template(template)
            chain = prompt | self.llm | self.parser
            post = chain.invoke({"query" : query})

            # Adding Metadata
            for key, value in inputs.items():
                if key in post:
                    continue
                post[key] = value

            # Storing in DB
            self.collection.insert_one(post)

            return f"Help Post created for {inputs['user_id']} : {post['text']}(role = {post['role']}, location = {post['location']})"

        @tool("edit_post")
        def edit_post(self, inputs: dict) -> str:
            """Edit an existing help post by user_id"""
            user_id = inputs['user_id']
            updates = {k : v for k, v in inputs.item() if k != "user_id"}
            result = self.collection.update_one({"user_id" : user_id}, {"$set" : updates})
            return f"Help Post updated for {user_id}" if result.modified_count > 0 else "No Help Post found to update."

        @tool("delete_post")
        def delete_post(self, inputs: dict) -> str:
            """Delete a help post by user_id"""
            user_id = inputs['user_id']
            result = self.collection.delete_one({"user_id" : user_id})
            return f"Post deleted for {user_id}" if result.deleted_count > 0 else "No Help Post found to delete"

        return [create_post, edit_post, delete_post]

    def run(self, state: dict[str, str]) -> dict[str, str]:
        """Agent scrapes/analyzes article"""
        result = self.agent.invoke({"input" : state['query']})       
        output = result['output']
        return output
    
if __name__ == "__main__":
    agent = HelpPostAgent(model = "llama3.1")
    state = {"query" : "I need"}
    results = agent.run(state)
    print(results)

             
        


            
            
