"""PyInstaller 打包入口：以包方式导入 main，规避相对导入问题。"""

from src.main import main

if __name__ == "__main__":
    raise SystemExit(main())
