from langchain_openai import OpenAIEmbeddings
from dotenv import load_dotenv

load_dotenv()

def get_embedding_model():

    embeddings = OpenAIEmbeddings(
        model="text-embedding-3-small",
    )

    return embeddings


def generate_embeddings(chunks):

    embeddings = get_embedding_model()

    chunk_embeddings = []

    vectors = embeddings.embed_documents(
        [chunk.page_content for chunk in chunks]
    )

    return chunk_embeddings


if __name__ == "__main__":

    model = get_embedding_model()

    vector = model.embed_query("What is RAG?")

    print("Embedding dimensions:", len(vector))
    print("First 5 values:", vector[:5])