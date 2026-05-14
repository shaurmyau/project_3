import time
import random

# ============================
# Имитация задержек (секунды)
# ============================
DB_READ_DELAY = 0.0005
DB_WRITE_DELAY = 0.001
CACHE_READ_DELAY = 0.00005
CACHE_WRITE_DELAY = 0.0001

# ============================
# База данных (in-memory с задержками)
# ============================
class Database:
    def __init__(self):
        self.data = {}
        self.reads = 0
        self.writes = 0

    def read(self, key):
        self.reads += 1
        time.sleep(DB_READ_DELAY)
        return self.data.get(key, None)

    def write(self, key, value):
        self.writes += 1
        time.sleep(DB_WRITE_DELAY)
        self.data[key] = value

# ============================
# Кэш (in-memory с задержками)
# ============================
class CacheStorage:
    def __init__(self):
        self.store = {}

    def get(self, key):
        time.sleep(CACHE_READ_DELAY)
        return self.store.get(key, None)

    def set(self, key, value):
        time.sleep(CACHE_WRITE_DELAY)
        self.store[key] = value

    def delete(self, key):
        time.sleep(CACHE_READ_DELAY)
        if key in self.store:
            del self.store[key]

# ============================
# Метрики
# ============================
class SystemMetrics:
    def __init__(self):
        self.cache_hits = 0
        self.cache_misses = 0
        self.flushes = 0

# ============================
# 1. Cache-Aside (Lazy Loading)
# ============================
class CacheAsideSystem:
    def __init__(self, db, cache):
        self.db = db
        self.cache = cache
        self.metrics = SystemMetrics()

    def read(self, key):
        value = self.cache.get(key)
        if value is None:
            self.metrics.cache_misses += 1
            value = self.db.read(key)
            self.cache.set(key, value)
        else:
            self.metrics.cache_hits += 1
        return value

    def write(self, key, value):
        self.db.write(key, value)
        self.cache.delete(key)

# ============================
# 2. Write-Through
# ============================
class WriteThroughSystem:
    def __init__(self, db, cache):
        self.db = db
        self.cache = cache
        self.metrics = SystemMetrics()

    def read(self, key):
        value = self.cache.get(key)
        if value is None:
            self.metrics.cache_misses += 1
            value = self.db.read(key)
            self.cache.set(key, value)
        else:
            self.metrics.cache_hits += 1
        return value

    def write(self, key, value):
        self.db.write(key, value)
        self.cache.set(key, value)

# ============================
# 3. Write-Back (отложенная запись)
# ============================
class WriteBackSystem:
    def __init__(self, db, cache, flush_batch=10):
        self.db = db
        self.cache = cache
        self.metrics = SystemMetrics()
        self.dirty_keys = set()
        self.flush_batch = flush_batch

    def read(self, key):
        value = self.cache.get(key)
        if value is None:
            self.metrics.cache_misses += 1
            value = self.db.read(key)
            self.cache.set(key, value)
        else:
            self.metrics.cache_hits += 1
        return value

    def write(self, key, value):
        self.cache.set(key, value)
        self.dirty_keys.add(key)
        if len(self.dirty_keys) >= self.flush_batch:
            self.flush()

    def flush(self):
        if not self.dirty_keys:
            return
        self.metrics.flushes += 1
        for key in self.dirty_keys:
            val = self.cache.get(key)
            self.db.write(key, val)
        self.dirty_keys.clear()

    def final_flush(self):
        if self.dirty_keys:
            self.flush()

# ============================
# Функция нагрузочного теста
# ============================
def load_test(system, read_ratio, num_ops, key_space=1000):
    # сброс счётчиков
    system.metrics.cache_hits = 0
    system.metrics.cache_misses = 0
    system.db.reads = 0
    system.db.writes = 0

    start = time.perf_counter()
    for _ in range(num_ops):
        key = random.randint(0, key_space - 1)
        if random.random() < read_ratio:
            _ = system.read(key)
        else:
            value = random.randint(0, 10000)
            system.write(key, value)

    if hasattr(system, 'final_flush'):
        system.final_flush()

    elapsed = time.perf_counter() - start
    total_ops = num_ops
    throughput = total_ops / elapsed if elapsed > 0 else 0
    avg_latency = elapsed / total_ops if total_ops > 0 else 0

    hits = system.metrics.cache_hits
    misses = system.metrics.cache_misses
    total_read_attempts = hits + misses
    hit_rate = (hits / total_read_attempts * 100) if total_read_attempts > 0 else 0.0

    result = {
        'ops': total_ops,
        'time': elapsed,
        'throughput': throughput,
        'avg_latency': avg_latency,
        'db_reads': system.db.reads,
        'db_writes': system.db.writes,
        'cache_hits': hits,
        'cache_misses': misses,
        'hit_rate': hit_rate,
    }
    if hasattr(system, 'metrics') and system.metrics.flushes > 0:
        result['flushes'] = system.metrics.flushes
        result['dirty_keys_final'] = len(system.dirty_keys)
    return result

