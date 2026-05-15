import time
import random
import sqlite3
import os

# ============================
# База данных (реальный SQLite)
# ============================
class Database:
    def __init__(self, db_path=":memory:"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA synchronous = NORMAL")
        self.conn.execute("PRAGMA journal_mode = WAL")
        self._create_table()
        self.reads = 0
        self.writes = 0

    def _create_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS kv (
                key INTEGER PRIMARY KEY,
                value INTEGER
            )
        """)
        self.conn.commit()

    def read(self, key):
        self.reads += 1
        cursor = self.conn.execute("SELECT value FROM kv WHERE key = ?", (key,))
        row = cursor.fetchone()
        return row[0] if row else None

    def write(self, key, value):
        self.writes += 1
        self.conn.execute(
            "INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)",
            (key, value)
        )
        self.conn.commit()

    def close(self):
        self.conn.close()

    def reset_stats(self):
        self.reads = 0
        self.writes = 0


# ============================
# Кэш (in-memory, без задержек)
# ============================
class CacheStorage:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key, None)

    def set(self, key, value):
        self.store[key] = value

    def delete(self, key):
        if key in self.store:
            del self.store[key]


# ============================
# Метрики (без изменений)
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
            if value is not None:
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
            if value is not None:
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
            if value is not None:
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
            if val is not None:
                self.db.write(key, val)
        self.dirty_keys.clear()

    def final_flush(self):
        if self.dirty_keys:
            self.flush()


# ============================
# Функция нагрузочного теста (обновлена)
# ============================
def load_test(system, read_ratio, num_ops, key_space=1000):
    # сброс счётчиков (но БД уже чистая)
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
        if hasattr(system, 'dirty_keys'):
            result['dirty_keys_final'] = len(system.dirty_keys)
    return result


# ============================
# Вспомогательная функция для создания и заполнения БД
# ============================
def create_filled_db(db_path, key_space, init_value_func=lambda i: i * 10):
    db = Database(db_path)
    for i in range(key_space):
        db.write(i, init_value_func(i))
    db.reset_stats()  # обнуляем счётчики после заполнения
    return db


# ============================
# Запуск всех сценариев с реальными БД
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

        # Для каждого теста используем отдельный файл БД, чтобы не влиять друг на друга
        # Cache-Aside
        db1_path = f"test_db_ca_{scenario_name.replace(' ', '_')}.db"
        db1 = create_filled_db(db1_path, KEY_SPACE)
        cache1 = CacheStorage()
        sys1 = CacheAsideSystem(db1, cache1)
        r1 = load_test(sys1, read_ratio, NUM_OPS, KEY_SPACE)
        db1.close()
        os.remove(db1_path)

        # Write-Through
        db2_path = f"test_db_wt_{scenario_name.replace(' ', '_')}.db"
        db2 = create_filled_db(db2_path, KEY_SPACE)
        cache2 = CacheStorage()
        sys2 = WriteThroughSystem(db2, cache2)
        r2 = load_test(sys2, read_ratio, NUM_OPS, KEY_SPACE)
        db2.close()
        os.remove(db2_path)

        # Write-Back
        db3_path = f"test_db_wb_{scenario_name.replace(' ', '_')}.db"
        db3 = create_filled_db(db3_path, KEY_SPACE)
        cache3 = CacheStorage()
        sys3 = WriteBackSystem(db3, cache3, flush_batch=10)
        r3 = load_test(sys3, read_ratio, NUM_OPS, KEY_SPACE)
        db3.close()
        os.remove(db3_path)

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
    print("ИТОГОВАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ (РЕАЛЬНАЯ БД - SQLite)")
    print("="*80)
    print(f"{'Сценарий':<25} {'Метрика':<15} {'Cache-Aside':<15} {'Write-Through':<15} {'Write-Back':<15}")
    print("-"*70)
    for scenario_name, _ in scenarios:
        r_ca = results["Cache-Aside"][scenario_name]
        r_wt = results["Write-Through"][scenario_name]
        r_wb = results["Write-Back"][scenario_name]
        print(f"{scenario_name:<25} {'Throughput':<15} {r_ca['throughput']:15.1f} {r_wt['throughput']:15.1f} {r_wb['throughput']:15.1f}")
        print(f"{'':<25} {'AvgLat(ms)':<15} {r_ca['avg_latency']*1000:15.4f} {r_wt['avg_latency']*1000:15.4f} {r_wb['avg_latency']*1000:15.4f}")
        print(f"{'':<25} {'DB Reads':<15} {r_ca['db_reads']:<15} {r_wt['db_reads']:<15} {r_wb['db_reads']:<15}")
        print(f"{'':<25} {'DB Writes':<15} {r_ca['db_writes']:<15} {r_wt['db_writes']:<15} {r_wb['db_writes']:<15}")
        print(f"{'':<25} {'Hit Rate %':<15} {r_ca['hit_rate']:15.2f} {r_wt['hit_rate']:15.2f} {r_wb['hit_rate']:15.2f}")
        if "flushes" in r_wb:
            print(f"{'':<25} {'Flushes':<15} {'-':<15} {'-':<15} {r_wb['flushes']:<15}")
        print("-"*70)


if __name__ == "__main__":
    run_all_tests()