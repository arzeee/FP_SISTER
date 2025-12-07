import redis
import time

# Koneksi
master = redis.Redis(host='localhost', port=6379, decode_responses=True)
replica = redis.Redis(host='localhost', port=6380, decode_responses=True)

print("--- MODE EKSTRIM: Pipeline Batch Write ---")

# Kita akan kirim 10 batch, masing-masing 10.000 data
batches = 10
batch_size = 1000
lag_detected = 0

start_time = time.time()

for b in range(batches):
    print(f"Mengirim Batch {b+1}...")
    pipe = master.pipeline()
    
    # 1. Tumpuk 10.000 perintah SET di memori
    for i in range(batch_size):
        key = f"batch{b}_key{i}"
        pipe.set(key, "data_berat")
    
    # 2. TEMBAKKAN SEMUA SEKALIGUS KE MASTER!
    pipe.execute()
    
    # 3. Langsung cek data TERAKHIR di Replica
    # Kita balapan: Siapa lebih cepat? Replikasi Redis atau Read Python?
    last_key = f"batch{b}_key{batch_size-1}"
    try:
        val = replica.get(last_key)
        if val is None:
            print(f"  [!] LAG TERDETEKSI di Batch {b+1}: Data belum sampai di Replica!")
            lag_detected += 1
    except Exception as e:
        print(e)

end_time = time.time()
print(f"\nSelesai dalam {end_time - start_time:.2f} detik.")
print(f"Total Write: {batches * batch_size}")
print(f"Kejadian Lag: {lag_detected} dari {batches} batch percobaan.")

if lag_detected == 0:
    print("\nKesimpulan: Wow, laptopmu terlalu ngebut! Network local-nya sangat stabil.")
else:
    print("\nKesimpulan: Terbukti! Ada jeda waktu (latency) antara Master menerima data dan Replica menyalinnya.")