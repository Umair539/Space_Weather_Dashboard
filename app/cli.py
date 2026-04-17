import argparse
import sys
from dotenv import load_dotenv
from streamlit.web import cli


def launch_app():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--env", choices=["dev", "prod"], required=True, help="Target environment"
    )
    args, remaining = parser.parse_known_args()
    load_dotenv(f".env.{args.env}", override=True)

    # Use the relative path directly
    app_file_path = "app/run_app.py"

    # Modify sys.argv to execute 'streamlit run scripts/run_app.py'
    sys.argv = ["streamlit", "run", app_file_path] + remaining

    # Launch Streamlit
    cli.main()


if __name__ == "__main__":
    launch_app()
