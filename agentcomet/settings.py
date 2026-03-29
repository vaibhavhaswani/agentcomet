import os

class Settings:
    AGENTCOMET_LOCAL_URL = None
    AGENTCOMET_LOCAL_KEY = None

    @classmethod
    def init(cls, **kwargs):
        for key, value in kwargs.items():
            setattr(cls, key, value)
            if value is not None:
                os.environ[key] = str(value)

    @classmethod
    def get_url(cls):
        url = getattr(cls, 'AGENTCOMET_LOCAL_URL', None)
        return url if url else os.environ.get("AGENTCOMET_LOCAL_URL")

    @classmethod
    def get_key(cls):
        key = getattr(cls, 'AGENTCOMET_LOCAL_KEY', None)
        return key if key else os.environ.get("AGENTCOMET_LOCAL_KEY")
