# Sienna – Your Dynamic AI Voice Companion

This repository contains the source code for Sienna. It can run locally on the
user’s machine.

## Requirements
Sienna requires the following to run properly:
- An audio input and output device
- A web browser and Internet connection
	- So far, Sienna has only been tested in Firefox, but it should be able to
	run in other browsers.
- Python ≥ 3.10
- The following Python packages: `Flask Flask_Cors Flask_SocketIO openai python-dotenv websockets`
	- You may need to install additional packages depending on your operating
	environment.

*Note:* Sienna has been confirmed to run on Ubuntu Desktop, Fedora Workstation,
and Windows 10. It **may or may not** work on other systems, so please report
any additional testing.

## Usage
To run Sienna, type `python3 index.py` to start the server. Then, navigate to
http://localhost:3000 in your browser. The Sienna UI should be displayed.

### API Keys
To run Sienna yourself, you will need an API key from OpenAI and ElevenLabs.
**These are not free of charge**.

Once you have your keys, please set them as environment variables like this:
```
ELEVENLABS_API_KEY=<ElevenLabs API key>
OPENAI_API_KEY=<OpenAI API key>
```

Alternatively, you can put the above into a file named `.env`, and save this
file in the same directory as the Python script.