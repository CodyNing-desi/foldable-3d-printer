import glob
import os

from fontTools.ttLib import TTCollection, TTFont

_original_glob = glob.glob


def _valid_font(path):
    try:
        if os.path.splitext(path)[1].lower() == ".ttc":
            TTCollection(path)
        else:
            TTFont(path)
    except (OSError, EOFError, ValueError, KeyError, AttributeError):
        return False
    except Exception as error:
        if error.__class__.__name__ in {"TTLibError", "AssertionError"}:
            return False
        raise
    return True


def _glob_with_valid_fonts(pattern, *args, **kwargs):
    paths = _original_glob(pattern, *args, **kwargs)
    if "fonts" not in str(pattern).lower():
        return paths
    font_paths = [path for path in paths if os.path.splitext(path)[1].lower() in {".ttf", ".otf", ".ttc"}]
    if len(font_paths) != len(paths):
        return paths
    return [path for path in paths if _valid_font(path)]


glob.glob = _glob_with_valid_fonts
