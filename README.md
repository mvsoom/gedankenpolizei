# gedankenpolizei

> *I be me, you be the thought police*

**gedankenpolizei** is an experiment where you, gentle user, gets to observe a continuous stream of consciousness from an AI, in real-time.

The code simulates a hurried, frantic inner monologue that we sometimes find ourselves having. The AI has sight (but it can't hear) and might comment on what it sees, or it might choose to ignore it altogether.

You are the judge of the inner thoughts of a "sentient" simulacrum ... a dystopian visualization of the thought police creeping ever closer to our deepest thoughts. I mean, that's dark, but also serious fun when you have it running in the background. Plus you finally found another use for `lolcat` other than `fortune | cowsay` :)

## Installation

I used Python 3.10.12. Install the runtime in a venv, clone this repo and then do
```bash
pip install -r requirements.txt
```
as usual.

Then create an env file:
```bash
touch .env
```
and fill a project ID for Vertex AI:
```bash
PROJECT_ID=[key here]
```
Note: I used Gemini Flash and Pro 1.5 with safety turned off and maxed out RPM at 1000. I also chose a server location close by me to minimize latency; if you experience latency issues you can set the location by changing the `gemini.location` key in `config.yaml`.

Then install the following programs:
```bash
ffmpeg
websocat  # make sure this is in PATH
```

Optional programs to install additionally are:
```bash
mdcat            # For visualizing logs
cool-retro-term  # For fancy output
lolcat           # For fancy output
```

### SLOW stream

If you want to use the SLOW thought stream, things are a bit more involved. Either you scrape and process it yourself as explained in `src/slow/reddit/REDDIT.md`, or you acquire Hugging Face tokens from me and put them in the `.env` file next to the `PROJECT_ID`:
```bash
PROJECT_ID=[key here]
HF_TOKEN_READ=[key here]
HF_TOKEN_WRITE=[key here]
```
Then you can run the following commands to cold-start and cache the embedding model and seeding SLOW thoughts:
```bash
python -m src.slow.embed   # Download embedding model
python -m src.slow.thought # Download seed SLOW thoughts
```
This is not required but enables a smooth first run.

## Properties and capabilities

The AI consists of Gemini 1.5 Flash and Pro, the former handling vision input and the latter outputting the raw stream of thoughts at **maximum** temperature. One reason to write this code was to get more insight at the less explored high temperature regime of LLMs (Gemini in this case).

The prompts used for each module are in `data/prompts`. Importantly, the design of gedankenpolizei uses **minimal prompt engineering**. Actually one of the things I learned while tuning for this partcular purpose is that "everytime I fired a prompt instruction, the output quality went up". For example, the system prompt conditioning the generation of the stream of consciousness is just:
```bash
$ cat data/prompts/raw/gemini.system_prompt 
I don't know what or who you are, only that you are immersed in RAW thoughts that flow spontaneously from deeper SLOW and present FAST thoughts and moods.
Complete the RAW stream directly, without repeating any of it!
```
Nothing of the output is scripted; there is minimal guidance.

The code consists of a fancy frontend (`client/client.html`) which delivers a dystopian visualization of the project, and a text-based backend which calculates the RAW thoughts based FAST and SLOW input thoughts as a walk in semantic (embedding) space.[^1] The logic is set up as a stream of data transformers. For example,
```bash
google-chrome client/client.html &        # Start frontend
grab/websocket | \                        # Grab the webcam stream exposed by the frontend
python -m src.fast.narrate \
    --config fast.novelty_threshold:10 \
    --jsonl \
    --output-frames | \                   # Process the webcam stream in near-realtime into FAST thoughts
python -m src.raw.stream \
    --config raw.memory_size:128 \
    --config slow.pace:0.5 \
    --config raw.pace:16 \
    --roll-tape \                         # Process FAST and SLOW thoughts into RAW thoughts and visualize them
    2> >(emit/websocket)                  # Send the RAW thoughts back to the client
```
This round-trip architecture has a latency of about (max) 1.5 seconds; meaning that the AI is generally aware of you waving your hand maximuum 1.5 seconds after the fact. Lower latencies are possible in some cases, which can be explored by tinkering with the parameters in `config.yaml` or passed directly through command line switches `--config key:value` is in the example above.

[^1]: See `src/slow/reddit/REDDIT.md` for more details on how the SLOW stream is designed. Its job is to seed the RAW thoughts with thought themes and moods.

### Transforming and monitoring streams

You can choose an optional vision **input source** by running one of the programs in `grab/`; available are webcam, screencast, movie files. For example, I like to keep gedankenpolizei open in a monitor while it watches me code; its quirky thoughts give a sort of lightness to the moment or provide some creative distraction.

You can choose the stream of consciousness **output source** by running one of the programs in `emit/` to transform the output in a fancy way, but this is completely optional and just adds persona to the output. I like to use `lolcat` for example:
```bash
python -m src.raw.stream | emit/lolcat
```

It is also possible to **monitor** the data streams by running one of the programs in `monitor/`, for example to see visualize the vision input stream:
```bash
monitor/log logs/src/fast/narrate.md
```

## Credits

- I want to thank Thalïa Viaene for unwavering support and love and Mathias Mu for artistic bro-support.
- Thanks to Google for providing an incredible LLM, generous credits and a stable API in terms of service and latency!
- Further thanks go to the `three.js` project and all the other open source projects this repo uses.