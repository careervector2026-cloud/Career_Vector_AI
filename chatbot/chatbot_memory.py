# chatbot_memory.py

CHATBOT_SESSIONS = {}

def get_session(resume_url: str):

    if resume_url not in CHATBOT_SESSIONS:
        CHATBOT_SESSIONS[resume_url] = {}

    return CHATBOT_SESSIONS[resume_url]


def update_session(resume_url: str, key: str, value):

    session = get_session(resume_url)
    session[key] = value


def read_session(resume_url: str, key: str):

    session = get_session(resume_url)
    return session.get(key)