#!/usr/bin/env bash
# =============================================================================
# raspi_setup.sh — contest_manager installer for Raspberry Pi 5
# Usage: bash scripts/raspi_setup.sh
# Run this once from the repo root on your Raspberry Pi.
# =============================================================================

set -euo pipefail

APP_NAME="contest_manager"
APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"   # repo root
VENV_DIR="$APP_DIR/env"
SERVICE_FILE="/etc/systemd/system/${APP_NAME}.service"
LOG_DIR="/var/log/${APP_NAME}"
PYTHON="python3"

echo "=== Contest Manager — Raspberry Pi Setup ==="
echo "App directory : $APP_DIR"
echo "Virtual env   : $VENV_DIR"
echo "Log directory : $LOG_DIR"
echo ""

# ── 1. System dependencies ────────────────────────────────────────────────────
echo "[1/6] Installing system packages..."
sudo apt-get update -qq
sudo apt-get install -y python3 python3-pip python3-venv git

# ── 2. Create log directory ───────────────────────────────────────────────────
echo "[2/6] Creating log directory at $LOG_DIR..."
sudo mkdir -p "$LOG_DIR"
sudo chown "$USER":"$USER" "$LOG_DIR"

# ── 3. Python virtual environment ─────────────────────────────────────────────
echo "[3/6] Setting up Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
    $PYTHON -m venv "$VENV_DIR"
fi
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

# ── 4. Install Python dependencies ────────────────────────────────────────────
echo "[4/6] Installing Python dependencies..."
pip install --upgrade pip -q
pip install -r "$APP_DIR/requirements.txt" -q

deactivate

# ── 5. Validate .env file ─────────────────────────────────────────────────────
echo "[5/6] Checking .env file..."
if [ ! -f "$APP_DIR/.env" ]; then
    echo "  ⚠️  WARNING: .env file not found at $APP_DIR/.env"
    echo "       Copy and fill in the template below, then re-run this script."
    cat <<'EOF'

  --- .env template ---
  EMAIL_SENDER="your_email@gmail.com"
  EMAIL_PASSWORD="your_app_password"
  EMAIL_RECIPIENT="recipient@gmail.com"
  CODEFORCES_USERNAME="your_cf_handle"
  CODEFORCES_KEY="your_cf_api_key"
  CODEFORCES_SECRET="your_cf_api_secret"
  LEETCODE_USERNAME="your_lc_handle"
  ---------------------

EOF
    exit 1
else
    echo "  ✅  .env found."
fi

# ── 6. Install systemd service ────────────────────────────────────────────────
echo "[6/6] Installing systemd service..."

sudo bash -c "cat > $SERVICE_FILE" <<EOF
[Unit]
Description=Contest Manager — coding contest tracker & notifier
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
EnvironmentFile=$APP_DIR/.env
ExecStart=$VENV_DIR/bin/python $APP_DIR/main.py
Restart=on-failure
RestartSec=30
StandardOutput=append:$LOG_DIR/contest_manager.log
StandardError=append:$LOG_DIR/contest_manager.log

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable "$APP_NAME"
sudo systemctl restart "$APP_NAME"

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Useful commands:"
echo "  View logs   : journalctl -u $APP_NAME -f"
echo "  Status      : sudo systemctl status $APP_NAME"
echo "  Stop        : sudo systemctl stop $APP_NAME"
echo "  Restart     : sudo systemctl restart $APP_NAME"
echo ""
echo "⚠️  If this is the first run, you may need to authenticate with Google Calendar."
echo "   SSH into the Pi and run once manually to complete OAuth:"
echo "   cd $APP_DIR && source env/bin/activate && python main.py"
