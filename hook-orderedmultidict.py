from PyInstaller.utils.hooks import get_package_paths
datas = [(get_package_paths('orderedmultidict')[1] + "/__version__.py", 'orderedmultidict')]
