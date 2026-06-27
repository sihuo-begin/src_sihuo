from pathlib import Path
import subprocess
from datetime import datetime
import os
import tempfile
import configparser

def get_git_commit():
    """
    尝试先从 git 获取短 commit id；如果不是 git 仓库或 git 命令失败，按顺序回退到环境变量 VERSION_COMMIT，
    最后使用 "unknown"。不会在非 git 仓库中抛出异常。
    """
    # 先尝试 git 仓库
    try:
        res = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=True,
        )
        commit = res.stdout.strip()
        if commit:
            return commit
    except subprocess.CalledProcessError:
        # git 命令返回非 0（例如不是仓库）
        pass
    except Exception:
        # 超时或其他问题都回退到环境变量或 unknown
        pass

    # 回退到环境变量（如果设置了）
    env_commit = os.getenv("VERSION_COMMIT")
    if env_commit:
        return env_commit

    return "unknown"


def get_build_time(fmt="%Y%m%d-%H%M%S"):
    """
    返回可配置格式的构建时间（默认：YYYYmmdd-HHMMSS）。
    优先使用环境变量 VERSION_BUILD_TIME（若设置）。
    """
    env_time = os.getenv("VERSION_BUILD_TIME")
    if env_time:
        return env_time
    return datetime.now().strftime(fmt)


def write_version_ini(target_path: Path, commit: str = None, build_time: str = None):
    """
    将版本信息写入 target_path（Path 或 字符串），使用 INI 格式：
    [version]
    commit = <...>
    build_time = <...>

    使用原子写入（临时文件再 os.replace），并确保父目录存在。
    """
    if commit is None:
        commit = get_git_commit()
    if build_time is None:
        build_time = get_build_time()

    target_path = Path(target_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    cfg = configparser.ConfigParser()
    cfg["version"] = {"commit": commit, "build_time": build_time}

    # 在目标目录下创建临时文件，然后替换目标文件以保证原子性
    with tempfile.NamedTemporaryFile("w", delete=False, dir=str(target_path.parent), encoding="utf-8") as tf:
        cfg.write(tf)
        tmp_name = tf.name

    os.replace(tmp_name, str(target_path))


if __name__ == "__main__":
    write_version_ini(target_path="src/config/version.ini")