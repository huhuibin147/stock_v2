#!/usr/bin/env python3
"""Stock V2 部署脚本"""

import os
import sys
import subprocess
import tarfile
import io
from pathlib import Path

import paramiko
import yaml

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG_FILE = SCRIPT_DIR / "config.yaml"

EXCLUDE = {
    ".venv", "venv", "__pycache__", ".git", "node_modules", "dist",
    "data", "logs", ".DS_Store",
    "deploy/config.yaml", "app.log", "app.pid",
}


def load_config():
    if not CONFIG_FILE.exists():
        print(f"错误: 配置文件不存在: {CONFIG_FILE}")
        print(f"请复制 config.yaml.example 为 config.yaml 并填写服务器信息")
        sys.exit(1)
    with open(CONFIG_FILE) as f:
        return yaml.safe_load(f)


def build_frontend():
    """构建前端"""
    frontend_dir = PROJECT_DIR / "frontend"
    if not frontend_dir.exists():
        print("  前端目录不存在，跳过构建")
        return

    print("[1/4] 构建前端...")
    subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True)
    print("  前端构建完成 ✓")


def make_archive():
    """打包项目"""
    print("[2/4] 打包项目...")
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for root, dirs, files in os.walk(PROJECT_DIR):
            # 过滤排除目录
            dirs[:] = [d for d in dirs if d not in EXCLUDE]
            rel_root = Path(root).relative_to(PROJECT_DIR)

            for f in files:
                rel_path = rel_root / f
                if str(rel_path) in EXCLUDE:
                    continue
                if f.endswith(".pyc"):
                    continue

                full_path = Path(root) / f
                arcname = f"stock_v2/{rel_path}"

                tarinfo = tar.gettarinfo(str(full_path), arcname)
                if tarinfo is None:
                    continue

                # 文本文件换行符转换
                if f.endswith((".py", ".vue", ".ts", ".js", ".css", ".html", ".json", ".yaml", ".yml", ".md", ".sh", ".txt")):
                    try:
                        content = full_path.read_text(encoding="utf-8")
                        content = content.replace("\r\n", "\n")
                        data = content.encode("utf-8")
                        tarinfo.size = len(data)
                        tar.addfile(tarinfo, io.BytesIO(data))
                    except (UnicodeDecodeError, ValueError):
                        tar.addfile(tarinfo, open(full_path, "rb"))
                else:
                    tar.addfile(tarinfo, open(full_path, "rb"))

    buf.seek(0)
    size_mb = len(buf.getvalue()) / 1024 / 1024
    print(f"  打包完成: {size_mb:.1f} MB")
    return buf


def deploy(config, archive):
    """上传并部署"""
    host = config["host"]
    port = config.get("port", 22)
    user = config["user"]
    password = config["password"]
    remote_dir = config["remote_dir"]
    remote_tmp = "/tmp/stock_v2_deploy.tar.gz"

    print(f"[3/4] 上传到 {user}@{host}:{remote_dir}...")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=user, password=password)

    # SFTP 上传
    sftp = ssh.open_sftp()
    with sftp.file(remote_tmp, "wb") as f:
        f.write(archive.getvalue())
    sftp.close()
    print("  上传完成 ✓")

    print("[4/4] 解压并部署...")
    commands = [
        f"mkdir -p {remote_dir}",
        f"tar xzf {remote_tmp} -C {remote_dir} --strip-components=1",
        f"rm -f {remote_tmp}",
        # 创建虚拟环境并安装依赖
        f"cd {remote_dir}/backend && python3 -m venv venv 2>/dev/null || true",
        f"cd {remote_dir}/backend && venv/bin/pip install -r requirements.txt -q",
        # 创建数据目录
        f"mkdir -p {remote_dir}/data {remote_dir}/logs",
        # 重启服务
        f"bash {remote_dir}/deploy/service.sh restart",
    ]

    for cmd in commands:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            err = stderr.read().decode().strip()
            print(f"  命令失败: {cmd}")
            print(f"  错误: {err}")
            ssh.close()
            sys.exit(1)

    ssh.close()
    print("  部署完成 ✓")


def main():
    config = load_config()

    # 构建前端
    build_frontend()

    # 打包
    archive = make_archive()

    # 部署
    deploy(config, archive)

    print()
    print("=== 部署完成 ===")
    print(f"  服务器: {config['host']}")
    print(f"  目录: {config['remote_dir']}")
    print(f"  后端: http://{config['host']}:38080")
    print(f"  API文档: http://{config['host']}:38080/docs")


if __name__ == "__main__":
    main()
