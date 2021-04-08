from daeploy import service
from daeploy.data_types import ArrayInput, ArrayOutput


@service.entrypoint
def array_sum(array1: ArrayInput, array2: ArrayInput) -> ArrayOutput:
    return array1 + array2


if __name__ == "__main__":
    service.run()
