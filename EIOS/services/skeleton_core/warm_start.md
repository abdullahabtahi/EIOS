# Warm start: skeleton_core

Holds in-memory state: no

The service keeps no cache, session or model in memory between requests, so a new instance serves correctly from its first request and needs no warm-up. If the owning feature adds in-memory state, change this to `holds in-memory state: yes` and describe the warm-up behaviour.
