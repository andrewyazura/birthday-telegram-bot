import requests
import time
import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

from core.config import BOT_TOKEN

PUBLIC_KEY = None
JWT_EXPIRES_SECONDS = 60 * 60


class UserSessionManager:
    """Class to manage user sessions.

    Methods:
        get_session(user_id): Create or return existing UserSession object for the given user_id

    """

    def __init__(self):
        self.sessions = {}

    def get_session(self, user_id):
        if user_id not in self.sessions or self.sessions[user_id].is_expired():
            self.sessions[user_id] = UserSession(user_id)

        return self.sessions[user_id]


class UserSession(requests.Session):
    """Extend requests.Session class with custom properties and methods.

    Attributes:
        user_id: User id of the session
        time_created: Time when the session was created

    Methods:
        is_expired(): Check if the session has expired
        login(encrypted_bot_id): Log in to the api with the given encrypted_bot_id
        pre_request_hook(response, *args, **kwargs): Function to be executed before each request.
            Check if the session has expired and relogin if needed.
    """

    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.time_created = time.time()
        self.login(_encrypt_bot_id())
        self.hooks["response"].append(self.pre_request_hook)

    def is_expired(self) -> bool:
        """Check if the session has expired"""
        return time.time() - self.time_created > JWT_EXPIRES_SECONDS

    def login(self, encrypted_bot_id) -> bool:
        """Logs in session to the api with the given encrypted_bot_id"""
        login_response = self.get(
            "http://127.0.0.1:8080/login",
            params={"encrypted_bot_id": encrypted_bot_id, "id": self.user_id},
        )
        if login_response.status_code != 200:
            print(f"Failed to login to api. {login_response.status_code}")  # fix later
            return False
        csrf_access_token = self.cookies["csrf_access_token"]

        self.headers.update({"X-CSRF-TOKEN": csrf_access_token})
        return True

    def pre_request_hook(self, response, *args, **kwargs):
        """Function to be executed before each request.

        Check if the session has expired and relogins if needed.

        """

        if self.is_expired():
            self.login(_encrypt_bot_id())


session_manager = UserSessionManager()


def _get_public_key():
    """Request public key from the api and return it as a cryptography object"""
    response = requests.get("http://127.0.0.1:8080/public-key")

    if response.status_code != 200:
        print(f"Failed to get api key. code: {response.status_code}")  # fix later

    public_key_json = response.json()
    public_key = serialization.load_pem_public_key(
        public_key_json["public_key"].encode("utf-8")
    )
    return public_key


def _encrypt_bot_id(request_key=False):
    """Encrypt bot token with the public key and return it as a base64 string"""
    global PUBLIC_KEY

    if PUBLIC_KEY is None or request_key:
        PUBLIC_KEY = _get_public_key()

    encrypted_data = PUBLIC_KEY.encrypt(
        BOT_TOKEN.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    encrypted_data_base64 = base64.b64encode(encrypted_data).decode("utf-8")
    return encrypted_data_base64


def post_request(id, data_json) -> requests.Response:
    """Post request to the api with the given user id and data"""
    user_session = session_manager.get_session(id)

    post_response = user_session.post("http://127.0.0.1:8080/birthdays", json=data_json)
    if post_response.status_code != 201:
        print(f"Failed to add birthday. {post_response.json()}")  # fix later
    else:
        print(post_response.json())

    return post_response
