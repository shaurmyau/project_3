import subprocess
import time
import sys
import json
import pika
import redis
from itertools import product

BROKERS = ['rabbitmq', 'redis']
MESSAGE_SIZES = [128, 1024, 10240, 102400]
RATES = [1000, 5000, 10000]
DURATION = 10
HOST = 'localhost'
QUEUE = 'benchmark_queue'

def purge_queue(broker, host, port, queue):
    """Очищает очередь перед тестом"""
    if broker == 'rabbitmq':
        try:
            params = pika.ConnectionParameters(host=host, port=port)
            conn = pika.BlockingConnection(params)
            channel = conn.channel()
            channel.queue_delete(queue=queue)
            channel.queue_declare(queue=queue, durable=False)
            conn.close()
            print(f"[Purge] RabbitMQ queue '{queue}' deleted and recreated", file=sys.stderr)
        except Exception as e:
            print(f"[Purge] RabbitMQ error: {e}", file=sys.stderr)
    elif broker == 'redis':
        try:
            r = redis.Redis(host=host, port=port, decode_responses=True)
            r.delete(queue)
            print(f"[Purge] Redis list '{queue}' deleted", file=sys.stderr)
        except Exception as e:
            print(f"[Purge] Redis error: {e}", file=sys.stderr)

def run_test(broker, size, rate):
    print(f"\n=== Testing {broker} | size={size}B | rate={rate}/s | duration={DURATION}s ===")
    
    # Очистка очереди перед тестом
    port = 5672 if broker == 'rabbitmq' else 6379
    purge_queue(broker, HOST, port, QUEUE)
    time.sleep(1)  # Даем время на очистку
    
    threads = 4
    
    consumer_cmd = [
        'python3', 'consumer.py',
        '--broker', broker,
        '--host', HOST,
        '--queue', QUEUE,
        '--timeout', str(DURATION + 5),
        '--prefetch', '5000'
    ]
    
    producer_cmd = [
        'python3', 'producer.py',
        '--broker', broker,
        '--host', HOST,
        '--queue', QUEUE,
        '--size', str(size),
        '--rate', str(rate),
        '--duration', str(DURATION),
        '--threads', str(threads)
    ]
    
    consumer_proc = subprocess.Popen(consumer_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    time.sleep(2)
    producer_proc = subprocess.run(producer_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    consumer_stdout, consumer_stderr = consumer_proc.communicate()
    
    # Парсинг статистики (как ранее)
    producer_stats = {}
    for line in producer_proc.stdout.splitlines():
        if line.startswith('PRODUCER_STATS'):
            parts = line.split()
            for part in parts[1:]:
                k, v = part.split('=')
                producer_stats[k] = int(v)
            break
    
    consumer_stats = {}
    for line in consumer_stdout.splitlines():
        if line.startswith('CONSUMER_STATS'):
            parts = line.split()
            for part in parts[1:]:
                k, v = part.split('=')
                if k in ('received', 'errors'):
                    consumer_stats[k] = int(v)
                elif k in ('duration', 'throughput'):
                    consumer_stats[k] = float(v)
            break
    
    sent = producer_stats.get('sent', 0)
    received = consumer_stats.get('received', 0)
    lost = sent - received
    
    return {
        'broker': broker,
        'size': size,
        'rate': rate,
        'sent': sent,
        'received': received,
        'lost': lost,
        'producer_failed': producer_stats.get('failed', 0),
        'consumer_errors': consumer_stats.get('errors', 0),
        'consumer_throughput': consumer_stats.get('throughput', 0.0),
        'duration': consumer_stats.get('duration', 0.0)
    }

def main():
    results = []
    for broker, size, rate in product(BROKERS, MESSAGE_SIZES, RATES):
        try:
            res = run_test(broker, size, rate)
            results.append(res)
            print(f"Result: sent={res['sent']}, received={res['received']}, lost={res['lost']}, "
                  f"throughput={res['consumer_throughput']:.2f} msg/s")
        except Exception as e:
            print(f"Test failed: {e}", file=sys.stderr)
    
    with open('benchmark_results.json', 'w') as f:
        json.dump(results, f, indent=2)
    
    print("\n=== SUMMARY TABLE ===")
    print(f"{'Broker':<10} {'Size(B)':<8} {'Target rate':<12} {'Sent':<8} {'Recv':<8} {'Lost':<8} {'Throughput':<12}")
    for r in results:
        print(f"{r['broker']:<10} {r['size']:<8} {r['rate']:<12} {r['sent']:<8} {r['received']:<8} "
              f"{r['lost']:<8} {r['consumer_throughput']:<12.2f}")

if __name__ == '__main__':
    main()