import pytest

from manager.data_models.request_models import BaseNewServiceRequest


def test_ServiceRequest_name_validator_invalid_names():
    with pytest.raises(ValueError):
        BaseNewServiceRequest(name="My Model", version="0.0.1", port=80)

    with pytest.raises(ValueError):
        BaseNewServiceRequest(name="My.Model", version="0.0.1", port=80)

    with pytest.raises(ValueError):
        BaseNewServiceRequest(name="My-Model", version="0.0.1", port=80)

    with pytest.raises(ValueError):
        BaseNewServiceRequest(name="MYMODEL", version="0.0.1", port=80)

    with pytest.raises(ValueError):
        BaseNewServiceRequest(name="my/service", version="0.0.1", port=80)

    with pytest.raises(ValueError):
        BaseNewServiceRequest(name="", version="0.0.1", port=80)

    with pytest.raises(ValueError):
        BaseNewServiceRequest(name="//////", version="0.0.1", port=80)

    with pytest.raises(ValueError):
        BaseNewServiceRequest(name="service_", version="0.0.1", port=80)

    with pytest.raises(ValueError):
        BaseNewServiceRequest(name="_service", version="0.0.1", port=80)

    with pytest.raises(ValueError):
        BaseNewServiceRequest(name="_service_", version="0.0.1", port=80)


def test_ServiceRequest_name_validator_valid_names():
    BaseNewServiceRequest(name="model", version="0.0.1", port=80)
    BaseNewServiceRequest(name="my_model", version="0.0.1", port=80)
    BaseNewServiceRequest(name="my_model_123", version="0.0.1", port=80)
