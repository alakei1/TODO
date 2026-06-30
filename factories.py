import os
import sys
from pathlib import Path

root_dir = Path(__file__).parent
sys.path.insert(0, str(root_dir))

import random

import factory
from factory import Faker

from app.extensions import db
from app.models import Client, Parking


class ClientFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Client
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = "commit"

    name = Faker("first_name")
    surname = Faker("last_name")
    car_number = Faker("license_plate")

    @factory.lazy_attribute
    def credit_card(self):
        # 50% chance to have a credit card
        if random.choice([True, False]):
            return Faker("credit_card_number").evaluate(None, None, {"locale": None})
        return None


class ParkingFactory(factory.alchemy.SQLAlchemyModelFactory):
    class Meta:
        model = Parking
        sqlalchemy_session = db.session
        sqlalchemy_session_persistence = "commit"

    address = Faker("street_address")
    opened = Faker("boolean", chance_of_getting_true=80)
    count_places = Faker("random_int", min=1, max=100)

    @factory.lazy_attribute
    def count_available_places(self):
        return self.count_places
