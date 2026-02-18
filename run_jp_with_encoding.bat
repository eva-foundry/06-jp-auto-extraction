@echo off
REM JP Automation Script with Windows Encoding Fix
REM This batch file sets proper UTF-8 encoding to prevent UnicodeEncodeError crashes

echo Setting UTF-8 encoding for Python output...
set PYTHONIOENCODING=utf-8

echo Running JP automation with enhanced response detection...
python scripts\run_jp_batch.py %*

echo.
echo Script execution completed.
echo.
echo Usage examples:
echo   run_jp_with_encoding.bat --in input\questions.csv --out output\jp_answers.csv --headed --connect --no-timestamp
echo   run_jp_with_encoding.bat --in input\questions.csv --out output\jp_answers.csv --persistent --limit 5 --no-timestamp
echo   run_jp_with_encoding.bat --in input\questions.csv --out output\jp_answers.csv --headed --connect
echo.
echo Note: Use --no-timestamp for exact filename, otherwise timestamps are automatically added
pause