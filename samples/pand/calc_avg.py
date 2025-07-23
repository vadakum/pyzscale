

import pandas as pd
from collections import deque

span = 10
qdata = deque([10, 12, 15, 18, 20, 10, 9, 9, 7, 9], maxlen=span)
last_point = qdata[-1]
print(list(qdata)[1:])

df = pd.DataFrame({'data' : qdata})
df['ewm1'] = df['data'].ewm(span=span, adjust=False).mean()
df['ewm2'] = df['ewm1'].ewm(span=span, adjust=False).mean()
df['ewm3'] = df['ewm2'].ewm(span=span, adjust=False).mean()
df['tema'] = (3 * df['ewm1']) - (3 * df['ewm2']) + df['ewm3']

ewm1 = float(df['ewm1'].iloc[-1])
ewm2 = float(df['ewm2'].iloc[-1])
ewm3 = float(df['ewm2'].iloc[-1])
tema = (3 * ewm1) - (3 * ewm2) + ewm3

print(df)
print("MEAN:", df['data'].mean())
print("TEMA:", df['tema'].iloc[-1])

if  last_point > tema:
    print("Going up")
elif last_point < tema:
    print("Going down")



