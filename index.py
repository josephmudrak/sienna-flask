import asyncio
import json
import os

import elevenlabs
from dotenv import load_dotenv
from flask import Flask, render_template, request
from flask_cors import CORS
from flask_socketio import SocketIO
from openai import OpenAI

load_dotenv()  # Take environment variables from .env

openai: OpenAI = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
VOICE_ID: str = "oWAxZDx7w5VEj9dCyTzz"  # Grace

messages: list[dict] = []

# Initialise Flask
app = Flask(__name__)
CORS(app)

# Initialise SocketIO for WebSocket streaming
socketio = SocketIO(
    app,
    async_mode="threading",
    # Allow localhost
    cors_allowed_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
)

# Queue to store audio chunks
audio_chunk_queue = asyncio.Queue()


@app.route("/", methods=["GET", "POST"])
def get_message():
    return render_template("index.htm")


# Handle audio chunk event
@socketio.on("audio_chunk", namespace="/stream")
def handle_audio_chunk(chunk_data):
    print(f"Received audio chunk: {chunk_data}")
    socketio.emit("audio_chunk", {"audio": chunk_data}, namespace="/stream")


# Handle start of audio stream
@socketio.on("connect", namespace="/stream")
def handle_connect():
    print("Client connected")

    # Audio chunks queued?
    while not audio_chunk_queue.empty():
        # De-queue & emit audio chunk
        chunk_data = audio_chunk_queue.get_nowait()
        socketio.emit("audio_chunk", chunk_data, namespace="/stream")


# Handle end of audio stream
@socketio.on("disconnect", namespace="/stream")
def handle_disconnect():
    print("Client disconnected")


# Retrieve text from OpenAI
@app.route("/reply", methods=["GET", "POST"])
def process_transcription():
    print("Received transcription")
    global messages
    query = request.data.decode("utf-8")  # Get transcription as string
    messages.append({"role": "user", "content": query})
    response = openai.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=messages,
        temperature=0.6,
        stream=True,
        max_tokens=15,  # Artifically limit number of tokens (for testing only)
    )
    current_response: str = ""

    def text_iterator():
        for chunk in response:
            delta = chunk.choices[0].delta

            if delta.content is not None:
                nonlocal current_response
                current_response += delta.content
                yield delta.content

    generator = text_iterator()
    elevenlabs.stream(
        elevenlabs.generate(
            text=generator,
            voice=VOICE_ID,
            model="eleven_turbo_v2",
            stream=True,
            api_key=os.getenv("ELEVENLABS_API_KEY"),
            latency=3,
        )
    )
    messages.append({"role": "assistant", "content": current_response})
    return json.dumps({"success": True}), 200


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", debug=True, port=3000)
