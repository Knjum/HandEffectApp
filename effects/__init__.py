"""
effects/__init__.py
Danh sách tất cả hiệu ứng. Muốn thêm hiệu ứng mới:
  1. Tạo file mới trong thư mục effects/ (copy từ một file có sẵn)
  2. Import class đó ở đây và thêm vào ALL_EFFECTS
"""

from effects.heart import HeartEffect
from effects.particles import ParticleEffect
from effects.lighting import HandGlowEffect, LightRaysEffect
from effects.background import BackgroundBlurEffect, BackgroundReplaceEffect
from effects.disappearing import DisappearEffect

# Thứ tự ở đây = số phím tắt (1, 2, 3...). Thứ tự VẼ do thuộc tính `layer` quyết định.
ALL_EFFECTS = [
    HeartEffect,              # phím 1
    ParticleEffect,           # phím 2
    HandGlowEffect,           # phím 3
    LightRaysEffect,          # phím 4
    BackgroundBlurEffect,     # phím 5
    BackgroundReplaceEffect,  # phím 6
    DisappearEffect,          # phím 7
]