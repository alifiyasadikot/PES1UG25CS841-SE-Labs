import os
import xml.sax
import paramiko
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
    digest = hashes.Hash(hashes.MD5())
    digest.update(ticket_text.encode())
    return digest.finalize().hex()

class StopHandler(xml.sax.ContentHandler):
    def __init__(self):
        super().__init__()
        self.stops = []

    def startElement(self, name, attrs):
        if name == "stop":
            self.stops.append(attrs["name"])

def loadStops(xml_text):
    handler = StopHandler()
    xml.sax.parseString(xml_text.encode(), handler)
    return handler.stops

def pushFaresToGate(gate_host, fare_file):
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(gate_host, username="depot")
    client.exec_command("install_fares " + fare_file)
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
