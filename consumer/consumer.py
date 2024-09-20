import pika, logging, sys, argparse, time
from argparse import RawTextHelpFormatter
from time import sleep
from flask import Flask
import threading

app = Flask(__name__)

# Global variable to track message count
message_count = 0
args = {}

def on_message(channel, method_frame, header_frame, body):
    global message_count
    print(method_frame.delivery_tag)
    
    message_count += 1
    print("Received message: %s, total count: %s", body, str(message_count))
    LOG.info("Received message: %s, total count: %s", body, str(message_count))
    channel.basic_ack(delivery_tag=method_frame.delivery_tag)

def rabbitmq_consumer():
    global message_count

    credentials = pika.PlainCredentials('guest', 'guest')
    parameters = pika.ConnectionParameters(args.server,
                                           int(args.port),
                                           '/',
                                           credentials)
    connection = pika.BlockingConnection(parameters)
    channel = connection.channel()

    channel.queue_declare('pc')
    channel.basic_consume(on_message, 'pc')

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        channel.stop_consuming()
    connection.close()

# Flask route to expose the message count
@app.route('/metrics')
def metrics():
    return "Received messages count: {}\n".format(message_count), 200

def start_flask_app():
    app.run(host='0.0.0.0', port=9422)

if __name__ == '__main__':
    examples = sys.argv[0] + " -p 5672 -s rabbitmq "
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                 description='Run consumer.py',
                                 epilog=examples)
    parser.add_argument('-p', '--port', action='store', dest='port', help='The port to listen on.')
    parser.add_argument('-s', '--server', action='store', dest='server', help='The RabbitMQ server.')

    args = parser.parse_args()
    if args.port == None:
        print("Missing required argument: -p/--port")
        sys.exit(1)
    if args.server == None:
        print("Missing required argument: -s/--server")
        sys.exit(1)

    # sleep a few seconds to allow RabbitMQ server to come up
    sleep(5)
    logging.basicConfig(level=logging.INFO)
    LOG = logging.getLogger(__name__)
    
    # Run the RabbitMQ consumer in a separate thread
    rabbitmq_thread = threading.Thread(target=rabbitmq_consumer)
    rabbitmq_thread.daemon = True
    rabbitmq_thread.start()
    #threading.Thread(target=rabbitmq_consumer, daemon=True).start()

    # Run the Flask app
    start_flask_app()