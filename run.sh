#!/bin/bash
# 앱 실행 — 접속 주소는 http://localhost:8501 하나만 사용합니다.
cd "$(dirname "$0")"
streamlit run app.py --server.port 8501
