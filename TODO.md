# SEER 1

## TODO

- Test src/slow/reddit: requirements, module recasting

- git LFS for slow.feather.encrypted

- yaml file and .env file

- Search for TODO everywhere

- Search for Claude and delete

- FAST.md

- SLOW.md

- update requirements.txt

- QA.md

- JURY.md

- GEMINI.md

- Make a README.md
  * animation of thought walks in embedding space

### General

- Overloaded errors: can and will happen (https://www.reddit.com/r/ClaudeAI/comments/1cdptpp/claude_api_is_not_ready_for_production_apps/) both in narrate and thoughts. Note Amazon Bedrock is same price as Anthropic API, but has European providers for Haiku and probably more stable: https://www.reddit.com/r/Anthropic/comments/1b8wawe/comment/ktxhztx/. Google Vertex AI seems more stable, and the Gemini models look good too, cheap prices. Video is 1 fps and is ~0.5$/hour. Also looks like prefill is supported.
- Using YAML for config (env) files and prompt files (with properties such as temperature, prefill, closure, etc.)
  * For this the https://pypi.org/project/yaml-config-override/ package is good
  * see `yaml` branch
- Maybe switch to ffmpegcv Python library if there is too much overhead in resizing/recasting images: it does this on ffmpeg side

### client

- seer_canvas.html vs seer_sprite.html:
  * Arial (is quite nearly monospaced, strangely) vs monospaced
  * 2D canvas vs sprite (sprite is supposed to be faster: a sprite is a 2D surface in a 3D scene, but not sure if we can add 3D effects on it)
- Looks like webcam size is still hardcoded, should change this
- Organize HTML code

### `seer.thoughts`

- Experiment with temperature

### `seer.narrate`

- Fix seer.narrate.frame, seriously
- Deal with RESPONSE_TIMEOUT and other API errors
- Set NARRATE_TILE_NUM_FRAMES higher. WARNING: turn off stop sequence "</narration>" to see if the model understands NARRATE_TILE_NUM_FRAMES > 1 -- otherwise it will describe each frame within the til
- Make a second log file that always records everything at the debug level