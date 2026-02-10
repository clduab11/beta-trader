# Redis Stack Setup

Beta-Trader uses **Redis Stack** (includes RediSearch module) for caching and the Council knowledge store.

## Installation

### Option A: Docker (Recommended)

From the project root:

```bash
docker compose up -d redis
```

This starts Redis Stack with:
- **Port 6379**: Redis server
- **Port 8001**: RedisInsight web UI
- **AOF persistence** enabled (data survives restarts)
- **volatile-lru eviction** (only TTL keys are evicted)

### Option B: Native Install (macOS)

```bash
brew tap redis-stack/redis-stack
brew install redis-stack
redis-stack-server
```

### Option C: Native Install (Linux)

```bash
curl -fsSL https://packages.redis.io/gpg | sudo gpg --dearmor -o /usr/share/keyrings/redis-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/redis-archive-keyring.gpg] https://packages.redis.io/deb $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/redis.list
sudo apt-get update
sudo apt-get install redis-stack-server
```

## Configuration

### Logical DB Split

Beta-Trader uses two logical databases within the same Redis instance:

| DB  | Purpose         | Key Policy  | Notes                                |
|-----|-----------------|-------------|--------------------------------------|
| db0 | Cache           | TTL keys    | Evictable, stores cached API results |
| db1 | Council         | No TTL      | Persistent, stores exported intel    |

### Persistence Settings

Ensure the following settings are active (already configured in `docker-compose.yml`):

```
appendonly yes
maxmemory-policy volatile-lru
```

- **AOF (`appendonly yes`)**: Write-ahead log ensures Council data survives restarts
- **volatile-lru**: Only keys with a TTL (cache) are evicted under memory pressure; Council keys (no TTL) are never evicted

### Verifying the Setup

```bash
# Test connectivity
redis-cli ping
# Expected: PONG

# Verify db0 (cache)
redis-cli -n 0 SET test:cache "hello" EX 60
redis-cli -n 0 GET test:cache
# Expected: "hello"

# Verify db1 (Council)
redis-cli -n 1 SET test:council "hello"
redis-cli -n 1 GET test:council
# Expected: "hello"

# Verify RediSearch module is loaded
redis-cli MODULE LIST
# Expected: output includes "search" module

# Cleanup test keys
redis-cli -n 0 DEL test:cache
redis-cli -n 1 DEL test:council
```

### RedisInsight

When using Docker, RedisInsight is available at [http://localhost:8001](http://localhost:8001). Use it to:
- Browse keys in db0 and db1
- Run ad-hoc queries
- Monitor memory usage and performance

## Troubleshooting

### "ERR unknown command 'FT.CREATE'"

RediSearch module is not loaded. Make sure you're using **Redis Stack**, not plain Redis:

```bash
# Check if you're running Redis Stack
redis-cli MODULE LIST | grep search
```

If the module isn't listed, switch to Redis Stack (Docker or native install above).

### Data Not Persisting After Restart

Verify AOF is enabled:

```bash
redis-cli CONFIG GET appendonly
# Expected: "yes"
```

If not, enable it:

```bash
redis-cli CONFIG SET appendonly yes
redis-cli CONFIG REWRITE
```
