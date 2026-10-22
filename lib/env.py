"""환경 파일 로딩과 필수 환경변수 조회. import 시 파일을 읽지 않는다."""
import os


def load_env_file(path, override=False):
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip().strip("\"'")
        if not name:
            continue
        if override or name not in os.environ:
            os.environ[name] = value


def get_required_env(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} 환경변수가 설정되지 않았습니다.")
    return value


