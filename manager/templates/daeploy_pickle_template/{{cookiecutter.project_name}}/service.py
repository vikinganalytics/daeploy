import logging
import pickle
from pathlib import Path
from typing import List, Any

import pandas as pd

from daeploy import service

THIS_DIR = Path(__file__).parent

# Setup a logger
logger = logging.getLogger(__name__)

# Startup message for autogenerated service
with (THIS_DIR / "README.md").open("r") as file_handle:
    documentation = file_handle.read()
logger.info(documentation)

# Unpack the model
with open("./models/model.pkl", "rb") as fp:
    model = pickle.load(fp)


@service.entrypoint
def predict(data: dict) -> List[Any]:
    """Example data::

        {
        "data": {
            "col1": [0.0, 1.0],
            "col2": [0.0, 1.0],
            "col3": [0.0, 1.0],
            "col4": [0.0, 1.0]
            }
        }

    \f
    Args:
        data (dict): Input data. Should be convertable to a pandas dataframe.

    Returns:
        list: List of predictions
    """
    data_df = pd.DataFrame(data)
    logger.info(f"Recieved data: \n{data_df}")
    y_pred = model.predict(data_df)
    logger.info(f"Predicted: {y_pred}")
    return list(y_pred)


if __name__ == "__main__":
    service.run()
