import subprocess
import time
import sys
import json
from itertools import product

BROKERS = ['rabbitmq', 'redis']
MESSAGE_SIZES = [128, 1024, 10240, 102400]
RATES = [1000, 5000, 10000] 
DURATION = 3
HOST = 'localhost'
QUEUE = 'benchmark_queue'

def run_test(broker, size, rate):
    print(f"\n=== Testing {broker} | size={size}B | rate={rate}/s | duration={DURATION}s ===")
    consumer_cmd = [
        'python3', 'consumer.py',
        '--broker', broker,
        '--host', HOST,
        '--queue', QUEUE,
        '--timeout', str(DURATION + 5)
    ]
    
    producer_cmd = [
        'python3', 'producer.py',
        '--broker', broker,
        '--host', HOST,
        '--queue', QUEUE,
        '--size', str(size),
        '--rate', str(rate),
        '--duration', str(DURATION)
    ]
        
    consumer_proc = subprocess.Popen(consumer_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    time.sleep(2)

    producer_proc = subprocess.run(producer_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    consumer_stdout, consumer_stderr = consumer_proc.communicate()

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

    result = {
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
    return result

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