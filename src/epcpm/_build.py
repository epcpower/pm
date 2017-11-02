try:
    from epcpm.__build import (
        build_system,
        build_id,
        build_number,
        build_version,
        job_id,
        job_url,
    )
except ImportError:
    build_system = None
    build_id = None
    build_number = None
    build_version = None
    job_id = None
    job_url = None
