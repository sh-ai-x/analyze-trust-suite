"""Session restore from a client-supplied token."""

import pickle


def load_session(blob):
    return pickle.loads(blob)
