@echo off
cd /d "%~dp0"

echo =^> 生成图标...
pip install pillow --quiet
python make_icon.py

echo =^> 安装 PyInstaller...
pip install pyinstaller --quiet

echo =^> 构建 Windows .exe...
pyinstaller --clean --noconfirm CodexSwitch.spec

echo.
echo ^> 构建完成！
echo   .exe  -^>  dist\CodexSwitch.exe
echo.
echo 分发说明：
echo   将 dist\CodexSwitch.exe 发给其他 Windows 用户直接运行即可
echo   用户需自行从 go.dev/dl 安装 Go，App 内有引导
pause
