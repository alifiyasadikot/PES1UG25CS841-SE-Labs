"""Metro fare calculator for a fictional city's public transit system."""
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


def fare_for_distance(km):
    """Return the base fare for a journey of the given distance in km."""
    for limit, fare in DISTANCE_SLABS:
        if km < limit:
            return fare
    return MAX_FARE


def is_peak(time_hhmm):
    """Return True if the given HH:MM time is in a peak period."""
    hour = int(time_hhmm.split(":")[0])
    return (8 <= hour <= 10) or (17 <= hour <= 20)


def journey_fare(km, time_hhmm, categories):
    """Return the fare for one journey after any discounts."""
    fare = fare_for_distance(km)
    if not is_peak(time_hhmm):
        fare = fare * (1 - OFF_PEAK_DISCOUNT)
    for category in categories:
        fare = fare * (1 - CONCESSIONS[category])
    return fare


def daily_total(journeys):
    """Return the total fare for a day of journeys, capped at DAILY_CAP."""
    fares = [journey_fare(km, time_hhmm, categories)
             for km, time_hhmm, categories in journeys]
    return min(sum(fares), DAILY_CAP)


def issue_card(card_id, balance=0):
    """Create a smart card with an opening balance."""
    cards[card_id] = {"balance": balance, "trips": []}


def tap_out(card_id, km, time_hhmm, categories=None):
    """Charge a journey to a card and return the new balance."""
    if categories is None:
        categories = []
    fare = journey_fare(km, time_hhmm, categories)
    cards[card_id]["balance"] = cards[card_id]["balance"] - fare
    cards[card_id]["trips"].append((km, time_hhmm, fare))
    return cards[card_id]["balance"]


def top_up(card_id, amount):
    """Add money to a card and return the new balance."""
    cards[card_id]["balance"] += amount
    return cards[card_id]["balance"]


def cheapest_route(routes):
    """Return the route distance with the lowest base fare."""
    return min(routes, key=fare_for_distance)


def ticket_checksum(ticket_text):
    """Return a SHA-256 checksum of the ticket text as hex."""
    digest = hashes.Hash(hashes.SHA256())
    digest.update(ticket_text.encode())
    return digest.finalize().hex()


def load_stops(xml_text):
    """Return the stop names listed in a line's XML description."""
    # defusedxml blocks entity-expansion and external-entity attacks;
    # forbid_dtd=True also rejects any <!DOCTYPE> in the fare data.
    root = parse_xml(xml_text, forbid_dtd=True)
    return [stop.attrib["name"] for stop in root.iter("stop")]


def push_fares_to_gate(gate_host, fare_file):
    """Install a fare file on a gate machine over a verified SSH link."""
    client = paramiko.SSHClient()
    # Only connect to gates whose host key is already known.
    client.load_system_host_keys()
    client.set_missing_host_key_policy(paramiko.RejectPolicy())
    try:
        client.connect(gate_host, username="depot", timeout=10)
        # fare_file is shell-quoted, so it is passed as one plain argument
        # and cannot add extra shell commands (reviewed Bandit B601).
        command = "install_fares " + shlex.quote(fare_file)
        _, out, err = client.exec_command(command, timeout=30)  # nosec B601
        exit_status = out.channel.recv_exit_status()
        if exit_status != 0:
            error = err.read().decode("utf-8", errors="replace").strip()
            raise RuntimeError(
                f"install_fares failed ({exit_status}): {error}")
    finally:
        client.close()


def main():
    """Print sample fares, card balances and stops."""
    print("Fare for exactly 2 km:", fare_for_distance(2))
    print("Fare for exactly 32 km:", fare_for_distance(32))
    print("Is 20:45 peak?", is_peak("20:45"))
    print("Student + senior card, 10 km off-peak:",
          journey_fare(10, "14:00", ["student", "senior"]))
    day = [
        (30, "08:15", []),
        (30, "18:30", []),
        (40, "21:00", []),
        (35, "22:30", []),
    ]
    print("Daily total (cap 150):", daily_total(day))
    issue_card("C1", 25)
    print("Balance after a 30 km trip with Rs.25:",
          tap_out("C1", 30, "09:00"))
    issue_card("C2", 0)
    print("Top up 0.1 then 0.2:", top_up("C2", 0.1), top_up("C2", 0.2))
    print("Cheapest of routes 12 km / 5 km / 21 km:",
          cheapest_route([12, 5, 21]))
    print("Ticket checksum:", ticket_checksum("C1|30km|09:00"))
    line_xml = "<line><stop name='Central'/><stop name='Market'/></line>"
    print("Stops:", load_stops(line_xml))


if __name__ == "__main__":
    main()
