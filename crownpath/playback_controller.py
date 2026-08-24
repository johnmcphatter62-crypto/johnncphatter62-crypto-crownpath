import uuid
from crownpath.models import AudioDevice, AudioZoneDevice
from crownpath.repositories import AudioDeviceRepository, AudioZoneDeviceRepository, AudioZoneRepository, AudioStationRepository
from crownpath.transactions import transaction

DEFAULT_DEVICES=[
 {"device_id":"CP-DEV-WAITING-01","name":"Waiting Area Speaker","device_type":"NETWORK_SPEAKER","provider":"DEMO","external_reference":None,"online":True,"max_volume":45},
 {"device_id":"CP-DEV-BARBER-01","name":"Barber Area Speaker","device_type":"NETWORK_SPEAKER","provider":"DEMO","external_reference":None,"online":True,"max_volume":55},
 {"device_id":"CP-DEV-SALON-01","name":"Cosmetology Area Speaker","device_type":"NETWORK_SPEAKER","provider":"DEMO","external_reference":None,"online":True,"max_volume":50},
]
DEFAULT_MAPPINGS=[("CP-ZONE-WAITING","CP-DEV-WAITING-01"),("CP-ZONE-BARBER","CP-DEV-BARBER-01"),("CP-ZONE-SALON","CP-DEV-SALON-01")]

def seed_devices():
    with transaction() as db:
        devices=AudioDeviceRepository(db); mappings=AudioZoneDeviceRepository(db)
        for item in DEFAULT_DEVICES:
            if not devices.by_id(item['device_id']): devices.add(AudioDevice(**item))
        for zone_id,device_id in DEFAULT_MAPPINGS:
            if not mappings.mapping(zone_id,device_id): mappings.add(AudioZoneDevice(mapping_id=f"CP-MAP-{uuid.uuid4().hex[:10].upper()}",zone_id=zone_id,device_id=device_id,primary_device=True))

def list_devices():
    with transaction() as db:
        return [{"device_id":d.device_id,"name":d.name,"device_type":d.device_type,"provider":d.provider,"online":d.online,"max_volume":d.max_volume,"configured":bool(d.external_reference)} for d in AudioDeviceRepository(db).list_enabled()]

def zone_devices(zone_id):
    with transaction() as db:
        mappings=AudioZoneDeviceRepository(db).for_zone(zone_id); devices=AudioDeviceRepository(db); results=[]
        for mapping in mappings:
            d=devices.by_id(mapping.device_id)
            if d: results.append({"device_id":d.device_id,"name":d.name,"online":d.online,"max_volume":d.max_volume,"provider":d.provider,"configured":bool(d.external_reference),"primary_device":mapping.primary_device})
        return results

def map_device(zone_id,device_id):
    with transaction() as db:
        mappings=AudioZoneDeviceRepository(db)
        if not AudioZoneRepository(db).by_id(zone_id) or not AudioDeviceRepository(db).by_id(device_id): return False
        if not mappings.mapping(zone_id,device_id): mappings.add(AudioZoneDevice(mapping_id=f"CP-MAP-{uuid.uuid4().hex[:10].upper()}",zone_id=zone_id,device_id=device_id,primary_device=True))
        return True

def effective_zone_volume(zone_id):
    with transaction() as db:
        zone=AudioZoneRepository(db).by_id(zone_id)
        if not zone: return None
        limits=[d['max_volume'] for d in zone_devices(zone_id) if d['online']]
        if not limits: return {"zone_id":zone_id,"requested_volume":zone.volume,"effective_volume":0,"muted":True,"reason":"No online playback device"}
        hard_limit=min(limits); effective=min(zone.volume,hard_limit)
        return {"zone_id":zone_id,"requested_volume":zone.volume,"effective_volume":0 if zone.muted else effective,"muted":zone.muted,"device_limit":hard_limit}

def playback_state(zone_id):
    with transaction() as db:
        zone=AudioZoneRepository(db).by_id(zone_id)
        if not zone: return None
        station=AudioStationRepository(db).by_id(zone.station_id) if zone.station_id else None
        devices=zone_devices(zone_id); volume=effective_zone_volume(zone_id)
        ready=bool(station and station.source_reference and any(d['online'] and d['configured'] for d in devices))
        return {"zone_id":zone.zone_id,"zone_name":zone.name,"station_id":zone.station_id,"station_name":station.name if station else None,"devices":devices,"volume":volume,"playback_ready":ready,"demo_mode":True}
