# SKENARIO 1
## 1. Jalankan Container
```
docker-compose -f docker-compose-replication.yml up -d
```

## 2. Jalankan Script Pengujian
```
python3 test_lag.py
```

atau

```
python3 test_lag_extreme.py
```

## 3. Bersihkan
```
docker-compose -f docker-compose-replication.yml down
```

# SKENARIO 2

## Jalankan Container
```
docker-compose -f docker-compose-sentinel.yml up -d
```

## Masuk ke Network Container
```
docker run -it --rm --network skenario2_redisnet -v "$PWD":/app -w /app python:3.9-slim bash
```

## Install redis
```
pip install redis
```

## Jalankan Python
```
python scenario2_failover.py
```

## Buka terminal lain dan matikan master
```
docker stop redis-master
```

# SKENARIO 3

## Jalankan Container
```
docker-compose -f docker-compose-cluster.yml up -d
```

## Cek Cluster
```
docker exec -it redis-node-1 redis-cli cluster nodes
```

## Jalankan untuk buat cluster
```
./init_cluster.sh
```

## Jalanin Test
```
docker run -it --rm   --network skenario3_redis-cluster-net   -v "$PWD":/app   -w /app   python:3.9-slim   sh -c "pip install redis && python test_sharding.py"
```

## Test Failover (Jika Master1 mati)
### Matikan Node 1
```
docker stop redis-node-1
```
### lalu cek node1 haruse mati dan replika node1 (biasanya node5) dia jadi master
```
docker exec -it redis-node-1 redis-cli cluster nodes
```
Lalu cek node5 (biasanya replika dari node 1) jika bukan bisa coba node-node lain selain node 1, 2 dan 3. Untuk cek cari baris myself, itu merupakan inisisasi node yang kamu panggil
```
docker exec -it redis-node-5 redis-cli cluster nodes
```
### Jalankan kode python failover
```
docker run -it --rm   --network skenario3_redis-cluster-net   -v "$PWD":/app   -w /app   python:3.9-slim   sh -c "pip install redis && python test_shardingfailover.py"
```



