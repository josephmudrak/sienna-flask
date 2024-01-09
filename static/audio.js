document.addEventListener("DOMContentLoaded", async () =>
{
	const btnStart	= document.getElementById("recStart");

	navigator.mediaDevices.getUserMedia({audio: true}).then(stream =>
	{
		const mediaRecorder	= new MediaRecorder(stream);
		
		btnStart.addEventListener("click",  () =>
		{
			// Initialise connection to Deepgram
			const dgSocket	= new WebSocket(
				"wss://api.deepgram.com/v1/listen",
				["token", "a12a55ee5b9e4bb5ed14bcbf6f8af42acfa0c63d"]
			);

			// Logging WebSocket events
			dgSocket.onopen	= () =>
			{
				// Send data to Deepgram in increments
				mediaRecorder.addEventListener("dataavailable", event =>
				{
					if (event.data.size > 0 && dgSocket.readyState == 1)
					{
						dgSocket.send(event.data);
					}
				});

				mediaRecorder.start(150);
			}

			dgSocket.onmessage	= async(msg) =>
			{
				// Parse data sent from Deepgram
				const dgReceived	= JSON.parse(msg.data);
				const dgTranscript	=
					dgReceived.channel.alternatives[0].transcript;
				
				if (dgTranscript && dgReceived.is_final)
				{
					console.log(dgTranscript);
					mediaRecorder.stop();
					dgSocket.close();

					// Send to GPT-4 & ElevenLabs
					await fetch("/reply", {method: "POST", body: dgTranscript});
					
					// WebSocket compatible with SocketIO to back-end
					const elSocket	= io.connect(
						"http://localhost:3000/stream"
					);

					// Queue for audio chunks
					let audioChunks		= [];
					let audioElement	= new Audio();

					let audioContext	= null;

					// Audio currently playing?
					let isPlaying		= false;

					// Logging
					elSocket.on("connect", () =>
					{
						console.log("WebSocket connection opened")
					})

					elSocket.on("audio_chunk", async(data) =>
					{
						// Add audio chunk to queue
						audioChunks.push(data.audio);

						// If not currently playing, start playback
						if (audioElement.paused)
						{
							await playNextChunk();
						}
					});

					elSocket.on("disconnect", () =>
					{
						console.log("WebSocket connection closed")
					});

					async function playNextChunk()
					{
						// Chunks remaining in queue?
						if (audioChunks.length > 0)
						{
							// Next chunk as audio element source
							audioElement.src	= `data:audio/mp3;base64,${audioChunks.shift()}`;

							audioElement.play();

							audioElement.onended	= playNextChunk;
						}
					}

					playNextChunk();
					dgSocket.close();
				}
			}

			dgSocket.onerror	= (err) =>
			{
				console.log({event: "onerror", err});
			}
		});
	})
	.catch(err => console.error("Error accessing microphone:", err));
});

// Convert base64-encoded string to Blob
function base64toBlob(base64, type)
{
	const strBin	= window.atob(base64);
	const len		= strBin.length;
	const bytes		= new Uint8Array(len);
	
	for (let i = 0; i < len; i++)
	{
		bytes[i]	= strBin.charCodeAt(i);
	}

	return new Blob([bytes], {type: type});
}

// Convert Blob to ArrayBuffer
function audioBlobToArrayBuffer(blob)
{
	return new Promise((resolve) =>
	{
		const reader	= new FileReader();

		reader.onloadend	= () =>
		{
			resolve(reader.result);
		}

		reader.readAsArrayBuffer(blob);
	});
}

// Convert base64 to ArrayBuffer
function base64ToArrayBuffer(base64)
{
	const strBin	= window.atob(base64);
	const len		= strBin.length;
	const bytes		= new Uint8Array(len);

	for (let i = 0; i < len; i++)
	{
		bytes[i]	= strBin.charCodeAt(i);
	}

	return bytes.buffer;
}