# PyInstaller spec for AgentHeroHost.exe — the no-console web host launcher.
# Build from the agenthero folder:
#   python -m PyInstaller --noconfirm --distpath dist agent_hero_host.spec
# Output: dist\AgentHeroHost.exe (single file, console=False).

a = Analysis(
    ['host_launcher.py'],
    path=['.'],
    # NOTE: the 2nd tuple element is a target DIRECTORY. Use '.' to place
    # config.json at the top level of _MEIPASS (a bare filename there would be
    # treated as a directory and break reads with PermissionError on Windows).
    datas=[
        ('plugins/', 'plugins/'),
        ('agenthero/webui/', 'agenthero/webui/'),
        ('config.json', '.'),
    ],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.zipfiles, a.datas,
    name='AgentHeroHost',
    console=False,
)
