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

## Jalankan untuk buat cluster
```
./init_cluster.sh
```

## Jalanin Test
```
docker run -it --rm   --network skenario3_redis-cluster-net   -v "$PWD":/app   -w /app   python:3.9-slim   sh -c "pip install redis && python test_sharding.py"
```


