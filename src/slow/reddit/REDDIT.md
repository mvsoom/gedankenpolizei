# Notes for `reddit` module

## Getting and processing raw posts from Reddit

The SLOW stream provides seeding thoughts for the NOW stream. We get these seeding thoughts from scraping appropriate subreddits. These are listed in `data/reddit/subreddit.list`.

The raw posts also **normalized** to be easier to handle: removing empty posts, providing unique ids, etc. They are also sentencised with NLP to subdivide them into atoms of thought.

The raw posts are then **labeled** using heuristic regex patterns and NER into categories defined in `patterns.py`. If a post contains one or more labels, it is unlikely to be a good seed thought as it is eg. too personal or too obvious a Reddit post or just containing links, etc.

Finally, the posts are **embedded** into semantic embedding space.

This pipeline can be activated by running
```bash
scripts/scrape.sh
```
This takes ~1 day and yields about 1.3m raw posts, of which roughly 350k are unlabeled and are thus candidates for good seed thoughts.

> *Note about legal issues.*
> Scraping public data isn’t in violation of the US Computer Fraud and Abuse Act. Academic research is allowed, which is how this code is framed, but redistributing scraped content is sketchy. Note that the `scrape.py` script does not use the Reddit API. All posts are anonymized and NER is used to ignore posts that could contain further personal information. In fact the whole goal of the processing pipeline is to amass seed thoughts that express any kind of human thought that is not specific human-identifying but rather a general "atom of thought".
> Nevertheless, the raw data is not redistributed. The final product (see below) *is* redistributed (to make the app work), but encrypted with a key that makes sure only selected people can run the app. A  better way would be the shield the final product behind an API, such that there is control over the access keys, but this is future work.
> Finally, note that the final NOW output does not echo these scraped posts; it rather builds upon them and transforms them into new thoughts. It is also not used directly to train new LLMs.

## Vetting posts manually

The 350k candidates are then vetted (ie. quality-controlled) through a manual process to get a feel for the seed quality. This is quite an instructive, though severely depressing, passtime. You can initiate it by
```bash
python -m src.slow.reddit.vet data/reddit/posts.feather data/reddit/vet.feather
```
This presents posts which you can upvote (GOOD seed thought) or downvote (BAD seed thought). You effectively start walking in the embedding space, finding nearby related posts if current post if GOOD, or teleporting if current post is BAD.

More vetting options are availably thru `python -m src.slow.reddit.vet -h`.

In this way 9k manually vetted posts were obtained, of which roughly 25% were deemed GOOD. This is the validation testset for the next step.

## Vetting posts automatically

Manually vetting (350k posts ~ 40m tokens) would likely lead to nihilistic depression.
So we use Gemini Flash to do this automatically:
```bash
python -m src.slow.reddit.vet data/reddit/posts.feather data/reddit/autovet.feather --autovet
```
This yields ... [TODO]
Confusion matrix on test set:

we err on the cautious side! This also functions as an additional toxicity filter.
Only TODO were rejected by Gemini as `PROHIBITED_CONTENT`. Note that I used Gemini Flash 1.5 with 'disabled' safety settings.






Cost: TODO




> *Note about prompting:* I was horrified to learn that few-shot prompting only gave marginal improvements to zero-shot prompting. The original idea for manual vetting was, of course, a test set for validation, but also to use as semantically related examples for autovetting the current post. Turned out that this was unnecessary: ~1% classification improvement at roughly 3x the cost. So don't waste time manually vetting 9k posts. A couple of 100 should do the trick.
> Nevertheless, if you want to use few-shot prompting, use the `--reference` switch of `vet.py`

## Final product: the SLOW seeding thoughts

The final step is to collect everything in a single .feather database and encrypt it to ensure legal compliance and restrict possible abuse.
```bash
python TODO slow.feather.encrypted TODO
```

To recap, `slow.feather.encrypted` contains .........TODO....... GOOD posts that have been labeled automatically by zero-shot prompting Gemini. The embeddings of these posts measure out the SLOW embedded space in which the AI can muse. Think of them as moods or larger thought themes, in contrast to our "quick" thoughts happening in the moment, which might be said to be conditioned on these thought themes, and on our current sensorial input (the FAST stream in our model).