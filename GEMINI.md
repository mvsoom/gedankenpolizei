# Gemini

Workbench: https://aistudio.google.com/

Pricing: https://ai.google.dev/pricing
Regions: https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations

## PROBLEMS:

- No prefill
  There is no prefill for the thoughts.stream module
  However prefills are done within user prompt and called "prefixes"

- No stop words

## Images

https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/send-multimodal-prompts#image-requirements

> There isn't a specific limit to the number of pixels in an image. However, larger images are scaled down and padded to fit a maximum resolution of 3072 x 3072 while preserving their original aspect ratio.

> If both dimensions of an image's aspect ratio are less than or equal to 384, then 258 tokens are used.
> If one dimension of an image's aspect ratio is greater than 384, then the image is cropped into tiles. Each tile size defaults to the smallest dimension (width or height) divided by 1.5. If necessary, each tile is adjusted so that it's not smaller than 256 and not greater than 768. Each tile is then resized to 768x768 and uses 258 tokens.

> The maximum number of images that can be in a prompt request is:

16 for Gemini 1.0 Pro Vision
3,000 for Gemini 1.5 Flash and Gemini 1.5 Pro

Up to 3600 images

> No specific limits to the number of pixels in an image; however, larger images are scaled down to fit a maximum resolution of 3072 x 3072 while preserving their original aspect ratio.

## Gemma and other models

### [PaliGemma: single turn image/video model](https://github.com/google-research/big_vision/tree/main/big_vision/configs/proj/paligemma)

!!!
RUN IN REALTIME ON VIDEO: need to check this: https://github.com/sumo43/loopvlm

He got it working at 16 fps (10 tokens) on the 224x224 on a RTX 4090: https://x.com/sumo43_/status/1791589684121903555
!!!

[Can be deployed on Google vertex](https://console.cloud.google.com/vertex-ai/publishers/google/model-garden/363?project=gen-lang-client-0149736153)

[Supports video captioning](https://github.com/google-research/big_vision/issues/117)
- Video support here: https://github.com/google-research/big_vision/blob/01edb81a4716f93a48be43b3a4af14e29cdb3a7f/big_vision/models/proj/paligemma/paligemma.py#L74
- Input shape is (num_frames, res, res, 3), where res = 224, 448, see https://github.com/google-research/big_vision/blob/01edb81a4716f93a48be43b3a4af14e29cdb3a7f/big_vision/configs/proj/paligemma/transfers/activitynet_cap.py#L47
- What is the prompt? For ActivyNet captioning it is "caption en", see https://github.com/google-research/big_vision/blob/01edb81a4716f93a48be43b3a4af14e29cdb3a7f/big_vision/configs/proj/paligemma/transfers/activitynet_cap.py#L49. Same for MSR-VTT and VATEX (the other [video captioning tasks](https://github.com/google-research/big_vision/tree/main/big_vision/configs/proj/paligemma#video-tasks-captionqa))
- Video tasks have only been evaluated at 224 resolution (see previous link [video captioning tasks])
- Captioning datasets flairs:
  * MSR-VTT: "A black and white horse runs around." Single sentences, very short
  * ActivityNet: "Walking the dog": just simple activities it seems
  * VATEX: "People are crossing the street and cars are turning at a busy intersection in a business district." Single sentences, a bit less concise than MSR-VTT
- Training frames per second is 1 fps: num_frames=16, stride=30, res=224. Stride = 30 at input video fps of 30 means 1 fps. See https://github.com/google-research/big_vision/blob/01edb81a4716f93a48be43b3a4af14e29cdb3a7f/big_vision/configs/proj/paligemma/transfers/activitynet_cap.py#L140

Might be possible for very fast captioning, should test on brev.dev

Notebooks (check all of them!):
- https://colab.research.google.com/drive/1CfXWtq-1l20jJqSKzWoSWrzIoRIOuwWP
- https://github.com/google-gemini/gemma-cookbook/blob/main/PaliGemma/Image_captioning_using_PaliGemma.ipynb
- https://colab.research.google.com/drive/1aJil6wmaef_EZ-eCS8T4WuqD2AiFNHkv?usp=sharing#scrollTo=25BV1ljHM7Wy

Available commands from last notebook:
"cap {lang}\n": very raw short caption (from WebLI-alt).
"caption {lang}\n": nice, coco-like short captions.
"describe {lang}\n": somewhat longer more descriptive captions.
"ocr\n": optical character recognition.
"answer en {question}\n": question answering about the image contents.
"question {lang} {answer}\n": question generation for a given answer.
"detect {thing} ; {thing}\n": count objects in a scene.

- 4 bit quantization of 3b model needs less than 3 GB VRAM
- bflat16 needs 6 GB VRAM
- 896x896 variant only pretrained available, not as mix of finetuned tasks (such as paligemma-3b-mix-224)

### [RecurrentGemma](https://github.com/google-deepmind/recurrentgemma)

Can handle very long states in O(1) time due to RNN architecture. Could be interesting for end-to-end training.

## Contest

https://ai.google.dev/competition

Deadline: 12 Aug 2024

### Requirements

- Public Youtube video
- Testing instructions for judges
- App description and tagline

### Evaluation
JUDGING ROUND
Sponsor will evaluate each Entrant and their Submission. Your Submission, including Your video and code will be evaluated based on following judging criteria (the “Judging Criteria”), weighted equally:

Submissions will be evaluated by Google judges who excel in the following five (5) categories as they relate to this challenge: impact, remarkability, creativity, usefulness, and execution. Each criteria will be scored on a scale of 1 (strongly disagree) to 5 (strongly agree). The judging criteria is as follows:

Category 1: Impact
Is the solution easy and enjoyable to use for everyone, including people with disabilities? (maximum 5 points)
Does this solution have potential to contribute meaningfully to environmental sustainability?(maximum 5 points)
Does this solution have potential to contribute meaningfully to improving people's lives? (maximum 5 points)

Category 2: Remarkability
Is the submission surprising to those that are well-versed in Large Language Models (“LLM”)? (maximum 5 points)
Is the submission surprising to those that are not well-versed in LLM? (maximum 5 points)

Category 3: Creativity
Does the submission differ from existing, well known, applications in functionality? (maximum 5 points)
Does the submission differ from existing, well known, applications in user experience? (maximum 5 points)
Is the submission implemented through the use of creative problem-solving approaches? (maximum 5 points)

Category 4: Usefulness
Does the submission include a well-defined target user persona/segmentation? (maximum 5 points)
Does the submission identify how the solution addresses specific user needs? (maximum 5 points)
How well does the solution, as implemented, help users meet these needs? (maximum 5 points)

Category 5: Execution
Is the solution well-designed and adhere to software engineering practices? (maximum 5 points)
Is the LLM component of the solution well-designed and adhere to Machine Learning (ML)/LLM best practices? (maximum 5 points)

Maximum score: 65
In the event of a tie(s), Sponsor will rejudge the Submissions for overall video impact to determine the applicable winner. Sponsor’s decisions are final and binding.