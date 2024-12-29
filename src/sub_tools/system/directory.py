import os


def change_directory(directory):
    os.makedirs(directory, exist_ok=True)
    os.chdir(directory)
