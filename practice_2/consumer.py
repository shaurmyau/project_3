import argparse
import time
import sys
import threading
import pika
import redis

class Stats:
    def __init__(self):
        self.received = 0
        self.errors = 0
        self.start_time = None
        self.lock = threading.Lock()
        self.latencies = []

    def record(self, latency=None):
        with self.lock:
            self.received += 1
            if latency is not None:
                self.latencies.append(latency)

    def record_error(self):
        with self.lock:
            self.errors += 1

def run_rabbitmq(args):
    params = pika.ConnectionParameters(host=args.host, port=args.port)
    conn = pika.BlockingConnection(params)
    channel = conn.channel()
    channel.queue_declare(queue=args.queue, durable=True)
    stats = Stats()
    stop_event = threading.Event()

    def on_message(ch, method, properties, body):
        stats.record()
        ch.basic_ack(delivery_tag=method.delivery_tag)
        if stats.received % 1000 == 0:
            print(f"[Consumer] Received {stats.received} messages", file=sys.stderr)

    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=args.queue, on_message_callback=on_message)

    print("[Consumer] RabbitMQ start. Waiting for messages...", file=sys.stderr)
    stats.start_time = time.time()

    def timeout_stop():
        time.sleep(args.timeout)
        stop_event.set()
        conn.add_callback_threadsafe(lambda: channel.stop_consuming())

    timer = threading.Thread(target=timeout_stop)
    timer.start()

    try:
        channel.start_consuming()
    except Exception as e:
        print(f"[Consumer] Error: {e}", file=sys.stderr)
    finally:
        conn.close()
        duration = time.time() - stats.start_time
        throughput = stats.received / duration if duration > 0 else 0
        print(f"[Consumer] Done. Received: {stats.received}, Errors: {stats.errors}, Duration: {duration:.2f}s",
              file=sys.stderr)
        print(f"CONSUMER_STATS received={stats.received} errors={stats.errors} duration={duration:.2f} throughput={throughput:.2f}")

def run_redis(args):
    r = redis.Redis(host=args.host, port=args.port, decode_responses=True)
    r.ping()
    stats = Stats()
    stats.start_time = time.time()
    end_time = stats.start_time + args.timeout

    print("[Consumer] Redis start. Waiting for messages...", file=sys.stderr)

    while time.time() < end_time:
        try:
            result = r.blpop(args.queue, timeout=1)
            if result:
                _, message = result
                stats.record()
                if stats.received % 1000 == 0:
                    print(f"[Consumer] Received {stats.received} messages", file=sys.stderr)
        except Exception as e:
            stats.record_error()
            print(f"[Consumer] redis error: {e}", file=sys.stderr)

    duration = time.time() - stats.start_time
    throughput = stats.received / duration if duration > 0 else 0
    print(f"[Consumer] Done. Received: {stats.received}, Errors: {stats.errors}, Duration: {duration:.2f}s",
          file=sys.stderr)
    print(f"CONSUMER_STATS received={stats.received} errors={stats.errors} duration={duration:.2f} throughput={throughput:.2f}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--broker', choices=['rabbitmq', 'redis'], required=True)
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=None)
    parser.add_argument('--queue', default='benchmark_queue')
    parser.add_argument('--timeout', type=int, default=60, help='consumer run duration')
    args = parser.parse_args()

    if args.port is None:
        args.port = 5672 if args.broker == 'rabbitmq' else 6379

    if args.broker == 'rabbitmq':
        run_rabbitmq(args)
    else:
        run_redis(args)

if __name__ == '__main__':
    main()