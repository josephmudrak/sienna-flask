import asyncio
import base64
import json
import os
import websockets

from dotenv import load_dotenv
from flask import Flask, request, render_template
from flask_cors import CORS
from flask_socketio import SocketIO
from io import BytesIO
from openai import AsyncOpenAI

load_dotenv()	# Take environment variables from .env

openai		= AsyncOpenAI(api_key = os.environ.get("OPENAI_API_KEY"))
VOICE_ID	= "oWAxZDx7w5VEj9dCyTzz"	# Grace

# Initialise Flask
app	= Flask(__name__)
CORS(app)

# Initialise SocketIO for WebSocket streaming
socketio	= SocketIO(app, async_mode="threading")

# Queue to store audio chunks
audio_chunk_queue	= asyncio.Queue()

@app.route("/", methods = ["GET", "POST"])
def get_message():
	return render_template("index.htm")

# Handle audio chunk event
@socketio.on("audio_chunk", namespace="/stream")
def handle_audio_chunk(chunk_data):
	print(f"Received audio chunk: {chunk_data}")
	socketio.emit("audio_chunk", {"audio": chunk_data}, namespace="/stream")

# Stream audio data to front-end
async def stream_audio_to_front_end(audio_stream):
	async for chunk in audio_stream:
		chunk_data		= chunk.read()
		base64_audio	= base64.b64encode(chunk_data).decode("utf-8")
		
		# Queue audio chunk
		await audio_chunk_queue.put({"audio": base64_audio})
		
	# Return empty response to show completion
	return b''

# Handle start of audio stream
@socketio.on("connect", namespace="/stream")
def handle_connect():
	print("Client connected")

	# Audio chunks queued?
	while not audio_chunk_queue.empty():
		# De-queue & emit audio chunk
		chunk_data	= audio_chunk_queue.get_nowait()
		socketio.emit("audio_chunk", chunk_data, namespace="/stream")

# Handle end of audio stream
@socketio.on("disconnect", namespace="/stream")
def handle_disconnect():
	print("Client disconnected")

# Split text into chunks, ensuring not to break sentences
async def text_chunker(chunks):
	splitters	= (
		".", ",", "?", "!", ";", ":", "—",
		"-", "(", ")", "[", "]", "}", " "
		)
	buffer		= ""

	async for text in chunks:
		if buffer.endswith(splitters):
			yield buffer + " "
			buffer	= text
		elif text.startswith(splitters):
			yield buffer + text[0] + " "
			buffer	= text[1:]
		else:
			buffer	+= text

	if buffer:
		yield buffer + " "

# Get TTS from ElevenLabs
async def stream_tts(voice_id, text_iterator):
	uri	= f"wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input?model_id=eleven_monolingual_v1"

	async with websockets.connect(uri) as websocket:
		await websocket.send(json.dumps({
			"text":				" ",
			"voice_settings":	{"stability": 0.5, "similarity_boost": 0.8},
			"xi_api_key":		os.environ.get("ELEVENLABS_API_KEY")
		}))

		# Listen to WebSocket for audio data & stream
		async def listen():
			while True:
				try:
					message	= await websocket.recv()
					data	= json.loads(message)

					if data.get("audio"):
						# Convert audio to streamable raw data
						yield BytesIO(base64.b64decode(data["audio"]))
					elif data.get("isFinal"):
						break
				except websockets.exceptions.ConnectionClosed:
					print("Connection closed")
					break

		# Stream audio to front-end
		listen_task	= asyncio.create_task(stream_audio_to_front_end(listen()))

		async for text in text_chunker(text_iterator):
			await websocket.send(json.dumps({
				"text":						text,
				"try_trigger_generation":	True
			}))

		await websocket.send(json.dumps({"text": ""}))

		await listen_task

		return json.dumps({"success": True}), 200

# Retrieve text from OpenAI
@app.route("/reply", methods = ["GET", "POST"])
async def process_transcription():
	query		= request.data.decode("utf-8")	# Get transcription as string
	response	= await openai.chat.completions.create(
		model="gpt-4-1106-preview",
		messages=[{"role": "user", "content": query}],
		temperature=1,
		stream=True,
		max_tokens=15	# Artifically limit number of tokens (for testing only)
	)

	async def text_iterator():
		async for chunk in response:
			delta	= chunk.choices[0].delta

			if delta.content:
				yield delta.content

	await stream_tts(VOICE_ID, text_iterator())
	return json.dumps({"success": True}), 200
	

if __name__ == "__main__":
	socketio.run(app, host = "0.0.0.0", debug = True, port = 3000)