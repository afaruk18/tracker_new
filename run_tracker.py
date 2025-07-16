"""
Simple runner script for the Activity Tracker.

This script provides an easy way to start the activity tracker
with proper error handling and logging setup.
"""

import sys
from pathlib import Path

# Add the src directory to Python path as a fallback
src_path = Path(__file__).parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

try:
    from tracker.core.app import DevPulseApp

    def main():
        """Main entry point for the tracker."""
        print("Starting Activity Tracker...")
        print("Press Ctrl+C to stop")

        devpulse = DevPulseApp()
        devpulse.run()

    if __name__ == "__main__":
        main()

except KeyboardInterrupt:
    print("\nTracker stopped by user.")
    sys.exit(0)
except ImportError as e:
    print(f"Import Error: {e}")
    print("Make sure to install the package first:")
    print("  uv pip install -e .")
    sys.exit(1)
except Exception as e:
    print(f"Error starting tracker: {e}")
    sys.exit(1)
