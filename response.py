# coding=utf-8
import io
from email.utils import formatdate
from string import Template

from status_codes import codes


class Body:
    def __init__ (self, body, *args, **kwargs):
        if isinstance(body, str):
            self.encoding = kwargs["encoding"]
            body = body.encode(self.encoding)
            self.length = len(body)
            self.io_raw_stream = io.BytesIO(body)
        elif isinstance(body, io.FileIO):
            self.io_raw_stream = body
            current_position = self.io_raw_stream.tell()
            self.io_raw_stream.seek(0, io.SEEK_END)
            self.length = self.io_raw_stream.tell()
            self.io_raw_stream.seek(current_position, io.SEEK_SET)

    def __len__ (self):
        return self.length

    def __iter__ (self):
        return self

    def __next__ (self):
        bytes = self.io_raw_stream.read(2048)
        if bytes:
            return bytes
        else:
            raise StopIteration


class Response:
    response_http_header_template = Template('''HTTP/$http_protocol_version $code $status\n$headers\n\n''')

    content_type_template = Template('''$type; charset=$encoding''')

    header_template = Template('''$header_field: $value''')

    def __init__ (self, status_code: int, body = "", headers: dict = None, encoding: str = "utf-8", mimetype: str = "text/plain", protocol_version: float = 1.1):
        # cant set headers to default argument's value
        if not headers:
            headers = { }
        self.body = Body(body, encoding=encoding)
        self.headers = {
            "Content-Type"  : Response.content_type_template.safe_substitute({
                "type"    : mimetype,
                "encoding": encoding
            }),
            # The length of the request body in octets (8-bit bytes).
            "Content-Length": str(len(self.body)),
            "Date"          : formatdate(timeval=None, localtime=False, usegmt=True),
            "Server"        : "socket server"
        }
        self.headers.update(headers)
        self.http_args = {
            "http_protocol_version": str(protocol_version),
            "code"                 : status_code,
            "status"               : codes[str(status_code)],
            "headers"              : self.generate_headers(self.headers)
        }
        self.http_head = Response.response_http_header_template.safe_substitute(self.http_args)

    def generate_headers (self, headers: dict):
        return "\n".join([Response.header_template.safe_substitute({
            "header_field": k,
            "value"       : v
        }) for k, v in headers.items()])

    def __str__ (self) -> str:
        return self.http_head

    def __repr__ (self) -> str:
        return self.__str__()

    def __iter__ (self):
        return self.iter(self.http_head, self.body)

    def __call__ (self, *args, **kwargs):
        return self.__iter__()

    def iter (self, head, body):
        yield head.encode("ascii")
        for chunk in body:
            yield chunk
        raise StopIteration
