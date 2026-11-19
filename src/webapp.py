"""Small web adapter for the existing YouTube transcript chatbot."""

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from langchain_core.documents import Document
from youtube_transcript_api import YouTubeTranscriptApi

from src.chunking import split_documents
from src.chatbot import create_chatbot
from src.transcript import extract_video_id
from src.vectorstore import create_retriever, create_vectorstore


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
chatbot = None
current_video_id = None


class AppHandler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def send_json(self, status, payload):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > 1_000_000:
            raise ValueError("Request must include a small JSON body.")
        payload = json.loads(self.rfile.read(length))
        if not isinstance(payload, dict):
            raise ValueError("Expected a JSON object.")
        return payload

    def do_POST(self):
        global chatbot, current_video_id

        if urlparse(self.path).path == "/api/video":
            try:
                payload = self.read_json()
                video_url = str(payload.get("url", "")).strip()
                video_id = extract_video_id(video_url)

                transcript = YouTubeTranscriptApi().fetch(
                    video_id, languages=["en", "en-US", "en-GB", "hi"]
                )
                transcript_text = " ".join(item.text for item in transcript)
                if not transcript_text.strip():
                    raise ValueError("No transcript text was found for this video.")

                document = Document(
                    page_content=transcript_text,
                    metadata={"video_id": video_id, "source": video_url},
                )
                chunks = split_documents([document])
                vectorstore = create_vectorstore(chunks)
                retriever = create_retriever(vectorstore)
                chatbot = create_chatbot(retriever)
                current_video_id = video_id

                self.send_json(200, {
                    "ok": True,
                    "video_id": video_id,
                    "transcript_preview": transcript_text[:650],
                    "transcript_characters": len(transcript_text),
                    "chunk_count": len(chunks),
                })
            except (ValueError, json.JSONDecodeError) as error:
                self.send_json(400, {"ok": False, "error": str(error)})
            except Exception as error:
                self.send_json(500, {
                    "ok": False,
                    "error": f"Could not prepare this video: {error}",
                })
            return

        if urlparse(self.path).path == "/api/chat":
            if chatbot is None:
                self.send_json(409, {
                    "ok": False,
                    "error": "Add a video and wait for its transcript before asking a question.",
                })
                return
            try:
                payload = self.read_json()
                question = str(payload.get("question", "")).strip()
                if not question:
                    raise ValueError("Enter a question about the video.")
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Transfer-Encoding", "chunked")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                try:
                    for part in chatbot.stream({"question": question}):
                        if not part:
                            continue
                        chunk = str(part).encode("utf-8")
                        self.wfile.write(f"{len(chunk):X}\r\n".encode("ascii"))
                        self.wfile.write(chunk + b"\r\n")
                        self.wfile.flush()
                except Exception as error:
                    print(f"Chat stream failed: {error}")
                    chunk = b"\n[The answer stream was interrupted. Check the server terminal for details.]"
                    self.wfile.write(f"{len(chunk):X}\r\n".encode("ascii"))
                    self.wfile.write(chunk + b"\r\n")
                    self.wfile.flush()
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
            except (ValueError, json.JSONDecodeError) as error:
                self.send_json(400, {"ok": False, "error": str(error)})
            except Exception as error:
                self.send_json(500, {"ok": False, "error": f"Could not answer the question: {error}"})
            return

        self.send_json(404, {"ok": False, "error": "Not found."})

    def log_message(self, format, *args):
        print(f"{self.address_string()} - {format % args}")


if __name__ == "__main__":
    address = ("127.0.0.1", 8000)
    print(f"YouTube chatbot UI: http://{address[0]}:{address[1]}")
    ThreadingHTTPServer(address, AppHandler).serve_forever()
