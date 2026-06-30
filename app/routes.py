from datetime import datetime

from flask import Blueprint, jsonify, request

from app.extensions import db
from app.models import Client, ClientParking, Parking

api_bp = Blueprint("api", __name__)


@api_bp.route("/clients", methods=["GET"])
def get_clients():
    clients = Client.query.all()
    return jsonify([client.to_dict() for client in clients]), 200


@api_bp.route("/clients/<int:client_id>", methods=["GET"])
def get_client(client_id):
    # Используем db.session.get() вместо Client.query.get()
    client = db.session.get(Client, client_id)
    if not client:
        return jsonify({"error": "Client not found"}), 404
    return jsonify(client.to_dict()), 200


@api_bp.route("/clients", methods=["POST"])
def create_client():
    data = request.get_json()

    if not data.get("name") or not data.get("surname"):
        return jsonify({"error": "Name and surname are required"}), 400

    client = Client(
        name=data["name"],
        surname=data["surname"],
        credit_card=data.get("credit_card"),
        car_number=data.get("car_number"),
    )

    db.session.add(client)
    db.session.commit()

    return jsonify(client.to_dict()), 201


@api_bp.route("/parkings", methods=["POST"])
def create_parking():
    data = request.get_json()

    if not data.get("address") or not data.get("count_places"):
        return jsonify({"error": "Address and count_places are required"}), 400

    count_places = data["count_places"]
    parking = Parking(
        address=data["address"],
        opened=data.get("opened", True),
        count_places=count_places,
        count_available_places=count_places,
    )

    db.session.add(parking)
    db.session.commit()

    return jsonify(parking.to_dict()), 201


@api_bp.route("/client_parkings", methods=["POST"])
def enter_parking():
    data = request.get_json()

    if not data.get("client_id") or not data.get("parking_id"):
        return jsonify({"error": "client_id and parking_id are required"}), 400

    # Используем db.session.get() вместо Client.query.get()
    client = db.session.get(Client, data["client_id"])
    if not client:
        return jsonify({"error": "Client not found"}), 404

    # Проверяем наличие кредитной карты при заезде
    if not client.credit_card:
        return jsonify({"error": "Client has no credit card attached"}), 400

    # Используем db.session.get() вместо Parking.query.get()
    parking = db.session.get(Parking, data["parking_id"])
    if not parking:
        return jsonify({"error": "Parking not found"}), 404

    if not parking.opened:
        return jsonify({"error": "Parking is closed"}), 400

    if parking.count_available_places <= 0:
        return jsonify({"error": "No available places"}), 400

    existing_entry = ClientParking.query.filter_by(
        client_id=data["client_id"], parking_id=data["parking_id"], time_out=None
    ).first()

    if existing_entry:
        return jsonify({"error": "Client already parked at this parking"}), 400

    client_parking = ClientParking(
        client_id=data["client_id"],
        parking_id=data["parking_id"],
        time_in=datetime.now(),
    )

    parking.count_available_places -= 1

    db.session.add(client_parking)
    db.session.commit()

    return jsonify(client_parking.to_dict()), 201


@api_bp.route("/client_parkings", methods=["DELETE"])
def exit_parking():
    data = request.get_json()

    if not data.get("client_id") or not data.get("parking_id"):
        return jsonify({"error": "client_id and parking_id are required"}), 400

    client_parking = ClientParking.query.filter_by(
        client_id=data["client_id"], parking_id=data["parking_id"], time_out=None
    ).first()

    if not client_parking:
        return jsonify({"error": "No active parking found"}), 404

    # Используем db.session.get() вместо Client.query.get()
    client = db.session.get(Client, data["client_id"])
    if not client:
        return jsonify({"error": "Client not found"}), 404

    # Проверяем наличие кредитной карты при выезде
    if not client.credit_card:
        return jsonify({"error": "Client has no credit card attached"}), 400

    client_parking.time_out = datetime.now()

    if client_parking.time_out <= client_parking.time_in:
        return jsonify({"error": "Invalid time_out"}), 400

    # Используем db.session.get() вместо Parking.query.get()
    parking = db.session.get(Parking, data["parking_id"])
    if not parking:
        return jsonify({"error": "Parking not found"}), 404

    parking.count_available_places += 1

    db.session.commit()

    return jsonify(client_parking.to_dict()), 200
