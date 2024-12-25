from sub_tools.arguments.parser import setup_arg_parser


def main() -> None:
    parser = setup_arg_parser()
    parser.print_help()
