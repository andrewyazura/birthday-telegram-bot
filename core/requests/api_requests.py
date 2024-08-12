import requests
from time import time
import base64

from requests import RequestException
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

from core.config import BOT_TOKEN

# with open("core/key.pem", "rb") as key_file:
#     PUBLIC_KEY = serialization.load_pem_public_key(key_file.read())
PUBLIC_KEY = None
JWT_EXPIRES_SECONDS = 60 * 60


# TODO: fix docs
class SessionManager:
    """Class to manage user sessions.

    Methods:
        get_session(user_id): Create or return existing CustomSession object for the given user_id

    """

    def __init__(self):
        self.sessions = {}

    def get_session(self, id):
        if id not in self.sessions or self.sessions[id].is_expired():
            if id == BOT_TOKEN:
                self.sessions[id] = AdminSession()
            else:
                self.sessions[id] = CustomSession(id)

        return self.sessions[id]


class CustomSession(requests.Session):
    """Extend requests.Session class with custom properties and methods.

    Attributes:
        id: id of the session
        time_created: Time when the session was created

    Methods:
        is_expired: Check if the session has expired
        login(encrypted_bot_id): Log in to the api with the given encrypted_bot_id
        pre_request_hook(response, *args, **kwargs): Function to check before each request if the session has expired and relogin if needed.
    """

    def __init__(self, id):
        super().__init__()
        self.id = id
        self.time_created = time()
        self.login(self._encrypt_bot_id())
        self.hooks["response"].append(self.pre_request_hook)

    def is_expired(self) -> bool:
        """Check if the session has expired"""
        return time() - self.time_created > JWT_EXPIRES_SECONDS

    def login(self, encrypted_bot_id) -> bool:
        """Logs in session to the api with the given encrypted_bot_id"""
        try:
            login_response = self.get(
                "http://127.0.0.1:8080/login",
                params={"encrypted_bot_id": encrypted_bot_id, "id": self.id},
            )
            login_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Failed to login to api. {e}. {login_response.text}")
            raise RequestException("Failed to login to api")

        csrf_access_token = self.cookies["csrf_access_token"]

        self.headers.update({"X-CSRF-TOKEN": csrf_access_token})
        return True

    # do i need response?
    def pre_request_hook(self, response, *args, **kwargs):
        """Function to be executed before each request.

        Check if the session has expired and relogins if needed.

        """

        if self.is_expired():
            self.login(self._encrypt_bot_id())

    def _get_public_key(self):
        """Request public key from the api and return it as a cryptography object"""
        try:
            response = requests.get("http://127.0.0.1:8080/public-key")
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(
                f"Failed to get public key. {e}"
            )  # TODO: accessing the response.text in except will raise an error if the request failed
            raise RequestException(f"Failed to request public key")

        public_key_json = response.json()
        public_key = serialization.load_pem_public_key(
            public_key_json["public_key"].encode("utf-8")
        )
        return public_key

    def _encrypt_bot_id(self, request_key=False):
        """Encrypt bot token with the public key and return it as a base64 string"""
        global PUBLIC_KEY

        if PUBLIC_KEY is None or request_key:
            PUBLIC_KEY = self._get_public_key()

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


class AdminSession(CustomSession):
    def __init__(self):
        super().__init__(BOT_TOKEN)

    def login(self, encrypted_bot_id) -> bool:
        """Logs in session to the api as admin with the given encrypted_bot_id"""
        try:
            login_response = self.get(
                "http://127.0.0.1:8080/admin/login",
                params={"encrypted_bot_id": encrypted_bot_id},
            )
            login_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Failed to login to api. {e}. {login_response.text}")
            raise RequestException("Failed to login to api")

        csrf_access_token = self.cookies["csrf_access_token"]

        self.headers.update({"X-CSRF-TOKEN": csrf_access_token})
        return True


session_manager = SessionManager()


def post_request(user_id, data_json) -> requests.Response:
    """Post request to the api with the given user id and data

    Doesn't handle exceptions, raises them to the caller.
    """
    user_session = session_manager.get_session(user_id)

    post_response = user_session.post("http://127.0.0.1:8080/birthdays", json=data_json)

    return post_response


def get_request(user_id) -> requests.Response:
    """Get request to the api with the given user id

    Doesn't handle exceptions, raises them to the caller.
    """
    user_session = session_manager.get_session(user_id)

    get_response = user_session.get("http://127.0.0.1:8080/birthdays")

    return get_response


def get_by_id_request(user_id, birthday_id) -> requests.Response:
    """Get request to the api with the given user id and birthday id

    Doesn't handle exceptions, raises them to the caller.
    """
    user_session = session_manager.get_session(user_id)

    get_response = user_session.get(f"http://127.0.0.1:8080/birthdays/{birthday_id}")

    return get_response


def put_request(user_id, birthday_id, data_json) -> requests.Response:
    """Put request to the api with the given user id and data

    Doesn't handle exceptions, raises them to the caller.
    """
    user_session = session_manager.get_session(user_id)

    put_response = user_session.put(
        f"http://127.0.0.1:8080/birthdays/{birthday_id}", json=data_json
    )

    return put_response


def delete_request(user_id, birthday_id) -> requests.Response:
    """Delete request to the api with the given user id and birthday id

    Doesn't handle exceptions, raises them to the caller.
    """
    user_session = session_manager.get_session(user_id)

    delete_response = user_session.delete(
        f"http://127.0.0.1:8080/birthdays/{birthday_id}"
    )

    return delete_response


def incoming_birthdays_request() -> requests.Response:
    """Get request to the api as admin to get incoming birthdays

    Doesn't handle exceptions, raises them to the caller.
    """

    admin_session = session_manager.get_session(BOT_TOKEN)

    response = admin_session.get("http://127.0.0.1:8080/admin/birthdays/incoming")

    return response
