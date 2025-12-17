import redis
from redis.cluster import RedisCluster as Redis
import time
import sys

# --- KONFIGURASI ---
STARTUP_NODES = [{"host": "redis-node-1", "port": "6379"}]
TOTAL_KEYS = 10000

# Fungsi helper log
def log_terminal(pesan):
    print(f"[LOG] {pesan}")

print("\n")
print("SKENARIO 3: TESTING REDIS CLUSTER SHARDING")
print("(Internal Network Mode)")
print("\n")

try:
    # 1. conect ke cluster
    log_terminal("Menghubungkan ke Redis Cluster")
    
    rc = Redis(
        host='redis-node-1', 
        port=6379, 
        decode_responses=True
    )
    
    if rc.ping():
        log_terminal("Terhubung ke Cluster!")

    # 2. masukin data
    print("\n")
    log_terminal(f"Memulai proses insert {TOTAL_KEYS} data dummy...")
    start_time = time.time()
    
    pipe = rc.pipeline()
    for i in range(TOTAL_KEYS):
        key = f"key{i}"
        value = f"value_for_{i}"
        pipe.set(key, value)
        
        if (i + 1) % 1000 == 0:
            pipe.execute()
            log_terminal(f"Progress: {i+1} data berhasil masuk...")
            
    pipe.execute()
    
    end_time = time.time()
    durasi = end_time - start_time
    log_terminal(f"INSERT SELESAI dalam {durasi:.2f} detik.")

    # 3. cek sharding (distribusi)
    print("\n")
    log_terminal("Menganalisis penyebaran data (Sharding)...")
    log_terminal("Sedang mengecek lokasi slot setiap key...")
    
    node_counts = {}
    
    for i in range(TOTAL_KEYS):
        key = f"key{i}"
        slot = rc.cluster_keyslot(key)
        
        if slot < 5461:
            node_name = "Master 1 (redis-node-1)"
        elif slot < 10923:
            node_name = "Master 2 (redis-node-2)"
        else:
            node_name = "Master 3 (redis-node-3)"
            
        node_counts[node_name] = node_counts.get(node_name, 0) + 1

    # 4. tampilkan hasil log sharding
    print("\n" + "="*70)
    print(f"{'NODE MASTER':<25} | {'JUMLAH KEY':<12} | {'PERSENTASE'}")
    print("-" * 70)
    
    for node, count in sorted(node_counts.items()):
        percentage = (count / TOTAL_KEYS) * 100
        print(f"{node:<25} | {count:<12} | {percentage:.2f}%")
        
    print("=" * 70)
    
    # 5. Log topologi cluster
    print("\n")
    print(f"DETAIL TOPOLOGI CLUSTER (MASTER & REPLICA)")

    # Ambil raw nodes dictionary
    nodes_dict = rc.cluster_nodes()
    
    nodes_info = []
    
    # PARSING BERDASARKAN HASIL DEBUG
    for addr, data in nodes_dict.items():
        # Pisahkan IP dari Port (172.18.0.6:6379 -> 172.18.0.6)
        ip_address = addr.split(':')[0]
        # Masukkan IP ini ke dalam data object agar mudah diakses
        data['extracted_ip'] = ip_address
        
        # Pastikan node_id diambil dari field yang benar (debug: key-nya adalah 'node_id')
        if 'node_id' not in data:
             data['node_id'] = "Unknown"
             
        nodes_info.append(data)
    
    # Filter Master dan Replica
    masters = [n for n in nodes_info if 'master' in n['flags']]
    replicas = [n for n in nodes_info if 'slave' in n['flags']]
    
    # Urutkan master berdasarkan slot awal
    masters.sort(key=lambda x: x.get('slots', [[0,0]])[0][0] if x.get('slots') else 99999)

    print(f"{'MASTER IP':<15} | {'SLOT RANGE':<15} | {'REPLICA IP':<15} | {'STATUS'}")
    print("-" * 70)

    for m in masters:
        master_ip = m['extracted_ip']
        master_id = m['node_id']
        
        # Format Slot Range
        slots = m.get('slots', [])
        slot_str = "-"
        if slots:
            start = slots[0][0]
            end = slots[0][1]
            slot_str = f"{start}-{end}"
            
        # Cari Replica dan mencocokkan replica['master_id'] dengan master['node_id']
        my_replicas = [
            r for r in replicas 
            if r.get('master_id') == master_id
        ]
        
        if not my_replicas:
            replica_ips = "NONE"
        else:
            replica_ips = ", ".join([r['extracted_ip'] for r in my_replicas])
        
        print(f"{master_ip:<15} | {slot_str:<15} | {replica_ips:<15} | OK")

    print("=" * 70)
    log_terminal("Log Topologi & Replica selesai ditampilkan.")

except Exception as e:
    print("\n[ERROR FATAL]")
    print(f"Pesan Error: {e}")
    import traceback
    traceback.print_exc()
