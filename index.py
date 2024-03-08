import json
import os

import elevenlabs
import pandas as pd

from dotenv import load_dotenv
from flask import Flask, render_template, request
from flask_cors import CORS
from flask_socketio import SocketIO
from openai import OpenAI
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

load_dotenv()  # Take environment variables from .env

# Initialise configuration
conversation_file: str = None
embeddings_file: str = None

while True:
    try:
        with open("config.json", "r") as f:
            try:
                config = json.load(f)
                conversation_file = config["conversations"]
                embeddings_file = config["embeddings"]
                prompt = config["prompt"]
            except json.decoder.JSONDecodeError:
                conversation_file = "data/convs.csv"
                embeddings_file = "data/embed.csv"
                config = {
                    "conversations": conversation_file,
                    "embeddings": embeddings_file,
                    "prompt": prompt,
                }

        with open("config.json", "w") as f:
            json.dump(config, f)

    except FileNotFoundError:
        f = open("config.json", "x")
        f.close()
        continue
    break

openai: OpenAI = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel

# Load conversation embeddings and model
while True:
    try:
        conversation_embeddings = pd.read_csv(embeddings_file).values
        df = pd.read_csv(conversation_file)
    except FileNotFoundError:
        # Create CSVs if they do not exist
        f = open(conversation_file, "x")
        g = open(embeddings_file, "x")
        f.close()
        g.close()
        continue
    break


model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def find_similar_conversations(query):
    query_embedding = model.encode([query])
    similarities = cosine_similarity(query_embedding, conversation_embeddings)
    top_k = 1
    most_similar_indexes = similarities.argsort()[0][::-1][:top_k]
    similar_conversations = (
        df["Conversation"].iloc[most_similar_indexes].tolist()
    )

    print(f"Query Embedding: {query_embedding[0][:10]}... (first 10 elements)")
    print(f"Top Similar Conversation: {similar_conversations[0]}")

    return similar_conversations


# Flask app initialization
app = Flask(__name__)
CORS(app)
socketio = SocketIO(
    app,
    async_mode="threading",
    cors_allowed_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
)


@app.route("/", methods=["GET", "POST"])
def get_message():
    return render_template("index.htm")


# SocketIO event handlers
@socketio.on("connect", namespace="/stream")
def handle_connect():
    print("Client connected")


@socketio.on("disconnect", namespace="/stream")
def handle_disconnect():
    print("Client disconnected")


# Messages history
messages: list[dict] = [{"role": "system", "content": prompt}]


@app.route("/reply", methods=["GET", "POST"])
def process_transcription():
    print("Received transcription")
    query = request.data.decode("utf-8")
    similar_conversations = find_similar_conversations(query)

    if similar_conversations:
        top_conversation = similar_conversations[0]
        conversation_context = f"CONVERSATION EXAMPLE: {top_conversation}"
        messages.append({"role": "system", "content": conversation_context})

    messages.append({"role": "user", "content": query})

    response = openai.chat.completions.create(
        model="gpt-4-1106-preview",
        messages=messages,
        temperature=0.5,
        stream=True,
        max_tokens=150,
    )
    current_response: str = ""

    def text_iterator():
        socketio.emit("message", "new_response", namespace="/stream")
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content is not None:
                nonlocal current_response
                current_response += delta.content
                socketio.emit("message", delta.content, namespace="/stream")
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
