# QA

## Why `gedankenpolizei`?

- Means "thought police" in German.
- Unleashing high-temperature LLMs. Probing their creative/artistic/more "human" side.
- Research into more relatable NPCs (non-playable characters) that are aware of what is happening around them in semi-real-time.
- This is an artistic research to question to which extent LLMs can model our raw thoughts, and how it feels to read the thoughts of another "being". What do we expect of it? Can we connect to it? We find ourselves literally in the role of thought police.
- Exploring a dystopian visualization of the thought police concept.

## How did you make this?

Trial-and-error, heuristics and also some more principled ideas, such as random walks in embedded space. Credit where credit is due, I was pleasantly surprised at Gemini's usefulness and companionship during this research.

To make `gedankenpolizei` possible, debug-able and operatable, I designed some components which some may find innovative or helpful for their own LLM research.

- The concept of three levels of semantic information: SLOW, FAST, RAW; each moving at different speeds in embedded space.
- A module for Reddit scraping and vetting tools which are reusable and robust. Used for SLOW.
- Nearly-realtime vision using subsecond video captioning in conjunction with an aggregation pipeline. Used for FAST.
- Realtime streaming of coherent thought-like text given the SLOW and FAST thought streams. Used for RAW.
- A module for Markdown logging which can be monitored live with [`mdcat`](https://github.com/swsnr/mdcat). Handy for debugging and logging apps that process images.

More information can be found in other Markdown files in this repo.

## Why the single HTML file?

This was done as convenience to sidestep CORS issues during local development. Also, as I don't know anything about front-end web development or [`three.js`](https://threejs.org/), it was heavily co-written with AI, and a single file is convenient for that.

## Do I have to use Google Chrome to view the frontend client?

No, I tested it with Chromium (126.0.6478.182) and it works. Also works with Firefox (tested 129.0.1) but the sound is off for some reason (it is generated live from pink noise).

## Why is the SLOW database gated?

Downloading the SLOW database requires setting `HF_TOKEN_READ` in the `.env` file. This prevents legal issues with Redit content redistribution and reduces possibility of abuse. More on this in [`REDDIT.md`](./src/slow/reddit/REDDIT.md).

## What can it do more?

Everthing is modular and primarily works with pipes, so you can fiddle around. For example:

- Let the AI see your desktop or a video instead of the webcam: any video `ffmpeg` MJPEG stream will do, just pipe it into the program from one of the scripts in `./grab`.
- Visualize output by piping the output to one of the backends in `./emit`: fancy `three.js` visuals, beautiful `cool-retro-term` nostalgia, or pipe into `lolcat` for lolz. Or just barebone print to stdout.

## Who are you?

I'm a PhD student in Bayesian machine learning who is struggling with their thesis and got distracted by Transformer architecture/LLMs.

Also a student of mindfulness, I naturally wondered if we can simulate our own inner monologue with LLMs in such a way that the richness/blandness/beauty/madness of our train of thought could be felt. It's a kind of NPC "sculpture" that could be an entity that mirrors its thoughts back to us. Maybe it can even be a friend sometimes.