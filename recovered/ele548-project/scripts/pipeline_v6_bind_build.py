"""Bind completed NEW BUILD2 to exact copied and reused source before CPU."""
from pipeline_v6_common import *
def bind_build():
 dest=OUT/'configs/BUILD_2_BINDING.json'
 if dest.exists():
  d=json.loads(dest.read_text());verify_sources()
  assert sha(BINARY)==d['binary_sha256'] and sha(OUT/'configs/source.lock.json')==d['source_lock_sha256']
  return d
 log=OUT/'reports/BUILD_2.log';timing=OUT/'reports/BUILD_2.time';lock=OUT/'configs/source.lock.json'
 assert timing.exists() and timing.stat().st_size and 'scons: done building targets.' in log.read_text(errors='replace'),'BUILD2_NOT_COMPLETE'
 assert BINARY.stat().st_mtime>=lock.stat().st_mtime,'BINARY_OLDER_THAN_PREPARED_SOURCE'
 verify_sources()
 d=dict(status='COMPLETED_BUILD2_SOURCE_CONFIG_TRANSPORT_BOUND_BEFORE_CPU',binary=str(BINARY.relative_to(ROOT)),binary_sha256=sha(BINARY),
  config=str(CONFIG.relative_to(ROOT)),config_sha256=sha(CONFIG),source_lock_sha256=sha(lock),
  build_log_sha256=sha(log),build_time_sha256=sha(timing),at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
  build1='Superseded before any CPU; copied BUILD1 source snapshot retained. No active old producer modified.')
 write(dest,d);return d
if __name__=='__main__':bind_build();print('PASS exact completed BUILD2 source/transport/config/binary binding')
