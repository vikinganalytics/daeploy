from pathlib import Path

# Change import if you have changed name of service.py
import service as app

# Read service source file
SERVICE_DIR = Path(__file__).parent.parent
service_path = (SERVICE_DIR / app.__name__).with_suffix(".py")
with service_path.open("r") as file_handle:
    service_code = file_handle.read()


def test_service_run():
    run_statement = "service.run()"
    run_row = ""

    for item in service_code.split("\n"):
        if run_statement in item:
            run_row = item

    assert (
        run_statement in run_row
    ), f"For the service to run, the service code must end with {run_statement}"

    run = run_row.find(run_statement)
    comment = run_row.find("#")
    assert comment == -1 or comment > run, f"{run_statement} commented out"
