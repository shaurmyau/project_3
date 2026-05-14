import argparse
import time
import sys
import pika
import redis
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

def create_rabbitmq_connection(host, port, queue):
    params = pika.ConnectionParameters(host=host, port=port)
    conn = pika.BlockingConnection(params)
    channel = conn.channel()
    channel.queue_declare(queue=queue, durable=False)   # без持久化
    # НЕТ confirm_delivery() – асинхронная отправка
    return conn, channel

def rabbitmq_worker(args, thread_id, thread_rate, results):
    conn, channel = create_rabbitmq_connection(args.host, args.port, args.queue)
    sent = 0
    failed = 0
    msg_body = 'x' * args.size
    interval = 1.0 / thread_rate if thread_rate > 0 else 0
    end_time = time.time() + args.duration

    while time.time() < end_time:
        loop_start = time.time()
        try:
            channel.basic_publish(
                exchange='',
                routing_key=args.queue,
                body=msg_body
                # НЕТ delivery_mode=2
            )
            sent += 1
        except Exception as e:
            failed += 1
            print(f"[Producer-{thread_id}] publish error: {e}", file=sys.stderr)

        elapsed = time.time() - loop_start
        sleep_time = interval - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

    conn.close()
    results[thread_id] = (sent, failed)

def run_rabbitmq_multithreaded(args):
    total_threads = args.threads
    per_thread_rate = max(1, args.rate // total_threads)
    print(f"[Producer] RabbitMQ multi ({total_threads} threads): size={args.size}B, "
          f"total_rate={args.rate}/s, per_thread={per_thread_rate}/s, duration={args.duration}s",
          file=sys.stderr)

    results = {}
    with ThreadPoolExecutor(max_workers=total_threads) as executor:
        futures = []
        for i in range(total_threads):
            future = executor.submit(rabbitmq_worker, args, i, per_thread_rate, results)
            futures.append(future)
        for future in as_completed(futures):
            future.result()

    total_sent = sum(r[0] for r in results.values())
    total_failed = sum(r[1] for r in results.values())
    print(f"[Producer] Done. Sent: {total_sent}, Failed: {total_failed}", file=sys.stderr)
    print(f"PRODUCER_STATS sent={total_sent} failed={total_failed}")

def run_redis(args):
    r = redis.Redis(host=args.host, port=args.port, decode_responses=True)
    sent = 0
    failed = 0
    start_time = time.time()
    end_time = start_time + args.duration
    msg_body = 'x' * args.size
    interval = 1.0 / args.rate if args.rate > 0 else 0

    print(f"[Producer] Redis start: size={args.size}B, rate={args.rate}/s, duration={args.duration}s",
          file=sys.stderr)

    while time.time() < end_time:
        loop_start = time.time()
        try:
            r.rpush(args.queue, msg_body)
            sent += 1
        except Exception as e:
            failed += 1
            print(f"[Producer] redis error: {e}", file=sys.stderr)

        elapsed = time.time() - loop_start
        sleep_time = interval - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

    print(f"[Producer] Done. Sent: {sent}, Failed: {failed}", file=sys.stderr)
    print(f"PRODUCER_STATS sent={sent} failed={failed}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--broker', choices=['rabbitmq', 'redis'], required=True)
    parser.add_argument('--host', default='localhost')
    parser.add_argument('--port', type=int, default=None)
    parser.add_argument('--queue', default='benchmark_queue')
    parser.add_argument('--size', type=int, default=128)
    parser.add_argument('--rate', type=int, default=1000)
    parser.add_argument('--duration', type=int, default=30)
    parser.add_argument('--threads', type=int, default=1)
    args = parser.parse_args()

    if args.port is None:
        args.port = 5672 if args.broker == 'rabbitmq' else 6379

    if args.broker == 'rabbitmq':
        run_rabbitmq_multithreaded(args)
    else:
        run_redis(args)

if __name__ == '__main__':
    main()