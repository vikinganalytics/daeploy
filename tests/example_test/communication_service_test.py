import examples.cross_service_communication.die_roller_service.service as die_roller
import examples.cross_service_communication.yatzee_service.service as yatzee
from daeploy.testing import patch


def test_roll_die():
    assert die_roller.roll_die() in range(1, 7)


def test_yatzee():
    with patch(
        "examples.cross_service_communication.yatzee_service.service.call_service"
    ) as call_service:
        call_service.return_value = 4
        print(yatzee.play())
        call_service.assert_called()
