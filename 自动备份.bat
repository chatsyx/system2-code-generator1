@echo off
chcp 936 >nul
cd /d c:\System2\code\system2-ui
md 备份数据 2>nul
md 备份数据\备份_%date:~0,4%%date:~5,2%%date:~8,2% 2>nul
md 备份数据\备份_%date:~0,4%%date:~5,2%%date:~8,2%\生成的代码 2>nul
copy system2_log.txt 备份数据\备份_%date:~0,4%%date:~5,2%%date:~8,2%\ 2>nul
copy system2_code_*.py 备份数据\备份_%date:~0,4%%date:~5,2%%date:~8,2%\生成的代码\ 2>nul
copy .env 备份数据\备份_%date:~0,4%%date:~5,2%%date:~8,2%\ 2>nul
echo 备份完成（文件在 备份数据 文件夹）
pause