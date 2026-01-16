import dotenv
import os

# 读取用户输入的GitHub配置
github_token = input("请输入你的GitHub个人访问令牌（带repo权限）：").strip()
github_username = input("请输入你的GitHub用户名：").strip()
github_repo = input("请输入默认仓库名（如system2-code-repo）：").strip() or "system2-code-repo"

# 写入.env文件（覆盖原有配置）
env_data = f"""
GITHUB_TOKEN={github_token}
GITHUB_USERNAME={github_username}
GITHUB_REPO_NAME={github_repo}
"""

with open(".env", "w", encoding="utf-8") as f:
    f.write(env_data.strip())

print("✅ 配置保存成功！后续无需重复配置GitHub信息")
