@echo off
echo ============================================
echo  Instalando dependencias do App Web CRTI
echo ============================================
cd /d C:\projetos\crti-claude-integration
pip install streamlit plotly pandas
echo.
echo ============================================
echo  Instalacao concluida!
echo  Para rodar o app execute: rodar_app.bat
echo ============================================
pause
