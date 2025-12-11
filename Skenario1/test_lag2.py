import redis
import time
import threading
from queue import Queue

# --- Konfigurasi ---
HOST = 'localhost'
MASTER_PORT = 6379
REPLICA_PORT_1 = 6380
REPLICA_PORT_2 = 6381
TOTAL_OPERATIONS = 10000 # Jumlah total operasi Tulis-Baca

# Koneksi Redis
master = redis.Redis(host=HOST, port=MASTER_PORT, decode_responses=True)
replica1 = redis.Redis(host=HOST, port=REPLICA_PORT_1, decode_responses=True)
replica2 = redis.Redis(host=HOST, port=REPLICA_PORT_2, decode_responses=True)

# Variabel Global untuk hasil dan sinkronisasi
results = {
    'missed_reads_r1': 0,
    'missed_reads_r2': 0,
    'total_processed_reads': 0
}
write_read_queue = Queue() 
results_lock = threading.Lock() 

# --- Fungsi Thread Write (Master) ---
def write_to_master(num_operations):
    
    print(f"\n[{threading.current_thread().name}] Memulai {num_operations} operasi TULIS ke Master...")
    
    for i in range(num_operations):
        key = f"kunci_{i}"
        value = f"nilai_{i}"

        # Operasi TULIS ke Master
        master.set(key, value)
        
        # DEBUG: Cetak kunci yang baru saja ditulis
        print(f"[{threading.current_thread().name}] TULIS #{i}: Set '{key}' ke Master (6379)")
        
        # Antrikan kunci untuk dibaca oleh thread Read
        write_read_queue.put(key)
        
    print(f"\n[{threading.current_thread().name}] Selesai TULIS.")
    write_read_queue.put(None) # Sinyal penghentian

# --- Fungsi Thread Read (Replica 1 & 2) ---
def read_from_replicas():
    global results
    
    print(f"\n[{threading.current_thread().name}] Memulai operasi BACA dari KEDUA Replica...")
    
    while True:
        key_to_read = write_read_queue.get()
        
        if key_to_read is None:
            write_read_queue.task_done()
            break
            
        # DEBUG: Cetak kunci yang akan dibaca
        print(f"[{threading.current_thread().name}] BACA: Mencoba baca '{key_to_read}' dari kedua Replika.")

        # --- 1. BACA dari REPLICA 1 (6380) ---
        read_val_r1 = replica1.get(key_to_read)
        
        # --- 2. BACA dari REPLICA 2 (6381) ---
        read_val_r2 = replica2.get(key_to_read)
        
        # --- Pencatatan Hasil dan Debug Akhir ---
        status_r1 = "DITEMUKAN" if read_val_r1 is not None else "GAGAL (LAG)"
        status_r2 = "DITEMUKAN" if read_val_r2 is not None else "GAGAL (LAG)"
        
        # DEBUG: Cetak hasil baca dari kedua replika
        print(f"[{threading.current_thread().name}] HASIL '{key_to_read}': R1(6380) -> {status_r1} | R2(6381) -> {status_r2}")
        
        with results_lock:
            if read_val_r1 is None:
                results['missed_reads_r1'] += 1
            
            if read_val_r2 is None:
                results['missed_reads_r2'] += 1
                
            results['total_processed_reads'] += 1
            
        write_read_queue.task_done()
            
    print(f"\n[{threading.current_thread().name}] Selesai BACA. Total dibaca: {results['total_processed_reads']}.")


# --- Main Program ---
if __name__ == "__main__":
    try:
        master.flushdb()
    except redis.exceptions.ConnectionError:
        print("🚨 Koneksi Redis Gagal. Pastikan Docker Compose Anda berjalan!")
        exit()

    print("--- Memulai Skenario Multi-Replica Eventual Consistency Test (dengan Debug) ---")
    
    start_time = time.time()

    # Inisialisasi Threads
    write_thread = threading.Thread(
        target=write_to_master, 
        args=(TOTAL_OPERATIONS,), 
        name="WriterThread"
    )
    
    read_thread = threading.Thread(
        target=read_from_replicas,
        name="ReaderThread"
    )

    # Memulai Threads
    write_thread.start()
    read_thread.start()

    # Menunggu Threads selesai
    write_thread.join()
    read_thread.join()

    end_time = time.time()

    # --- Hasil ---
    print("\n--- Hasil Uji Coba Konkurensi Multi-Replica ---")
    print(f"Waktu total eksekusi: {end_time - start_time:.4f} detik.")
    print(f"Total Write ke Master: {TOTAL_OPERATIONS}")
    print(f"Total Baca yang Diproses: {results['total_processed_reads']}")
    print("--------------------------------------------------")
    print(f"Lag pada **Replica 1 (6380)**: {results['missed_reads_r1']} kunci gagal dibaca.")
    print(f"Lag pada **Replica 2 (6381)**: {results['missed_reads_r2']} kunci gagal dibaca.")
    print("--------------------------------------------------")

    if results['missed_reads_r1'] == 0 and results['missed_reads_r2'] == 0:
        print("✅ Kesimpulan: Replikasi sangat cepat (Strong Consistency terlihat) pada kedua replika.")
    else:
        print("⚠️ Kesimpulan: Terjadi Eventual Consistency pada salah satu atau kedua replika.")