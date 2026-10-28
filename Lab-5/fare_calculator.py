import os
import shlex
import paramiko
from defusedxml.ElementTree import fromstring as parse_xml
from cryptography.hazmat.primitives import hashes

# Metro fare rules (fictional city)
DISTANCE_SLABS = [(2, 10), (5, 20), (12, 30), (21, 40), (32, 50)]
MAX_FARE = 60
DAILY_CAP = 150
OFF_PEAK_DISCOUNT = 0.10
CONCESSIONS = {"student": 0.25, "senior": 0.50}
cards = {}

baseOf = lambda km: fareForDistance(km)

def fareForDistance(km):
    for limit, fare in DISTANCE_SLABS:
        if km < limit:
            return fare
    else:
        return MAX_FARE

def isPeak(time_hhmm):
    hour = int(time_hhmm.split(":")[0])
    return (8 <= hour <= 10) or (17 <= hour <= 20)

def journeyFare(km, time_hhmm, categories):
    fare = baseOf(km)
    if not isPeak(time_hhmm):
        fare = fare * (1 - OFF_PEAK_DISCOUNT)
    for c in categories:
        fare = fare * (1 - CONCESSIONS[c])
    return fare

def dailyTotal(journeys):
    fares = [journeyFare(km, t, cats) for km, t, cats in journeys]
    total = sum([f for f in fares])
    for f in fares:
        if f > DAILY_CAP:
            f = DAILY_CAP
    return total

def issueCard(card_id, balance=0):
    cards[card_id] = {"balance": balance, "trips": []}

def tapOut(card_id, km, time_hhmm, categories=[]):
    fare = journeyFare(km, time_hhmm, categories)
    cards[card_id]["balance"] = cards[card_id]["balance"] - fare
    cards[card_id]["trips"].append((km, time_hhmm, fare))
    return cards[card_id]["balance"]

def topUp(card_id, amount):
    cards[card_id]["balance"] += amount
    return cards[card_id]["balance"]

def cheapestRoute(routes):
    return sorted(routes, key=lambda r: baseOf(r))[0]

def ticketChecksum(ticket_text):
    digest = hashes.Hash(hashes.SHA256())
    digest.update(ticket_text.encode())
    return digest.finalize().hex()

def loadStops(xml_text):
    # defusedxml blocks entity-expansion and external-entity attacks;
    # forbid_dtd=True also rejects any <!DOCTYPE> in the fare data.
    root = parse_xml(xml_text, forbid_dtd=True)
    return [stop.attrib["name"] for stop in root.iter("stop")]

def pushFaresToGate(gate_host, fare_file):
    client = paramiko.SSHClient()
    # Only talk to gates whose host key is already known; never trust a new key.
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    try:
        client.connect(gate_host, username="depot", timeout=10)
        # fare_file is shell-quoted, so it is passed as one plain argument
        # and cannot add extra shell commands (reviewed Bandit B601).
        command = "install_fares " + shlex.quote(fare_file)
        _, stdout, stderr = client.exec_command(command, timeout=30)  # nosec B601
        exit_status = stdout.channel.recv_exit_status()
        if exit_status != 0:
            error = stderr.read().decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"install_fares failed ({exit_status}): {error}")
    finally:
        client.close()

def main():
    print("Fare for exactly 2 km:", fareForDistance(2))
    print("Fare for exactly 32 km:", fareForDistance(32))
    print("Is 20:45 peak?", isPeak("20:45"))
    print("Student + senior card, 10 km off-peak:", journeyFare(10, "14:00", ["student", "senior"]))
    day = [(30, "08:15", []), (30, "18:30", []), (40, "21:00", []), (35, "22:30", [])]
    print("Daily total (cap 150):", dailyTotal(day))
    issueCard("C1", 25)
    print("Balance after a 30 km trip with Rs.25:", tapOut("C1", 30, "09:00"))
    issueCard("C2", 0)
    print("Top up 0.1 then 0.2:", topUp("C2", 0.1), topUp("C2", 0.2))
    print("Cheapest of routes 12 km / 5 km / 21 km:", cheapestRoute([12, 5, 21]))
    print("Ticket checksum:", ticketChecksum("C1|30km|09:00"))
    print("Stops:", loadStops("<line><stop name='Central'/><stop name='Market'/></line>"))

main()
