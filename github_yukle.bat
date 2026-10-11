@echo off
REM blender-shorts-toolkit klasörünün İÇİNDE çalıştırın. GitHub CLI gerekir: winget install GitHub.cli
gh auth status >nul 2>&1 || gh auth login
gh repo create blender-shorts-toolkit --public --source . --remote origin --push
pause
