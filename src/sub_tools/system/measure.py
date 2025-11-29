import time
from contextlib import contextmanager


@contextmanager
def measure():
    """
    Measures the time taken for a block of code to execute.
    """
    start_time = time.time()
    try:
        yield
    finally:
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Elapsed time: {elapsed_time:.6f} seconds")
