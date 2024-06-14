# Gemini

Workbench: https://aistudio.google.com/

Pricing: https://ai.google.dev/pricing
Regions: https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations

## PROBLEMS:

- Speed
  Very slow speed: ~2.5 sec for a single Haiku request
  Likely linked to free trial and very low RPM quotum (1 per minute)
  But can't upgrade as they don't accept prepaid cards

- No prefill
  There is no prefill for the thoughts.stream module
  However prefills are done within user prompt and called "prefixes"

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

## Contest

https://ai.google.dev/competition

Deadline: 12 Aug 2024
