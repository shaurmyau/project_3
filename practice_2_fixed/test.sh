
BROKER=$1
SIZE=$2
RATE=$3
COUNT=$4
DURATION=60
THREADS_P=4
THREADS_C=2

echo "Starting test: broker=$BROKER, size=$SIZE, rate=$RATE, count=$COUNT"

# Start consumer in background
python consumer.py --broker $BROKER --threads $THREADS_C --duration $DURATION > consumer_out.json &
CONSUMER_PID=$!

sleep 2

# Start producer
python producer.py --broker $BROKER --size $SIZE --rate $RATE --count $COUNT --threads $THREADS_P > producer_out.json

wait $CONSUMER_PID

echo "Producer stats:"
cat producer_out.json
echo "Consumer stats:"
cat consumer_out.json