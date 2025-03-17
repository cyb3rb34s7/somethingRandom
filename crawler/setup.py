#!/usr/bin/env python3
"""
setup.py - Setup script for the sports video fetcher project

This script:
1. Installs all required dependencies
2. Attempts to download the spaCy model (if needed)
3. Creates the necessary directory structure
4. Verifies the installation
"""

import os
import sys
import subprocess
import importlib
from pathlib import Path

def print_header(message):
    """Print a formatted header message."""
    print("\n" + "=" * 60)
    print(f" {message}")
    print("=" * 60)

def run_command(command, description):
    """Run a shell command and handle errors."""
    print(f"\n> {description}...")
    try:
        result = subprocess.run(
            command, 
            shell=True, 
            check=True,
            capture_output=True,
            text=True
        )
        print(f"  Success: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  Error: {e}")
        print(f"  Output: {e.stdout}")
        print(f"  Error output: {e.stderr}")
        return False

def check_module(module_name):
    """Check if a Python module is installed."""
    try:
        importlib.import_module(module_name)
        return True
    except ImportError:
        return False

def create_directory_structure():
    """Create the necessary directory structure for the project."""
    dirs = [
        "sports_video_fetcher",
        "sports_video_fetcher/modules",
        "sports_video_fetcher/data"
    ]
    
    for directory in dirs:
        os.makedirs(directory, exist_ok=True)
        print(f"  Created directory: {directory}")
    
    return True

def setup_spacy():
    """Attempt to set up spaCy and download the required model."""
    if not check_module("spacy"):
        print("  spaCy not installed, skipping model download")
        return False
    
    try:
        # Try different methods to download the model
        methods = [
            "python -m spacy download en_core_web_sm",
            "pip install https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.5.0/en_core_web_sm-3.5.0-py3-none-any.whl"
        ]
        
        for i, method in enumerate(methods, 1):
            print(f"  Attempting method {i} to download spaCy model...")
            if run_command(method, f"Downloading spaCy model (method {i})"):
                # Verify the model was installed
                try:
                    import spacy
                    spacy.load("en_core_web_sm")
                    print("  Successfully installed and verified spaCy model")
                    return True
                except OSError:
                    print("  Model download appeared to succeed but verification failed")
                    # Continue to next method
        
        print("  All download methods failed. The script will use fallback classification.")
        return False
    
    except Exception as e:
        print(f"  Error setting up spaCy: {str(e)}")
        return False

def main():
    """Main setup function."""
    print_header("Sports Video Fetcher Setup")
    
    # Install dependencies
    print_header("Installing Dependencies")
    run_command("pip install -r requirements.txt", "Installing required packages")
    
    # Create directory structure
    print_header("Creating Directory Structure")
    create_directory_structure()
    
    # Set up spaCy (optional)
    print_header("Setting up NLP Components (Optional)")
    spacy_success = setup_spacy()
    
    # Final verification
    print_header("Verifying Installation")
    
    required_modules = ["requests", "pandas", "pytrends"]
    optional_modules = ["spacy"]
    
    # Check required modules
    missing_required = [mod for mod in required_modules if not check_module(mod)]
    if missing_required:
        print(f"  Warning: The following required modules are missing: {', '.join(missing_required)}")
        print("  The application may not function correctly.")
    else:
        print("  All required modules are installed.")
    
    # Check optional modules
    missing_optional = [mod for mod in optional_modules if not check_module(mod)]
    if missing_optional:
        print(f"  Note: The following optional modules are missing: {', '.join(missing_optional)}")
        print("  The application will use fallback methods for these functionalities.")
    else:
        print("  All optional modules are installed.")
    
    # Final message
    print_header("Setup Complete")
    if not missing_required:
        print("The sports video fetcher is ready to use!")
        print("\nTo run the application:")
        print("  1. Navigate to the project directory")
        print("  2. Run: python main.py")
    else:
        print("The setup completed with warnings. Please resolve the issues mentioned above.")
    
    return 0 if not missing_required else 1

if __name__ == "__main__":
    sys.exit(main())