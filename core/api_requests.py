import requests
from time import time
import base64
import logging

from requests import RequestException
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes

from core.config import BOT_TOKEN
import core.logger

PUBLIC_KEY = None
JWT_EXPIRES_SECONDS = 60 * 60


class SessionManager:
    """Class to manage sessions

    Should be used to get sessions by id. If the session doesn't exist or has expired,
    a new session is created.

    Attributes:
        sessions (dict): Dictionary to store sessions with their ids as keys

    """

    def __init__(self):
        self.sessions = {}

    def get_session(self, id):
        """Get session by id.

        Create a new session if it doesn't exist or has expired."""
        if id not in self.sessions or self.sessions[id].is_expired():
            if id == BOT_TOKEN:
                logging.info("Creating admin session")
                self.sessions[id] = AdminSession()
            else:
                logging.info(f"Creating user session with id: {id}")
                self.sessions[id] = CustomSession(id)

        return self.sessions[id]


session_manager = SessionManager()


class CustomSession(requests.Session):
    """Extend `requests.Session` class with custom properties and methods.

    Args:
        id: id of the session. Should be user's id or bot's token

    Attributes:
        id: id of the session
        time_created: Time when the session was created
        hooks: List of hooks to be executed before or after the request
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
        """Login to the api with the given `encrypted_bot_id`.

        Args:
            encrypted_bot_id (str): Bot's id encrypted with the `PUBLIC_KEY`

        Raises:
            RequestException: Raised if request to the api failed

        Returns:
            bool: True if login was successful
        """
        try:
            login_response = self.get(
                "http://127.0.0.1:8080/login",
                params={"encrypted_bot_id": encrypted_bot_id, "id": self.id},
            )
            login_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to login user {self.id} to the api: {e}.")
            raise RequestException("Failed to login to api")

        csrf_access_token = self.cookies["csrf_access_token"]

        self.headers.update({"X-CSRF-TOKEN": csrf_access_token})

        logging.info(f"User with id: {self.id} successfully logged in to the api")
        return True

    # do i need response?
    def pre_request_hook(self, response, *args, **kwargs):
        """Function to be executed before each request.

        Check if the session has expired and relogins if needed.

        """

        if self.is_expired():
            logging.info(f"Session with id: {self.id} has expired. Relogging")
            self.login(self._encrypt_bot_id())

    def _get_public_key(self):
        """Request public key from the api and return it as a cryptography object

        Raises:
            RequestException: Raised if the request to the api failed

        Returns:
            cryptography.hazmat.primitives.asymmetric.rsa.RSAPublicKey:
            Public key as a cryptography object

        """
        try:
            response = requests.get("http://127.0.0.1:8080/public-key")
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to request public key: {e}")
            raise RequestException("Failed to request public key")

        public_key_json = response.json()
        public_key = serialization.load_pem_public_key(
            public_key_json["public_key"].encode("utf-8")
        )

        logging.info("Public key successfully received")
        return public_key

    def _encrypt_bot_id(self, request_key=False):
        """Encrypt bot token with the public key and return it as a base64 string

        Args:
            request_key (bool): If True, requests the public key from the api. Else,
              tries to use the cached key.

        Raises:
            RequestException: Raised if the public key request to the api failed

        Returns:
            str: Encrypted bot token as a base64 string

        """
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

        logging.info("Bot id successfully encrypted")
        return encrypted_data_base64


class AdminSession(CustomSession):
    """Extend `CustomSession` class with admin specific properties and methods"""

    def __init__(self):
        super().__init__(BOT_TOKEN)

    def login(self, encrypted_bot_id) -> bool:
        """Logs in session to the api as admin with the given `encrypted_bot_id`

        Args:
            encrypted_bot_id (str): Bot id encrypted with the public key

        Raises:
            RequestException: Raised if the request to the api failed

        Returns:
            bool: True if the login was successful
        """
        try:
            login_response = self.get(
                "http://127.0.0.1:8080/admin/login",
                params={"encrypted_bot_id": encrypted_bot_id},
            )
            login_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to login as admin to the api: {e}")
            raise RequestException("Failed to login to api")

        csrf_access_token = self.cookies["csrf_access_token"]
        self.headers.update({"X-CSRF-TOKEN": csrf_access_token})

        logging.info("Admin successfully logged in to the api")
        return True


def post_request(user_id, data_json) -> requests.Response:
    """Post request to the api with the given user id and data

    Doesn't handle exceptions, raises them to the caller.

    Args:
        user_id (str): id of the user
        data_json (dict): data to be posted

    Returns:
        requests.Response: Response object of the post request

    """
    user_session = session_manager.get_session(user_id)

    logging.info(f"Posting data: {data_json} from user: {user_id}")
    post_response = user_session.post("http://127.0.0.1:8080/birthdays", json=data_json)

    return post_response


def get_request(user_id) -> requests.Response:
    """Get request to the api with the given user id

    Doesn't handle exceptions, raises them to the caller.

    Args:
        user_id (str): id of the user

    Returns:
        requests.Response: Response object of the get request
    """
    user_session = session_manager.get_session(user_id)

    logging.info(f"Getting data for user: {user_id}")
    get_response = user_session.get("http://127.0.0.1:8080/birthdays")

    return get_response


def get_by_id_request(user_id, birthday_id) -> requests.Response:
    """Get request to the api with the given user id and birthday id

    Doesn't handle exceptions, raises them to the caller.

    Args:
        user_id (str): id of the user
        birthday_id (str): id of the birthday

    Returns:
        requests.Response: Response object of the get request
    """
    user_session = session_manager.get_session(user_id)

    logging.info(f"Getting data for user: {user_id} with birthday_id: {birthday_id}")
    get_response = user_session.get(f"http://127.0.0.1:8080/birthdays/{birthday_id}")

    return get_response


def put_request(user_id, birthday_id, data_json) -> requests.Response:
    """Put request to the api with the given user id and data

    Doesn't handle exceptions, raises them to the caller.

    Args:
        user_id (str): id of the user
        birthday_id (str): id of the birthday
        data_json (dict): data to be put

    Returns:
        requests.Response: Response object of the put request
    """
    user_session = session_manager.get_session(user_id)

    logging.info(f"Putting data: {data_json} from user: {user_id}")
    put_response = user_session.put(
        f"http://127.0.0.1:8080/birthdays/{birthday_id}", json=data_json
    )

    return put_response


def delete_request(user_id, birthday_id) -> requests.Response:
    """Delete request to the api with the given user id and birthday id

    Doesn't handle exceptions, raises them to the caller.

    Args:
        user_id (str): id of the user
        birthday_id (str): id of the birthday

    Returns:
        requests.Response: Response object of the delete request
    """
    user_session = session_manager.get_session(user_id)

    logging.info(f"Deleting birthday with id: {birthday_id} from user: {user_id}")
    delete_response = user_session.delete(
        f"http://127.0.0.1:8080/birthdays/{birthday_id}"
    )

    return delete_response


def incoming_birthdays_request() -> requests.Response:
    """Get request to the api as admin to get incoming birthdays

    Doesn't handle exceptions, raises them to the caller.

    Returns:
        requests.Response: Response object of the get request
    """

    admin_session = session_manager.get_session(BOT_TOKEN)

    logging.info("Getting incoming birthdays")
    response = admin_session.get("http://127.0.0.1:8080/admin/birthdays/incoming")

    return response
