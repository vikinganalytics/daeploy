import logging

# Lets import what we need from daeploy
from daeploy import service
from daeploy.communication import notify, Severity

# We need a logger. Logging is good.
# When this service is deployed, all logs will be reachable on the daeploy dashboard.
logger = logging.getLogger(__name__)

# The daeploy service stores parameters which are readable and changeable from outside
# the service, while it is running
service.add_parameter("greeting_phrase", "Hello")


# The '@service.entrypoint' decorater is used to make the function
# available via an API entrypoint. By using typed arguments in the
# function signature, you make sure that the function won't be reachable
# with wrong argument types. Convenient!
@service.entrypoint
def hello(name: str) -> str:
    # Let's get the latests greeting phrase.
    # It could have been changed to "Hola" or something else.
    greeting_phrase = service.get_parameter("greeting_phrase")
    # We want to get notified if someone is trying to greet the world.
    # Notifications shows up on the dashboard, there is also an option of receving
    # the notifications as emails, if wanted.
    if name == "World":
        notify(
            msg="Someone is trying to greet the World, too time consuming. Skipping!",
            severity=Severity.WARNING,
            emails=None,
        )
        return "Greeting failed"
    # Let's make sure that we log what we are doing!
    logger.info(f"Greeting someone with the name: {name}")
    return f"{greeting_phrase} {name}"


# Lastly, we need to make sure that our service runs when it is deployed.
# It is good practice to put this in a top-level script check according to
# below. This way, your service code is importable from other modules, for
# example for testing purposes.
if __name__ == "__main__":
    service.run()
