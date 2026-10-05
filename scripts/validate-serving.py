#!/usr/bin/env python3
"""Validación del serving existente; evidencia privada en .local/."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.request
from serving_validation_checks import complete_choice, complete_stream, final_answer, quality, require

MODEL = "nvidia/NVIDIA-Nemotron-Nano-9B-v2-FP8"
REVISION = "8bc5eece2eb5514c4bca7f2ec655b91eb554f4c0"
CODE_REVISION = "6533e8de2c68e4536bf7c411d7a3ce5734111476"
DIGEST = "sha256:c62343ee72f094ef574ab3af2717d0c60fec5e0808b238f19ac4c0d22fd152f7"
ROOT = Path(__file__).resolve().parents[1]
CASES = json.loads((ROOT / "scripts/serving-validation-cases.json").read_text())


def configure_requests(reasoning, max_tokens):
    require(1 <= max_tokens <= 3072, "max_tokens debe estar entre 1 y 3072 para contexto 4096")
    CASES.update(system="/think" if reasoning else "/no_think", max_tokens=max_tokens,
                 temperature=0.6 if reasoning else 0, top_p=0.95 if reasoning else 1)


def sdk_check(base, mode):
    from openai import OpenAI
    client = OpenAI(base_url=base + "/v1", api_key="unused", timeout=300)
    messages = [{"role": "system", "content": CASES["system"]},
                {"role": "user", "content": "Explica en español qué es Terraform en dos frases."}]
    options = dict(model=MODEL, messages=messages, temperature=CASES["temperature"],
                   top_p=CASES["top_p"], max_tokens=CASES["max_tokens"])
    result = {"sdk_version": importlib.metadata.version("openai"), "mode": mode, "request": options}
    if mode == "chat":
        start = time.monotonic()
        reply = client.chat.completions.create(**options)
        choice = reply.choices[0]
        result.update(content=choice.message.content, finish_reason=choice.finish_reason,
                      chat_seconds=time.monotonic() - start,
                      usage=reply.usage.model_dump() if reply.usage else None)
        print(json.dumps(result, ensure_ascii=False, indent=2), flush=True)
        final_answer(complete_choice(choice.model_dump()), CASES["system"] == "/think")
        return
    start = time.monotonic()
    fragments, times, finish = [], [], None
    for chunk in client.chat.completions.create(**options, stream=True):
        for item in chunk.choices:
            if item.delta.content:
                fragments.append(item.delta.content)
                times.append(time.monotonic() - start)
            finish = item.finish_reason or finish
    result.update(stream_content="".join(fragments), stream_finish=finish,
                  content_events=len(times), arrival_seconds=times)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    require(fragments and finish == "stop", f"SDK streaming vacío/incompleto: {finish}")
    final_answer("".join(fragments), CASES["system"] == "/think")


# Ejecutado dentro del pod: no lee tokens ni variables de entorno completas.
REMOTE = r'''
import hashlib, importlib.util, json, pathlib, torch, vllm
from vllm.model_executor.models import ModelRegistry
root = pathlib.Path("/root/.cache/huggingface")
code = []
for name in ("configuration_nemotron_h.py", "modeling_nemotron_h.py"):
    for p in root.rglob(name):
        code.append({"path": str(p), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
weights = []
for p in sorted(root.glob("hub/models--nvidia--NVIDIA-Nemotron-Nano-9B-v2-FP8/snapshots/*/*.safetensors")):
    s = p.stat()
    with p.open("rb") as f:
        digest = hashlib.file_digest(f, "sha256").hexdigest()
    weights.append({"path": str(p), "target": str(p.resolve()), "bytes": s.st_size, "sha256": digest})
architecture = "NemotronHForCausalLM"
registered = ModelRegistry.models[architecture]
source = pathlib.Path(importlib.util.find_spec(registered.module_name).origin)
print(json.dumps({"vllm": vllm.__version__, "cuda": torch.version.cuda,
 "cuda_available": torch.cuda.is_available(), "gpu": torch.cuda.get_device_name(0),
 "cmdline": pathlib.Path("/proc/1/cmdline").read_text().replace("\0", " "),
 "model_class": {"module": registered.module_name, "architecture": architecture,
                 "class": registered.class_name, "observation": "registry mapping in independent process",
                 "source": str(source), "sha256": hashlib.sha256(source.read_bytes()).hexdigest()},
 "code": code, "weights": weights,
 "incomplete_files": [str(p) for p in root.rglob("*.incomplete")]}))
'''


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--with-recovery", action="store_true", help="Recrea el pod: interrumpe serving")
    parser.add_argument("--install-sdk", action="store_true", help="Instala openai en .local/validation-venv")
    parser.add_argument("--timeout", type=int, default=1800, help="Segundos máximos de recuperación")
    parser.add_argument("--reasoning", choices=("off", "on"), default="off")
    parser.add_argument("--max-tokens", type=int, default=None)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout debe ser mayor que cero")
    configure_requests(args.reasoning == "on", args.max_tokens if args.max_tokens is not None else
                       (2048 if args.reasoning == "on" else 128))
    os.umask(0o077)
    out = ROOT / ".local/serving-validation" / time.strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=False)
    (out / "protocol.json").write_text(json.dumps(CASES, ensure_ascii=False, indent=2))
    results = []
    print(f"Evidencia: {out}", flush=True)

    def note(name, status, detail):
        results.append((name, status, detail))
        print(f"{status}: {name}: {detail}", flush=True)

    def run(name, command, stdin=None, timeout=120):
        r = subprocess.run(command, input=stdin, text=True, capture_output=True, timeout=timeout)
        text = r.stdout + r.stderr
        text = re.sub(r"hf_[A-Za-z0-9]+", "[REDACTED]", text)
        (out / (name + ".txt")).write_text(text)
        if r.returncode:
            raise RuntimeError(f"{name}: código {r.returncode}; revisar {name}.txt")
        return r.stdout

    def kube(name, *command, stdin=None, timeout=120):
        return run(name, ["kubectl", "-n", "inference", *command], stdin, timeout)

    def attempt(name, function):
        try:
            value = function()
            status = "EVIDENCIA" if name.endswith("-captura") or name in ("before-API", "after-API") else "PASS"
            note(name, status, "Comprobación ejecutada; ver archivo de evidencia")
            return value
        except Exception as exc:
            note(name, "FAIL", str(exc) or type(exc).__name__)
            return None

    def snapshot(label):
        # Solo campos seleccionados; nunca exportar Secrets ni valores env arbitrarios.
        deploy = json.loads(kube(label + "-deployment", "get", "deploy", "vllm", "-o",
                                 'jsonpath={.spec.replicas}'))
        pods = json.loads(kube(label + "-pods", "get", "pods", "-l",
                              "app.kubernetes.io/name=vllm", "-o", "json"))
        # El archivo del pod podría contener valores env: conservar versión redactada.
        for pod in pods["items"]:
            for container in pod["spec"]["containers"]:
                for env in container.get("env", []):
                    if env["name"] not in ("HF_HOME", "LD_LIBRARY_PATH") and "value" in env:
                        env["value"] = "[REDACTED]"
            pod["metadata"].get("annotations", {}).pop("kubectl.kubernetes.io/last-applied-configuration", None)
        (out / (label + "-pods.txt")).write_text(json.dumps(pods, indent=2))
        pvc = json.loads(kube(label + "-pvc", "get", "pvc", "vllm-cache", "-o", "json"))
        require(deploy == 1 and len(pods["items"]) == 1, "Se requiere una réplica y un pod")
        pod = pods["items"][0]
        require(any(c["type"] == "Ready" and c["status"] == "True" for c in pod["status"].get("conditions", [])), "Pod no Ready")
        require(pvc["status"]["phase"] == "Bound", "PVC no Bound")
        require(pvc["spec"]["storageClassName"] == "standard-rwo", "StorageClass inesperada")
        require(pvc["spec"]["resources"]["requests"]["storage"] == "50Gi", "Capacidad solicitada inesperada")
        require(pvc["spec"]["accessModes"] == ["ReadWriteOnce"], "AccessMode inesperado")
        container = pod["spec"]["containers"][0]
        require(container["resources"]["limits"].get("nvidia.com/gpu") == "1", "Límite GPU inesperado")
        require(pod["spec"].get("nodeSelector", {}).get("workload") == "gpu", "Selector GPU ausente")
        require(any(t.get("key") == "dedicated" and t.get("value") == "gpu" and
                   t.get("effect") == "NoSchedule" and t.get("operator", "Equal") == "Equal"
                   for t in pod["spec"].get("tolerations", [])), "Toleration GPU ausente")
        require(all(p in container for p in ("startupProbe", "readinessProbe", "livenessProbe")), "Faltan probes")
        raw_runtime = kube(label + "-runtime", "exec", "deploy/vllm", "--",
                           "python3", "-c", REMOTE, timeout=600)
        runtime = json.loads(next(line for line in reversed(raw_runtime.splitlines()) if line.startswith('{"vllm":')))
        require(runtime["cuda_available"], "CUDA no disponible")
        require(runtime["weights"] and not runtime["incomplete_files"], "Pesos ausentes o descargas incompletas")
        return pod, pvc, runtime

    forward = None
    forward_log = None

    def stop_forward():
        nonlocal forward, forward_log
        if forward:
            forward.terminate()
            try:
                forward.wait(timeout=5)
            except subprocess.TimeoutExpired:
                forward.kill()
                forward.wait()
            forward = None
        if forward_log:
            forward_log.close()
            forward_log = None

    def api(label):
        nonlocal forward, forward_log
        stop_forward()
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        forward_log = (out / (label + "-port-forward.txt")).open("w")
        forward = subprocess.Popen(["kubectl", "-n", "inference", "port-forward", "svc/vllm",
                                    f"{port}:8000", "--address=127.0.0.1"],
                                   stdout=forward_log, stderr=forward_log)
        base = f"http://127.0.0.1:{port}"
        for _ in range(30):
            if forward.poll() is not None:
                raise RuntimeError("port-forward terminó; revisar evidencia")
            try:
                with urllib.request.urlopen(base + "/health", timeout=2) as r:
                    require(r.status == 200, 'Contrato incumplido: r.status == 200')
                break
            except Exception:
                time.sleep(1)
        else:
            raise RuntimeError("/health no respondió HTTP 200")
        note(label + "-SRV-07-health", "PASS", "HTTP 200 por port-forward propio")
        def catalog():
            with urllib.request.urlopen(base + "/v1/models", timeout=15) as r:
                models = json.load(r)
            (out / (label + "-models.json")).write_text(json.dumps(models, indent=2))
            require(any(m["id"] == MODEL and m["max_model_len"] == 4096 for m in models["data"]),
                    "Catálogo no identifica modelo/contexto esperados")
        attempt(label + "-SRV-09-catalog", catalog)

        def request_body(case, stream=False):
            return {"model": MODEL, "messages": [{"role": "system", "content": CASES["system"]},
                    {"role": "user", "content": case["prompt"]}], "max_tokens": CASES["max_tokens"],
                    "temperature": CASES["temperature"], "top_p": CASES["top_p"], "stream": stream}

        def chat_test(case):
            body = request_body(case)
            (out / f"{label}-{case['id']}-request.json").write_text(json.dumps(body, ensure_ascii=False, indent=2))
            req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=300) as r:
                chat = json.load(r)
            (out / f"{label}-{case['id']}-chat.json").write_text(json.dumps(chat, ensure_ascii=False, indent=2))
            attempt(label + "-SRV-09-contrato-chat-" + case["id"],
                    lambda: final_answer(complete_choice(chat["choices"][0]), args.reasoning == "on"))
            attempt(label + "-calidad-" + case["id"],
                    lambda: quality(final_answer(chat["choices"][0]["message"].get("content") or "",
                                                 args.reasoning == "on"), case))

        def stream_test():
            case = CASES["cases"][0]
            body = request_body(case, stream=True)
            req = urllib.request.Request(base + "/v1/chat/completions", data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            started, events = time.monotonic(), []
            try:
                with urllib.request.urlopen(req, timeout=300) as r:
                    for raw in r:
                        line = raw.decode().strip()
                        if line.startswith("data: "):
                            events.append({"seconds": time.monotonic() - started, "data": line[6:]})
                            if line[6:] == "[DONE]":
                                break
            finally:
                (out / (label + "-sse.json")).write_text(json.dumps(events, ensure_ascii=False, indent=2))
            attempt(label + "-SRV-09-contrato-SSE", lambda: final_answer(complete_stream(events), args.reasoning == "on"))
        for case in CASES["cases"]:
            attempt(label + "-chat-" + case["id"] + "-captura", lambda case=case: chat_test(case))
        attempt(label + "-SSE-captura", stream_test)
        python = ROOT / ".local/validation-venv/bin/python"
        if args.install_sdk and not python.exists():
            run("sdk-venv", ["uv", "venv", "--python", sys.executable, str(python.parent.parent)])
        if args.install_sdk and label == "before":
            run("sdk-install", ["uv", "pip", "install", "--python", str(python), "openai"], timeout=300)
        if python.exists():
            for mode in ("chat", "stream"):
                attempt(label + "-SRV-09-SDK-" + mode, lambda mode=mode: run(label + "-sdk-" + mode,
                    ["uv", "run", "--no-project", "--python", str(python), "python", str(Path(__file__).resolve()),
                     "--sdk-base", base, "--sdk-mode", mode, "--reasoning", args.reasoning,
                     "--max-tokens", str(CASES["max_tokens"])], timeout=360))
        else:
            note(label + "-SDK", "PENDIENTE", "Ejecutar con --install-sdk")

    try:
        run("context", ["kubectl", "config", "current-context"])
        context = (out / "context.txt").read_text().strip()
        require(context == "gke_llmresearch-510422_us-central1-a_nemotron-lab",
                "Contexto inesperado; no consultar ni recrear cargas de otro clúster")
        kube("ready-preflight", "wait", "--for=condition=Ready", "pod", "-l",
             "app.kubernetes.io/name=vllm", f"--timeout={args.timeout}s", timeout=args.timeout + 30)
        before = attempt("SRV-03/06/07/14-inicial", lambda: snapshot("before"))
        if before is None:
            raise RuntimeError("Se necesita serving Ready para validar")
        pod, pvc, runtime = before
        for label, command in [
            ("service", ["get", "svc", "vllm", "-o", "json"]),
            ("exposure", ["get", "svc,ingress", "-o", "json"]),
            ("pv", ["get", "pv", pvc["spec"]["volumeName"], "-o", "json"]),
            ("node", ["get", "node", pod["spec"]["nodeName"], "-o", "json"]),
            ("events", ["get", "events", "--sort-by=.lastTimestamp"]),
            ("logs", ["logs", "deploy/vllm", "--tail=300", "--timestamps"]),
        ]:
            attempt(label + "-captura", lambda label=label, command=command: kube(label, *command))
        service = json.loads((out / "service.txt").read_text())
        require(service["spec"]["type"] == "ClusterIP", 'Contrato incumplido: service["spec"]["type"] == "ClusterIP"')
        require(pod["spec"].get("enableServiceLinks") is False, 'Contrato incumplido: pod["spec"].get("enableServiceLinks") is False')
        require(DIGEST in pod["spec"]["containers"][0]["image"], 'Contrato incumplido: DIGEST in pod["spec"]["containers"][0]["image"]')
        require(all(v in runtime["cmdline"] for v in (REVISION, CODE_REVISION)), 'Contrato incumplido: all(v in runtime["cmdline"] for v in (REVISION, CODE_REVISION))')
        strategy = kube("strategy", "get", "deploy", "vllm", "-o", "jsonpath={.spec.strategy.type}")
        require(strategy == "Recreate", "Se requiere estrategia Recreate")
        exposure = json.loads((out / "exposure.txt").read_text())
        require(not any(item["kind"] == "Ingress" or
                       (item["kind"] == "Service" and item["spec"].get("type") != "ClusterIP")
                       for item in exposure["items"]), "Exposición inesperada en inference")
        note("SRV-01/04/08-contrato", "PASS", "Digest, reserva GPU, Recreate y exposición interna comprobados")
        def resources():
            node = json.loads((out / "node.txt").read_text())
            require(node["metadata"]["labels"].get("workload") == "gpu", "Nodo sin etiqueta GPU")
            require(any(t.get("key") == "dedicated" and t.get("value") == "gpu" and
                        t.get("effect") == "NoSchedule" for t in node["spec"].get("taints", [])), "Taint GPU ausente")
            require(node["status"]["allocatable"].get("nvidia.com/gpu") == "1", "GPU asignable inesperada")
            require(not any(c["type"] == "DiskPressure" and c["status"] == "True"
                            for c in node["status"].get("conditions", [])), "Nodo con DiskPressure")
            requests = pod["spec"]["containers"][0]["resources"]["requests"]
            def quantity(value):
                multipliers = {"m": .001, "Ki": 1024, "Mi": 1024**2, "Gi": 1024**3}
                for suffix in ("Ki", "Mi", "Gi", "m"):
                    if str(value).endswith(suffix):
                        return float(str(value)[:-len(suffix)]) * multipliers[suffix]
                return float(value)
            for resource in ("cpu", "memory", "ephemeral-storage"):
                require(resource in requests and quantity(requests[resource]) <=
                        quantity(node["status"]["allocatable"][resource]), "Request incompatible: " + resource)
            require(not any(s.get("lastState", {}).get("terminated", {}).get("reason") == "OOMKilled"
                            for s in pod["status"].get("containerStatuses", [])), "OOMKilled observado")
        attempt("SRV-04/05/10-recursos", resources)
        def storage_mount():
            container = pod["spec"]["containers"][0]
            mounts = container.get("volumeMounts", [])
            mount = next(m for m in mounts if m["mountPath"] == "/root/.cache/huggingface")
            require(any(v["name"] == mount["name"] and v.get("persistentVolumeClaim", {}).get("claimName") ==
                        "vllm-cache" for v in pod["spec"]["volumes"]), "Montaje HF no usa PVC esperado")
            require(any(e["name"] == "HF_HOME" and e.get("value") == mount["mountPath"]
                        for e in container.get("env", [])), "HF_HOME no apunta al PVC")
            pv = json.loads((out / "pv.txt").read_text())
            require(pv["spec"]["csi"]["driver"] == "pd.csi.storage.gke.io", "Driver PV inesperado")
            require("us-central1-a" in json.dumps(pv["spec"].get("nodeAffinity", {})), "Zona PV inesperada")
        attempt("SRV-14-montaje-zona", storage_mount)
        args_live = pod["spec"]["containers"][0].get("args", [])
        require("--no-enable-log-requests" in args_live and "--disable-uvicorn-access-log" in args_live,
                "Logging de solicitudes no deshabilitado")
        note("SRV-11-logs", "PARCIAL", "Logging de solicitudes deshabilitado; revisar logs privados y archivos versionables por contenido/secrets")
        require("--api-key" not in args_live, "API key inesperada para laboratorio autorizado")
        note("SRV-12-limite", "PASS", "ClusterIP sin API key: cargas con conectividad pueden llamar; port-forward requiere credenciales Kubernetes, no autentica llamadas internas")
        note("SRV-10-historico-pull", "PARCIAL", "Capturas actuales no reconstruyen espacio libre anterior al pull ni ocupación OCI exacta")
        # Muestreo durante las solicitudes; puede omitir picos entre muestras.
        def sampled_api(label):
            stopped = threading.Event()
            samples = []
            command = ["kubectl", "-n", "inference", "exec", "deploy/vllm", "--", "sh", "-c",
                       "/usr/local/nvidia/bin/nvidia-smi --query-gpu=timestamp,memory.used,memory.free,utilization.gpu --format=csv,noheader; "
                       "cat /sys/fs/cgroup/memory.current /sys/fs/cgroup/memory.peak 2>/dev/null"]
            def collect():
                while not stopped.is_set():
                    try:
                        r = subprocess.run(command, capture_output=True, text=True, timeout=20)
                        samples.append({"utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                                        "output": r.stdout, "error": r.stderr, "exit_code": r.returncode})
                    except Exception as exc:
                        samples.append({"error": str(exc)})
                    stopped.wait(1)
            worker = threading.Thread(target=collect, daemon=True)
            worker.start()
            try:
                return api(label)
            finally:
                stopped.set()
                worker.join(timeout=25)
                (out / (label + "-memory-samples.json")).write_text(json.dumps(samples, indent=2))
                if not samples or all(s.get("exit_code", 1) != 0 for s in samples):
                    note(label + "-memoria", "PENDIENTE", "Muestreo sin lectura completa; revisar errores del archivo")
        attempt("before-API", lambda: sampled_api("before"))
        for label, command in [
            ("disk", ["exec", "deploy/vllm", "--", "sh", "-c", "df -h / /root/.cache/huggingface; du -sh /root/.cache/huggingface"]),
            ("gpu", ["exec", "deploy/vllm", "--", "/usr/local/nvidia/bin/nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.used,memory.free", "--format=csv"]),
            ("ram", ["top", "pod"]),
        ]:
            attempt(label + "-captura", lambda label=label, command=command: kube(label, *command))
        try:
            node = json.loads((out / "node.txt").read_text())
            provider = node["spec"]["providerID"].removeprefix("gce://").split("/")
            project, zone, instance = provider
            require(project == "llmresearch-510422", "Proyecto inesperado; no ejecutar recuperación")
            disks = json.loads(run("boot-disk-reference", ["gcloud", "compute", "instances", "describe", instance,
                "--project=" + project, "--zone=" + zone, "--format=json(disks)"]))
            boot = next(d for d in disks["disks"] if d["boot"])
            disk = json.loads(run("boot-disk-size", ["gcloud", "compute", "disks", "describe", boot["source"].split("/")[-1],
                "--project=" + project, "--zone=" + zone, "--format=json(name,sizeGb,type)"]))
            require(disk["sizeGb"] == "100" and disk["type"].endswith("/pd-balanced"), "Boot disk GPU no coincide con 100 GB pd-balanced")
            terraform = (ROOT / "terraform/infra/gke.tf").read_text().split('resource "google_container_node_pool" "gpu"', 1)[1]
            require(re.search(r"disk_size_gb\s*=\s*100", terraform) and
                    "node_config[0].disk_size_gb" in terraform,
                    "Terraform no declara 100 GB y excepción controlada del pool existente")
            note("SRV-10-boot-disk", "PASS", "Disco real 100 GB pd-balanced; Terraform declara 100 GB y excepción de actualización del pool")
        except Exception as exc:
            note("SRV-10-boot-disk", "PENDIENTE", str(exc))
        for name in ("configuration_nemotron_h.py",):
            try:
                url = f"https://huggingface.co/nvidia/NVIDIA-Nemotron-Nano-9B-v2/resolve/{CODE_REVISION}/{name}"
                with urllib.request.urlopen(url, timeout=30) as r:
                    expected = hashlib.sha256(r.read()).hexdigest()
                matches = [c for c in runtime["code"] if c["path"].endswith("/" + name)]
                (out / (name + "-comparison.json")).write_text(json.dumps({"expected_sha256": expected, "cached": matches}, indent=2))
                if not matches or any(c["sha256"] != expected for c in matches):
                    note("SRV-02-" + name, "PENDIENTE", "Archivos ausentes o distintos; revisar comparación")
                else:
                    require(any(CODE_REVISION in c["path"] for c in matches), "Falta ruta con revisión de código fijada")
                    note("SRV-02-" + name, "PASS", "Código cacheado coincide con commit fijado; se conserva ruta y hash")
            except Exception as exc:
                note("SRV-02-" + name, "PENDIENTE", str(exc))
        def native_model():
            model_class = runtime["model_class"]
            require(model_class["module"] == "vllm.model_executor.models.nemotron_h", "Modelo nativo inesperado")
            url = "https://raw.githubusercontent.com/vllm-project/vllm/v0.10.1/vllm/model_executor/models/nemotron_h.py"
            with urllib.request.urlopen(url, timeout=30) as r:
                expected = hashlib.sha256(r.read()).hexdigest()
            require(model_class["sha256"] == expected, "Código nativo no coincide con versión v0.10.1")
            (out / "native-model.json").write_text(json.dumps({"resolver": model_class, "expected_sha256": expected}, indent=2))
        attempt("SRV-01/02-modelo-nativo", native_model)

        def checkpoint_integrity():
            url = f"https://huggingface.co/api/models/{MODEL}/revision/{REVISION}?blobs=true"
            with urllib.request.urlopen(url, timeout=30) as r:
                published = json.load(r)
            require(published["sha"] == REVISION, "Revisión publicada inesperada")
            expected = {s["rfilename"]: s["lfs"]["sha256"] for s in published["siblings"] if s["rfilename"].endswith(".safetensors")}
            require(len(expected) == len(runtime["weights"]), "Número de shards distinto del checkpoint publicado")
            for weight in runtime["weights"]:
                require(REVISION in weight["path"], "Pesos de una revisión inesperada")
                require(expected.get(Path(weight["path"]).name) == weight["sha256"], "Hash de pesos distinto del checkpoint publicado")
            (out / "checkpoint-integrity.json").write_text(json.dumps({"revision": REVISION, "sha256": expected}, indent=2))
        attempt("SRV-02-integridad-pesos", checkpoint_integrity)
        if args.with_recovery:
            node = json.loads((out / "node.txt").read_text())
            require(node["spec"]["providerID"].startswith("gce://llmresearch-510422/"), "Proyecto inesperado")
            stop_forward()
            started = time.monotonic()
            print("Recreando pod; serving se interrumpe temporalmente...", flush=True)
            kube("delete-pod", "delete", "pod", pod["metadata"]["name"], "--wait=true")
            deadline = started + args.timeout
            observations = []
            try:
                while time.monotonic() < deadline:
                    items = json.loads(kube("recovery-observation", "get", "pods", "-l",
                                            "app.kubernetes.io/name=vllm", "-o", "json"))["items"]
                    observations.append({"seconds": time.monotonic() - started,
                                         "pods": [{"name": p["metadata"]["name"], "phase": p["status"]["phase"]} for p in items]})
                    require(len(items) <= 1, "Más de un pod observado durante recuperación")
                    if items and items[0]["metadata"]["uid"] != pod["metadata"]["uid"] and any(
                        c["type"] == "Ready" and c["status"] == "True" for c in items[0]["status"].get("conditions", [])):
                        break
                    print(f"Recuperación: {int(time.monotonic() - started)} s", flush=True)
                    time.sleep(5)
                else:
                    raise RuntimeError("Recuperación excedió timeout")
            finally:
                (out / "recovery.json").write_text(json.dumps(observations, indent=2))
            ready_seconds = time.monotonic() - started
            after = snapshot("after")
            require(after[1]["metadata"]["uid"] == pvc["metadata"]["uid"], 'Contrato incumplido: after[1]["metadata"]["uid"] == pvc["metadata"]["uid"]')
            require(after[1]["spec"]["volumeName"] == pvc["spec"]["volumeName"], 'Contrato incumplido: after[1]["spec"]["volumeName"] == pvc["spec"]["volumeName"]')
            require(after[2]["weights"] == runtime["weights"], "Pesos cambiaron: revisar persistencia")
            note("SRV-13/14/15", "PASS", f"Nuevo pod Ready en {ready_seconds:.1f}s; mismo PVC/PV y hashes SHA256 de pesos; muestreo cada 5s")
            attempt("after-API", lambda: sampled_api("after"))
            kube("after-logs", "logs", "deploy/vllm", "--tail=300", "--timestamps")
        else:
            note("SRV-13/14/15-recuperación", "PENDIENTE", "Ejecutar con --with-recovery")
        final = snapshot("final")
        require(all(s.get("restartCount", 0) == 0 for s in final[0]["status"].get("containerStatuses", [])), "Se observaron reinicios")
        note("estabilidad-final", "PASS", "Pod Ready, cero reinicios y PVC Bound al terminar")
    except KeyboardInterrupt:
        note("ejecución", "FAIL", "Interrumpida por el operador; validación incompleta")
    except Exception as exc:
        note("ejecución", "FAIL", str(exc))
    finally:
        stop_forward()
        lines = ["# Validación automatizada de serving", "", "| Comprobación | Estado | Evidencia / límite |",
                 "|---|---|---|"]
        lines += [f"| {name} | {status} | {detail.replace('|', '/')} |" for name, status, detail in results]
        lines += ["", "EVIDENCIA identifica capturas/orquestación; no equivale a aceptar un requisito.",
                  "Calidad: predicados acotados de contenido/formato; no evaluación general del modelo. El resolver se inspecciona en un proceso independiente del servidor.",
                  "Mediciones puntuales no son picos sostenidos; espacio anterior al pull no se puede reconstruir.",
                  "Persistencia compara PVC/PV y hashes SHA256 completos de pesos. Logs y zona del PV requieren revisión. No se elimina infraestructura."]
        (out / "report.md").write_text("\n".join(lines) + "\n")
        (out / "results.json").write_text(json.dumps([{"check": name, "status": status, "detail": detail}
            for name, status, detail in results], ensure_ascii=False, indent=2))
        coverage = []
        for number in range(1, 16):
            identifier = f"SRV-{number:02d}"
            matches = []
            for name, status, detail in results:
                ids = set()
                for found in re.finditer(r"SRV-(\d+)((?:/\d+)*)", name):
                    ids.update(int(n) for n in (found.group(1) + found.group(2)).split("/"))
                if number in ids:
                    matches.append({"check": name, "status": status, "detail": detail})
            status = next((s for s in ("FAIL", "PENDIENTE", "PARCIAL") if any(m["status"] == s for m in matches)),
                          "OBSERVADO" if matches else "PENDIENTE")
            coverage.append({"requirement": identifier, "status": status, "checks": matches,
                             "limit": "Comprobar criterio completo en validation.md; OBSERVADO no declara cierre"})
        (out / "requirements.json").write_text(json.dumps(coverage, ensure_ascii=False, indent=2))
        print(f"\nReporte: {out / 'report.md'}", flush=True)
        print("PARCIAL/PENDIENTE requiere revisión; código de salida 0 no significa entrega terminada.", flush=True)
    if any(status == "FAIL" for _, status, _ in results):
        return 1
    return 2 if any(status in ("PENDIENTE", "PARCIAL") for _, status, _ in results) else 0


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--sdk-base":
        sdk_parser = argparse.ArgumentParser()
        sdk_parser.add_argument("--sdk-base", required=True)
        sdk_parser.add_argument("--sdk-mode", choices=("chat", "stream"), required=True)
        sdk_parser.add_argument("--reasoning", choices=("off", "on"), default="off")
        sdk_parser.add_argument("--max-tokens", type=int, default=128)
        sdk_args = sdk_parser.parse_args()
        configure_requests(sdk_args.reasoning == "on", sdk_args.max_tokens)
        sdk_check(sdk_args.sdk_base, sdk_args.sdk_mode)
    else:
        sys.exit(main())
