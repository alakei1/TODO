import os
import sys
from pathlib import Path

root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from datetime import datetime

import pytest

from app.extensions import db
from app.models import Client, ClientParking, Parking
from factories import ClientFactory, ParkingFactory


class TestAPI:
    @pytest.mark.parametrize('endpoint', [
        '/clients',
        '/clients/1',
    ])
    def test_get_endpoints_status_200(self, client, db_session, endpoint):
        """Тест GET endpoints возвращают статус 200"""
        response = client.get(endpoint)
        assert response.status_code == 200

    def test_create_client(self, client, db_session):
        """Тест создания клиента"""
        data = {
            'name': 'Jane',
            'surname': 'Smith',
            'credit_card': '9876543210987654',
            'car_number': 'XYZ789'
        }

        initial_count = Client.query.count()
        response = client.post('/clients', json=data)

        assert response.status_code == 201
        assert Client.query.count() == initial_count + 1

        response_data = response.get_json()
        assert response_data['name'] == 'Jane'
        assert response_data['surname'] == 'Smith'
        assert 'id' in response_data

    def test_create_parking(self, client, db_session):
        """Тест создания парковки"""
        data = {
            'address': 'New Parking 456',
            'count_places': 20,
            'opened': True
        }

        initial_count = Parking.query.count()
        response = client.post('/parkings', json=data)

        assert response.status_code == 201
        assert Parking.query.count() == initial_count + 1

        response_data = response.get_json()
        assert response_data['address'] == 'New Parking 456'
        assert response_data['count_places'] == 20
        assert response_data['count_available_places'] == 20
        assert 'id' in response_data

    @pytest.mark.parking
    def test_enter_parking(self, client, db_session):
        """Тест заезда на парковку"""
        # Создаем клиента с картой
        client_obj = Client(
            name='Test',
            surname='User',
            credit_card='1111222233334444',
            car_number='TEST123'
        )
        parking_obj = Parking(
            address='Test Parking',
            opened=True,
            count_places=5,
            count_available_places=3
        )
        db.session.add(client_obj)
        db.session.add(parking_obj)
        db.session.flush()

        data = {
            'client_id': client_obj.id,
            'parking_id': parking_obj.id
        }

        initial_available = parking_obj.count_available_places
        response = client.post('/client_parkings', json=data)

        assert response.status_code == 201
        db.session.refresh(parking_obj)
        assert parking_obj.count_available_places == initial_available - 1

        # Проверяем, что создалась запись о парковке
        log = ClientParking.query.filter_by(
            client_id=client_obj.id,
            parking_id=parking_obj.id,
            time_out=None
        ).first()
        assert log is not None
        assert log.time_in is not None

    @pytest.mark.parking
    def test_exit_parking(self, client, db_session):
        """Тест выезда с парковки"""
        # Создаем клиента с картой
        client_obj = Client(
            name='Test',
            surname='User',
            credit_card='1111222233334444',
            car_number='TEST123'
        )
        parking_obj = Parking(
            address='Test Parking',
            opened=True,
            count_places=5,
            count_available_places=3
        )
        db.session.add(client_obj)
        db.session.add(parking_obj)
        db.session.flush()

        # Создаем активную запись о парковке
        parking_log = ClientParking(
            client_id=client_obj.id,
            parking_id=parking_obj.id,
            time_in=datetime.now()
        )
        db.session.add(parking_log)
        db.session.commit()

        data = {
            'client_id': client_obj.id,
            'parking_id': parking_obj.id
        }

        initial_available = parking_obj.count_available_places
        response = client.delete('/client_parkings', json=data)

        assert response.status_code == 200
        db.session.refresh(parking_obj)
        assert parking_obj.count_available_places == initial_available + 1

        # Проверяем, что время выезда установлено
        log = ClientParking.query.filter_by(
            client_id=client_obj.id,
            parking_id=parking_obj.id
        ).first()
        assert log.time_out is not None
        assert log.time_out > log.time_in

    def test_create_client_with_factory(self, client, db_session):
        """Тест создания клиента с использованием ClientFactory"""
        initial_count = Client.query.count()
        test_client = ClientFactory()

        assert Client.query.count() == initial_count + 1
        saved_client = Client.query.filter_by(id=test_client.id).first()
        assert saved_client is not None
        assert saved_client.name is not None
        assert saved_client.surname is not None

    def test_create_parking_with_factory(self, client, db_session):
        """Тест создания парковки с использованием ParkingFactory"""
        initial_count = Parking.query.count()
        test_parking = ParkingFactory()

        assert Parking.query.count() == initial_count + 1
        saved_parking = Parking.query.filter_by(id=test_parking.id).first()
        assert saved_parking is not None
        assert saved_parking.address is not None
        assert saved_parking.count_places > 0
        assert saved_parking.count_available_places == saved_parking.count_places

    def test_enter_parking_with_no_credit_card(self, client, db_session):
        """Тест заезда без привязанной карты"""
        # Создаем клиента без карты
        client_obj = Client(
            name='NoCard',
            surname='User',
            credit_card=None,
            car_number='NOCARD'
        )
        parking_obj = Parking(
            address='Test Parking',
            opened=True,
            count_places=5,
            count_available_places=3
        )
        db.session.add(client_obj)
        db.session.add(parking_obj)
        db.session.flush()

        data = {
            'client_id': client_obj.id,
            'parking_id': parking_obj.id
        }

        response = client.post('/client_parkings', json=data)
        assert response.status_code == 400
        assert 'credit card' in response.get_json()['error'].lower()

    def test_enter_parking_with_closed_parking(self, client, db_session):
        """Тест заезда на закрытую парковку"""
        client_obj = Client(
            name='Test',
            surname='User',
            credit_card='1111222233334444',
            car_number='TEST123'
        )
        parking_obj = Parking(
            address='Closed Parking',
            opened=False,  # Парковка закрыта
            count_places=5,
            count_available_places=3
        )
        db.session.add(client_obj)
        db.session.add(parking_obj)
        db.session.flush()

        data = {
            'client_id': client_obj.id,
            'parking_id': parking_obj.id
        }

        response = client.post('/client_parkings', json=data)
        assert response.status_code == 400
        assert 'closed' in response.get_json()['error'].lower()

    def test_enter_parking_no_available_places(self, client, db_session):
        """Тест заезда на парковку без свободных мест"""
        client_obj = Client(
            name='Test',
            surname='User',
            credit_card='1111222233334444',
            car_number='TEST123'
        )
        parking_obj = Parking(
            address='Full Parking',
            opened=True,
            count_places=5,
            count_available_places=0  # Нет свободных мест
        )
        db.session.add(client_obj)
        db.session.add(parking_obj)
        db.session.flush()

        data = {
            'client_id': client_obj.id,
            'parking_id': parking_obj.id
        }

        response = client.post('/client_parkings', json=data)
        assert response.status_code == 400
        assert 'available' in response.get_json()['error'].lower()