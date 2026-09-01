@echo off
cd /d "%~dp0"
echo [%date% %time%] 启动工具 >> debug.log
python -u "%~dp0main.pyw" %* >> debug.log 2>&1
echo [%date% %time%] 退出，错误码：%errorlevel% >> debug.log
pause