import redis
from redis.cluster import RedisCluster as Redis
from redis.exceptions import RedisError
import time
import sys

# --- KONFIGURASI ---
# Daftar node yang akan dicoba dihubungi satu per satu,penting agar script tetap jalan meski Node 1 mati (Failover Test)
STARTUP_NODES = [
    {"host": "redis-node-1", "port": 6379},
    {"host": "redis-node-2", "port": 6379},
    {"host": "redis-node-3", "port": 6379}
]
TOTAL_KEYS = 10000

# Fungsi helper log
def log_terminal(pesan):
    print(f"[LOG] {pesan}")

print("   SKENARIO 3: TESTING REDIS CLUSTER SHARDING")
print("   (Auto-Failover Support Version)")

rc = None

try:
    
    # 1. KONEKSI KE CLUSTER (DENGAN FAILOVER)   
    log_terminal("Mencoba menghubungkan ke Redis Cluster...")
    
    connected_node = None
    
    # Loop untuk mencari node yang hidup
    for node in STARTUP_NODES:
        try:
            temp_host = node['host']
            print(f"Mencoba connect ke {temp_host}...", end=" ")
            
            # Coba koneksi
            rc = Redis(host=temp_host, port=6379, decode_responses=True)
            
            # Cek apakah benar-benar tersambung
            if rc.ping():
                print("BERHASIL!")
                connected_node = temp_host
                break
        except Exception:
            print("GAGAL (Node mungkin mati/unreachable)")
            continue
            
    if not connected_node:
        raise Exception("Semua node startup tidak bisa dihubungi. Pastikan Cluster jalan!")

    log_terminal(f"Terhubung via entry point: {connected_node}")

    
    # 2. INSERT DATA (SIMULASI BEBAN)
    log_terminal(f"Memulai proses insert {TOTAL_KEYS} data dummy...")
    start_time = time.time()
    
    try:
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
        
    except RedisError as e:
        log_terminal(f"Warning Insert: Sebagian data mungkin gagal karena failover sedang terjadi.")
        log_terminal(f"Pesan Error Redis: {e}")

    
    # 3. CEK DISTRIBUSI KEY (LOGIKA SHARDING)
    log_terminal("Menganalisis penyebaran data (Sharding)...")
    
    node_counts = {}
    
    for i in range(TOTAL_KEYS):
        key = f"key{i}"
        # Menggunakan exception handler in-case node sedang down saat query
        try:
            slot = rc.cluster_keyslot(key)
            
            if slot < 5461:
                node_name = "Master 1 (Range 0-5460)"
            elif slot < 10923:
                node_name = "Master 2 (Range 5461-10922)"
            else:
                node_name = "Master 3 (Range 10923-16383)"
        except:
            node_name = "Unknown/Error"
            
        node_counts[node_name] = node_counts.get(node_name, 0) + 1

    # Tampilkan Tabel Sharding
    print("\n" + "="*70)
    print(f"{'NODE MASTER':<30} | {'KEY':<8} | {'PERSENTASE'}")
    print("-" * 70)
    
    for node, count in sorted(node_counts.items()):
        percentage = (count / TOTAL_KEYS) * 100
        print(f"{node:<30} | {count:<8} | {percentage:.2f}%")
        
    print("=" * 70)
    

    # 4. CEK TOPOLOGI (MASTER & REPLICA)
    print("\n" + "="*70)
    print(f"{'DETAIL TOPOLOGI CLUSTER (HIGH AVAILABILITY CHECK)':^70}")
    print("="*70)
    
    nodes_dict = rc.cluster_nodes()
    nodes_info = []
    
    for addr, data in nodes_dict.items():
        # Ambil IP bersih
        ip_address = addr.split(':')[0]
        data['extracted_ip'] = ip_address
        
        if 'node_id' not in data:
             data['node_id'] = "Unknown"
        nodes_info.append(data)
    
    masters = [n for n in nodes_info if 'master' in n['flags']]
    replicas = [n for n in nodes_info if 'slave' in n['flags']]
    
    # Fungsi helper untuk memastikan slot selalu dianggap Integer saat sorting
    def get_slot_start(node_data):
        slots = node_data.get('slots', [])
        # Jika node mati/fail, dia tidak punya slots -> return angka gede
        if not slots:
            return 999999 
        
        try:
            # Slot biasanya list of list [[start, end]]. Ambil start-nya. paksa cast ke int() karena decode_responses=True bikin dia jadi string
            return int(slots[0][0])
        except (ValueError, TypeError, IndexError):
            return 999999

    # Gunakan fungsi helper untuk sorting
    masters.sort(key=get_slot_start)

    print(f"{'MASTER IP':<15} | {'SLOT RANGE':<15} | {'REPLICA IP (BACKUP)':<25} | {'STATUS'}")
    print("-" * 70)

    for m in masters:
        master_ip = m['extracted_ip']
        master_id = m['node_id']
        master_flags = m.get('flags', [])
        
        # Cek status Master
        status_str = "OK"
        if 'fail' in master_flags or 'fail?' in master_flags:
            status_str = "FAIL"
        
        # Format Slot Range
        slots = m.get('slots', [])
        slot_str = "-"
        if slots:
            try:
                # Pastikan display slot juga aman
                start = slots[0][0]
                end = slots[0][1]
                slot_str = f"{start}-{end}"
            except:
                slot_str = "Error fmt"
            
        # Cari Replica
        my_replicas = [r for r in replicas if r.get('master_id') == master_id]
        
        if not my_replicas:
            replica_ips = "NONE"
        else:
            replica_ips = ", ".join([r['extracted_ip'] for r in my_replicas])
        
        print(f"{master_ip:<15} | {slot_str:<15} | {replica_ips:<25} | {status_str}")

    print("=" * 70)
    log_terminal("Validasi Selesai.")

except Exception as e:
    print("\n[ERROR FATAL]")
    print(f"Pesan Error: {e}")
    import traceback
    traceback.print_exc()