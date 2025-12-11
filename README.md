# SKENARIO 1
## 1. Jalankan Container
docker-compose -f docker-compose-replication.yml up -d

## 2. Jalankan Script Pengujian
python3 test_lag.py

atau

python3 test_lag_extreme.py

## 3. Bersihkan
docker-compose -f docker-compose-replication.yml down


# SKENARIO 2
## 1. Persiapan Config (Wajib reset jika mengulang)
rm sentinel.conf
nano sentinel.conf # (Paste konfigurasi default)
```
port 26379
dir /tmp
sentinel monitor mymaster redis-master 6379 2
sentinel auth-pass mymaster password123
sentinel down-after-milliseconds mymaster 5000
sentinel failover-timeout mymaster 5000
sentinel parallel-syncs mymaster 1
```

## 2. Jalankan Container
docker-compose -f docker-compose-sentinel.yml up -d

## 3. Monitoring (Buka di terminal baru)
docker logs -f sentinel-1

## 4. Simulasi Crash (Buka di terminal lain)
docker stop redis-master

## 5. Verifikasi Master Baru
docker exec -it sentinel-1 redis-cli -p 26379 sentinel get-master-addr-by-name mymaster
