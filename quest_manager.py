import json
import os
import random
import string
from datetime import datetime

CONFIG_FILE = "config.json"
QUEST_FILE = "data/quests.json"

# Ensure data folder exists
os.makedirs("data", exist_ok=True)


def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {"guild_id": 0, "quest_role_id": 0, "log_channel_id": 0}
    with open(CONFIG_FILE, "r") as f:
        return json.load(f)


def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)


def load_quests():
    if not os.path.exists(QUEST_FILE):
        return {}
    with open(QUEST_FILE, "r") as f:
        return json.load(f)


def save_quests(data):
    with open(QUEST_FILE, "w") as f:
        json.dump(data, f, indent=4)


def generate_contract_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))


def create_quest(title, description, reward, deadline):
    quests = load_quests()
    contract_id = generate_contract_id()

    quest_data = {
        "title": title,
        "description": description,
        "reward": reward,
        "deadline": deadline,
        "contract_id": contract_id,
        "created_at": datetime.utcnow().isoformat(),
        "accepted": [],
        "declined": []
    }

    quests[contract_id] = quest_data
    save_quests(quests)
    return quest_data