# ============================
# Запуск всех сценариев
# ============================
def run_all_tests():
    random.seed(42)
    NUM_OPS = 2000
    KEY_SPACE = 1000
    scenarios = [
        ("READ-HEAVY (80/20)", 0.8),
        ("BALANCED (50/50)", 0.5),
        ("WRITE-HEAVY (20/80)", 0.2),
    ]
    systems = ["Cache-Aside", "Write-Through", "Write-Back"]

    results = {s: {} for s in systems}

    for scenario_name, read_ratio in scenarios:
        print(f"\n{'='*60}")
        print(f"  {scenario_name}  (total ops = {NUM_OPS})")
        print(f"{'='*60}")

        # Cache-Aside
        db1 = Database()
        cache1 = CacheStorage()
        for i in range(KEY_SPACE):
            db1.write(i, i * 10)
        db1.reads = 0; db1.writes = 0
        sys1 = CacheAsideSystem(db1, cache1)
        r1 = load_test(sys1, read_ratio, NUM_OPS, KEY_SPACE)

        # Write-Through
        db2 = Database()
        cache2 = CacheStorage()
        for i in range(KEY_SPACE):
            db2.write(i, i * 10)
        db2.reads = 0; db2.writes = 0
        sys2 = WriteThroughSystem(db2, cache2)
        r2 = load_test(sys2, read_ratio, NUM_OPS, KEY_SPACE)

        # Write-Back
        db3 = Database()
        cache3 = CacheStorage()
        for i in range(KEY_SPACE):
            db3.write(i, i * 10)
        db3.reads = 0; db3.writes = 0
        sys3 = WriteBackSystem(db3, cache3, flush_batch=10)
        r3 = load_test(sys3, read_ratio, NUM_OPS, KEY_SPACE)

        # Сохраняем
        results["Cache-Aside"][scenario_name] = r1
        results["Write-Through"][scenario_name] = r2
        results["Write-Back"][scenario_name] = r3

        # Вывод таблицы
        header = f"{'System':<15} {'Throughput':>12} {'AvgLat(ms)':>12} {'DB Reads':>10} {'DB Writes':>10} {'HitRate%':>10}"
        print(header)
        print("-" * len(header))
        for name, res in [("Cache-Aside", r1), ("Write-Through", r2), ("Write-Back", r3)]:
            extra = ""
            if "flushes" in res:
                extra = f"  flushes={res['flushes']}"
            print(f"{name:<15} {res['throughput']:12.1f} {res['avg_latency']*1000:12.4f} {res['db_reads']:10} {res['db_writes']:10} {res['hit_rate']:10.2f}{extra}")

    # Итоговая сводная таблица
    print("\n\n" + "="*80)
    print("ИТОГОВАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ")
    print("="*80)
    print(f"{'Сценарий':<25} {'Метрика':<15} {'Cache-Aside':<15} {'Write-Through':<15} {'Write-Back':<15}")
    print("-"*70)
    for scenario_name, _ in scenarios:
        r_ca = results["Cache-Aside"][scenario_name]
        r_wt = results["Write-Through"][scenario_name]
        r_wb = results["Write-Back"][scenario_name]
        # Throughput
        print(f"{scenario_name:<25} {'Throughput':<15} {r_ca['throughput']:15.1f} {r_wt['throughput']:15.1f} {r_wb['throughput']:15.1f}")
        # Avg Latency (ms)
        print(f"{'':<25} {'AvgLat(ms)':<15} {r_ca['avg_latency']*1000:15.4f} {r_wt['avg_latency']*1000:15.4f} {r_wb['avg_latency']*1000:15.4f}")
        # DB Reads
        print(f"{'':<25} {'DB Reads':<15} {r_ca['db_reads']:<15} {r_wt['db_reads']:<15} {r_wb['db_reads']:<15}")
        # DB Writes
        print(f"{'':<25} {'DB Writes':<15} {r_ca['db_writes']:<15} {r_wt['db_writes']:<15} {r_wb['db_writes']:<15}")
        # Hit Rate
        print(f"{'':<25} {'Hit Rate %':<15} {r_ca['hit_rate']:15.2f} {r_wt['hit_rate']:15.2f} {r_wb['hit_rate']:15.2f}")
        # extra write-back
        if "flushes" in r_wb:
            print(f"{'':<25} {'Flushes':<15} {'-':<15} {'-':<15} {r_wb['flushes']:<15}")
        print("-"*70)

if __name__ == "__main__":
    run_all_tests()