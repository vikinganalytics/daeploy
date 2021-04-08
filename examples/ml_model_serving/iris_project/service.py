import logging
import pickle
from pathlib import Path

from daeploy import service
from daeploy.data_types import ArrayOutput, DataFrameInput

logger = logging.getLogger(__name__)
THIS_DIR = Path(__file__).parent

with open(THIS_DIR / "models/classifier.pkl", "rb") as fp:
    CLASSIFIER = pickle.load(fp)


@service.entrypoint
def predict(data: DataFrameInput) -> ArrayOutput:
    logger.info(f"Recieved data: \n{data}")
    pred = CLASSIFIER.predict(data)
    logger.info(f"Predicted: {pred}")
    return pred


if __name__ == "__main__":
    service.run()
