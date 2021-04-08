import logging
from daeploy import service
from daeploy.communication import notify, Severity, call_service

logger = logging.getLogger(__name__)


@service.entrypoint
def play() -> list:
    n_dice = 5
    die_rolls = []

    for _ in range(n_dice):
        die_roll = call_service(
            service_name="die_roller",
            entrypoint_name="roll_die",
        )
        die_rolls.append(die_roll)

    if sum(die_rolls) == 6 * n_dice:
        notify(
            msg="YATZEE!!!",
            severity=Severity.INFO,
        )

    return sorted(die_rolls)


if __name__ == "__main__":
    service.run()
