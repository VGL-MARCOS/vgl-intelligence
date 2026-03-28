@echo off
echo ============================================
echo  Iniciando CRTI Intelligence App
echo ============================================
cd /d C:\projetos\crti-claude-integration
streamlit run app.py --server.port 8501
