from urllib.parse import urlparse, parse_qs
import re
from youtube_transcript_api import YouTubeTranscriptApi
from langchain_core.documents import Document

from src.chunking import split_documents

from src.vectorstore import create_vectorstore, create_retriever

from src.chatbot import create_chatbot

def extract_video_id(video_url : str) -> str:
    
    parsed_url = urlparse(video_url)

    if parsed_url.hostname in ["youtu.be", "www.youtu.be"]:
        video_id = parsed_url.path.lstrip("/").split("/")[0]

    elif parsed_url.hostname in [
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com"
    ]:

        if parsed_url.path == "/watch":
            video_id = parse_qs(parsed_url.query).get("v", [None])[0]
        else: 
            video_id = parsed_url.path.split("/")[-1]

    else:
        raise ValueError("Invalid YouTube URL")

    if not video_id or not re.fullmatch(r"[A-Za-z0-9_-]{11}", video_id):
        raise ValueError("Could not extract a valid YouTube video ID")


    return video_id



if __name__ == "__main__":

    video_url = input("Enter the YouTube video URL: ")
    video_id = extract_video_id(video_url)

    youtube_api = YouTubeTranscriptApi()
    transcript = youtube_api.fetch(video_id, languages=['en', 'en-US', 'en-GB', 'hi'])

    transcript_text = []

    for i in transcript:
        transcript_text.append(i.text)

    full_transcript = " ".join(transcript_text)

    # print(full_transcript)


    document = Document(
        page_content = full_transcript,
        metadata = {
            "video_id": video_id,
            "source" : video_url
        }
    )

    # print(document)
    # print(document.metadata)
    # print(document.page_content[:500])

    chunks = split_documents([document])
    # print("Total Chunks: ", len(chunks))

    # for i, chunk in enumerate(chunks[:3]):
    #     print(f"\nChunk {i + 1}:")
    #     print(chunk.page_content)
    #     print(chunk.metadata)

    vectorstore = create_vectorstore(chunks)
    print("Vectorstore created successfully.")

    retriever = create_retriever(vectorstore)

    # query = "what are the main topics explained in the video?"

    # results = retriever.invoke(query)

    # for i, result in enumerate(results):
    #     print(f"\nResult {i + 1}:")
    #     print(result.page_content)
    #     print(result.metadata)

    chatbot = create_chatbot(retriever)

    while True:
        question = input("\nAsk a question about the video (or type 'exit' to quit): ")

        if question.lower() == "exit":
            break

        response = chatbot.invoke({"question": question})

        print("\nChatbot Response: ", response)

