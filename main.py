import argparse
from src.cli import run_cli
from src.scheduler import run_pending_jobs


def main():
    parser = argparse.ArgumentParser(description="Flight Price Monitor")
    parser.add_argument(
        "--run-jobs",
        action="store_true",
        help="Executa os jobs de monitoramento pendentes e sai (para uso com cron)",
    )
    args = parser.parse_args()

    if args.run_jobs:
        run_pending_jobs()
    else:
        run_cli()


if __name__ == "__main__":
    main()
