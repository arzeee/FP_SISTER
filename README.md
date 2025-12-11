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


