import os
from typing import Annotated
from typing_extensions import TypedDict
from dotenv import load_dotenv

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langchain_openai import ChatOpenAI 
from langchain_core.messages import HumanMessage, BaseMessage

# بارگذاری متغیرهای محیطی
load_dotenv()

# تعریف ساختار State (همون چیزی که خودت داشتی)
class State(TypedDict):
    messages: Annotated[list, add_messages]

class AIAgent:
    def __init__(self):
        """
        اینجا مدل و گراف رو یک بار می‌سازیم تا هر دفعه نخوایم لود کنیم.
        """
        api_key = os.getenv("API_AI")
        if not api_key:
            raise ValueError("Error: API_KEY not found in .env file")

        self.llm = ChatOpenAI(
            api_key=api_key, 
            model="gpt-5.2",
            base_url="https://api.gapgpt.app/v1",
            temperature=0
            )

        # تنظیم حافظه
        self.memory = MemorySaver()
        
        # ساخت گراف
        builder = StateGraph(State)
        builder.add_node("chatbot", self.chatbot_node)
        builder.add_edge(START, "chatbot")
        builder.add_edge("chatbot", END)
        
        # تغییر مهم ۳: این خط حتما باید اجرا شود تا ارور graph رفع شود
        self.graph = builder.compile(checkpointer=self.memory)
        print("✅ AI Graph compiled successfully!")

    def chatbot_node(self, state: State):
        """
        گره اصلی که پیام رو به مدل میده و جواب میگیره
        """
        messages = state["messages"]
        response = self.llm.invoke(messages)
        return {"messages": [response]}

    async def chat(self, user_id: int, user_message: str) -> str:
        """
        این تابع اصلیه که ربات تلگرام صدا میزنه.
        user_id: آیدی عددی کاربر (برای اینکه حافظه قاطی نشه)
        user_message: متنی که کاربر فرستاده
        """
        # تنظیم کانفیگ برای حافظه اختصاصی هر کاربر
        config = {"configurable": {"thread_id": str(user_id)}}
        
        # ساخت پیام کاربر
        input_message = HumanMessage(content=user_message)
        
        # استفاده از ainvoke (نسخه Async) برای اینکه ربات هنگ نکنه
        # ما اینجا کل دیکشنری خروجی رو میگیریم
        result = await self.graph.ainvoke(
            {"messages": [input_message]}, 
            config=config
        )
        
        # آخرین پیام رو که جواب هوش مصنوعیه استخراج می‌کنیم
        last_message: BaseMessage = result["messages"][-1]
        return last_message.content

# این تیکه برای تست دستی فایله که ببینی کار میکنه یا نه
if __name__ == "__main__":
    import asyncio
    async def test():
        agent = AIAgent()
        print(await agent.chat(123, "Hello, who are you?"))
    
    asyncio.run(test())