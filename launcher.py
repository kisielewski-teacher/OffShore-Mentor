import os
import sys

# Small launcher that starts the bundled Streamlit app.
# It locates `streamlit_app.py` next to the executable (or in _MEIPASS for onefile bundles)
# and invokes Streamlit's CLI programmatically.

def main():
    try:
        # When bundled by PyInstaller, resources are extracted to _MEIPASS
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.argv[0])))
    except Exception:
        base_dir = os.getcwd()

    app_path = os.path.join(base_dir, "streamlit_app.py")
    if not os.path.exists(app_path):
        # fallback to current working dir
        app_path = os.path.join(os.getcwd(), "streamlit_app.py")

    # Prepare argv for Streamlit CLI
    sys.argv = ["streamlit", "run", app_path, "--server.headless", "true"]

    try:
        # Import Streamlit CLI and run
        from streamlit.web import cli as stcli
        sys.exit(stcli.main())
    except Exception:
        # Older Streamlit versions may expose a different CLI entrypoint
        try:
            # As a last resort, attempt to run via subprocess
            import subprocess
            subprocess.check_call([sys.executable, "-m", "streamlit", "run", app_path])
        except Exception as exc:
            print("Failed to launch Streamlit app:", exc)
            raise

if __name__ == "__main__":
    main()
