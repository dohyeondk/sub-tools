from datetime import datetime


def write_log(*args):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    with open(f"{timestamp}.log", "w") as file:
        for arg in args:
            file.write(str(arg))
            file.write("\n")
