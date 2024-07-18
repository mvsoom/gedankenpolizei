# Instructions for jury

## Installation instructions:

1. Python environment:
  * Clone repo
  * Create Python >= 3.10.12 `.venv`
  * `pip -r install requirements.txt`
2. Tokens
  * Create an .env file with contents:
    ```
    HF_TOKEN_READ=xxx
    PROJECT_ID=yyy
    ```
    where `xxx` and `yyy` are the given Hugging Face token and Google Cloud credentials.
3. Additional programs for running `./client`
  * `ffmpeg`
  * `websocat` (make sure this is in PATH)

Optional programs to install additionally are:
```
mdcat
cool-retro-term
lolcat
```

## Running the client

TODO

## Additional information

I used Python 3.10.12 with Ubuntu 22.04.4 LTS on a HP EliteBook 850 G5. For the LLM I used Gemini Flash 1.5 with safety turned off and maxed out RPM at 1000.