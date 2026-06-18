"""Application entry point."""

from __future__ import annotations

from .ui.main_window import MainWindow


def main() -> None:
    """Launch the GUI."""
    MainWindow().mainloop()


if __name__ == "__main__":
    main()
