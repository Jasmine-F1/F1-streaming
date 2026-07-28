from .config import parse_args
from .replay import run


def main() -> None:
    config = parse_args()
    run(config)


if __name__ == "__main__":
    main()
