import sys
import subprocess


def main():
    command = sys.argv[1]

    # Define test directories and corresponding coverage targets
    test_config = {
        "unit": {"dir": "tests/unit_tests", "cov": ["src/transform"]},
        "component": {
            "dir": "tests/component_tests/transform",
            "cov": ["src/transform"],
        },
        "integration": {
            "dir": "tests/integration_tests",
            "cov": ["src/transform", "src/extract"],
        },
        "all": {"dir": "tests", "cov": ["src/transform"]},
    }

    # Check to see if a command was supplied for the test run
    if command in test_config:
        # Access the test_config dictionary to get the test directory
        # and coverage targets
        test_dir = test_config[command]["dir"]
        cov_sources = ",".join(test_config[command]["cov"])

        # Build the test command for tests with coverage
        if cov_sources:
            cov_command = (
                f"coverage run --source={cov_sources} "
                f"-m pytest --verbose {test_dir} "
                "&& coverage report -m && coverage html "
                "&& coverage report --fail-under=90"
            )
        else:
            cov_command = f"pytest --verbose {test_dir}"

        subprocess.run(cov_command, shell=True)
    elif command == "lint":
        run_lint()
    else:
        raise ValueError(f"Unknown command: {command}")


def run_lint() -> None:
    print("Linting Python...")
    subprocess.run(["flake8", "."])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise ValueError("Usage: run_tests.py <unit>")
    else:
        main()
