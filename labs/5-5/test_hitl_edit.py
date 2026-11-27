#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# [5-5] hitl_edit.py 테스트 실행 스크립트

import sys
from pathlib import Path

# 경로 설정
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).parent))

if __name__ == "__main__":
    from hitl_edit import test_hitl_edit
    test_hitl_edit()
