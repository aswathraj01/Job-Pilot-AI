#!/bin/bash
# setup.sh  —  One-time setup for Job Autopilot
# Run once on your server: bash setup.sh

set -e
echo "=== Job Autopilot Setup ==="

# Python 3.10+ required
python3 --version

# Install dependencies
echo "Installing Python packages..."
pip3 install -r requirements.txt --break-system-packages 2>/dev/null || pip3 install -r requirements.txt

# Install Playwright browsers
echo "Installing Playwright browsers (Chromium)..."
python3 -m playwright install chromium
python3 -m playwright install-deps chromium

# Create resume placeholder if missing
if [ ! -f resume.txt ]; then
  cat > resume.txt << 'EOF'
YOUR NAME
your.email@example.com | +1 (555) 000-0000 | linkedin.com/in/yourprofile | github.com/yourhandle

PROFESSIONAL SUMMARY
Experienced software engineer with X years building scalable web applications...

EXPERIENCE

Company Name  |  Job Title  |  Jan 2022 – Present
- Achievement 1 with measurable impact
- Achievement 2

SKILLS
Languages: Python, JavaScript, TypeScript
Frameworks: FastAPI, React, Node.js
Cloud: AWS, GCP, Docker, Kubernetes

EDUCATION
Your University  |  B.S. Computer Science  |  2020
EOF
  echo "Created resume.txt placeholder — EDIT THIS with your real resume."
fi

# Install as a systemd service (Linux)
if command -v systemctl &>/dev/null; then
  WORKDIR=$(pwd)
  PYTHON=$(which python3)
  SERVICE_FILE="/etc/systemd/system/job-autopilot.service"
  
  sudo tee $SERVICE_FILE > /dev/null << EOF
[Unit]
Description=Job Autopilot
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$WORKDIR
ExecStart=$PYTHON $WORKDIR/main.py
Restart=always
RestartSec=30
StandardOutput=append:$WORKDIR/logs/service.log
StandardError=append:$WORKDIR/logs/service.log

[Install]
WantedBy=multi-user.target
EOF

  sudo systemctl daemon-reload
  echo ""
  echo "Systemd service installed. Commands:"
  echo "  sudo systemctl start  job-autopilot   # start"
  echo "  sudo systemctl enable job-autopilot   # auto-start on reboot"
  echo "  sudo systemctl status job-autopilot   # check status"
  echo "  sudo journalctl -u job-autopilot -f   # live logs"
fi

echo ""
echo "=== Setup complete ==="
echo "Next steps:"
echo "  1. Edit config.yaml with your API key, credentials, and job keywords"
echo "  2. Edit resume.txt with your real resume"
echo "  3. Run: python3 main.py"
echo "     Or as a service: sudo systemctl start job-autopilot"
