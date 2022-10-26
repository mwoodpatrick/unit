import re
import socket
import time

import pytest
from unit.applications.lang.python import TestApplicationPython
from unit.utils import sysctl


class TestSettings(TestApplicationPython):
    prerequisites = {'modules': {'python': 'any'}}

    def test_settings_header_read_timeout(self):
        self.load('empty')

        def req():
            (resp, sock) = self.http(
                b"""GET / HTTP/1.1
""",
                start=True,
                read_timeout=1,
                raw=True,
            )

            time.sleep(3)

            return self.http(
                b"""Host: localhost
Connection: close

    """,
                sock=sock,
                raw=True,
            )

        assert 'success' in self.conf(
            {'http': {'header_read_timeout': 2}}, 'settings'
        )
        assert req()['status'] == 408, 'status header read timeout'

        assert 'success' in self.conf(
            {'http': {'header_read_timeout': 7}}, 'settings'
        )
        assert req()['status'] == 200, 'status header read timeout 2'

    def test_settings_header_read_timeout_update(self):
        self.load('empty')

        assert 'success' in self.conf(
            {'http': {'header_read_timeout': 4}}, 'settings'
        )

        sock = self.http(
            b"""GET / HTTP/1.1
""",
            raw=True,
            no_recv=True,
        )

        time.sleep(2)

        sock = self.http(
            b"""Host: localhost
""",
            sock=sock,
            raw=True,
            no_recv=True,
        )

        time.sleep(2)

        (resp, sock) = self.http(
            b"""X-Blah: blah
""",
            start=True,
            sock=sock,
            read_timeout=1,
            raw=True,
        )

        if len(resp) != 0:
            sock.close()

        else:
            time.sleep(2)

            resp = self.http(
                b"""Connection: close

""",
                sock=sock,
                raw=True,
            )

        assert resp['status'] == 408, 'status header read timeout update'

    def test_settings_body_read_timeout(self):
        self.load('empty')

        def req():
            (resp, sock) = self.http(
                b"""POST / HTTP/1.1
Host: localhost
Content-Length: 10
Connection: close

""",
                start=True,
                raw_resp=True,
                read_timeout=1,
                raw=True,
            )

            time.sleep(3)

            return self.http(b"""0123456789""", sock=sock, raw=True)

        assert 'success' in self.conf(
            {'http': {'body_read_timeout': 2}}, 'settings'
        )
        assert req()['status'] == 408, 'status body read timeout'

        assert 'success' in self.conf(
            {'http': {'body_read_timeout': 7}}, 'settings'
        )
        assert req()['status'] == 200, 'status body read timeout 2'

    def test_settings_body_read_timeout_update(self):
        self.load('empty')

        assert 'success' in self.conf(
            {'http': {'body_read_timeout': 4}}, 'settings'
        )

        (resp, sock) = self.http(
            b"""POST / HTTP/1.1
Host: localhost
Content-Length: 10
Connection: close

""",
            start=True,
            read_timeout=1,
            raw=True,
        )

        time.sleep(2)

        (resp, sock) = self.http(
            b"""012""", start=True, sock=sock, read_timeout=1, raw=True
        )

        time.sleep(2)

        (resp, sock) = self.http(
            b"""345""", start=True, sock=sock, read_timeout=1, raw=True
        )

        time.sleep(2)

        resp = self.http(b"""6789""", sock=sock, raw=True)

        assert resp['status'] == 200, 'status body read timeout update'

    def test_settings_send_timeout(self, temp_dir):
        self.load('body_generate')

        def req(addr, data_len):
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(addr)

            req = (
                """GET / HTTP/1.1
Host: localhost
X-Length: %d
Connection: close

"""
                % data_len
            )

            sock.sendall(req.encode())

            data = sock.recv(16).decode()

            time.sleep(3)

            data += self.recvall(sock).decode()

            sock.close()

            return data

        sysctl_out = sysctl()
        values = re.findall(
            r'net.core.[rw]mem_(?:max|default).*?(\d+)', sysctl_out
        )
        values = [int(v) for v in values]

        data_len = 1048576 if len(values) == 0 else 10 * max(values)

        addr = temp_dir + '/sock'

        assert 'success' in self.conf(
            {"unix:" + addr: {'application': 'body_generate'}}, 'listeners'
        )

        assert 'success' in self.conf({'http': {'send_timeout': 1}}, 'settings')

        data = req(addr, data_len)
        assert re.search(r'200 OK', data), 'send timeout status'
        assert len(data) < data_len, 'send timeout data '

        self.conf({'http': {'send_timeout': 7}}, 'settings')

        data = req(addr, data_len)
        assert re.search(r'200 OK', data), 'send timeout status  2'
        assert len(data) > data_len, 'send timeout data 2'

    def test_settings_idle_timeout(self):
        self.load('empty')

        def req():
            (resp, sock) = self.get(
                headers={'Host': 'localhost', 'Connection': 'keep-alive'},
                start=True,
                read_timeout=1,
            )

            time.sleep(3)

            return self.get(sock=sock)

        assert self.get()['status'] == 200, 'init'

        assert 'success' in self.conf({'http': {'idle_timeout': 2}}, 'settings')
        assert req()['status'] == 408, 'status idle timeout'

        assert 'success' in self.conf({'http': {'idle_timeout': 7}}, 'settings')
        assert req()['status'] == 200, 'status idle timeout 2'

    def test_settings_idle_timeout_2(self):
        self.load('empty')

        def req():
            sock = self.http(b'', raw=True, no_recv=True)

            time.sleep(3)

            return self.get(sock=sock)

        assert self.get()['status'] == 200, 'init'

        assert 'success' in self.conf({'http': {'idle_timeout': 1}}, 'settings')
        assert req()['status'] == 408, 'status idle timeout'

        assert 'success' in self.conf({'http': {'idle_timeout': 7}}, 'settings')
        assert req()['status'] == 200, 'status idle timeout 2'

    def test_settings_max_body_size(self):
        self.load('empty')

        assert 'success' in self.conf(
            {'http': {'max_body_size': 5}}, 'settings'
        )

        assert self.post(body='01234')['status'] == 200, 'status size'
        assert self.post(body='012345')['status'] == 413, 'status size max'

    def test_settings_max_body_size_large(self):
        self.load('mirror')

        assert 'success' in self.conf(
            {'http': {'max_body_size': 32 * 1024 * 1024}}, 'settings'
        )

        body = '0123456789abcdef' * 4 * 64 * 1024
        resp = self.post(body=body, read_buffer_size=1024 * 1024)
        assert resp['status'] == 200, 'status size 4'
        assert resp['body'] == body, 'status body 4'

        body = '0123456789abcdef' * 8 * 64 * 1024
        resp = self.post(body=body, read_buffer_size=1024 * 1024)
        assert resp['status'] == 200, 'status size 8'
        assert resp['body'] == body, 'status body 8'

        body = '0123456789abcdef' * 16 * 64 * 1024
        resp = self.post(body=body, read_buffer_size=1024 * 1024)
        assert resp['status'] == 200, 'status size 16'
        assert resp['body'] == body, 'status body 16'

        body = '0123456789abcdef' * 32 * 64 * 1024
        resp = self.post(body=body, read_buffer_size=1024 * 1024)
        assert resp['status'] == 200, 'status size 32'
        assert resp['body'] == body, 'status body 32'

    @pytest.mark.skip('not yet')
    def test_settings_negative_value(self):
        assert 'error' in self.conf(
            {'http': {'max_body_size': -1}}, 'settings'
        ), 'settings negative value'

    def test_settings_body_buffer_size(self):
        self.load('mirror')

        assert 'success' in self.conf(
            {
                'http': {
                    'max_body_size': 64 * 1024 * 1024,
                    'body_buffer_size': 32 * 1024 * 1024,
                }
            },
            'settings',
        )

        body = '0123456789abcdef'
        resp = self.post(body=body)
        assert bool(resp), 'response from application'
        assert resp['status'] == 200, 'status'
        assert resp['body'] == body, 'body'

        body = '0123456789abcdef' * 1024 * 1024
        resp = self.post(body=body, read_buffer_size=1024 * 1024)
        assert bool(resp), 'response from application 2'
        assert resp['status'] == 200, 'status 2'
        assert resp['body'] == body, 'body 2'

        body = '0123456789abcdef' * 2 * 1024 * 1024
        resp = self.post(body=body, read_buffer_size=1024 * 1024)
        assert bool(resp), 'response from application 3'
        assert resp['status'] == 200, 'status 3'
        assert resp['body'] == body, 'body 3'

        body = '0123456789abcdef' * 3 * 1024 * 1024
        resp = self.post(body=body, read_buffer_size=1024 * 1024)
        assert bool(resp), 'response from application 4'
        assert resp['status'] == 200, 'status 4'
        assert resp['body'] == body, 'body 4'
