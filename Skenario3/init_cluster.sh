#!/bin/bash
echo "Membentuk Redis Cluster (Tanpa Password)..."

# Hapus flag "-a password123" karena server redis:alpine sedang berjalan tanpa password
docker exec -it redis-node-1 redis-cli --cluster create \
redis-node-1:6379 \
redis-node-2:6379 \
redis-node-3:6379 \
redis-node-4:6379 \
redis-node-5:6379 \
redis-node-6:6379 \
--cluster-replicas 1