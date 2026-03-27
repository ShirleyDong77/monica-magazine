#!/usr/bin/env python3
"""
Magazine 网站自动更新脚本
每天 23:30 自动执行：
1. 读取飞书当日反思文档
2. 转换为 HTML
3. 生成封面图（MiniMax AI）
4. 提交到 GitHub
"""

import os
import json
import requests
from datetime import datetime
from pathlib import Path

# 配置
FEISHU_TOKEN = os.environ.get("FEISHU_TOKEN", "")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
REPO_OWNER = "ShirleyDong77"
REPO_NAME = "monica-eden"
BRANCH = "main"
SITE_DIR = Path(__file__).parent.parent
DAILY_DIR = SITE_DIR / "daily"

TODAY = datetime.now().strftime("%Y-%m-%d")
TODAY_DISPLAY = datetime.now().strftime("%Y.%m.%d")


def get_feishu_doc(token: str) -> dict:
    """从飞书获取当日反思文档"""
    # 查找今日反思文档
    # TODO: 实际实现时需要查询 Monica 知识库的每日反思节点
    # 目前用环境变量里的文档 ID
    doc_id = os.environ.get("TODAY_REFLECTION_DOC_ID", "")
    if not doc_id:
        print("未设置 TODolist_REFLECTION_DOC_ID，跳过")
        return None

    url = f"https://open.feishu.cn/open-apis/doc/v2/doc/{doc_id}"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers)
    if resp.status_code == 200:
        return resp.json()
    else:
        print(f"读取飞书文档失败: {resp.status_code}")
        return None


def convert_to_html(content: str, date: str) -> str:
    """将飞书 Markdown 内容转换为 HTML"""
    # 简单转换，实际需要更完善的 Markdown → HTML 转换
    html_content = content.replace("\n", "<br>")
    template = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>每日反思 {date} · MONICA</title>
  <link rel="stylesheet" href="../css/style.css">
</head>
<body>

<header class="masthead">
  <div class="container">
    <div class="masthead-inner">
      <div>
        <div class="magazine-title"><a href="../index.html">MONICA</a></div>
        <div class="magazine-subtitle">数字分身的认知周报</div>
      </div>
      <div class="masthead-date">{date}</div>
    </div>
  </div>
</header>

<nav class="nav">
  <div class="container">
    <ul class="nav-list">
      <li><a href="../index.html" class="nav-link">首页</a></li>
      <li><a href="../#daily" class="nav-link">每日反思</a></li>
    </ul>
  </div>
</nav>

<article class="article-body">
  <div class="container">
    <div class="article-content">
{html_content}
    </div>
  </div>
</article>

<footer class="footer">
  <div class="container">
    <div class="footer-inner">
      <div class="footer-logo"><a href="../index.html">MONICA</a></div>
      <div class="footer-copy">© 2026 Monica · Shirley 的数字分身</div>
    </div>
  </div>
</footer>

</body>
</html>'''
    return template


def generate_cover_image(prompt: str, output_path: str):
    """用 MiniMax AI 生成封面图"""
    api_key = os.environ.get("MINIMAX_API_KEY", "")
    if not api_key:
        print("未设置 MINIMAX_API_KEY，跳过封面图生成")
        return False

    url = "https://api.minimaxi.com/v1/image_generation"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "image-01",
        "prompt": prompt,
        "aspect_ratio": "16:9",
        "response_format": "url"
    }

    resp = requests.post(url, headers=headers, json=data)
    if resp.status_code == 200:
        result = resp.json()
        image_url = result.get("data", {}).get("url", "")
        if image_url:
            # 下载图片
            img_resp = requests.get(image_url)
            if img_resp.status_code == 200:
                with open(output_path, "wb") as f:
                    f.write(img_resp.content)
                print(f"封面图已生成: {output_path}")
                return True
    print(f"封面图生成失败: {resp.status_code}")
    return False


def commit_to_github(file_path: Path, content: str, message: str):
    """提交文件到 GitHub"""
    if not GITHUB_TOKEN:
        print("未设置 GITHUB_TOKEN，跳过 GitHub 提交")
        return False

    import base64

    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{file_path}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }

    # 获取当前 SHA（如果文件存在）
    get_resp = requests.get(url, headers=headers)
    sha = None
    if get_resp.status_code == 200:
        sha = get_resp.json().get("sha")

    # 准备提交数据
    data = {
        "message": message,
        "content": base64.b64encode(content.encode("utf-8")).decode("ascii"),
        "branch": BRANCH
    }
    if sha:
        data["sha"] = sha

    put_resp = requests.put(url, headers=headers, json=data)
    if put_resp.status_code in [200, 201]:
        print(f"已提交到 GitHub: {file_path}")
        return True
    else:
        print(f"GitHub 提交失败: {put_resp.status_code} - {put_resp.text}")
        return False


def main():
    print(f"开始 Magazine 自动更新 - {TODAY}")

    # 1. 获取飞书文档
    doc = get_feishu_doc(FEISHU_TOKEN)
    if not doc:
        print("未获取到文档，退出")
        return

    # 2. 转换为 HTML
    content = doc.get("data", {}).get("content", "")
    html = convert_to_html(content, TODAY_DISPLAY)

    # 3. 生成封面图
    cover_path = SITE_DIR / "images" / f"cover-{TODAY}.jpg"
    generate_cover_image(
        f"Magazine cover for {TODAY}, minimalist editorial design, black and white with gold accents, elegant typography",
        str(cover_path)
    )

    # 4. 写入本地文件
    daily_html = DAILY_DIR / f"{TODAY}.html"
    daily_html.write_text(html, encoding="utf-8")
    print(f"本地文件已写入: {daily_html}")

    # 5. 提交到 GitHub（Vercel 会自动部署）
    commit_to_github(
        f"daily/{TODAY}.html",
        html,
        f"daily: add reflection {TODAY}"
    )

    print(f"更新完成: {TODAY}")


if __name__ == "__main__":
    main()
