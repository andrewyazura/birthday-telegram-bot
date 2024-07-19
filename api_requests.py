import requests
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import hashes
import base64
from birthday_bot import BOT_TOKEN, PUBLIC_KEY


class UserSessionManager:
    def __init__(self):
        self.sessions = {}

    def get_session(self, user_id):
        if user_id not in self.sessions:
            self.sessions[user_id] = requests.Session()
        return self.sessions[user_id]
    
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
    # get public key once, store it and use. request only if request_key is True(if login failed try to request for a key)
    if PUBLIC_KEY is None or request_key:
        public_key = request_public_key()
    else:
        public_key = PUBLIC_KEY  # fix later

    encrypted_data = public_key.encrypt(
        BOT_TOKEN.encode("utf-8"),
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    encrypted_data_base64 = base64.b64encode(encrypted_data).decode("utf-8")
    return encrypted_data_base64


def login_user_session(user_session, encrypted_bot_id, id):
    login_response = user_session.get(
        "http://127.0.0.1:8080/login",
        params={"encrypted_bot_id": encrypted_bot_id, "id": 651472384},
    )
    if login_response.status_code != 200:
        print(f"Failed to login to api. {login_response.status_code}")  # fix later

    csrf_access_token = user_session.cookies["csrf_access_token"]

    user_session.headers.update({"X-CSRF-TOKEN": csrf_access_token})


def post_request(id, data_json):
    encrypted_bot_id = encrypt_bot_id()

    user_session = session_manager.get_session(id)

    login_user_session(user_session, encrypted_bot_id, id)

    post_response = user_session.post("http://127.0.0.1:8080/birthdays", json=data_json)
    if post_response.status_code != 201:
        print(f"Failed to add birthday. {post_response.json()}")
    else:
        print(post_response.json())

    return post_response
