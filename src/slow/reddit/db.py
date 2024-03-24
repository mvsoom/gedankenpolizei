import pandas as pd

# Open the vet.h5 file
df = pd.read_hdf('/home/marnix/ART/CAMERA/code/reddit/vet.h5')

# Display the column names
print(df.columns)

# Count occurences in the score column
print(df['score'].value_counts())

# Print a random row with a score of "1" until user interrupts
while True:
    print(df[df['score'] == 1].sample(n=1).normalized.values[0])
    if input() == 'q':
            break

# Print a random row with a score of "1" until user interrupts
while True:
    print(df[df['score'] == -1].sample(n=1).normalized.values[0])
    if input() == 'q':
            break


import hashlib

# Create a new column with a hash of the row
def inthash(row):
    base16 = hashlib.md5(str(tuple(row)).encode('utf-8')).hexdigest()
    return int(base16, 16)

df["rowhash"] = df.apply(lambda x: inthash(x), axis = 1)

# Check if all rowhash are unique
print(df["rowhash"].is_unique)
# False

# Find duplicates
print(df[df.duplicated(subset="rowhash", keep=False)].sort_values(by="rowhash"))



# OK so cleaning stage
- normalization
- deduplicating
- hashing
- sorting (date)

# Then filtering
- nothing gets deleted, only marked
- assign badness score

# then manual vetting
- assign largest score to distinguish from filtering