import redis


class Config(object):
    SQLALCHEMY_DATABASE_URI = "mysql://root:123123@127.0.0.1/information1501"
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    SECRET_KEY = ".;kjfd;;djd"

    REDIS_HOST = "127.0.0.1"
    REDIS_PORT = 6379

    SESSION_TYPE = "redis"
    SESSION_REDIS = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT)
    SESSION_USE_SIGNER = True
    PERMANENT_SESSION_LIFETIME = 86400 * 10


class DevelopConfig(Config):
    DEBUG = True


class ProcutionConfig(Config):
    pass


config_map = {
    "develop": DevelopConfig,
    "product": ProcutionConfig
}