from langchain_openai import ChatOpenAI
import os
llmmodel = ChatOpenAI(
    api_key=os.environ.get('longcat_api'),
    base_url="https://api.longcat.chat/openai",
    model="LongCat-Flash-Chat",
    ##base_url="https://api.minimaxi.com/v1",
    ##model="LongCat-Flash-Thinking",
)

basemodel = ChatOpenAI(
    api_key=os.environ.get('longcat_api'),
    base_url="https://api.longcat.chat/openai",
    model="LongCat-Flash-Chat",
    temperature=0
)


