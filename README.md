# gedankenpolizei

https://github.com/user-attachments/assets/08b1bf15-da92-46db-9b0b-c1578b2be271

[[Youtube demo](https://www.youtube.com/watch?v=OIdcJpiyxC0)] [[Longer demo](https://www.youtube.com/watch?v=JX2Fib6inp0)]

> *I be me, you be the thought police*

**gedankenpolizei** is an experiment where you get to observe a continuous stream of consciousness from an AI, in real-time. The video shows a demo of the code and is completely unscripted and in real time. This is part of research into more relatable NPCs (non-playable characters) that are aware of their environment.

The code simulates a hurried, frantic inner monologue that we sometimes find ourselves having. The AI has sight (but it can't hear) and might comment on what it sees, or it might choose to ignore it altogether.

You are the judge of the inner thoughts of a "sentient" simulacrum ... a dystopian visualization of the thought police creeping ever closer to our deepest thoughts. I mean, that's dark, but also serious fun when you have it running in the background. Plus you finally found a new excuse to use `lolcat` :)

<p align="center">
  <img width="440" src="https://github.com/mvsoom/gedankenpolizei/blob/main/data/examples/lolcat.gif">
</p>

## Installation and quick run

I used Python 3.10.12. Install the runtime in a venv, clone this repo and then do
```bash
pip install -r requirements.txt
```
as usual.

Then create an env file:
```bash
touch .env
```
and insert a project ID for Vertex AI into the newly created `.env` file:
```bash
PROJECT_ID=[key here]
```
Note: I used Gemini Flash and Pro 1.5 with safety turned off and maxed out RPM at 1000. I also chose a server location close by me to minimize latency; if you experience latency issues you can set the location by changing the `gemini.location` key in [`config.yaml`](./config.yaml).

Then install the following programs:
```bash
ffmpeg    # Probably on your system already
websocat  # https://github.com/vi/websocat
```
and run the demo script used to generate the video above to see it in action:
```bash
google-chrome client/client.html &  # Or Chromium or Firefox -- see QA.md
scripts/demo.sh
```
You can press `SPACE` to move the camera around and `C` to explore the weirdness.

### SLOW stream

To get the same output quality as the demo, you need to activate the SLOW thought stream, and things are a bit more involved. Either you scrape and process it yourself as explained in [`REDDIT.md`](./src/slow/reddit/REDDIT.md), or you acquire Hugging Face tokens from me[^1] and put them in the `.env` file next to the `PROJECT_ID`:
```bash
PROJECT_ID=[key here]
HF_TOKEN_READ=[key here]
HF_TOKEN_WRITE=[key here]
```
Then you can run the following commands to cold-start and cache the embedding model and seeding SLOW thoughts:
```bash
python -m src.slow.embed    # Download embedding model
python -m src.slow.thought  # Download seed SLOW thoughts
```
This is not required but enables a smooth first run.

[^1]: The unfortunate reason for gating the seeding SLOW thoughts is explained in [`QA.md`](./QA.md).

## Properties and capabilities

The AI consists of Gemini 1.5 Flash and Pro, the former handling vision input and the latter outputting the raw stream of thoughts at **maximum** temperature. One reason to write this code was to get more insight at the less explored high temperature regime of LLMs (Gemini in this case).

If vision input is enabled, the round-trip architecture has a latency of max 1.5 seconds; meaning that the AI is generally aware of you typing code or waving your hand max 1.5 seconds after the fact. Lower latencies up to 0.7 seconds are generally possible and can be explored by tinkering with the parameters in [`config.yaml`](./config.yaml) or passed directly through command line switches in `--config key:value` form.

The prompts used for each module are in [`data/prompts/`](./data/prompts/). Importantly, the design of gedankenpolizei uses **minimal prompt engineering**. Actually one of the things I learned while tuning for this partcular purpose is that "everytime I fired a prompt instruction, the output quality went up". For example, the system prompt conditioning the generation of the stream of consciousness is just:
```bash
$ cat data/prompts/raw/gemini.system_prompt 
I don't know what or who you are, only that you are immersed in RAW thoughts that flow spontaneously from deeper SLOW and present FAST thoughts and moods.
Complete the RAW stream directly, without repeating any of it!
```
Nothing of the output is scripted; there is minimal guidance.

The code consists of a fancy frontend ([`client.html`](./client/client.html)) which delivers a dystopian visualization of the project, and a text-based backend which calculates the RAW thoughts, from FAST and SLOW input thoughts, as a walk in semantic (embedding) space.[^2] The logic is set up as a stream of data transformers. For example,
```bash
google-chrome client/client.html &      # Start frontend
grab/websocket | \                      # Grab the webcam stream exposed by the frontend
python -m src.fast.narrate \            # Process the webcam stream in near-realtime into FAST thoughts
    --jsonl  --output-frames | \
python -m src.raw.stream --roll-tape \  # Process FAST and SLOW thoughts into RAW thoughts and visualize them
    2> >(emit/websocket)                # Send the RAW thoughts back to the frontend client
```
This command runs the backend in the terminal and sends its output to the Javascript frontend via stderr. In the GIFs below you can see how the backend output (on the left) is rendered in the frontend (on the right) in realtime:
<p align="center">
  <div style="display: flex; justify-content: center;">
    <img width="48%" src="https://github.com/mvsoom/gedankenpolizei/blob/main/data/examples/backend.gif">
    <img width="48%" src="https://github.com/mvsoom/gedankenpolizei/blob/main/data/examples/frontend.gif">
  </div>
</p>

[^2]: See [`REDDIT.md`](./src/slow/reddit/REDDIT.md) for more details on how the SLOW stream is designed. Its job is to seed the RAW thoughts with overall thought themes and moods.

### Transforming and monitoring streams

You can choose an optional vision **input source** by running one of the programs in [`grab/`](./grab/); available input sources are webcam, screencast, movie files.

For example, I like to keep gedankenpolizei open in a monitor while it watches me code; its quirky thoughts give a sort of lightness to the moment or provide some creative distraction:
```bash
grab/screen | \
python -m src.fast.narrate --jsonl --output-frames | \
python -m src.raw.stream
```

You can choose the stream of consciousness **output source** by running one of the programs in [`emit/`](./emit/) to transform the output in a fancy way, but this is completely optional and just adds persona to the output. I like to use `cool-retro-term` for example:
```bash
python -m src.raw.stream | emit/retroterm
```
Combined with the previous command enabling it to see its own output, this gives a kind of HAL 9000 feeling (at least to me):
<p align="center">
  <img width="440" src="https://github.com/mvsoom/gedankenpolizei/blob/main/data/examples/retroterm.gif">
</p>

Finally, it is also possible to **monitor** the data streams by running one of the programs in [`monitor/`](./monitor/), for example to visualize the vision input stream:
```bash
monitor/log logs/src/fast/narrate.md
```

Note: the optional "addons" of this section require installing some additional programs:
```bash
mdcat  # https://github.com/swsnr/mdcat
lolcat
cool-retro-term
```

## Credits

- I want to thank Thalïa Viaene for unwavering support and love and Mathias Mu for artistic bro-support.
- Thanks to Google for providing an incredible LLM, generous credits and a stable API in terms of service and latency!
- Further special thanks go to [three.js](https://threejs.org/), [websocat](https://github.com/vi/websocat) and [mdcat](https://github.com/swsnr/mdcat) projects for being great solutions to problems I had; and of course all other open source projects used by this repo.