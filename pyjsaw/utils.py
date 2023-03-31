from pathlib import Path
import importlib.util as imp_util


def imp_to_path(imp_id: str) -> Path:
    pkg, *rest = imp_id.split('.')
    sp = imp_util.find_spec(pkg)
    if not sp:
        return None
    pth = Path(sp.origin)
    if not rest or pth.name != '__init__.py':
        return pth

    pth = pth.parent

    if rest:
        pth = pth / '/'.join(rest)

    if pth.is_dir():
        pth = pth / '__init__.py'
    else:
        pth = pth.with_suffix('.py')
    return pth
