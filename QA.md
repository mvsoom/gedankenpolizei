# QA

## Why `gedankenpolizei`?

Explore more realistic thoguhts

[Content From proposals here]

Exploring high-temperature regime of LLMs, often the thing we want to avoid

This is an artistic research to question to which extent LLMs can model our thoughts, and how it feels to read the thoughts of another "being", and does it make us judgy? Are we the thought police?

## How much does it cost?

TODO

## How did you make this?

Trial-and-error, heuristics and also some more principled ideas, such as random walks in embedded space. Credit where credit is due, I was pleasantly surprised at Gemini's usefulness and companionship during this research.

To make `gedankenpolizei` possible, debug-able and operatable, I designed some components which some may find innovative or helpful for their own artistic LLM research.

- The concept of three levels of semantic information: SLOW, FAST, NOW; each moving at different speeds in embedded space.
- A module for Reddit scraping and vetting tools which are reusable and robust. Used for SLOW.
- Nearly-realtime vision using subsecond video captioning in conjunction with an aggregation pipeline. Used for FAST.
- Realtime streaming of coherent thought-like text given the SLOW and FAST thought streams. Used for NOW.
- A module for Markdown logging which can be monitored live with `mdcat`. Handy for debugging and logging apps that process images.

More information can be found in other Markdown files in this repo.

## Why the single HTML file?

This was done as convenience to sidestep CORS issues during local development. Also, as I don't know anything about front-end web development or `three.js`, it was heavily co-written with AI, and a single file is convenient for that.

## Why is the SLOW database gated?

Downloading the SLOW database requires setting `HF_TOKEN_READ` in the `.env` file. This prevents legal issues with Redit content redistribution and reduces possibility of abuse. More on this in `REDDIT.md`.

## What can it do more?

Everthing is modular and primarily works with pipes, so you can fiddle around. For example:

- Let the AI see your desktop, a video, basically any video `ffmpeg` MJPEG stream instead of the webcam. Just pipe it into the program.
- Visualize output by piping the output to a backend: fancy `three.js` visuals, beautiful `cool-retro-term` nostalgia, or pipe into `lolcat` for lolz. Or just barebone print to stdout.

## Who are you?

I'm a PhD student in Bayesian machine learning who is struggling with their thesis and got distracted by Transformer architecture/LLMs.

Also a student of mindfulness, I naturally wondered if we can simulate our own inner monologue with LLMs in such a way that the richness/blandness/beauty/madness of our train of thought could be felt. It's a kind of NPC "sculpture" that could be an entity that mirrors its thoughts back to us. Maybe it can even be a friend sometimes.