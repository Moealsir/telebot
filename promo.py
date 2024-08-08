import requests
import random
import string
import sqlite3
import time
import json
from concurrent.futures import ThreadPoolExecutor

# Define API endpoints
LOGIN_URL = "https://api.gamepromo.io/promo/login-client"
REGISTER_EVENT_URL = "https://api.gamepromo.io/promo/register-event"
CREATE_CODE_URL = "https://api.gamepromo.io/promo/create-code"

# Load user agents from file
def load_user_agents(file_path):
    with open(file_path, 'r') as f:
        return [line.strip() for line in f]

# Function to get a random user agent
def get_random_user_agent(user_agents):
    return random.choice(user_agents)

# Define base headers (common across all requests)
def get_base_headers(user_agent):
    platform = get_sec_ch_ua_platform(user_agent)
    return {
        "authority": "api.gamepromo.io",
        "accept": "*/*",
        "accept-language": "en-GB,en-US;q=0.9,en;q=0.8",
        "origin": "https://iappsbest.github.io",
        "referer": "https://iappsbest.github.io/",
        "sec-ch-ua": f'"Not-A.Brand";v="99", "Chromium";v="124", "{platform}";v="1"',
        "sec-ch-ua-mobile": "?1",
        "sec-ch-ua-platform": platform,
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "cross-site",
        "user-agent": user_agent
    }

# Function to generate a random 19-character client ID
def generate_client_id():
    timestamp = str(int(time.time() * 1000))
    random_chars = str(random.randint(10**18, 10**19 - 1))
    return timestamp + "-" + random_chars

def login(app_token, user_agents):
    user_agent = get_random_user_agent(user_agents)
    login_data = {"appToken": app_token, "clientId": generate_client_id(), "clientOrigin": "deviceid"}
    login_headers = get_base_headers(user_agent)
    login_headers["content-type"] = "application/json"
    response = requests.post(LOGIN_URL, headers=login_headers, json=login_data, verify=True)  # Enable SSL verification
    response.raise_for_status()
    while(response.status_code != 200):
        time.sleep(10)
        response = requests.post(LOGIN_URL, headers=login_headers, json=login_data, verify=True)  # Enable SSL verification
        response.raise_for_status()
    return response.json()["clientToken"]

def register_event(client_token, promo_id, user_agents, max_retries=100):
    user_agent = get_random_user_agent(user_agents)
    event_id = generate_client_id()
    authorization = f"Bearer {client_token}"
    register_data = {"promoId": promo_id, "eventId": event_id, "eventOrigin": "undefined"}
    register_headers = get_base_headers(user_agent)
    register_headers["authorization"] = authorization
    register_headers["content-type"] = "application/json"
    for attempt in range(1, max_retries + 1):
        response = requests.post(REGISTER_EVENT_URL, headers=register_headers, json=register_data, verify=True)  # Enable SSL verification
        if response.status_code == 200:
            return response.json()
        else:
            time.sleep(1)  # Add a short delay between retries
    raise Exception(f"Failed to register event for promo ID {promo_id} after {max_retries} attempts")  # Raise exception if all retries fail

def create_code(client_token, promo_id, user_agents):
    user_agent = get_random_user_agent(user_agents)
    authorization = f"Bearer {client_token}"
    create_code_data = {"promoId": promo_id}
    create_code_headers = get_base_headers(user_agent)
    create_code_headers["authorization"] = authorization
    create_code_headers["content-type"] = "application/json"
    response = requests.post(CREATE_CODE_URL, headers=create_code_headers, json=create_code_data, verify=True)  # Enable SSL verification
    response.raise_for_status()
    return response.json()["promoCode"]

def handle_database(promo_code):
    with open('keys.txt', 'a') as f:  # Open in append mode
        f.write(promo_code + '\n')  # Write the promo code followed by a newline

def get_sec_ch_ua_platform(user_agent):
    if "Linux" in user_agent:
        return "Linux"
    elif "Windows" in user_agent:
        return "Windows"
    elif "Macintosh" in user_agent:
        return "macOS"
    elif "iPad" in user_agent:
        return "iOS"
    else:
        return "Unknown"

def process_promo(app_token, promo_id, user_agents):
    try:
        client_token = login(app_token, user_agents)
        register_response = register_event(client_token, promo_id, user_agents)
        reg = register_response['hasCode']
        if register_response['hasCode']:
            promo_code = create_code(client_token, promo_id, user_agents)
            handle_database(promo_code)
            print(f"Promo ID {promo_id} processed successfully: {promo_code}")
        while not reg:
            register_response = register_event(client_token, promo_id, user_agents)
            if register_response['hasCode']:
                promo_code = create_code(client_token, promo_id, user_agents)
                handle_database(promo_code)
                print(f"Promo ID {promo_id} processed successfully: {promo_code}")
                reg = register_response['hasCode']
    except Exception as e:
        pass
        # print(f"Error processing promo ID {promo_id}: {e}")

def main():
    user_agents = load_user_agents('user-agents.txt')
    
    app_tokens = [
        "74ee0b5b-775e-4bee-974f-63e7f4d5bacb",
        "d28721be-fd2d-4b45-869e-9f253b554e50",
        "d1690a07-3780-4068-810f-9b5bbf2931b2",
        "82647f43-3f87-402d-88dd-09a90025313f",
        # ... other app tokens
    ]
    promo_ids = [
        "fe693b26-b342-4159-8808-15e3ff7f8767",
        "43e35910-c168-4634-ad4f-52fd764a843f",
        "b4170868-cef0-424f-8eb9-be0622e8e8e3",
        "c4480ac7-e178-4973-8061-9ed5b2e17954",
        # ... other promo IDs
    ]

    if len(app_tokens) != len(promo_ids):
        raise ValueError("Number of app tokens must match number of promo IDs")

    with ThreadPoolExecutor(max_workers=4) as executor:
        for i in range(len(app_tokens)):
            executor.submit(process_promo, app_tokens[i], promo_ids[i], user_agents)

if __name__ == "__main__":
    while True:
        main()
        time.sleep(5)
