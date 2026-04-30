import argparse
import time
import sys
import pika
import redis

def create_rabbitmq_connection(host, port, queue):
    params = pika.ConnectionParameters(host=host, port=port)
    conn = pika.BlockingConnection(params)
    channel = conn.channel()
    channel.queue_declare(queue=queue, durable=True)
    channel.confirm_delivery()
    return conn, channel

def create_redis_connection(host, port, queue):
    r = redis.Redis(host=host, port=port, decode_responses=True)
    r.ping()
    return r

def run_rabbitmq(args):
    conn, channel = create_rabbitmq_connection(args.host, args.port, args.queue)
    sent = 0
    failed = 0
    start_time = time.time()
    end_time = start_time + args.duration
    msg_body = 'x' * args.size
    rate = args.rate
    interval = 1.0 / rate if rate > 0 else 0

    print(f"[Producer] RabbitMQ start: size={args.size}B, rate={rate}/s, duration={args.duration}s",
          file=sys.stderr)

    while time.time() < end_time:
        loop_start = time.time()
        try:
            channel.basic_publish(
                exchange='',
                routing_key=args.queue,
                body=msg_body,
                properties=pika.BasicProperties(delivery_mode=2)
            )
            sent += 1
        except Exception as e:
            failed += 1
            print(f"[Producer] publish error: {e}", file=sys.stderr)

        elapsed = time.time() - loop_start
        sleep_time = interval - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)

    conn.close()
    print(f"[Producer] Done. Sent: {sent}, Failed: {failed}", file=sys.stderr)
    print(f"PRODUCER_STATS sent={sent} failed={failed}")

def run_redis(args):
    r = create_redis_connection(args.host, args.port, args.queue)
    sent = 0
    failed = 0
    start_time = time.time()
    end_time = start_time + args.duration
    msg_body = 'x' * args.size
    rate = args.rate
    interval = 1.0 / rate if rate > 0 else 0

    print(f"[Producer] Redis start: size={args.size}B, rate={rate}/s, duration={args.duration}s",
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
    parser.add_argument('--size', type=int, default=128, help='message size in bytes')
    parser.add_argument('--rate', type=int, default=1000, help='messages per second')
    parser.add_argument('--duration', type=int, default=30, help='test duration in seconds')
    args = parser.parse_args()

    if args.port is None:
        args.port = 5672 if args.broker == 'rabbitmq' else 6379

    if args.broker == 'rabbitmq':
        run_rabbitmq(args)
    else:
        run_redis(args)

if __name__ == '__main__':
    main()