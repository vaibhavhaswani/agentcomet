import os

class Settings:
    AGENTCOMET_URL = None
    AGENTCOMET_KEY = None
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
        url = getattr(cls, 'AGENTCOMET_URL', None) or os.environ.get("AGENTCOMET_URL")
        if url: return url
        url_local = getattr(cls, 'AGENTCOMET_LOCAL_URL', None) or os.environ.get("AGENTCOMET_LOCAL_URL")
        return url_local

    @classmethod
    def get_key(cls):
        key = getattr(cls, 'AGENTCOMET_KEY', None) or os.environ.get("AGENTCOMET_KEY")
        if key: return key
        key_local = getattr(cls, 'AGENTCOMET_LOCAL_KEY', None) or os.environ.get("AGENTCOMET_LOCAL_KEY")
        return key_local
