from datetime import datetime


def write_log(prefix: str, *args, directory: str = ".") -> None:
    """
    Writes a log file with the current timestamp and the provided arguments.
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    with open(f"{directory}/{prefix}_{timestamp}.log", "w") as file:
        for arg in args:
            file.write(str(arg))
            file.write("\n")
