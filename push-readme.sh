#!/bin/bash
# README를 GitHub에 올리기 위한 명령 (한 줄씩 터미널에 복사해서 써도 됨)

cd /Users/seonpil/.cursor/worktrees/FQDC_Project/ici

git checkout -b main

git add README.md

git commit -m "Add README for GitHub"

# 아래 URL을 본인 GitHub 저장소 주소로 바꾼 뒤 실행
# git remote add origin https://github.com/본인아이디/저장소이름.git

# git push -u origin main
