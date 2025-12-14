import time
import sys
import threading
from datetime import datetime
from redis.sentinel import Sentinel
from redis.exceptions import ConnectionError, ReadOnlyError, TimeoutError

# --- Konfigurasi ---
# Ganti 'localhost' dengan nama container sentinel
SENTINEL_NODES = [
    ('redis-sentinel-1', 26379),
    ('redis-sentinel-2', 26379),
    ('redis-sentinel-3', 26379)
]
SERVICE_NAME = 'mymaster'

# Setup Sentinel Connection
sentinel = Sentinel(
    SENTINEL_NODES,
    socket_timeout=0.5
)

stop_event = threading.Event()

def get_time():
    """Mengambil waktu saat ini dengan presisi milidetik"""
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]

# ============================================================
#  THREAD: Monitor Leader Election
# ============================================================
def monitor_leader():
    last_master = None
    print(f"[{get_time()}] [MONITOR] Memulai monitor Master...")

    while not stop_event.is_set():
        try:
            master_addr = sentinel.discover_master(SERVICE_NAME)
            current_master = f"{master_addr[0]}:{master_addr[1]}"

            if current_master != last_master:
                if last_master:
                    # Mencetak Timestamp saat Sentinel sadar ada perubahan
                    print(f"\n[{get_time()}] [EVENT] 🚨 FAILOVER TERDETEKSI OLEH SENTINEL!")
                    print(f"[{get_time()}] [EVENT] 🔄 Master berubah: {last_master} → {current_master}")
                else:
                    print(f"[{get_time()}] [INFO] Master awal: {current_master}")

                last_master = current_master

        except Exception as e:
            # print(f"\n[{get_time()}] [MONITOR] Gagal menghubungi Sentinel: {e}")
            pass

        time.sleep(1)

# ============================================================
#   Koneksi Master Fresh
# ============================================================
def get_master_conn():
    return sentinel.master_for(SERVICE_NAME, socket_timeout=0.5)

# ============================================================
#  THREAD: Continuous Writer
# ============================================================
def continuous_writer():
    i = 0
    fail_count = 0
    
    # Flag untuk menandai apakah kita sedang dalam kondisi 'sukses' atau 'gagal'
    # agar log tidak spamming
    last_state_was_success = True 

    print(f"[{get_time()}] [WRITER] Mulai menulis data...")

    while not stop_event.is_set():
        try:
            master = get_master_conn()
            key = f"failover_test_{i}"
            value = f"data_{i}"

            master.set(key, value)

            # --- LOGIKA LOGGING SUCCESS ---
            if not last_state_was_success:
                # Jika sebelumnya gagal dan sekarang berhasil, berarti PULIH
                print(f"\n[{get_time()}] [WRITER] ✅ SUKSES MENULIS KEMBALI! (Sistem Pulih)")
                fail_count = 0
            
            last_state_was_success = True
            
            sys.stdout.write(".")
            sys.stdout.flush()

        except (ConnectionError, TimeoutError):
            # --- LOGIKA LOGGING FAILURE ---
            if last_state_was_success:
                # Jika sebelumnya sukses dan sekarang gagal, ini AWAL DOWNTIME
                print(f"\n[{get_time()}] [WRITER] ❌ GAGAL MENULIS! (Awal Downtime - Master Mati)")
                last_state_was_success = False

            sys.stdout.write("X")
            sys.stdout.flush()
            fail_count += 1
            time.sleep(0.5) # Jeda sedikit saat error agar tidak flooding

        except ReadOnlyError:
            print(f"\n[{get_time()}] [WRITER] ⚠️ Read Only (Replica). Menunggu master baru...")
            time.sleep(1)

        except Exception as e:
            print(f"\n[{get_time()}] [WRITER] ERROR: {e}")

        i += 1
        time.sleep(0.4) # Normal delay

# ============================================================
#   MAIN
# ============================================================
if __name__ == "__main__":
    print("--- Redis Sentinel Failover Test (Time Stamp Version) ---")
    
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
        print("Selesai.")
