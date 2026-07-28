@echo off
set SCRIPT_DIR=%~dp0
if exist "%SCRIPT_DIR%kilo.jar" (
    java -jar "%SCRIPT_DIR%kilo.jar" %*
) else (
    if not exist "%SCRIPT_DIR%classes" mkdir "%SCRIPT_DIR%classes"
    javac --release 21 -d "%SCRIPT_DIR%classes" "%SCRIPT_DIR%src\main\java\com\kilo\*.java"
    java -cp "%SCRIPT_DIR%classes" com.kilo.Main %*
)
