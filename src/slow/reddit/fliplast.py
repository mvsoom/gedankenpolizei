import pandas as pd

df = pd.read_hdf('vet.h5')

df.iloc[-1, -2] = -df.iloc[-1, -2]
print("DONE:", df.iloc[-1]["normalized"])
print("NEW SCORE:", df.iloc[-1]["score"])

df.to_hdf("vet.h5", key="df")