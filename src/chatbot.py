from operator import itemgetter

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


def create_chatbot(retriver):

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0.2,
        max_tokens=500
    )

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """
            You are a helpful YouTube video assistant.

            Answer the user's question using only the
            provided video transcript context.

            If the answer is not available in the context,
            say that the information is not available
            in the video transcript.
            """
        ),
        (
            "human",
            """
            Context:
            {context}

            Question:
            {question}
            """
        )
    ])

    def format_documents(documents):
        return "\n\n".join(
            document.page_content for document in documents
        )

    chatbot = (
        {
            "context": itemgetter("question") | retriver | format_documents,
            "question": itemgetter("question")
        }

        | prompt | llm | StrOutputParser()
    )

    return chatbot