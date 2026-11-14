"""Every string used by telemetry.py lives here. Standard library only, Python 3.8+."""

# Where counts go: one Firestore counter per day, version, model and option combination, raised by
# one with the Firestore REST API. The web API key below only identifies the project; the security
# rules in the web repo decide what a write may do (create a counter at 1, or raise it by exactly 1).
FIRESTORE_PROJECT = "adversarypr"
FIRESTORE_API_KEY = "AIzaSyDVSGjqZpW9ruMw5SgpokCQ6tGXJJInxhs"
FIRESTORE_COLLECTION = "usage"
FIRESTORE_FIELD = "runs"
FIRESTORE_DOC_PATH = "projects/%s/databases/(default)/documents/%s/%s"
ENDPOINT_URL = (
    "https://firestore.googleapis.com/v1/projects/" + FIRESTORE_PROJECT
    + "/databases/(default)/documents:commit?key=" + FIRESTORE_API_KEY
)
DAY_FORMAT = "%Y-%m-%d"
ID_JOINER = "_"
DOT = "."
DOT_REPLACEMENT = "_"
TIMEOUT_SECONDS = 2
HTTP_METHOD = "POST"
CONTENT_TYPE_HEADER = "Content-Type"
CONTENT_TYPE_JSON = "application/json"
ENCODING = "utf-8"

# Consent state file: ~/.adversary/telemetry.json holding only {"consent": "on"|"off"}
STATE_DIR_NAME = ".adversary"
STATE_FILE_NAME = "telemetry.json"
STATE_DIR_MODE = 0o700
STATE_FILE_MODE = 0o600
CONSENT_KEY = "consent"

# Consent values and the one word `status` prints.
ON = "on"
OFF = "off"
ASK = "ask"

# Environment switches. Either one forces telemetry off and the skill never asks.
ENV_TELEMETRY = "ADVERSARY_TELEMETRY"
ENV_TELEMETRY_OFF_VALUES = ("0", "false", "off", "no")
ENV_DO_NOT_TRACK = "DO_NOT_TRACK"
ENV_DO_NOT_TRACK_ON_VALUES = ("1", "true", "yes", "on")

# Payload: a strict allowlist. Nothing else is ever added.
SCHEMA_VERSION = 1
EVENT_RUN = "run"
KEY_SCHEMA = "schema"
KEY_EVENT = "event"
KEY_VERSION = "version"
KEY_DRY_RUN = "dry_run"
KEY_HTML = "html"
KEY_MODEL = "model"
KEY_VERSION_PINNED = "version_pinned"
PAYLOAD_KEYS = (
    KEY_SCHEMA,
    KEY_EVENT,
    KEY_VERSION,
    KEY_DRY_RUN,
    KEY_HTML,
    KEY_MODEL,
    KEY_VERSION_PINNED,
)
VERSION_PATTERN = r"^\d+\.\d+\.\d+$"
MODEL_DEFAULT = "default"
MODELS = (MODEL_DEFAULT, "haiku", "sonnet", "opus", "fable")

# Command line.
PROG = "telemetry.py"
DESCRIPTION = (
    "Anonymous, opt-in usage counts for the AdversaryPR skill. Off until you say yes. "
    "When on, it sends only the skill version and which options you used."
)
CMD_STATUS = "status"
CMD_SET = "set"
CMD_PREVIEW = "preview"
CMD_SEND = "send"
DEST_COMMAND = "command"
DEST_VALUE = "value"
DEST_VERSION = "version"
DEST_DRY_RUN = "dry_run"
DEST_HTML = "html"
DEST_MODEL = "model"
DEST_PINNED = "pinned"
FLAG_VERSION = "--version"
FLAG_DRY_RUN = "--dry-run"
FLAG_HTML = "--html"
FLAG_MODEL = "--model"
FLAG_PINNED = "--pinned"
HELP_STATUS = "print one word: ask, on, or off"
HELP_SET = "turn anonymous usage counts on or off"
HELP_SET_VALUE = "on or off"
HELP_PREVIEW = "print the exact JSON that would be sent; sends nothing"
HELP_SEND = "send one count if consent is on; always exits 0 and prints nothing"
HELP_VERSION = "skill version that ran, such as 2.5.0"
HELP_DRY_RUN = "the run used dry run"
HELP_HTML = "the run used html"
HELP_MODEL = "the model option the run used (default when none)"
HELP_PINNED = "the user pinned a version with version="
JSON_INDENT = 2

# Exit codes.
EXIT_OK = 0
EXIT_USAGE = 2

# Messages printed by the CLI (never printed on a failed send).
MSG_SET_ON = "Anonymous usage counts are on. Turn them off any time: telemetry.py set off"
MSG_SET_OFF = "Anonymous usage counts are off."
MSG_ENV_OFF = "Note: an environment switch (ADVERSARY_TELEMETRY=0 or DO_NOT_TRACK=1) is forcing counts off."
ERR_BAD_VERSION = "version must look like 1.2.3"
ERR_BAD_MODEL = "model must be one of: " + ", ".join(MODELS)
ERR_STATE_WRITE = "could not save the choice"

# What the skill shows the user, once, on first run. Do not weaken.
CONSENT_QUESTION = (
    "Anonymous usage counts are off until you say yes. The skill asks once. "
    "If you agree, it sends the skill version and which options you used "
    "(dry run, html, model, pinned version) and nothing else: no code, no PR content, "
    "no repo or org names, no token. Turn it off any time."
)
