"""Steam discovery and bundled retoc selection."""
import os
from pathlib import Path
import re
import sys

APP_ID = '2634950'


def expanded(value):
    return Path(os.path.expandvars(str(value))).expanduser()


def parse_vdf(text):
    # Quoted KeyValues strings, braces, and comments. Preserve Unicode paths.
    tokens = re.findall(r'//[^\n]*|"(?:\\.|[^"\\])*"|[{}]', text)
    tokens = [t for t in tokens if not t.startswith('//')]
    position = 0

    def string(token):
        if not token.startswith('"'):
            raise ValueError('Expected a quoted VDF string.')
        return re.sub(r'\\([\\"])', r'\1', token[1:-1])

    def block(nested=False, depth=0):
        nonlocal position
        if depth > 16:
            raise ValueError('VDF nesting is too deep.')
        result = {}
        while position < len(tokens):
            token = tokens[position]
            position += 1
            if token == '}':
                if not nested:
                    raise ValueError('Unexpected VDF closing brace.')
                return result
            key = string(token)
            if position >= len(tokens):
                raise ValueError('Missing VDF value.')
            value = tokens[position]
            position += 1
            result[key] = block(True, depth + 1) if value == '{' else string(value)
        if nested:
            raise ValueError('Unclosed VDF block.')
        return result
    return block()


def read_vdf(path):
    try:
        return parse_vdf(path.read_text(encoding='utf-8-sig'))
    except (OSError, ValueError):
        return {}


def windows_steam_roots():
    import winreg
    roots = []
    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            try:
                with winreg.OpenKey(hive, r'Software\Valve\Steam', 0, winreg.KEY_READ | view) as key:
                    for name in ('SteamPath', 'InstallPath'):
                        try:
                            roots.append(Path(winreg.QueryValueEx(key, name)[0]))
                        except OSError:
                            pass
            except OSError:
                pass
    # A bounded fallback for portable Steam installs; no recursive disk search.
    import ctypes
    mask = ctypes.windll.kernel32.GetLogicalDrives()
    for i in range(26):
        if mask & (1 << i):
            drive = Path(f'{chr(65+i)}:/')
            # Skip network and removable drives to avoid prompting or long hangs.
            if ctypes.windll.kernel32.GetDriveTypeW(str(drive)) == 3:
                roots.extend(drive / part for part in ('Steam', 'Games/Steam', 'SteamLibrary'))
    return roots


def steam_roots(env=None, home=None, platform=None):
    env = os.environ if env is None else env
    home = Path.home() if home is None else Path(home)
    platform = sys.platform if platform is None else platform
    roots = [expanded(env[k]) for k in ('SteamPath', 'STEAM_PATH', 'STEAM_DIR',
             'STEAM_COMPAT_CLIENT_INSTALL_PATH') if env.get(k)]
    if platform == 'win32':
        roots.extend(windows_steam_roots())
        roots.extend(Path(env[k]) / 'Steam' for k in ('ProgramFiles(x86)', 'ProgramFiles') if env.get(k))
    else:
        roots.extend([home / '.steam/steam', home / '.steam/root',
                      Path(env.get('XDG_DATA_HOME', home / '.local/share')) / 'Steam',
                      home / '.var/app/com.valvesoftware.Steam/.local/share/Steam',
                      home / '.var/app/com.valvesoftware.Steam/data/Steam',
                      home / 'snap/steam/common/.local/share/Steam'])
    return roots


def libraries(roots):
    result = []
    seen = set()
    pending = list(map(Path, roots))
    while pending:
        root = pending.pop(0).resolve()
        if root in seen:
            continue
        seen.add(root)
        if not root.is_dir():
            continue
        result.append(root)
        for relative in ('steamapps/libraryfolders.vdf', 'config/libraryfolders.vdf'):
            entries = read_vdf(root / relative).get('libraryfolders', {})
            if not isinstance(entries, dict):
                continue
            for key, entry in entries.items():
                if not key.isdigit():
                    continue
                value = entry.get('path') if isinstance(entry, dict) else entry
                if isinstance(value, str) and value:
                    candidate = expanded(value)
                    if candidate.is_absolute():
                        pending.append(candidate)
    return result


def mod_directory(game):
    path = expanded(game).resolve()
    candidates = [path / 'TokyoXtremeRacer/Content/Paks', path / 'Content/Paks',
                  path / 'Paks', path, path.parent if path.name == '~mods' else path]
    for paks in candidates:
        if (paks.name == 'Paks' and paks.parent.name == 'Content'
                and paks.parent.parent.name == 'TokyoXtremeRacer'
                and (paks / 'global.utoc').is_file() and any(paks.glob('pakchunk*.utoc'))):
            return paks / '~mods'
    raise ValueError(f'TXR game files were not found in {path}. Choose the TokyoXtremeRacer installation folder.')


def find_games(roots=None, env=None):
    env = os.environ if env is None else env
    candidates = []
    if env.get('STEAM_COMPAT_INSTALL_PATH'):
        candidates.append(expanded(env['STEAM_COMPAT_INSTALL_PATH']))
    for root in libraries(steam_roots(env=env) if roots is None else roots):
        state = read_vdf(root / 'steamapps' / f'appmanifest_{APP_ID}.acf').get('AppState', {})
        if isinstance(state, dict) and state.get('appid') == APP_ID:
            directory = state.get('installdir', '')
            if directory and directory not in ('.', '..') and not any(c in directory for c in '/\\:'):
                candidates.append(root / 'steamapps/common' / directory)
        candidates.append(root / 'steamapps/common/TokyoXtremeRacer')
    games = set()
    for candidate in candidates:
        try:
            games.add(mod_directory(candidate).parents[3])
        except (OSError, ValueError):
            pass
    return sorted(games, key=str)


def resolve_game(value=None):
    if value:
        return mod_directory(value)
    found = find_games()
    if not found:
        raise ValueError('TXR was not found automatically. Browse to the game folder or use --game PATH.')
    if len(found) > 1:
        raise ValueError('More than one TXR installation found. Choose one with --game PATH:\n' + '\n'.join(map(str, found)))
    return mod_directory(found[0])


def resolve_retoc(resource_root=None):
    """Locate the retoc binary embedded in a release or staged for development."""
    name = 'retoc.exe' if sys.platform == 'win32' else 'retoc'
    root = Path(resource_root or getattr(sys, '_MEIPASS', Path(__file__).resolve().parent))
    candidates = [root / 'retoc' / name, root / name, root / 'vendor' / 'retoc' / name]
    # This override is for source-tree development and CI; it is not user-facing.
    if os.environ.get('COLORFUL_RIVALS_RETOC'):
        candidates.insert(0, expanded(os.environ['COLORFUL_RIVALS_RETOC']))
    for candidate in candidates:
        if candidate.is_file():
            if sys.platform != 'win32' and not os.access(candidate, os.X_OK):
                continue
            return candidate.resolve()
    raise ValueError('The bundled retoc executable is missing or cannot be run. Re-extract the Colorful Rivals release.')
