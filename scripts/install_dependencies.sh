#!/usr/bin/env bash
# Script to install sub-tools dependencies

set -e

# Print colored messages
print_green() {
    echo -e "\033[0;32m$1\033[0m"
}

print_yellow() {
    echo -e "\033[0;33m$1\033[0m"
}

print_red() {
    echo -e "\033[0;31m$1\033[0m"
}

# Detect OS
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="linux"
    if [ -f /etc/debian_version ]; then
        DISTRO="debian"
    elif [ -f /etc/redhat-release ]; then
        DISTRO="redhat"
    else
        DISTRO="unknown"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macos"
    DISTRO="macos"
else
    OS="unknown"
    DISTRO="unknown"
fi

print_yellow "Detected OS: $OS ($DISTRO)"
print_yellow "Installing dependencies for sub-tools...\n"

# Install system dependencies
if [ "$OS" == "linux" ]; then
    if [ "$DISTRO" == "debian" ]; then
        print_green "Installing system dependencies with apt..."
        sudo apt-get update
        sudo apt-get install -y ffmpeg libasound2-dev
    elif [ "$DISTRO" == "redhat" ]; then
        print_green "Installing system dependencies with yum..."
        sudo yum update -y
        sudo yum install -y ffmpeg alsa-lib-devel
    else
        print_red "Unsupported Linux distribution. Please install FFmpeg manually."
        exit 1
    fi
elif [ "$OS" == "macos" ]; then
    if command -v brew >/dev/null 2>&1; then
        print_green "Installing system dependencies with Homebrew..."
        brew install ffmpeg portaudio
    else
        print_red "Homebrew not found. Please install Homebrew first:"
        print_yellow "/bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
        exit 1
    fi
else
    print_red "Unsupported OS. Please install dependencies manually according to the README."
    exit 1
fi

# Install Python dependencies
print_green "\nInstalling Python dependencies with pip..."
python -m pip install -r requirements.txt

print_green "\nDependencies installation completed!"
print_yellow "You can verify the installation by running: python scripts/check_dependencies.py"