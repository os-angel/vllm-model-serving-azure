"""Smoke-test a local amd64 chat image; remove only the test container on exit."""
import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path


def docker(*args):
    return subprocess.check_output(["docker", *args], text=True).strip()


def get(base, path):
    with urllib.request.urlopen(base + path, timeout=5) as response:
        return response.read().decode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="nemotron-chat:group2")
    parser.add_argument("--output", type=Path, default=Path(".local/integration-validation/image-smoke.json"))
    args = parser.parse_args()
    image = json.loads(docker("image", "inspect", args.image))[0]
    if (image["Os"], image["Architecture"]) != ("linux", "amd64"):
        raise RuntimeError("La imagen debe ser linux/amd64 para los nodos GKE.")
    container = None
    report = {"image_id": image["Id"], "platform": "linux/amd64", "local_size_bytes": image["Size"], "cloud_tested": False}
    try:
        container = docker("run", "--detach", "--rm", "--platform", "linux/amd64",
                           "--read-only", "--user", "10001:10001", "--cap-drop", "ALL",
                           "--security-opt", "no-new-privileges", "--cpus", "0.5", "--memory", "512m",
                           "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m", "--publish", "127.0.0.1::8080",
                           "--env", "VLLM_BASE_URL=http://127.0.0.1:1/v1", args.image)
        data = json.loads(docker("inspect", container))[0]
        port = data["NetworkSettings"]["Ports"]["8080/tcp"][0]["HostPort"]
        base = f"http://127.0.0.1:{port}"
        deadline = time.monotonic() + 60
        while True:
            try:
                health = json.loads(get(base, "/health"))
                break
            except (urllib.error.URLError, TimeoutError, ConnectionError):
                if time.monotonic() >= deadline:
                    raise RuntimeError("La imagen no alcanzó /health en 60 segundos.")
                time.sleep(0.25)
        assert health == {"backend": "available"}
        assert "Nemotron Chat" in get(base, "/")
        assert "textContent" in get(base, "/static/chat.js")
        status = json.loads(get(base, "/api/status"))
        assert status["backend"] == "available" and status["serving"] == "unavailable"
        body = json.dumps({"messages": [{"role": "user", "content": "CONTROLLED_SMOKE_MARKER"}]}).encode()
        request = urllib.request.Request(base + "/api/chat", data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=10) as response:
            stream = response.read().decode()
        assert '"type": "error"' in stream and '"type": "done"' not in stream
        probe = """import os, importlib.util, json
from pathlib import Path
assert os.getuid() == 10001
assert importlib.util.find_spec('pytest') is None
assert importlib.util.find_spec('playwright') is None
assert not Path('/usr/local/bin/uv').exists()
assert not Path('/app/tests').exists()
try:
    Path('/app/should-not-write').write_text('test')
except OSError:
    pass
else:
    raise AssertionError('Filesystem raíz escribible')
Path('/tmp/write-test').write_text('test')
print(json.dumps({'uid': os.getuid(), 'runtime_only': True, 'root_read_only': True, 'tmp_writable': True}))
"""
        report.update(json.loads(docker("exec", container, "python", "-c", probe)))
        logs = docker("logs", container)
        assert "CONTROLLED_SMOKE_MARKER" not in logs
        report.update({"backend_health": "PASS", "static_files": "PASS", "offline_serving": "PASS", "chat_error": "PASS", "marker_absent_in_logs": True})
    finally:
        if container:
            docker("rm", "--force", container)
            report["test_container_removed"] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
