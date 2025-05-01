from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# 🧭 Routes des microservices
SERVICE_MAP = {
    "reservation": "http://reservation:5000",
    "salle": "http://salle:5000",
    "user": "http://user:5000"  # 🔐 Service user
}

# 🔀 Fonction utilitaire de proxy
def proxy_request(service_name, path):
    base_url = SERVICE_MAP.get(service_name)
    if not base_url:
        return jsonify({"error": "Unknown service"}), 400

    url = f"{base_url}{path}"
    method = request.method
    headers = {k: v for k, v in request.headers if k != 'Host'}
    data = request.get_data()
    params = request.args
    print(url)
    try:
        resp = requests.request(method, url, headers=headers, data=data, params=params)
        return (resp.content, resp.status_code, resp.headers.items())
    except requests.exceptions.RequestException as e:
        return jsonify({"error": f"Failed to contact service: {str(e)}"}), 502
def is_token_valid():
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return False

    token = auth_header.split(" ")[1]

    try:
        resp = requests.get(
            f"{SERVICE_MAP['user']}/api/users/token/verify",
            headers={"Authorization": f"Bearer {token}"},
            timeout=3
        )
        print(resp.content)
        return resp.status_code == 200
    except requests.RequestException:
        return False
@app.before_request
def check_jwt():
    if request.path == "/api/users" or request.method=="POST":
        return
    # 🔓 Skip auth for health check or root
    if request.path == "/api/users/login" or request.path.startswith("/public"):
        return

    if not is_token_valid():
        return jsonify({"error": "Unauthorized"}), 401

# ✅ Route vers reservation microservice
@app.route("/api/reservation/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
@app.route("/api/reservation", defaults={"path": ""}, methods=["GET", "POST"])
def reservation_proxy(path):
    return proxy_request("reservation", f"/api/reservation/{path}" if path else "/api/reservation")

# ✅ Route vers salle microservice
@app.route("/api/salles/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
@app.route("/api/salles", defaults={"path": ""}, methods=["GET", "POST"])
def salle_proxy(path):
    print("hhhh")
    return proxy_request("salle", f"/api/salles/{path}" if path else "/api/salles")
@app.route("/api/users/<path:path>", methods=["GET", "POST", "PUT", "DELETE"])
@app.route("/api/users", defaults={"path": ""}, methods=["GET", "POST"])
def user_proxy(path):
    return proxy_request("user", f"/api/users/{path}" if path else "/api/users")
# ✅ Endpoint racine
@app.route("/")
def root():
    return jsonify({"message": "API Gateway is running"})

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=5000, debug=True)
