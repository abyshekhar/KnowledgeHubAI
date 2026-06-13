# Windows Service Installation

Use NSSM or Windows Task Scheduler to run KnowledgeHub AI as a service.

## NSSM

```powershell
nssm install KnowledgeHubAI "C:\path\to\knowledgehub-ai\.venv\Scripts\python.exe" "C:\path\to\knowledgehub-ai\run.py"
nssm set KnowledgeHubAI AppDirectory "C:\path\to\knowledgehub-ai"
nssm start KnowledgeHubAI
```

## Task Scheduler

Create a task that starts at boot and runs:

```text
C:\path\to\knowledgehub-ai\.venv\Scripts\python.exe C:\path\to\knowledgehub-ai\run.py
```

