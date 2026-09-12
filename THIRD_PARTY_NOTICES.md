# Third-party resources

The MIT license covers original code, documentation and template designs, not third-party font software.

## Fonts — SIL Open Font License 1.1

- `src/namishu_printables/assets/fonts/NotoSansSC-Light.ttf`: unmodified Noto Sans SC Light,
  version 2.004-H2, copyright 2014–2021 Adobe, reserved font name Source.
  The file was migrated from Namishu's existing private printables project.
  Source: https://github.com/notofonts/noto-cjk
  License: `src/namishu_printables/assets/fonts/OFL.txt`.
- `src/namishu_printables/assets/fonts/pinyin-regular.ttf`: unmodified regular font from
  https://github.com/jaywcjlove/pinyin-font, copyright 2024 Wang Chujiang.
  Reserved Font Names: `pinyin` and `宝宝字帖拼音字体`.
  Download: https://jaywcjlove.github.io/pinyin-font/pinyin-regular.ttf
  License: `src/namishu_printables/assets/fonts/pinyin-OFL.txt`.

Font embedding does not make the generated document subject to OFL; the font software retains OFL.
Custom fonts supplied by users remain subject to their own licenses.

## Reward card illustrations

The four PNG illustrations in `src/namishu_printables/reward_card/gfx/` were copied unchanged
from the sibling project `printables-latex/07-reward-card/gfx/` (star, event, face and cut).

## Map data excluded

No Amap-derived map data or generated map examples are distributed in this project.
See `docs/map-data-review.md` for the source review and future integration requirements.

## Runtime dependencies

PyYAML, ReportLab, pypinyin and fontTools are declared dependencies installed separately; they retain their respective licenses.
