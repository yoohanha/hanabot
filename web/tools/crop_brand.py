#!/usr/bin/env python3
# [3-3] 하나 AI 브랜드 이미지 자르기

from PIL import Image
from pathlib import Path

# 경로
PROJECT_ROOT = Path(__file__).parent.parent.parent
BRAND_BOARD = PROJECT_ROOT / 'web' / 'static' / 'assets' / 'hana_brand_board.png'
BRAND_DIR = PROJECT_ROOT / 'web' / 'static' / 'assets' / 'brand'

# 디렉토리 생성
BRAND_DIR.mkdir(parents=True, exist_ok=True)

# 원본 이미지 열기
img = Image.open(BRAND_BOARD)
width, height = img.size
print(f"원본 이미지 크기: {width}x{height}")

# 4칸 자르기
half_w = width // 2
half_h = height // 2

# 1. logo_grid.png (왼쪽 위)
logo_grid = img.crop((0, 0, half_w, half_h))
logo_grid.save(BRAND_DIR / 'logo_grid.png')
print(f"✓ logo_grid.png 저장 ({half_w}x{half_h})")

# 2. app_icon.png (왼쪽 아래)
app_icon = img.crop((0, half_h, half_w, height))
app_icon.save(BRAND_DIR / 'app_icon.png')
print(f"✓ app_icon.png 저장 ({half_w}x{half_h})")

# 3. mark_glass.png (오른쪽 아래, 배경 투명)
mark_glass = img.crop((half_w, half_h, width, height)).convert('RGBA')
# 하얀색 배경을 투명하게
data = mark_glass.getdata()
newData = []
for item in data:
    # RGB가 (255, 255, 255) 또는 가까운 흰색이면 투명
    if item[0] > 240 and item[1] > 240 and item[2] > 240:
        newData.append((255, 255, 255, 0))
    else:
        newData.append(item)
mark_glass.putdata(newData)
mark_glass.save(BRAND_DIR / 'mark_glass.png')
print(f"✓ mark_glass.png 저장 ({half_w}x{half_h}, 배경 투명)")

print("\n✅ 모든 이미지 자르기 완료!")
