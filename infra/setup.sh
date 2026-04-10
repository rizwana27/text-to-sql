#!/usr/bin/env bash
# infra/setup.sh — Provision a bare Ubuntu 22.04 EC2 instance.
# Run as root or with sudo: sudo bash infra/setup.sh

set -e  # Exit immediately on any error

echo "=== [1/6] Updating package index ==="
apt-get update -y

echo "=== [2/6] Installing system dependencies ==="
apt-get install -y \
    software-properties-common \  # Needed for add-apt-repository
    curl \                         # HTTP client for health checks and downloads
    git \                          # Source control
    nginx \                        # Reverse proxy and static file server
    build-essential \              # Compilers needed for some Python packages
    libssl-dev \                   # TLS support for Python's ssl module
    libffi-dev \                   # Foreign Function Interface for cryptography
    python3-dev \                  # Python headers for native extensions
    python3-pip \                  # Bootstrap pip before we create venv
    python3-venv                   # Virtual environment support

echo "=== [3/6] Installing Python 3.11 ==="
add-apt-repository -y ppa:deadsnakes/ppa          # PPA with newer Python versions
apt-get update -y
apt-get install -y python3.11 python3.11-venv python3.11-dev
update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1  # Set as default python3

echo "=== [4/6] Installing Node.js 20 ==="
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -  # Official NodeSource setup script
apt-get install -y nodejs
node --version  # Confirm installation

echo "=== [5/6] Enabling and starting nginx ==="
systemctl enable nginx   # Start nginx on boot
systemctl start nginx    # Start nginx now

echo "=== [6/6] Creating application directory ==="
mkdir -p /opt/text-to-sql   # Application root
chown ubuntu:ubuntu /opt/text-to-sql

echo "✅ System setup complete."
echo "Next: Run infra/configure_env.sh to set environment variables."
