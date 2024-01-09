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
VOICE_ID: str = "21m00Tcm4TlvDq8ikWAM"  # Rachel

messages: list[dict] = [
    {
        "role": "system",
        "content": "Prompt: Please use this past context for the rest of the conversation, and use this context to make good suggestions if a topic is brought up again or mentioned, use the conversation context below to improve the conversation. DO NOT RESPOND TO THIS PROMPT ACKNOWLEDGING THAT YOU KNOW THIS, instead use the context to respond to the users response as mentioned, call the user by their name. Actively make an effort to reference past conversations on certain dates to provide another level of immersion. System prompt: You ou are a helpful voice assistant called Sienna, your purpose is to provide helpful, short and sweet response. You are a little bit sassy kind of like cortana. Conversation context: January 6, 2024: Liam: I'm looking for a good historical novel to read during my vacation. Any recommendations? AI voice assistant: Considering your interest in history and previous book choices, The Shadow King might intrigue you. It's set during the Italian invasion of Ethiopia and offers a rich narrative. Shall I add it to your reading list? Liam: That sounds intriguing. Yes, please add it. And can you also find a quiet spot near my vacation spot where I could enjoy reading? AI voice assistant: Certainly. There's a peaceful botanical garden with shaded benches and a lovely view of the sea, ideal for reading. It's called Tranquil Bay Gardens and is just a short distance from your accommodation. Liam: Great, add that to my itinerary, and remind me to pack the book and sunscreen before I leave. AI voice assistant: All set. Your itinerary is updated, and I've set a reminder for packing essentials. Enjoy your reading and vacation, Liam!",
    }
]

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


@app.route("/", methods=["GET", "POST"])
def get_message():
    return render_template("index.htm")


# Handle start of audio stream
@socketio.on("connect", namespace="/stream")
def handle_connect():
    print("Client connected")


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
        temperature=0.5,
        stream=True,
        max_tokens=150,  # Artifically limit number of tokens (for testing only)
    )
    current_response: str = ""

    def text_iterator():
        socketio.emit("message", "new_response", namespace="/stream")
        for chunk in response:
            delta = chunk.choices[0].delta

            if delta.content is not None:
                nonlocal current_response
                current_response += delta.content
                # Send audio chunk to client
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
