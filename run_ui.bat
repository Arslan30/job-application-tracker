@echo off
cd /d I:\job-application-tracker
call venv\Scripts\activate
python -m streamlit run ui.py
pause
