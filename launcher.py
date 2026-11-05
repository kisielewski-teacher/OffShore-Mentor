import logging
import os
import sys
import traceback
from logging.handlers import RotatingFileHandler

# Small launcher that starts the bundled Streamlit app.
# It locates `streamlit_app.py` next to the executable (or in _MEIPASS for onefile bundles)
# and invokes Streamlit's CLI programmatically.
#
# The release build runs with console=False (no visible console window - see
# packaging/README_BUILD.md), so any startup failure here would otherwise be
# silent. Errors are logged to logs/launcher.log and, on Windows, also shown
# in a native message box so end users are never left without feedback.


def _base_dir() -> str:
    try:
        return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.argv[0])))
    except Exception:
        return os.getcwd()


def _setup_logger(base_dir: str) -> logging.Logger:
    logger = logging.getLogger("offshore_launcher")
    logger.setLevel(logging.DEBUG)
    if not logger.handlers:
        log_dir = os.path.join(base_dir, "logs")
        try:
            os.makedirs(log_dir, exist_ok=True)
            handler = RotatingFileHandler(
                os.path.join(log_dir, "launcher.log"),
                maxBytes=1_000_000,
                backupCount=2,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
            logger.addHandler(handler)
        except Exception:
            # Logging to disk failing must never stop the app from trying to start.
            pass
    return logger


def _show_error_dialog(title: str, message: str) -> None:
    if os.name != "nt":
        print(f"{title}: {message}")
        return
    try:
        import ctypes

        MB_ICONERROR = 0x10
        ctypes.windll.user32.MessageBoxW(None, message, title, MB_ICONERROR)
    except Exception:
        print(f"{title}: {message}")


def main() -> None:
    base_dir = _base_dir()
    logger = _setup_logger(base_dir)

    app_path = os.path.join(base_dir, "streamlit_app.py")
    if not os.path.exists(app_path):
        # fallback to current working dir
        app_path = os.path.join(os.getcwd(), "streamlit_app.py")

    logger.info("Starting OffShore Mentor, app_path=%s", app_path)

    # Prepare argv for Streamlit CLI
    sys.argv = ["streamlit", "run", app_path, "--server.headless", "true"]

    try:
        # Import Streamlit CLI and run
        from streamlit.web import cli as stcli

        sys.exit(stcli.main())
    except SystemExit:
        raise
    except Exception:
        logger.exception("Primary Streamlit CLI launch failed, trying subprocess fallback")
        try:
            # As a last resort, attempt to run via subprocess
            import subprocess

            subprocess.check_call([sys.executable, "-m", "streamlit", "run", app_path])
        except Exception:
            logger.exception("Failed to launch Streamlit app")
            _show_error_dialog(
                "OffShore Mentor - blad uruchomienia",
                "Nie udalo sie uruchomic aplikacji.\n\n"
                "Szczegoly zapisano w pliku logs\\launcher.log obok programu.\n\n"
                + traceback.format_exc(),
            )
            sys.exit(1)


if __name__ == "__main__":
    main()
