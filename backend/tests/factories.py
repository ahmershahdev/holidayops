import datetime

import factory

from apps.accounts.models import User
from apps.calendars.models import Calendar, CalendarSource, CustomDay
from apps.orgs.models import Membership, Organization, Role

PASSWORD = "correct-horse-battery"


class UserFactory(factory.django.DjangoModelFactory[User]):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    name = factory.Faker("name")
    password = factory.django.Password(PASSWORD)


class OrgFactory(factory.django.DjangoModelFactory[Organization]):
    class Meta:
        model = Organization

    name = factory.Sequence(lambda n: f"Org {n}")
    slug = factory.Sequence(lambda n: f"org-{n}")


class MembershipFactory(factory.django.DjangoModelFactory[Membership]):
    class Meta:
        model = Membership

    user = factory.SubFactory(UserFactory)
    org = factory.SubFactory(OrgFactory)
    role = Role.OWNER


class CalendarFactory(factory.django.DjangoModelFactory[Calendar]):
    class Meta:
        model = Calendar

    org = factory.SubFactory(OrgFactory)
    name = factory.Sequence(lambda n: f"Calendar {n}")
    slug = factory.Sequence(lambda n: f"calendar-{n}")


class SourceFactory(factory.django.DjangoModelFactory[CalendarSource]):
    class Meta:
        model = CalendarSource

    calendar = factory.SubFactory(CalendarFactory)
    country = "PK"


class CustomDayFactory(factory.django.DjangoModelFactory[CustomDay]):
    class Meta:
        model = CustomDay

    calendar = factory.SubFactory(CalendarFactory)
    date = datetime.date(2027, 4, 5)
    name = "Office move"
    kind = "closure"
