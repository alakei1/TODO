import os
import sys
from pathlib import Path

# Добавляем корневую директорию в PYTHONPATH
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from datetime import datetime, timedelta

import pytest

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import Client, ClientParking, Parking
from factories import ClientFactory, ParkingFactory


@pytest.fixture(scope="session")
def app():
    app = create_app(TestingConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


@pytest.fixture(scope="session")
def client(app):
    return app.test_client()


@pytest.fixture(scope="function")
def db_session(app):
    with app.app_context():
        # Clean up any existing data
        db.session.query(ClientParking).delete()
        db.session.query(Client).delete()
        db.session.query(Parking).delete()
        db.session.commit()

        # Create test data
        test_client = Client(
            name="John",
            surname="Doe",
            credit_card="1234567890123456",
            car_number="ABC123",
        )

        test_parking = Parking(
            address="Test Street 123",
            opened=True,
            count_places=10,
            count_available_places=8,
        )

        db.session.add(test_client)
        db.session.add(test_parking)
        db.session.flush()

        # Create parking log with fixed time
        test_log = ClientParking(
            client_id=test_client.id,
            parking_id=test_parking.id,
            time_in=datetime.now() - timedelta(hours=2),
            time_out=datetime.now() - timedelta(hours=1),
        )

        db.session.add(test_log)
        db.session.commit()

        yield db_session

        # Cleanup
        db.session.rollback()
        db.drop_all()
        db.create_all()


@pytest.fixture(scope="function")
def test_data(db_session):
    client = Client.query.first()
    parking = Parking.query.first()
    return {"client": client, "parking": parking}
