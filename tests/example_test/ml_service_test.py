import json
import shutil

import examples.ml_model_serving.iris_project.service as iris_service
import examples.ml_model_serving.train_model as train_model
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

app = iris_service.service.app
client = TestClient(app)

shutil.copy(
    train_model.THIS_DIR / "classifier.pkl",
    train_model.THIS_DIR / "iris_project" / "models" / "classifier.pkl",
)

n = 3
test_data = {"col1": n * [1], "col2": n * [2], "col3": n * [3], "col4": n * [4]}
test_prediction = n * [1]


def test_predict_api():
    response = client.post("/predict", data=json.dumps({"data": test_data}))
    assert response.status_code == 200
    assert response.json() == test_prediction


def test_predict_local():
    test_df = pd.DataFrame(test_data)
    pred = iris_service.predict(test_df)
    assert all(pred == test_prediction)
    assert isinstance(pred, np.ndarray)
