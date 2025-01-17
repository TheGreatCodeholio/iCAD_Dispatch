import os
import sys

import redis
from dotenv import load_dotenv
from flask import Flask
from flask_session import Session
from werkzeug.middleware.proxy_fix import ProxyFix

# Import Routes
from routes import base_site, register_middlewares

from lib.logging_module import CustomLogger
from lib.mysql_module import MySQLDatabase
from lib.redis_module import RedisCache

app_name = "icad_dispatch"
__version__ = "1.0"

root_path = os.getcwd()
config_path = os.path.join(root_path, 'etc')
log_path = os.path.join(root_path, 'log')
log_file_name = f"{app_name}.log"

if not os.path.exists(log_path):
    os.makedirs(log_path)

if not os.path.exists(config_path):
    os.makedirs(config_path)

# Load .env
load_dotenv()

# Start Logger
main_logger = CustomLogger(os.getenv('LOG_LEVEL', 1), f'{app_name}',
                                os.path.join(log_path, log_file_name), show_threads=True).logger

try:
    db = MySQLDatabase()
    main_logger.info("MySQL Database connected successfully.")
except Exception as e:
    main_logger.error(f'Error while <<connecting>> to the <<MySQL Database:>> {e}')
    sys.exit(1)

try:
    rd = RedisCache()
    main_logger.info("Redis Pool Connection Pool connected successfully.")
except Exception as e:
    main_logger.error(f'Error while <<connecting>> to the <<Redis Cache:>> {e}')
    sys.exit(1)

app = Flask(__name__)

app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_port=1, x_prefix=1)

# Load or create secret key
if not os.getenv('SECRET_KEY'):
    try:
        with open(os.path.join(root_path + '/etc', 'secret_key'), 'rb') as f:
            app.config['SECRET_KEY'] = f.read()
    except FileNotFoundError:
        secret_key = os.urandom(24)
        with open(os.path.join(root_path + '/etc', 'secret_key'), 'wb') as f:
            f.write(secret_key)
            app.config['SECRET_KEY'] = secret_key
else:
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

app.config['logger'] = main_logger
app.config['base_url'] = os.getenv('BASE_URL')
app.config['db'] = db
app.config['rd'] = rd

# Session Configuration
app.config['SESSION_TYPE'] = 'redis'
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SESSION_KEY_PREFIX'] = 'icad_dispatch_session:'
app.config['SESSION_REDIS'] = redis.StrictRedis(host=os.getenv("REDIS_HOST"),
                                                password=os.getenv("REDIS_PASSWORD"),
                                                port=os.getenv("REDIS_PORT"), db=os.getenv("REDIS_SESSION_DB"))

# Cookie Configuration
app.config['SESSION_COOKIE_SECURE'] = os.getenv("SESSION_COOKIE_SECURE")
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_DOMAIN'] = os.getenv("SESSION_COOKIE_DOMAIN")
app.config['SESSION_COOKIE_NAME'] = os.getenv("SESSION_COOKIE_NAME")
app.config['SESSION_COOKIE_PATH'] = os.getenv("SESSION_COOKIE_PATH")
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Initializing the session
sess = Session()
sess.init_app(app)

# Register base site /
app.register_blueprint(base_site, url_prefix='/')

# Register Middleware
register_middlewares(app)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8099, debug=True)