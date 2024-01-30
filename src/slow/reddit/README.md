# Training an LLM on reddit data

## Datasets

- [x] [1m confessions](https://www.kaggle.com/datasets/pavellexyr/one-million-reddit-confessions/data): Looks good, downloaded zip file
- [x] [convokit-reddit](https://convokit.cornell.edu/documentation/subreddit.html): Looks good, downloadable via Python API
- [?] [tf-reddit](https://www.tensorflow.org/datasets/catalog/reddit): Could be good; untested
- [/] [reddit self-post](https://www.kaggle.com/datasets/mswarbrickjones/reddit-selfposts): Bad choice of subreddits for our purposes ... but good notebooks on Kaggle
- [/] [reddit 2014 graph](https://paperswithcode.com/dataset/reddit): Unusuable
- [/] [webis/tldr-17](https://huggingface.co/datasets/webis/tldr-17): Bad choice of subreddits for our purposes ... but good for summarization (metathoughts)
- [?] [Reddit comments/submissions 2005-06 to 2023-12](https://academictorrents.com/details/9c263fc85366c1ef8f5bb9da0203f4c8c8db75f4): Full scrape, 2 TB.
  - [More of these](https://academictorrents.com/browse.php?search=stuck_in_the_matrix)
  - [API service to query this data](https://www.pullpush.io/): Very good but site is unstable

## Good subreddits...

... are those containing posts with a stream-of-consciousness (SOC) feel.

Good starting point is 
- [x] https://www.reddit.com/r/letters/

From there, see related subreddits of r/letters at https://anvaka.github.io/map-of-reddit/?x=23033.519670875172&y=19494.765659988872&z=50&v=2&q=letters:

- https://www.reddit.com/r/LoveLetters/
- https://www.reddit.com/r/unsent/
- [x] https://www.reddit.com/r/Diary/ => very good
- [ ] https://www.reddit.com/r/LibraryofBabel/ => funky, tasteful noise
- https://www.reddit.com/r/ShrugLifeSyndicate/ => weird noise

Other gems:

- [ ] https://www.reddit.com/r/venting/
- [x] https://www.reddit.com/r/self/

python scrape.py Life subreddit/Life.csv --maxfsize 10 --verbose

## Vetting

Mark as negative => more signal

Possible improvements to filter on (to remove or replace by ellipsis):
- Names (Christine, Paul)
- "post", "repost", "front page" (the literal word), "account"
- "comment"
- "title"
- "mom", "dad"
- "moderator", "mods"
- "edit:"
- "(17f), (50M)" etc.
- "20yo" etc.
- "I'm 19" etc.
- "Discord", "4chan"
- "hello everyone", "you guys"
- "spencer"
- "school", "college", "undergrad"
- "years old"

Or just mark as negative (-1) examples

Replace \s+ by ...? (if repeated whitespace)
Many paragraphs don't end with punctuation (the poems etc)

## Filtering pipeline

We can rank these posts by embedding them and dotting them with embeddings of exemplary SOCs.

Posts are naturally structured in <thought>...</thought> and good length.

Other filtering:
- Exclude mentions of "Reddit", "OP"
- Excluding links
- Excluding mentions of the years or date
- deMarkdown: \[ etc
- See: https://www.kaggle.com/code/fazilbtopal/nlp-data-preprocessing#Cleaning-Text-Data


And perhaps encourage parentheses if we go for that scheme

We can use the post titles as seed/summaries/...! In the training data we could for example use them as metathoughts

## Sentenze tokenization

For training we can do sentence tokenization using spaCy as in below, with sentence separator |:

```
I just finished the Fountainhead by Ayn Rand.|Highly recommend.|It
 speaks of the collectivist mindset and it's flaws shown throughout hi
story.|Our natural disposition is to be selfish, so if the ideal of 
selflessness is held as the highest moral virtue, humans will naturall
y think of themselves as unclean/unworthy/etc.|Helping out the colle
ctive is undoubtedly a virtue, but it's a slippery slope down the path
 of losing oneself. ...
```

This way the program outputs delineated sentences, and we dont print out the | symbols

## Sequence classification

into good and bad posts:

https://medium.com/@lukas.hauzenberger/multilabel-classification-using-mistral-7b-on-a-single-gpu-with-quantization-and-lora-8f848b5237f3

can we reuse mistral 7b then? -- yes, it seems so: the classificaton (linear) layer is added after the last layer before converting to a prob distribution over next token. in this way we can use the negative posts when finetuning further to predict SOCs: a good initial guess for further LoRA training

https://stackoverflow.com/questions/69907682/what-are-differences-between-automodelforsequenceclassification-vs-automodel

![Alt text](assets/automodel.png)

Concatenate posts by the same author sorted by date to get longer training sequences!

## Other

Create character personalities
- by grouping semantically similar reddit posts such as happy, narcicistix, etc, and training on thay

Memories
- fresh seeding from RAG in our reddit db, so finding semanticallt similar thoughts to the current ones (in current soc)
- get interesting thought seeds from https://www.kaggle.com/datasets/a24998667/reddit-showerthoughts-corpus

Camera-like posts
- finding posts by vector search for "I see" etc

Post lenths
- posts are already structured as single thoughts! And have good lengths. And have meta title
- are good building blocks

Comments
- could be good meta thoughts too

Leapfrog idea:
-  go from title to content to title to content ... where the content contains camera descriptions and only title predictions are shown (short thoughts) ... and the predicted content given title then serves as a "lower level metathought" which seeds the next "surface thought"

## Detection of movement

- with simple energy measure and mfbod (mckay basian online detection)
- if burst of movement, then inject description

## Ideas

Rewrite posts using an LLM; could also be good for copyright

https://kaitchup.substack.com/p/phi-2-a-small-model-easy-to-fine

contrastive learning

Semi-supervised learning: A small amount of data that is correctly labeled data is used with large unlabeled data. The model makes predictions on the unlabeled data and where it is very sure, those samples are added to the next iteration of model training. It’s an iterative process in which models keep getting better with more and more trained data

Triple loss

https://huggingface.co/blog/Andyrasika/finetune-unsloth-qlora


## Integrating stream in 3D
Piping ffmpeg into the 3D engine is not directly possible in unreal or unity it seems

But we can hack it by having ffmpeg pipe the output as if it is a webcam

https://superuser.com/questions/411897/using-desktop-as-fake-webcam-on-linux

Then:

https://docs.unrealengine.com/4.27/en-US/WorkingWithMedia/IntegratingMedia/MediaFramework/HowTo/UsingWebCams/

https://docs.unity3d.com/ScriptReference/WebCamTexture.html

or better to use webgl:

https://medium.com/docler-engineering/webgl-video-manipulation-8d0892b565b6


## Resources

- https://www.reddit.com/r/LocalLLaMA/comments/17j1zcw/best_way_to_finetune_llm_based_on_daily_journals/
- https://www.reddit.com/r/LocalLLaMA/comments/190xnij/can_a_rag_in_conjunction_with_an_llm_create_a/

## Other random ideas

- Generate ASCII art to represent images?