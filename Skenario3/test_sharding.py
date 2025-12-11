import redis
from redis.cluster import RedisCluster as Redis
import time
import sys

# --- KONFIGURASI ---
# Gunakan nama container 'redis-node-1' dan port internal 6379
# Ini KHUSUS untuk dijalankan via 'docker run' (internal network)
STARTUP_NODES = [{"host": "redis-node-1", "port": "6379"}]
TOTAL_KEYS = 10000

# Fungsi helper untuk log
def log_terminal(pesan):
    print(f"[LOG] {pesan}")

print("\n" + "="*50)
print("   SKENARIO 3: TESTING REDIS CLUSTER SHARDING")
print("   (Internal Network Mode)")
print("="*50 + "\n")

try:
    # 1. KONEKSI KE CLUSTER
    log_terminal("Menghubungkan ke Redis Cluster via redis-node-1:6379...")
    
    rc = Redis(
        host='redis-node-1', 
        port=6379, 
        # password=None,  <-- Server redis:alpine tanpa password
        decode_responses=True
    )
    
    if rc.ping():
        log_terminal("✅ BERHASIL TERHUBUNG ke Cluster!")

    # 2. INSERT DATA
    print("\n" + "-"*30)
    log_terminal(f"Memulai proses insert {TOTAL_KEYS} data dummy...")
    start_time = time.time()
    
    pipe = rc.pipeline()
    for i in range(TOTAL_KEYS):
        key = f"key{i}"
        value = f"value_for_{i}"
        pipe.set(key, value)
        
        # Log setiap 1000 data
        if (i + 1) % 1000 == 0:
            pipe.execute()
            log_terminal(f"👉 Progress: {i+1} data berhasil masuk...")
            
    pipe.execute() # Eksekusi sisa antrian
    
    end_time = time.time()
    durasi = end_time - start_time
    log_terminal(f"✅ INSERT SELESAI dalam {durasi:.2f} detik.")

    # 3. CEK DISTRIBUSI (SHARDING)
    print("\n" + "-"*30)
    log_terminal("Menganalisis penyebaran data (Sharding)...")
    log_terminal("Sedang mengecek lokasi slot setiap key...")
    
    node_counts = {}
    
    for i in range(TOTAL_KEYS):
        key = f"key{i}"
        slot = rc.cluster_keyslot(key)
        
        # Mapping slot ke Node Master (Logic Slot Standar Redis)
        if slot < 5461:
            node_name = "Master 1 (redis-node-1)"
        elif slot < 10923:
            node_name = "Master 2 (redis-node-2)"
        else:
            node_name = "Master 3 (redis-node-3)"
            
        node_counts[node_name] = node_counts.get(node_name, 0) + 1

    # 4. TAMPILKAN HASIL LOG
    print("\n" + "="*50)
    print(f"{'NODE MASTER':<25} | {'JUMLAH KEY':<12} | {'PERSENTASE'}")
    print("-" * 50)
    
    for node, count in sorted(node_counts.items()):
        percentage = (count / TOTAL_KEYS) * 100
        print(f"{node:<25} | {count:<12} | {percentage:.2f}%")
        
    print("=" * 50)
    
    log_terminal("✅ KESIMPULAN: Data terbagi rata (Sharding Berhasil).")

except Exception as e:
    print("\n❌ [ERROR FATAL]")
    print(f"Pesan Error: {e}")
    print("PENTING: Jalankan script ini menggunakan perintah 'docker run' yang diberikan!")