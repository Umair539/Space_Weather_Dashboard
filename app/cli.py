import sys
from streamlit.web import cli


def launch_app():

    # Use the relative path directly
    app_file_path = "app/run_app.py"

    # Modify sys.argv to execute 'streamlit run scripts/run_app.py'
    sys.argv = ["streamlit", "run", app_file_path] + sys.argv[1:]

    # Launch Streamlit
    cli.main()
