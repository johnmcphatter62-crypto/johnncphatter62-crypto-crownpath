from sqlalchemy import select
from sqlalchemy.orm import Session
from crownpath.models import User, AudioStation, AuditEvent, AudioZone, AudioSchedule, AudioDevice, AudioZoneDevice

class UserRepository:
    def __init__(self, db: Session): self.db = db
    def by_id(self, user_id: str): return self.db.get(User, user_id)
    def by_email(self, email: str): return self.db.scalar(select(User).where(User.email == email.strip().lower()))
    def add(self, user: User): self.db.add(user); return user

class AudioStationRepository:
    def __init__(self, db: Session): self.db = db
    def list_enabled(self): return list(self.db.scalars(select(AudioStation).where(AudioStation.enabled.is_(True)).order_by(AudioStation.name)))
    def by_id(self, station_id: str): return self.db.get(AudioStation, station_id)
    def add(self, station: AudioStation): self.db.add(station); return station

class AuditRepository:
    def __init__(self, db: Session): self.db = db
    def add(self, event: AuditEvent): self.db.add(event); return event

class AudioZoneRepository:
    def __init__(self, db: Session): self.db = db
    def list_enabled(self): return list(self.db.scalars(select(AudioZone).where(AudioZone.enabled.is_(True)).order_by(AudioZone.name)))
    def by_id(self, zone_id: str): return self.db.get(AudioZone, zone_id)
    def add(self, zone: AudioZone): self.db.add(zone); return zone

class AudioScheduleRepository:
    def __init__(self, db: Session): self.db = db
    def for_zone(self, zone_id: str): return list(self.db.scalars(select(AudioSchedule).where(AudioSchedule.zone_id == zone_id).order_by(AudioSchedule.day_of_week, AudioSchedule.start_time)))
    def add(self, schedule: AudioSchedule): self.db.add(schedule); return schedule

class AudioDeviceRepository:
    def __init__(self, db: Session): self.db = db
    def list_enabled(self): return list(self.db.scalars(select(AudioDevice).where(AudioDevice.enabled.is_(True)).order_by(AudioDevice.name)))
    def by_id(self, device_id: str): return self.db.get(AudioDevice, device_id)
    def add(self, device: AudioDevice): self.db.add(device); return device

class AudioZoneDeviceRepository:
    def __init__(self, db: Session): self.db = db
    def for_zone(self, zone_id: str): return list(self.db.scalars(select(AudioZoneDevice).where(AudioZoneDevice.zone_id == zone_id, AudioZoneDevice.enabled.is_(True))))
    def mapping(self, zone_id: str, device_id: str): return self.db.scalar(select(AudioZoneDevice).where(AudioZoneDevice.zone_id == zone_id, AudioZoneDevice.device_id == device_id))
    def add(self, mapping: AudioZoneDevice): self.db.add(mapping); return mapping
