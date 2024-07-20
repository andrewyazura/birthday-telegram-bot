import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
import base64
import time

from config import BOT_TOKEN

PUBLIC_KEY = None


class UserSessionManager:
    def __init__(self):
        self.sessions = {}

    def get_session(self, user_id):
        if user_id not in self.sessions or self.sessions[user_id].is_expired():
            self.sessions[user_id] = UserSession(user_id)

        return self.sessions[user_id]


class UserSession(requests.Session):
    def __init__(self, user_id):
        super().__init__()
        self.user_id = user_id
        self.time_created = time.time()
        self.login(encrypt_bot_id())
        self.hooks["response"].append(self.pre_request_hook)

    # expires in 15 minutes
    def is_expired(self):
        return time.time() - self.time_created > 3600

    def login(self, encrypted_bot_id):
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
        # This function will be executed before each request
        if self.is_expired():
            self.login(encrypt_bot_id())


session_manager = UserSessionManager()
# Example usage
# user1_session = session_manager.get_session("user1")
# response = user1_session.get("https://example.com")


def request_public_key():
    response = requests.get("http://127.0.0.1:8080/public-key")

    if response.status_code != 200:
        print(f"Failed to get api key. code: {response.status_code}")

    public_key_json = response.json()
    public_key = serialization.load_pem_public_key(
        public_key_json["public_key"].encode("utf-8")
    )
    return public_key


def encrypt_bot_id(request_key=False):
    global PUBLIC_KEY

    if PUBLIC_KEY is None or request_key:
        PUBLIC_KEY = request_public_key()

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


# def login_user_session(user_session, encrypted_bot_id, id):
#     login_response = user_session.get(
#         "http://127.0.0.1:8080/login",
#         params={"encrypted_bot_id": encrypted_bot_id, "id": id},
#     )
#     if login_response.status_code != 200:
#         print(f"Failed to login to api. {login_response.status_code}")  # fix later

#     csrf_access_token = user_session.cookies["csrf_access_token"]

#     user_session.headers.update({"X-CSRF-TOKEN": csrf_access_token})


def post_request(id, data_json):
    user_session = session_manager.get_session(id)

    post_response = user_session.post("http://127.0.0.1:8080/birthdays", json=data_json)
    if post_response.status_code != 201:
        print(f"Failed to add birthday. {post_response.json()}")  # fix later
    else:
        print(post_response.json())

    return post_response
