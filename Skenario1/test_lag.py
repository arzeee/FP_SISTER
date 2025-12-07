import redis
import time

# Koneksi ke Master (Port 6379) dan Replica (Port 6380)
master = redis.Redis(host='localhost', port=6379, decode_responses=True)
replica = redis.Redis(host='localhost', port=6380, decode_responses=True)

print("--- Memulai Skenario 1: 1000 Writes ---")

missed_keys = 0
total_keys = 100000

start_time = time.time()

for i in range(total_keys):
    key = f"kunci_{i}"
    value = f"nilai_{i}"

    # 1. Tulis ke Master
    master.set(key, value)

    # 2. LANGSUNG baca dari Replica (tanpa jeda)
    # Ini untuk mengecek "Eventual Consistency"
    read_val = replica.get(key)

    if read_val is None:
        missed_keys += 1

end_time = time.time()

print(f"Selesai dalam {end_time - start_time:.2f} detik.")
print(f"Total Write: {total_keys}")
print(f"Gagal terbaca langsung di Replica (Lag): {missed_keys}")

if missed_keys == 0:
    print("Kesimpulan: Replikasi sangat cepat (Strong Consistency terlihat), karena berjalan di satu mesin lokal.")
else:
    print("Kesimpulan: Terjadi Eventual Consistency. Ada delay replikasi.")