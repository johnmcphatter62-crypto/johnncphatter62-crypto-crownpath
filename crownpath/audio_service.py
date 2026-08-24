from datetime import datetime, timezone
import uuid
from crownpath.models import AudioStation, AudioZone, AudioSchedule, AuditEvent
from crownpath.repositories import AudioStationRepository, AudioZoneRepository, AudioScheduleRepository, AuditRepository
from crownpath.transactions import transaction

DEFAULT_STATIONS = [
 {"station_id":"CP-AUDIO-JAZZ","name":"CrownPath Jazz Station","category":"JAZZ","source_type":"LICENSED_STREAM","source_reference":None},
 {"station_id":"CP-AUDIO-INSTRUMENTAL","name":"CrownPath Instrumental Station","category":"INSTRUMENTAL","source_type":"LICENSED_STREAM","source_reference":None},
 {"station_id":"CP-AUDIO-RELAX","name":"CrownPath Relaxation Station","category":"RELAXATION","source_type":"LICENSED_STREAM","source_reference":None},
]
DEFAULT_ZONES = [
 {"zone_id":"CP-ZONE-WAITING","name":"Client Waiting Area","location_type":"WAITING_AREA","station_id":"CP-AUDIO-JAZZ","volume":28},
 {"zone_id":"CP-ZONE-BARBER","name":"Barber Service Area","location_type":"BARBER_AREA","station_id":"CP-AUDIO-JAZZ","volume":34},
 {"zone_id":"CP-ZONE-SALON","name":"Cosmetology Service Area","location_type":"SALON_AREA","station_id":"CP-AUDIO-INSTRUMENTAL","volume":30},
]

def seed_audio_stations():
    with transaction() as db:
        repo=AudioStationRepository(db)
        for item in DEFAULT_STATIONS:
            if not repo.by_id(item['station_id']): repo.add(AudioStation(**item))

def seed_audio_zones():
    with transaction() as db:
        repo=AudioZoneRepository(db)
        for item in DEFAULT_ZONES:
            if not repo.by_id(item['zone_id']): repo.add(AudioZone(**item))

def list_audio_stations():
    with transaction() as db:
        return [{"station_id":s.station_id,"name":s.name,"category":s.category,"enabled":s.enabled,"client_facing":s.client_facing,"source_type":s.source_type,"configured":bool(s.source_reference)} for s in AudioStationRepository(db).list_enabled()]

def list_audio_zones():
    with transaction() as db:
        return [{"zone_id":z.zone_id,"name":z.name,"location_type":z.location_type,"station_id":z.station_id,"volume":z.volume,"muted":z.muted,"enabled":z.enabled} for z in AudioZoneRepository(db).list_enabled()]

def update_zone(zone_id, station_id=None, volume=None, muted=None):
    with transaction() as db:
        zone=AudioZoneRepository(db).by_id(zone_id)
        if not zone: return None
        if station_id is not None: zone.station_id=station_id
        if volume is not None: zone.volume=max(0,min(100,int(volume)))
        if muted is not None: zone.muted=bool(muted)
        return {"zone_id":zone.zone_id,"station_id":zone.station_id,"volume":zone.volume,"muted":zone.muted}

def add_schedule(zone_id,day_of_week,start_time,end_time,station_id):
    schedule_id=f"CP-SCHED-{uuid.uuid4().hex[:10].upper()}"
    with transaction() as db:
        if not AudioZoneRepository(db).by_id(zone_id) or not AudioStationRepository(db).by_id(station_id): return None
        AudioScheduleRepository(db).add(AudioSchedule(schedule_id=schedule_id,zone_id=zone_id,day_of_week=day_of_week.upper(),start_time=start_time,end_time=end_time,station_id=station_id))
    return schedule_id

def schedules_for_zone(zone_id):
    with transaction() as db:
        return [{"schedule_id":s.schedule_id,"day_of_week":s.day_of_week,"start_time":s.start_time,"end_time":s.end_time,"station_id":s.station_id,"enabled":s.enabled} for s in AudioScheduleRepository(db).for_zone(zone_id)]

def record_audio_action(user_id,action,zone_id=None,station_id=None,reason=None):
    with transaction() as db:
        AuditRepository(db).add(AuditEvent(user_id=user_id,action=action,category="CLIENT_EXPERIENCE_AUDIO",resource_type="AUDIO_ZONE" if zone_id else "AUDIO_STATION",resource_id=zone_id or station_id,result="SUCCESS",reason=reason,created_at=datetime.now(timezone.utc)))
