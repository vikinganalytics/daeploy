import pickle
from pathlib import Path

import numpy as np
from sklearn import datasets
from sklearn.neighbors import KNeighborsClassifier

np.random.seed(1000)
THIS_DIR = Path(__file__).parent

iris = datasets.load_iris(as_frame=True)

X_df = iris["data"]
y = iris["target"]

n = X_df.shape[0]
i_train = np.random.choice(n, round(0.7 * n))

y_train = y[i_train]
X_train = X_df.loc[i_train, :]

y_test = y.drop(i_train, axis=0)
X_test = X_df.drop(i_train, axis=0)

knn = KNeighborsClassifier()
knn.fit(X_train, y_train)

with open(THIS_DIR / "classifier.pkl", "wb+") as fp:
    pickle.dump(knn, fp)
