import time
import sys
import threading
from redis.sentinel import Sentinel
from redis.exceptions import ConnectionError, ReadOnlyError, TimeoutError

# --- Konfigurasi ---
SENTINEL_NODES = [
    ('localhost', 26379),
    ('localhost', 26380),
    ('localhost', 26381)
]
SERVICE_NAME = 'mymaster'

# Setup Sentinel Connection (KOMPATIBEL)
sentinel = Sentinel(
    SENTINEL_NODES,
    socket_timeout=0.5
)

stop_event = threading.Event()


# ============================================================
#  THREAD: Monitor Leader Election
# ============================================================
def monitor_leader():
    last_master = None
    print("[MONITOR] Memulai monitor Master...")

    while not stop_event.is_set():
        try:
            master_addr = sentinel.discover_master(SERVICE_NAME)
            current_master = f"{master_addr[0]}:{master_addr[1]}"

            if current_master != last_master:
                if last_master:
                    print(f"\n[EVENT] 🚨 FAILOVER TERDETEKSI!")
                    print(f"[EVENT] 🔄 Master berubah: {last_master} → {current_master}")
                    print("[EVENT] 🗳️  Leader Election Selesai.\n")
                else:
                    print(f"[INFO] Master awal: {current_master}")

                last_master = current_master

        except Exception as e:
            print(f"[MONITOR] Gagal menghubungi Sentinel: {e}")

        time.sleep(1)


# ============================================================
#   Koneksi Master Fresh (Tanpa Cache)
# ============================================================
def get_master_conn():
    """Selalu dapat koneksi master baru tanpa cache."""
    return sentinel.master_for(
        SERVICE_NAME,
        socket_timeout=0.5,
    )


# ============================================================
#  THREAD: Continuous Writer
# ============================================================
def continuous_writer():
    i = 0
    fail_count = 0

    print("[WRITER] Mulai menulis data...")

    while not stop_event.is_set():

        try:
            master = get_master_conn()
            key = f"failover_test_{i}"
            value = f"data_{i}"

            master.set(key, value)

            sys.stdout.write(".")
            sys.stdout.flush()
            fail_count = 0

        except (ConnectionError, TimeoutError):
            sys.stdout.write("X")
            sys.stdout.flush()

            if fail_count == 0:
                print("\n[WRITER] ⚠️ Write gagal! Master mungkin down. Menunggu failover...")

            fail_count += 1
            time.sleep(1)

        except ReadOnlyError:
            print("\n[WRITER] ⚠️ Replica detected! Menunggu master baru...\n")
            time.sleep(1)

        except Exception as e:
            print(f"\n[WRITER] ERROR: {e}")

        i += 1
        time.sleep(0.4)


# ============================================================
#   MAIN
# ============================================================
if __name__ == "__main__":
    print("--- Redis Sentinel Failover Test ---")
    print("1. Biarkan script ini berjalan.")
    print("2. Matikan container master:  docker stop redis-master")
    print("3. Perhatikan tanda '.' dan 'X' serta event failover.")
    print("------------------------------------")

    t_monitor = threading.Thread(target=monitor_leader, daemon=True)
    t_writer = threading.Thread(target=continuous_writer, daemon=True)

    t_monitor.start()
    t_writer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        stop_event.set()
        t_monitor.join()
        t_writer.join()
        print("Selesai.")
