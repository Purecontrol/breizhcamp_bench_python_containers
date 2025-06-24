from __future__ import annotations
import concurrent.futures as cf
import os
import tempfile
import time
import threading
from functools import partial
import argparse
from pathlib import Path
import json
from datetime import datetime
import random

def little_io_operation(taille_mo: int = 4) -> None:
    bloc = os.urandom(1*10**6) # 1 mo
    with tempfile.TemporaryFile() as fichier:
        for _ in range(taille_mo):
            fichier.write(bloc)
        fichier.seek(0)
        while fichier.read(1*10**6): # on lit par bloc de 1 mo
            pass

def little_cpu_operation(iterations: int = 50_000) -> int:
    total = 0
    for i in range(iterations):
        total += i * random.randint(-i, i)
    return total

def target_worker(
    taille_mo: int,
    nb_ops_io: int,
    nb_threads_io: int,
    iterations_cpu: int) -> None:
    with cf.ThreadPoolExecutor(max_workers=nb_threads_io) as pool_io:
        futurs_io = [pool_io.submit(little_io_operation, taille_mo) for _ in range(nb_ops_io)]
        for fut in cf.as_completed(futurs_io):
            fut.result()
    little_cpu_operation(iterations_cpu)

def tasks_producer(
        executor: cf.ProcessPoolExecutor,
        task,
        future_set: set[cf.Future],
        stop_event: threading.Event,
        max_tasks_waiting: int
        ) -> None:
    while not stop_event.is_set():
        deficit = max_tasks_waiting - len(future_set)
        for _ in range(deficit):
            futur = executor.submit(task)
            future_set.add(futur)
        time.sleep(0.5)

def start_bench(time_duration: int,
                       target_task,
                       nb_proc: int,
                       max_tasks_waiting: int) -> int:
    tasks_suceeded = 0
    stop_event  = threading.Event()
    futures: set[cf.Future] = set()

    with cf.ProcessPoolExecutor(max_workers=nb_proc) as pool_proc:
        tasks_producer_thread = threading.Thread(target=tasks_producer,
                                    args=(pool_proc, target_task, futures,
                                          stop_event, max_tasks_waiting),
                                    daemon=True)
        tasks_producer_thread.start()
        time_limit = time.perf_counter() + time_duration

        while True:
            done, _ = cf.wait(futures,
                               timeout=0.25,
                               return_when=cf.FIRST_COMPLETED)

            for fut in done:
                fut.result()
                tasks_suceeded += 1
                futures.discard(fut)

            if time.perf_counter() >= time_limit:
                stop_event.set()
                pool_proc.shutdown(wait=False, cancel_futures=True)
                break

        tasks_producer_thread.join()
    return tasks_suceeded

def load_conf(path: Path | None) -> dict:
    if path and path.is_file():
        with path.open() as f:
            return json.load(f)
    return {
        "duration_sec":       240,
        "size_mo":            4,
        "nb_ops_io":          8,
        "nb_threads_io":      8,
        "iterations_cpu":     50_000,
        "nb_proc":            os.cpu_count() or 4,
        "max_task_wait_mult": 50
    }
    
def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark python images.")
    parser.add_argument("-c", "--config", type=Path,
                        help="json configuration file.")
    args = parser.parse_args()

    image_name  = os.getenv("IMAGE_NAME",  "unknown")
    results_dir = Path(os.getenv("RESULTS_DIR", "/results"))

    cfg = load_conf(args.config)
    max_wait = cfg["nb_proc"] * cfg["max_task_wait_mult"]
    print("loaded parameters :", cfg, f"(max_tasks_waiting={max_wait})", sep="\n")

    task = partial(target_worker,
                   cfg["size_mo"], cfg["nb_ops_io"],
                   cfg["nb_threads_io"], cfg["iterations_cpu"])

    total = start_bench(cfg["duration_sec"], task, cfg["nb_proc"], max_wait)
    tpm   = total / (cfg["duration_sec"] / 60)

    results_dir.mkdir(parents=True, exist_ok=True)
    stamp  = datetime.now().isoformat(timespec="seconds").replace(":", "-")
    fname  = f"{stamp}_{image_name}.json"
    out    = results_dir / fname

    output_data = {
        "timestamp":       stamp,
        "image":           image_name,
        "duration_s":      cfg["duration_sec"],
        "tasks":           total,
        "tasks_per_min":   tpm,
        "size_mo":         cfg["size_mo"],
        "nb_ops_io":       cfg["nb_ops_io"],
        "nb_threads_io":   cfg["nb_threads_io"],
        "iterations_cpu":  cfg["iterations_cpu"],
        "nb_proc":         cfg["nb_proc"],
    }
    out.write_text(json.dumps(output_data, indent=2))
    print(f"\nRESULT ({image_name}) : {total} tasks → {tpm:.2f} tasks/min")
    print(f"↪ results written in {out}")

if __name__ == "__main__":
    main()
