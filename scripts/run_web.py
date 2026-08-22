"""Runs the API and the Vite dev server together for local development.

Equivalent to running `run_api` and `npm run dev` in two terminals - this
just saves doing that by hand, and with --expose, points the frontend at
the right LAN address automatically instead of leaving it on localhost.
"""

import argparse
import os
import socket
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(PROJECT_ROOT, "web")
WEB_PORT = 5173  # fixed in web/vite.config.ts


def _lan_ip() -> str:
    """Best-effort LAN IP: connects a UDP socket to a public address (no
    packet is actually sent) purely so the OS reports which local interface
    it would route through - that's this machine's real LAN IP, as opposed
    to the loopback address `socket.gethostname()` can resolve to."""
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]


def run_web() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", choices=["dev", "prod"], default="dev")
    parser.add_argument("--api-port", type=int, default=8000)
    # Binds both servers to all interfaces and points the frontend at this
    # machine's LAN IP, so another device on the same network can load it.
    parser.add_argument("--expose", action="store_true")
    args = parser.parse_args()

    api_cmd = ["run_api", "--env", args.env, "--port", str(args.api_port)]
    npm = "npm.cmd" if os.name == "nt" else "npm"
    web_cmd = [npm, "run", "dev"]
    env = os.environ.copy()

    if args.expose:
        ip = _lan_ip()
        api_cmd.append("--expose")
        web_cmd += ["--", "--host"]
        env["VITE_API_BASE_URL"] = f"http://{ip}:{args.api_port}"
        print(f"Exposed - open http://{ip}:{WEB_PORT} on another device on this network")

    # cwd pinned explicitly - run_api's load_dotenv(".env.dev") is a relative
    # path, and would otherwise silently find nothing (no error, just an
    # unset DATABASE_READ_URL) if run_web was launched from anywhere else,
    # e.g. from inside web/.
    api_proc = subprocess.Popen(api_cmd, cwd=PROJECT_ROOT)
    try:
        subprocess.run(web_cmd, cwd=WEB_DIR, env=env)
    except KeyboardInterrupt:
        pass
    finally:
        api_proc.terminate()
        api_proc.wait()


if __name__ == "__main__":
    sys.exit(run_web())
