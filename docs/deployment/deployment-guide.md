# Deployment Guide

KnowledgeHub AI is designed to run without Docker on a single machine.

## Linux

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python setup.py
scripts/linux/start.sh
```

Copy `scripts/linux/knowledgehub-ai.service` into `/etc/systemd/system/`, adjust the working directory and user, then run:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now knowledgehub-ai
```

## macOS

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python setup.py
scripts/macos/start.sh
```

Use `scripts/macos/com.knowledgehub.ai.plist` as a launchd example.

## Windows

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python setup.py
scripts\windows\start.ps1
```

For service deployment, use NSSM or Windows Task Scheduler to run `python run.py` from the repository root.

## Local Models

Install Ollama locally and pull a supported model:

```bash
ollama pull mistral
ollama serve
```

No external API key is required.

