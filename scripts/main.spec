# -*- mode: python ; coding: utf-8 -*-
# Template to create packages for setuptools package: https://github.com/pyinstaller/pyinstaller/wiki/Recipe-Setuptools-Entry-Point

block_cipher = None

def Entrypoint(dist, group, name, **kwargs):
    from importlib.metadata import distribution, entry_points

    # get toplevel packages of distribution from metadata
    def get_toplevel(dist):
        top_level = distribution(dist).read_text('top_level.txt')
        return top_level.split() if top_level else []

    kwargs.setdefault('hiddenimports', [])
    packages = []
    for distribution_name in kwargs['hiddenimports']:
        packages += get_toplevel(distribution_name)

    kwargs.setdefault('pathex', [])
    # get the entry point
    ep = next(ep for ep in entry_points(group=group) if ep.name == name)
    # insert path of the distribution at the verify front of the search path
    kwargs['pathex'] = [str(distribution(dist).locate_file(''))] + kwargs['pathex']
    # script name must not be a valid module name to avoid name clashes on import
    script_path = os.path.join(workpath, name + '-script.py')
    print("creating script for entry point", dist, group, name)
    with open(script_path, 'w') as fh:
        print("import", ep.module, file=fh)
        print("%s.%s()" % (ep.module, ep.attr), file=fh)
        for package in packages:
            print("import", package, file=fh)

    return Analysis(
        [script_path] + kwargs.get('scripts', []),
        **kwargs
    )

# distribution needs to be installed in the machine when trying to package.
# dist, group, name
a = Entrypoint('lean', 'console_scripts', 'lean')

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# update executable name to lean-cli as modules.json is expected to be inside lean/
# the portable directory can't have two files with name lean 
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='lean-cli',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='lean-cli',
)