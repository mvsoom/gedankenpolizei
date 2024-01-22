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
- https://www.reddit.com/r/LibraryofBabel/ => funky, tasteful noise
- https://www.reddit.com/r/ShrugLifeSyndicate/ => weird noise

Other gems:

- https://www.reddit.com/r/venting/
- https://www.reddit.com/r/self/

## Filtering pipeline

We can rank these posts by embedding them and dotting them with embeddings of exemplary SOCs.

Posts are naturally structured in <thought>...</thought> and good length.

Other filtering:
- Exclude mentions of "Reddit", "OP"
- Excluding links
- Excluding mentions of the years or date
- See: https://www.kaggle.com/code/fazilbtopal/nlp-data-preprocessing#Cleaning-Text-Data

And perhaps encourage parentheses if we go for that scheme

We can use the post titles as seed/summaries/...! In the training data we could for example use them as metathoughts

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

## Resources

- https://www.reddit.com/r/LocalLLaMA/comments/17j1zcw/best_way_to_finetune_llm_based_on_daily_journals/
- https://www.reddit.com/r/LocalLLaMA/comments/190xnij/can_a_rag_in_conjunction_with_an_llm_create_a/