from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

from flask import Flask, redirect, render_template, request, session, url_for


BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "designvault.json"

app = Flask(__name__)
app.secret_key = "designvault-demo-secret"


SEED_INSPIRATIONS = [
    {"id": "i1", "name": "SaaS Launch Panel", "category": "SaaS", "style": "Bold", "score": 92, "colors": ["#10131f", "#7c5cff", "#d9ff4a"], "saved": True},
    {"id": "i2", "name": "Luxury Portfolio", "category": "Portfolio", "style": "Luxury", "score": 88, "colors": ["#080808", "#f4e7cf", "#c9964b"], "saved": False},
    {"id": "i3", "name": "Health Dashboard", "category": "Healthcare", "style": "Minimal", "score": 84, "colors": ["#eef7f4", "#2d8f78", "#101620"], "saved": True},
    {"id": "i4", "name": "Creator Shop", "category": "Ecommerce", "style": "Playful", "score": 79, "colors": ["#fff3e8", "#ff5c8a", "#2837ff"], "saved": False},
]

STYLE_PRESETS = {
    "Corporate": ["#0b1220", "#2f6bff", "#f6f8ff"],
    "Playful": ["#fff3e8", "#ff5c8a", "#2837ff"],
    "Luxury": ["#080808", "#f4e7cf", "#c9964b"],
    "Minimal": ["#f7f7f2", "#111111", "#c7d4cc"],
    "Bold": ["#10131f", "#7c5cff", "#d9ff4a"],
}


def default_store() -> dict:
    return {"users": {}, "vaults": {}}


def load_store() -> dict:
    if not DATA_FILE.exists():
        return default_store()
    store = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    store.setdefault("users", {})
    store.setdefault("vaults", {})
    return store


def save_store(store: dict) -> None:
    DATA_FILE.parent.mkdir(exist_ok=True)
    DATA_FILE.write_text(json.dumps(store, indent=2), encoding="utf-8")


def password_hash(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def current_user() -> dict | None:
    user_id = session.get("user_id")
    if not user_id:
        return None
    return load_store()["users"].get(user_id)


def vault_for(user_id: str) -> dict:
    store = load_store()
    if user_id not in store["vaults"]:
        store["vaults"][user_id] = {"inspirations": json.loads(json.dumps(SEED_INSPIRATIONS)), "briefs": []}
        save_store(store)
    return store["vaults"][user_id]


def save_vault(user_id: str, vault: dict) -> None:
    store = load_store()
    store["vaults"][user_id] = vault
    save_store(store)


@app.route("/", methods=["GET", "POST"])
def login():
    if current_user():
        return redirect(url_for("dashboard"))

    message = ""
    mode = request.form.get("mode") or request.args.get("mode", "login")

    if request.method == "POST":
        store = load_store()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        name = request.form.get("name", "").strip()

        if not email or not password:
            message = "Email and password are required."
        elif mode == "register":
            if not name:
                message = "Name is required."
            elif any(user["email"] == email for user in store["users"].values()):
                message = "That account already exists."
            else:
                user_id = uuid.uuid4().hex
                store["users"][user_id] = {"id": user_id, "name": name, "email": email, "password_hash": password_hash(password)}
                store["vaults"][user_id] = {"inspirations": json.loads(json.dumps(SEED_INSPIRATIONS)), "briefs": []}
                save_store(store)
                session["user_id"] = user_id
                return redirect(url_for("dashboard"))
        else:
            user = next((candidate for candidate in store["users"].values() if candidate["email"] == email), None)
            if not user or user["password_hash"] != password_hash(password):
                message = "Account not found. Create one first."
            else:
                session["user_id"] = user["id"]
                return redirect(url_for("dashboard"))

    return render_template("login.html", message=message, mode=mode)


@app.route("/dashboard")
def dashboard():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    vault = vault_for(user["id"])
    category = request.args.get("category", "All")
    style = request.args.get("style", "All")
    inspirations = [
        item
        for item in vault["inspirations"]
        if (category == "All" or item["category"] == category) and (style == "All" or item["style"] == style)
    ]
    categories = ["All", *sorted({item["category"] for item in vault["inspirations"]})]
    styles = ["All", *STYLE_PRESETS.keys()]
    saved_count = sum(1 for item in vault["inspirations"] if item["saved"])
    avg_score = round(sum(item["score"] for item in vault["inspirations"]) / max(1, len(vault["inspirations"])))

    return render_template(
        "dashboard.html",
        user=user,
        vault=vault,
        inspirations=inspirations,
        categories=categories,
        styles=styles,
        category=category,
        style=style,
        saved_count=saved_count,
        avg_score=avg_score,
        presets=STYLE_PRESETS,
    )


@app.route("/brief/add", methods=["POST"])
def add_brief():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    vault = vault_for(user["id"])
    style = request.form.get("style", "Bold")
    industry = request.form.get("industry", "Startup").strip()
    score = min(99, 70 + len(industry) + len(style))
    colors = STYLE_PRESETS.get(style, STYLE_PRESETS["Bold"])
    brief = {
        "id": uuid.uuid4().hex,
        "business": request.form.get("business", "Untitled Brand").strip(),
        "industry": industry,
        "style": style,
        "score": score,
        "colors": colors,
    }
    vault["briefs"].insert(0, brief)
    vault["inspirations"].insert(
        0,
        {
            "id": uuid.uuid4().hex,
            "name": f"{brief['business']} Direction",
            "category": industry,
            "style": style,
            "score": score,
            "colors": colors,
            "saved": True,
        },
    )
    save_vault(user["id"], vault)
    return redirect(url_for("dashboard"))


@app.route("/inspiration/<item_id>/<action>", methods=["POST"])
def inspiration_action(item_id: str, action: str):
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    vault = vault_for(user["id"])
    for item in vault["inspirations"]:
        if item["id"] != item_id:
            continue
        if action == "save":
            item["saved"] = not item["saved"]
        elif action == "boost":
            item["score"] = min(100, item["score"] + 3)
        elif action == "delete":
            vault["inspirations"] = [candidate for candidate in vault["inspirations"] if candidate["id"] != item_id]
        break

    save_vault(user["id"], vault)
    return redirect(request.referrer or url_for("dashboard"))


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    app.run(debug=True, port=5185)
