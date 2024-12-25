import argparse


def setup_arg_parser():
    parser = argparse.ArgumentParser(
        description="Download HLS video, convert to audio, transcribe and translate using Gemini API.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    return parser
