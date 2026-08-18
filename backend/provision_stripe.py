import os, json, urllib.request
import stripe

base = os.environ["INTEGRATION_PROXY_URL"]
job_id = "15dadd8b-4601-4691-b0d8-2f5b23f8b555"
key = "sk-emergent-68d20Ea23E2Df354eC"
req = urllib.request.Request(
    base + "/stripe/sandboxes",
    data=json.dumps({"job_id": job_id}).encode(),
    headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(req) as r:
    sandbox = json.load(r)

print("SANDBOX_SECRET=" + sandbox["sandbox_secret_key"])
print("SANDBOX_PUB=" + sandbox["sandbox_publishable_key"])
print("SANDBOX_ACCOUNT=" + sandbox["sandbox_account_id"])
print("WEBHOOK_SECRET=" + sandbox["preview_webhook_secret"])
print("ONBOARDING_URL=" + sandbox.get("onboarding_url", ""))

stripe.api_key = sandbox["sandbox_secret_key"]
country = stripe.Account.retrieve()["country"]
print("COUNTRY=" + country)
