import requests
import sys

BASE_URL = "http://127.0.0.1:8000"
passed = 0
failed = 0

def test(name, method, url, data=None, expected_status=200):
    global passed, failed
    try:
        if method == "GET":
            res = requests.get(f"{BASE_URL}{url}")
        elif method == "POST":
            res = requests.post(f"{BASE_URL}{url}", json=data)
        elif method == "PATCH":
            res = requests.patch(f"{BASE_URL}{url}", json=data)
        elif method == "DELETE":
            res = requests.delete(f"{BASE_URL}{url}")
            
        if res.status_code == expected_status or (expected_status == 200 and res.status_code in (200, 201)):
            print(f"[PASS] {name} - {url}")
            passed += 1
        else:
            print(f"[FAIL] {name} - {url} | Expected {expected_status}, got {res.status_code} - {res.text}")
            failed += 1
    except Exception as e:
        print(f"[ERROR] {name} - {url} | {e}")
        failed += 1

print("--- Starting API Verification ---")
test("Get Services", "GET", "/api/services")
test("Get Time Slots", "GET", "/api/time-slots")
test("Get Slot Cards (no date)", "GET", "/api/slot-cards")
test("Get Slot Cards (with date)", "GET", "/api/slot-cards/2026-06-28")
test("Get Stylists", "GET", "/api/stylists")
test("Get Bookings", "GET", "/api/bookings")
test("Create Booking", "POST", "/api/bookings", data={
    "customer_name": "Test User",
    "phone": "9999999999",
    "age": "30",
    "service": "Haircut",
    "appointment_date": "2026-07-01",
    "time_slot": "10:00 AM"
})
test("Get Dashboard Stats", "GET", "/api/dashboard-stats")
test("Get Gallery", "GET", "/api/gallery")

print(f"--- Complete: {passed} passed, {failed} failed ---")
