import logging

from ipware import get_client_ip


class AddIPFilter(logging.Filter):
    def filter(self, record):
        if hasattr(record, "request"):
            client_ip, is_routable = get_client_ip(record.request)  # type: ignore

            record.ip = f"{client_ip} ({'public' if is_routable else 'private'})"
        else:
            record.ip = "-"
        return True


class AddRequestParamsFilter(logging.Filter):
    def filter(self, record):
        if hasattr(record, "request"):
            record.params = record.request.get_full_path()  # type: ignore
        else:
            record.params = "-"

        return True
