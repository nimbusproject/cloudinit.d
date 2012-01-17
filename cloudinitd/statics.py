import os

callback_action_started = "starting"
callback_action_transition = "transition"
callback_action_complete = "complete"
callback_action_error = "error"

callback_return_default = None
callback_return_restart = "restart"

REMOTE_WORKING_DIR = "/tmp/nimbusready"
REMOTE_WORKING_DIR_ENV_STR = "REMOTE_WORKING_DIR_ENV"

def get_remote_working_dir():
    if REMOTE_WORKING_DIR_ENV_STR in os.environ:
        return os.environ[REMOTE_WORKING_DIR_ENV_STR]
    return REMOTE_WORKING_DIR

