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
app.config["SEND_FILE_MAX_AGE_DEFAULT"] = 0


@app.after_request
def add_no_cache_headers(response):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


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

INDUSTRIES = ["Technology", "Healthcare", "Finance", "Restaurants", "Law Firms", "Real Estate", "Consulting", "Automotive", "Travel"]

PACKAGES = {
    "starter": {"name": "Starter Site", "price": 999, "features": ["5 custom sections", "Mobile-ready layout", "Lead capture form"]},
    "pro": {"name": "Professional Website", "price": 5000, "features": ["8 custom pages", "Conversion sections", "SEO-ready structure", "Advanced animations"]},
    "elite": {"name": "Elite Brand System", "price": 9500, "features": ["15 page system", "Brand direction", "Motion guidelines", "Launch checklist"]},
}

ADDONS = {
    "domain": {"name": "Domain & Setup", "price": 1000},
    "seo": {"name": "SEO Boost Pack", "price": 2000},
    "brand": {"name": "Brand Kit & Logo", "price": 2500},
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
        store["vaults"][user_id] = {"inspirations": json.loads(json.dumps(SEED_INSPIRATIONS)), "briefs": [], "audit": {}, "cart": {"package": "pro", "addons": []}, "orders": []}
        save_store(store)
    vault = store["vaults"][user_id]
    vault.setdefault("inspirations", json.loads(json.dumps(SEED_INSPIRATIONS)))
    vault.setdefault("briefs", [])
    vault.setdefault("audit", {})
    vault.setdefault("cart", {"package": "pro", "addons": []})
    vault.setdefault("orders", [])
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
                store["vaults"][user_id] = {"inspirations": json.loads(json.dumps(SEED_INSPIRATIONS)), "briefs": [], "audit": {}, "cart": {"package": "pro", "addons": []}, "orders": []}
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
    cart = vault["cart"]
    package = PACKAGES.get(cart.get("package", "pro"), PACKAGES["pro"])
    selected_addons = [ADDONS[key] for key in cart.get("addons", []) if key in ADDONS]
    total = package["price"] + sum(addon["price"] for addon in selected_addons)

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
        industries=INDUSTRIES,
        packages=PACKAGES,
        addons=ADDONS,
        package=package,
        selected_addons=selected_addons,
        total=total,
    )


@app.route("/audit", methods=["POST"])
def audit():
    user = current_user()
    if not user:
        return redirect(url_for("login"))

    vault = vault_for(user["id"])
    business = request.form.get("business", "Untitled Business").strip()
    website = request.form.get("website", "your-old-site.com").strip()
    industry = request.form.get("industry", "Technology")
    style = request.form.get("style", "Bold")
    score = max(2, min(8, 10 - (len(website) % 5)))
    vault["audit"] = {
        "business": business,
        "website": website,
        "industry": industry,
        "style": style,
        "score": score,
        "issues": ["Outdated first impression", "Weak mobile conversion", "Missing trust sections"],
        "new_url": f"https://{business.lower().replace(' ', '-')}.designvault.site",
    }
    save_vault(user["id"], vault)
    return redirect(url_for("dashboard") + "#audit")


@app.route("/package/<package_id>", methods=["POST"])
def choose_package(package_id: str):
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    if package_id not in PACKAGES:
        return redirect(url_for("dashboard"))
    vault = vault_for(user["id"])
    vault["cart"]["package"] = package_id
    save_vault(user["id"], vault)
    return redirect(url_for("dashboard") + "#order")


@app.route("/addon/<addon_id>", methods=["POST"])
def toggle_addon(addon_id: str):
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    if addon_id not in ADDONS:
        return redirect(url_for("dashboard"))
    vault = vault_for(user["id"])
    addons = vault["cart"].setdefault("addons", [])
    if addon_id in addons:
        addons.remove(addon_id)
    else:
        addons.append(addon_id)
    save_vault(user["id"], vault)
    return redirect(url_for("dashboard") + "#cart")


@app.route("/checkout", methods=["POST"])
def checkout():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    vault = vault_for(user["id"])
    package = PACKAGES.get(vault["cart"].get("package", "pro"), PACKAGES["pro"])
    selected_addons = [ADDONS[key] for key in vault["cart"].get("addons", []) if key in ADDONS]
    total = package["price"] + sum(addon["price"] for addon in selected_addons)
    order = {
        "id": uuid.uuid4().hex[:8].upper(),
        "package": package["name"],
        "total": total,
        "business": vault.get("audit", {}).get("business", "Your New Website"),
    }
    vault["orders"].insert(0, order)
    save_vault(user["id"], vault)
    return redirect(url_for("dashboard") + "#confirmed")


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
