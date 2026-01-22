#!/usr/bin/env python3
import subprocess
import sys
import socket
import os

def check_command(cmd, name):
    try:
        subprocess.run(cmd, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"✅ {name: <15} [OK]")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ {name: <15} [FAILED]")
        return False

def check_port(host, port, name):
    try:
        with socket.create_connection((host, port), timeout=1):
            print(f"✅ {name: <15} [OK] ({host}:{port})")
            return True
    except OSError:
        print(f"❌ {name: <15} [FAILED] (Connection refused)")
        return False

def main():
    print("🏥 Running System Health Check (The Doctor)...\n")
    all_good = True

    # 1. 基础工具检查
    all_good &= check_command("uv --version", "uv installed")
    all_good &= check_command("docker --version", "Docker Engine")
    
    # 2. 配置文件检查
    if os.path.exists("openspec/project.md"):
        print(f"✅ {'Project Spec': <15} [OK]")
    else:
        print(f"❌ {'Project Spec': <15} [MISSING]")
        all_good = False

    # 3. 核心服务端口检查 (假设在 WSL2 localhost)
    # 注意：如果你用 Docker Compose，确保端口映射出来了
    all_good &= check_port("localhost", 6379, "Redis")
    all_good &= check_port("localhost", 5432, "PostgreSQL")
    all_good &= check_port("localhost", 8000, "ChromaDB") 

    print("\n" + ("="*30))
    if all_good:
        print("✨ System is HEALTHY. Ready to code.")
        sys.exit(0)
    else:
        print("⚠️  System has ISSUES. Please fix before starting.")
        sys.exit(1)

if __name__ == "__main__":
    main()