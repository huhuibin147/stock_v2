#!/usr/bin/env python3
"""Stock V2 部署脚本"""

import os
import sys
import subprocess
import tarfile
import io
import hashlib
from pathlib import Path

import paramiko
import yaml

SCRIPT_DIR = Path(__file__).parent
PROJECT_DIR = SCRIPT_DIR.parent
CONFIG_FILE = SCRIPT_DIR / "config.yaml"
HASH_FILE = SCRIPT_DIR / ".deploy_hash"

EXCLUDE = {
    ".venv", "venv", "__pycache__", ".git", "node_modules",
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


def get_frontend_hash():
    """计算前端代码的hash"""
    frontend_dir = PROJECT_DIR / "frontend"
    if not frontend_dir.exists():
        return None

    files_to_hash = []
    for root, dirs, files in os.walk(frontend_dir / "src"):
        dirs[:] = [d for d in dirs if d not in EXCLUDE]
        for f in files:
            if f.endswith((".vue", ".ts", ".js", ".css")):
                files_to_hash.append(str(Path(root) / f))

    # 加上 package.json
    pkg = frontend_dir / "package.json"
    if pkg.exists():
        files_to_hash.append(str(pkg))

    if not files_to_hash:
        return None

    hasher = hashlib.md5()
    for f in sorted(files_to_hash):
        try:
            hasher.update(Path(f).read_bytes())
        except Exception:
            pass
    return hasher.hexdigest()


def get_backend_hash():
    """计算后端代码的hash"""
    backend_dir = PROJECT_DIR / "backend"
    if not backend_dir.exists():
        return None

    files_to_hash = []
    for root, dirs, files in os.walk(backend_dir / "app"):
        dirs[:] = [d for d in dirs if d not in EXCLUDE]
        for f in files:
            if f.endswith(".py"):
                files_to_hash.append(str(Path(root) / f))

    # 加上 requirements.txt 和 service.sh
    for extra in ["requirements.txt", "../deploy/service.sh"]:
        p = backend_dir / extra
        if p.exists():
            files_to_hash.append(str(p))

    if not files_to_hash:
        return None

    hasher = hashlib.md5()
    for f in sorted(files_to_hash):
        try:
            hasher.update(Path(f).read_bytes())
        except Exception:
            pass
    return hasher.hexdigest()


def load_deploy_hash():
    """加载上次部署的hash"""
    if HASH_FILE.exists():
        data = HASH_FILE.read_text().strip().split("\n")
        result = {}
        for line in data:
            if "=" in line:
                k, v = line.split("=", 1)
                result[k.strip()] = v.strip()
        return result
    return {}


def save_deploy_hash(frontend_hash, backend_hash):
    """保存本次部署的hash"""
    HASH_FILE.write_text(f"frontend={frontend_hash}\nbackend={backend_hash}\n")


def build_frontend(force=False):
    """构建前端（仅当代码变化时）"""
    frontend_dir = PROJECT_DIR / "frontend"
    if not frontend_dir.exists():
        print("  前端目录不存在，跳过构建")
        return False

    current_hash = get_frontend_hash()
    last_hash = load_deploy_hash().get("frontend")

    if not force and current_hash == last_hash:
        print("[1/4] 前端代码未变化，跳过构建 ✓")
        return False

    print("[1/4] 构建前端...")
    subprocess.run(["npm", "run", "build"], cwd=frontend_dir, check=True)
    print("  前端构建完成 ✓")
    return True


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


def deploy(config, archive, backend_changed=True):
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

    # SFTP 上传项目包
    sftp = ssh.open_sftp()
    with sftp.file(remote_tmp, "wb") as f:
        f.write(archive.getvalue())

    # 上传本地数据库（仅当文件大小变化时）
    local_db = PROJECT_DIR / "backend" / "data" / "stock_v2.db"
    if local_db.exists():
        remote_db = f"{remote_dir}/backend/data/stock_v2.db"
        need_upload = True
        try:
            remote_stat = sftp.stat(remote_db)
            local_size = local_db.stat().st_size
            if remote_stat.st_size == local_size:
                need_upload = False
                print(f"  数据库未变化，跳过上传")
        except FileNotFoundError:
            pass
        if need_upload:
            print(f"  上传数据库 ({local_db.stat().st_size / 1024 / 1024:.1f} MB)...")
            sftp.put(str(local_db), remote_db)
            print("  数据库上传完成 ✓")

    sftp.close()
    print("  上传完成 ✓")

    print("[4/4] 解压并部署...")
    commands = [
        f"mkdir -p {remote_dir}",
        f"tar xzf {remote_tmp} -C {remote_dir} --strip-components=1",
        f"rm -f {remote_tmp}",
        f"mkdir -p {remote_dir}/data {remote_dir}/logs",
    ]

    # 仅当后端代码变化时才重新安装依赖和重启服务
    if backend_changed:
        commands.extend([
            f"cd {remote_dir}/backend && python3 -m venv .venv && .venv/bin/pip install --upgrade pip -q && .venv/bin/pip install -r requirements.txt -q",
            f"cp {remote_dir}/deploy/nginx.conf /etc/nginx/conf.d/stock_v2.conf",
            f"chmod +x {remote_dir}/deploy/service.sh",
            f"bash {remote_dir}/deploy/service.sh restart",
        ])
    else:
        # 只更新nginx配置（前端变化时）
        commands.extend([
            f"cp {remote_dir}/deploy/nginx.conf /etc/nginx/conf.d/stock_v2.conf",
        ])

    for cmd in commands:
        stdin, stdout, stderr = ssh.exec_command(cmd)
        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode().strip()
        err = stderr.read().decode().strip()
        if exit_code != 0:
            print(f"  命令失败: {cmd}")
            if out:
                print(f"  输出: {out}")
            if err:
                print(f"  错误: {err}")
            ssh.close()
            sys.exit(1)

    ssh.close()
    print("  部署完成 ✓")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Stock V2 部署脚本")
    parser.add_argument("--force", action="store_true", help="强制重新构建前端")
    parser.add_argument("--backend-only", action="store_true", help="仅部署后端")
    parser.add_argument("--frontend-only", action="store_true", help="仅部署前端")
    args = parser.parse_args()

    config = load_config()

    # 计算当前hash
    current_frontend_hash = get_frontend_hash()
    current_backend_hash = get_backend_hash()
    last_hash = load_deploy_hash()

    # 判断是否有变化
    frontend_changed = current_frontend_hash != last_hash.get("frontend")
    backend_changed = current_backend_hash != last_hash.get("backend")

    if not frontend_changed and not backend_changed and not args.force:
        print("代码未变化，跳过部署。使用 --force 强制部署。")
        return

    # 构建前端
    if not args.backend_only:
        build_frontend(force=args.force)
    else:
        print("[1/4] 跳过前端构建（仅后端模式）")

    # 打包
    archive = make_archive()

    # 部署
    deploy(config, archive, backend_changed=backend_changed or args.backend_only)

    # 保存hash
    save_deploy_hash(current_frontend_hash or "", current_backend_hash or "")

    print()
    print("=== 部署完成 ===")
    print(f"  服务器: {config['host']}")
    print(f"  目录: {config['remote_dir']}")
    print(f"  后端: http://{config['host']}:38080")
    print(f"  API文档: http://{config['host']}:38080/docs")
    if frontend_changed:
        print(f"  前端: 已更新")
    if backend_changed:
        print(f"  后端: 已更新")


if __name__ == "__main__":
    main()
