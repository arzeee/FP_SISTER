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

# Setup Sentinel Connection
sentinel = Sentinel(SENTINEL_NODES, socket_timeout=0.5)

stop_event = threading.Event()

def monitor_leader():
    """Thread untuk memantau siapa Leader/Master saat ini"""
    last_master = None
    while not stop_event.is_set():
        try:
            # Bertanya ke Sentinel: Siapa master dari 'mymaster'?
            master_addr = sentinel.discover_master(SERVICE_NAME)
            current_master = f"{master_addr[0]}:{master_addr[1]}"
            
            if current_master != last_master:
                if last_master is not None:
                    print(f"\n[EVENT] 🚨 FAILOVER DETECTED! Master berubah dari {last_master} ke {current_master}")
                    print(f"[EVENT] 🗳️  Leader Election Selesai.\n")
                else:
                    print(f"[INFO] Master awal terdeteksi: {current_master}")
                last_master = current_master
                
        except Exception as e:
            print(f"[MONITOR] Gagal menghubungi Sentinel: {e}")
        
        time.sleep(1)

def continuous_writer():
    """Thread untuk mencoba menulis data terus menerus"""
    i = 0
    fail_count = 0
    
    print("[WRITER] Memulai penulisan data...")
    
    while not stop_event.is_set():
        try:
            # Minta koneksi Master terbaru dari Sentinel
            master = sentinel.master_for(SERVICE_NAME, socket_timeout=0.5)
            
            key = f"failover_test_{i}"
            value = f"data_{i}"
            
            # Coba Tulis
            master.set(key, value)
            
            # Jika berhasil
            sys.stdout.write(".") # Indikator sukses (titik)
            sys.stdout.flush()
            fail_count = 0 # Reset fail count jika sukses
            
        except (ConnectionError, TimeoutError):
            # Ini terjadi saat Master MATI dan Sentinel belum mempromosikan Master baru
            sys.stdout.write("X") # Indikator gagal (X)
            sys.stdout.flush()
            fail_count += 1
            if fail_count == 1:
                 print(f"\n[WRITER] ⚠️ Gagal menulis! Master mungkin down. Menunggu failover...")
        except ReadOnlyError:
             print(f"\n[WRITER] ⚠️ Read Only! Anda mungkin terhubung ke Replica, bukan Master.")
        except Exception as e:
            print(f"\n[WRITER] Error lain: {e}")
            
        i += 1
        time.sleep(0.5) # Jeda penulisan

if __name__ == "__main__":
    print("--- Skenario 2: Redis Sentinel Failover Test ---")
    print("Instruksi:")
    print("1. Biarkan script ini berjalan.")
    print("2. Buka terminal lain, matikan master dengan: 'docker stop redis-master'")
    print("3. Amati output 'X' (gagal tulis) dan notifikasi Failover.")
    print("------------------------------------------------")

    t_monitor = threading.Thread(target=monitor_leader)
    t_writer = threading.Thread(target=continuous_writer)

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