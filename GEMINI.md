# Gemini

Workbench: https://aistudio.google.com/

Pricing: https://ai.google.dev/pricing
Regions: https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations

## PROBLEMS:

- Speed
  Slow speed: ~1.5 sec for a single Flash request
  Likely linked to free trial and very low RPM quotum (1 per minute)
  But can't upgrade as they don't accept prepaid cards

- Censoring
  Can ask for whitelist (monthly billing only for large companies) here: https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/configure-safety-attributes#safety_attribute_definitions

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